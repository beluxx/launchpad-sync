BugTask Status Workflow
=======================

BugTasks have a natural status workflow: New => Confirmed => In
Progress => Fix Committed => Fix Released, etc. Some state transitions
have "side effects".

Currently, the only side effect is that we record the date on which some
status transitions occurred.

Here are examples of each transition that we record. First, let's create
a new bug to work with:

    >>> from zope.component import getUtility
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.registry.interfaces.distribution import IDistributionSet

    >>> login("foo.bar@canonical.com")
    >>> foobar = getUtility(ILaunchBag).user

    >>> ubuntu = getUtility(IDistributionSet).get(1)
    >>> ubuntu_mozilla_firefox = ubuntu.getSourcePackage("mozilla-firefox")

    >>> params = CreateBugParams(
    ...     owner=foobar, title="a new bug", comment="a test comment"
    ... )
    >>> new_bug = ubuntu_mozilla_firefox.createBug(params)

    >>> ubuntu_firefox_task = new_bug.bugtasks[0]

    >>> print(ubuntu_firefox_task.distribution.name)
    ubuntu
    >>> print(ubuntu_firefox_task.sourcepackagename.name)
    mozilla-firefox

Only its datecreated value will be set. All other dates will be None.

    >>> ubuntu_firefox_task.datecreated
    datetime.datetime...

    >>> ubuntu_firefox_task.date_confirmed is None
    True

    >>> ubuntu_firefox_task.date_assigned is None
    True

    >>> ubuntu_firefox_task.date_inprogress is None
    True

    >>> ubuntu_firefox_task.date_closed is None
    True

The bug status cannot be set directly, but the value can be retrieved
directly.

    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus

    >>> ubuntu_firefox_task.status = BugTaskStatus.CONFIRMED
    Traceback (most recent call last):
      ...
    zope.security.interfaces.ForbiddenAttribute: ...

    >>> print(ubuntu_firefox_task.status.title)
    New

Confirming the bug will set IBugTask.date_confirmed. As with all the
dates we track on bug tasks, this date value is set/changed only when
the task enters that state from another state. Setting an already
CONFIRMED task to CONFIRMED again will not alter the date_confirmed
value.

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user
    ... )

    >>> print(ubuntu_firefox_task.status.title)
    Confirmed
    >>> ubuntu_firefox_task.date_confirmed
    datetime.datetime...

    >>> prev_date_confirmed = ubuntu_firefox_task.date_confirmed

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user
    ... )

    >>> ubuntu_firefox_task.date_confirmed == prev_date_confirmed
    True

In addition, we record the date on which this task left the NEW status.

    >>> ubuntu_firefox_task.date_left_new
    datetime.datetime...

    >>> (
    ...     ubuntu_firefox_task.date_left_new
    ...     == ubuntu_firefox_task.date_confirmed
    ... )
    True

Unlike in other transitions, `date_left_new` is never reset back. We always
keep the first time the task's status changed from NEW.

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.NEW, getUtility(ILaunchBag).user
    ... )
    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user
    ... )

    >>> (
    ...     ubuntu_firefox_task.date_left_new
    ...     < ubuntu_firefox_task.date_confirmed
    ... )
    True

If the status regresses to an earlier workflow state, the date_confirmed
is set to None, because it wouldn't make sense to have a date_confirmed
on a bug that's New.

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.NEW, getUtility(ILaunchBag).user
    ... )

    >>> ubuntu_firefox_task.date_confirmed is None
    True

Marking the bug In Progress sets IBugTask.date_inprogress. This is
like an "implicit" confirmation of the bug, so date_confirmed will be
set too.

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.INPROGRESS, getUtility(ILaunchBag).user
    ... )

    >>> print(ubuntu_firefox_task.status.title)
    In Progress
    >>> ubuntu_firefox_task.date_inprogress
    datetime.datetime...
    >>> ubuntu_firefox_task.date_confirmed
    datetime.datetime...

    >>> prev_date_inprogress = ubuntu_firefox_task.date_inprogress

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.INPROGRESS, getUtility(ILaunchBag).user
    ... )

    >>> ubuntu_firefox_task.date_inprogress == prev_date_inprogress
    True

If the status regresses to an earlier workflow state, then
date_inprogress is set to None, similar to the logic behind date_confirmed:

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user
    ... )

    >>> ubuntu_firefox_task.date_inprogress is None
    True

Marking the bug Triaged sets `date_triaged`.

    >>> print(ubuntu_firefox_task.date_triaged)
    None

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.TRIAGED, getUtility(ILaunchBag).user
    ... )

    >>> ubuntu_firefox_task.date_triaged
    datetime.datetime...

But rolling it back to a previous status unsets `date_triaged` to None.

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.NEW, getUtility(ILaunchBag).user
    ... )

    >>> print(ubuntu_firefox_task.date_triaged)
    None

