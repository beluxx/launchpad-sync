# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`SQLObject` implementation of `IPOTemplate` interface."""

__all__ = [
    "get_pofiles_for",
    "POTemplate",
    "POTemplateSet",
    "POTemplateSubset",
    "POTemplateToTranslationFileDataAdapter",
    "TranslationTemplatesCollection",
]

import logging
import operator
import os
from datetime import datetime, timezone

from psycopg2.extensions import TransactionRollbackError
from storm.expr import SQL, And, Desc, Join, LeftJoin, Or
from storm.info import ClassAlias
from storm.properties import Bool, DateTime, Int, Unicode
from storm.references import Reference, ReferenceSet
from storm.store import Store
from zope.component import getAdapter, getUtility
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import ServiceUsage
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.person import validate_public_person
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.database.bulk import load_related
from lp.services.database.collection import Collection
from lp.services.database.constants import DEFAULT
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import IPrimaryStore, IStore
from lp.services.database.sqlbase import flush_database_updates
from lp.services.database.stormbase import StormBase
from lp.services.database.stormexpr import RegexpMatch
from lp.services.helpers import shortlist
from lp.services.mail.helpers import get_email_template
from lp.services.propertycache import cachedproperty
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.services.worlddata.model.language import Language
from lp.translations.enums import RosettaImportStatus
from lp.translations.interfaces.pofile import IPOFileSet
from lp.translations.interfaces.potemplate import (
    IPOTemplate,
    IPOTemplateSet,
    IPOTemplateSharingSubset,
    IPOTemplateSubset,
    LanguageNotFound,
)
from lp.translations.interfaces.side import TranslationSide
from lp.translations.interfaces.translationcommonformat import (
    ITranslationFileData,
)
from lp.translations.interfaces.translationexporter import ITranslationExporter
from lp.translations.interfaces.translationfileformat import (
    TranslationFileFormat,
)
from lp.translations.interfaces.translationimporter import (
    ITranslationImporter,
    TranslationFormatInvalidInputError,
    TranslationFormatSyntaxError,
)
from lp.translations.model.pofile import POFile
from lp.translations.model.pomsgid import POMsgID
from lp.translations.model.potmsgset import POTMsgSet
from lp.translations.model.translationimportqueue import collect_import_info
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
)
from lp.translations.model.vpotexport import VPOTExport
from lp.translations.utilities.rosettastats import RosettaStats
from lp.translations.utilities.sanitize import MixedNewlineMarkersError
from lp.translations.utilities.translation_common_format import (
    TranslationMessageData,
)

sharing_subset_cte = """
RECURSIVE location(product, distribution, sourcepackagename) AS (
    VALUES (?::integer, ?::integer, ?::integer)
  UNION
    SELECT
        ps_from_packaging.product, ds_from_packaging.distribution,
        packaging_from_ps.sourcepackagename
    FROM
        location
        -- Find a (Distribution, SPN) via a Packaging from a Product.
        LEFT JOIN (
            productseries AS ps_from_location
            JOIN packaging AS packaging_from_ps
                ON packaging_from_ps.productseries = ps_from_location.id
            JOIN distroseries AS ds_from_packaging
                ON ds_from_packaging.id = packaging_from_ps.distroseries
            ) ON ps_from_location.product = location.product
        -- Find a Product via a Packaging from a (Distribution, SPN).
        LEFT JOIN (
            distroseries AS ds_from_location
            JOIN packaging AS packaging_from_ds
                ON packaging_from_ds.distroseries = ds_from_location.id
            JOIN productseries AS ps_from_packaging
                ON ps_from_packaging.id = packaging_from_ds.productseries
            ) ON (
                ds_from_location.distribution = location.distribution
                AND packaging_from_ds.sourcepackagename =
                    location.sourcepackagename)
    WHERE
        -- All rows must have a target.
        (ps_from_packaging.product IS NOT NULL
         OR packaging_from_ps.distroseries IS NOT NULL))
"""


log = logging.getLogger(__name__)


standardPOFileTopComment = """ %(languagename)s translation for %(origin)s
 Copyright %(copyright)s %(year)s
 This file is distributed under the same license as the %(origin)s package.
 FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.

"""

standardTemplateHeader = (
    "Project-Id-Version: %(origin)s\n"
    "Report-Msgid-Bugs-To: FULL NAME <EMAIL@ADDRESS>\n"
    "POT-Creation-Date: %(templatedate)s\n"
    "PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
    "Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
    "Language-Team: %(languagename)s <%(languagecode)s@li.org>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
)


standardPOFileHeader = (
    standardTemplateHeader
    + "Plural-Forms: nplurals=%(nplurals)d; plural=%(pluralexpr)s\n"
)


def get_pofiles_for(potemplates, language):
    """Return list of `IPOFile`s for given templates in given language.

    :param potemplates: a list or sequence of `POTemplate`s.
    :param language: the language that the `IPOFile`s should be for.
    :return: a list of exactly one `IPOFile` for each `POTemplate`
        in `potemplates`.  They will be `POFile`s where available,
        and `PlaceholderPOFile`s where not.
    """
    potemplates = list(potemplates)
    if len(potemplates) == 0:
        return []

    template_ids = [template.id for template in potemplates]

    pofiles = Store.of(potemplates[0]).find(
        POFile,
        And(
            POFile.potemplate_id.is_in(template_ids),
            POFile.language == language,
        ),
    )

    mapping = {pofile.potemplate.id: pofile for pofile in pofiles}
    result = [mapping.get(id) for id in template_ids]
    for entry, pofile in enumerate(result):
        assert pofile == result[entry], "This enumerate confuses me."
        if pofile is None:
            result[entry] = potemplates[entry].getPlaceholderPOFile(
                language, check_for_existing=False
            )

    return result


