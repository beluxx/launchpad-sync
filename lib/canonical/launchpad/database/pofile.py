# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""`SQLObject` implementation of `IPOFile` interface."""

__metaclass__ = type
__all__ = [
    'POFile',
    'DummyPOFile',
    'POFileSet',
    'POFileToTranslationFileDataAdapter',
    'POFileTranslator',
    ]

import datetime
import logging
import StringIO
import pytz
from urllib2 import URLError
from sqlobject import (
    ForeignKey, IntCol, StringCol, BoolCol, SQLMultipleJoin
    )
from zope.interface import implements
from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (
    SQLBase, flush_database_updates, quote, sqlvalues)
from canonical.launchpad import helpers
from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.translationimportqueue import (
    TranslationImportQueueEntry)
from canonical.launchpad.database.translationmessage import (
    DummyTranslationMessage, TranslationMessage)
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, ILibraryFileAliasSet, IPersonSet, IPOFile,
    IPOFileSet, IPOFileTranslator, ITranslationExporter,
    ITranslationFileData, ITranslationImporter, IVPOExportSet,
    NotExportedFromLaunchpad, NotFoundError, OutdatedTranslationError,
    RosettaImportStatus, TranslationFormatSyntaxError,
    TranslationFormatInvalidInputError, TranslationPermission,
    TranslationValidationStatus, ZeroLengthPOExportError)
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.mailnotification import MailWrapper
from canonical.launchpad.translationformat import TranslationMessageData
from canonical.launchpad.webapp import canonical_url
from canonical.librarian.interfaces import (
    ILibrarianClient, UploadFailed)


def _check_translation_perms(permission, translators, person):
    """Return True or False dependening on whether the person is part of the
    right group of translators, and the permission on the relevant project,
    product or distribution.

    :param permission: The kind of TranslationPermission.
    :param translators: The list of official translators for the
        product/project/distribution.
    :param person: The person that we want to check if has translation
        permissions.
    """
    # Let's determine if the person is part of a designated translation team
    is_designated_translator = False
    # XXX sabdfl 2005-05-25:
    # This code could be improved when we have implemented CrowdControl.
    for translator in translators:
        if person.inTeam(translator):
            is_designated_translator = True
            break

    # have a look at the applicable permission policy
    if permission == TranslationPermission.OPEN:
        # if the translation policy is "open", then yes, anybody is an
        # editor of any translation
        return True
    elif permission == TranslationPermission.STRUCTURED:
        # in the case of a STRUCTURED permission, designated translators
        # can edit, unless there are no translators, in which case
        # anybody can translate
        if len(translators) > 0:
            # when there are designated translators, only they can edit
            if is_designated_translator is True:
                return True
        else:
            # since there are no translators, anyone can edit
            return True
    elif permission in (TranslationPermission.RESTRICTED,
                        TranslationPermission.CLOSED):
        # if the translation policy is "restricted" or "closed", then check if
        # the person is in the set of translators
        if is_designated_translator:
            return True
    else:
        raise NotImplementedError('Unknown permission %s' % permission.name)

    # ok, thats all we can check, and so we must assume the answer is no
    return False


def _can_edit_translations(pofile, person):
    """Say if a person is able to edit existing translations.

    Return True or False indicating whether the person is allowed
    to edit these translations.

    Admins and Rosetta experts are always able to edit any translation.
    If the `IPOFile` is for an `IProductSeries`, the owner of the `IProduct`
    has also permissions.
    Any other mortal will have rights depending on if he/she is on the right
    translation team for the given `IPOFile`.translationpermission and the
    language associated with this `IPOFile`.
    """
    # If the person is None, then they cannot edit
    if person is None:
        return False

    # XXX Carlos Perello Marin 2006-02-07 bug=4814:
    # We should not check the permissions here but use the standard
    # security system.

    # XXX Carlos Perello Marin 2006-02-08 bug=30789:
    # The check person.id == rosetta_experts.id must be removed as soon as
    # the is closed.

    # Rosetta experts and admins can always edit translations.
    admins = getUtility(ILaunchpadCelebrities).admin
    rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_expert
    if (person.inTeam(admins) or person.inTeam(rosetta_experts) or
        person.id == rosetta_experts.id):
        return True

    # The owner of the product is also able to edit translations.
    if pofile.potemplate.productseries is not None:
        product = pofile.potemplate.productseries.product
        if person.inTeam(product.owner):
            return True

    # Finally, check whether the user is member of the translation team or
    # owner for the given PO file.
    translators = [t.translator for t in pofile.translators]
    return _check_translation_perms(
        pofile.translationpermission,
        translators,
        person) or person.inTeam(pofile.owner)

def _can_add_suggestions(pofile, person):
    """Whether a person is able to add suggestions.

    Any user that can edit translations can add suggestions, the others will
    be able to add suggestions only if the permission is not CLOSED.
    """
    return (_can_edit_translations(pofile, person) or
            pofile.translationpermission <> TranslationPermission.CLOSED)


class POFileMixIn(RosettaStats):
    """Base class for `POFile` and `DummyPOFile`.

    Provides machinery for retrieving `TranslationMessage`s and populating
    their submissions caches.  That machinery is needed even for
    `DummyPOFile`s.
    """

    def getHeader(self):
        """See `IPOFile`."""
        translation_importer = getUtility(ITranslationImporter)
        format_importer = translation_importer.getTranslationFormatImporter(
            self.potemplate.source_file_format)
        header = format_importer.getHeaderFromString(self.header)
        header.comment = self.topcomment
        header.has_plural_forms = self.potemplate.hasPluralMessage()
        return header

    def getCurrentTranslationMessage(self, msgid_text, context=None,
                                     ignore_obsolete=False):
        """See `IPOFile`."""
        if not isinstance(msgid_text, unicode):
            raise AssertionError(
                "Can't index with type %s. (Must be unicode.)"
                % type(msgid_text))

        potmsgset = self.potemplate.getPOTMsgSetByMsgIDText(key=msgid_text,
                                                            context=context)
        return self.getCurrentTranslationMessageFromPOTMsgSet(
            potmsgset, ignore_obsolete=ignore_obsolete)

    def getCurrentSuggestions(self, potmsgsets):
        """See `IPOTemplate`."""
        raise NotImplementedError
