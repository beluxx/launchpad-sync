Legacy KDE PO file format
=========================

KDE versions before 4.0 used regular PO files with translatable
strings and their translations specially formatted to accommodate
features that were introduced in GNU gettext PO files later.

Such features include plural forms support and context support.

Helper imports
--------------

    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.translations.interfaces.translationfileformat import (
    ...     TranslationFileFormat,
    ... )
    >>> from lp.translations.model.potemplate import POTemplateSubset
    >>> import datetime
    >>> import pytz
    >>> UTC = pytz.timezone("UTC")
    >>> ISO_FORMATTED_DATE = datetime.datetime.now(UTC).isoformat()

To ease the pain of importing many files during testing, we use this
helper function to import either a PO file or a PO template from the
string with the contents of the file.

    >>> from lp.translations.utilities.tests.helpers import (
    ...     import_pofile_or_potemplate,
    ... )

We'll be doing all our imports into Firefox trunk as
carlos@canonical.com.

    >>> carlos = getUtility(IPersonSet).getByEmail("carlos@canonical.com")
    >>> login("carlos@canonical.com")

    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> firefox_trunk = firefox.getSeries("trunk")
    >>> firefox_potsubset = POTemplateSubset(productseries=firefox_trunk)

    >>> firefox_potemplate = firefox_potsubset.new(
    ...     name="firefox",
    ...     translation_domain="firefox",
    ...     path="po/firefox.pot",
    ...     owner=carlos,
    ... )

Non-KDE PO file detection
-------------------------

Our KDE PO support is built on top of existing gettext support.  As
such, it has precedence in handling any PO files, but it correctly
sets the format to regular PO if it's not a KDE style file.

    >>> non_kde_template = (
    ...     r"""
    ... msgid ""
    ... msgstr ""
    ... "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ... "Content-Type: text/plain; charset=CHARSET\n"
    ... "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n"
    ... "X-Launchpad-Export-Date: %s\n"
    ...
    ... msgid "foo"
    ... msgstr ""
    ... """
    ...     % ISO_FORMATTED_DATE
    ... ).encode("UTF-8")

Importing this file works, but the format is set to Gettext PO.

    >>> entry = import_pofile_or_potemplate(
    ...     non_kde_template, carlos, potemplate=firefox_potemplate
    ... )
    >>> print(entry.status.name)
    IMPORTED
    >>> flush_database_caches()
    >>> print(entry.format.title)
    PO format

Plural forms support
--------------------

Import
......

Plural forms are supported by using a specially formatted msgid where
English singular and plural are split with a newline, and the entire
message is preceded with '_n: ' (space at the end of the string is important).

    >>> plural_forms_template = (
    ...     r"""
    ... msgid ""
    ... msgstr ""
    ... "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ... "Content-Type: text/plain; charset=CHARSET\n"
    ... "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n"
    ... "X-Launchpad-Export-Date: %s\n"
    ...
    ... # This is not considered a plural forms message because
    ... # of a missing space in '_n:'.
    ... msgid "_n:bar\nbars"
    ... msgstr ""
    ...
    ... # "c-format" flag enforces printf-specifiers checking, so we use that
    ... # to make sure import doesn't fail on a differing number of specifiers
    ... # in a msgid and in a msgstr.
    ... #, c-format
    ... msgid "_n: %%d foo\n%%d foos"
    ... msgstr ""
    ...
    ... # Legacy KDE PO files allow two messages with same singular message
    ... # ID, but different or no plural to exist, what is otherwise not
    ... # allowed by standard gettext support.
    ... #, c-format
    ... msgid "%%d foo"
    ... msgstr ""
    ...
    ... #, c-format
    ... msgid "_n: %%d foo\n%%d bars"
    ... msgstr ""
    ...
    ... msgid "_n: entry\nentries"
    ... msgstr ""
    ... """
    ...     % ISO_FORMATTED_DATE
    ... ).encode(
    ...     "UTF-8"
    ... )  # noqa

And strangely, importing this file actually works, and format is changed
to KDE PO format.

    >>> entry = import_pofile_or_potemplate(
    ...     plural_forms_template, carlos, potemplate=firefox_potemplate
    ... )
    >>> print(entry.status.name)
    IMPORTED
    >>> flush_database_caches()
    >>> print(entry.format.title)
    KDE PO format

Messages which are preceded with just '_n:' and no space after it are
not considered plural forms messages.

    >>> potmsgset = firefox_potemplate.getPOTMsgSetByMsgIDText("_n:bar\nbars")
    >>> print(potmsgset.singular_text)
    _n:bar
    bars
    >>> print(potmsgset.plural_text)
    None

