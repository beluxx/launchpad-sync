POFile
======

Get evolution template for Ubuntu Hoary

    >>> from datetime import datetime, timezone
    >>> from zope.component import getUtility
    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet,
    ... )
    >>> from lp.translations.interfaces.pofile import IPOFile
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> sourcepackagenameset = getUtility(ISourcePackageNameSet)
    >>> sourcepackagename = sourcepackagenameset["evolution"]
    >>> distributionset = getUtility(IDistributionSet)
    >>> distribution = distributionset["ubuntu"]
    >>> series = distribution["hoary"]
    >>> potemplateset = getUtility(IPOTemplateSet)
    >>> potemplatesubset = potemplateset.getSubset(
    ...     distroseries=series, sourcepackagename=sourcepackagename
    ... )
    >>> potemplate = potemplatesubset["evolution-2.2"]

Get Xhosa translation

    >>> pofile = potemplate.getPOFileByLang("xh")
    >>> language_pt_BR = getUtility(ILanguageSet).getLanguageByCode("pt_BR")
    >>> placeholder_pofile = potemplate.getPlaceholderPOFile(language_pt_BR)

Both implement the IPOFile interface:

    >>> verifyObject(IPOFile, pofile)
    True

    >>> verifyObject(IPOFile, placeholder_pofile)
    True

PlaceholderPOFile returns empty SelectResults for getPOTMsgSet* methods,
except for untranslated messages.

    >>> placeholder_pofile.getPOTMsgSetTranslated().count()
    0

    >>> placeholder_pofile.getPOTMsgSetDifferentTranslations().count()
    0

    >>> placeholder_pofile.getPOTMsgSetWithNewSuggestions().count()
    0

    >>> placeholder_pofile.getPOTMsgSetUntranslated().count()
    22

Get the set of POTMsgSets that are untranslated.

    >>> potmsgsets = list(pofile.getPOTMsgSetUntranslated())
    >>> len(potmsgsets)
    22

Get Spanish translation

    >>> pofile = potemplate.getPOFileByLang("es")

Get the set of POTMsgSets that are untranslated.

    >>> potmsgsets = list(pofile.getPOTMsgSetUntranslated())
    >>> len(potmsgsets)
    15

We need a helper method to better display test results.

    >>> def print_potmsgsets(potmsgsets, pofile):
    ...     for potmsgset in potmsgsets:
    ...         singular = plural = None
    ...         translation = ""
    ...         if potmsgset.singular_text:
    ...             singular = potmsgset.singular_text
    ...             if len(singular) > 20:
    ...                 singular = singular[:17] + "..."
    ...         if potmsgset.plural_text:
    ...             plural = potmsgset.plural_text
    ...             if len(plural) > 20:
    ...                 plural = plural[:17] + "..."
    ...         if pofile is not None:
    ...             message = potmsgset.getCurrentTranslation(
    ...                 pofile.potemplate,
    ...                 pofile.language,
    ...                 pofile.potemplate.translation_side,
    ...             )
    ...             if message is not None:
    ...                 translation = message.translations[0]
    ...             if len(translation) > 20:
    ...                 translation = translation[:17] + "..."
    ...         print(
    ...             "%2d. %-20s   %-20s   %-20s"
    ...             % (
    ...                 potmsgset.getSequence(pofile.potemplate),
    ...                 singular,
    ...                 plural,
    ...                 translation,
    ...             )
    ...         )
    ...


getFullLanguageCode
-------------------

Returns the complete code for this POFile's language.

    >>> print(potemplate.getPOFileByLang("es").getFullLanguageCode())
    es

    >>> sr_latin = factory.makeLanguage("sr@latin", "Serbian Latin")
    >>> print(potemplate.getPlaceholderPOFile(sr_latin).getFullLanguageCode())
    sr@latin


getFullLanguageName
-------------------

Returns the complete English name for this POFile's language.

    >>> print(potemplate.getPOFileByLang("es").getFullLanguageName())
    Spanish

    >>> print(potemplate.getPlaceholderPOFile(sr_latin).getFullLanguageName())
    Serbian Latin


findPOTMsgSetsContaining
------------------------

