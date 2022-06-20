This file lists all the karma events that Malone produces. First let's
import some stuff and define a function to help us make the
documentation cleaner:

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.karma import IKarmaActionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> foo_bar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')

Setup an event listener to help ensure karma is assigned when it should.

    >>> from zope.event import notify
    >>> from lp.testing.karma import KarmaAssignedEventListener
    >>> karma_helper = KarmaAssignedEventListener()
    >>> karma_helper.register_listener()

Foo Bar is the one that will get all the karma:

    >>> login('foo.bar@canonical.com')


Karma Actions
-------------

Create a bug:

    >>> from lazr.lifecycle.event import ObjectCreatedEvent
    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> debian = getUtility(IDistributionSet).getByName('debian')
    >>> params = CreateBugParams(
    ...     comment=u"Give me some karma!", title=u"New Bug", owner=foo_bar)
    >>> bug = debian.createBug(params)
    Karma added: action=bugcreated, distribution=debian

Change the title of a bug:

    >>> from lp.services.webapp.snapshot import notify_modified
    >>> with notify_modified(bug, ['title']):
    ...     bug.title = "Better Title"
    Karma added: action=bugtitlechanged, distribution=debian

Change the description of a bug:

    >>> with notify_modified(bug, ['description']):
    ...     bug.description = "Description of bug"
    Karma added: action=bugdescriptionchanged, distribution=debian

Add a CVE reference to a bug:

    >>> from lp.bugs.interfaces.cve import CveStatus, ICveSet
    >>> cve = getUtility(ICveSet).new('2003-1234', description="Blah blah",
    ...     status=CveStatus.CANDIDATE)
    >>> cve.linkBug(bug)
    Karma added: action=bugcverefadded, distribution=debian
    True

Link a merge proposal to a bug:

    >>> dsp = factory.makeDistributionSourcePackage(distribution=debian)
    >>> merge_proposal = factory.makeBranchMergeProposalForGit(target=dsp)
    Karma added: action=branchmergeproposed, distribution=debian
    >>> bug.linkMergeProposal(merge_proposal, getUtility(ILaunchBag).user)
    Karma added: action=bugbranchcreated, distribution=debian

Add watch for external bug to the bug:

    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerSet
    >>> from lp.bugs.model.bugwatch import BugWatch
    >>> debbugs = getUtility(IBugTrackerSet)['debbugs']
    >>> bugwatch = BugWatch(
    ...     bug=bug,bugtracker=debbugs, remotebug=u'42', owner=foo_bar)
    >>> notify(ObjectCreatedEvent(bugwatch))
    Karma added: action=bugwatchadded, distribution=debian

Mark a bug task as fixed:

    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> bugtask = bug.bugtasks[0]
    >>> with notify_modified(bugtask, ['status']):
    ...     bugtask.transitionToStatus(
    ...         BugTaskStatus.FIXRELEASED, getUtility(ILaunchBag).user)
    Karma added: action=bugfixed, distribution=debian

Mark a bug task as fixed when it is assigned awards the karma to the assignee:

    >>> ufo_product = factory.makeProduct(name='ufo')
    >>> assignee = factory.makePerson(name='assignee')
    >>> assigned_bugtask = factory.makeBugTask(bug=bug, target=ufo_product)
    >>> assigned_bugtask.transitionToAssignee(assignee)
    >>> with notify_modified(assigned_bugtask, ['status']):
    ...     assigned_bugtask.transitionToStatus(
    ...         BugTaskStatus.FIXRELEASED, getUtility(ILaunchBag).user)
    Karma added: action=bugfixed, product=ufo

    >>> for karma in assignee.latestKarma():
    ...     print(karma.action.name)
    bugfixed

Reject a bug task:

    >>> with notify_modified(bugtask, ['status']):
    ...     bugtask.transitionToStatus(
    ...         BugTaskStatus.INVALID, bugtask.target.owner)
    Karma added: action=bugrejected, distribution=debian

User accept a bug task:

    >>> with notify_modified(bugtask, ['status']):
    ...     bugtask.transitionToStatus(
    ...         BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user)
    Karma added: action=bugaccepted, distribution=debian

Driver accept a bug task:

    >>> ignored = login_person(bugtask.target.owner)
    >>> with notify_modified(bugtask, ['status']):
    ...     bugtask.transitionToStatus(
    ...         BugTaskStatus.TRIAGED, getUtility(ILaunchBag).user)
    Karma added: action=bugaccepted, distribution=debian

    >>> login('admin@canonical.com')

Change a bug task's importance:

    >>> from lp.bugs.interfaces.bugtask import BugTaskImportance
    >>> bugtask.transitionToImportance(
    ...     BugTaskImportance.HIGH, getUtility(ILaunchBag).user)
    >>> for importance in BugTaskImportance.items:
    ...     with notify_modified(bugtask, ['importance']):
    ...         bugtask.transitionToImportance(
    ...             importance, getUtility(ILaunchBag).user)
    ...         print(importance.name)
    UNKNOWN
    Karma added: action=bugtaskimportancechanged, distribution=debian
    UNDECIDED
    Karma added: action=bugtaskimportancechanged, distribution=debian
    CRITICAL
    Karma added: action=bugtaskimportancechanged, distribution=debian
    HIGH
    Karma added: action=bugtaskimportancechanged, distribution=debian
    MEDIUM
    Karma added: action=bugtaskimportancechanged, distribution=debian
    LOW
    Karma added: action=bugtaskimportancechanged, distribution=debian
    WISHLIST
    Karma added: action=bugtaskimportancechanged, distribution=debian

