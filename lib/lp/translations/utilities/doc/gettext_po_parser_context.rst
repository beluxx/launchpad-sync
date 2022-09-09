Translation context
===================

GNU gettext 0.15 introduced a 'msgctxt' keyword, which allows defining
a string to be used as 'context disambiguator' when two messages have
identical msgids, but different meanings (are used in different "contexts"),
and they are usually translated differently.

Helper imports
--------------

    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.translations.model.potemplate import POTemplateSubset
    >>> import datetime
    >>> import pytz
    >>> UTC = pytz.timezone("UTC")

This is a function for importing a pofile or potemplate from a string,
printing out the import status after import is done.

    >>> from lp.translations.utilities.tests.helpers import (
    ...     import_pofile_or_potemplate,
    ... )

Import PO templates
-------------------

Login as an admin to be able to do changes to the import queue.

    >>> login("carlos@canonical.com")

We are creating a new potemplate for Firefox product.

    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> firefox_trunk = firefox.getSeries("trunk")
    >>> firefox_potsubset = POTemplateSubset(productseries=firefox_trunk)

Here's the person who'll be doing the import.

    >>> carlos = getUtility(IPersonSet).getByEmail("carlos@canonical.com")

And this is the POTemplate where the import will be done.

    >>> potemplate = firefox_potsubset.new(
    ...     name="firefox",
    ...     translation_domain="firefox",
    ...     path="po/firefox.pot",
    ...     owner=carlos,
    ... )

We've got a template with two pairs of messages with duplicated msgids.
In the first pair of messages, there is context added using 'msgctxt'
to only one, and in the second pair of messages, different context is
present on both messages (note that two messages with the same msgid,
where one contains a plural form and the other doesn't, are treated as
the same message in gettext, and we have to use msgctxt on one of them).

    >>> potemplate_contents = (
    ...     r"""
    ... msgid ""
    ... msgstr ""
    ... "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ... "Content-Type: text/plain; charset=CHARSET\n"
    ... "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n"
    ... "X-Launchpad-Export-Date: %s\n"
    ...
    ... msgid "bar"
    ... msgstr ""
    ...
    ... msgctxt "context"
    ... msgid "bar"
    ... msgstr ""
    ...
    ... #, c-format
    ... msgctxt "First message"
    ... msgid "%%d file"
    ... msgstr ""
    ...
    ... # This message has the same msgid as the one above, but it's a plural
    ... # form message which gettext treats as the same if no context is added
    ... #, c-format
    ... msgctxt "Second message"
    ... msgid "%%d file"
    ... msgid_plural "%%d files"
    ... msgstr[0] ""
    ... msgstr[1] ""
    ... """
    ...     % datetime.datetime.now(UTC).isoformat()
    ... ).encode(
    ...     "UTF-8"
    ... )  # noqa

This file can now be correctly imported:

    >>> entry = import_pofile_or_potemplate(
    ...     potemplate_contents, carlos, potemplate=potemplate
    ... )
    >>> print(entry.status.name)
    IMPORTED
    >>> flush_database_caches()  # replace date SQL constant with real date

The method getPOTMsgSetByMsgIDText returns a message without context if
no context is specified.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText("bar")
    >>> print(potmsgset.singular_text)
    bar
    >>> print(potmsgset.context)
    None

And if all the messages have a context, getPOTMsgSetByMsgIDText returns
nothing when context is not specified.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText("%d file")
    >>> print(potmsgset)
    None

To get a message with a context, we pass a context parameter.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText(
    ...     "bar", context="context"
    ... )
    >>> print(potmsgset.singular_text)
    bar
    >>> print(potmsgset.context)
    context

It also works for plural form messages.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText(
    ...     "%d file", context="First message"
    ... )
    >>> print(potmsgset.singular_text)
    %d file
    >>> print(potmsgset.context)
    First message
    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText(
    ...     "%d file", "%d files", context="Second message"
    ... )
    >>> print(potmsgset.singular_text)
    %d file
    >>> print(potmsgset.context)
    Second message