@implementer(IPOTemplate)
class POTemplate(StormBase, RosettaStats):
    __storm_table__ = "POTemplate"

    id = Int(primary=True)
    productseries_id = Int(name="productseries", allow_none=True, default=None)
    productseries = Reference(productseries_id, "ProductSeries.id")
    priority = Int(name="priority", allow_none=False, default=DEFAULT)
    name = Unicode(name="name", allow_none=False)
    translation_domain = Unicode(name="translation_domain", allow_none=False)
    description = Unicode(name="description", allow_none=True, default=None)
    copyright = Unicode(name="copyright", allow_none=True, default=None)
    datecreated = DateTime(
        name="datecreated", default=DEFAULT, tzinfo=timezone.utc
    )
    path = Unicode(name="path", allow_none=False)
    source_file_id = Int(name="source_file", allow_none=True, default=None)
    source_file = Reference(source_file_id, "LibraryFileAlias.id")
    source_file_format = DBEnum(
        name="source_file_format",
        enum=TranslationFileFormat,
        default=TranslationFileFormat.PO,
        allow_none=False,
    )
    iscurrent = Bool(name="iscurrent", allow_none=False, default=True)
    messagecount = Int(name="messagecount", allow_none=False, default=0)
    owner_id = Int(
        name="owner", validator=validate_public_person, allow_none=False
    )
    owner = Reference(owner_id, "Person.id")
    sourcepackagename_id = Int(
        name="sourcepackagename", allow_none=True, default=None
    )
    sourcepackagename = Reference(sourcepackagename_id, "SourcePackageName.id")
    from_sourcepackagename_id = Int(
        name="from_sourcepackagename", allow_none=True, default=None
    )
    from_sourcepackagename = Reference(
        from_sourcepackagename_id, "SourcePackageName.id"
    )
    sourcepackageversion = Unicode(
        name="sourcepackageversion", allow_none=True, default=None
    )
    distroseries_id = Int(name="distroseries", allow_none=True, default=None)
    distroseries = Reference(distroseries_id, "DistroSeries.id")
    header = Unicode(name="header", allow_none=False)
    languagepack = Bool(name="languagepack", allow_none=False, default=False)
    date_last_updated = DateTime(
        name="date_last_updated", default=DEFAULT, tzinfo=timezone.utc
    )

    # joins
    pofiles = ReferenceSet("id", "POFile.potemplate_id")

    # In-memory cache: maps language_code to list of POFiles
    # translating this template to that language.
    _cached_pofiles_by_language = None

    _uses_english_msgids = None

    def __init__(
        self,
        name,
        translation_domain,
        path,
        owner,
        header,
        productseries=None,
        distroseries=None,
        sourcepackagename=None,
        languagepack=False,
    ):
        super().__init__()
        self.name = name
        self.translation_domain = translation_domain
        self.path = path
        self.owner = owner
        self.header = header
        self.productseries = productseries
        self.distroseries = distroseries
        self.sourcepackagename = sourcepackagename
        self.languagepack = languagepack

    @cachedproperty
    def _sharing_ids(self):
        """Return the IDs of all sharing templates including this one."""
        subset = getUtility(IPOTemplateSet).getSharingSubset(
            product=self.product,
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
        )
        # Convert  to a list for caching.
        result = list(subset.getSharingPOTemplateIDs(self.name))
        if len(result) == 0:
            # Always return at least the template itself.
            return [self.id]
        else:
            return result

    def __storm_invalidated__(self):
        super().__storm_invalidated__()
        self.clearPOFileCache()
        self._uses_english_msgids = None

    def clearPOFileCache(self):
        """See `IPOTemplate`."""
        self._cached_pofiles_by_language = None

    def _removeFromSuggestivePOTemplatesCache(self):
        """One level of indirection to make testing easier."""
        getUtility(IPOTemplateSet).removeFromSuggestivePOTemplatesCache(self)

    def setActive(self, active):
        """See `IPOTemplate`."""
        if not active and active != self.iscurrent:
            self._removeFromSuggestivePOTemplatesCache()
        self.iscurrent = active

    @property
    def uses_english_msgids(self):
        """See `IPOTemplate`."""
        if self._uses_english_msgids is not None:
            return self._uses_english_msgids

        translation_importer = getUtility(ITranslationImporter)
        format = translation_importer.getTranslationFormatImporter(
            self.source_file_format
        )
        self._uses_english_msgids = not format.uses_source_string_msgids
        return self._uses_english_msgids

    def __iter__(self):
        """See `IPOTemplate`."""
        yield from self.getPOTMsgSets()

    def __getitem__(self, key):
        """See `IPOTemplate`."""
        potmsgset = self.getPOTMsgSetByMsgIDText(key, only_current=True)
        if potmsgset is None:
            raise NotFoundError(key)
        else:
            return potmsgset

    def sharingKey(self):
        """See `IPOTemplate.`"""
        if self.productseries is not None:
            product_focus = (
                self.productseries
                == self.productseries.product.primary_translatable
            )
        else:
            product_focus = False
        if self.distroseries is not None:
            distro_focus = (
                self.distroseries
                == self.distroseries.distribution.translation_focus
            )
        else:
            distro_focus = False
        return self.iscurrent, product_focus, distro_focus, self.id

    @property
    def displayname(self):
        """See `IPOTemplate`."""
        if self.productseries:
            dn = "%s in %s %s" % (
                self.name,
                self.productseries.product.displayname,
                self.productseries.displayname,
            )
        if self.distroseries:
            dn = '%s in %s %s package "%s"' % (
                self.name,
                self.distroseries.distribution.displayname,
                self.distroseries.displayname,
                self.sourcepackagename.name,
            )
        return dn

    @property
    def title(self):
        """See `IPOTemplate`."""
        if self.productseries:
            title = 'Template "%s" in %s %s' % (
                self.name,
                self.productseries.product.displayname,
                self.productseries.displayname,
            )
        if self.distroseries:
            title = 'Template "%s" in %s %s package "%s"' % (
                self.name,
                self.distroseries.distribution.displayname,
                self.distroseries.displayname,
                self.sourcepackagename.name,
            )
        return title

    @property
    def distribution(self):
        """See `IPOTemplate`."""
        if self.distroseries is not None:
            return self.distroseries.distribution
        else:
            return None

    @property
    def product(self):
        """See `IPOTemplate`."""
        if self.productseries is not None:
            return self.productseries.product
        else:
            return None

    def getTranslationPolicy(self):
        """See `IPOTemplate`."""
        if self.productseries is not None:
            return self.productseries.product
        else:
            return self.distroseries.distribution

    @property
    def translationgroups(self):
        """See `IPOTemplate`."""
        return self.getTranslationPolicy().getTranslationGroups()

    @property
    def translationpermission(self):
        """See `IPOTemplate`."""
        return self.getTranslationPolicy().getEffectiveTranslationPermission()

    @property
    def relatives_by_source(self):
        """See `IPOTemplate`."""
        if self.productseries is not None:
            return (
                Store.of(self)
                .find(
                    POTemplate,
                    POTemplate.id != self.id,
                    POTemplate.productseries == self.productseries,
                    POTemplate.iscurrent,
                )
                .order_by(POTemplate.name)
            )
        elif (
            self.distroseries is not None
            and self.sourcepackagename is not None
        ):
            return (
                Store.of(self)
                .find(
                    POTemplate,
                    POTemplate.id != self.id,
                    POTemplate.distroseries == self.distroseries,
                    POTemplate.sourcepackagename == self.sourcepackagename,
                    POTemplate.iscurrent,
                )
                .order_by(POTemplate.name)
            )
        else:
            raise AssertionError("Unknown POTemplate source.")

    @property
    def language_count(self):
        return (
            IStore(Language)
            .find(
                Language,
                POFile.language == Language.id,
                POFile.currentcount + POFile.rosettacount > 0,
                POFile.potemplate_id == self.id,
            )
            .config(distinct=True)
            .count()
        )

    @cachedproperty
    def sourcepackage(self):
        """See `IPOTemplate`."""
        # Avoid circular imports
        from lp.registry.model.sourcepackage import SourcePackage

        if self.distroseries is None:
            return None
        return SourcePackage(
            distroseries=self.distroseries,
            sourcepackagename=self.sourcepackagename,
        )

    @property
    def translationtarget(self):
        """See `IPOTemplate`."""
        if self.productseries is not None:
            return self.productseries
        else:
            return self.sourcepackage

    def getHeader(self):
        """See `IPOTemplate`."""
        translation_importer = getUtility(ITranslationImporter)
        format_importer = translation_importer.getTranslationFormatImporter(
            self.source_file_format
        )
        header = format_importer.getHeaderFromString(self.header)
        header.has_plural_forms = self.hasPluralMessage()
        return header

    def _getPOTMsgSetSelectionClauses(self):
        """Return SQL clauses for finding POTMsgSets which belong
        to this POTemplate."""
        clauses = [
            TranslationTemplateItem.potemplate_id == self.id,
            TranslationTemplateItem.potmsgset_id == POTMsgSet.id,
        ]
        return clauses

    def getPOTMsgSetByMsgIDText(
        self, singular_text, plural_text=None, only_current=False, context=None
    ):
        """See `IPOTemplate`."""
        # Find a message ID with the given text.
        try:
            singular_msgid = POMsgID.getByMsgid(singular_text)
        except NotFoundError:
            return None

        # Find a message ID for the plural string.
        plural_msgid = None
        if plural_text is not None:
            try:
                plural_msgid = POMsgID.getByMsgid(plural_text)
            except NotFoundError:
                return None

        # Find a message set with the given message ID.
        clauses = self._getPOTMsgSetSelectionClauses()
        clauses.extend(
            [
                POTMsgSet.msgid_singular == singular_msgid,
                POTMsgSet.msgid_plural == plural_msgid,
                POTMsgSet.context == context,
            ]
        )
        if only_current:
            clauses.append(TranslationTemplateItem.sequence > 0)
        return Store.of(self).find(POTMsgSet, *clauses).one()

    def getPOTMsgSetBySequence(self, sequence):
        """See `IPOTemplate`."""
        assert sequence > 0, "%r is out of range"
        clauses = self._getPOTMsgSetSelectionClauses()
        clauses.append(TranslationTemplateItem.sequence == sequence)
        return Store.of(self).find(POTMsgSet, *clauses).one()

    def getPOTMsgSets(self, current=True, prefetch=True):
        """See `IPOTemplate`."""
        clauses = self._getPOTMsgSetSelectionClauses()
        if current:
            # Only count the number of POTMsgSet that are current.
            clauses.append(TranslationTemplateItem.sequence > 0)
        result = (
            Store.of(self)
            .find(POTMsgSet, *clauses)
            .order_by(TranslationTemplateItem.sequence)
        )

        if prefetch:

            def prefetch_msgids(rows):
                load_related(
                    POMsgID, rows, ["msgid_singular_id", "msgid_plural_id"]
                )

            return DecoratedResultSet(result, pre_iter_hook=prefetch_msgids)
        else:
            return result

    def getTranslationCredits(self):
        """See `IPOTemplate`."""
        # Find potential credits messages by the message ids.
        store = IStore(POTemplate)
        origin1 = Join(
            TranslationTemplateItem,
            TranslationTemplateItem.potmsgset == POTMsgSet.id,
        )
        origin2 = Join(POMsgID, POTMsgSet.msgid_singular == POMsgID.id)
        result = store.using(POTMsgSet, origin1, origin2).find(
            POTMsgSet,
            TranslationTemplateItem.potemplate == self,
            POMsgID.msgid.is_in(POTMsgSet.credits_message_ids),
        )
        # Filter these candidates because is_translation_credit checks for
        # more conditions than the special msgids.
        for potmsgset in result:
            if potmsgset.is_translation_credit:
                yield potmsgset

    def getPOTMsgSetsCount(self, current=True):
        """See `IPOTemplate`."""
        results = self.getPOTMsgSets(current, prefetch=False)
        return results.count()

    def getPOTMsgSetByID(self, id):
        """See `IPOTemplate`."""
        clauses = self._getPOTMsgSetSelectionClauses()
        clauses.append(POTMsgSet.id == id)
        return Store.of(self).find(POTMsgSet, *clauses).one()

    def languages(self):
        """See `IPOTemplate`."""
        return (
            Store.of(self)
            .find(
                Language,
                POFile.language_id == Language.id,
                Language.code != "en",
                POFile.potemplate_id == self.id,
            )
            .config(distinct=True)
        )

    def getPOFileByPath(self, path):
        """See `IPOTemplate`."""
        return IStore(POFile).find(POFile, potemplate=self, path=path).one()

    def getPOFileByLang(self, language_code):
        """See `IPOTemplate`."""
        # Consult cache first.
        if self._cached_pofiles_by_language is None:
            self._cached_pofiles_by_language = {}
        elif language_code in self._cached_pofiles_by_language:
            # Cache contains a remembered POFile for this language.  Don't do
            # the usual get() followed by "is None"; the dict may contain None
            # values to indicate we looked for a POFile and found none.
            return self._cached_pofiles_by_language[language_code]
        self._cached_pofiles_by_language[language_code] = (
            Store.of(self)
            .find(
                POFile,
                POFile.potemplate_id == self.id,
                POFile.language_id == Language.id,
                Language.code == language_code,
            )
            .one()
        )
        return self._cached_pofiles_by_language[language_code]

    def getOtherSidePOTemplate(self):
        """See `IPOTemplate`."""
        if self.translation_side == TranslationSide.UBUNTU:
            other_side_object = self.sourcepackage.productseries
        else:
            other_side_object = (
                self.productseries.getUbuntuTranslationFocusPackage()
            )
        if other_side_object is None:
            return None
        return other_side_object.getTranslationTemplateByName(self.name)

    def messageCount(self):
        """See `IRosettaStats`."""
        return self.messagecount

    def updateMessageCount(self):
        """Update `self.messagecount`."""
        self.messagecount = self.getPOTMsgSetsCount()

    def currentCount(self, language=None):
        """See `IRosettaStats`."""
        if language is None:
            return 0
        pofile = self.getPOFileByLang(language)
        if pofile is None:
            return 0
        else:
            return pofile.currentCount()

    def updatesCount(self, language=None):
        """See `IRosettaStats`."""
        if language is None:
            return 0
        pofile = self.getPOFileByLang(language)
        if pofile is None:
            return 0
        else:
            pofile.updatesCount()

    def rosettaCount(self, language=None):
        """See `IRosettaStats`."""
        if language is None:
            return 0
        pofile = self.getPOFileByLang(language)
        if pofile is None:
            return 0
        else:
            pofile.rosettaCount()

    def unreviewedCount(self, language=None):
        """See `IRosettaStats`."""
        if language is None:
            return 0
        pofile = self.getPOFileByLang(language)
        if pofile is None:
            return 0
        else:
            pofile.unreviewedCount()

    def _getPOTMsgSetBy(
        self,
        msgid_singular,
        msgid_plural=None,
        context=None,
        sharing_templates=False,
    ):
        """Look for a POTMsgSet by msgid_singular, msgid_plural, context.

        If `sharing_templates` is True, and the current template has no such
        POTMsgSet, look through sharing templates as well.
        """
        clauses = [
            TranslationTemplateItem.potmsgset_id == POTMsgSet.id,
            POTMsgSet.msgid_singular == msgid_singular,
            POTMsgSet.msgid_plural == msgid_plural,
            POTMsgSet.context == context,
        ]
        if sharing_templates:
            clauses.append(
                TranslationTemplateItem.potemplate_id.is_in(self._sharing_ids)
            )
        else:
            clauses.append(TranslationTemplateItem.potemplate_id == self.id)

        # If there are multiple messages, make the one from the
        # current POTemplate be returned first.
        order_by = SQL(
            "TranslationTemplateItem.potemplate <> ?", params=(self.id,)
        )
        return (
            IStore(POTMsgSet)
            .find(POTMsgSet, *clauses)
            .order_by(order_by)
            .first()
        )

    def hasMessageID(self, msgid_singular, msgid_plural, context=None):
        """See `IPOTemplate`."""
        return bool(
            self._getPOTMsgSetBy(msgid_singular, msgid_plural, context)
        )

    def hasPluralMessage(self):
        """See `IPOTemplate`."""
        clauses = self._getPOTMsgSetSelectionClauses()
        clauses.append(POTMsgSet.msgid_plural != None)
        return not Store.of(self).find(POTMsgSet, *clauses).is_empty()

    def export(self):
        """See `IPOTemplate`."""

        translation_exporter = getUtility(ITranslationExporter)
        template_file = getAdapter(self, ITranslationFileData, "all_messages")
        exported_file = translation_exporter.exportTranslationFiles(
            [template_file]
        )

        try:
            file_content = exported_file.read()
        finally:
            exported_file.close()

        return file_content

    def _generateTranslationFileDatas(self):
        """Yield `ITranslationFileData` objects for translations and self.

        This lets us construct the in-memory representations of the template
        and its translations one by one before exporting them, rather than
        building them all beforehand and keeping them in memory at the same
        time.
        """
        for pofile in self.pofiles:
            yield getAdapter(pofile, ITranslationFileData, "all_messages")

        yield getAdapter(self, ITranslationFileData, "all_messages")

    def exportWithTranslations(self):
        """See `IPOTemplate`."""

        translation_exporter = getUtility(ITranslationExporter)
        return translation_exporter.exportTranslationFiles(
            self._generateTranslationFileDatas()
        )

    def expireAllMessages(self):
        """See `IPOTemplate`."""
        for potmsgset in self.getPOTMsgSets(prefetch=False):
            potmsgset.setSequence(self, 0)

    def _lookupLanguage(self, language_code):
        """Look up named `Language` object, or raise `LanguageNotFound`."""
        language = getUtility(ILanguageSet).getLanguageByCode(language_code)
        if language is None:
            raise LanguageNotFound(language_code)
        return language

    def isPOFilePathAvailable(self, path):
        """Can we assign given path to a new `POFile` without clashes?

        Tests for uniqueness within the context of all templates for either
        self's product release series, or the combination of self's distro
        release series and source package (whichever applies).
        """
        pofileset = getUtility(IPOFileSet)
        existing_pofiles = pofileset.getPOFilesByPathAndOrigin(
            path, self.productseries, self.distroseries, self.sourcepackagename
        )
        return existing_pofiles.is_empty()

    def _composePOFilePath(self, language):
        """Make up a good name for a new `POFile` for given language.

        The name should be unique in this `ProductSeries` or this combination
        of `DistroSeries` and source package.  It is not guaranteed that the
        returned name will be unique, however, to avoid hiding obvious
        naming mistakes.
        """
        potemplate_dir = os.path.dirname(self.path)
        path = "%s-%s.po" % (self.translation_domain, language.code)

        return os.path.join(potemplate_dir, path)

    def _createPOFilesInSharingPOTemplates(self, pofile):
        """Create copies of the given pofile in all sharing potemplates."""
        subset = getUtility(IPOTemplateSet).getSharingSubset(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
            product=self.product,
        )
        for template in subset.getSharingPOTemplates(self.name):
            template = removeSecurityProxy(template)
            if template is self:
                continue
            language_code = pofile.language.code
            existingpo = template.getPOFileByLang(language_code)
            if existingpo is not None:
                continue
            newpopath = template._composePOFilePath(pofile.language)
            pofile = POFile(
                potemplate=template,
                language=pofile.language,
                topcomment=pofile.topcomment,
                header=pofile.header,
                fuzzyheader=pofile.fuzzyheader,
                owner=pofile.owner,
                path=newpopath,
            )

            # Update cache to reflect the change.
            template._cached_pofiles_by_language[language_code] = pofile

            # Set dummy translations for translation credits in this POFile.
            for credits in template.getTranslationCredits():
                credits.setTranslationCreditsToTranslated(pofile)

    def newPOFile(self, language_code, create_sharing=True, owner=None):
        """See `IPOTemplate`."""
        # Make sure we don't already have a PO file for this language.
        existingpo = self.getPOFileByLang(language_code)
        assert existingpo is None, (
            "There is already a valid IPOFile (%s)" % existingpo.title
        )

        # Since we have no PO file for this language yet, create one.
        language = self._lookupLanguage(language_code)

        now = datetime.now()
        data = {
            "year": now.year,
            "languagename": language.englishname,
            "languagecode": language_code,
            "date": now.isoformat(" "),
            "templatedate": self.datecreated,
            "copyright": "(c) %d Rosetta Contributors and Canonical Ltd"
            % now.year,
            "nplurals": language.pluralforms or 1,
            "pluralexpr": language.pluralexpression or "0",
        }

        if self.productseries is not None:
            data["origin"] = self.productseries.product.name
        else:
            data["origin"] = self.sourcepackagename.name

        # The default POFile owner is the Rosetta Experts team.
        if owner is None:
            owner = getUtility(ILaunchpadCelebrities).rosetta_experts

        path = self._composePOFilePath(language)

        pofile = POFile(
            potemplate=self,
            language=language,
            topcomment=standardPOFileTopComment % data,
            header=standardPOFileHeader % data,
            fuzzyheader=True,
            owner=owner,
            path=path,
        )

        # Update cache to reflect the change.
        self._cached_pofiles_by_language[language_code] = pofile

        # Set dummy translations for translation credits in this POFile.
        for credits in self.getTranslationCredits():
            credits.setTranslationCreditsToTranslated(pofile)

        if create_sharing:
            self._createPOFilesInSharingPOTemplates(pofile)

        pofile.updateStatistics()

        # Store the changes.
        flush_database_updates()

        return pofile

    def getPlaceholderPOFile(
        self, language, requester=None, check_for_existing=True
    ):
        """See `IPOTemplate`."""
        # Avoid circular import.
        from lp.translations.model.pofile import PlaceholderPOFile

        if check_for_existing:
            # see if a valid one exists.
            existingpo = self.getPOFileByLang(language.code)
            assert existingpo is None, (
                "There is already a valid IPOFile (%s)" % existingpo.title
            )

        return PlaceholderPOFile(self, language, owner=requester)

    def createPOTMsgSetFromMsgIDs(
        self, msgid_singular, msgid_plural=None, context=None, sequence=0
    ):
        """See `IPOTemplate`."""
        potmsgset = POTMsgSet(
            context=context,
            msgid_singular=msgid_singular,
            msgid_plural=msgid_plural,
        )

        potmsgset.setSequence(self, sequence)
        if potmsgset.is_translation_credit:
            for language in self.languages():
                pofile = self.getPOFileByLang(language.code)
                if pofile is not None:
                    potmsgset.setTranslationCreditsToTranslated(pofile)

        return potmsgset

    @staticmethod
    def getOrCreatePOMsgID(text):
        """Creates or returns existing POMsgID for given `text`."""
        try:
            msgid = POMsgID.getByMsgid(text)
        except NotFoundError:
            # If there are no existing message ids, create a new one.
            # We do not need to check whether there is already a message set
            # with the given text in this template.
            msgid = POMsgID.new(text)
        return msgid

    def createMessageSetFromText(
        self, singular_text, plural_text, context=None, sequence=0
    ):
        """See `IPOTemplate`."""

        msgid_singular = self.getOrCreatePOMsgID(singular_text)
        if plural_text is None:
            msgid_plural = None
        else:
            msgid_plural = self.getOrCreatePOMsgID(plural_text)
        assert not self.hasMessageID(msgid_singular, msgid_plural, context), (
            "There is already a message set for this template, file and"
            " primary msgid and context '%r'" % context
        )

        return self.createPOTMsgSetFromMsgIDs(
            msgid_singular, msgid_plural, context, sequence
        )

    def getOrCreateSharedPOTMsgSet(
        self,
        singular_text,
        plural_text,
        context=None,
        initial_file_references=None,
        initial_source_comment=None,
    ):
        """See `IPOTemplate`."""
        msgid_singular = self.getOrCreatePOMsgID(singular_text)
        if plural_text is None:
            msgid_plural = None
        else:
            msgid_plural = self.getOrCreatePOMsgID(plural_text)
        potmsgset = self._getPOTMsgSetBy(
            msgid_singular, msgid_plural, context, sharing_templates=True
        )
        if potmsgset is None:
            potmsgset = self.createPOTMsgSetFromMsgIDs(
                msgid_singular, msgid_plural, context, sequence=0
            )
            potmsgset.filereferences = initial_file_references
            potmsgset.sourcecomment = initial_source_comment
        return potmsgset

    def importFromQueue(self, entry_to_import, logger=None, txn=None):
        """See `IPOTemplate`."""
        assert entry_to_import is not None, "Attempt to import None entry."
        assert (
            entry_to_import.import_into.id == self.id
        ), "Attempt to import entry to POTemplate it doesn't belong to."
        assert (
            entry_to_import.status == RosettaImportStatus.APPROVED
        ), "Attempt to import non-approved entry."

        # XXX: JeroenVermeulen 2007-11-29: This method is called from the
        # import script, which can provide the right object but can only
        # obtain it in security-proxied form.  We need full, unguarded access
        # to complete the import.
        entry_to_import = removeSecurityProxy(entry_to_import)

        translation_importer = getUtility(ITranslationImporter)

        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
        subject = "Translation template import - %s" % self.displayname
        # Can use template_mail = 'poimport-template-confirmation.txt' to send
        # mail when everything is imported, but those mails aren't very useful
        # to or much welcomed by the recipients.  See bug 855150.
        template_mail = None
        errors, warnings = None, None
        try:
            errors, warnings = translation_importer.importFile(
                entry_to_import, logger
            )
        except (
            MixedNewlineMarkersError,
            TranslationFormatSyntaxError,
            TranslationFormatInvalidInputError,
            UnicodeDecodeError,
        ) as exception:
            if logger:
                logger.info(
                    "We got an error importing %s", self.title, exc_info=1
                )
            subject = "Import problem - %s" % self.displayname
            if isinstance(exception, UnicodeDecodeError):
                template_mail = "poimport-bad-encoding.txt"
            else:
                template_mail = "poimport-syntax-error.txt"
            entry_to_import.setStatus(
                RosettaImportStatus.FAILED, rosetta_experts
            )
            error_text = str(exception)
            entry_to_import.setErrorOutput(error_text)
        else:
            error_text = None
            entry_to_import.setErrorOutput(None)

        replacements = collect_import_info(entry_to_import, self, warnings)
        replacements.update(
            {
                "import_title": "translation templates for %s"
                % self.displayname,
            }
        )

        if error_text is not None:
            replacements["error"] = error_text

        entry_to_import.addWarningOutput(replacements["warnings"])

        if entry_to_import.status != RosettaImportStatus.FAILED:
            entry_to_import.setStatus(
                RosettaImportStatus.IMPORTED, rosetta_experts
            )

            # Assign karma to the importer if this is not an automatic import
            # (all automatic imports come from the rosetta expert team).
            celebs = getUtility(ILaunchpadCelebrities)
            rosetta_experts = celebs.rosetta_experts
            if entry_to_import.importer.id != rosetta_experts.id:
                entry_to_import.importer.assignKarma(
                    "translationtemplateimport",
                    product=self.product,
                    distribution=self.distribution,
                    sourcepackagename=self.sourcepackagename,
                )

            # Synchronize changes to database so we can calculate fresh
            # statistics on the server side.
            flush_database_updates()

            # Update cached number of msgsets.
            self.updateMessageCount()

            # The upload affects the statistics for all translations of this
            # template.  Recalculate those as well.  This takes time and
            # covers a lot of data, so if appropriate, break this up
            # into smaller transactions.
            if txn is not None:
                txn.commit()
                txn.begin()

            for pofile in self.pofiles:
                try:
                    pofile.updateStatistics()
                    if txn is not None:
                        txn.commit()
                        txn.begin()
                except TransactionRollbackError as error:
                    if txn is not None:
                        txn.abort()
                        txn.begin()
                    if logger:
                        logger.warning(
                            "Statistics update failed: %s" % str(error)
                        )

        if template_mail is not None:
            template = get_email_template(template_mail, "translations")
            message = template % replacements
            return (subject, message)
        else:
            return None, None

    def getTranslationRows(self):
        """See `IPOTemplate`."""
        Singular = ClassAlias(POMsgID)
        Plural = ClassAlias(POMsgID)

        SingularJoin = LeftJoin(
            Singular, Singular.id == POTMsgSet.msgid_singular_id
        )
        PluralJoin = LeftJoin(Plural, Plural.id == POTMsgSet.msgid_plural_id)

        source = Store.of(self).using(
            TranslationTemplateItem, POTMsgSet, SingularJoin, PluralJoin
        )

        rows = source.find(
            (TranslationTemplateItem, POTMsgSet, Singular, Plural),
            TranslationTemplateItem.potemplate == self,
            POTMsgSet.id == TranslationTemplateItem.potmsgset_id,
        )

        rows = rows.order_by(TranslationTemplateItem.sequence)

        for row in rows:
            yield VPOTExport(self, *row)

    @property
    def translation_side(self):
        """See `IPOTemplate`."""
        if self.productseries_id is not None:
            return TranslationSide.UPSTREAM
        else:
            return TranslationSide.UBUNTU

    def awardKarma(self, person, action_name):
        """See `IPOTemplate`."""
        person.assignKarma(
            action_name,
            product=self.product,
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
        )