It is common to want to find those POTMsgSets which contain a certain
substring in their original English string.

    >>> found_potmsgsets = placeholder_pofile.findPOTMsgSetsContaining(
    ...     "contact"
    ... )
    >>> found_potmsgsets.count()
    4

    >>> print_potmsgsets(found_potmsgsets, placeholder_pofile)
     7. contact's header:      None
    14. The location and ...   None
    15. %d contact             %d contacts
    16. Opening %d contac...   Opening %d contac...

Search is case-insensitive.

    >>> found_potmsgsets = placeholder_pofile.findPOTMsgSetsContaining(
    ...     "CONTact"
    ... )
    >>> found_potmsgsets.count()
    4

    >>> print_potmsgsets(found_potmsgsets, placeholder_pofile)
     7. contact's header:      None
    14. The location and ...   None
    15. %d contact             %d contacts
    16. Opening %d contac...   Opening %d contac...

Search will look through plural msgids as well.

    >>> found_potmsgsets = placeholder_pofile.findPOTMsgSetsContaining(
    ...     "contacts"
    ... )
    >>> found_potmsgsets.count()
    2

    >>> print_potmsgsets(found_potmsgsets, placeholder_pofile)
    15. %d contact             %d contacts
    16. Opening %d contac...   Opening %d contac...

Looking for a non-existing string returns an empty SelectResults.

    >>> found_potmsgsets = placeholder_pofile.findPOTMsgSetsContaining(
    ...     "non-existing-string"
    ... )
    >>> found_potmsgsets.count()
    0

Trying to find a string shorter than two characters doesn't work.

    >>> found_potmsgsets = placeholder_pofile.findPOTMsgSetsContaining("a")
    Traceback (most recent call last):
    ...
    AssertionError: You can not search for strings shorter than 2 characters.

In a Spanish translation, you will also get matching translations.

    >>> found_potmsgsets = pofile.findPOTMsgSetsContaining("ventana")
    >>> found_potmsgsets.count()
    1

    >>> print_potmsgsets(found_potmsgsets, pofile)
    16. Opening %d contac...   Opening %d contac...   Abrir %d contacto...

Searching for translations is case insensitive.

    >>> found_potmsgsets = pofile.findPOTMsgSetsContaining("VENTANA")
    >>> found_potmsgsets.count()
    1

    >>> print_potmsgsets(found_potmsgsets, pofile)
    16. Opening %d contac...   Opening %d contac...   Abrir %d contacto...

Searching for plural forms other than the first one also works.

    >>> found_potmsgsets = pofile.findPOTMsgSetsContaining("estos")
    >>> found_potmsgsets.count()
    1

    >>> print_potmsgsets(found_potmsgsets, pofile)
    16. Opening %d contac...   Opening %d contac...   Abrir %d contacto...

One can find a message by looking for a suggestion (non-current
translation).

    >>> found_potmsgsets = pofile.findPOTMsgSetsContaining("tarjetas")
    >>> found_potmsgsets.count()
    1

    >>> print_potmsgsets(found_potmsgsets, pofile)
     5.  cards                 None                    caratas


path
----

A PO file has a storage path that determines where the file is to be
stored in a filesystem tree (such as an export tarball).  The path ends
with the actual file name and should include a language code.

    >>> pofile_xh = potemplate.getPOFileByLang("xh")
    >>> print(pofile_xh.path)
    xh.po

To change this path, use setPathIfUnique().

    >>> pofile_xh.setPathIfUnique("xh2.po")
    >>> print(pofile_xh.path)
    xh2.po

The path must be unique within its distribution series package or
product release series, so that a single file system tree can contain
all translations found there.

If the given path is not locally unique, setPathIfUnique() simply does
nothing.  There can be no naming conflict in that case because the PO
file's existing path is already supposed to be unique.

Here we try to copy the path of another translation of the same template
but the PO file correctly retains its original path.

    >>> pofile_xh.setPathIfUnique(pofile.path)
    >>> print(pofile_xh.path)
    xh2.po


updateHeader()
--------------

This method is used to update the header of the POFile to a newer
version.

This is the new header we are going to apply.

    >>> new_header_string = '''Project-Id-Version: es
    ... POT-Creation-Date: 2004-08-18 11:10+0200
    ... PO-Revision-Date: 2005-08-18 13:22+0000
    ... Last-Translator: Carlos Perell\xc3\xb3 Mar\xc3\xadn
    ... <carlos@canonical.com>
    ... Language-Team: Spanish <traductores@es.gnome.org>
    ... MIME-Version: 1.0
    ... Content-Type: text/plain; charset=UTF-8
    ... Content-Transfer-Encoding: 8bit
    ... Report-Msgid-Bugs-To: serrador@hispalinux.es'''