Importing a PO template with two messages with identical strings, but no
context differences fails.

    >>> potemplate_contents = (
    ...     r"""
    ... msgid ""
    ... msgstr ""
    ... "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ... "Content-Type: text/plain; charset=CHARSET\n"
    ... "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n"
    ... "X-Launchpad-Export-Date: %s\n"
    ...
    ... msgctxt "context"
    ... msgid "bar"
    ... msgstr ""
    ...
    ... msgctxt "context"
    ... msgid "bar"
    ... msgstr ""
    ... """
    ...     % datetime.datetime.now(UTC).isoformat()
    ... ).encode("UTF-8")

Importing this file fails because of conflicting messages.

    >>> entry = import_pofile_or_potemplate(
    ...     potemplate_contents, carlos, potemplate=potemplate
    ... )
    INFO We got an error import...
    ...duplicate msgid...
    >>> print(entry.status.name)
    FAILED

Importing PO files
------------------

We can also import POFile with context messages.

    >>> pofile = potemplate.newPOFile("sr")
    >>> pofile.path = "sr.po"
    >>> pofile_contents = (
    ...     r"""
    ... msgid ""
    ... msgstr ""
    ... "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ... "Content-Type: text/plain; charset=CHARSET\n"
    ... "Language: Serbian\n"
    ... "Plural-Forms: nplurals=3; plural=(n%%10==1 && n%%100!=11 ? 0 : n%%10>=2 && n%%10<=4 && (n%%100<10 || n%%100>=20) ? 1 : 2);\n"
    ... "X-Launchpad-Export-Date: %s\n"
    ...
    ... msgid "bar"
    ... msgstr "bar with no context"
    ...
    ... msgctxt "context"
    ... msgid "bar"
    ... msgstr "bar with context"
    ...
    ... #, c-format
    ... msgctxt "First message"
    ... msgid "%%d file"
    ... msgstr "Translation %%d"
    ...
    ... #, c-format
    ... msgctxt "Second message"
    ... msgid "%%d file"
    ... msgid_plural "%%d files"
    ... msgstr[0] "%%d translation"
    ... msgstr[1] "%%d translationes"
    ... msgstr[2] "%%d translations"
    ... """
    ...     % datetime.datetime.now(UTC).isoformat()
    ... ).encode(
    ...     "UTF-8"
    ... )  # noqa

Importing this file succeeds.

    >>> entry = import_pofile_or_potemplate(
    ...     pofile_contents, carlos, pofile=pofile
    ... )
    >>> print(entry.status.name)
    IMPORTED
    >>> flush_database_caches()  # replace date SQL constant with real date

If we don't pass context to POFile.getPOMsgSet method, we get the translation
for the message without a context.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText("bar")
    >>> current = potmsgset.getCurrentTranslation(
    ...     potemplate, pofile.language, potemplate.translation_side
    ... )
    >>> print(pretty(current.translations))
    ['bar with no context']

If we pass the context parameter to getPOMsgSet, we get the translation for
a message with context.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText(
    ...     "bar", context="context"
    ... )
    >>> current = potmsgset.getCurrentTranslation(
    ...     potemplate, pofile.language, potemplate.translation_side
    ... )
    >>> print(pretty(current.translations))
    ['bar with context']

If message has a context, you cannot get it without specifying the context:

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText("%file")
    >>> print(potmsgset)
    None

If you specify context, it actually works.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText(
    ...     "%d file", context="First message"
    ... )
    >>> current = potmsgset.getCurrentTranslation(
    ...     potemplate, pofile.language, potemplate.translation_side
    ... )
    >>> print(pretty(current.translations))
    ['Translation %d']

And for messages with plural forms, it gets all the translations.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText(
    ...     "%d file", "%d files", context="Second message"
    ... )
    >>> current = potmsgset.getCurrentTranslation(
    ...     potemplate, pofile.language, potemplate.translation_side
    ... )
    >>> print(pretty(current.translations))
    ['%d translation', '%d translationes', '%d translations']

Export
------

