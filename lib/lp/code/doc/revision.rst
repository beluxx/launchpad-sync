Bazaar Revisions
================

Branches are collection of revisions, and a revision can exist independently
from any branch. Revisions are created automatically by scanning branches,
they have no creation interface and Launchpad cannot create or modify them.

Interfaces
----------

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.testing import verifyObject
    >>> from lp.code.interfaces.revision import (
    ...     IRevision, IRevisionAuthor, IRevisionParent, IRevisionSet)
    >>> from lp.code.interfaces.branchrevision import IBranchRevision
    >>> from lp.code.model.revision import (
    ...     Revision, RevisionAuthor, RevisionParent, RevisionSet)
    >>> from lp.code.model.branchrevision import BranchRevision
    >>> verifyObject(IRevision, IStore(Revision).find(Revision).any())
    True
    >>> verifyObject(
    ...     IRevisionAuthor,
    ...     IStore(RevisionAuthor).find(RevisionAuthor).any())
    True
    >>> verifyObject(
    ...     IRevisionParent,
    ...     IStore(RevisionParent).find(RevisionParent).any())
    True
    >>> verifyObject(IRevisionSet, RevisionSet())
    True
    >>> verifyObject(
    ...     IBranchRevision,
    ...     IStore(BranchRevision).find(BranchRevision).any())
    True

Creating revisions
------------------

The creator of a revision is identified by a RevisionAuthor. A RevisionAuthor
is not a person because that is only an informational attribute, and even if
we trust it, there's really no simple way to map that reliably to persons.

    >>> from lp.code.model.revision import RevisionAuthor
    >>> author = RevisionAuthor(name='ddaa@localhost')
    >>> print(author.name)
    ddaa@localhost

The log-body of a revision is the commit message of that revision.

    >>> log_body_1 = "Initial import"
    >>> log_body_2 = "Fix froboizer"

The revision-id is the globally unique id used by the revision control. For
native Bazaar2 revisions it's a GUID, for Bazaar2 imports it's a string based
on the Arch revision id.

    >>> revision_id_1 = "Arch-1:ddaa@example.com/junk--devel--base-0"
    >>> revision_id_2 = "some random unique string, we do not care, really"

The revision_date is the commit date recorded by the revision control system,
while the date_created is the time when the database record was created.

    >>> from datetime import datetime
    >>> from pytz import UTC
    >>> date = datetime(2005, 3, 8, 12, 0, tzinfo=UTC)
    >>> revision_1 = Revision(log_body=log_body_1,
    ...     revision_author=author, revision_id=revision_id_1,
    ...     revision_date=date)

Parents
-------

Bazaar revisions can have multiple parents, the "leftmost" parent is the
revision that was used as a base when committing, other parents are used to
record merges. All revisions except initial imports have at least one parent.

Parents are accessed through their revision_id without using a foreign key so
we can represent revisions whose at least one parent is a ghost revision.

    >>> revision_2 = Revision(log_body=log_body_2,
    ...     revision_author=author, revision_id=revision_id_2,
    ...     revision_date=date)

    >>> from lp.code.model.revision import RevisionParent
    >>> rev2_parent = RevisionParent(sequence=0, revision=revision_2,
    ...                              parent_id=revision_1.revision_id)

Branch ancestry
---------------

Revisions are associated to branches through the BranchRevision table. A given
revision may appear in different positions in different branches thanks to
Bazaar converge-on-pull logic.

    >>> from lp.code.interfaces.branchlookup import IBranchLookup
    >>> branch = getUtility(IBranchLookup).get(1)
    >>> branch.revision_history.count()
    0

BranchRevision rows are created using `Branch.createBranchRevision`.

    >>> rev_no_1 = branch.createBranchRevision(
    ...     sequence=1, revision=revision_1)
    >>> rev_no_2 = branch.createBranchRevision(
    ...     sequence=2, revision=revision_2)
    >>> rev_no_1.branch == rev_no_2.branch == branch
    True

Accessing BranchRevision
........................

    >>> branch = getUtility(IBranchLookup).getByUniqueName(
    ...     '~name12/+junk/junk.contrib')