#        if not potmsgsets:
#            return
#        for potmsgset in potmsgsets:
#            assert potmsgset.potemplate == self.potemplate, (
#                "Requesting external suggestions in wrong template.")
#
#        parameters = {}
#        parameters['this_template'] = quote(self.potemplate)
#        parameters['language'] = quote(self.language)
#        parameters['wanted_msgids'] = ', '.join([
#            quote(msgid) for msgid in takers_for_msgid.keys()])
#
#        cur = cursor()
#
#        # Retrieve (the ids of) external suggestions, and for each, the
#        # message identifier (original English message, in the singular) it
#        # translates.
#        # The msgids come from the suggestions' potmsgsets, not from the
#        # potmsgsets we got in our parameter.  We need to know those msgids,
#        # but we avoid retrieving the potmsgsets from the database.
#        cur.execute("""
#            SELECT DISTINCT id, msgid_singular FROM (
#                SELECT
#                    DISTINCT ON (
#                        msgid_singular,
#                        msgstr0,
#                        msgstr1,
#                        msgstr2,
#                        msgstr3)
#                    Suggestion.id,
#                    Suggestion.msgstr0,
#                    Suggestion.msgstr1,
#                    Suggestion.msgstr2,
#                    Suggestion.msgstr3,
#                    POTMsgSet.msgid_singular
#                FROM TranslationMessage Suggestion
#                JOIN POTMsgSet ON Suggestion.potmsgset = POTMsgSet.id
#                JOIN POFile ON Suggestion.pofile = POFile.id
#                -- If this is slow, we can try joining POTemplate in through
#                -- POTMsgSet instead.
#                JOIN POTemplate ON POFile.potemplate = POTemplate.id
#                LEFT JOIN ProductSeries ON
#                    POTemplate.productseries = ProductSeries.id
#                LEFT JOIN Product ON ProductSeries.product = Product.id
#                LEFT JOIN DistroRelease ON
#                    POTemplate.distrorelease = DistroRelease.id
#                LEFT JOIN Distribution ON
#                    DistroRelease.distribution = Distribution.id
#                -- If there's a more recent translation message offering the
#                -- exact same translations, never mind the current one.
#                -- XXX CarlosPerelloMarin 20071107 This is crap and useless,
#                -- we should look in the local potmsgset not in the
#                -- suggestions ones...
#                LEFT JOIN TranslationMessage AS Better ON
#                    Better.potmsgset = Suggestion.potmsgset AND
#                    COALESCE(Better.msgstr0, -1) =
#                        COALESCE(Suggestion.msgstr0, -1) AND
#                    COALESCE(Better.msgstr1, -1) =
#                        COALESCE(Suggestion.msgstr1, -1) AND
#                    COALESCE(Better.msgstr2, -1) =
#                        COALESCE(Suggestion.msgstr2, -1) AND
#                    COALESCE(Better.msgstr3, -1) =
#                        COALESCE(Suggestion.msgstr3, -1))
#                WHERE
#                    POTMsgSet.msgid_singular IN (%(wanted_msgids)s) AND
#                    POTemplate.id <> %(this_template)s AND
#                    POTemplate.iscurrent AND
#                    Suggestion.is_current AND
#                    POFile.language = %(language)s AND
#                    NOT Suggestion.is_fuzzy AND
#                    COALESCE(msgstr0, msgstr1, msgstr2, msgstr3)
#                        IS NOT NULL AND
#                    (Product.official_rosetta OR
#                     Distribution.official_rosetta) AND
#                    Better.id IS NULL
#                    )
#                ORDER BY
#                    msgid_singular,
#                    msgstr0,
#                    msgstr1,
#                    msgstr2,
#                    msgstr3,
#                    Suggestion.id DESC
#                ) AS Suggestions
#            """ % parameters)
#
#        external_suggestions = cur.fetchall()
#
#        if external_translations:
#            # Retrieve the actual suggestions.  Keep these in
#            # newest-to-oldest order, because that's the way the view
#            # class likes them.
#            messages_query = TranslationMessage.select(
#                "id IN (%s)" % ", ".join(
#                    [quote(id) for id in external_translations]),
#                orderBy="-datecreated")
#            messages = shortlist(
#                messages_query, longest_expected=100, hardlimit=200)
#        else:
#            messages = []
#
#        suggestions_by_id = dict(
#            (message.id, message) for message in messages)
#
#        # For each of the message identifiers belonging to potmsgsets,
#        # exactly which potmsgsets could benefit from a suggestion for
#        # that message identifier?  There could be multiple because the
#        # same message identifier may occur in different contexts.
#        takers_for_msgid = dict(
#            (potmsgset.msgid_singular, []) for potmsgset in potmsgsets)
#        for potmsgset in potmsgsets:
#            takers_for_msgid[potmsgset.msgid_singular].append(potmsgset)
#
#        # Figure out which of potmsgsets each suggestion is relevant to,
#        # and return our mapping from potmsgsets to various subsets of
#        # load_submissions.  The subsets may overlap because two
#        # potmsgsets could have the same msgid (i.e. translate the same
#        # string) but in different contexts.  The same suggestions would
#        # apply to both.
#        # Suggestions are still kept in new-to-old order.
#        result = dict((potmsgset, []) for potmsgset in potmsgsets)
#        for translationmessage_id, msgid in external_suggestions:
#            suggestion = suggestions_by_id[translationmessage_id]
#            result[takers_for_msgid[msgid]].append(suggestion)
#
#        return result

    def getExternalSuggestions(self, potmsgsets):
        """See `IPOTemplate`."""
        raise NotImplementedError
