Milestones
==========

A milestone is a significant event in a project. In Malone, milestones
can be defined to assign bug fixes to a specific release of some
software.

This document is about milestones in Malone.


Working with Milestones in Malone
---------------------------------

All Milestone creation and retrieval is done through IMilestoneSet.
IMilestoneSet can be accessed as a utility.

    >>> from lp.registry.interfaces.milestone import IMilestoneSet
    >>> milestoneset = getUtility(IMilestoneSet)

To retrieve all milestones, iterate over an IMilestoneSet object:

    >>> sorted(ms.id for ms in milestoneset)
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

To create a new Milestone, use the .newMilestone(name,
dateexpected=None) method of a ProductSeries or DistroSeries:

    >>> from lp.registry.interfaces.product import IProductSet
    >>> productset = getUtility(IProductSet)
    >>> upstream_firefox = productset.get(4)
    >>> ff_onedotzero = upstream_firefox.getSeries('1.0')

    # Only owners, experts, or admins can create a milestone.

    >>> login('test@canonical.com')
    >>> firefox_ms = ff_onedotzero.newMilestone(
    ...     name="1.0rc1", code_name="Candidate One",
    ...     summary="A beta version that is feature complete.")
    >>> print(firefox_ms.name)
    1.0rc1

Milestone's have many descriptive names. The name and code_name are
atomic attributes. The display and and title attributes are composed.

    >>> print(firefox_ms.name)
    1.0rc1

    >>> print(firefox_ms.code_name)
    Candidate One

    >>> print(firefox_ms.displayname)
    Mozilla Firefox 1.0rc1

    >>> print(firefox_ms.title)
    Mozilla Firefox 1.0rc1 "Candidate One"

The summary describes the intent of the milestone.

    >>> print(firefox_ms.summary)
    A beta version that is feature complete.

A milestones can access their product and series targets.

    >>> print(firefox_ms.target.displayname)
    Mozilla Firefox

    >>> print(firefox_ms.series_target.name)
    1.0

To retrieve a specific Milestone, use IMilestoneSet.get:

    >>> firefox_ms_1_0 = milestoneset.get(1)
    >>> print(firefox_ms_1_0.name)
    1.0

    >>> print(firefox_ms_1_0.displayname)
    Mozilla Firefox 1.0

Of course, you can also get them off a Product or Distribution using the
getMilestone() method:

    >>> ms = upstream_firefox.getMilestone('1.0rc1')
    >>> print(ms.name)
    1.0rc1

Trying to retrieve a milestone that does not exist from a product will
return None:

    >>> non_ms = upstream_firefox.getMilestone('0.99x1')
    >>> print(non_ms)
    None

Now, lets test all of that for DistroSeriess too!

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> kubuntu = getUtility(IDistributionSet).getByName('kubuntu')
    >>> krunch = kubuntu.getSeries('krunch')

    # Only owners, experts, or admins can create a milestone.

    >>> login('mark@example.com')
    >>> new_ms = krunch.newMilestone('1.3rc2')
    >>> print(new_ms.name)
    1.3rc2

    >>> print(new_ms.code_name)
    None

    >>> print(new_ms.displayname)
    Kubuntu 1.3rc2

    >>> print(new_ms.title)
    Kubuntu 1.3rc2

    >>> print(new_ms.target.name)
    kubuntu

    >>> print(new_ms.series_target.name)
    krunch

    >>> print(kubuntu.getMilestone('foo2.3'))
    None

    >>> print(kubuntu.getMilestone('1.3rc2').dateexpected)
    None

Trying to retrieve a milestone that doesn't exist will raise a
zope.exceptions.NotFoundError:

    >>> milestoneset.get(-1)
    Traceback (most recent call last):
      ...
    lp.app.errors.NotFoundError: 'Milestone with ID -1 does not exist'


ProjectGroup Milestones
-----------------------

The database associates milestones only with products and distroseries.
The interface IProjectGroupMilestone provides a virtual view of
milestones that are related to a project by collecting all milestones
that are associated with products that belong to a project.

The class ProjectMilestone collects the milestone names from products
that belong to one project and creates virtual milestones for each
distinct name.

