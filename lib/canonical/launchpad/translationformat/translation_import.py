# Copyright 2005-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TranslationImporter',
    'importers',
    'is_identical_translation',
    ]

import gettextpo
import datetime
import os
import pytz
from zope.component import getUtility
from zope.interface import implements

from operator import attrgetter

from canonical.database.sqlbase import cursor, quote

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad.interfaces import (
    IPersonSet, ITranslationExporter, ITranslationImporter,
    NotExportedFromLaunchpad, OutdatedTranslationError,
    PersonCreationRationale, RosettaImportStatus, TranslationConflict,
    TranslationConstants, TranslationFileFormat)
from canonical.launchpad.translationformat.kde_po_importer import (
    KdePOImporter)
from canonical.launchpad.translationformat.gettext_po_importer import (
    GettextPOImporter)
from canonical.launchpad.translationformat.mozilla_xpi_importer import (
    MozillaXpiImporter)
from canonical.launchpad.translationformat.translation_common_format import (
    TranslationMessageData)

from canonical.launchpad.webapp import canonical_url


importers = {
    TranslationFileFormat.KDEPO: KdePOImporter(),
    TranslationFileFormat.PO: GettextPOImporter(),
    TranslationFileFormat.XPI: MozillaXpiImporter(),
    }


def is_identical_translation(existing_msg, new_msg):
    """Is a new translation substantially the same as the existing one?

    Compares fuzzy flags, msgid and msgid_plural, and all translations.

    :param existing_msg: a `TranslationMessageData` representing a translation
        message currently kept in the database.
    :param new_msg: an alternative `TranslationMessageData` translating the
        same original message.
    :return: True if the new message is effectively identical to the
        existing one, or False if replacing existing_msg with new_msg
        would make a semantic difference.
    """
    assert new_msg.msgid_singular == existing_msg.msgid_singular, (
        "Comparing translations for different messages.")

    if ((existing_msg.msgid_plural != new_msg.msgid_plural) or
        (existing_msg.fuzzy != ('fuzzy' in new_msg.flags))):
        return False
    if len(new_msg.translations) < len(existing_msg.translations):
        return False
    length_overlap = min(
        len(existing_msg.translations), len(new_msg.translations))
    for pluralform_index in xrange(length_overlap):
        # Plural forms that both messages have.  Translations for each
        # must match.
        existing_text = existing_msg.translations[pluralform_index]
        new_text = new_msg.translations[pluralform_index]
        if existing_text != new_text:
            return False
    for pluralform_index in xrange(length_overlap, len(new_msg.translations)):
        # Plural forms that exist in new_translations but not in
        # existing_translations.  That's okay, as long as all of them are
        # None.
        if new_msg.translations[pluralform_index] is not None:
            return False
    return True