If the status is changed from any unresolved status to any resolved
status (Invalid, Expired or Fix Released), the date_closed property is
set. The date_closed is always set to None when the task's status is
set to an open status. Note in the transition to FIXRELEASED the
date_inprogress is also set, when it had previously been None.

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.INVALID, getUtility(ILaunchBag).user
    ... )

    >>> ubuntu_firefox_task.date_closed
    datetime.datetime...

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user
    ... )
    >>> ubuntu_firefox_task.date_closed is None
    True

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.EXPIRED, getUtility(ILaunchBag).user
    ... )
    >>> ubuntu_firefox_task.date_closed
    datetime.datetime...

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user
    ... )
    >>> ubuntu_firefox_task.date_closed is None
    True

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.OPINION, getUtility(ILaunchBag).user
    ... )
    >>> ubuntu_firefox_task.date_closed
    datetime.datetime...

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.CONFIRMED, getUtility(ILaunchBag).user
    ... )
    >>> ubuntu_firefox_task.date_inprogress is None
    True
    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.FIXRELEASED, getUtility(ILaunchBag).user
    ... )
    >>> ubuntu_firefox_task.date_closed
    datetime.datetime...
    >>> ubuntu_firefox_task.date_inprogress
    datetime.datetime...

Changing from one closed status to another does not change the
date_closed.

    >>> print(ubuntu_firefox_task.status.title)
    Fix Released
    >>> prev_date_closed = ubuntu_firefox_task.date_closed
    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.INVALID, getUtility(ILaunchBag).user
    ... )

    >>> print(ubuntu_firefox_task.status.title)
    Invalid
    >>> ubuntu_firefox_task.date_closed == prev_date_closed
    True

Whenever a bugtask is being reopened, that is, its status is changed from
a closed status to an open one, we record the date in date_left_closed.

    >>> last_date_closed = ubuntu_firefox_task.date_closed
    >>> ubuntu_firefox_task.date_left_closed > last_date_closed
    False
    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.TRIAGED, getUtility(ILaunchBag).user
    ... )
    >>> ubuntu_firefox_task.date_left_closed > last_date_closed
    True

We also record the date a task was marked Fix Committed.

    >>> print(ubuntu_firefox_task.date_fix_committed)
    None

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.FIXCOMMITTED, getUtility(ILaunchBag).user
    ... )

    >>> ubuntu_firefox_task.date_fix_committed
    datetime.datetime...

But rolling it back to a previous status unsets `date_fix_committed` to None.

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.INPROGRESS, getUtility(ILaunchBag).user
    ... )

    >>> print(ubuntu_firefox_task.date_fix_committed)
    None

We also record the date a task was marked Fix Released.

    >>> print(ubuntu_firefox_task.date_fix_released)
    None

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.FIXRELEASED, getUtility(ILaunchBag).user
    ... )

    >>> ubuntu_firefox_task.date_fix_released
    datetime.datetime...

But rolling it back to a previous status unsets `date_fix_released` to None.

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.INPROGRESS, getUtility(ILaunchBag).user
    ... )

    >>> print(ubuntu_firefox_task.date_fix_committed)
    None

Lastly, IBugTask.date_assigned is set when a bugtask goes from being
unassigned, to assigned, but not if the assignee changes from one person
to another. Like status, assignee cannot be set directly, because
setting an assignee has "side effects".

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> sample_person = getUtility(IPersonSet).get(12)

    >>> ubuntu_firefox_task.assignee = foobar
    Traceback (most recent call last):
      ...
    zope.security.interfaces.ForbiddenAttribute: ...

    >>> ubuntu_firefox_task.transitionToAssignee(foobar)

    >>> ubuntu_firefox_task.date_assigned
    datetime.datetime...

    >>> prev_date_assigned = ubuntu_firefox_task.date_assigned
    >>> ubuntu_firefox_task.transitionToAssignee(sample_person)
    >>> ubuntu_firefox_task.date_assigned == prev_date_assigned
    True

    >>> ubuntu_firefox_task.transitionToAssignee(None)
    >>> ubuntu_firefox_task.date_assigned is None
    True


date_xxx and the UNKNOWN status
-------------------------------

When an IBugTask is set to status UNKNOWN, the date_confirmed,
date_closed, date_inprogress, date_triaged, date_fixcommitted
and date_fix_released fields are all set to None, since UNKNOWN
is the lowest status, and the task didn't yet progress through
these statuses.

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.FIXRELEASED, getUtility(ILaunchBag).user
    ... )

    >>> ubuntu_firefox_task.date_confirmed
    datetime.datetime...

    >>> ubuntu_firefox_task.date_inprogress
    datetime.datetime...

    >>> ubuntu_firefox_task.date_closed
    datetime.datetime...

    >>> ubuntu_firefox_task.date_triaged
    datetime.datetime...

    >>> ubuntu_firefox_task.date_fix_committed
    datetime.datetime...

    >>> ubuntu_firefox_task.date_fix_released
    datetime.datetime...

    >>> ubuntu_firefox_task.transitionToStatus(
    ...     BugTaskStatus.UNKNOWN, getUtility(ILaunchBag).user
    ... )

    >>> ubuntu_firefox_task.date_confirmed is None
    True

    >>> ubuntu_firefox_task.date_inprogress is None
    True

    >>> ubuntu_firefox_task.date_closed is None
    True

    >>> ubuntu_firefox_task.date_triaged is None
    True

    >>> ubuntu_firefox_task.date_fix_committed is None
    True

    >>> ubuntu_firefox_task.date_fix_released is None
    True
