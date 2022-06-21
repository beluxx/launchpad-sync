PO Import test with a .po file that has a syntax error
======================================================

When we import a .po file with a syntax error, we should notify the user
about that error so they have a chance to fix it.

In this test, we are going to check that we detect and notify the error.

Here are some imports we need to get this test running.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue)
    >>> from lp.translations.model.potemplate import POTemplateSubset
    >>> import datetime
    >>> import pytz
    >>> UTC = pytz.timezone('UTC')
    >>> translation_import_queue = getUtility(ITranslationImportQueue)
    >>> rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts

We need this for the Librarian to work properly.

    >>> import transaction

And also, the DBSchema to change the imports status

    >>> from lp.translations.enums import RosettaImportStatus

Login as an admin to be able to do changes to the import queue.

    >>> login('carlos@canonical.com')

Here's the person who'll be doing the import.

    >>> person_set = getUtility(IPersonSet)
    >>> person = person_set.getByName('mark')

Now, is time to create the new potemplate

    >>> from lp.registry.model.productrelease import ProductRelease
    >>> release = ProductRelease.get(3)
    >>> print(release.milestone.productseries.product.name)
    firefox

    >>> series = release.milestone.productseries
    >>> subset = POTemplateSubset(productseries=series)
    >>> potemplate = subset.new(
    ...     name='firefox',
    ...     translation_domain='firefox',
    ...     path='po/firefox.pot',
    ...     owner=person)

We create the POFile object where we are going to attach the .po file.

    >>> pofile = potemplate.newPOFile('cy')

Let's import a .po file that misses the '"' char after msgstr. That's a
syntax error.

    >>> pofile_contents = six.ensure_binary(r'''
    ... msgid ""
    ... msgstr ""
    ... "PO-Revision-Date: 2005-06-03 20:41+0100\n"
    ... "Last-Translator: Foo <no-priv@canonical.com>\n"
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ... "Plural-Forms: nplurals=4; plural=n==1) "
    ...     "? 0 : n==2 ? 1 : (n != 8 || n != 11) ? 2 : 3;\n"
    ... "X-Rosetta-Export-Date: %s\n"
    ... 
    ... msgid "foo"
    ... msgstr blah"
    ... ''' % datetime.datetime.now(UTC).isoformat())
    >>> by_maintainer = False
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, by_maintainer, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()

We must approve the entry to be able to import it.

    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)

The import fails.

    >>> (subject, message) = pofile.importFromQueue(entry)
    >>> print(entry.status.name)
    FAILED

    >>> print(entry.error_output)
    Line 12: String is not quoted

And the code composed an email with the notification of the error.

    >>> print(subject)
    Import problem - Welsh (cy) - firefox in Mozilla Firefox trunk

    >>> print(message)
    Hello Mark Shuttleworth,
    <BLANKLINE>
    On ..., you uploaded a file with Welsh (cy) translations for firefox in
    Mozilla Firefox trunk to Launchpad.
    <BLANKLINE>
    We were unable to import the file because of errors in its format:
    <BLANKLINE>
    Line 12: String is not quoted
    <BLANKLINE>
    If you use gettext, you can check your file for correct formatting with
    the 'msgfmt -c' command.
    Please fix any errors raised by msgfmt and upload the file again. If you
    check the file and you don't find any error in it, please look for an
    answer or file a question at https://answers.launchpad.net/rosetta/
    <BLANKLINE>
    For your convenience, you can get the file you uploaded at:
    http://.../firefox-cy.po
    <BLANKLINE>
    Thank you,
    <BLANKLINE>
    The Launchpad team
    <BLANKLINE>


Encoding errors
---------------

Encoding problems are similarly reported, but with a different
explanatory text.

    >>> pofile = potemplate.newPOFile('fy')
    >>> pofile_contents = u'''
    ... msgid ""
    ... msgstr ""
    ... "Content-Type: text/plain; charset=ASCII\\n"
    ... "X-Rosetta-Export-Date: 2009-07-13 00:00+0700\\n"
    ... 
    ... msgid "\xa9 Yoyodine Industries"
    ... msgstr ""
    ... '''.encode('utf-8')
    >>> by_maintainer = False
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, by_maintainer, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> transaction.commit()
    >>> (subject, message) = pofile.importFromQueue(entry)
    >>> print(entry.status.name)
    FAILED