We can get an ITranslationHeaderData from the file format importer.

    >>> from lp.translations.interfaces.translationimporter import (
    ...     ITranslationImporter,
    ... )
    >>> translation_importer = getUtility(ITranslationImporter)
    >>> format_importer = translation_importer.getTranslationFormatImporter(
    ...     pofile.potemplate.source_file_format
    ... )
    >>> new_header = format_importer.getHeaderFromString(new_header_string)
    >>> new_header.comment = " This is the top comment."

Before doing any change, we can see what's right now in the database:

    >>> print(pretty(pofile.topcomment.splitlines()[:2]))
    [' traducci\xf3n de es.po al Spanish',
     ' translation of es.po to Spanish']

    >>> print(pofile.header)
    Project-Id-Version: es
    POT-Creation-Date: 2004-08-17 11:10+0200
    PO-Revision-Date: 2005-04-07 13:22+0000
    ...
    Plural-Forms: nplurals=2; plural=(n != 1);

Let's update the header with the new one.

    >>> pofile.updateHeader(new_header)

The new comment is now applied.

    >>> print(pretty(pofile.topcomment))
    ' This is the top comment.'

And the new header contains the new string.

    >>> print(pofile.header)
    Project-Id-Version: es
    Report-Msgid-Bugs-To: serrador@hispalinux.es
    POT-Creation-Date: 2004-08-18 11:10+0200
    PO-Revision-Date: 2005-08-18 13:22+0000
    ...


isTranslationRevisionDateOlder
------------------------------

This method helps to compare two PO files header and decide if the given
one is older than the one we have in the IPOFile object. We are using
this method, for instance, to know if a new imported PO file should be
ignored because we already have a newer one.

This test is to be sure that the date comparison is working and that
two headers with the same date will always be set as newer, because lazy
translators forget to update that field from time to time and sometimes,
we were losing translations because we were ignoring those imports too.

    >>> print(pofile.header)
    Project-Id-Version: es
    ...
    PO-Revision-Date: 2005-08-18 13:22+0000
    ...

    >>> header = pofile.getHeader()

First, with the same date, we don't consider it older.

    >>> pofile.isTranslationRevisionDateOlder(header)
    False

Now, we can see how we detect that it's older with an older date.

    >>> header.translation_revision_date = datetime(
    ...     2005, 8, 18, 13, 21, tzinfo=timezone.utc
    ... )
    >>> pofile.isTranslationRevisionDateOlder(header)
    True

If the revision date of the stored translation file is missing, the new
one is considered an update.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.translations.utilities.gettext_po_parser import POHeader

    >>> old_pofile = removeSecurityProxy(potemplate.newPOFile("tl"))
    >>> old_pofile.header = """
    ...     Project-Id-Version: foo
    ...     MIME-Version: 1.0
    ...     Content-Type: text/plain; charset=UTF-8
    ...     Content-Transfer-Encoding: 8bit
    ...     """
    >>> new_header = POHeader(
    ...     """
    ...     Project-Id-Version: foo
    ...     PO-Revision-Date: 2007-05-03 14:00+0200
    ...     MIME-Version: 1.0
    ...     Content-Type: text/plain; charset=UTF-8
    ...     Content-Transfer-Encoding: 8bit
    ...     """
    ... )

    >>> old_pofile.isTranslationRevisionDateOlder(new_header)
    False

This even goes if the new file also omits the revision date.

    >>> new_header = POHeader(
    ...     """
    ...     Project-Id-Version: foo
    ...     MIME-Version: 1.0
    ...     Content-Type: text/plain; charset=UTF-8
    ...     Content-Transfer-Encoding: 8bit
    ...     """
    ... )
    >>> old_pofile.isTranslationRevisionDateOlder(new_header)
    False


plural_forms
------------

This method returns a number of plural forms for the language of the
POFile, or a default of 2 when language doesn't specify it: 2 is the
most common value for number of plural forms, so most likely to be
correct for any new language.  Even if the default value is incorrect,
it is handled gracefully by the rest of the system (see doc/poimport.rst
for example).

