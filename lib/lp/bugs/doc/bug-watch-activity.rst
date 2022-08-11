BugWatchActivity
================

The activity on a given bug watch is recorded in the BugWatchActivity
table.

We can create a new BugWatchActivity record for a bug watch using that
BugWatch's addActivity() method.

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.testing.dbuser import lp_dbuser
    >>> from lp.bugs.model.bugwatch import BugWatchActivity

In order to create a BugWatch to test with we need to switch DB users.
This is because the checkwatches DB user can't create BugWatches, whilst
at the same time _only_ the checkwatches DB user can create
BugWatchActivity instances.

    >>> with lp_dbuser():
    ...     bug_watch = factory.makeBugWatch(remote_bug='42')

When a BugWatch is first created there has been no activity on it.

    >>> print(bug_watch.activity.count())
    0

    >>> bug_watch.addActivity()
    >>> store = IStore(BugWatchActivity)
    >>> store.flush()

We can access the BugWatchActivity record by looking at the BugWatch's
activity property.

    >>> print(bug_watch.activity.count())
    1

    >>> activity = bug_watch.activity.first()
    >>> activity.bug_watch == bug_watch
    True

The BugWatchActivity's activity_date will be set automatically when it
is written to the database.

    >>> activity.activity_date
    datetime.datetime...

The BugWatchActivity's result will be BugWatchActivityStatus.SYNC_SUCCEEDED.

    >>> print(activity.result.title)
    Synchronisation succeeded

The other fields on the BugWatchActivity record, which aren't required,
will all be None.

    >>> print(activity.message)
    None
    >>> print(activity.oops_id)
    None


Recording BugWatch updates as BugWatchActivity
-----------------------------------------------

Whenever an update is made to a BugWatch that update is recorded as a
BugWatchActivity entry.

We can demonstrate this by passing our bug watch to
CheckwatchesMaster.updateBugWatches().

    >>> from lp.services.log.logger import BufferLogger
    >>> from lp.bugs.scripts.checkwatches import CheckwatchesMaster
    >>> from lp.bugs.tests.externalbugtracker import TestExternalBugTracker
    >>> updater = CheckwatchesMaster(transaction, BufferLogger())
    >>> updater.updateBugWatches(
    ...     TestExternalBugTracker('http://example.com'), [bug_watch])

An extra activity item will have been added to the BugWatch's activity
property.

    >>> print(bug_watch.activity.count())
    2

The most recent activity entry will have a result of
BugWatchActivityStatus.SYNC_SUCCEEDED since it was
successful.

    >>> most_recent_activity = bug_watch.activity.first()
    >>> print(most_recent_activity.result.title)
    Synchronisation succeeded

Its message will also be empty

    >>> print(most_recent_activity.message)
    None

As will its oops_id

    >>> print(most_recent_activity.oops_id)
    None

If the remote bug tracker breaks during an update the error will be
recorded in the activity entry for that update.

    >>> from lp.bugs.externalbugtracker.base import UnparsableBugData
    >>> from lp.bugs.tests.externalbugtracker import (
    ...     TestBrokenExternalBugTracker)
    >>> broken_bugtracker = TestBrokenExternalBugTracker('http://example.com')
    >>> broken_bugtracker.get_remote_status_error = UnparsableBugData

    >>> updater.updateBugWatches(broken_bugtracker, [bug_watch])

Another entry will have been added to the watch's activity property.

    >>> print(bug_watch.activity.count())
    3

And this time its result field will record that the remote bug was
not found.

    >>> most_recent_activity = bug_watch.activity.first()
    >>> print(most_recent_activity.result.title)
    Unparsable Bug

The OOPS ID for the error will also have been recorded.

    >>> print(most_recent_activity.oops_id)
    OOPS...

The CheckwatchesMaster also adds BugWatchActivity entries when errors occur
that don't have an entry in the BugWatchActivityStatus DB Enum.

    >>> broken_bugtracker.get_remote_status_error = Exception
    >>> updater.updateBugWatches(broken_bugtracker, [bug_watch])
    >>> most_recent_activity = bug_watch.activity.first()

    >>> print(most_recent_activity.result.title)
    Unknown

The OOPS ID of the error is recorded so that we can debug it.

    >>> print(most_recent_activity.oops_id)
    OOPS...