An email describes the problem in relatively helpful terms.

    >>> print(subject)
    Import problem - Frisian (fy) - firefox in Mozilla Firefox trunk

    >>> print(message)
    Hello Mark Shuttleworth,
    <BLANKLINE>
    On ..., you uploaded a file with Frisian (fy) translations for
    firefox in Mozilla Firefox trunk to Launchpad.
    <BLANKLINE>
    The file could not be imported because of text encoding problems.
    This may indicate that the file does not specify the correct
    encoding, or that it contains garbled or truncated text data.
    <BLANKLINE>
    The specific error message was:
    <BLANKLINE>
    'ascii' codec can't decode byte ... in position ...: ordinal not in
    range(128)
    <BLANKLINE>
    For your convenience, you can find the file you uploaded at: ...
    <BLANKLINE>
    Thank you,
    <BLANKLINE>
    The Launchpad team
    <BLANKLINE>

The error output field is more terse.

    >>> print(entry.error_output)
    'ascii' codec can't decode byte ... in position ...: ordinal not in
    range(128)


Invalid numbers of plural forms
-------------------------------

Some uploads declare impossible numbers of plural forms.  Those uploads
are rejected.


Non-numeric plural forms
........................

In his rush to be the first Sumerian translator for Firefox, Mark
submits a translation with a nonsensical plurals definition.

    >>> pofile = potemplate.newPOFile('sux')
    >>> pofile_contents = six.ensure_binary(r'''
    ... msgid ""
    ... msgstr ""
    ... "PO-Revision-Date: 2005-06-29 11:44+0100\n"
    ... "Last-Translator: Foo <no-priv@canonical.com>\n"
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ... "Plural-Forms: nplurals=n; plural=0\n"
    ... "X-Rosetta-Export-Date: %s\n"
    ... 
    ... msgid "foo"
    ... msgstr "bar"
    ... ''' % datetime.datetime.now(UTC).isoformat())
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, False, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> (subject, message) = pofile.importFromQueue(entry)

The submission is rejected with a syntax error.

    >>> print(entry.status.name)
    FAILED

    >>> print(subject)
    Import problem - Sumerian (sux) - firefox in Mozilla Firefox trunk

    >>> print(message)
    Hello Mark Shuttleworth,
    ...
    <BLANKLINE>
    We were unable to import the file because of errors in its format:
    <BLANKLINE>
    Invalid nplurals declaration in header: 'n' (should be a number).
    <BLANKLINE>
    ...


Not enough forms
................

Mark mistakenly attempts to import a translation with "zero" plural
forms.  He receives an email notifying him of a syntax error.

    >>> pofile_contents = six.ensure_binary(r'''
    ... msgid ""
    ... msgstr ""
    ... "PO-Revision-Date: 2005-06-14 18:33+0100\n"
    ... "Last-Translator: Foo <no-priv@canonical.com>\n"
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ... "Plural-Forms: nplurals=0; plural=0\n"
    ... "X-Rosetta-Export-Date: %s\n"
    ... 
    ... msgid "foo"
    ... msgstr "bar"
    ... ''' % datetime.datetime.now(UTC).isoformat())
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, False, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> (subject, message) = pofile.importFromQueue(entry)

    >>> print(entry.status.name)
    FAILED

    >>> print(subject)
    Import problem - Sumerian (sux) - firefox in Mozilla Firefox trunk

    >>> print(message)
    Hello Mark Shuttleworth,
    ...
    <BLANKLINE>
    We were unable to import the file because of errors in its format:
    <BLANKLINE>
    Number of plural forms is impossibly low.
    <BLANKLINE>
    ...