Proper format in messages is to use '_n: ' and separate singular and
plural with a newline.

    >>> potmsgset = firefox_potemplate.getPOTMsgSetByMsgIDText(
    ...     "%d foo", plural_text="%d foos"
    ... )
    >>> print(potmsgset.singular_text)
    %d foo
    >>> print(potmsgset.plural_text)
    %d foos

To get a non-plural message, we can either not specify plural_text or
set it as None:

    >>> potmsgset = firefox_potemplate.getPOTMsgSetByMsgIDText(
    ...     "%d foo", plural_text=None
    ... )
    >>> print(potmsgset.singular_text)
    %d foo
    >>> print(potmsgset.plural_text)
    None

For translations, a specially formatted msgstr is used to hold all plural
forms. They are simply newline-separated strings.

    >>> firefox_serbian_pofile = firefox_potemplate.newPOFile("sr")
    >>> firefox_serbian_pofile.path = "sr.po"
    >>> firefox_serbian_pofile_contents = (
    ...     r"""
    ... msgid ""
    ... msgstr ""
    ... "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ... "Content-Type: text/plain; charset=CHARSET\n"
    ... "Language: Serbian\n"
    ... "Plural-Forms: nplurals=3; plural=(n%%10==1 && n%%100!=11 ? 0 : "
    ... "n%%10>=2 && n%%10<=4 && (n%%100<10 || n%%100>=20) ? 1 : 2);\n"
    ... "X-Launchpad-Export-Date: %s\n"
    ...
    ... # This is not considered a plural forms message because
    ... # of a missing space in '_n:'.
    ... msgid "_n:bar\nbars"
    ... msgstr "non-plural forms message"
    ...
    ... # "c-format" flag enforces printf-specifiers checking, so we use that
    ... # to make sure import doesn't fail on a differing number of specifiers
    ... # in a msgid and in a msgstr.
    ... #, c-format
    ... msgid "_n: %%d foo\n%%d foos"
    ... msgstr "%%d translation\n%%d translationes\n%%d translations"
    ...
    ... # Legacy KDE PO files allow multiple messages with the same
    ... # singular msgid.
    ... msgid "%%d foo"
    ... msgstr "no-plural translation %%d"
    ...
    ... # This translation is incomplete, since it fails to provide
    ... # translations for the second plural form.
    ... msgid "_n: entry\nentries"
    ... msgstr "singular entry\n\nplural entries"
    ...
    ... """
    ...     % ISO_FORMATTED_DATE
    ... ).encode(
    ...     "UTF-8"
    ... )  # noqa

Importing this file succeeds, even if the number of %d printf specifications
doesn't match: this is because this is now specially handled with KDE PO
format support.

    >>> entry = import_pofile_or_potemplate(
    ...     firefox_serbian_pofile_contents,
    ...     carlos,
    ...     pofile=firefox_serbian_pofile,
    ... )
    >>> print(entry.status.name)
    IMPORTED
    >>> flush_database_caches()
    >>> print(entry.format.title)
    KDE PO format

Non-KDE style messages get their translations in the usual way.

    >>> potmsgset = firefox_potemplate.getPOTMsgSetByMsgIDText(
    ...     singular_text="_n:bar\nbars"
    ... )
    >>> current = potmsgset.getCurrentTranslation(
    ...     firefox_potemplate,
    ...     firefox_serbian_pofile.language,
    ...     firefox_potemplate.translation_side,
    ... )
    >>> for translation in current.translations:
    ...     print(translation)
    ...
    non-plural forms message

While KDE style plural form message is correctly split into three separate
plural messages:

    >>> potmsgset = firefox_potemplate.getPOTMsgSetByMsgIDText(
    ...     singular_text="%d foo", plural_text="%d foos"
    ... )
    >>> current = potmsgset.getCurrentTranslation(
    ...     firefox_potemplate,
    ...     firefox_serbian_pofile.language,
    ...     firefox_potemplate.translation_side,
    ... )
    >>> for translation in current.translations:
    ...     print(translation)
    ...
    %d translation
    %d translationes
    %d translations

Export
......