@implementer(IPOTemplateSubset)
class POTemplateSubset:
    def __init__(
        self,
        sourcepackagename=None,
        from_sourcepackagename=None,
        distroseries=None,
        productseries=None,
        iscurrent=None,
        ordered_by_names=False,
    ):
        """Create a new `POTemplateSubset` object.

        The set of POTemplate depends on the arguments you pass to this
        constructor. The sourcepackagename, from_sourcepackagename,
        distroseries and productseries are just filters for that set.
        In addition, iscurrent sets the filter for the iscurrent flag.
        """
        self.sourcepackagename = sourcepackagename
        self.distroseries = distroseries
        self.productseries = productseries
        self.iscurrent = iscurrent
        self.orderby = [POTemplate.id]
        self.clauses = []

        assert (
            productseries is None or distroseries is None
        ), "A product series must not be used with a distro series."

        assert (
            productseries is not None or distroseries is not None
        ), "Either productseries or distroseries must be not None."

        # Construct the base clauses.
        if productseries is not None:
            self.clauses.append(POTemplate.productseries == productseries)
            if ordered_by_names:
                self.orderby = [POTemplate.name]
        else:
            self.clauses.append(POTemplate.distroseries == distroseries)
            if ordered_by_names:
                self.orderby = [SourcePackageName.name, POTemplate.name]
            if from_sourcepackagename is not None:
                self.clauses.append(
                    POTemplate.from_sourcepackagename == from_sourcepackagename
                )
                self.sourcepackagename = from_sourcepackagename
            elif sourcepackagename is not None:
                self.clauses.append(
                    POTemplate.sourcepackagename == sourcepackagename
                )
            else:
                # Select all POTemplates in a Distroseries.
                pass
        # Add the filter for the iscurrent flag if requested.
        if iscurrent is not None:
            self.clauses.append(POTemplate.iscurrent == iscurrent)

    def _build_query(
        self, additional_clause=None, ordered=True, do_prejoin=True
    ):
        """Construct the storm query."""
        if additional_clause is None:
            condition = And(self.clauses)
        else:
            condition = And(self.clauses + [additional_clause])

        if self.productseries is not None:
            store = Store.of(self.productseries)
            query = store.find(POTemplate, condition)
        else:
            store = Store.of(self.distroseries)
            if do_prejoin:
                query = DecoratedResultSet(
                    store.find(
                        (POTemplate, SourcePackageName),
                        (
                            POTemplate.sourcepackagename_id
                            == SourcePackageName.id
                        ),
                        condition,
                    ),
                    operator.itemgetter(0),
                )
            else:
                query = store.find(POTemplate, condition)

        if ordered:
            return query.order_by(self.orderby)
        return query

    def __iter__(self):
        """See `IPOTemplateSubset`."""
        yield from self._build_query()

    def __len__(self):
        """See `IPOTemplateSubset`."""
        result = self._build_query(do_prejoin=False, ordered=False)
        return result.count()

    def __getitem__(self, name):
        """See `IPOTemplateSubset`."""
        potemplate = self.getPOTemplateByName(name)
        if potemplate is None:
            raise NotFoundError(name)
        else:
            return potemplate

    @property
    def title(self):
        """See `IPOTemplateSubset`."""
        titlestr = ""
        if self.distroseries:
            titlestr += " " + self.distroseries.displayname
        if self.sourcepackagename:
            titlestr += " " + self.sourcepackagename.name
        if self.productseries:
            titlestr += " "
            titlestr += self.productseries.displayname
        return titlestr

    def _copyPOFilesFromSharingTemplates(self, template):
        subset = getUtility(IPOTemplateSet).getSharingSubset(
            distribution=template.distribution,
            sourcepackagename=template.sourcepackagename,
            product=template.product,
        )
        for shared_template in subset.getSharingPOTemplates(template.name):
            shared_template = removeSecurityProxy(shared_template)
            if shared_template is template:
                continue
            for pofile in shared_template.pofiles:
                template.newPOFile(pofile.language.code, create_sharing=False)
            # Do not continue, else it would trigger an existingpo assertion.
            return

    def _getSuperSet(self):
        """Return the set of all POTemplates for this series and package."""
        if self.iscurrent is None:
            return self
        else:
            return getUtility(IPOTemplateSet).getSubset(
                productseries=self.productseries,
                distroseries=self.distroseries,
                sourcepackagename=self.sourcepackagename,
            )

    def isNameUnique(self, name):
        """See `IPOTemplateSubset`."""
        return self._getSuperSet().getPOTemplateByName(name) is None

    def new(self, name, translation_domain, path, owner, copy_pofiles=True):
        """See `IPOTemplateSubset`."""
        existing_template = self._getSuperSet().getPOTemplateByName(name)
        if existing_template is not None:
            raise ValueError(
                "POTempate %s already exists and is iscurrent=%s"
                % (name, existing_template.iscurrent)
            )
        header_params = {
            "origin": "PACKAGE VERSION",
            "templatedate": datetime.now(),
            "languagename": "LANGUAGE",
            "languagecode": "LL",
        }
        template = POTemplate(
            name=name,
            translation_domain=translation_domain,
            sourcepackagename=self.sourcepackagename,
            distroseries=self.distroseries,
            productseries=self.productseries,
            path=path,
            owner=owner,
            header=standardTemplateHeader % header_params,
        )
        if copy_pofiles:
            self._copyPOFilesFromSharingTemplates(template)
        return template

    def getPOTemplateByName(self, name):
        """See `IPOTemplateSubset`."""
        result = self._build_query(POTemplate.name == name, ordered=False)
        return result.one()

    def getPOTemplatesByTranslationDomain(self, translation_domain):
        """See `IPOTemplateSubset`."""
        return self._build_query(
            POTemplate.translation_domain == translation_domain
        )

    def getPOTemplateByPath(self, path):
        """See `IPOTemplateSubset`."""
        result = self._build_query(POTemplate.path == path, ordered=False)
        return result.one()

    def getAllOrderByDateLastUpdated(self):
        """See `IPOTemplateSet`."""
        result = self._build_query(ordered=False)
        return result.order_by(Desc(POTemplate.date_last_updated))

    def getClosestPOTemplate(self, path):
        """See `IPOTemplateSubset`."""
        if path is None:
            return None

        closest_template = None
        closest_template_path_length = 0
        repeated = False
        for template in self:
            template_path_length = len(
                os.path.commonprefix([template.path, path])
            )
            if template_path_length > closest_template_path_length:
                # This template is more near than the one we got previously
                closest_template = template
                closest_template_path_length = template_path_length
                repeated = False
            elif template_path_length == closest_template_path_length:
                # We found two templates with the same length, we note that
                # fact, if we don't get a better template, we ignore them and
                # leave it to the admins.
                repeated = True
        if repeated:
            return None
        else:
            return closest_template

    def findUniquePathlessMatch(self, filename):
        """See `IPOTemplateSubset`."""
        result = self._build_query(
            Or(
                POTemplate.path == filename,
                POTemplate.path.endswith("/%s" % filename),
            ),
            ordered=False,
        )
        candidates = list(result.config(limit=2))

        if len(candidates) == 1:
            # Found exactly one match.
            return candidates[0]
        else:
            return None