When the language has number of plural forms defined, that value is
used.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> evolution = getUtility(IProductSet).getByName("evolution")
    >>> evolution_trunk = evolution.getSeries("trunk")
    >>> evolution_pot = evolution_trunk.getPOTemplate("evolution-2.2")
    >>> serbian = getUtility(ILanguageSet)["sr"]
    >>> serbian.pluralforms
    3

    >>> evolution_sr = evolution_pot.getPlaceholderPOFile(serbian)
    >>> evolution_sr.plural_forms
    3

And when a language has no plural forms defined, a POFile defaults to 2,
the most common number of plural forms:

    >>> divehi = getUtility(ILanguageSet)["dv"]
    >>> print(divehi.pluralforms)
    None

    >>> evolution_dv = evolution_pot.getPlaceholderPOFile(divehi)
    >>> evolution_dv.plural_forms
    2


export
------

This method serializes an IPOFile as a .po file.

Get a concrete POFile we know doesn't have a UTF-8 encoding.

    >>> from lp.translations.model.pofile import POFile
    >>> pofile = POFile.get(24)
    >>> print(pofile.header)
    Project-Id-Version: PACKAGE VERSION
    ...
    Content-Type: text/plain; charset=EUC-JP
    ...

Now, let's export it with its default encoding.

    >>> stream = pofile.export()
    >>> stream_list = stream.splitlines()

The header is not changed.

    >>> for i in range(len(stream_list)):
    ...     if stream_list[i].startswith(b'"Content-Type:'):
    ...         print(stream_list[i].decode("ASCII"))
    ...
    "Content-Type: text/plain; charset=EUC-JP\n"

And checking one of the translations, we can see that it's using the
EUC-JP encoding.

    >>> for i in range(len(stream_list)):
    ...     if (
    ...         stream_list[i].startswith(b"msgstr")
    ...         and b"prefs.js" in stream_list[i]
    ...     ):
    ...         break
    ...
    >>> print(stream_list[i].decode("EUC-JP"))
    msgstr "設定のカ...ズに /etc/mozilla/prefs.js が利用できます。"

Now, let's force the UTF-8 encoding.

    >>> stream = pofile.export(force_utf8=True)
    >>> stream_list = stream.splitlines()

We can see that the header has been updated to have UTF-8

    >>> for i in range(len(stream_list)):
    ...     if stream_list[i].startswith(b'"Content-Type:'):
    ...         print(stream_list[i].decode("ASCII"))
    ...
    "Content-Type: text/plain; charset=UTF-8\n"

And the encoding used is also using UTF-8 chars.

    >>> for i in range(len(stream_list)):
    ...     if (
    ...         stream_list[i].startswith(b"msgstr")
    ...         and b"prefs.js" in stream_list[i]
    ...     ):
    ...         break
    ...
    >>> print(stream_list[i].decode("UTF-8"))
    msgstr "設定のカ...ズに /etc/mozilla/prefs.js が利用できます。"

There are some situations when a msgid_plural changes, while the msgid
singular remains unchanged.

So for a concrete export, we have a message like:

    >>> pofile_es = potemplate.getPOFileByLang("es")
    >>> print(pofile_es.export(force_utf8=True).decode("utf8"))
    # ...
    ...
    #: addressbook/gui/widgets/foo.c:345
    #, c-format
    msgid "%d foo"
    msgid_plural "%d bars"
    msgstr[0] ""
    ...

When it changes...

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText("%d foo", "%d bars")

    # It has plural forms.

    >>> print(potmsgset.plural_text)
    %d bars

    # We change the plural form.

    >>> potmsgset.updatePluralForm("something else")
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> flush_database_updates()
    >>> print(potmsgset.plural_text)
    something else

...the export reflects that change.

    >>> print(pofile_es.export(force_utf8=True).decode("utf8"))
    # ...
    ...
    #: addressbook/gui/widgets/foo.c:345
    #, c-format
    msgid "%d foo"
    msgid_plural "something else"
    msgstr[0] ""
    ...


createMessageSetFromText
------------------------

This method returns a new IPOMsgSet for the associated text.

Let's get the IPOFile we are going to use for this test.

    >>> pofile_sr = potemplate.newPOFile("sr")