Let's define a helper function for the exports.

    >>> from zope.component import getAdapter
    >>> def export_with_format(translation_file, format):
    ...     from lp.translations.interfaces.translationexporter import (
    ...         ITranslationExporter,
    ...     )
    ...     from lp.translations.interfaces.translationcommonformat import (
    ...         ITranslationFileData,
    ...     )
    ...
    ...     translation_exporter = getUtility(ITranslationExporter)
    ...     requested_file = getAdapter(
    ...         translation_file, ITranslationFileData, "all_messages"
    ...     )
    ...     exported_file = translation_exporter.exportTranslationFiles(
    ...         [requested_file], target_format=format
    ...     )
    ...     return exported_file.read()
    ...

Make sure all the date constants are replaced with real values in database:

    >>> flush_database_caches()

Template export turns it back into a KDE-style PO file:

    >>> print(
    ...     export_with_format(
    ...         firefox_potemplate, TranslationFileFormat.KDEPO
    ...     ).decode("UTF-8")
    ... )
    #, fuzzy
    msgid ""
    msgstr ""
    ...
    "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ...
    "Content-Type: text/plain; charset=UTF-8\n"
    ...
    "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n"
    ...
    <BLANKLINE>
    # This is not considered a plural forms message because
    # of a missing space in '_n:'.
    msgid ""
    "_n:bar\n"
    "bars"
    msgstr ""
    <BLANKLINE>
    # "c-format" flag enforces printf-specifiers checking, so we use that
    # to make sure import doesn't fail on a differing number of specifiers
    # in a msgid and in a msgstr.
    #, c-format
    msgid ""
    "_n: %d foo\n"
    "%d foos"
    msgstr ""
    <BLANKLINE>
    # Legacy KDE PO files allow two messages with same singular message
    # ID, but different or no plural to exist, what is otherwise not
    # allowed by standard gettext support.
    #, c-format
    msgid "%d foo"
    msgstr ""
    <BLANKLINE>
    #, c-format
    msgid ""
    "_n: %d foo\n"
    "%d bars"
    msgstr ""
    <BLANKLINE>
    msgid ""
    "_n: entry\n"
    "entries"
    msgstr ""

But, we can also export it as a regular gettext PO file.  This format
does not support messages that are identical in all but the plural, so
those are stripped out.

    >>> print(
    ...     export_with_format(
    ...         firefox_potemplate, TranslationFileFormat.PO
    ...     ).decode("UTF-8")
    ... )
    #, fuzzy
    msgid ""
    msgstr ""
    ...
    "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ...
    "Content-Type: text/plain; charset=UTF-8\n"
    ...
    "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n"
    ...
    <BLANKLINE>
    # This is not considered a plural forms message because
    # of a missing space in '_n:'.
    msgid ""
    "_n:bar\n"
    "bars"
    msgstr ""
    <BLANKLINE>
    # "c-format" flag enforces printf-specifiers checking, so we use that
    # to make sure import doesn't fail on a differing number of specifiers
    # in a msgid and in a msgstr.
    #, c-format
    msgid "%d foo"
    msgid_plural "%d foos"
    msgstr[0] ""
    msgstr[1] ""
    <BLANKLINE>
    msgid "entry"
    msgid_plural "entries"
    msgstr[0] ""
    msgstr[1] ""

Exporting a translation is possible in a very similar way.

    >>> print(firefox_serbian_pofile.export().decode("utf8"))
    msgid ""
    msgstr ""
    ...
    "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ...
    "Content-Type: text/plain; charset=UTF-8\n"
    ...
    "Plural-Forms: ...
    ...
    <BLANKLINE>
    # This is not considered a plural forms message because
    # of a missing space in '_n:'.
    msgid ""
    "_n:bar\n"
    "bars"
    msgstr "non-plural forms message"
    <BLANKLINE>
    # "c-format" flag enforces printf-specifiers checking, so we use that
    # to make sure import doesn't fail on a differing number of specifiers
    # in a msgid and in a msgstr.
    #, c-format
    msgid ""
    "_n: %d foo\n"
    "%d foos"
    msgstr ""
    "%d translation\n"
    "%d translationes\n"
    "%d translations"
    <BLANKLINE>
    # Legacy KDE PO files allow multiple messages with the same
    # singular msgid.
    #, c-format
    msgid "%d foo"
    msgstr "no-plural translation %d"
    <BLANKLINE>
    #, c-format
    msgid ""
    "_n: %d foo\n"
    "%d bars"
    msgstr ""
    <BLANKLINE>
    # This translation is incomplete, since it fails to provide
    # translations for the second plural form.
    msgid ""
    "_n: entry\n"
    "entries"
    msgstr ""
    "singular entry\n"
    "\n"
    "plural entries"