class ExistingPOFileInDatabase:
    """All existing translations for a PO file.

    Fetches all information needed to compare messages to be imported in one
    go. Used to speed up PO file import."""

    def __init__(self, pofile, is_imported=False):
        self.pofile = pofile
        self.is_imported = is_imported

        # Dict indexed by (msgid, context) containing current
        # TranslationMessageData: doing this for the speed.
        self.messages = {}
        # Messages which have been seen in the file: messages which exist
        # in the database, but not in the import, will be expired.
        self.seen = set()

        # Contains published but inactive translations.
        self.imported = {}

        # Pre-fill self.messages and self.imported with data.
        self._fetchDBRows()


    def _fetchDBRows(self):
        msgstr_joins = [
            "LEFT OUTER JOIN POTranslation pt%d "
            "ON pt%d.id = TranslationMessage.msgstr%d" % (form, form, form)
            for form in xrange(TranslationConstants.MAX_PLURAL_FORMS)]

        translations = [
            "pt%d.translation AS translation%d" % (form, form)
            for form in xrange(TranslationConstants.MAX_PLURAL_FORMS)]

        sql = '''
        SELECT
            POMsgId.msgid AS msgid,
            POMsgID_Plural.msgid AS msgid_plural,
            context,
            date_reviewed,
            is_fuzzy,
            is_current,
            is_imported,
            was_fuzzy_in_last_import,
            %s
          FROM TranslationMessage
            JOIN POFile ON
              TranslationMessage.pofile=POFile.id AND POFile.id=%s
            JOIN POTMsgSet ON
              POTMsgSet.id=TranslationMessage.potmsgset
            %s
            JOIN POMsgID ON
              POMsgID.id=POTMsgSet.msgid_singular
            LEFT OUTER JOIN POMsgID AS POMsgID_Plural ON
              POMsgID_Plural.id=POTMsgSet.msgid_plural
          WHERE
                is_current or is_imported
          ''' % (','.join(translations), quote(self.pofile),
                 '\n'.join(msgstr_joins))
        cur = cursor()
        cur.execute(sql)
        rows = cur.fetchall()

        assert TranslationConstants.MAX_PLURAL_FORMS == 6, (
            "Change this code to support %d plural forms"
            % TranslationConstants.MAX_PLURAL_FORMS)
        for (msgid, msgid_plural, context, date, is_fuzzy, is_current,
             is_imported, was_fuzzy_in_last_import,
             msgstr0, msgstr1, msgstr2, msgstr3, msgstr4,
             msgstr5) in rows:

            if not is_current and not is_imported:
                # We don't care about non-current and non-imported messages
                # yet.  To be part of super-fast-imports-phase2.
                continue

            update_caches = []
            if is_current:
                update_caches.append(self.messages)
            if is_imported:
                update_caches.append(self.imported)
                is_fuzzy = was_fuzzy_in_last_import

            for look_at in update_caches:
                if (msgid, msgid_plural, context) in look_at:
                    message = look_at[(msgid, msgid_plural, context)]
                else:
                    message = TranslationMessageData()
                    look_at[(msgid, msgid_plural, context)] = message

                    message.context = context
                    message.msgid_singular = msgid
                    message.msgid_plural = msgid_plural

                assert TranslationConstants.MAX_PLURAL_FORMS == 6, (
                    "Change this code to support %d plural forms"
                    % TranslationConstants.MAX_PLURAL_FORMS)
                if msgstr0 is not None:
                    message.addTranslation(0, msgstr0)
                if msgstr1 is not None:
                    message.addTranslation(1, msgstr1)
                if msgstr2 is not None:
                    message.addTranslation(2, msgstr2)
                if msgstr3 is not None:
                    message.addTranslation(3, msgstr3)
                if msgstr4 is not None:
                    message.addTranslation(4, msgstr4)
                if msgstr5 is not None:
                    message.addTranslation(5, msgstr5)

                message.fuzzy = is_fuzzy

    def markMessageAsSeen(self, message):
        """Marks a message as seen in the import, to avoid expiring it."""
        self.seen.add((message.msgid_singular, message.msgid_plural,
                       message.context))

    def getUnseenMessages(self):
        """Return a set of messages present in the database but not seen
        in the file being imported.
        """
        unseen = set()
        for (singular, plural, context) in self.messages:
            if (singular, plural, context) not in self.seen:
                unseen.add((singular, plural, context))
        for (singular, plural, context) in self.imported:
            if ((singular, plural, context) not in self.messages and
                (singular, plural, context) not in self.seen):
                unseen.add((singular, plural, context))
        return unseen

    def isAlreadyTranslatedTheSame(self, message):
        """Check whether this message is already translated in exactly
        the same way.
        """
        (msgid, plural, context) = (message.msgid_singular,
                                    message.msgid_plural,
                                    message.context)
        if (msgid, plural, context) in self.messages:
            msg_in_db = self.messages[(msgid, plural, context)]
            return is_identical_translation(msg_in_db, message)
        else:
            return False

    def isAlreadyImportedTheSame(self, message):
        """Check whether this translation is already present in DB as
        'is_imported' translation, and thus needs no changing if we are
        submitting an imported update.
        """
        (msgid, plural, context) = (message.msgid_singular,
                                    message.msgid_plural,
                                    message.context)
        if ((msgid, plural, context) in self.imported) and self.is_imported:
            msg_in_db = self.imported[(msgid, plural, context)]
            return is_identical_translation(msg_in_db, message)
        else:
            return False