And the msgid we are looking for.

    >>> msgid = "Found %i invalid file."
    >>> msgid_plural = "Found %i invalid files."

Now, just to be sure that this entry doesn't exist yet:

    >>> potmsgset = pofile_sr.potemplate.getOrCreateSharedPOTMsgSet(
    ...     singular_text=msgid, plural_text=msgid_plural
    ... )
    >>> print(
    ...     potmsgset.getCurrentTranslation(
    ...         pofile_sr.potemplate,
    ...         pofile_sr.language,
    ...         pofile_sr.potemplate.translation_side,
    ...     )
    ... )
    None

Is time to create it.  We need some extra privileges here.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> login("carlos@canonical.com")
    >>> rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
    >>> translations = {0: ""}
    >>> is_current_upstream = False
    >>> lock_timestamp = datetime.now(timezone.utc)
    >>> translation_message = factory.makeCurrentTranslationMessage(
    ...     pofile_sr,
    ...     potmsgset,
    ...     rosetta_experts,
    ...     translations=translations,
    ...     current_other=is_current_upstream,
    ... )

As we can see, is the msgid we were looking for.

    >>> print(translation_message.potmsgset.msgid_singular.msgid)
    Found %i invalid file.

    >>> print(pofile_sr.language.code)
    sr

    >>> print(translation_message.language.code)
    sr

We created it without translations.

    >>> translation_message.translations
    [None, None, None]


People who contributed translations
-----------------------------------

The 'contributors' property of a POFile returns all the people who
contributed translations to it.

    >>> def print_names(persons):
    ...     """Print name for each of `persons`."""
    ...     for person in persons:
    ...         print(person.name)
    ...     print("--")
    ...

    >>> evolution = getUtility(IProductSet).getByName("evolution")
    >>> evolution_trunk = evolution.getSeries("trunk")
    >>> potemplatesubset = potemplateset.getSubset(
    ...     productseries=evolution_trunk
    ... )
    >>> evolution_template = potemplatesubset["evolution-2.2"]
    >>> evolution_es = evolution_template.getPOFileByLang("es")
    >>> print_names(evolution_es.contributors)
    carlos
    mark
    no-priv
    --

If you have a distroseries and want to know all the people who
contributed translations on a given language for that distroseries, you
can use the getPOFileContributorsByLanguage() method of IDistroSeries.

    >>> hoary = distribution.getSeries("hoary")
    >>> spanish = getUtility(ILanguageSet)["es"]
    >>> print_names(hoary.getPOFileContributorsByLanguage(spanish))
    jorge-gonzalez-gonzalez
    carlos
    valyag
    name16
    name12
    tsukimi
    --

    # We can see that there is another translator that doesn't appear in
    # previous list because the template they translated is not current.

    >>> non_current_pofile = POFile.get(31)
    >>> non_current_pofile.potemplate.iscurrent
    False

    >>> print_names(non_current_pofile.contributors)
    jordi
    --

    >>> non_current_pofile.potemplate.distroseries == hoary
    True

    >>> non_current_pofile.language == spanish
    True

The rosetta_experts team is special: it never shows up in contributors
lists.

    >>> experts_pofile = factory.makePOFile("nl")
    >>> experts_message = factory.makeCurrentTranslationMessage(
    ...     pofile=experts_pofile,
    ...     translator=rosetta_experts,
    ...     reviewer=rosetta_experts,
    ...     translations=["hi"],
    ... )

    >>> print_names(experts_pofile.contributors)
    --


getPOTMsgSetTranslated
----------------------