#        # XXX JeroenVermeulen 2007-11-08: Unify this with
#        # getCurrentSuggestions(), and sort out the current suggestions from
#        # the full set at the call site.
#        if not potmsgsets:
#            return
#        for potmsgset in potmsgsets:
#            assert potmsgset.potemplate == self.potemplate, (
#                "Requesting external suggestions in wrong template.")
#
#        parameters = {}
#        parameters['this_template'] = quote(self.potemplate)
#        parameters['language'] = quote(self.language)
#        parameters['wanted_msgids'] = ', '.join([
#            quote(msgid) for msgid in takers_for_msgid.keys()])
#
#        cur = cursor()
#
#        # Retrieve (the ids of) external suggestions, and for each, the
#        # message identifier (original English message, in the singular) it
#        # translates.
#        # The msgids come from the suggestions' potmsgsets, not from the
#        # potmsgsets we got in our parameter.  We need to know those msgids,
#        # but we avoid retrieving the potmsgsets from the database.
#        cur.execute("""
#            SELECT DISTINCT id, msgid_singular FROM (
#                SELECT
#                    DISTINCT ON (
#                        msgid_singular,
#                        msgstr0,
#                        msgstr1,
#                        msgstr2,
#                        msgstr3)
#                    Suggestion.id,
#                    Suggestion.msgstr0,
#                    Suggestion.msgstr1,
#                    Suggestion.msgstr2,
#                    Suggestion.msgstr3,
#                    POTMsgSet.msgid_singular
#                FROM TranslationMessage Suggestion
#                JOIN POTMsgSet ON Suggestion.potmsgset = POTMsgSet.id
#                JOIN POFile ON Suggestion.pofile = POFile.id
#                -- If this is slow, we can try joining POTemplate in through
#                -- POTMsgSet instead.
#                JOIN POTemplate ON POFile.potemplate = POTemplate.id
#                LEFT JOIN ProductSeries ON
#                    POTemplate.productseries = ProductSeries.id
#                LEFT JOIN Product ON ProductSeries.product = Product.id
#                LEFT JOIN DistroRelease ON
#                    POTemplate.distrorelease = DistroRelease.id
#                LEFT JOIN Distribution ON
#                    DistroRelease.distribution = Distribution.id
#                WHERE
#                    POTMsgSet.msgid_singular IN (%(wanted_msgids)s) AND
#                    POTemplate.id <> %(this_template)s AND
#                    POTemplate.iscurrent AND
#                    Suggestion.is_current IS FALSE AND
#                    POFile.language = %(language)s AND
#                    NOT Suggestion.is_fuzzy AND
#                    COALESCE(msgstr0, msgstr1, msgstr2, msgstr3)
#                        IS NOT NULL AND
#                    (Product.official_rosetta OR
#                     Distribution.official_rosetta) AND
#                    Better.id IS NULL
#                    )
#                ORDER BY
#                    msgid_singular,
#                    msgstr0,
#                    msgstr1,
#                    msgstr2,
#                    msgstr3,
#                    Suggestion.id DESC
#                ) AS Suggestions
#            """ % parameters)
#
#        external_suggestions = cur.fetchall()
#
#        if external_translations:
#            # Retrieve the actual suggestions.  Keep these in
#            # newest-to-oldest order, because that's the way the view
#            # class likes them.
#            messages_query = TranslationMessage.select(
#                "id IN (%s)" % ", ".join(
#                    [quote(id) for id in external_translations]),
#                orderBy="-datecreated")
#            messages = shortlist(
#                messages_query, longest_expected=100, hardlimit=200)
#        else:
#            messages = []
#
#        suggestions_by_id = dict(
#            (message.id, message) for message in messages)
#
#        # For each of the message identifiers belonging to potmsgsets,
#        # exactly which potmsgsets could benefit from a suggestion for
#        # that message identifier?  There could be multiple because the
#        # same message identifier may occur in different contexts.
#        takers_for_msgid = dict(
#            (potmsgset.msgid_singular, []) for potmsgset in potmsgsets)
#        for potmsgset in potmsgsets:
#            takers_for_msgid[potmsgset.msgid_singular].append(potmsgset)
#
#        # Figure out which of potmsgsets each suggestion is relevant to,
#        # and return our mapping from potmsgsets to various subsets of
#        # load_submissions.  The subsets may overlap because two
#        # potmsgsets could have the same msgid (i.e. translate the same
#        # string) but in different contexts.  The same suggestions would
#        # apply to both.
#        # Suggestions are still kept in new-to-old order.
#        result = dict((potmsgset, []) for potmsgset in potmsgsets)
#        for translationmessage_id, msgid in external_suggestions:
#            suggestion = suggestions_by_id[translationmessage_id]
#            result[takers_for_msgid[msgid]].append(suggestion)
#
#        return result