project.all_milestones returns all milestones for this project. No
product belonging to the Gnome project has any milestones, hence Gnome
itself has neither any milestones.

    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> gnome = getUtility(IProjectGroupSet)['gnome']
    >>> for product in gnome.products:
    ...     print('%s %s' % (
    ...         product.name,
    ...         pretty([milestone.title
    ...                 for milestone in product.all_milestones])))
    evolution ['Evolution 2.1.6']
    gnome-terminal []
    applets []
    netapplet ['NetApplet 1.0']
    gnomebaker []

    >>> for milestone in gnome.all_milestones:
    ...     print(milestone.title)
    GNOME 2.1.6
    GNOME 1.0

When a milestone for a product is defined, this milestone is "inherited"
by the project.

    >>> from lp.registry.tests.test_project_milestone import (
    ...     ProjectMilestoneTest)
    >>> test_helper = ProjectMilestoneTest(helper_only=True)
    >>> evolution_1_1 = test_helper.createProductMilestone(
    ...     '1.1', 'evolution', date_expected=None)
    >>> evolution = productset['evolution']
    >>> for milestone in evolution.all_milestones:
    ...     print(milestone.name)
    2.1.6
    1.1

    >>> for milestone in gnome.all_milestones:
    ...     print(milestone.name)
    2.1.6
    1.1
    1.0

Adding a milestone with the same name to another Gnome product does not
increase the number of Gnome milestones.

    >>> applets_1_1 = test_helper.createProductMilestone(
    ...     '1.1', 'applets', date_expected=None)
    >>> applets = productset['applets']
    >>> for milestone in applets.all_milestones:
    ...     print(milestone.name)
    1.1

    >>> for milestone in gnome.all_milestones:
    ...     print(milestone.name)
    2.1.6
    1.1
    1.0

Since project milestones are generated from the names of the product
milestones, milestone names with typos like '1.1.' instead of '1.1' will
appear as separate project milestones.

    >>> netapplet_1_1 = test_helper.createProductMilestone(
    ...     '1.1.', 'netapplet', date_expected=None)
    >>> netapplet = productset['netapplet']
    >>> for milestone in netapplet.all_milestones:
    ...     print(milestone.name)
    1.1.
    1.0

    >>> for milestone in gnome.all_milestones:
    ...     print(milestone.name)
    2.1.6
    1.1.
    1.1
    1.0

A project milestone has the same attributes as product and distribution
milestones, but most are None because project milestones are
aggregations. The code_name and series attributes are always none.

    >>> project_milestone = gnome.all_milestones[0]
    >>> print(project_milestone.name)
    2.1.6

    >>> print(project_milestone.code_name)
    None

    >>> print(project_milestone.displayname)
    GNOME 2.1.6

    >>> print(project_milestone.title)
    GNOME 2.1.6

    >>> print(project_milestone.target.name)
    gnome

    >>> print(project_milestone.series_target)
    None

A project milestone is active, if at least one product milestone with
the same name is active.

    >>> print(applets_1_1.active, evolution_1_1.active)
    True True

    >>> print(gnome.getMilestone('1.1').active)
    True

    >>> applets_1_1.active = False
    >>> print(gnome.getMilestone('1.1').active)
    True

    >>> evolution_1_1.active = False
    >>> print(gnome.getMilestone('1.1').active)
    False

A project milestone is not shown for active milestones from inactive
products.

    >>> for milestone in gnome.milestones:
    ...     print(milestone.name)
    1.1.

    # Unlink the source packages so the project can be deactivated.

    >>> from lp.testing import unlink_source_packages
    >>> unlink_source_packages(netapplet)
    >>> netapplet.active = False
    >>> print([milestone.name for milestone in gnome.milestones])
    []

    # Reset the product back to original status so future tests pass.

    >>> netapplet.active = True

The dateexpected attribute is set to the minimum of the dateexpected
values of the product milestones.

    >>> print(applets_1_1.dateexpected, evolution_1_1.dateexpected)
    None None

    >>> print(gnome.getMilestone('1.1').dateexpected)
    None

    >>> from datetime import datetime
    >>> applets_1_1.dateexpected = datetime(2007, 4, 2)
    >>> print(gnome.getMilestone('1.1').dateexpected)
    2007-04-02 00:00:00

    >>> evolution_1_1.dateexpected = datetime(2007, 4, 1)
    >>> print(gnome.getMilestone('1.1').dateexpected)
    2007-04-01 00:00:00

All bugtasks that are associated with a product milestone are also
associated with the project milestone of the same name. For details, see
bugtask-search.rst