With this method we can get all POTMsgSet objects that are fully
translated for a given POFile.

    >>> def print_message_status(potmsgsets, pofile):
    ...     print(
    ...         "%-10s %-5s %-10s %-11s"
    ...         % ("msgid", "form", "translat.", "Has plurals")
    ...     )
    ...     for potmsgset in potmsgsets:
    ...         translationmessage = potmsgset.getCurrentTranslation(
    ...             pofile.potemplate,
    ...             pofile.language,
    ...             pofile.potemplate.translation_side,
    ...         )
    ...         msgid = potmsgset.msgid_singular.msgid
    ...         if len(msgid) > 10:
    ...             msgid = msgid[:7] + "..."
    ...         for index in range(len(translationmessage.translations)):
    ...             if translationmessage.translations[index] is None:
    ...                 translation = "None"
    ...             else:
    ...                 translation = translationmessage.translations[index]
    ...                 if len(translation) > 10:
    ...                     translation = translation[:7] + "..."
    ...             print(
    ...                 "%-10s %-5s %-10s %s"
    ...                 % (
    ...                     msgid,
    ...                     index,
    ...                     translation,
    ...                     potmsgset.msgid_plural is not None,
    ...                 )
    ...             )
    ...

    >>> potmsgsets_translated = evolution_es.getPOTMsgSetTranslated()
    >>> print_message_status(potmsgsets_translated, evolution_es)
    msgid      form  translat.  Has plurals
    evoluti... 0     libreta... False
    current... 0     carpeta... False
    have       0     tiene      False
     cards     0      tarjetas  False
    The loc... 0     La ubic... False
    %d contact 0     %d cont... True
    %d contact 1     %d cont... True
    Opening... 0     Abrir %... True
    Opening... 1     Abrir %... True
    EncFS P... 0     Contras... False


getTranslationsFilteredBy
-------------------------