@implementer(IPOTemplateSet)
class POTemplateSet:
    def __iter__(self):
        """See `IPOTemplateSet`."""
        yield from IStore(POTemplate).find(POTemplate)

    def getAllByName(self, name):
        """See `IPOTemplateSet`."""
        return (
            IStore(POTemplate)
            .find(POTemplate, name=name)
            .order_by(POTemplate.name, POTemplate.id)
        )

    def getAllOrderByDateLastUpdated(self):
        """See `IPOTemplateSet`."""
        return (
            IStore(POTemplate)
            .find(POTemplate)
            .order_by(Desc(POTemplate.date_last_updated))
        )

    def getSubset(
        self,
        distroseries=None,
        sourcepackagename=None,
        productseries=None,
        iscurrent=None,
        ordered_by_names=False,
    ):
        """See `IPOTemplateSet`."""
        return POTemplateSubset(
            distroseries=distroseries,
            sourcepackagename=sourcepackagename,
            productseries=productseries,
            iscurrent=iscurrent,
            ordered_by_names=ordered_by_names,
        )

    def getSharingSubset(
        self, distribution=None, sourcepackagename=None, product=None
    ):
        """See `IPOTemplateSet`."""
        return POTemplateSharingSubset(
            self,
            distribution=distribution,
            sourcepackagename=sourcepackagename,
            product=product,
        )

    def getPOTemplateByPathAndOrigin(
        self,
        path,
        productseries=None,
        distroseries=None,
        sourcepackagename=None,
    ):
        """See `IPOTemplateSet`."""
        assert (productseries is None) != (
            sourcepackagename is None
        ), "Must specify either productseries or sourcepackagename."

        conditions = And(
            POTemplate.iscurrent == True,
            POTemplate.path == path,
            POTemplate.productseries == productseries,
            Or(
                POTemplate.from_sourcepackagename == sourcepackagename,
                POTemplate.sourcepackagename == sourcepackagename,
            ),
        )

        if distroseries:
            conditions = And(
                conditions, POTemplate.distroseries == distroseries
            )

        store = IStore(POTemplate)
        matches = shortlist(store.find(POTemplate, conditions))

        if len(matches) == 0:
            # Nope.  Sorry.
            return None
        elif len(matches) == 1:
            # Yup.  Great.
            return matches[0]
        elif sourcepackagename is None:
            # Multiple matches, and for a product not a package.
            logging.warning(
                "Found %d templates with path '%s' for productseries %s",
                len(matches),
                path,
                productseries.title,
            )
            return None
        else:
            # Multiple matches, for a distribution package.  Prefer a
            # match on from_sourcepackagename: the file may have been
            # uploaded for another package than the one it is meant to
            # be imported into.
            preferred_matches = [
                match
                for match in matches
                if match.from_sourcepackagename == sourcepackagename
            ]

            if len(preferred_matches) == 1:
                return preferred_matches[0]
            else:
                logging.warning(
                    "Found %d templates with path '%s' for package %s "
                    "(%d matched on from_sourcepackagename).",
                    len(matches),
                    path,
                    sourcepackagename.name,
                    len(preferred_matches),
                )
                return None

    def preloadPOTemplateContexts(self, templates):
        """See `IPOTemplateSet`."""
        from lp.registry.model.product import Product
        from lp.registry.model.productseries import ProductSeries

        pses = load_related(ProductSeries, templates, ["productseries_id"])
        load_related(Product, pses, ["product_id"])
        load_related(SourcePackageName, templates, ["sourcepackagename_id"])

    def wipeSuggestivePOTemplatesCache(self):
        """See `IPOTemplateSet`."""
        return (
            IPrimaryStore(POTemplate)
            .execute("DELETE FROM SuggestivePOTemplate")
            .rowcount
        )

    def removeFromSuggestivePOTemplatesCache(self, potemplate):
        """See `IPOTemplateSet`."""
        rowcount = (
            IPrimaryStore(POTemplate)
            .execute(
                "DELETE FROM SuggestivePOTemplate WHERE potemplate = ?",
                params=(potemplate.id,),
            )
            .rowcount
        )
        return rowcount == 1

    def populateSuggestivePOTemplatesCache(self):
        """See `IPOTemplateSet`."""
        return (
            IPrimaryStore(POTemplate)
            .execute(
                """
            INSERT INTO SuggestivePOTemplate (
                SELECT POTemplate.id
                FROM POTemplate
                LEFT JOIN DistroSeries ON
                    DistroSeries.id = POTemplate.distroseries
                LEFT JOIN Distribution ON
                    Distribution.id = DistroSeries.distribution
                LEFT JOIN ProductSeries ON
                    ProductSeries.id = POTemplate.productseries
                LEFT JOIN Product ON
                    Product.id = ProductSeries.product
                WHERE
                    POTemplate.iscurrent AND (
                        Distribution.translations_usage IN (?, ?) OR
                        Product.translations_usage IN (?, ?))
                ORDER BY POTemplate.id
            )
            """,
                params=(
                    ServiceUsage.LAUNCHPAD.value,
                    ServiceUsage.EXTERNAL.value,
                    ServiceUsage.LAUNCHPAD.value,
                    ServiceUsage.EXTERNAL.value,
                ),
            )
            .rowcount
        )


