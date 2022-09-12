Editing Bug Tasks
=================

A bugtask's status, assignee, package name, milestone, etc., can be
modified on its +editstatus page.


Edit the Status
---------------

Let's start simple and edit the status of a bug task logged in as Sample
Person:

    >>> from zope.component import getMultiAdapter
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> login("test@canonical.com")
    >>> bug_nine = getUtility(IBugSet).get(9)
    >>> ubuntu_thunderbird_task = bug_nine.bugtasks[1]
    >>> ubuntu_thunderbird_task.status.title
    'Confirmed'

    >>> edit_form = {
    ...     "ubuntu_thunderbird.actions.save": "Save Changes",
    ...     "ubuntu_thunderbird.status": "In Progress",
    ...     "ubuntu_thunderbird.importance": (
    ...         ubuntu_thunderbird_task.importance.title
    ...     ),
    ...     "ubuntu_thunderbird.ubuntu_thunderbird.assignee.option": (
    ...         "ubuntu_thunderbird.assignee.assign_to_nobody"
    ...     ),
    ... }
    >>> request = LaunchpadTestRequest(method="POST", form=edit_form)
    >>> edit_view = getMultiAdapter(
    ...     (ubuntu_thunderbird_task, request), name="+editstatus"
    ... )
    >>> edit_view.initialize()
    >>> ubuntu_thunderbird_task.status.title
    'In Progress'


Edit the Package
----------------

When editing the package of a distribution task, the user may enter
either a binary or a source package name. We only deal with bugs on
source packages, though, so if a binary name is entered, it gets mapped
to the correct source package. For example, the binary package
linux-2.6.12 is built from the source package linux-source-2.6.15, so
if linux-2.6.12 is entered in the package field, the bugtask will be
assigned to linux-source-2.6.15 instead.


    >>> ubuntu_thunderbird = ubuntu_thunderbird_task.target
    >>> edit_form["ubuntu_thunderbird.target"] = "package"
    >>> edit_form["ubuntu_thunderbird.target.distribution"] = "ubuntu"
    >>> edit_form["ubuntu_thunderbird.target.package"] = "linux-2.6.12"
    >>> request = LaunchpadTestRequest(method="POST", form=edit_form)
    >>> edit_view = getMultiAdapter(
    ...     (ubuntu_thunderbird_task, request), name="+editstatus"
    ... )
    >>> edit_view.initialize()
    >>> print(ubuntu_thunderbird_task.sourcepackagename.name)
    linux-source-2.6.15

A notification was added informing the user that the binary package was
changed to the corresponding source package.

    >>> for notification in edit_view.request.response.notifications:
    ...     print(notification.message)
    ...
    &#x27;linux-2.6.12&#x27; is a binary package. This bug has been
    assigned to its source package &#x27;linux-source-2.6.15&#x27;
    instead.

The sampledata is bad -- the original thunderbird task should not exist, as
there is no publication. Create one so we can set it back.

    >>> ignored = factory.makeSourcePackagePublishingHistory(
    ...     distroseries=ubuntu_thunderbird_task.target.distribution.currentseries,  # noqa
    ...     sourcepackagename="thunderbird",
    ... )
    >>> ubuntu_thunderbird_task.transitionToTarget(
    ...     ubuntu_thunderbird, getUtility(ILaunchBag).user
    ... )

