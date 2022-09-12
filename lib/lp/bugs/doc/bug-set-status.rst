Setting the status of a bug
===========================

If you have a bug and a target, there's method which makes it easier to
change the bug's status for that specific target. It expects the user
changing the status, the target, and the new status.

    >>> from lp.testing.dbuser import lp_dbuser
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> from lp.registry.interfaces.product import IProductSet

    >>> with lp_dbuser():
    ...     login("no-priv@canonical.com")
    ...     no_priv = getUtility(IPersonSet).getByName("no-priv")
    ...     bug_params = CreateBugParams(
    ...         owner=no_priv,
    ...         title="Sample bug",
    ...         comment="This is a sample bug.",
    ...     )
    ...     firefox = getUtility(IProductSet).getByName("firefox")
    ...     bug = firefox.createBug(bug_params)
    ...     bug_id = bug.id
    ...     # Set a milestone to ensure that the current db user has enough
    ...     # privileges to access it.
    ...     [firefox_task] = bug.bugtasks
    ...     firefox_task.milestone = firefox.getMilestone("1.0")
    ...

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> bug = getUtility(IBugSet).get(bug_id)
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> firefox_bugtask = bug.setStatus(
    ...     firefox, BugTaskStatus.CONFIRMED, no_priv
    ... )

It returns the edited bugtask.

    >>> print(firefox_bugtask.target.name)
    firefox
    >>> firefox_bugtask.status.name
    'CONFIRMED'

It also emits an ObjectModifiedEvent so that BugNotification and
BugActivity records are created.

    >>> from lp.bugs.model.bugnotification import BugNotification
    >>> from lp.services.database.interfaces import IStore
    >>> latest_notification = (
    ...     IStore(BugNotification)
    ...     .find(BugNotification)
    ...     .order_by(BugNotification.id)
    ...     .last()
    ... )
    >>> print(latest_notification.message.owner.displayname)
    No Privileges Person
    >>> print(latest_notification.message.text_contents)
    ** Changed in: firefox
           Status: New => Confirmed

    >>> from lp.bugs.model.bugactivity import BugActivity
    >>> from lp.services.database.interfaces import IStore
    >>> latest_activity = (
    ...     IStore(BugActivity)
    ...     .find(BugActivity)
    ...     .order_by(BugActivity.id)
    ...     .last()
    ... )
    >>> print(latest_activity.whatchanged)
    firefox: status
    >>> print(latest_activity.oldvalue)
    New
    >>> print(latest_activity.newvalue)
    Confirmed

The edited bugtask is only returned if it's actually edited. If the
bugtask already has the specified status, None is returned.

    >>> firefox_bugtask.status.name
    'CONFIRMED'
    >>> print(bug.setStatus(firefox, BugTaskStatus.CONFIRMED, no_priv))
    None

Product series
..............

If a product series is specified, but the bug is target only to the
product, not the product series, the product bugtask is edited.

    >>> firefox_trunk = firefox.getSeries("trunk")
    >>> bug.getBugTask(firefox_trunk) is None
    True
    >>> firefox_bugtask = bug.setStatus(
    ...     firefox_trunk, BugTaskStatus.NEW, no_priv
    ... )
    >>> print(firefox_bugtask.target.name)
    firefox
    >>> firefox_bugtask.status.name
    'NEW'

If the bug is targeted to the product series, the product series bugtask
is edited.

    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> with lp_dbuser():
    ...     bug = getUtility(IBugSet).get(bug_id)
    ...     no_priv = getUtility(IPersonSet).getByName("no-priv")
    ...     firefox = getUtility(IProductSet).getByName("firefox")
    ...     firefox_trunk = firefox.getSeries("trunk")
    ...     ignore = getUtility(IBugTaskSet).createTask(
    ...         bug, no_priv, firefox_trunk
    ...     )
    ...

    >>> bug = getUtility(IBugSet).get(bug_id)
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> firefox_trunk = firefox.getSeries("trunk")
    >>> firefox_trunk_bugtask = bug.setStatus(
    ...     firefox_trunk, BugTaskStatus.INCOMPLETE, no_priv
    ... )

    >>> print(firefox_trunk_bugtask.target.name)
    trunk
    >>> firefox_trunk_bugtask.status.name
    'INCOMPLETE'

If the target bugtask has a conjoined primary bugtask, the conjoined
primary will be edited and returned. The conjoined replica is of course
updated automatically.

    >>> firefox_bugtask = firefox_trunk_bugtask.conjoined_replica
    >>> print(firefox_bugtask.target.name)
    firefox
    >>> firefox_bugtask.conjoined_primary is not None
    True
    >>> firefox_bugtask.status.name
    'INCOMPLETE'
    >>> firefox_trunk_bugtask = bug.setStatus(
    ...     firefox_bugtask.target, BugTaskStatus.CONFIRMED, no_priv
    ... )
    >>> print(firefox_trunk_bugtask.target.name)
    trunk
    >>> firefox_trunk_bugtask.status.name
    'CONFIRMED'
    >>> firefox_bugtask.status.name
    'CONFIRMED'

Distributions and packages
..........................