All specifications that are associated with a product milestone are also
associated with the project milestone of the same name. No product of
the Gnome project has yet any specifications.

    >>> for product in gnome.products:
    ...     print(product.name, list(product.visible_specifications))
    evolution []
    gnome-terminal []
    applets []
    netapplet []
    gnomebaker []

    >>> print(list(gnome.getMilestone('1.1').getSpecifications(None)))
    []

When a specification for a product is created and assigned to a product
milestone, it is "inheritied" by the project milestone.

    >>> spec = test_helper.createSpecification('1.1', 'applets')
    >>> for spec in applets.visible_specifications:
    ...     print(spec.name)
    applets-specification

    >>> specs = gnome.getMilestone('1.1').getSpecifications(None)
    >>> for spec in specs:
    ...     print(spec.name)
    applets-specification


Target change notifications
---------------------------

When we change the milestone for a bug task, subscribers to both the old
milestone and the new one are notified.

    >>> from lp.bugs.model.bugnotification import BugNotification
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.services.webapp.snapshot import notify_modified
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> firefox_trunk = firefox.getSeries('trunk')
    >>> [milestone_one] = [milestone
    ...                    for milestone in firefox_trunk.milestones
    ...                    if milestone.name == '1.0']
    >>> milestone_two = firefox_trunk.newMilestone('2.0')
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> bug_task = bug_one.bugtasks[0]
    >>> bug_task.milestone = milestone_one

The first task of bug #1 is targeted to milestone 1.0. Celso is
subscribed to milestone 1.0, and David is subscribed to milestone 2.0.

    >>> cprov = getUtility(IPersonSet).getByName('cprov')
    >>> ddaa = getUtility(IPersonSet).getByName('ddaa')
    >>> milestone_one.addBugSubscription(cprov, cprov)
    <...StructuralSubscription object at ...>

    >>> milestone_two.addBugSubscription(ddaa, ddaa)
    <...StructuralSubscription object at ...>

We change the milestone for the task from 1.0 to 2.0, and fire the
change event.

    >>> with notify_modified(bug_task, ['milestone']):
    ...     bug_task.milestone = milestone_two

A new bug notification is created, and both Celso and David are in the
list of recipients.

    >>> from lp.services.database.interfaces import IStore
    >>> notification = IStore(BugNotification).find(
    ...     BugNotification, date_emailed=None).order_by('id').last()
    >>> print(notification.message.chunks[0].content)
    ** Changed in: firefox
        Milestone: 1.0 => 2.0

    >>> for recipient in notification.recipients:
    ...     print(recipient.person.name, recipient.reason_header)
    cprov Subscriber (Mozilla Firefox 1.0)
    ddaa Subscriber (Mozilla Firefox 2.0)
    ...


Editing milestones
------------------

Persons with launchpad.Edit permissions for milestones may create and
edit them. These users play the roles of owners, drivers or Launchpad
admins. The name, dateexpected, summary, and active, attributes are
editable.

    >>> ignored = login_person(upstream_firefox.owner)
    >>> fizzy_milestone = ff_onedotzero.newMilestone('fuzzy')

    >>> print(fizzy_milestone.name)
    fuzzy

    >>> fizzy_milestone.name = 'fizzy'
    >>> print(fizzy_milestone.name)
    fizzy

    >>> print(fizzy_milestone.code_name)
    None

    >>> fizzy_milestone.code_name = 'dizzy'
    >>> print(fizzy_milestone.code_name)
    dizzy

    >>> fizzy_milestone.summary = 'fizzy love'
    >>> print(fizzy_milestone.summary)
    fizzy love

    >>> date = datetime(2007, 4, 2)
    >>> fizzy_milestone.dateexpected = date
    >>> fizzy_milestone.dateexpected
    datetime.date(2007, 4, 2)

    >>> fizzy_milestone.active
    True

    >>> fizzy_milestone.active = False
    >>> fizzy_milestone.active
    False

The productseries attribute can be edited if the milestones belongs to a
product.

    >>> print(fizzy_milestone.productseries.name)
    1.0

    >>> two_series = upstream_firefox.newSeries(
    ...     upstream_firefox.owner, '2.0', 'Two dot n')
    >>> fizzy_milestone.productseries = two_series
    >>> print(fizzy_milestone.productseries.name)
    2.0