This method returns a list of TranslationMessages in a given POFile
created by a certain person.

    >>> person_set = getUtility(IPersonSet)
    >>> carlos = person_set.getByName("carlos")
    >>> translationmessages = evolution_es.getTranslationsFilteredBy(carlos)
    >>> for translationmessage in translationmessages:
    ...     print(
    ...         pretty(removeSecurityProxy(translationmessage.translations))
    ...     )
    ...
    ['libreta de direcciones de Evolution']
    ['carpeta de libretas de direcciones actual']
    ['lalalala']
    ['tiene ']
    [' tarjetas']
    ['La ubicaci\xf3n y jerarqu\xeda de las carpetas de contactos de
    Evolution ha cambiado desde Evolution 1.x.\n\nTenga paciencia mientras
    Evolution migra sus carpetas...']
    ['%d contacto', '%d contactos']
    ['Abrir %d contacto abrir\xe1 %d ventanas nuevas tambi\xe9n.\n\xbfQuiere
    realmente mostrar este contacto?',
    'Abrir %d contactos abrir\xe1 %d ventanas nuevas tambi\xe9n.\n\xbfQuiere
    realmente mostrar todos estos contactos?']
    ['Contrase\xf1a de EncFS: ']

If the passed person is None, the call fails with an assertion.

    >>> translationmessages = evolution_es.getTranslationsFilteredBy(None)
    Traceback (most recent call last):
    ...
    AssertionError: You must provide a person to filter by.


Translation credits
-------------------

Translation credits are handled automatically, and cannot be
translated in any other way except through an upload from upstream.

Lets get Spanish translation for alsa-utils.

    >>> alsautils = getUtility(IProductSet).getByName("alsa-utils")
    >>> alsa_trunk = alsautils.getSeries("trunk")
    >>> alsa_template = alsa_trunk.getPOTemplate("alsa-utils")
    >>> alsa_translation = alsa_template.newPOFile("sr")

This translation file contains a translation-credits message. By default
it is created with a dummy translation

    >>> potmsgset = alsa_template.getPOTMsgSetByMsgIDText(
    ...     "translation-credits"
    ... )
    >>> current = potmsgset.getCurrentTranslation(
    ...     alsa_template,
    ...     alsa_translation.language,
    ...     alsa_template.translation_side,
    ... )
    >>> for translation in current.translations:
    ...     print(translation)
    ...
    This is a dummy translation so that the credits are counted as translated.

If we submit an upstream translation, the translation for this message
is updated.

    >>> new_credits = factory.makeCurrentTranslationMessage(
    ...     alsa_translation,
    ...     potmsgset,
    ...     alsa_translation.owner,
    ...     translations={0: "Happy translator"},
    ...     current_other=True,
    ... )
    >>> flush_database_updates()
    >>> current = potmsgset.getCurrentTranslation(
    ...     alsa_template,
    ...     alsa_translation.language,
    ...     alsa_template.translation_side,
    ... )
    >>> for translation in current.translations:
    ...     print(translation)
    ...
    Happy translator

If we submit non-upstream translation, it's rejected.

    >>> no_credits = potmsgset.submitSuggestion(
    ...     alsa_translation,
    ...     alsa_translation.owner,
    ...     {0: "Unhappy translator"},
    ... )
    >>> print(no_credits)
    None

    >>> flush_database_updates()
    >>> current = potmsgset.getCurrentTranslation(
    ...     alsa_template,
    ...     alsa_translation.language,
    ...     alsa_template.translation_side,
    ... )
    >>> for translation in current.translations:
    ...     print(translation)
    ...
    Happy translator


POFileToTranslationFileDataAdapter
----------------------------------

POFileToTranslationFileDataAdapter is an adapter to export a POFile
object. It implements the ITranslationFileData interface which is a
common file format in-memory to convert from one file format to another.

    >>> from lp.translations.interfaces.translationcommonformat import (
    ...     ITranslationFileData,
    ... )
    >>> evolution_sourcepackagename = sourcepackagenameset["evolution"]
    >>> ubuntu = distributionset["ubuntu"]
    >>> hoary = ubuntu["hoary"]
    >>> potemplatesubset = potemplateset.getSubset(
    ...     distroseries=hoary, sourcepackagename=evolution_sourcepackagename
    ... )
    >>> evolution_22 = potemplatesubset["evolution-2.2"]
    >>> evolution_ja = evolution_22.getPOFileByLang("ja")

Getting the translation file data is just a matter of adapting the
object to the ITranslationFileData interface. Since there are multiple
adapters for different purposes, this adapter is named.

    >>> from zope.component import getAdapter
    >>> translation_file_data = getAdapter(
    ...     evolution_ja, ITranslationFileData, "all_messages"
    ... )

We get an updated header based on some metadata in our database instead
of the imported one stored in POFile.header.

    >>> print(evolution_ja.header)
    Project-Id-Version: evolution
    Report-Msgid-Bugs-To: FULL NAME <EMAIL@ADDRESS>
    POT-Creation-Date: 2005-05-06 20:39:27.778946+00:00
    PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
    Last-Translator: FULL NAME <EMAIL@ADDRESS>
    Language-Team: Japanese <ja@li.org>
    MIME-Version: 1.0
    Content-Type: text/plain; charset=UTF-8
    Content-Transfer-Encoding: 8bit
    Plural-Forms: nplurals=1; plural=0

    >>> print(translation_file_data.header.getRawContent())
    Project-Id-Version: evolution
    Report-Msgid-Bugs-To: FULL NAME <EMAIL@ADDRESS>
    POT-Creation-Date: 2005-04-07 14:10+0200
    PO-Revision-Date: 2005-10-11 23:08+0000
    Last-Translator: Carlos Perell... <carlos@canonical.com>
    Language-Team: Japanese <ja@li.org>
    MIME-Version: 1.0
    Content-Type: text/plain; charset=UTF-8
    Content-Transfer-Encoding: 8bit
    Plural-Forms: nplurals=1; plural=0;
    X-Launchpad-Export-Date: ...-...-... ...:...+...
    X-Generator: Launchpad (build ...)

We can see that last translator is Carlos, just like the updated header
says:

    >>> print(backslashreplace(evolution_ja.lasttranslator.displayname))
    Carlos Perell\xf3 Mar\xedn

And the PO Revision Date matches when was the PO file last changed.

    >>> print(evolution_ja.date_changed)
    2005-10-11 23:08:01.899322+00:00


POFileToChangedFromPackagedAdapter
----------------------------------

Another adapter to the ITranslationFileData interface includes only
those messages that were changed from their packaged version. The class
is called POFileToChangedFromPackagedAdapter and it is registered as a
named adapter, too.

    >>> translation_file_data = getAdapter(
    ...     evolution_ja, ITranslationFileData, "changed_messages"
    ... )
    >>> ITranslationFileData.providedBy(translation_file_data)
    True


POFile Security tests
=====================

Import the function that will help us to do this test.

    >>> from lp.services.webapp.authorization import check_permission

A Launchpad admin must have permission to edit an IPOFile always.

    >>> login("foo.bar@canonical.com")
    >>> check_permission("launchpad.Edit", pofile)
    True

And a Rosetta Expert too.

    >>> login("jordi@ubuntu.com")
    >>> check_permission("launchpad.Edit", pofile)
    True

And that's all, folks!
