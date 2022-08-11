ExternalBugTracker: Roundup
===========================

This covers the implementation of the ExternalBugTracker class for Roundup
bugwatches.


Basics
------

The ExternalBugTracker descendant class which implements methods for updating
bug watches on Roundup bug trackers is externalbugtracker.Roundup, which
implements IExternalBugTracker.

    >>> from lp.bugs.externalbugtracker import Roundup
    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> from lp.bugs.interfaces.externalbugtracker import IExternalBugTracker
    >>> from lp.bugs.tests.externalbugtracker import (
    ...     new_bugtracker)
    >>> from lp.testing import verifyObject
    >>> verifyObject(
    ...     IExternalBugTracker,
    ...     Roundup('http://example.com'))
    True


Status Conversion
-----------------

The basic Roundup bug statuses (i.e. those available by default in new
Roundup instances) map to Launchpad bug statuses.

Roundup.convertRemoteStatus() handles the conversion.

    >>> roundup = Roundup('http://example.com/')
    >>> roundup.convertRemoteStatus('1').title
    'New'
    >>> roundup.convertRemoteStatus('2').title
    'Confirmed'
    >>> roundup.convertRemoteStatus('3').title
    'Incomplete'
    >>> roundup.convertRemoteStatus('4').title
    'Incomplete'
    >>> roundup.convertRemoteStatus('5').title
    'In Progress'
    >>> roundup.convertRemoteStatus('6').title
    'In Progress'
    >>> roundup.convertRemoteStatus('7').title
    'Fix Committed'
    >>> roundup.convertRemoteStatus('8').title
    'Fix Released'

Some Roundup trackers are set up to use multiple fields (columns in
Roundup terminology) to represent bug statuses. We store multiple
values by joining them with colons. The Roundup class knows how many
fields are expected for a particular remote host (for those that we
support), and will generate an error when we have more or less field
values compared to the expected number of fields.

    >>> roundup.convertRemoteStatus('1:2')
    Traceback (most recent call last):
      ...
    lp.bugs.externalbugtracker.base.UnknownRemoteStatusError:
    1 field(s) expected, got 2: 1:2

If the status isn't something that our Roundup ExternalBugTracker can
understand an UnknownRemoteStatusError will be raised.

    >>> roundup.convertRemoteStatus('eggs').title
    Traceback (most recent call last):
      ...
    lp.bugs.externalbugtracker.base.UnknownRemoteStatusError:
    Unrecognized value for field 1 (status): eggs


Initialization
--------------

Calling initializeRemoteBugDB() on our Roundup instance and passing it a set
of remote bug IDs will fetch those bug IDs from the server and file them in a
local variable for later use.

We use a test-oriented implementation for the purposes of these tests, which
avoids relying on a working network connection.

    >>> from lp.bugs.tests.externalbugtracker import (
    ...     TestRoundup, print_bugwatches)
    >>> roundup = TestRoundup(u'http://test.roundup/')
    >>> with roundup.responses():
    ...     roundup.initializeRemoteBugDB([1])
    >>> sorted(roundup.bugs.keys())
    [1]


Export Methods
--------------

There are two means by which we can export Roundup bug statuses: on a
bug-by-bug basis and as a batch. When the number of bugs that need updating is
less than a given bug tracker's batch_query_threshold the bugs will be
fetched one-at-a-time:

    >>> roundup.batch_query_threshold
    10

    >>> with roundup.responses(trace_calls=True):
    ...     roundup.initializeRemoteBugDB([6, 7, 8, 9, 10])
    GET http://test.roundup/issue?...&id=6
    GET http://test.roundup/issue?...&id=7
    GET http://test.roundup/issue?...&id=8
    GET http://test.roundup/issue?...&id=9
    GET http://test.roundup/issue?...&id=10

If there are more than batch_query_threshold bugs to update then they are
fetched as a batch:

    >>> roundup.batch_query_threshold = 4
    >>> with roundup.responses(trace_calls=True):
    ...     roundup.initializeRemoteBugDB([6, 7, 8, 9, 10])
    GET http://test.roundup/issue?...@startwith=0


Updating Bug Watches
--------------------

First, we create some bug watches to test with:

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> sample_person = getUtility(IPersonSet).getByEmail(
    ...     'test@canonical.com')

    >>> example_bug_tracker = new_bugtracker(BugTrackerType.ROUNDUP)

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> example_bug = getUtility(IBugSet).get(10)
    >>> example_bugwatch = example_bug.addWatch(
    ...     example_bug_tracker, '1',
    ...     getUtility(ILaunchpadCelebrities).janitor)


Collect the Example.com watches:

    >>> print_bugwatches(example_bug_tracker.watches)
    Remote bug 1: None

And have a Roundup instance process them:

    >>> transaction.commit()

    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.testing.layers import LaunchpadZopelessLayer
    >>> from lp.bugs.scripts.checkwatches import CheckwatchesMaster
    >>> txn = LaunchpadZopelessLayer.txn
    >>> bug_watch_updater = CheckwatchesMaster(
    ...     txn, logger=FakeLogger())
    >>> roundup = TestRoundup(example_bug_tracker.baseurl)
    >>> with roundup.responses():
    ...     bug_watch_updater.updateBugWatches(
    ...         roundup, example_bug_tracker.watches)
    INFO Updating 1 watches for 1 bugs on http://bugs.some.where
    >>> print_bugwatches(example_bug_tracker.watches)
    Remote bug 1: 1

We'll add some more watches now.

    >>> from lp.bugs.interfaces.bugwatch import IBugWatchSet
    >>> print_bugwatches(example_bug_tracker.watches,
    ...     roundup.convertRemoteStatus)
    Remote bug 1: New

    >>> remote_bugs = [
    ...     (2, 'Confirmed'),
    ...     (3, 'Incomplete'),
    ...     (4, 'Incomplete'),
    ...     (5, 'In Progress'),
    ...     (9, 'In Progress'),
    ...     (10, 'Fix Committed'),
    ...     (11, 'Fix Released'),
    ...     (12, 'Incomplete'),
    ...     (13, 'Incomplete'),
    ...     (14, 'In Progress')
    ... ]

    >>> bug_watch_set = getUtility(IBugWatchSet)
    >>> for remote_bug_id, remote_status in remote_bugs:
    ...     bug_watch = bug_watch_set.createBugWatch(
    ...         bug=example_bug, owner=sample_person,
    ...         bugtracker=example_bug_tracker,
    ...         remotebug=str(remote_bug_id))

    >>> with roundup.responses(trace_calls=True):
    ...     bug_watch_updater.updateBugWatches(
    ...         roundup, example_bug_tracker.watches)
    INFO Updating 11 watches for 11 bugs on http://bugs.some.where
    GET http://.../issue?...@startwith=0

    >>> print_bugwatches(example_bug_tracker.watches,
    ...     roundup.convertRemoteStatus)
    Remote bug 1: New
    Remote bug 2: Confirmed
    Remote bug 3: Incomplete
    Remote bug 4: Incomplete
    Remote bug 5: In Progress
    Remote bug 9: In Progress
    Remote bug 10: Fix Committed
    Remote bug 11: Fix Released
    Remote bug 12: Incomplete
    Remote bug 13: Incomplete
    Remote bug 14: In Progress

