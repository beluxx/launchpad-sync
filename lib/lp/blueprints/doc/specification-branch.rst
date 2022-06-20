Specification Branch Links
==========================

    >>> from lp.testing import verifyObject
    >>> from lp.blueprints.interfaces.specificationbranch import (
    ...     ISpecificationBranch)
    >>> from lp.blueprints.model.specification import SpecificationBranch
    >>> from lp.services.database.interfaces import IStore
    >>> verifyObject(
    ...     ISpecificationBranch,
    ...     IStore(SpecificationBranch).get(SpecificationBranch, 1))
    True

A specification can be linked to a number of branches.  For example,
the Ubuntu media-integrity-check specifcation has a branch link:

    >>> from zope.component import getUtility
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.code.interfaces.branchlookup import IBranchLookup
    >>> from lp.registry.interfaces.person import IPersonSet

    >>> ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    >>> spec = ubuntu.getSpecification('media-integrity-check')

    >>> for branchlink in spec.linked_branches:
    ...     print(branchlink.branch.unique_name)
    ~name12/+junk/junk.dev

We can create a new branch link with the linkBranch() method:

    >>> branch = getUtility(IBranchLookup).getByUniqueName(
    ...     '~name12/+junk/junk.contrib')
    >>> user = getUtility(IPersonSet).getByEmail('test@canonical.com')
    >>> branchlink = spec.linkBranch(branch, user)

The branch link records the person who created the link as the registrant.

    >>> print(branchlink.registrant.displayname)
    Sample Person

Now the branch has two branch links:

    >>> for branchlink in spec.linked_branches:
    ...     print(branchlink.branch.unique_name)
    ~name12/+junk/junk.dev
    ~name12/+junk/junk.contrib

Similarly, the branch has a list of attached specifications:

    >>> for speclink in branch.spec_links:
    ...     print(speclink.specification.name)
    media-integrity-check

We can also look up a branch link with the getBranchLink() method:

    >>> branchlink = spec.getBranchLink(branch)
    >>> branchlink.specification == spec
    True
    >>> branchlink.branch == branch
    True

Finally, the branch link can be removed using the unlinkBranch()
method:

    >>> spec.unlinkBranch(branch, user)
    >>> for branchlink in spec.linked_branches:
    ...     print(branchlink.branch.unique_name)
    ~name12/+junk/junk.dev