class TranslationImporter:
    """Handle translation resources imports."""

    implements(ITranslationImporter)

    @cachedproperty
    def supported_file_extensions(self):
        """See `ITranslationImporter`."""
        file_extensions = []

        for importer in importers.itervalues():
            file_extensions.extend(importer.file_extensions)

        return sorted(set(file_extensions))

    @cachedproperty
    def template_suffixes(self):
        """See `ITranslationImporter`."""
        # Several formats (particularly the various gettext variants) can have
        # the same template suffix.
        unique_suffixes = set(
            importer.template_suffix for importer in importers.values())
        return sorted(unique_suffixes)

    def isTemplateName(self, path):
        """See `ITranslationImporter`."""
        for importer in importers.itervalues():
            if path.endswith(importer.template_suffix):
                return True
        return False

    def isTranslationName(self, path):
        """See `ITranslationImporter`."""
        base_name, suffix = os.path.splitext(path)
        if suffix not in self.supported_file_extensions:
            return False
        for importer_suffix in self.template_suffixes:
            if path.endswith(importer_suffix):
                return False
        return True

    def getTranslationFileFormat(self, file_extension, file_contents):
        """See `ITranslationImporter`."""
        all_importers = importers.values()
        all_importers.sort(key=attrgetter('priority'), reverse=True)
        for importer in all_importers:
            if file_extension in importer.file_extensions:
                return importer.getFormat(file_contents)

        return None

    def getTranslationFormatImporter(self, file_format):
        """See `ITranslationImporter`."""
        return importers.get(file_format, None)

    def importFile(self, translation_import_queue_entry, logger=None):
        """See ITranslationImporter."""
        assert translation_import_queue_entry is not None, (
            "The translation import queue entry cannot be None.")
        assert (translation_import_queue_entry.status ==
                RosettaImportStatus.APPROVED), (
                "The entry is not approved!.")
        assert (translation_import_queue_entry.potemplate is not None or
                translation_import_queue_entry.pofile is not None), (
                "The entry has not any import target.")

        # Get the importer needed to import a file of this format.
        importer = self.getTranslationFormatImporter(
            translation_import_queue_entry.format)
        # Check that we really got an importer.
        assert importer is not None, (
            'There is no importer available for %s files' % (
                translation_import_queue_entry.format.name))

        # Select the import file type.
        if translation_import_queue_entry.pofile is None:
            # Importing a translation template (POT file).
            import_file = PotFileImporter(
                translation_import_queue_entry, importer, logger )
        else:
            # Importing a translation (PO file).
            import_file = PoFileImporter(
                translation_import_queue_entry, importer, logger )
                
        # Do the import and return the errors.
        return import_file.doImport()
               
