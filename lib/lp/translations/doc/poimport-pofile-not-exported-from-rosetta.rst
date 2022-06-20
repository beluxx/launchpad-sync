PO Import test with a .po file that lacks X-Rosetta-Export-Date header
======================================================================

When we import a .po file as not coming from upstream, it needs to have a
header named 'X-Rosetta-Export-Date' to be able to detect conflicts with
other translations done for the same POFile while we do translations offline.
Without that header, we cannot detect conflicts, so we don't accept that
file. We should notify the user about that error so they have a chance
to fix it.

If the file being imported is from upstream, we don't care about
X-Rosetta-Export-Date header. That's because upstream translations
don't change translations being used in Rosetta, it's just a reference
of what upstream has and they only add active translations if there
isn't one already so there aren't conflicts to solve.

This test shows that we don't accept .po imports that weren't first
exported from Launchpad, and that a notification email is generated to
warn the uploader about this.

Here are some imports we need to get this test running.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.translations.enums import RosettaImportStatus
    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue)
    >>> from lp.translations.model.potemplate import POTemplateSubset
    >>> import pytz
    >>> UTC = pytz.timezone('UTC')
    >>> translation_import_queue = getUtility(ITranslationImportQueue)
    >>> rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts

We need this for the Librarian to work properly.

    >>> import transaction

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

And now, we import a .po file, not uploaded by the maintainer, that lacks the
header 'X-Rosetta-Export-Date'. That header is the one that notes that the
file comes from a previous export from Rosetta and when did it happen.

    >>> pofile_contents = br'''
    ... msgid ""
    ... msgstr ""
    ... "PO-Revision-Date: 2005-06-03 19:41+0100\n"
    ... "Last-Translator: Carlos Perello Marin <carlos@canonical.com>\n"
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ...
    ... msgid "foo"
    ... msgstr "blah"
    ... '''
    >>> by_maintainer = False
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, by_maintainer, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()

We must approve the entry to be able to import it.

    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)

We do the import.

    >>> (subject, message) = pofile.importFromQueue(entry)

The status is now FAILED:

    >>> entry.status == RosettaImportStatus.FAILED
    True

And the method returned an email with a notification of the error.

    >>> print(subject)
    Import problem - Welsh (cy) - firefox in Mozilla Firefox trunk

    >>> print(message)
    Hello Mark Shuttleworth,
    <BLANKLINE>
    On ..., you uploaded a file with
    Welsh (cy) translations for firefox in Mozilla Firefox trunk in Launchpad.
    <BLANKLINE>
    We were unable to import it because either this file did not
    originate in Launchpad, or you removed the tag we use to mark files
    exported from Launchpad.
    <BLANKLINE>
    The reason we require that tag is to prevent translators who work
    offline from inadvertently reverting translations made by others.
    <BLANKLINE>
    To fix the problem, please get the latest export from Launchpad,
    apply your changes and upload the merged file.
    <BLANKLINE>
    For your convenience, you can get the file you uploaded at:
    http://.../firefox-cy.po
    <BLANKLINE>
    Thank you,
    <BLANKLINE>
    The Launchpad team
    <BLANKLINE>

A much shorter version of that information is stored in the entry's
error_output.

    >>> print(entry.error_output)
    File was not exported from Launchpad.

We should also be sure that we don't block any import that is coming from
upstream. That kind of import is not blocked if they lack the
'X-Rosetta-Export-Date' header.

We need to fetch again some SQLObjects because we did a transaction
commit.

    >>> release = ProductRelease.get(3)
    >>> series = release.milestone.productseries
    >>> subset = POTemplateSubset(productseries=series)
    >>> potemplate = subset.getPOTemplateByName('firefox')
    >>> pofile = potemplate.getPOFileByLang('cy')
    >>> person = person_set.getByName('mark')

Now, attach the file again, but this time as coming from upstream.

    >>> by_maintainer = True
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, by_maintainer, person,
    ...     productseries=series, potemplate=potemplate, pofile=pofile)
    >>> transaction.commit()

We must approve the entry to be able to import it.

    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)

We do the import.

    >>> (subject, message) = pofile.importFromQueue(entry)

The status is now IMPORTED:

    >>> entry.status == RosettaImportStatus.IMPORTED
    True

The import code has also composed an email with the notification of the
import.

    >>> print(subject)
    None
    >>> print(message)
    Hello Mark Shuttleworth,
    ...

There was no error output this time.

    >>> print(entry.error_output)
    None
