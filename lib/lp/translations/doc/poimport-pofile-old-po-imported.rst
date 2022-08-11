PO Import test with a .po file that has a PO-Revision-Date not updated
======================================================================

When we import a .po file with a 'PO-Revision-Date' that has an older
value than the one stored in IPOFile.header, we should detect it and
notify the user that they should update that field or we assume that
such file is an old version that should not be imported. That way, they
have a chance to fix it.

We have to make an exception for files coming from upstream, though, because
the user may not be able to get the file fixed upstream or the file is older
because a user upload occured before the upstream file made it to Launchpad.
In either case we assume that the upstream file is OK and accept it for
upload.

In this test, we are going to check that we detect these situations and
notify the user about them.

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

And also, the DBSchema to change the imports status

    >>> from lp.translations.enums import RosettaImportStatus

Login as an admin to be able to do changes to the import queue.

    >>> login('carlos@canonical.com')

Here's the person who'll be doing the import.

    >>> person_set = getUtility(IPersonSet)
    >>> person = person_set.getByName('mark')

Now it's time to create the new potemplate

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

First, we do a valid import.

    >>> pofile_contents = six.ensure_binary(r'''
    ... msgid ""
    ... msgstr ""
    ... "PO-Revision-Date: 2005-05-03 20:41+0100\n"
    ... "Last-Translator: Carlos Perello Marin <carlos@canonical.com>\n"
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ... "Plural-Forms: nplurals=4; plural=n==1) "
    ...     "? 0 : n==2 ? 1 : (n != 8 || n != 11) ? 2 : 3;\n"
    ... "X-Rosetta-Export-Date: %s\n"
    ...
    ... msgid "foo"
    ... msgstr "blah"
    ... ''' % datetime.datetime.now(UTC).isoformat())
    >>> by_maintainer = False
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, by_maintainer, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()

We must approve the entry to be able to import it.

    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)

We do the import.  This succeeds without errors.

    >>> (subject, message) = pofile.importFromQueue(entry)
    >>> print(entry.error_output)
    None

The status is now IMPORTED:

    >>> entry.status == RosettaImportStatus.IMPORTED
    True

(The procedure also generates a confirmation email, but that is tested
in `poimport.rst`.)

We can see that the header has the same 'PO-Revision-Date' as the
file we just imported.

    >>> print(pofile.header)
    Project-Id-Version:...
    PO-Revision-Date: 2005-05-03 20:41+0100
    ...

Now, we are going to import a .po file that has a 'PO-Revision-Date'
field with a date older than a previous .po import.

    >>> pofile_contents = six.ensure_binary(r'''
    ... msgid ""
    ... msgstr ""
    ... "PO-Revision-Date: 2005-05-03 19:41+0100\n"
    ... "Last-Translator: Carlos Perello Marin <carlos@canonical.com>\n"
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ... "Plural-Forms: nplurals=4; plural=n==1) "
    ...     "? 0 : n==2 ? 1 : (n != 8 || n != 11) ? 2 : 3;\n"
    ... "X-Rosetta-Export-Date: %s\n"
    ...
    ... msgid "foo"
    ... msgstr "blah"
    ... ''' % datetime.datetime.now(UTC).isoformat())
    >>> by_maintainer = False
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, by_maintainer, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()

We must approve the entry to be able to import it.

    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)

We do the import.

    >>> (subject, message) = pofile.importFromQueue(entry)

This fails because the file's timestamp was not updated.

    >>> entry.status == RosettaImportStatus.FAILED
    True

    >>> print(entry.error_output)
    Outdated translation.  The last imported version of this file was dated
    2005-05-03 20:41:00+01:00; the timestamp in the file you uploaded is
    2005-05-03 19:41:00+01:00.

We can see that the header remains unchanged

    >>> print(pofile.header)
    Project-Id-Version:...
    PO-Revision-Date: 2005-05-03 20:41+0100
    ...

The code also generated an email about the error we produced.

    >>> print(subject)
    Import problem - Welsh (cy) - firefox in Mozilla Firefox trunk
    >>> print(message)
    Hello Mark Shuttleworth,
    <BLANKLINE>
    On ..., you uploaded a file with
    Welsh (cy) translations for firefox in Mozilla Firefox trunk in
    Launchpad.
    <BLANKLINE>
    We were unable to import your translations because you did not update
    the timestamp in its header to state when you added your translations.
    <BLANKLINE>
    The last imported version of this file was dated
    2005-05-03 20:41:00+01:00; the timestamp in the file you uploaded is
    2005-05-03 19:41:00+01:00.
    <BLANKLINE>
    To fix this problem, please upload the file again, but with the
    'PO-Revision-Date' field updated.
    <BLANKLINE>
    For your convenience, you can get the file you uploaded at:
    http://.../firefox-cy.po
    <BLANKLINE>
    Thank you,
    <BLANKLINE>
    The Launchpad team
    <BLANKLINE>

Finally we are going to import the same po file with the old
'PO-Revision-Date' field but mark it as a file uploaded by the maintainer.

    >>> by_maintainer = True
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, by_maintainer, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()

We approve the entry and import it.

    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> (subject, message) = pofile.importFromQueue(entry)

This succeeds although the file's timestamp is older than that of the
previous import.

    >>> entry.status == RosettaImportStatus.IMPORTED
    True
    >>> print(entry.error_output)
    None

But the header remains unchanged, so that the older date is not recorded.

    >>> print(pofile.header)
    Project-Id-Version:...
    PO-Revision-Date: 2005-05-03 20:41+0100
    ...
