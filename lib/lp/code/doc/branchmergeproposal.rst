Branch merge proposals
======================

The purpose of branch merge proposals are to indicate that the one branch
should be merged into another branch.

The branch to be merged is referred to as the "source branch", and the branch
that is being merged into is referred to as the "target branch".

In the early phases of development of this feature there was often a mixing of
terms where the term "merge proposal" was used interchangably with "code
review" which caused some confusion.

- **Merge Proposal:** indicates that one branch should be merged with another.
- **Code Review:** a discussion that takes place about the changes that would
  occur should the proposed merge happen

A merge proposal may have a code reivew, but a code review always happens with
respect to a merge proposal.


Other Terms
-----------

Landing Targets
  These are the merge proposals related to the branch for which the branch
  that is being looked at is the source branch.  It is called that due to the
  idea that the target branch is where the code intentds to 'land' or 'merge'.

Landing Candidates
  These are the merge proposals that indicate the intent to merge with the
  branch being looked at.


Creating a Merge Proposal
-------------------------

All merge proposals are created from the source branch using a method called
``addLandingTarget``.

    >>> fooix = factory.makeProduct(name='fooix')
    >>> source_branch = factory.makeProductBranch(product=fooix)
    >>> target_branch = factory.makeProductBranch(product=fooix)
    >>> merge_proposal = source_branch.addLandingTarget(
    ...     registrant=source_branch.owner,
    ...     merge_target=target_branch)

The bare minimum that needs to be specified is the person that is proposing
the merge, the ``registrant``, and the branch that the registrant wants the
branch to be merged into, the ``target_branch``.

There are other optional parameters to initialize other merge proposal
attributes such as the description, commit message or requested reviewers.

It is considered good form to set at least one of the commit message or
description.  For very simple branches a commit message might be enough, but
for non-trivial branches a description is often needed to describe the intent
of the changes.


States of a Merge Proposal
--------------------------

During the life time of a merge proposal it will go through many states.

Work in Progress
  The source branch is intended to be merged into the target, but the work has
  not yet been fully completed.

Needs Review
  The work has been completed to the satisfaction of the branch owner, or at
  least some form of review of the change is being requested.

Approved
  The reviewer is happy with the change.

Rejected
  The reviews is not happy with the change.

Merged
  The source branch has been merged into the target.  The branch scanner also
  sets the ``merge_revno`` of the merge proposal to indicate which revision
  number on the target branch has this merge in it.

Superseded
  The intent of superseded proposals has changed somewhat over time, and needs
  some rework (bugs 383352, 397444, 400030, 488544)