Setting the status of a distribution or package bugtask work the same as
for product tasks.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> with lp_dbuser():
    ...     ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    ...     # Set a milestone to ensure that the current db user has enough
    ...     # privileges to access it.
    ...     ubuntu_hoary = ubuntu.getSeries("hoary")
    ...     # Only owners, experts, or admins can create a milestone.
    ...     login("foo.bar@canonical.com")
    ...     feature_freeze = ubuntu_hoary.newMilestone("feature-freeze")
    ...     login("no-priv@canonical.com")
    ...     bug = ubuntu.createBug(bug_params)
    ...     [ubuntu_bugtask] = bug.bugtasks
    ...     ubuntu_bugtask.milestone = feature_freeze
    ...     bug_id = bug.id
    ...

    >>> bug = getUtility(IBugSet).get(bug_id)
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> ubuntu_bugtask = bug.setStatus(
    ...     ubuntu, BugTaskStatus.CONFIRMED, no_priv
    ... )
    >>> print(ubuntu_bugtask.target.name)
    ubuntu
    >>> ubuntu_bugtask.status.name
    'CONFIRMED'

If a source package is given, but no such package exists, no bugtask
will be edited.

    >>> ubuntu_firefox = ubuntu.getSourcePackage("mozilla-firefox")
    >>> bug.setStatus(
    ...     ubuntu_firefox, BugTaskStatus.CONFIRMED, no_priv
    ... ) is None
    True

If the bug is targeted to a source package, that bugtask is of course
edited.

    # Need to be privileged user to transition the target.
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> login("foo.bar@canonical.com")
    >>> ubuntu_bugtask.transitionToTarget(
    ...     ubuntu_firefox, getUtility(ILaunchBag).user
    ... )
    >>> ubuntu_firefox_task = bug.setStatus(
    ...     ubuntu_firefox, BugTaskStatus.INCOMPLETE, no_priv
    ... )
    >>> print(ubuntu_firefox_task.target.displayname)
    mozilla-firefox in Ubuntu
    >>> ubuntu_firefox_task.status.name
    'INCOMPLETE'

If a distro series is given, but the bug is only targeted to the
distribution and not to the distro series, the distribution task is
edited.

    >>> ubuntu_warty = ubuntu.getSeries("warty")
    >>> warty_firefox = ubuntu_warty.getSourcePackage("mozilla-firefox")
    >>> ubuntu_firefox_task = bug.setStatus(
    ...     warty_firefox, BugTaskStatus.CONFIRMED, no_priv
    ... )
    >>> print(ubuntu_firefox_task.target.displayname)
    mozilla-firefox in Ubuntu
    >>> ubuntu_firefox_task.status.name
    'CONFIRMED'

    >>> ubuntu_hoary = ubuntu.getSeries("hoary")
    >>> hoary_firefox = ubuntu_hoary.getSourcePackage("mozilla-firefox")
    >>> ubuntu_firefox_task = bug.setStatus(
    ...     hoary_firefox, BugTaskStatus.NEW, no_priv
    ... )
    >>> print(ubuntu_firefox_task.target.displayname)
    mozilla-firefox in Ubuntu
    >>> ubuntu_firefox_task.status.name
    'NEW'

However, if the bug is targeted to the current series, passing a
non-current series won't modify any bugtask, unless the bug is already
targeted to the non-current series of course.

    >>> print(ubuntu.currentseries.name)
    hoary

    # Need to be privileged user to target the bug to a series.
    >>> login("foo.bar@canonical.com")
    >>> with lp_dbuser():
    ...     bug = getUtility(IBugSet).get(bug_id)
    ...     ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    ...     ubuntu_hoary = ubuntu.getSeries("hoary")
    ...     nomination = bug.addNomination(
    ...         getUtility(ILaunchBag).user, ubuntu_hoary
    ...     )
    ...     nomination.approve(getUtility(ILaunchBag).user)
    ...
    >>> login("no-priv@canonical.com")

    >>> bug = getUtility(IBugSet).get(bug_id)
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> ubuntu_warty = ubuntu.getSeries("warty")
    >>> warty_firefox = ubuntu_warty.getSourcePackage("mozilla-firefox")
    >>> bug.setStatus(
    ...     warty_firefox, BugTaskStatus.INCOMPLETE, no_priv
    ... ) is None
    True

    >>> login("foo.bar@canonical.com")
    >>> with lp_dbuser():
    ...     bug = getUtility(IBugSet).get(bug_id)
    ...     ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    ...     ubuntu_warty = ubuntu.getSeries("warty")
    ...     nomination = bug.addNomination(
    ...         getUtility(ILaunchBag).user, ubuntu_warty
    ...     )
    ...     nomination.approve(getUtility(ILaunchBag).user)
    ...
    >>> login("no-priv@canonical.com")

    >>> bug = getUtility(IBugSet).get(bug_id)
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> ubuntu_warty = ubuntu.getSeries("warty")
    >>> warty_firefox = ubuntu_warty.getSourcePackage("mozilla-firefox")
    >>> ubuntu_firefox_task = bug.setStatus(
    ...     warty_firefox, BugTaskStatus.INCOMPLETE, no_priv
    ... )
    >>> print(ubuntu_firefox_task.target.displayname)
    mozilla-firefox in Ubuntu Warty
    >>> ubuntu_firefox_task.status.name
    'INCOMPLETE'
