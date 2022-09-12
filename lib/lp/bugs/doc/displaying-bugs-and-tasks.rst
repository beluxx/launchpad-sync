Displaying Information on Bugs and Bug Tasks
============================================

This document discusses TALES techniques and IBugTask object
attributes that may be useful to you, if you're writing some code to
display bug and bug task information.


Displaying an Icon with image:icon
----------------------------------

image:sprite_css is a TALES adapter that returns the CSS class for
an icon for a bugtask.
The icon is dependent on the importance of the IBugTask object.

Let's use a few examples to demonstrate:

    >>> from zope.component import getUtility
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.bugs.interfaces.bugtask import BugTaskImportance, IBugTaskSet
    >>> from lp.testing import (
    ...     login,
    ...     test_tales,
    ... )

    >>> login("foo.bar@canonical.com")
    >>> bugtaskset = getUtility(IBugTaskSet)
    >>> test_task = bugtaskset.get(4)
    >>> ORIGINAL_IMPORTANCE = test_task.importance

    >>> test_task.transitionToImportance(
    ...     BugTaskImportance.CRITICAL, getUtility(ILaunchBag).user
    ... )
    >>> test_tales("bugtask/image:sprite_css", bugtask=test_task)
    'sprite bug-critical'

    >>> test_task.transitionToImportance(
    ...     BugTaskImportance.HIGH, getUtility(ILaunchBag).user
    ... )
    >>> test_tales("bugtask/image:sprite_css", bugtask=test_task)
    'sprite bug-high'

    >>> test_task.transitionToImportance(
    ...     BugTaskImportance.MEDIUM, getUtility(ILaunchBag).user
    ... )
    >>> test_tales("bugtask/image:sprite_css", bugtask=test_task)
    'sprite bug-medium'

    >>> test_task.transitionToImportance(
    ...     BugTaskImportance.LOW, getUtility(ILaunchBag).user
    ... )
    >>> test_tales("bugtask/image:sprite_css", bugtask=test_task)
    'sprite bug-low'

    >>> test_task.transitionToImportance(
    ...     BugTaskImportance.WISHLIST, getUtility(ILaunchBag).user
    ... )
    >>> test_tales("bugtask/image:sprite_css", bugtask=test_task)
    'sprite bug-wishlist'

    >>> test_task.transitionToImportance(
    ...     BugTaskImportance.UNDECIDED, getUtility(ILaunchBag).user
    ... )
    >>> test_tales("bugtask/image:sprite_css", bugtask=test_task)
    'sprite bug-undecided'

    >>> test_task.transitionToImportance(
    ...     ORIGINAL_IMPORTANCE, getUtility(ILaunchBag).user
    ... )


Displaying Logos for Bug Tasks
------------------------------

The logo for a bug task display the corresponding logo for its
target.

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> bug1 = getUtility(IBugSet).get(1)
    >>> upstream_task = bug1.bugtasks[0]
    >>> print(upstream_task.product.name)
    firefox
    >>> ubuntu_task = bug1.bugtasks[1]
    >>> print(ubuntu_task.distribution.name)
    ubuntu

So the logo for an upstream bug task shows the project icon:

    >>> test_tales("bugtask/image:logo", bugtask=upstream_task)
    '<img alt="" width="64" height="64" src="/@@/product-logo" />'

And the logo for a distro bug task shows the source package icon:

    >>> test_tales("bugtask/image:logo", bugtask=ubuntu_task)
    '<img alt="" width="64" height="64" src="/@@/distribution-logo" />'


Displaying Status
-----------------

Sometimes it's useful to display the status of an IBugTask as a
human-readable string. So, instead of displaying something like:

  Status: Confirmed, Assignee: foo.bar@canonical.com

you might prefer that to read, simply:

  assigned to Foo Bar

We define a helper that uses the BugTaskListingView class (obtained via
+listing-view) to render the status:

    >>> from zope.component import getMultiAdapter
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus

    >>> def render_bugtask_status(task):
    ...     view = getMultiAdapter(
    ...         (task, LaunchpadTestRequest()), name="+listing-view"
    ...     )
    ...     return view.status
    ...

Let's see some examples of how this works:

    >>> login("foo.bar@canonical.com", LaunchpadTestRequest())
    >>> foobar = getUtility(ILaunchBag).user

    >>> ORIGINAL_STATUS = test_task.status
    >>> ORIGINAL_ASSIGNEE = test_task.assignee

    >>> test_task.transitionToAssignee(None)
    >>> render_bugtask_status(test_task)
    'Confirmed (unassigned)'

    >>> test_task.transitionToAssignee(foobar)
    >>> test_task.transitionToStatus(
    ...     BugTaskStatus.NEW, getUtility(ILaunchBag).user
    ... )
    >>> print(render_bugtask_status(test_task))
    New, assigned to ...Foo Bar...

    >>> test_task.transitionToStatus(
    ...     BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user
    ... )
    >>> print(render_bugtask_status(test_task))
    Confirmed, assigned to ...Foo Bar...

    >>> test_task.transitionToStatus(
    ...     BugTaskStatus.INVALID, getUtility(ILaunchBag).user
    ... )
    >>> print(render_bugtask_status(test_task))
    Invalid by ...Foo Bar...

    >>> test_task.transitionToAssignee(None)
    >>> render_bugtask_status(test_task)
    'Invalid (unassigned)'

    >>> test_task.transitionToStatus(
    ...     BugTaskStatus.FIXRELEASED, getUtility(ILaunchBag).user
    ... )
    >>> render_bugtask_status(test_task)
    'Fix released (unassigned)'

    >>> test_task.transitionToAssignee(foobar)
    >>> print(render_bugtask_status(test_task))
    Fix released, assigned to ...Foo Bar...

Lastly, some cleanup:

    >>> test_task.transitionToStatus(
    ...     ORIGINAL_STATUS, test_task.distribution.owner
    ... )
    >>> test_task.transitionToAssignee(ORIGINAL_ASSIGNEE)


Status Elsewhere
----------------

It's often useful to present information about the status of a bug in
other contexts. Again, the listing-view holds a method which provides us
with this information; let's define a helper for it:

    >>> def render_bugtask_status_elsewhere(task):
    ...     view = getMultiAdapter(
    ...         (task, LaunchpadTestRequest()), name="+listing-view"
    ...     )
    ...     return view.status_elsewhere
    ...

The main questions of interest, in order, are:

  1. Has this bug been fixed elsewhere?

  2. Has this bug been reported elsewhere?

Let's see some examples:

    >>> render_bugtask_status_elsewhere(bugtaskset.get(13))
    'not filed elsewhere'

    >>> render_bugtask_status_elsewhere(bugtaskset.get(2))
    'filed in 2 other places'

Let's take a random task related to task 2, mark it Fixed, and see how the
statuselsewhere value is affected:

    >>> related_task = bugtaskset.get(2).related_tasks[0]
    >>> ORIGINAL_STATUS = related_task.status
    >>> related_task.transitionToStatus(
    ...     BugTaskStatus.FIXRELEASED, getUtility(ILaunchBag).user
    ... )

    >>> render_bugtask_status_elsewhere(bugtaskset.get(2))
    'fixed in 1 of 3 places'

    >>> related_task.transitionToStatus(
    ...     ORIGINAL_STATUS, getUtility(ILaunchBag).user
    ... )
