Bazaar Branches
===============

The Branch table holds information about a Bazaar branch.  It contains
the metadata associated with the branch -- the owner, the whiteboard and
so on.  Where the actual branch data lives depends on the branch.

It has a N-N association to the Revision table through the
BranchRevision table. An associated table is required because the
sequence of revisions listed by "bzr log" is defined by a "revision-
history" file which has some freedom with respect to the ancestry of
revisions, at least in Branch5 and older branches.

  * Distinct revision histories may point to same revision.

  * Revision histories including the same revision may have different
    starting points, they need not trace history back to the initial
    import. Therefore a given revision may have a different order
    number in different branches.

  * A revision history is required to follow the ancestry DAG, but two
    different branches may have histories tracing a different path between two
    shared revisions. This is exercised by the "convergence" feature of "bzr
    pull".


Interfaces
----------

    >>> from lp.testing import verifyObject
    >>> from lp.code.enums import BranchType
    >>> from lp.code.interfaces.branch import IBranchSet
    >>> from lp.code.interfaces.branchsubscription import IBranchSubscription
    >>> from lp.code.model.branch import Branch


Branch types
------------

There are four different types of branches:

 * Hosted
 * Mirrored
 * Imported
 * Remote

Hosted branches use the Launchpad codehosting as a primary location for
the branch.  The branch (as far as Launchpad is concerned) can be pushed
to and pulled from.

Mirrored branches have a main location outside of Launchpad, and
Launchpad pulls the branch into the codehosting area.  Mirrored branches
can be pulled from but not pushed to.  Launchpad keeps the branch up to
date using the `branch_puller` script.

Imported branches are those where a bazaar branch is built from a CVS or
Subversion repository.  Imported branches have to be requested and go
through a testing and verification process.

Remote branches are registered in Launchpad, but the branch is not
stored in the Launchpad codehosting service, and as such are not
accessible using the anonymous http access, nor through the Launchpad
SFTP or smart server.  The remote branches can still be linked to bugs
and blueprints.


Fetching branches by ID
-----------------------

The collection of all branches is represented by IBranchSet, which is
registered as an utility.

    >>> from zope.component import getUtility
    >>> from lp.code.interfaces.branchlookup import IBranchLookup
    >>> branchset = getUtility(IBranchSet)
    >>> branch_lookup = getUtility(IBranchLookup)

The 'get' method on the branch set fetches branches by ID.

    >>> branch = factory.makeAnyBranch(name="foobar")
    >>> print(branch_lookup.get(branch.id).name)
    foobar

It returns None if there is no branch with the specified ID.

    >>> print(branch_lookup.get(-1))
    None


Creating branches
-----------------

Branches can be created with IBranchNamespace.createBranch, which takes
details like the type of the branch -- whether it is mirrored, hosted,
imported or remote, name, and so on.

    >>> registrant = factory.makePerson(name="registrant")
    >>> from lp.code.interfaces.branchnamespace import get_branch_namespace
    >>> namespace = get_branch_namespace(registrant, factory.makeProduct())
    >>> new_branch = namespace.createBranch(
    ...     branch_type=BranchType.MIRRORED,
    ...     name="dev",
    ...     registrant=registrant,
    ...     url=factory.getUniqueURL(),
    ... )

    >>> print(new_branch.name)
    dev

The registrant of the branch is the user that originally registered the
branch, whereas the owner is the current owner of the branch.

    >>> print(new_branch.registrant.name)
    registrant

    >>> print(new_branch.owner.name)
    registrant

A user can create a branch where the owner is either themselves, or a
team that they are a member of.  Neither the owner nor the registrant
are writable, but the owner can be set using the `setOwner` method.

    >>> login("admin@canonical.com")
    >>> new_branch.registrant = factory.makePerson()
    Traceback (most recent call last):
      ...
    zope.security.interfaces.ForbiddenAttribute: ('registrant', <Branch ...>)

    >>> team = factory.makeTeam(name="new-owner", owner=new_branch.owner)
    >>> new_branch.setOwner(new_owner=team, user=new_branch.owner)
    >>> print(new_branch.registrant.name)
    registrant

    >>> print(new_branch.owner.name)
    new-owner

Branch names must start with a number or a letter (upper or lower case)
and -, +, _ and @ are allowed after that.

    >>> owner = factory.makePerson()
    >>> namespace.createBranch(
    ...     branch_type=BranchType.HOSTED,
    ...     name="invalid name!",
    ...     registrant=registrant,
    ... )
    Traceback (most recent call last):
      ...
    lp.app.validators.LaunchpadValidationError: Invalid branch name
    &#x27;invalid name!&#x27;.  Branch ...


Determining the recently changed, registered and imported branches
------------------------------------------------------------------