If we try to change the source package to package name that doesn't
exist in Launchpad. we'll get an error message.

    >>> edit_form["ubuntu_thunderbird.target.package"] = "no-such-package"
    >>> request = LaunchpadTestRequest(form=edit_form, method="POST")
    >>> edit_view = getMultiAdapter(
    ...     (ubuntu_thunderbird_task, request), name="+editstatus"
    ... )
    >>> edit_view.initialize()
    >>> for error in edit_view.errors:
    ...     print(pretty(error.args))
    ...
    ('ubuntu_thunderbird.target', 'Target',
     LaunchpadValidationError(...'There is no package named
     &#x27;no-such-package&#x27; published in Ubuntu.'))

An error is reported to the user when a bug is retargeted and there is
an existing task for the same target.

Edit the Product
----------------

+editstatus allows a bug to be retargeted to another product.

    >>> login("test@canonical.com")
    >>> bug_seven = getUtility(IBugSet).get(7)
    >>> product_task = bug_seven.bugtasks[0]
    >>> print(product_task.bugtargetname)
    evolution

    >>> edit_form = {
    ...     "evolution.actions.save": "Save Changes",
    ...     "evolution.status": product_task.status.title,
    ...     "evolution.importance": product_task.importance.title,
    ...     "evolution.evolution.assignee.option": (
    ...         "evolution.assignee.assign_to_nobody"
    ...     ),
    ...     "evolution.target": "product",
    ...     "evolution.target.product": "firefox",
    ... }
    >>> request = LaunchpadTestRequest(form=edit_form, method="POST")
    >>> edit_view = getMultiAdapter(
    ...     (product_task, request), name="+editstatus"
    ... )
    >>> edit_view.initialize()
    >>> [str(error) for error in edit_view.errors]
    []
    >>> print(product_task.bugtargetname)
    firefox

If no product name is given, an error message is displayed.

    >>> edit_form = {
    ...     "firefox.actions.save": "Save Changes",
    ...     "firefox.status": product_task.status.title,
    ...     "firefox.importance": product_task.importance.title,
    ...     "firefox.firefox.assignee.option": (
    ...         "firefox.assignee.assign_to_nobody"
    ...     ),
    ...     "firefox.target": "product",
    ...     "firefox.target.product": "",
    ... }
    >>> request = LaunchpadTestRequest(form=edit_form, method="POST")
    >>> edit_view = getMultiAdapter(
    ...     (product_task, request), name="+editstatus"
    ... )
    >>> edit_view.initialize()
    >>> for error in edit_view.errors:
    ...     print(pretty(error.args))
    ...
    ('product', 'Project', RequiredMissing('product'))


Bug Watch Linkage
-----------------

Let's edit a bugtask which is linked to a remote bug. The most
important thing to edit is the bug watch, since it controls the status
information about the bug task. To show it how it works we remove the
link temporarily:

    >>> bug_nine = getUtility(IBugSet).get(9)
    >>> thunderbird_task = bug_nine.bugtasks[0]
    >>> bugzilla_watch = thunderbird_task.bugwatch
    >>> thunderbird_task.bugwatch = None

Now we simulate that the bug watch got updated:

    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(bugzilla_watch).remotestatus = "RESOLVED FIXED"

If we now link the bugtask to the bug watch, the bugtask's status will
be set to Unknown:

XXX: We really should update the status from the bug watch, but that's
     not trivial to do at the moment. I will fix this later.
     -- Bjorn Tillenius, 2006-03-01

    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> thunderbird_task.transitionToStatus(
    ...     BugTaskStatus.NEW, getUtility(ILaunchBag).user
    ... )
    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "thunderbird.actions.save": "Save Changes",
    ...         "thunderbird.status": "Confirmed",
    ...         "thunderbird.importance": "Critical",
    ...         "thunderbird.bugwatch": "6",
    ...     },
    ... )
    >>> edit_view = getMultiAdapter(
    ...     (thunderbird_task, request), name="+editstatus"
    ... )
    >>> edit_view.initialize()
    >>> thunderbird_task.bugwatch == bugzilla_watch
    True
    >>> thunderbird_task.status.title
    'Unknown'

If we unlink the bug watch, the bugtask's status and importance will be
set to their default values:

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "thunderbird.actions.save": "Save Changes",
    ...         "thunderbird.bugwatch-empty-marker": "1",
    ...     },
    ... )
    >>> edit_view = getMultiAdapter(
    ...     (thunderbird_task, request), name="+editstatus"
    ... )
    >>> edit_view.initialize()
    >>> thunderbird_task.bugwatch is None
    True

    >>> from lp.bugs.interfaces.bugtask import IBugTask
    >>> thunderbird_task.status == IBugTask["status"].default
    True
    >>> thunderbird_task.importance == IBugTask["importance"].default
    True


Milestone Editing Permissions
-----------------------------

A milestone can be edited only by a user with launchpad.Edit permissions
on the distribution or product context. When the user has this
permission, the edit page renders an input widget, otherwise it renders
a display widget.

    >>> from zope.formlib.interfaces import IInputWidget
    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet

The distribution owner gets an edit widget for the distribution task.

    >>> login("mark@example.com")

    >>> request = LaunchpadTestRequest()
    >>> ubuntu_task = getUtility(IBugTaskSet).get(17)
    >>> bugtask_edit_view = getMultiAdapter(
    ...     (ubuntu_task, request), name="+editstatus"
    ... )
    >>> bugtask_edit_view.initialize()

    >>> IInputWidget.providedBy(bugtask_edit_view.widgets["milestone"])
    True

But an unprivileged user does not.

    >>> from zope.formlib.itemswidgets import ItemDisplayWidget

    >>> login("no-priv@canonical.com")

    >>> bugtask_edit_view = getMultiAdapter(
    ...     (ubuntu_task, request), name="+editstatus"
    ... )
    >>> bugtask_edit_view.initialize()

    >>> isinstance(bugtask_edit_view.widgets["milestone"], ItemDisplayWidget)
    True

A bug supervisor can also change the milestone. Let's set no-priv as
Ubuntu's bug supervisor.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.distribution import IDistributionSet

    >>> login("foo.bar@canonical.com")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> ubuntu.bug_supervisor = no_priv

Unlike before, no-priv can now edit the milestone.

    >>> bugtask_edit_view = getMultiAdapter(
    ...     (ubuntu_task, request), name="+editstatus"
    ... )
    >>> bugtask_edit_view.initialize()

    >>> IInputWidget.providedBy(bugtask_edit_view.widgets["milestone"])
    True
