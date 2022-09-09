TranslationBranchApprover
=========================

The TranslationBranchApprover approves simple cases of import of translation
template files (POT). It is used for the approval of template files uploaded
from bazaar branches in Launchpad. It operates either on a product series or
sourcepackagename within a distroseries but the productseries is the only use
case in this scenario.

    >>> from lp.translations.model.approver import TranslationBranchApprover
    >>> series = factory.makeProductSeries()

The goal of the approval process is to match the files in the import queue
to POTemplate objects that are already in the database. Only current (active,
visible) templates are taken into account.

The matching is done by path first and then by template name if the path did
not match. The template name of a queue entry is derived from the translation
domain which in turn is derived from the path itself.

The name is used for matching instead of the translation domain because the
domain may change when the source tree is updated to a new version as
the developers may choose to include version information in the domain. This
makes it possible to intall multiple versions of the same software on a
system without having mo files clash. Evolution is a noteable example of
doing this.

To be able to assess the context of a template file it should approve, the
approver is initialized with a list of all the template files names that are
in the current source tree. As the branch upload job will only upload actually
changed files, not all files on this list will need to be approved but their
names are needed for context.

Upon initization TranslationBranchApprover will try to find matching
POTemplate objects for each file name (path) in the list and store these in
an internal dict indexed with the path. It also knows the total number of
POTemplate objects and thus if all objects have been matched to a file. On
the other hand it also knows about files that have no matching object. This
will lead to one of four situations.

 1. All files are matched to POTemplate objects and vice versa so that no
    file or oject is left unmatched. All subsequent approval requests can
    safely be approved.
 2. All objects are matched to files but at least one file is left unmatched.
    The matched files can safly be approved wereas the unmatched file
    triggers the creation of a new POTemplate object. If multiple files are
    unmatched, a POTemplate will be created for each.
 3. Some files *and* some objects are left unmatched. Only the matched files
    can safely be approved but the unmatched files will not be approved as
    their relation to the unmatched POTemplate objects is unclear.
 4. All files are matched to POTemplate objects but some objects are left
    unmatched. This is like the first situation except that the unmatched
    POTemplate objects are simply ignored.

We need special permissions to do the following steps so we'd better login.

    >>> login("foo.bar@canonical.com")

Ok, we have a fresh product series that has no POTemplate object yet.
The branch upload job places the only template file in the branch into
the import queue.

    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue,
    ... )
    >>> queue = getUtility(ITranslationImportQueue)
    >>> entry = queue.addOrUpdateEntry(
    ...     "foo.pot",
    ...     b"foo pot content",
    ...     True,
    ...     series.owner,
    ...     productseries=series,
    ... )

The job initializes the approver with the list of template files in the tree,
which has only one entry. This is situtation 2 (see above).

    >>> approver = TranslationBranchApprover(
    ...     ["foo.pot"], productseries=series
    ... )

It approves the entry which leads to the creation of a new POTemplate object.

    >>> print(entry.potemplate)
    None
    >>> entry = approver.approve(entry)
    >>> print(repr(entry.potemplate))
    <POTemplate at ...>
    >>> foo_potemplate = entry.potemplate
    >>> print(foo_potemplate.name)
    foo
    >>> print(repr(entry.status))
    <DBItem RosettaImportStatus.APPROVED, (1) Approved>

Now the project owner wants to use two translation domains in their project
and thus creates another template file in the branch. The branch upload job
detects this new file on its next run and places it into the import queue
(but not the first one which is left unchanged).

    >>> entry = queue.addOrUpdateEntry(
    ...     "bar.pot",
    ...     b"bar pot content",
    ...     True,
    ...     series.owner,
    ...     productseries=series,
    ... )

The job does know about all the template files in the tree and so it
initializes the approver accordingly. This is situtation 2 again.

    >>> approver = TranslationBranchApprover(
    ...     ["foo.pot", "bar.pot"], productseries=series
    ... )