The IBranchSet methods getRecentlyChangedBranches,
getRecentlyImportedBranches, and getRecentlyRegisteredBranches are used
to give summary information that is to be displayed on the
code.launchpad.net page to entice the user to click through.

Changed branches are branches that are owned by real people or groups
(as opposed to vcs-imports), and have recently had new revisions
detected by the branch scanner, either through the branch being pushed
to Launchpad or the branch puller script mirroring a remote branch.

Imported branches are those branches owned by vcs-imports, and are
"imported" from other VCS hosted code bases.  Again recently imported
branches are identified by new revisions detected by the branch scanner.

Branches that have been recently registered have either been created by
a user using the web UI, or by pushing a new branch directly to
Launchpad.

In order to determine changes in the branches the last_scanned timestamp
is used.  This is set by the branch scanner when it has finished
scanning the branches and recording the branch data in the launchpad
database.  We don't want any of the branches in the sample data to mess
up our tests, so we clear the last_scanned data in all existing
branches.

    >>> from lp.services.database.interfaces import IStore
    >>> IStore(Branch).find(Branch).set(last_scanned=None)

    >>> list(branchset.getRecentlyChangedBranches(5))
    []

Now we create a few branches that we pretend were updated in a definite
order.

    >>> from datetime import datetime, timezone
    >>> from lp.testing import time_counter
    >>> today = datetime.now(timezone.utc)
    >>> product = factory.makeProduct(name="product")
    >>> user = factory.makePerson(name="user")
    >>> time_generator = time_counter()

    >>> def make_new_scanned_branch(name, owner=user, branch_type=None):
    ...     """Create"""
    ...     new_branch = factory.makeProductBranch(
    ...         branch_type=branch_type,
    ...         owner=owner,
    ...         product=product,
    ...         name=name,
    ...         date_created=next(time_generator),
    ...     )
    ...     new_branch.last_scanned = new_branch.date_created
    ...

    >>> make_new_scanned_branch("oldest")
    >>> make_new_scanned_branch("middling")
    >>> make_new_scanned_branch("young")
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    >>> make_new_scanned_branch(
    ...     "imported", owner=vcs_imports, branch_type=BranchType.IMPORTED
    ... )

    >>> for branch in branchset.getRecentlyChangedBranches(5):
    ...     print(branch.unique_name)
    ...
    ~user/product/young
    ~user/product/middling
    ~user/product/oldest

    >>> for branch in branchset.getRecentlyImportedBranches(5):
    ...     print(branch.unique_name)
    ...
    ~vcs-imports/product/imported

    >>> for branch in branchset.getRecentlyRegisteredBranches(3):
    ...     print(branch.unique_name)
    ...
    ~vcs-imports/product/imported
    ~user/product/young
    ~user/product/middling


Finding a branch by URL
-----------------------

It is possible to find a branch by URL. Either using the pull URL:

    >>> new_url = factory.getUniqueURL()
    >>> new_mirrored_branch = factory.makeAnyBranch(
    ...     branch_type=BranchType.MIRRORED, url=new_url
    ... )
    >>> branch_lookup.getByUrl(new_url) == new_mirrored_branch
    True

Or using the URL of the mirror of the branch on Launchpad:

    >>> new_branch_mirrored = (
    ...     "http://bazaar.launchpad.test/" + new_mirrored_branch.unique_name
    ... )
    >>> branch_lookup.getByUrl(new_branch_mirrored) == new_mirrored_branch
    True

    >>> new_junk_branch = factory.makePersonalBranch()
    >>> junkcode_mirrored = (
    ...     "http://bazaar.launchpad.test/" + new_junk_branch.unique_name
    ... )
    >>> branch_lookup.getByUrl(junkcode_mirrored) == new_junk_branch
    True

If no branch is found for the specified URL, getByUrl returns None.

    >>> not_there_url = factory.getUniqueURL()
    >>> print(branch_lookup.getByUrl(not_there_url))
    None


Branch names
------------

Branches have a display name that is the bzr_identity.

    >>> untitled_branch = factory.makeAnyBranch(title=None)
    >>> untitled_branch.displayname == untitled_branch.bzr_identity
    True


Branch subscriptions
--------------------

Branch subscriptions have attributes associated with them. The
notification_level is used to control what email is sent to the
subscribed user, and max_diff_lines is used to control the size of any
generated diffs between revisions that are emailed out.  The
review_level controls the amount of notification caused by code review
activities.