class POFile(SQLBase, POFileMixIn):
    implements(IPOFile)

    _table = 'POFile'

    potemplate = ForeignKey(foreignKey='POTemplate',
                            dbName='potemplate',
                            notNull=True)
    language = ForeignKey(foreignKey='Language',
                          dbName='language',
                          notNull=True)
    description = StringCol(dbName='description',
                            notNull=False,
                            default=None)
    topcomment = StringCol(dbName='topcomment',
                           notNull=False,
                           default=None)
    header = StringCol(dbName='header',
                       notNull=False,
                       default=None)
    fuzzyheader = BoolCol(dbName='fuzzyheader',
                          notNull=True)
    lasttranslator = ForeignKey(foreignKey='Person',
                                dbName='lasttranslator',
                                notNull=False,
                                default=None)

    date_changed = UtcDateTimeCol(
        dbName='date_changed', notNull=True, default=UTC_NOW)

    license = IntCol(dbName='license',
                     notNull=False,
                     default=None)
    currentcount = IntCol(dbName='currentcount',
                          notNull=True,
                          default=0)
    updatescount = IntCol(dbName='updatescount',
                          notNull=True,
                          default=0)
    rosettacount = IntCol(dbName='rosettacount',
                          notNull=True,
                          default=0)
    unreviewed_count = IntCol(dbName='unreviewed_count',
                              notNull=True,
                              default=0)
    lastparsed = UtcDateTimeCol(dbName='lastparsed',
                                notNull=False,
                                default=None)
    owner = ForeignKey(foreignKey='Person',
                       dbName='owner',
                       notNull=True)
    variant = StringCol(dbName='variant',
                        notNull=False,
                        default=None)
    path = StringCol(dbName='path',
                     notNull=True)
    exportfile = ForeignKey(foreignKey='LibraryFileAlias',
                            dbName='exportfile',
                            notNull=False,
                            default=None)
    exporttime = UtcDateTimeCol(dbName='exporttime',
                                notNull=False,
                                default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    from_sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='from_sourcepackagename', notNull=False, default=None)

    # joins
    translation_messages = SQLMultipleJoin(
        'TranslationMessage', joinColumn='pofile')

    @property
    def title(self):
        """See `IPOFile`."""
        title = '%s translation of %s' % (
            self.language.displayname, self.potemplate.displayname)
        return title

    @property
    def translators(self):
        """See `IPOFile`."""
        translators = set()
        for group in self.potemplate.translationgroups:
            translator = group.query_translator(self.language)
            if translator is not None:
                translators.add(translator)
        return sorted(list(translators), key=lambda x: x.translator.name)

    @property
    def translationpermission(self):
        """See `IPOFile`."""
        return self.potemplate.translationpermission

    @property
    def contributors(self):
        """See `IPOFile`."""
        return getUtility(IPersonSet).getPOFileContributors(self)

    @property
    def is_cached_export_valid(self):
        """See `IPOFile`."""
        if self.exportfile is None:
            return False

        return self.exporttime >= self.date_changed

    def prepareTranslationCredits(self, potmsgset):
        """See `IPOFile`."""
        msgid = potmsgset.singular_text
        assert potmsgset.is_translation_credit, (
            "Calling prepareTranslationCredits on a message with "
            "msgid '%s'." % msgid)
        imported = potmsgset.getImportedTranslationMessage(self.language)
        if imported is None:
            text = None
        else:
            text = imported.translations[0]
        if msgid in [u'_: EMAIL OF TRANSLATORS\nYour emails', u'Your emails']:
            emails = []
            if text is not None:
                emails.append(text)

            # Add two empty email fields to make formatting nicer.
            # See bug #133817 for details.
            emails.extend([u'',u''])

            for contributor in self.contributors:
                preferred_email = contributor.preferredemail
                if (contributor.hide_email_addresses or
                    preferred_email is None):
                    emails.append('')
                else:
                    emails.append(preferred_email.email)
            return u','.join(emails)
        elif msgid in [u'_: NAME OF TRANSLATORS\nYour names', u'Your names']:
            names = []
            if text is not None:
                names.append(text)
            # Add an empty name as a separator, and 'Launchpad
            # Contributions' header; see bug #133817 for details.
            names.extend([u'',
                          u'Launchpad Contributions:'])
            names.extend([
                contributor.displayname
                for contributor in self.contributors])
            return u','.join(names)
        elif (msgid in [u'translation-credits',
                        u'translator-credits',
                        u'translator_credits']):
            if len(list(self.contributors)):
                if text is None:
                    text = u''
                else:
                    text += u'\n\n'

                text += 'Launchpad Contributions:'
                for contributor in self.contributors:
                    text += ("\n  %s %s" %
                             (contributor.displayname,
                              canonical_url(contributor)))
            return text
        else:
            raise AssertionError(
                "Calling prepareTranslationCredits on a message with "
                "msgid '%s'." % (msgid))

    def canEditTranslations(self, person):
        """See `IPOFile`."""
        return _can_edit_translations(self, person)

    def canAddSuggestions(self, person):
        """See `IPOFile`."""
        return _can_add_suggestions(self, person)

    def translated(self):
        """See `IPOFile`."""
        raise NotImplementedError
        # return iter(TranslationMessage.select('''
        #     POMsgSet.pofile = %d AND
        #     POMsgSet.iscomplete=TRUE AND
        #     POMsgSet.potmsgset = POTMsgSet.id AND
        #     POTMsgSet.sequence > 0''' % self.id,
        #     clauseTables = ['POMsgSet']
        #     ))

    def untranslated(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def __iter__(self):
        """See `IPOFile`."""
        return iter(self.currentMessageSets())

    def getCurrentTranslationMessageFromPOTMsgSet(self, potmsgset,
                                                  ignore_obsolete=False):
        """See `IPOFile`."""
        if potmsgset is None or (ignore_obsolete and potmsgset.sequence <= 0):
            # There is no IPOTMsgSet for this id.
            return None

        current = potmsgset.getCurrentTranslationMessage(self.language)
        if current is None:
            return DummyTranslationMessage(self, potmsgset)
        else:
            return current

    def __getitem__(self, msgid_text):
        """See `IPOFile`."""
        translation_message = self.getCurrentTranslationMessage(
            unicode(msgid_text), ignore_obsolete=True)
        if translation_message is None:
            raise NotFoundError(msgid_text)
        else:
            return translation_message

    def getPOTMsgSetTranslated(self):
        """See `IPOFile`."""
        query = ['POTMsgSet.potemplate = %s' % sqlvalues(self.potemplate)]
        query.append('POTMsgSet.sequence > 0')
        query.append('TranslationMessage.potmsgset = POTMsgSet.id')
        query.append('TranslationMessage.pofile = %s' % sqlvalues(self))
        query.append('NOT TranslationMessage.is_fuzzy')
        for plural_form in range(self.language.pluralforms):
            query.append(
                'TranslationMessage.msgstr%d IS NOT NULL' % plural_form)

        return POTMsgSet.select(
            ' AND '.join(query), clauseTables=['TranslationMessage'],
            orderBy='POTMsgSet.sequence')

    def getPOTMsgSetFuzzy(self):
        """See `IPOFile`."""
        return POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            TranslationMessage.potmsgset = POTMsgSet.id AND
            TranslationMessage.pofile = %s AND
            TranslationMessage.is_fuzzy
            ''' % sqlvalues(self.potemplate, self),
            clauseTables=['TranslationMessage'], orderBy='POTmsgSet.sequence')

    def getPOTMsgSetUntranslated(self):
        """See `IPOFile`."""
        incomplete_check = ['TranslationMessage.msgstr0 IS NULL']
        # Plural forms only matter if we are in a message with a msgid_plural.
        incomplete_plurals_check = ['FALSE']
        for plural_form in range(self.language.pluralforms)[1:]:
            incomplete_plurals_check.append(
                'TranslationMessage.msgstr%d IS NULL' % plural_form)
        incomplete_check.append(
            '(POTMsgSet.msgid_plural IS NOT NULL AND (%s))' % ' OR '.join(
                incomplete_plurals_check))

        # We use a subselect to allow the LEFT OUTER JOIN
        query = """POTMsgSet.id IN (
            SELECT POTMsgSet.id
            FROM POTMsgSet
            LEFT OUTER JOIN TranslationMessage ON
                TranslationMessage.potmsgset = POTMsgSet.id AND
                TranslationMessage.pofile = %s AND
                TranslationMessage.is_current IS TRUE
            WHERE
                POTMsgSet.sequence > 0 AND
                POTMsgSet.potemplate = %s AND
                (TranslationMessage.id IS NULL OR
                 (NOT TranslationMessage.is_fuzzy AND (%s))))
            """ % tuple(
                sqlvalues(self, self.potemplate) +
                (' OR '.join(incomplete_check),))
        return POTMsgSet.select(query, orderBy='POTMsgSet.sequence')

    def getPOTMsgSetWithNewSuggestions(self):
        """See `IPOFile`."""
        # A POT set has "new" suggestions if there is a non current
        # TranslationMessage newer than the current reviewed one.
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            TranslationMessage.potmsgset = POTMsgSet.id AND
            TranslationMessage.pofile = %s AND
            TranslationMessage.is_current IS NOT TRUE AND
            TranslationMessage.date_created > COALESCE(
                (SELECT COALESCE(current.date_reviewed, current.date_created)
                    FROM TranslationMessage current
                    WHERE current.potmsgset = POTMsgSet.id AND
                          current.pofile = TranslationMessage.pofile AND
                          current.id != TranslationMessage.id AND
                          current.is_current IS TRUE
                    LIMIT 1),
                TIMESTAMP '1970-01-01 00:00:00')
            ''' % sqlvalues(self.potemplate, self),
            clauseTables=['TranslationMessage'],
            orderBy='POTmsgSet.sequence',
            distinct=True)

        return results

    def getPOTMsgSetChangedInLaunchpad(self):
        """See `IPOFile`."""
        # POT set has been changed in Launchpad if it contains active
        # translation which didn't come from a published package
        # (iow, it's different from a published translation: this only
        # lists translations which have actually changed in LP, not
        # translations which are 'new' and only exist in LP).
        results = POTMsgSet.select('''POTMsgSet.id IN (
            SELECT POTMsgSet.id
            FROM POTMsgSet
            LEFT JOIN TranslationMessage imported ON
                POTMsgSet.id = imported.potmsgset
            LEFT OUTER JOIN TranslationMessage current ON
                POTMsgSet.id = current.potmsgset AND
                imported.id != current.id AND
                current.pofile = imported.pofile
            WHERE
                imported.pofile = %s AND
                imported.is_imported IS TRUE AND
                current.is_current IS TRUE AND
                POTMsgSet.sequence > 0 AND
                POTMsgSet.potemplate = %s)
            ''' % sqlvalues(self, self.potemplate),
            orderBy='POTmsgSet.sequence')

        return results

    def getPOTMsgSetWithErrors(self, slice=None):
        """See `IPOFile`."""
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            TranslationMessage.potmsgset = POTMsgSet.id AND
            TranslationMessage.pofile = %s AND
            TranslationMessage.is_imported IS TRUE AND
            TranslationMessage.validation_status <> %s
            ''' % sqlvalues(self.potemplate.id, self.id,
                            TranslationValidationStatus.OK),
            clauseTables=['TranslationMessage'],
            orderBy='POTmsgSet.sequence')

        if slice is not None:
            results = results[slice]

        return results

    def hasMessageID(self, messageID):
        """See `IPOFile`."""
        return TranslationMessage.select("""
            TranslationMessage.pofile = %s AND
            TranslationMessage.potmsgset = POTMsgSet.id AND
            POTMsgSet.msgid_singular = %s""" % sqlvalues(
                self, messageID)).count() > 0

    def messageCount(self):
        """See `IRosettaStats`."""
        return self.potemplate.messageCount()

    def currentCount(self, language=None):
        """See `IRosettaStats`."""
        return self.currentcount

    def updatesCount(self, language=None):
        """See `IRosettaStats`."""
        return self.updatescount

    def rosettaCount(self, language=None):
        """See `IRosettaStats`."""
        return self.rosettacount

    def unreviewedCount(self):
        """See `IRosettaStats`."""
        return self.unreviewed_count

    @property
    def fuzzy_count(self):
        """See `IPOFile`."""
        return TranslationMessage.select("""
            TranslationMessage.pofile = %s AND
            TranslationMessage.is_fuzzy AND
            TranslationMessage.is_current AND
            TranslationMessage.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0
            """ % sqlvalues(self), clauseTables=['POTMsgSet']).count()

    def getStatistics(self):
        """See `IPOFile`."""
        return (
            self.currentcount,
            self.updatescount,
            self.rosettacount,
            self.unreviewed_count)

    def updateStatistics(self):
        """See `IPOFile`."""
        # make sure all the data is in the db
        flush_database_updates()

        # Get the number of translations that we got from imports.
        query = ['TranslationMessage.pofile = %s' % sqlvalues(self),
                 'TranslationMessage.is_imported IS TRUE',
                 'NOT TranslationMessage.was_fuzzy_in_last_import',
                 'TranslationMessage.potmsgset = POTMsgSet.id',
                 'POTMsgSet.sequence > 0',
                 'TranslationMessage.msgstr0 IS NOT NULL']
        for plural_form in range(1, self.language.pluralforms):
            query.append(
                '(POTMsgSet.msgid_plural IS NULL OR TranslationMessage.msgstr%d IS NOT NULL)' % plural_form)

        current = TranslationMessage.select(
            ' AND '.join(query), clauseTables=['POTMsgSet']).count()

        # Get the number of translations that we have updated from what we got
        # from imports.
        updates = self.getPOTMsgSetChangedInLaunchpad().count()

        # Get the number of new translations in Launchpad that imported ones
        # were not translated.
        query = ['TranslationMessage.pofile = %s' % sqlvalues(self)]
        query.append('NOT TranslationMessage.is_fuzzy')
        # Check only complete translations.  For messages with only a single
        # msgid, that's anything with a singular translation; for ones with a
        # plural form, it's the number of plural forms the language supports.
        query.append('TranslationMessage.msgstr0 IS NOT NULL')
        for plural_form in range(1, self.language.pluralforms):
            query.append("""
                (POTMsgSet.msgid_plural IS NULL OR
                 TranslationMessage.msgstr%d IS NOT NULL)""" % plural_form)
        query.append('''NOT EXISTS (
            SELECT TranslationMessage.id
            FROM TranslationMessage AS imported
            WHERE
                imported.potmsgset = TranslationMessage.potmsgset AND
                imported.pofile = TranslationMessage.pofile AND
                imported.is_imported IS TRUE)''')
        query.append('TranslationMessage.potmsgset = POTMsgSet.id')
        query.append('POTMsgSet.sequence > 0')
        rosetta = TranslationMessage.select(
            ' AND '.join(query), clauseTables=['POTMsgSet']).count()

        unreviewed = self.getPOTMsgSetWithNewSuggestions().count()

        self.currentcount = current
        self.updatescount = updates
        self.rosettacount = rosetta
        self.unreviewed_count = unreviewed
        return self.getStatistics()

    def updateHeader(self, new_header):
        """See `IPOFile`."""
        if new_header is None:
            return

        # XXX sabdfl 2005-05-27 should we also differentiate between
        # washeaderfuzzy and isheaderfuzzy?
        self.topcomment = new_header.comment
        self.header = new_header.getRawContent()
        self.fuzzyheader = new_header.is_fuzzy

    def isTranslationRevisionDateOlder(self, header):
        """See `IPOFile`."""
        old_header = self.getHeader()

        # Get the old and new PO-Revision-Date entries as datetime objects.
        old_date = old_header.translation_revision_date
        new_date = header.translation_revision_date
        if old_date is None or new_date is None:
            # If one of the headers has an unknown revision date, they cannot
            # be compared, so we consider the new one as the most recent.
            return False

        # Check whether the date is older.
        return old_date > new_date

    def getNextToImport(self):
        """See `IPOFile`."""
        flush_database_updates()
        return TranslationImportQueueEntry.selectFirstBy(
                pofile=self,
                status=RosettaImportStatus.APPROVED,
                orderBy='dateimported')

    def importFromQueue(self, logger=None):
        """See `IPOFile`."""
        librarian_client = getUtility(ILibrarianClient)

        entry_to_import = self.getNextToImport()

        if entry_to_import is None:
            # There is no new import waiting for being imported.
            return

        import_file = librarian_client.getFileByAlias(entry_to_import.content.id)

        # While importing a file, there are two kinds of errors:
        #
        # - Errors that prevent us to parse the file. That's a global error,
        #   is handled with exceptions and will not change any data other than
        #   the status of that file to note the fact that its import failed.
        #
        # - Errors in concrete messages included in the file to import. That's
        #   a more localised error that doesn't affect the whole file being
        #   imported. It allows us to accept other translations so we accept
        #   everything but the messages with errors. We handle it returning a
        #   list of faulty messages.
        import_rejected = False
        try:
            importer = getUtility(ITranslationImporter)
            errors = importer.importFile(entry_to_import, logger=logger)
        except NotExportedFromLaunchpad:
            # We got a file that was not exported from Rosetta as a non
            # published upload. We log it and select the email template.
            if logger:
                logger.warning(
                    'Error importing %s' % self.title, exc_info=1)
            template_mail = 'poimport-not-exported-from-rosetta.txt'
            import_rejected = True
        except (TranslationFormatSyntaxError,
                TranslationFormatInvalidInputError):
            # The import failed with a format error. We log it and select the
            # email template.
            if logger:
                logger.warning(
                    'Error importing %s' % self.title, exc_info=1)
            template_mail = 'poimport-syntax-error.txt'
            import_rejected = True
        except OutdatedTranslationError:
            # The attached file is older than the last imported one, we ignore
            # it. We also log this problem and select the email template.
            if logger:
                logger.warning('Got an old version for %s' % self.title)
            template_mail = 'poimport-got-old-version.txt'
            import_rejected = True

        flush_database_updates()

        # Prepare the mail notification.
        msgsets_imported = TranslationMessage.select(
            'was_obsolete_in_last_import IS FALSE AND pofile=%s' %
            (sqlvalues(self.id))).count()

        replacements = {
            'dateimport': entry_to_import.dateimported.strftime('%F %R%z'),
            'elapsedtime': entry_to_import.getElapsedTimeText(),
            'file_link': entry_to_import.content.http_url,
            'import_title': '%s translations for %s' % (
                self.language.displayname, self.potemplate.displayname),
            'importer': entry_to_import.importer.displayname,
            'language': self.language.displayname,
            'numberofmessages': msgsets_imported,
            'template': self.potemplate.displayname,
            }

        if import_rejected:
            # We got an error that prevented us to import any translation, we
            # need to notify the user.
            subject = 'Import problem - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)
        elif len(errors):
            # There were some errors with translations.
            errorsdetails = ''
            for error in errors:
                pofile = error['pofile']
                potmsgset = error['potmsgset']
                pomessage = error['pomessage']
                error_message = error['error-message']
                errorsdetails = '%s%d.  [msg ??]\n"%s":\n\n%s\n\n' % (
                    errorsdetails,
                    potmsgset.sequence,
                    error_message,
                    pomessage)

            replacements['numberoferrors'] = len(errors)
            replacements['errorsdetails'] = errorsdetails
            replacements['numberofcorrectmessages'] = (msgsets_imported -
                len(errors))

            template_mail = 'poimport-with-errors.txt'
            subject = 'Translation problems - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)
        else:
            # The import was successful.
            template_mail = 'poimport-confirmation.txt'
            subject = 'Translation import - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)

        # Send the email.
        template = helpers.get_email_template(template_mail)
        message = template % replacements

        fromaddress = config.rosetta.rosettaadmin.email

        toaddress = helpers.contactEmailAddresses(entry_to_import.importer)

        simple_sendmail(fromaddress,
            toaddress,
            subject,
            MailWrapper().format(message))

        if import_rejected:
            # There were no imports at all and the user needs to review that
            # file, we tag it as FAILED.
            entry_to_import.status = RosettaImportStatus.FAILED
            return

        # The import has been done, we mark it that way.
        entry_to_import.status = RosettaImportStatus.IMPORTED
        # And add karma to the importer if it's not imported automatically
        # (all automatic imports come from the rosetta expert user) and comes
        # from upstream.
        rosetta_expert = getUtility(ILaunchpadCelebrities).rosetta_expert
        if (entry_to_import.is_published and
            entry_to_import.importer.id != rosetta_expert.id):
            # The Rosetta Experts team should not get karma.
            entry_to_import.importer.assignKarma(
                'translationimportupstream',
                product=self.potemplate.product,
                distribution=self.potemplate.distribution,
                sourcepackagename=self.potemplate.sourcepackagename)

        # Now we update the statistics after this new import
        self.updateStatistics()

    def updateExportCache(self, contents):
        """See `IPOFile`."""
        alias_set = getUtility(ILibraryFileAliasSet)

        if self.variant:
            filename = '%s@%s.po' % (
                self.language.code, self.variant.encode('UTF-8'))
        else:
            filename = '%s.po' % (self.language.code)

        size = len(contents)
        file = StringIO.StringIO(contents)


        # XXX CarlosPerelloMarin 2006-02-27: Added the debugID argument to
        # help us to debug bug #1887 on production. This will let us track
        # this librarian import so we can discover why sometimes, the fetch
        # of it fails.
        self.exportfile = alias_set.create(
            filename, size, file, 'application/x-po',
            debugID='pofile-id-%d' % self.id)

        # Note that UTC_NOW is resolved to the time at the beginning of the
        # transaction. This is significant because translations could be added
        # to the database while the export transaction is in progress, and the
        # export would not include those translations. However, we want to be
        # able to compare the export time to other datetime object within the
        # same transaction -- e.g. in is_cached_export_valid. This is
        # why we call .sync() -- it turns the UTC_NOW reference into an
        # equivalent datetime object.
        self.exporttime = UTC_NOW
        self.sync()

    def fetchExportCache(self):
        """Return the cached export file, if it exists, or None otherwise."""

        if self.exportfile is None:
            return None
        else:
            alias_set = getUtility(ILibraryFileAliasSet)
            return alias_set[self.exportfile.id].read()

    def uncachedExport(self, ignore_obsolete=False, force_utf8=False):
        """See `IPOFile`."""
        # Get the exporter for this translation.
        translation_exporter = getUtility(ITranslationExporter)
        translation_format_exporter = (
            translation_exporter.getExporterProducingTargetFileFormat(
                self.potemplate.source_file_format))

        translation_file = ITranslationFileData(self)
        if (self.lasttranslator is not None):
            if self.lasttranslator.preferredemail is None:
                # We are supposed to have always a valid email address, but
                # with removed accounts that's not true anymore so we just set
                # it to 'Unknown' to note we don't know it.
                email = 'Unknown'
            else:
                email = self.lasttranslator.preferredemail.email
            displayname = self.lasttranslator.displayname
            translation_file.header.setLastTranslator(email, name=displayname)

        # Get the export file.
        exported_file = translation_format_exporter.exportTranslationFiles(
            [translation_file], ignore_obsolete, force_utf8)

        try:
            file_content = exported_file.read()
        finally:
            exported_file.close()

        return file_content

    def export(self, ignore_obsolete=False):
        """See `IPOFile`."""
        if self.is_cached_export_valid and not ignore_obsolete:
            # Only use the cache if the request includes obsolete messages,
            # without them, we always do a full export.
            try:
                return self.fetchExportCache()
            except LookupError:
                # XXX: Carlos Perello Marin 2006-02-24: LookupError is a
                # workaround for bug #1887. Something produces LookupError
                # exception and we don't know why. This will allow us to
                # provide an export in those cases.
                logging.error(
                    "Error fetching a cached file from librarian", exc_info=1)
            except URLError:
                # There is a problem getting a cached export from Librarian.
                # Log it and do a full export.
                logging.warning(
                    "Error fetching a cached file from librarian", exc_info=1)

        contents = self.uncachedExport()

        if len(contents) == 0:
            # The export is empty, this is completely broken.
            raise ZeroLengthPOExportError, "Exporting %s" % self.title

        if not ignore_obsolete:
            # Update the cache if the request includes obsolete messages.
            try:
                self.updateExportCache(contents)
            except UploadFailed:
                # For some reason, we were not able to upload the exported
                # file in librarian, that's fine. It only means that next
                # time, we will do a full export again.
                logging.warning(
                    "Error uploading a cached file into librarian", exc_info=1)

        return contents

    def invalidateCache(self):
        """See `IPOFile`."""
        self.exportfile = None


class DummyPOFile(POFileMixIn):
    """Represents a POFile where we do not yet actually HAVE a POFile for
    that language for this template.
    """
    implements(IPOFile)

    def __init__(self, potemplate, language, variant=None, owner=None):
        self.id = None
        self.potemplate = potemplate
        self.language = language
        self.variant = variant
        self.description = None
        self.topcomment = None
        self.header = None
        self.fuzzyheader = False
        self.lasttranslator = None
        UTC = pytz.timezone('UTC')
        self.date_changed  = datetime.datetime.now(UTC)
        self.license = None
        self.lastparsed = None
        self.owner = getUtility(ILaunchpadCelebrities).rosetta_expert

        # The default POFile owner is the Rosetta Experts team unless the
        # given owner has rights to write into that file.
        if self.canEditTranslations(owner):
            self.owner = owner

        self.path = u'unknown'
        self.exportfile = None
        self.datecreated = datetime.datetime.now(UTC)
        self.last_touched_pomsgset = None
        self.contributors = []
        self.from_sourcepackagename = None
        self.translation_messages = None

    def __getitem__(self, msgid_text):
        translation_message = self.getCurrentTranslationMessage(
            msgid_text, ignore_obsolete=True)
        if translation_message is None:
            raise NotFoundError(msgid_text)
        else:
            return translation_message

    def __iter__(self):
        """See `IPOFile`."""
        return iter(self.currentMessageSets())

    def messageCount(self):
        return self.potemplate.messageCount()

    @property
    def title(self):
        """See `IPOFile`."""
        title = '%s translation of %s' % (
            self.language.displayname, self.potemplate.displayname)
        return title

    @property
    def translators(self):
        tgroups = self.potemplate.translationgroups
        ret = []
        for group in tgroups:
            translator = group.query_translator(self.language)
            if translator is not None:
                ret.append(translator)
        return ret

    @property
    def translationpermission(self):
        """See `IPOFile`."""
        return self.potemplate.translationpermission

    @property
    def is_cached_export_valid(self):
        """See `IPOFile`."""
        return False

    def canEditTranslations(self, person):
        """See `IPOFile`."""
        return _can_edit_translations(self, person)

    def canAddSuggestions(self, person):
        """See `IPOFile`."""
        return _can_add_suggestions(self, person)

    def getCurrentTranslationMessageFromPOTMsgSet(self, potmsgset,
                                                  ignore_obsolete=False):
        """See `IPOFile`."""
        if potmsgset is None or (ignore_obsolete and potmsgset.sequence <= 0):
            # There is no IPOTMsgSet for this id.
            return None

        return DummyTranslationMessage(self, potmsgset)

    def emptySelectResults(self):
        return POFile.select("1=2")

    def getPOMsgSetsNotInTemplate(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetTranslated(self, slice=None):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetFuzzy(self, slice=None):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetUntranslated(self, slice=None):
        """See `IPOFile`."""
        return self.potemplate.getPOTMsgSets(slice)

    def getPOTMsgSetWithNewSuggestions(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetChangedInLaunchpad(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetWithErrors(self, slice=None):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def hasMessageID(self, msgid):
        """See `IPOFile`."""
        raise NotImplementedError

    def currentCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def rosettaCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def updatesCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def unreviewedCount(self, language=None):
        """See `IPOFile`."""
        return 0

    def nonUpdatesCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def translatedCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def untranslatedCount(self, language=None):
        """See `IRosettaStats`."""
        return self.messageCount()

    @property
    def fuzzy_count(self):
        """See `IPOFile`."""
        return 0

    def currentPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def rosettaPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def updatesPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def nonUpdatesPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def translatedPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def untranslatedPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 100.0

    def updateExportCache(self, contents):
        """See `IPOFile`."""
        raise NotImplementedError

    def export(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def uncachedExport(self, ignore_obsolete=False, force_utf8=False):
        """See `IPOFile`."""
        raise NotImplementedError

    def invalidateCache(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def createMessageSetFromMessageSet(self, potmsgset):
        """See `IPOFile`."""
        raise NotImplementedError

    def translated(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def untranslated(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def getStatistics(self):
        """See `IPOFile`."""
        return (0, 0, 0, )

    def updateStatistics(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def updateHeader(self, new_header):
        """See `IPOFile`."""
        raise NotImplementedError

    def isTranslationRevisionDateOlder(self, header):
        """See `IPOFile`."""
        raise NotImplementedError

    def getNextToImport(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def importFromQueue(self, logger=None):
        """See `IPOFile`."""
        raise NotImplementedError

    def prepareTranslationCredits(self, potmsgset):
        """See `IPOFile`."""
        return None

class POFileSet:
    implements(IPOFileSet)

    def getPOFilesPendingImport(self):
        """See `IPOFileSet`."""
        results = POFile.selectBy(
            rawimportstatus=RosettaImportStatus.PENDING,
            orderBy='-daterawimport')

        for pofile in results:
            yield pofile

    def getDummy(self, potemplate, language):
        return DummyPOFile(potemplate, language)

    def getPOFileByPathAndOrigin(self, path, productseries=None,
        distroseries=None, sourcepackagename=None):
        """See `IPOFileSet`."""
        assert productseries is not None or distroseries is not None, (
            'Either productseries or sourcepackagename arguments must be'
            ' not None.')
        assert productseries is None or distroseries is None, (
            'productseries and sourcepackagename/distroseries cannot be used'
            ' at the same time.')
        assert ((sourcepackagename is None and distroseries is None) or
                (sourcepackagename is not None and distroseries is not None)
                ), ('sourcepackagename and distroseries must be None or not'
                   ' None at the same time.')

        if productseries is not None:
            return POFile.selectOne('''
                POFile.path = %s AND
                POFile.potemplate = POTemplate.id AND
                POTemplate.productseries = %s''' % sqlvalues(
                    path, productseries.id),
                clauseTables=['POTemplate'])
        else:
            # The POFile belongs to a distribution and it could come from
            # another package that its POTemplate is linked to, so we first
            # check to find it at IPOFile.from_sourcepackagename
            pofile = POFile.selectOne('''
                POFile.path = %s AND
                POFile.potemplate = POTemplate.id AND
                POTemplate.distrorelease = %s AND
                POFile.from_sourcepackagename = %s''' % sqlvalues(
                    path, distroseries.id, sourcepackagename.id),
                clauseTables=['POTemplate'])

            if pofile is not None:
                return pofile

            # There is no pofile in that 'path' and
            # 'IPOFile.from_sourcepackagename' so we do a search using the
            # usual sourcepackagename.
            return POFile.selectOne('''
                POFile.path = %s AND
                POFile.potemplate = POTemplate.id AND
                POTemplate.distrorelease = %s AND
                POTemplate.sourcepackagename = %s''' % sqlvalues(
                    path, distroseries.id, sourcepackagename.id),
                clauseTables=['POTemplate'])

    def getBatch(self, starting_id, batch_size):
        """See `IPOFileSet`."""
        return POFile.select(
            "id >= %s" % quote(starting_id), orderBy="id", limit=batch_size)


class POFileTranslator(SQLBase):
    """See `IPOFileTranslator`."""

    implements(IPOFileTranslator)
    pofile = ForeignKey(foreignKey='POFile', dbName='pofile', notNull=True)
    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)
    latest_message = ForeignKey(foreignKey='TranslationMessage',
        dbName='latest_message', notNull=True)
    date_last_touched = UtcDateTimeCol(dbName='date_last_touched',
        notNull=False, default=None)


class POFileToTranslationFileDataAdapter:
    """Adapter from `IPOFile` to `ITranslationFileData`."""
    implements(ITranslationFileData)

    def __init__(self, pofile):
        self._pofile = pofile
        self.messages = self._getMessages()

    @cachedproperty
    def path(self):
        """See `ITranslationFileData`."""
        return self._pofile.path

    @cachedproperty
    def translation_domain(self):
        """See `ITranslationFileData`."""
        return self._pofile.potemplate.translation_domain

    @property
    def is_template(self):
        """See `ITranslationFileData`."""
        return False

    @cachedproperty
    def language_code(self):
        """See `ITranslationFile`."""
        if self.is_template:
            return None

        return self._pofile.language.code

    @cachedproperty
    def header(self):
        """See `ITranslationFileData`."""
        template_header = self._pofile.potemplate.getHeader()
        translation_header = self._pofile.getHeader()
        # Update default fields based on its values in the template header.
        translation_header.updateFromTemplateHeader(template_header)
        date_reviewed = None
        translation_header.translation_revision_date = (
            self._pofile.date_changed)

        translation_header.comment = self._pofile.topcomment

        if self._pofile.potemplate.hasPluralMessage():
            number_plural_forms = None
            plural_form_expression = None
            if self._pofile.language.pluralforms is not None:
                # We have pluralforms information for this language so we
                # update the header to be sure that we use the language
                # information from our database instead of use the one
                # that we got from upstream. We check this information so
                # we are sure it's valid.
                number_plural_forms = self._pofile.language.pluralforms
                plural_form_expression = (
                    self._pofile.language.pluralexpression)

            translation_header.number_plural_forms = number_plural_forms
            translation_header.plural_form_expression = plural_form_expression

        # We need to tag every export from Launchpad so we know whether a
        # later upload should change every translation in our database or
        # that we got a change between the export and the upload with
        # modifications.
        UTC = pytz.timezone('UTC')
        datetime_now = datetime.datetime.now(UTC)
        translation_header.launchpad_export_date = datetime_now

        return translation_header

    def _getMessages(self):
        """Return a list of `ITranslationMessageData` for the `IPOFile`
        adapted."""
        pofile = self._pofile
        # Get all rows related to this file. We do this to speed the export
        # process so we have a single DB query to fetch all needed
        # information.
        rows = getUtility(IVPOExportSet).get_pofile_rows(pofile)

        messages = []

        for row in rows:
            assert row.pofile == pofile, 'Got a row for a different IPOFile.'

            # Skip messages which are neither in the PO template nor in the PO
            # file. (Messages which are in the PO template but not in the PO
            # file are untranslated, and messages which are not in the PO
            # template but in the PO file are obsolete.)
            if row.sequence == 0 and not row.is_imported:
                continue

            # Create new message set
            msgset = TranslationMessageData()
            msgset.is_obsolete = (row.sequence == 0)
            msgset.msgid_singular = row.msgid_singular
            msgset.msgid_plural = row.msgid_plural

            forms = [
                (0, row.translation0), (1, row.translation1),
                (2, row.translation2), (3, row.translation3)]
            max_forms = pofile.language.pluralforms
            for (pluralform, translation) in forms[:max_forms]:
                if translation is not None:
                    msgset.addTranslation(pluralform, translation)

            msgset.context = row.context
            msgset.comment = row.comment
            msgset.source_comment = row.source_comment
            msgset.file_references = row.file_references

            if row.flags_comment:
                msgset.flags = set([
                    flag.strip()
                    for flag in row.flags_comment.split(',')
                    if flag
                    ])

            if row.is_fuzzy:
                msgset.flags.add('fuzzy')

            messages.append(msgset)

        return messages