It approves the entry which leads to the creation of another POTemplate
object.

    >>> print(entry.potemplate)
    None
    >>> entry = approver.approve(entry)
    >>> print(repr(entry.potemplate))
    <POTemplate at ...>
    >>> bar_potemplate = entry.potemplate
    >>> print(bar_potemplate.name)
    bar
    >>> print(repr(entry.status))
    <DBItem RosettaImportStatus.APPROVED, (1) Approved>


Next the owner of the branch realizes that they need to put their translation
template files in proper subdirectories for multiple templates to work
correctly. Also, they start using a tool that calls the template
"messages.pot" consistently. So they move and rename the files. The branch
upload job detects two changed files and places them in the upload queue.

    >>> foo_entry = queue.addOrUpdateEntry(
    ...     "po/foo/messages.pot",
    ...     b"foo pot content",
    ...     True,
    ...     series.owner,
    ...     productseries=series,
    ... )
    >>> bar_entry = queue.addOrUpdateEntry(
    ...     "po/bar/messages.pot",
    ...     b"bar pot content",
    ...     True,
    ...     series.owner,
    ...     productseries=series,
    ... )

Since these two files are all the translation template files in the tree,
the job initializes the approver with their names. This is situation 1.

    >>> approver = TranslationBranchApprover(
    ...     ["po/foo/messages.pot", "po/bar/messages.pot"],
    ...     productseries=series,
    ... )

Upon approval both entries retain their POTemplate links but the path
attributes of the linked objects are updated.

    >>> foo_entry = approver.approve(foo_entry)
    >>> print(foo_entry.potemplate == foo_potemplate)
    True
    >>> print(foo_potemplate.path)
    po/foo/messages.pot
    >>> print(repr(foo_entry.status))
    <DBItem RosettaImportStatus.APPROVED, (1) Approved>
    >>> bar_entry = approver.approve(bar_entry)
    >>> print(bar_entry.potemplate == bar_potemplate)
    True
    >>> print(bar_potemplate.path)
    po/bar/messages.pot
    >>> print(repr(bar_entry.status))
    <DBItem RosettaImportStatus.APPROVED, (1) Approved>

But now the branch owner messes things up and renames the bar template
completely. The branch import job picks up on this and places the file in the
queue.

    >>> spam_entry = queue.addOrUpdateEntry(
    ...     "po/spam/messages.pot",
    ...     b"bar pot content",
    ...     True,
    ...     series.owner,
    ...     productseries=series,
    ... )

Since these two files are again all the translation template files in the
tree, the job initializes the approver with their names. But this is
situation 3 now as both the new file name and the bar_potemplate object in
the database are not matched against anything.

    >>> approver = TranslationBranchApprover(
    ...     ["po/foo/messages.pot", "po/spam/messages.pot"],
    ...     productseries=series,
    ... )

Trying to approve the new entry fails gloriously because there is no way of
knowing if and how the unmatached file and the unmatched object relate to
each other.

    >>> spam_entry = approver.approve(spam_entry)
    >>> print(spam_entry.potemplate)
    None
    >>> print(repr(spam_entry.status))
    <DBItem RosettaImportStatus.NEEDS_REVIEW, (5) Needs Review>

It is however still possible to update the foo template as this can be matched
safely against the existing foo_template object, even in situation 3.

    >>> foo_entry = queue.addOrUpdateEntry(
    ...     "po/foo/messages.pot",
    ...     b"CHANGED foo pot content",
    ...     True,
    ...     series.owner,
    ...     productseries=series,
    ... )
    >>> approver = TranslationBranchApprover(
    ...     ["po/foo/messages.pot", "po/spam/messages.pot"],
    ...     productseries=series,
    ... )
    >>> foo_entry = approver.approve(foo_entry)
    >>> print(repr(foo_entry.status))
    <DBItem RosettaImportStatus.APPROVED, (1) Approved>