@implementer(IPOTemplateSharingSubset)
class POTemplateSharingSubset:
    distribution = None
    sourcepackagename = None
    product = None

    def __init__(
        self,
        potemplateset,
        distribution=None,
        sourcepackagename=None,
        product=None,
    ):
        assert product or distribution, "Pick a product or distribution!"
        assert not (
            product and distribution
        ), "Pick a product or distribution, not both!"
        assert (
            distribution or not sourcepackagename
        ), "Picking a source package only makes sense with a distribution."
        self.potemplateset = potemplateset

        self.distribution = distribution
        self.sourcepackagename = sourcepackagename
        self.product = product

    def _get_potemplate_equivalence_class(self, template):
        """Return whatever we group `POTemplate`s by for sharing purposes."""
        if template.sourcepackagename is None:
            package = None
        else:
            package = template.sourcepackagename.name
        return (template.name, package)

    def _queryPOTemplates(self, templatename_clause):
        """Find all POTemplates in this sharing subset."""
        from lp.registry.model.distroseries import DistroSeries
        from lp.registry.model.productseries import ProductSeries

        product_id = distro_id = spn_id = None
        if self.product is not None:
            product_id = self.product.id
        else:
            distro_id = self.distribution.id
            spn_id = self.sourcepackagename.id

        # Fake Storm table class for the CTE. The PK is a lie.
        class Location:
            __storm_table__ = "location"
            __storm_primary__ = (
                "product_id",
                "distribution_id",
                "sourcepackagename_id",
            )
            product_id = Int(name="product")
            distribution_id = Int(name="distribution")
            sourcepackagename_id = Int(name="sourcepackagename")

        # Message sharing is by necessity symmetric and transitive,
        # since the POTMsgSets records themselves are shared. Two
        # relationships are defined to cause templates to share:
        #
        #  - A template shares with identically named templates in other
        #    series in its own location (other ProductSeries in the same
        #    Product, or other SourcePackages in the same
        #    DistributionSourcePackage).
        #
        #  - A template shares with identically named templates on the
        #    other side of a Packaging record (in a ProductSeries for a
        #    SourcePackage template, or a SourcePackage for a
        #    ProductSeries template).
        #
        # To avoid surprising changes when a new template is created
        # somewhere, and to simplify implementation, we make the second
        # relationship slightly more liberal: Packagings directly link
        # entire Products and DistributionSourcePackages, not just the
        # specified series.
        #
        # The only practical change is that templates can be shared
        # between locations even if a similarly named template doesn't
        # exist in the exact series specified by the Packaging. With
        # transitivity but without this extension, two big existing
        # sharing subsets might end up being joined later on just
        # because a template was copied from an unlinked series to a
        # linked one.
        #
        # XXX wgrant 2014-08-28: An outdated version of these rules is
        # reimplemented in TranslationSplitter, but TranslationSplitter
        # is terribly broken (see XXXs in its module).

        # The recursive CTE finds all Products and
        # DistributionSourcePackages that are transitively linked by
        # Packagings, starting with the location that we have. We then
        # join out to their series and find any templates with the right
        # name.
        context = IStore(POTemplate).with_(
            SQL(sharing_subset_cte, params=(product_id, distro_id, spn_id))
        )
        return context.using(
            Location,
            LeftJoin(
                DistroSeries,
                DistroSeries.distribution_id == Location.distribution_id,
            ),
            LeftJoin(
                ProductSeries, ProductSeries.product_id == Location.product_id
            ),
            Join(
                POTemplate,
                And(
                    Or(
                        POTemplate.productseries_id == ProductSeries.id,
                        And(
                            POTemplate.distroseries_id == DistroSeries.id,
                            POTemplate.sourcepackagename_id
                            == Location.sourcepackagename_id,
                        ),
                    ),
                    templatename_clause,
                ),
            ),
        ).find(POTemplate)

    def getSharingPOTemplates(self, potemplate_name):
        """See `IPOTemplateSharingSubset`."""
        if self.distribution is not None:
            assert (
                self.sourcepackagename is not None
            ), "Need sourcepackagename to select from distribution."
        return self._queryPOTemplates(POTemplate.name == potemplate_name)

    def getSharingPOTemplatesByRegex(self, name_pattern=None):
        """See `IPOTemplateSharingSubset`."""
        if name_pattern is None:
            templatename_clause = True
        else:
            templatename_clause = RegexpMatch(POTemplate.name, name_pattern)

        return self._queryPOTemplates(templatename_clause)

    def getSharingPOTemplateIDs(self, potemplate_name):
        """See `IPOTemplateSharingSubset`."""
        return self.getSharingPOTemplates(potemplate_name).values(
            POTemplate.id
        )

    def groupEquivalentPOTemplates(self, name_pattern=None):
        """See `IPOTemplateSharingSubset`."""
        equivalents = {}

        for template in self.getSharingPOTemplatesByRegex(name_pattern):
            key = self._get_potemplate_equivalence_class(template)
            if key not in equivalents:
                equivalents[key] = []
            equivalents[key].append(template)

        for equivalence_list in equivalents.values():
            # Sort potemplates from "most representative" to "least
            # representative."
            equivalence_list.sort(key=POTemplate.sharingKey, reverse=True)

        return equivalents