The driver of a milestone's target or series can make changes.

    >>> from lp.services.webapp.authorization import check_permission

    >>> driver = factory.makePerson(name='driver')
    >>> fizzy_milestone.target.driver = driver

    >>> release_manager = factory.makePerson(name='release-manager')
    >>> fizzy_milestone.series_target.driver = release_manager

    >>> ignored = login_person(driver)
    >>> check_permission('launchpad.Edit', fizzy_milestone)
    True

    >>> ignored = login_person(release_manager)
    >>> check_permission('launchpad.Edit', fizzy_milestone)
    True


Deleting a milestone
--------------------

A milestone can be deleted using its destroySelf() method, as long as it
doesn't have an IProductRelease associated with it, nor any bugtasks or
specifications targeted to it.

    >>> owner = getUtility(IPersonSet).getByName('name12')
    >>> ignored = login_person(owner)
    >>> milestone = ff_onedotzero.newMilestone('1.0.10')
    >>> print(milestone.product_release)
    None

    >>> milestone.destroySelf()
    >>> print(upstream_firefox.getMilestone('1.0.10'))
    None

If a milestone has a product release associated with it though, it can
not be deleted.

    >>> from datetime import datetime
    >>> from pytz import UTC

    >>> milestone = ff_onedotzero.newMilestone('1.0.11')
    >>> release = milestone.createProductRelease(
    ...     owner, datetime.now(UTC))
    >>> milestone.destroySelf()
    Traceback (most recent call last):
    ...
    AssertionError: You cannot delete a milestone which has a product release
                    associated with it.

If bugtasks are targeted to the milestone, it cannot be deleted.

    >>> milestone = ff_onedotzero.newMilestone('1.0.12')
    >>> bug = factory.makeBug(target=upstream_firefox)
    >>> bugtask = bug.bugtasks[0]
    >>> bugtask.milestone = milestone
    >>> milestone.destroySelf()
    Traceback (most recent call last):
    ...
    AssertionError: You cannot delete a milestone which has bugtasks
                    targeted to it.

If specifications are targeted to the milestone, it cannot be deleted.

    >>> milestone = ff_onedotzero.newMilestone('1.0.13')
    >>> specification = factory.makeSpecification(product=upstream_firefox)
    >>> specification.milestone = milestone
    >>> milestone.destroySelf()
    Traceback (most recent call last):
    ...
    AssertionError: You cannot delete a milestone which has specifications
                    targeted to it.

If a milestone has a structural subscription, it cannot be deleted.

    >>> milestone = ff_onedotzero.newMilestone('1.0.14')
    >>> subscription = milestone.addSubscription(owner, owner)
    >>> milestone.destroySelf()
    Traceback (most recent call last):
    ...
    AssertionError: You cannot delete a milestone which has structural
                    subscriptions.


Closing milestone targeted bugs
-------------------------------

When a milestone with bug tasks creates a release, those bug tasks in
fix committed status are updated to fix released. An ObjectModifiedEvent
event is signaled for each changed bug task.

    >>> from lazr.lifecycle.interfaces import IObjectModifiedEvent
    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus, IBugTask
    >>> from lp.testing.fixture import ZopeEventHandlerFixture

    >>> def print_event(object, event):
    ...     print("Received %s on %s" % (
    ...         event.__class__.__name__.split('.')[-1],
    ...         object.__class__.__name__.split('.')[-1]))

    >>> milestone = ff_onedotzero.newMilestone('kia')
    >>> fixed_bugtask = factory.makeBugTask(target=upstream_firefox)
    >>> fixed_bugtask.transitionToMilestone(milestone, owner)
    >>> fixed_bugtask.transitionToStatus(BugTaskStatus.FIXCOMMITTED, owner)
    >>> triaged_bugtask = factory.makeBugTask(target=upstream_firefox)
    >>> triaged_bugtask.transitionToMilestone(milestone, owner)
    >>> triaged_bugtask.transitionToStatus(BugTaskStatus.TRIAGED, owner)
    >>> release = milestone.createProductRelease(owner, datetime.now(UTC))
    >>> bugtask_event_listener = ZopeEventHandlerFixture(
    ...     print_event, (IBugTask, IObjectModifiedEvent))
    >>> bugtask_event_listener.setUp()

    >>> milestone.closeBugsAndBlueprints(owner)
    Received ObjectModifiedEvent on BugTask

    >>> fixed_bugtask.status
    <DBItem BugTaskStatus.FIXRELEASED, (30) Fix Released>

    >>> triaged_bugtask.status
    <DBItem BugTaskStatus.TRIAGED, (21) Triaged>

    >>> bugtask_event_listener.cleanUp()