Context support
---------------

Message context is supported in legacy KDE PO files using a specially
formatted msgid: context is preceded with a string '_: ', and split with
a new line from the rest of the message.

Import
......

We can have a template with a message with context.

    >>> kde_context_template = (
    ...     r"""
    ... msgid ""
    ... msgstr ""
    ... "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ... "Content-Type: text/plain; charset=CHARSET\n"
    ... "X-Launchpad-Export-Date: %s\n"
    ...
    ... msgid "_: Context\nMessage"
    ... msgstr ""
    ...
    ... msgid "_: Different Context\nMessage"
    ... msgstr ""
    ... """
    ...     % ISO_FORMATTED_DATE
    ... ).encode("UTF-8")

Importing this template works and the format is recognized as a KDE PO format.

    >>> entry = import_pofile_or_potemplate(
    ...     kde_context_template, carlos, potemplate=firefox_potemplate
    ... )
    >>> print(entry.status.name)
    IMPORTED
    >>> flush_database_caches()
    >>> print(entry.format.title)
    KDE PO format

Message with context is properly split into msgid and context fields.

    >>> potmsgset = firefox_potemplate.getPOTMsgSetByMsgIDText(
    ...     "Message", context="Context"
    ... )
    >>> print(potmsgset.singular_text)
    Message
    >>> print(potmsgset.context)
    Context

If we ask for a message without specifying context, we get no results:

    >>> potmsgset = firefox_potemplate.getPOTMsgSetByMsgIDText("Message")
    >>> print(potmsgset)
    None

We can also import a translated file with message contexts:

    >>> kde_context_translation = (
    ...     r"""
    ... msgid ""
    ... msgstr ""
    ... "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ... "Content-Type: text/plain; charset=CHARSET\n"
    ... "X-Launchpad-Export-Date: %s\n"
    ...
    ... msgid "_: Context\nMessage"
    ... msgstr "First translation"
    ...
    ... msgid "_: Different Context\nMessage"
    ... msgstr "Second translation"
    ... """
    ...     % ISO_FORMATTED_DATE
    ... ).encode("UTF-8")
    >>> entry = import_pofile_or_potemplate(
    ...     kde_context_translation, carlos, pofile=firefox_serbian_pofile
    ... )
    >>> print(entry.status.name)
    IMPORTED
    >>> flush_database_caches()
    >>> print(entry.format.title)
    KDE PO format


We can get the first translation by specifying 'Context' for the context:

    >>> potmsgset = firefox_potemplate.getPOTMsgSetByMsgIDText(
    ...     singular_text="Message", context="Context"
    ... )
    >>> current = potmsgset.getCurrentTranslation(
    ...     firefox_potemplate,
    ...     firefox_serbian_pofile.language,
    ...     firefox_potemplate.translation_side,
    ... )
    >>> for translation in current.translations:
    ...     print(translation)
    ...
    First translation

And if we ask for a message with context 'Different Context', we get the
other message and its translation:

    >>> potmsgset = firefox_potemplate.getPOTMsgSetByMsgIDText(
    ...     singular_text="Message", context="Different Context"
    ... )
    >>> current = potmsgset.getCurrentTranslation(
    ...     firefox_potemplate,
    ...     firefox_serbian_pofile.language,
    ...     firefox_potemplate.translation_side,
    ... )
    >>> for translation in current.translations:
    ...     print(translation)
    ...
    Second translation

Export
......

Exporting a PO template as a KDE PO file joins the context back together:

    >>> print(
    ...     export_with_format(
    ...         firefox_potemplate, TranslationFileFormat.KDEPO
    ...     ).decode("UTF-8")
    ... )
    #, fuzzy
    msgid ""
    msgstr ""
    ...
    "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ...
    "Content-Type: text/plain; charset=UTF-8\n"
    ...
    <BLANKLINE>
    msgid ""
    "_: Context\n"
    "Message"
    msgstr ""
    <BLANKLINE>
    msgid ""
    "_: Different Context\n"
    "Message"
    msgstr ""

And the same happens with a translation:

    >>> print(firefox_serbian_pofile.export().decode("utf8"))
    msgid ""
    msgstr ""
    ...
    "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ...
    "Content-Type: text/plain; charset=UTF-8\n"
    ...
    <BLANKLINE>
    msgid ""
    "_: Context\n"
    "Message"
    msgstr "First translation"
    <BLANKLINE>
    msgid ""
    "_: Different Context\n"
    "Message"
    msgstr "Second translation"
    ...