Both of these attributes are contolled through the UI through the use of
the enumerated types: BranchSubscriptionDiffSize, and
BranchSubscriptionNotificationLevel.

    >>> from lp.code.enums import (
    ...     BranchSubscriptionDiffSize,
    ...     BranchSubscriptionNotificationLevel,
    ...     CodeReviewNotificationLevel,
    ... )
    >>> subscriber = factory.makePerson(name="subscriber")
    >>> branch = factory.makeProductBranch(
    ...     owner=user, product=product, name="subscribed"
    ... )
    >>> subscription = branch.subscribe(
    ...     subscriber,
    ...     BranchSubscriptionNotificationLevel.FULL,
    ...     BranchSubscriptionDiffSize.FIVEKLINES,
    ...     CodeReviewNotificationLevel.FULL,
    ...     subscriber,
    ... )
    >>> verifyObject(IBranchSubscription, subscription)
    True

    >>> subscription.branch == branch and subscription.person == subscriber
    True

    >>> print(subscription.notification_level.name)
    FULL

    >>> subscription.max_diff_lines == BranchSubscriptionDiffSize.FIVEKLINES
    True

    >>> subscription.review_level == CodeReviewNotificationLevel.FULL
    True

    >>> branch.subscriptions[1] == subscription
    True

    >>> set(branch.subscribers) == set([branch.owner, subscriber])
    True

    >>> from lp.services.webapp import canonical_url
    >>> print(canonical_url(subscription))
    http://code...test/~user/product/subscribed/+subscription/subscriber

The settings for a subscription can be changed by re-subscribing.

    >>> subscription1 = branch.getSubscription(subscriber)
    >>> subscription1.review_level == CodeReviewNotificationLevel.FULL
    True

    >>> subscription2 = branch.subscribe(
    ...     subscriber,
    ...     BranchSubscriptionNotificationLevel.FULL,
    ...     BranchSubscriptionDiffSize.FIVEKLINES,
    ...     CodeReviewNotificationLevel.NOEMAIL,
    ...     subscriber,
    ... )
    >>> subscription == subscription2
    True

    >>> subscription2.review_level == CodeReviewNotificationLevel.NOEMAIL
    True

    Unsubscribing is also supported.

    >>> branch.unsubscribe(subscriber, subscriber)
    >>> branch.subscribers.count()
    1

We can get the subscribers for a branch based on their level of
subscription.

    >>> branch2 = factory.makeProductBranch(
    ...     owner=user, product=product, name="subscribed2"
    ... )

    >>> def print_names(persons):
    ...     """Print the name of each person on a new line."""
    ...     for person in persons:
    ...         print(person.person.name)
    ...

    >>> subscription = branch2.subscribe(
    ...     subscriber,
    ...     BranchSubscriptionNotificationLevel.FULL,
    ...     BranchSubscriptionDiffSize.FIVEKLINES,
    ...     CodeReviewNotificationLevel.NOEMAIL,
    ...     subscriber,
    ... )

    >>> print_names(
    ...     branch2.getSubscriptionsByLevel(
    ...         [BranchSubscriptionNotificationLevel.FULL]
    ...     )
    ... )
    subscriber

    >>> print_names(
    ...     branch2.getSubscriptionsByLevel(
    ...         [BranchSubscriptionNotificationLevel.DIFFSONLY]
    ...     )
    ... )

    >>> print_names(
    ...     branch2.getSubscriptionsByLevel(
    ...         [
    ...             BranchSubscriptionNotificationLevel.DIFFSONLY,
    ...             BranchSubscriptionNotificationLevel.FULL,
    ...         ]
    ...     )
    ... )
    subscriber


Branch references
-----------------

When new references to the branch table are added, these need to be
taken into consideration with branch deletion.

The current references to the branch table are shown here.

    >>> from lp.services.database import postgresql
    >>> from lp.services.database.sqlbase import cursor
    >>> cur = cursor()
    >>> references = list(postgresql.listReferences(cur, "branch", "id"))

    >>> listing = sorted(
    ...     [
    ...         "%s.%s" % (src_tab, src_col)
    ...         for src_tab, src_col, ref_tab, ref_col, updact, delact in references  # noqa
    ...     ]
    ... )
    >>> for name in listing:
    ...     print(name)
    ...
    branch.stacked_on
    branchjob.branch
    branchmergeproposal.dependent_branch
    branchmergeproposal.source_branch
    branchmergeproposal.target_branch
    branchrevision.branch
    branchsubscription.branch
    bugbranch.branch
    codeimport.branch
    productseries.branch
    productseries.translations_branch
    seriessourcepackagebranch.branch
    snap.branch
    sourcepackagerecipedata.base_branch
    sourcepackagerecipedatainstruction.branch
    specificationbranch.branch
    translationtemplatesbuild.branch
    webhook.branch

(Unfortunately, references can form a cycle-- note that
codereviewcomments

 aren't shown.)