class FileImporter(object):
    """
    Base class for importing translations (PO) or translation templates (POT).
    
    This class is meant to be subclassed for the specialised tasks of
    importing translations or translation templates respectively. It contains
    all code common to both tasks. Provides method hooks for the derived
    classes to implement but does not provide default implementation for these
    hooks. It can therefore not be instantiated directly.
    
    The hooks that must be implemented are:
    markAndCheck( message )
    checkPlurals( message, potmsgset)
    setUpMsgset( message, potmsgset, flags_comment )
    """
    
    def __init__( self, translation_import_queue_entry, importer, logger ):
        """
        Base constructor to set up common attributes and parse the imported
        file into a member variable (self.translation_file).
        """
        self.translation_import_queue_entry = translation_import_queue_entry
        self.importer = importer
        self.logger = logger

        # These two must be set correctly by the derived classes.
        self.pofile = None
        self.potemplate = None
        
        # Get the exporter to display a message in error messages.
        self.format_exporter = (
            getUtility(
                ITranslationExporter).getExporterProducingTargetFileFormat(
                    translation_import_queue_entry.format) )

        # Parse the file using the importer.
        self.translation_file = importer.parse(
            translation_import_queue_entry)

        self.is_editor = False
        self.last_translator = None
        self.lock_timestamp = None
        self.pofile_in_db = None
        self.count = 0
        self.errors = []

    def doImport(self):
        """
        Import a parsed file into the database.
        
        Loops through all message entries in the parsed file and performs
        various checks on them, calling the hook message along the way.
        
        :return: The errors encountered during the import.
        """
        # Messages are counted to maintain the original sequence.
        self.count = 0
        # Collect errors here.
        self.errors = []
        
        for message in self.translation_file.messages:
            if not message.msgid_singular:
                # The message has no msgid, we ignore it and jump to next
                # message.
                continue

            # Run a hook method.
            if not self.markAndCheck( message ):
                continue

            # Get the msgid OR create the IPOTMsgSet for it,
            # if it's the first time we see this msgid.
            potmsgset = (
                self.potemplate.getPOTMsgSetByMsgIDText(
                    message.msgid_singular, plural_text=message.msgid_plural,
                    context=message.context) )
            if potmsgset is None:
                potmsgset = (
                    self.potemplate.createMessageSetFromText(
                        message.msgid_singular, message.msgid_plural,
                        context=message.context) )

            # Run a hook method.
            if not self.checkPlurals(message, potmsgset):
                continue

            self.count += 1
            flags_comment, fuzzy = (
                self.createFlagsCommentAndRemoveFuzzy( message ) )
            
            # Run a hook method.
            self.setUpMsgset( message, potmsgset, flags_comment )

            # Store translations.
            if self.pofile is None:
                # It's neither an IPOFile nor an IPOTemplate that needs to
                # store English strings in an IPOFile.
                continue

            if not message.translations:
                # We don't have anything to import.
                continue

            try:
                # Do the actual import.
                translation_message = potmsgset.updateTranslation(
                    self.pofile, self.last_translator,
                    message.translations,
                    fuzzy, self.translation_import_queue_entry.is_published,
                    self.lock_timestamp,
                    force_edition_rights=self.is_editor)

            except TranslationConflict:
                self.addConflictError( message, potmsgset )
                if self.logger is not None:
                    self.logger.info(
                        "Conflicting updates on message %d." % potmsgset.id)
                continue
            except gettextpo.error, e:
                # We got an error, so we submit the translation again but
                # this time asking to store it as a translation with
                # errors.
                translation_message = potmsgset.updateTranslation(
                    self.pofile, self.last_translator,
                    message.translations,
                    fuzzy, self.translation_import_queue_entry.is_published,
                    self.lock_timestamp, ignore_errors=True,
                    force_edition_rights=self.is_editor)

                # Add the pomsgset to the list of pomsgsets with errors.
                self.addUpdateError( message, potmsgset, unicode(e) )

            # Update translation_message's comments and flags.
            if translation_message is not None:
                translation_message.flags_comment = flags_comment
                translation_message.comment = message.comment
                if self.translation_import_queue_entry.is_published:
                    translation_message.was_obsolete_in_last_import = (
                        message.is_obsolete)
                    translation_message.was_fuzzy_in_last_import = fuzzy

        # Run the clean up hoook.
        self.cleanUp()

        return self.errors

    def createFlagsCommentAndRemoveFuzzy( self, message ):
        """
        Build flags comment and remove fuzzy from message flags,
        saving the fuzzy state.
        
        :param message: The message that has the flags.
        :return: A tuple of the flags comment and the fuzzy flag.
        """
        flags_comment = u", " + u", ".join(message.flags)
        fuzzy = 'fuzzy' in message.flags
        if fuzzy:
            message.flags.remove('fuzzy')

        return (flags_comment, fuzzy)

    def addConflictError( self, message, potmsgset ):
        """
        Add an error if there was an edit conflict.

        This has been put in a method enhance clarity by removing the long
        error text from the calling method.
        
        :param message: The current message from the translation file.
        :param potmsgset: The current messageset for this message id.
        """
        self.errors.append( {
            'potmsgset': potmsgset,
            'pofile': self.pofile,
            'pomessage': self.format_exporter.exportTranslationMessageData(
                message),
            'error-message': (
                "This message was updated by someone else after you"
                " got the translation file. This translation is now"
                " stored as a suggestion, if you want to set it as"
                " the used one, go to %s/+translate and approve"
                " it." % canonical_url(self.pofile))
        } )

    def addUpdateError( self, message, potmsgset, errormsg ):
        """
        Add an error returned by updateTranslation.

        This has been put in a method enhance clarity by removing the long
        error text from the calling method.
        
        :param message: The current message from the translation file.
        :param potmsgset: The current messageset for this message id.
        :param errormsg: The errormessage returned by updateTranslation.
        """
        self.errors.append( {
            'potmsgset': potmsgset,
            'pofile': self.pofile,
            'pomessage': self.format_exporter.exportTranslationMessageData(
                message),
            'error-message': errormsg
        } )

        