Make sure exported files are correct.  Exporting a POT file returns exactly
the same contents, except that header is marked fuzzy.

    >>> print(potemplate.export().decode("UTF-8"))
    #, fuzzy
    msgid ""
    msgstr ""
    "Project-Id-Version: PACKAGE VERSION\n"
    "Report-Msgid-Bugs-To: \n"
    "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    "PO-Revision-Date: ...-...-... ...:...+...\n"
    "Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
    "Language-Team: LANGUAGE <LL@li.org>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n"
    "X-Launchpad-Export-Date: ...-...-... ...:...+...\n"
    "X-Generator: Launchpad (build ...)\n"
    <BLANKLINE>
    msgid "bar"
    msgstr ""
    <BLANKLINE>
    msgctxt "context"
    msgid "bar"
    msgstr ""
    <BLANKLINE>
    #, c-format
    msgctxt "First message"
    msgid "%d file"
    msgstr ""
    <BLANKLINE>
    # This message has the same msgid as the one above, but it's a plural
    # form message which gettext treats as the same if no context is added
    #, c-format
    msgctxt "Second message"
    msgid "%d file"
    msgid_plural "%d files"
    msgstr[0] ""
    msgstr[1] ""

And a Serbian PO file is exported using regular export_pofile call.
It's different from the imported file only in a few headers.

    >>> pofile = potemplate.getPOFileByLang("sr")
    >>> print(pofile.export().decode("UTF-8"))
    msgid ""
    msgstr ""
    "Project-Id-Version: PACKAGE VERSION\n"
    "Report-Msgid-Bugs-To: \n"
    "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    "PO-Revision-Date: ...\n"
    "Last-Translator: Carlos...\n"
    "Language-Team: LANGUAGE <LL@li.org>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Plural-Forms: nplurals=3; plural=n%10==1 && n%100!=11 ? 0 : n%10>=2 && "
    "n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2;\n"
    "X-Launchpad-Export-Date: ...\n"
    "X-Generator: Launchpad (build ...)\n"
    "Language: Serbian\n"
    <BLANKLINE>
    msgid "bar"
    msgstr "bar with no context"
    <BLANKLINE>
    msgctxt "context"
    msgid "bar"
    msgstr "bar with context"
    <BLANKLINE>
    #, c-format
    msgctxt "First message"
    msgid "%d file"
    msgstr "Translation %d"
    <BLANKLINE>
    #, c-format
    msgctxt "Second message"
    msgid "%d file"
    msgid_plural "%d files"
    msgstr[0] "%d translation"
    msgstr[1] "%d translationes"
    msgstr[2] "%d translations"

Edge cases
----------

Messages with empty context
...........................

Messages without msgctxt keyword and with empty value for msgctxt are
not same.

    >>> potemplate_contents = (
    ...     r"""
    ... msgid ""
    ... msgstr ""
    ... "POT-Creation-Date: 2004-07-11 16:16+0900\n"
    ... "Content-Type: text/plain; charset=CHARSET\n"
    ... "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n"
    ... "X-Launchpad-Export-Date: %s\n"
    ...
    ... msgid "bar"
    ... msgstr ""
    ...
    ... msgctxt ""
    ... msgid "bar"
    ... msgstr ""
    ... """
    ...     % datetime.datetime.now(UTC).isoformat()
    ... ).encode("UTF-8")

This file can now be correctly imported:

    >>> entry = import_pofile_or_potemplate(
    ...     potemplate_contents, carlos, potemplate=potemplate
    ... )
    >>> print(entry.status.name)
    IMPORTED
    >>> flush_database_caches()  # replace date SQL constant with real date

The method getPOTMsgSetByMsgIDText returns a message without context if
no context is specified.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText("bar")
    >>> print(potmsgset.singular_text)
    bar
    >>> print(potmsgset.context)
    None

The method getPOTMsgSetByMsgIDText returns a message with empty context
if empty context is specified, and not the message with None context.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText("bar", context="")
    >>> print(potmsgset.singular_text)
    bar
    >>> print(potmsgset.context)
    <BLANKLINE>