@implementer(ITranslationFileData)
class POTemplateToTranslationFileDataAdapter:
    """Adapter from `IPOTemplate` to `ITranslationFileData`."""

    def __init__(self, potemplate):
        self._potemplate = potemplate
        self.messages = self._getMessages()
        self.format = potemplate.source_file_format

    @cachedproperty
    def path(self):
        """See `ITranslationFileData`."""
        return self._potemplate.path

    @cachedproperty
    def translation_domain(self):
        """See `ITranslationFileData`."""
        return self._potemplate.translation_domain

    @property
    def is_template(self):
        """See `ITranslationFileData`."""
        return True

    @property
    def language_code(self):
        """See `ITraslationFile`."""
        return None

    @cachedproperty
    def header(self):
        """See `ITranslationFileData`."""
        return self._potemplate.getHeader()

    def _getMessages(self):
        """Return a list of `ITranslationMessageData`."""
        potemplate = self._potemplate
        # Get all rows related to this file. We do this to speed the export
        # process so we have a single DB query to fetch all needed
        # information.
        rows = potemplate.getTranslationRows()

        messages = []

        for row in rows:
            assert (
                row.potemplate.id == potemplate.id
            ), "Got a row for a different IPOTemplate."

            # Skip messages which aren't anymore in the PO template.
            if row.sequence == 0:
                continue

            # Create new message set
            msgset = TranslationMessageData()
            msgset.sequence = row.sequence
            msgset.obsolete = False
            msgset.msgid_singular = row.msgid_singular
            msgset.singular_text = row.potmsgset.singular_text
            msgset.msgid_plural = row.msgid_plural
            msgset.plural_text = row.potmsgset.plural_text
            msgset.context = row.context
            msgset.comment = row.comment
            msgset.source_comment = row.source_comment
            msgset.file_references = row.file_references

            if row.flags_comment:
                msgset.flags = {
                    flag.strip()
                    for flag in row.flags_comment.split(",")
                    if flag
                }

            # Store the message.
            messages.append(msgset)

        return messages