On his next attempt, Mark accidentally types a negative number of plural
forms.  The same error is given.

    >>> pofile_contents = six.ensure_binary(r'''
    ... msgid ""
    ... msgstr ""
    ... "PO-Revision-Date: 2005-06-15 19:04+0100\n"
    ... "Last-Translator: Foo <no-priv@canonical.com>\n"
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ... "Plural-Forms: nplurals=-1; plural=0\n"
    ... "X-Rosetta-Export-Date: %s\n"
    ... 
    ... msgid "foo"
    ... msgstr "bar"
    ... ''' % datetime.datetime.now(UTC).isoformat())
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, False, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> (subject, message) = pofile.importFromQueue(entry)

    >>> print(entry.status.name)
    FAILED

    >>> print(subject)
    Import problem - Sumerian (sux) - firefox in Mozilla Firefox trunk

    >>> print(message)
    Hello Mark Shuttleworth,
    ...
    We were unable to import the file because of errors in its format:
    <BLANKLINE>
    Number of plural forms is impossibly low.
    <BLANKLINE>
    ...


Too many plural forms
---------------------

Next Mark, eclectic polyglot that he is, uploads an Arabic translation.
He mistakenly defines seven instead of six plural forms.  That would be
fine but Launchpad only supports up to six forms.  He receives a message
about this.

The email points to Launchpad's information about Arabic and shows how
to get that information corrected if need be.

    >>> pofile = potemplate.newPOFile('ar')

    # PO file with nplurals=7, a value we can't handle.
    >>> pofile_contents = six.ensure_binary(r'''
    ... msgid ""
    ... msgstr ""
    ... "PO-Revision-Date: 2005-07-01 08:35+0100\n"
    ... "Last-Translator: Foo <no-priv@canonical.com>\n"
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ... "Plural-Forms: nplurals=7; plural=n%%7\n"
    ... "X-Rosetta-Export-Date: %s\n"
    ... 
    ... msgid "%%d foo"
    ... msgid_plural "%%d foos"
    ... msgstr[0] "bar %%d"
    ... msgstr[1] "bares %%d"
    ... msgstr[2] "baris %%d"
    ... msgstr[3] "baribus %%d"
    ... msgstr[4] "baros %%d"
    ... msgstr[5] "barorum %%d"
    ... msgstr[6] "barim %%d"
    ... ''' % datetime.datetime.now(UTC).isoformat())
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, False, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> (subject, message) = pofile.importFromQueue(entry)

    >>> print(entry.status.name)
    FAILED

    >>> print(subject)
    Import problem - Arabic (ar) - firefox in Mozilla Firefox trunk

    >>> print(message)
    Hello Mark Shuttleworth,
    <BLANKLINE>
    On ..., you uploaded a file with Arabic (ar) translations for firefox in
    Mozilla Firefox trunk to Launchpad.
    <BLANKLINE>
    We were unable to import it because it declares more plural forms than
    Launchpad can currently handle.  The maximum supported is 6.
    <BLANKLINE>
    Please see if you can get by with fewer plural forms.  You can find
    Launchpad's default plural-forms information for Arabic (ar) here:
    <BLANKLINE>
    https://translations.launchpad.net/+languages/ar
    <BLANKLINE>
    If you believe the information listed there is incorrect, please file a
    question here:
    <BLANKLINE>
    https://answers.launchpad.net/rosetta/+addquestion
    <BLANKLINE>
    For your convenience, you can get the file you uploaded at:
    http://.../firefox-ar.po
    <BLANKLINE>
    <BLANKLINE>
    Thank you,
    <BLANKLINE>
    The Launchpad team
    <BLANKLINE>

Once Mark has checked the language page and corrected the number of
plural forms, the file imports just fine.

    # Same PO file as before, but with nplurals=6.
    >>> pofile_contents = six.ensure_binary(r'''
    ... msgid ""
    ... msgstr ""
    ... "PO-Revision-Date: 2005-07-01 08:35+0100\n"
    ... "Last-Translator: Foo <no-priv@canonical.com>\n"
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ... "Plural-Forms: nplurals=6; plural=n%%6\n"
    ... "X-Rosetta-Export-Date: %s\n"
    ... 
    ... msgid "%%d foo"
    ... msgid_plural "%%d foos"
    ... msgstr[0] "bar %%d"
    ... msgstr[1] "bares %%d"
    ... msgstr[2] "baris %%d"
    ... msgstr[3] "baribus %%d"
    ... msgstr[4] "baros %%d"
    ... msgstr[5] "barorum %%d"
    ... ''' % datetime.datetime.now(UTC).isoformat())
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, False, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> (subject, message) = pofile.importFromQueue(entry)

    >>> print(entry.status.name)
    IMPORTED