Create a new bug task on a product:

    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> evolution = getUtility(IProductSet)['evolution']
    >>> evolution_task = getUtility(IBugTaskSet).createTask(
    ...     bug, foo_bar, evolution)
    >>> notify(ObjectCreatedEvent(evolution_task))
    Karma added: action=bugtaskcreated, product=evolution

Create a new bug task on a product series:

    >>> evolution_trunk = evolution.getSeries('trunk')
    >>> evolution_trunk_task = getUtility(IBugTaskSet).createTask(
    ...     bug, foo_bar, evolution_trunk)
    >>> notify(ObjectCreatedEvent(evolution_trunk_task))
    Karma added: action=bugtaskcreated, product=evolution

Create a new bug task on a distroseries:

    >>> debian_woody = debian.getSeries("woody")
    >>> debian_woody_task = getUtility(IBugTaskSet).createTask(
    ...     bug, foo_bar, debian_woody)
    >>> notify(ObjectCreatedEvent(debian_woody_task))
    Karma added: action=bugtaskcreated, distribution=debian

Accept a distro series task.

    >>> debian_woody_task.transitionToStatus(
    ...     BugTaskStatus.NEW, getUtility(ILaunchBag).user)
    >>> with notify_modified(debian_woody_task, ['status']):
    ...     debian_woody_task.transitionToStatus(
    ...         BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user)
    Karma added: action=bugaccepted, distribution=debian

Accept a productseries task.

    >>> evolution_trunk_task.transitionToStatus(
    ...     BugTaskStatus.NEW, getUtility(ILaunchBag).user)
    >>> with notify_modified(evolution_trunk_task, ['status']):
    ...     evolution_trunk_task.transitionToStatus(
    ...         BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user)
    Karma added: action=bugaccepted, product=evolution

Mark a bug as a duplicate:

(Notice how changing a bug with multiple bugtasks will assign karma to you
once for each bugtask. This is so because we consider changes in a bug to
be actual contributions to all bugtasks of that bug.)

    >>> bug_one = getUtility(IBugSet).get(1)
    >>> with notify_modified(bug, ['duplicateof']):
    ...     bug.markAsDuplicate(bug_one)
    Karma added: action=bugmarkedasduplicate, product=evolution
    Karma added: action=bugmarkedasduplicate, product=evolution
    Karma added: action=bugmarkedasduplicate, product=ufo
    Karma added: action=bugmarkedasduplicate, distribution=debian
    Karma added: action=bugmarkedasduplicate, distribution=debian

Adding a comment generates a karma event, but gives no points:

    >>> from lp.bugs.interfaces.bugmessage import IBugMessageSet
    >>> comment = getUtility(IBugMessageSet).createMessage(
    ...     subject="foo", bug=bug, owner=foo_bar, content="bar")
    >>> notify(ObjectCreatedEvent(comment))
    Karma added: action=bugcommentadded, product=evolution
    Karma added: action=bugcommentadded, product=evolution
    Karma added: action=bugcommentadded, product=ufo
    Karma added: action=bugcommentadded, distribution=debian
    Karma added: action=bugcommentadded, distribution=debian

Now, let's check that we've covered all of Launchpad's bug-related karma
actions, except for updating the obsolete "summary", "priority", and "Web
links":

    >>> from lp.registry.model.karma import KarmaCategory
    >>> bugs_category = KarmaCategory.byName('bugs')
    >>> bugs_karma_actions = bugs_category.karmaactions
    >>> summary_change = getUtility(
    ...     IKarmaActionSet).getByName('bugsummarychanged')
    >>> karma_helper.added_karma_actions.add(summary_change)
    >>> priority_change = getUtility(
    ...     IKarmaActionSet).getByName('bugtaskprioritychanged')
    >>> karma_helper.added_karma_actions.add(priority_change)
    >>> link_change = getUtility(
    ...     IKarmaActionSet).getByName('bugextrefadded')
    >>> karma_helper.added_karma_actions.add(link_change)
    >>> karma_helper.added_karma_actions.issuperset(bugs_karma_actions)
    True

Unregister the event listener to make sure we won't interfere in other tests.

    >>> karma_helper.unregister_listener()

XXX Matthew Paul Thomas 2006-03-22: On 2007-03-23, a year after bug summaries
were removed, all the karma gained from updating bug summaries will have
expired. Then the 'bugsummarychanged' row should be removed from the database,
and summary_change can be removed from this test. The same applies to the
'bugtaskprioritychanged' row after about 2007-05-15, and the 'bugextrefadded'
row after about 2008-09-25.
