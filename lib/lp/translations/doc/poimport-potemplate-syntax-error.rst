PO Import test with a .pot file that has a syntax error
=======================================================

When we import a .pot file with a syntax error, we should notify
the user about that error so they have a chance to fix it.

In this test, we are going to check that we detect and notify the error.

Here are some imports we need to get this test running.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue)
    >>> from lp.translations.model.potemplate import POTemplateSubset
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

Let's import a .pot file that is missing its header. That's a
TranslationFormatSyntaxError

    >>> potemplate_contents = br'''
    ... msgid "foo"
    ... msgstr ""
    ... '''
    >>> by_maintainer = True
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     potemplate.path, potemplate_contents, by_maintainer, person,
    ...     productseries=series, potemplate=potemplate)
    >>> transaction.commit()
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> (subject, message) = potemplate.importFromQueue(entry)

The import failed.

    >>> print(entry.status.name)
    FAILED

    >>> print(entry.error_output)
    No header found in this pofile

And the code composed email with a notification of the error.

    >>> print(subject)
    Import problem - firefox in Mozilla Firefox trunk
    >>> print(message)
    Hello Mark Shuttleworth,
    <BLANKLINE>
    On ..., you uploaded a file with translation templates for firefox in
    Mozilla Firefox trunk to Launchpad.
    <BLANKLINE>
    We were unable to import the file because of errors in its format:
    <BLANKLINE>
    No header found in this pofile
    <BLANKLINE>
    If you use gettext, you can check your file for correct formatting with
    the 'msgfmt -c' command.
    Please fix any errors raised by msgfmt and upload the file again. If you
    check the file and you don't find any error in it, please look for an
    answer or file a question at https://answers.launchpad.net/rosetta/
    <BLANKLINE>
    For your convenience, you can get the file you uploaded at:
    http://.../firefox.pot
    <BLANKLINE>
    Thank you,
    <BLANKLINE>
    The Launchpad team
    <BLANKLINE>


Encoding errors
===============

    >>> potemplate = subset.new(
    ...     name='nonascii',
    ...     translation_domain='nonascii',
    ...     path='po/nonascii.pot',
    ...     owner=person)

    >>> potemplate_contents = u'''
    ... msgid ""
    ... msgstr ""
    ... "Content-Type: text/plain; charset=ASCII\\n"
    ...
    ... msgid "\xa9 Yoyodine Industries"
    ... msgstr ""
    ... '''.encode('utf-8')
    >>> by_maintainer = False
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     potemplate.path, potemplate_contents, by_maintainer, person,
    ...     productseries=series, potemplate=potemplate)
    >>> transaction.commit()
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> (subject, message) = potemplate.importFromQueue(entry)

The import failed.

    >>> print(entry.status.name)
    FAILED

The uploader receives an email about the encoding problem.

    >>> print(subject)
    Import problem - nonascii in Mozilla Firefox trunk

    >>> print(message)
    Hello Mark Shuttleworth,
    <BLANKLINE>
    On ..., you uploaded a file with translation templates for nonascii
    in Mozilla Firefox trunk to Launchpad.
    <BLANKLINE>
    The file could not be imported because of text encoding problems.
    ...
    <BLANKLINE>
    The specific error message was:
    <BLANKLINE>
    'ascii' codec can't decode byte ...
    <BLANKLINE>
    For your convenience, you can find the file you uploaded at:
    http://.../nonascii.pot
    <BLANKLINE>
    Thank you,
    <BLANKLINE>
    The Launchpad team
    <BLANKLINE>

The queue entry's error_output field also contains a brief
description of the error.

    >>> print(entry.error_output)
    'ascii' codec can't decode byte ... in position ...: ordinal not in
    range(128)