class TranslationTemplatesCollection(Collection):
    """A `Collection` of `POTemplate`."""

    starting_table = POTemplate

    def restrictProductSeries(self, productseries):
        return self.refine(POTemplate.productseries == productseries)

    def restrictDistroSeries(self, distroseries):
        return self.refine(POTemplate.distroseries == distroseries)

    def restrictSourcePackageName(self, sourcepackagename):
        return self.refine(POTemplate.sourcepackagename == sourcepackagename)

    def restrictCurrent(self, current_value=True):
        """Select based on `POTemplate.iscurrent`.

        :param current_value: The value for `iscurrent` that you are
            looking for.  Defaults to True, meaning this will restrict
            to current templates.  If False, will select obsolete
            templates instead.
        :return: A `TranslationTemplatesCollection` based on this one,
            but restricted to ones with the desired `iscurrent` value.
        """
        return self.refine(POTemplate.iscurrent == current_value)

    def restrictName(self, template_name):
        """Select based on `POTemplate.name`.

        :param template: The value for `name` that you are looking for.
        :return: A `TranslationTemplatesCollection based on this one but
            restricted to ones with the desired `name` value.
        """
        return self.refine(POTemplate.name == template_name)

    def joinPOFile(self):
        """Join `POFile` into the collection.

        :return: A `TranslationTemplatesCollection` with an added inner
            join to `POFile`.
        """
        return self.joinInner(POFile, POTemplate.id == POFile.potemplate_id)

    def joinOuterPOFile(self, language=None):
        """Outer-join `POFile` into the collection.

        :return: A `TranslationTemplatesCollection` with an added outer
            join to `POFile`.
        """
        if language is not None:
            return self.joinOuter(
                POFile,
                And(
                    POTemplate.id == POFile.potemplate_id,
                    POFile.language_id == language.id,
                ),
            )
        else:
            return self.joinOuter(
                POFile, POTemplate.id == POFile.potemplate_id
            )