class PotFileImporter( FileImporter ):
    """
    Import a translation template file.
    
    Implements the hook methods for FileImporter.doImport().
    """
    
    def __init__( self, translation_import_queue_entry, importer, logger ):
        """
        Construct an Importer for a translation template.
        """
        assert( translation_import_queue_entry.pofile is None,
            "Pofile must be None when importing a template." )

        # Call base constructor
        super( PotFileImporter, self ).__init__(
             translation_import_queue_entry, importer, logger )
            
        self.pofile = None
        self.potemplate = translation_import_queue_entry.potemplate

        self.potemplate.source_file_format = (
            translation_import_queue_entry.format)
        self.potemplate.source_file = (
            translation_import_queue_entry.content)
        if self.importer.uses_source_string_msgids:
            # We use the special 'en' language as the way to store the
            # English strings to show instead of the msgids.
            self.pofile = self.potemplate.getPOFileByLang('en')
            if self.pofile is None:
                self.pofile = self.potemplate.newPOFile('en')
        
        # Expire old messages.
        self.potemplate.expireAllMessages()
        if self.translation_file.header is not None:
            # Update the header.
            self.potemplate.header = (
                self.translation_file.header.getRawContent())
        UTC = pytz.timezone('UTC')
        self.potemplate.date_last_updated = datetime.datetime.now(UTC)

        # By default translation template uploads are done only by
        # editors.
        self.is_editor = True
        self.last_translator = (
            translation_import_queue_entry.importer )

    def addPluralError( self, message, potmsgset ):
        """
        Add an error if the msgid for plural has been changed.

        This has been put in a method enhance clarity by removing the long
        error text from the calling method.
        
        :param message: The current message from the translation file.
        :param potmsgset: The current messageset for this message id.
        """
        # Add the pomsgset to the list of pomsgsets with errors.
        self.errors.append( {
            'potmsgset': potmsgset,
            'pofile': self.pofile,
            'pomessage':
                self.format_exporter.exportTranslationMessageData(
                    message),
            'error-message': (
                "The msgid_plural field has changed since the"
                " last time this file was generated, please"
                " report this error to %s" % (
                    config.rosettaadmin.email))
            } )

    def markAndCheck(self, message):
        """ Nothing to be done for POT files. """
        return True

    def checkPlurals(self, message, potmsgset):
        """ Nothing to be done for POT files. """
        return True

    def setUpMsgset( self, message, potmsgset, flags_comment ):
        """
        Setup the potmsgset structure for importing a message id for a
            template.
        
        :param message: The current message from the translation file.
        :param potmsgset: The current messageset for this message id.
        :param flags_comment: The flags_comment from message.flags, possibly
            adapted.
        """
        potmsgset.setSequence(potmsgset.potemplate, self.count)
        potmsgset.commenttext = message.comment
        potmsgset.sourcecomment = message.source_comment
        potmsgset.filereferences = message.file_references
        potmsgset.flagscomment = flags_comment

    def cleanUp( self ):
        """ Nothing to do for clean up. """