The full ancestry of a branch is recorded. That includes the history commits
on this branch, but also revisions that were merged into this branch. Such
merged revisions are associated to the branch using BranchRevision whose
sequence attribute is None.

    >>> from lp.code.model.branchrevision import BranchRevision
    >>> ancestry = IStore(BranchRevision).find(
    ...     BranchRevision, BranchRevision.branch == branch)
    >>> for branch_revision in sorted(ancestry,
    ...         key=lambda r: (
    ...             0 if r.sequence is None else 1, r.sequence,
    ...             r.revision.id),
    ...         reverse=True):
    ...     print(branch_revision.sequence, branch_revision.revision.id)
    6 9
    5 8
    4 11
    3 10
    2 5
    1 4
    None 7
    None 6

If you need to operate on the ancestry of a branch, you should write a focused
query to avoid creating the tens of thousands of objects necessary to
represent the ancestry of a large branch.

In particular, IBranch.getScannerData efficiently retrieves the BranchRevision
data needed by the branch-scanner script.

    >>> ancestry, history = branch.getScannerData()

The first return value is a set of revision_id strings for the full ancestry
of the branch.

    >>> for revision_id in sorted(ancestry):
    ...     print(revision_id)
    foo@localhost-20051031165758-48acedf2b6a2e898
    foo@localhost-20051031170008-098959758bf79803
    foo@localhost-20051031170239-5fce7d6bd3f01efc
    foo@localhost-20051031170357-1301ad6d387feb23
    test@canonical.com-20051031165248-6f1bb97973c2b4f4
    test@canonical.com-20051031165338-5f2f3d6b10bb3bf0
    test@canonical.com-20051031165532-3113df343e494daa
    test@canonical.com-20051031165901-43b9644ec2eacc4e

The second return value is a sequence of revision_id strings for the revision
history of the branch.

    >>> for revision_id in history:
    ...     print(revision_id)
    test@canonical.com-20051031165248-6f1bb97973c2b4f4
    test@canonical.com-20051031165338-5f2f3d6b10bb3bf0
    foo@localhost-20051031165758-48acedf2b6a2e898
    foo@localhost-20051031170008-098959758bf79803
    foo@localhost-20051031170239-5fce7d6bd3f01efc
    foo@localhost-20051031170357-1301ad6d387feb23


Deleting BranchRevisions
........................

If a branch gets overwritten or some revisions get uncommitted,
Launchpad's view of the branch will differ from the actual state of the
branch. If the bzr branch now has fewer revisions than Launchpad's view
of the branch, then some of BranchRevision records will need to be
removed.

BranchRevision records are deleted using the `Branch.removeBranchRevisions`
method.


First, get a branch:

    >>> from zope.component import getUtility
    >>> branch = getUtility(IBranchLookup).getByUniqueName(
    ...     '~name12/+junk/junk.dev')

The last commit on this branch has the revision number 6.

    >>> [revno_6] = branch.latest_revisions(1)
    >>> revno_6.sequence
    6
    >>> revno_6.branch == branch
    True
    >>> rev_id = revno_6.revision.revision_id
    >>> print(rev_id)
    foo@localhost-20051031170357-1301ad6d387feb23

We remove the last revision from the branch. This is similar to what
"bzr uncommit" does.

    >>> branch.removeBranchRevisions(rev_id)

Afterwards, the last commit on the branch has revision number 5.

    >>> branch.latest_revisions(1)[0].sequence
    5

Note that while the BranchRevision object linking the revision to the
branch has been destroyed, the associated revision object is not (it
may be referenced by some other branch):

    >>> from lp.code.interfaces.revision import IRevisionSet
    >>> revision = getUtility(IRevisionSet).getByRevisionId(
    ...     'foo@localhost-20051031170357-1301ad6d387feb23')
    >>> print(revision.revision_id)
    foo@localhost-20051031170357-1301ad6d387feb23


IRevisionSet.new()
------------------

Revision objects can be created using the IRevisionSet utility.
Associated RevisionAuthor and RevisionParent objects will be created
as needed.

    >>> revision = getUtility(IRevisionSet).new(
    ...     revision_id='rev-3',
    ...     log_body='commit message',
    ...     revision_date=date,
    ...     revision_author='ddaa@localhost',
    ...     parent_ids=['rev-1', 'rev-2'],
    ...     properties={u'key': u'value'})
    >>> print(revision.revision_id)
    rev-3
    >>> print(revision.log_body)
    commit message
    >>> print(revision.revision_date)
    2005-03-08 12:00:00+00:00
    >>> print(revision.revision_author.name)
    ddaa@localhost
    >>> for parent_id in revision.parent_ids:
    ...     print(parent_id)
    rev-1
    rev-2
    >>> for key, value in sorted(revision.getProperties().items()):
    ...     print('%s: %s' % (key, value))
    key: value