class PoFileImporter( FileImporter ):
    """
    Import a translation file.
    
    Implements the hook methods for FileImporter.doImport().
    """
    
    def __init__( self, translation_import_queue_entry, importer, logger ):
        """
        Construct an Importer for a translation template.
        """
        assert( translation_import_queue_entry.pofile is not None,
            "Pofile must not be None when importing a translation." )

        # Call base constructor
        super( PoFileImporter, self ).__init__(
             translation_import_queue_entry, importer, logger )
            
        self.pofile = translation_import_queue_entry.pofile
        self.potemplate = self.pofile.potemplate

        if self.translation_file.header is not None:
            # Check whether we are importing a new version.
            if self.pofile.isTranslationRevisionDateOlder(
                self.translation_file.header):
                # The new imported file is older than latest one imported,
                # we don't import it, just ignore it as it could be a
                # mistake and it would make us lose translations.
                raise OutdatedTranslationError(
                    'Previous imported file is newer than this one.')
            # Get the timestamp when this file was exported from
            # Launchpad. If it was not exported from Launchpad, it will be
            # None.
            self.lock_timestamp = (
                self.translation_file.header.launchpad_export_date )

        if (not self.translation_import_queue_entry.is_published and
            self.lock_timestamp is None):
            # We got a translation file from offline translation (not
            # published) and it misses the export time so we don't have a
            # way to figure whether someone changed the same translations
            # while the offline work was done.
            raise NotExportedFromLaunchpad

        # Update the header with the new one.
        self.pofile.updateHeader(self.translation_file.header)
        # Get last translator that touched this translation file.
        # We may not be able to guess it from the translation file, so
        # we take the importer as the last translator then.
        name, email = self.translation_file.header.getLastTranslator()
        self.last_translator = ( self._getPersonByEmail(email, name) )
        if self.last_translator is None:
            self.last_translator = (
                self.translation_import_queue_entry.importer )

        # Use the importer rights to make sure the imported
        # translations are actually accepted instead of being just
        # suggestions.
        self.is_editor = (
            self.pofile.canEditTranslations(
                self.translation_import_queue_entry.importer) )

        self.pofile_in_db = (
            ExistingPOFileInDatabase(
                self.pofile,
                is_imported=self.translation_import_queue_entry.is_published))

    def _getPersonByEmail(self, email, name=None):
        """
        Return the person for given email.

        If the person is unknown in Launchpad, the account will be created but
        it will not have a password and thus, will be disabled.

        :param email: text that contains the email address.
        :param name: name of the owner of the given email address.

        :return: A person object or None, if email is None.
        """
        if email is None:
            return None

        personset = getUtility(IPersonSet)
        person = personset.getByEmail(email)

        if person is None:
            # We create a new user without a password.
            comment = 'when importing the %s translation of %s' % (
                self.pofile.language.displayname, self.potemplate.displayname)

            person, dummy = personset.createPersonAndEmail(
                email, PersonCreationRationale.POFILEIMPORT,
                displayname=name, comment=comment)

        return person

    def markAndCheck(self, message):
        """
        Mark this message off as seen and then check if the translation
        is the same as what has already been imported into or translated
        in LP.
        
        :param translation_import_queue_entry: The queue entry that requested
            this import.
        :param message: the message to mark and check
        :return: True if the translation already exists
        """
        # Mark this message as seen in the import
        self.pofile_in_db.markMessageAsSeen(message)
        # Check for same imported or local translation
        if self.translation_import_queue_entry.is_published:
            same_translation = (
                self.pofile_in_db.isAlreadyImportedTheSame(
                    message) )
        else:
            same_translation = (
                self.pofile_in_db.isAlreadyTranslatedTheSame(
                    message))

        return not same_translation
        
    def checkPlurals(self, message, potmsgset):
        """
        Check this message for changes in the plural definition.
        A change is detected if msgid_plural for this plural form is different
        from the existing plural form (and msgid matches).
        Appends an error to the list if a change is detected.
        
        :param message: the message to check
        :param potmsgset: the msgset to check against
        :return: True if no error was found.
        """
        if (message.msgid_plural is not None and
            potmsgset.msgid_plural is not None and
            (message.msgid_plural != potmsgset.msgid_plural.msgid)):
            # The PO file wants to change the plural msgid from the PO
            # template, that's broken and not usual, so we raise an
            # exception to log the issue. It needs to be fixed
            # manually in the imported translation file.
            # XXX CarlosPerelloMarin 2007-04-23 bug=109393:
            # Gettext doesn't allow two plural messages with the
            # same msgid but different msgid_plural so I think is
            # safe enough to just go ahead and import this translation
            # here but setting the fuzzy flag.

            self.addPluralError( message, potmsgset )
            return False

        # Plural forms match, no error
        return True
        
    def setUpMsgset( self, message, potmsgset, flags_comment ):
        """
        Update the potmsgset structure with the new values from the PO file.
        
        :param message: The current message from the translation file.
        :param potmsgset: The current messageset for this message id.
        :param flags_comment: The flags_comment from message.flags,
            ignored here.
        """
        # The import is a translation file.
        if potmsgset.sequence == 0:
            # We are importing a message that does not exist in
            # latest translation template so we can update its values.
            potmsgset.sourcecomment = message.source_comment
            potmsgset.filereferences = message.file_references

    def cleanUp( self ):
        """ Mark messages that were not imported. """
        # Check if there is a PO file in the DB
        if self.pofile_in_db is not None:
            # Get relevant messages from dB
            unseen = self.pofile_in_db.getUnseenMessages()
            for unseen_message in unseen:
                # Get the message from the message set
                (msgid, plural, context) = unseen_message
                potmsgset = self.potemplate.getPOTMsgSetByMsgIDText(
                    msgid, plural_text=plural, context=context)
                translationmessage = potmsgset.getImportedTranslationMessage(
                    self.pofile.language)
                # Mark this message as not imported
                if translationmessage is not None:
                    translationmessage.is_imported = False

