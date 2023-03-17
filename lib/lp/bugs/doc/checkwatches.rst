checkwatches.py
===============

The updating and syncing of bug watches is done by a cronscript. We
can't test it properly, since we don't yet have a mock HTTP server we
can use for testing, so let's just make sure that it doesn't try to
contact any external servers.

    >>> from lp.services.database.sqlbase import cursor, sqlvalues
    >>> from lp.services.database.constants import UTC_NOW
    >>> cur = cursor()
    >>> cur.execute("UPDATE BugWatch SET lastchecked=%s" % sqlvalues(UTC_NOW))
    >>> import transaction
    >>> transaction.commit()

We set a default timeout on checkwatches to 30 seconds. In order to test
this, we can inject a mock timeout using `responses` and call the
checkwatches cronscript machinery directly.

First, we create some bug watches to test with:

    >>> from datetime import datetime, timezone
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> from lp.bugs.model.bugtracker import BugTracker
    >>> from lp.bugs.scripts.checkwatches import CheckwatchesMaster
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> sample_person = getUtility(IPersonSet).getByEmail(
    ...     "test@canonical.com"
    ... )

    >>> example_bug_tracker_name = "example-bugs"
    >>> example_bug_tracker = BugTracker(
    ...     name=example_bug_tracker_name,
    ...     title="Example.com Roundup",
    ...     bugtrackertype=BugTrackerType.ROUNDUP,
    ...     baseurl="http://bugs.example.com",
    ...     summary="Contains bugs for Example.com",
    ...     contactdetails="foo.bar@example.com",
    ...     owner=sample_person,
    ... )

    >>> login("test@canonical.com")

    >>> example_bug = getUtility(IBugSet).get(10)
    >>> example_bugwatch = example_bug.addWatch(
    ...     example_bug_tracker,
    ...     "1",
    ...     getUtility(ILaunchpadCelebrities).janitor,
    ... )
    >>> example_bugwatch.next_check = datetime.now(timezone.utc)

    >>> login("no-priv@canonical.com")

Next, we ensure that the request always times out.

The timeout will not produce an OOPS report; they happen routinely and
require no action from the Launchpad end.

    >>> from contextlib import contextmanager
    >>> import re
    >>> import socket
    >>> import responses
    >>> from lp.testing.fixture import CaptureOops

    >>> @contextmanager
    ... def timeout_requests():
    ...     with responses.RequestsMock() as requests_mock:
    ...         requests_mock.add(
    ...             "GET",
    ...             re.compile(r".*"),
    ...             body=socket.timeout("Connection timed out."),
    ...         )
    ...         yield
    ...

    >>> with CaptureOops() as capture, timeout_requests():
    ...     updater = CheckwatchesMaster(transaction.manager)
    ...     updater.updateBugTrackers(
    ...         bug_tracker_names=[example_bug_tracker_name]
    ...     )
    ...     print(capture.oopses)
    ...
    []

Errors that occur when updating a bug watch are recorded against that
bug watch. The timeout will be recorded against the bug watch we just
created in its last_error_type field.

    >>> from lp.bugs.interfaces.bugwatch import BugWatchActivityStatus
    >>> example_bugwatch.last_error_type == BugWatchActivityStatus.TIMEOUT
    True

Another error which may occur and which checkwatches is responsible for
handling is UnknownBugTrackerTypeError, which is raised when
checkwatches attempts to instantiate the ExternalBugtracker descendant
for a bugtracker which Launchpad doesn't support.

We can demonstrate this by altering the get_external_bugtracker method
of the externalbugtracker module to ensure that it raises this error.

    >>> from lp.bugs import externalbugtracker
    >>> real_get_external_bugtracker = (
    ...     externalbugtracker.get_external_bugtracker
    ... )

    >>> def broken_get_external_bugtracker(bugtracker):
    ...     bugtrackertype = bugtracker.bugtrackertype
    ...     raise externalbugtracker.UnknownBugTrackerTypeError(
    ...         bugtrackertype.name, bugtracker.name
    ...     )
    ...

    >>> login(ANONYMOUS)
    >>> example_bugwatch.next_check = datetime.now(timezone.utc)
    >>> try:
    ...     externalbugtracker.get_external_bugtracker = (
    ...         broken_get_external_bugtracker
    ...     )
    ...     updater = CheckwatchesMaster(transaction.manager)
    ...     transaction.commit()
    ...     updater._updateBugTracker(example_bug_tracker)
    ... finally:
    ...     externalbugtracker.get_external_bugtracker = (
    ...         real_get_external_bugtracker
    ...     )
    ...

The bug watch's last error type field will have been updated to reflect
the error that was raised:

    >>> example_bugwatch.last_error_type.title
    'Unsupported Bugtracker'


Batched Bugwatch Updating
-------------------------

checkwatches.py will only update those bugs that need updating, but
there is a further limit on the amount of bugs which will be updated for
a given ExternalBugTracker in each checkwatches run: the batch size.

We need to add some bug watches again since
BugWatchUpdate._updateBugTracker() automatically rolls back the
transaction if something goes wrong.

    >>> login("test@canonical.com")
    >>> for bug_id in range(1, 10):
    ...     example_bugwatch = example_bug.addWatch(
    ...         example_bug_tracker,
    ...         str(bug_id),
    ...         getUtility(ILaunchpadCelebrities).janitor,
    ...     )
    ...     example_bugwatch.next_check = datetime.now(timezone.utc)
    ...

Since we know how many bugwatches example_bug has we will be able to see
when checkwatches only updates a subset of them.

    >>> example_bug.watches.count()
    9

Since our example bug tracker is a Roundup bug tracker we can
monkey-patch the Roundup ExternalBugTrackerClass in order to set its
batch size. We will also insert a mock response again so that no requests
are actually made.

    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.bugs import externalbugtracker

    >>> transaction.commit()
    >>> updater = CheckwatchesMaster(transaction.manager)
    >>> original_log = updater.logger
    >>> batch_size = externalbugtracker.Roundup.batch_size
    >>> with timeout_requests():
    ...     try:
    ...         externalbugtracker.Roundup.batch_size = 5
    ...         transaction.commit()
    ...         updater.logger = FakeLogger()
    ...         updater.updateBugTrackers([example_bug_tracker_name])
    ...     finally:
    ...         updater.logger = original_log
    ...         externalbugtracker.Roundup.batch_size = batch_size
    ...
    DEBUG No global batch size specified.
    INFO Updating 5 watches for 5 bugs on http://bugs.example.com
    INFO Connection timed out when updating ...


Updating all the watches on a bug tracker
-----------------------------------------

It's possible to update all the watches on a bug tracker using
checkwatches using CheckwatchesMaster's forceUpdateAll() method.
forceUpdateAll() accepts a bug_tracker_name argument because it's
called by the checkwatches script, which doesn't know or care about
IBugTracker and instances thereof.

Let's first create a watch on our Savannah bug tracker.

    >>> from lp.testing.dbuser import dbuser
    >>> savannah = getUtility(ILaunchpadCelebrities).savannah_tracker
    >>> with dbuser("launchpad"):
    ...     bug_watch = factory.makeBugWatch(bugtracker=savannah)
    ...
    >>> savannah.watches.count()
    1

We'll set the lastchecked time on that Savannah instance to make sure
that it looks as though it has been updated recently

    >>> login("test@canonical.com")
    >>> savannah.resetWatches()

So our Savannah instance now has no watches that need checking.

    >>> savannah.watches_needing_update.count()
    0

However, forceUpdateAll() will update every watch, whether they've
been recently checked or not.

We'll create a helper method here, because we want to monkey patch the
CheckwatchesMaster's logger.

    >>> def update_all(bug_tracker_name, batch_size=None):
    ...     transaction.commit()
    ...     updater = CheckwatchesMaster(transaction.manager)
    ...     updater.logger = FakeLogger()
    ...     updater.forceUpdateAll(bug_tracker_name, batch_size)
    ...

    >>> update_all("savannah", batch_size)
    INFO Resetting 1 bug watches for bug tracker 'savannah'
    INFO Updating 1 watches on bug tracker 'savannah'
    INFO 'Unsupported Bugtracker' error updating http://savannah.gnu.org/:
    SAVANE
    INFO 0 watches left to check on bug tracker 'savannah'

We can see that the Savannah bug watch has been updated recently. Also,
its last_error_type field will be set to "Unsupported bug tracker"
since that's the error that was raised during the update.

    >>> for watch in savannah.watches:
    ...     print(
    ...         "%s, %s"
    ...         % (watch.lastchecked is not None, watch.last_error_type.title)
    ...     )
    ...
    True, Unsupported Bugtracker

If a bug tracker doesn't have any watches to update, forceUpdateAll()
will ignore it.

    >>> with dbuser("launchpad"):
    ...     login("test@canonical.com")
    ...     empty_tracker = factory.makeBugTracker(
    ...         "http://example.com", BugTrackerType.ROUNDUP
    ...     )
    ...
    >>> empty_tracker_name = empty_tracker.name
    >>> update_all(empty_tracker_name)
    INFO Bug tracker 'auto-example.com' doesn't have any watches. Ignoring.

Similarly, forceUpdateAll() will ignore the bug tracker if it doesn't exist.

    >>> update_all("nah-this-wont-work")
    INFO Bug tracker 'nah-this-wont-work' doesn't exist. Ignoring.

The batch_size parameter is set, the watches will be updated in batches.
We'll add some more watches in order to demonstrate this.

    >>> transaction.commit()
    >>> with dbuser("launchpad"):
    ...     for i in range(5):
    ...         bug_watch = factory.makeBugWatch(bugtracker=empty_tracker)
    ...

    >>> empty_tracker.watches.count()
    5

With a batch_size of 1, only one bug watch will be updated at once.
We'll use a custom CheckwatchesMaster to make sure that no connections are
made.

    >>> class NonConnectingUpdater(CheckwatchesMaster):
    ...     def _updateBugTracker(self, bug_tracker, batch_size):
    ...         # Update as many watches as the batch size says.
    ...         with self.transaction:
    ...             watches_to_update = bug_tracker.watches_needing_update[
    ...                 :batch_size
    ...             ]
    ...             now = datetime.now(timezone.utc)
    ...             for watch in watches_to_update:
    ...                 watch.lastchecked = now
    ...                 watch.next_check = None
    ...

    >>> transaction.commit()
    >>> non_connecting_updater = NonConnectingUpdater(transaction.manager)
    >>> non_connecting_updater.logger = FakeLogger()
    >>> non_connecting_updater.forceUpdateAll(empty_tracker_name, 1)
    INFO Resetting 5 bug watches for bug tracker 'auto-example.com'
    INFO Updating 5 watches on bug tracker 'auto-example.com'
    INFO 4 watches left to check on bug tracker 'auto-example.com'
    INFO 3 watches left to check on bug tracker 'auto-example.com'
    INFO 2 watches left to check on bug tracker 'auto-example.com'
    INFO 1 watches left to check on bug tracker 'auto-example.com'
    INFO 0 watches left to check on bug tracker 'auto-example.com'


Comment syncing for duplicate bugs
----------------------------------

checkwatches won't try to sync comments for bugs which are duplicates of
other bugs in Launchpad. This is to avoid spamming both the upstream bug
tracker and Launchpad users with comments from the duplicate bugs. It
also side-steps the issue of Launchpad syncing with itself via an
external bug tracker (bug 484712).

We'll create a non-functioning ExternalBugtracker to demonstrate this.

    >>> from zope.interface import implementer
    >>> from lp.bugs.interfaces.bugtask import (
    ...     BugTaskStatus,
    ...     BugTaskImportance,
    ... )
    >>> from lp.bugs.interfaces.externalbugtracker import (
    ...     ISupportsCommentImport,
    ...     ISupportsCommentPushing,
    ...     ISupportsBackLinking,
    ... )
    >>> from lp.bugs.externalbugtracker.base import (
    ...     BATCH_SIZE_UNLIMITED,
    ...     ExternalBugTracker,
    ... )

    >>> nowish = datetime.now(timezone.utc)
    >>> @implementer(
    ...     ISupportsBackLinking,
    ...     ISupportsCommentImport,
    ...     ISupportsCommentPushing,
    ... )
    ... class UselessExternalBugTracker(ExternalBugTracker):
    ...     batch_size = BATCH_SIZE_UNLIMITED
    ...
    ...     def initializeRemoteBugDB(self, bug_ids):
    ...         # This just exists to stop errors from being raised.
    ...         pass
    ...
    ...     def getCurrentDBTime(self):
    ...         return nowish
    ...
    ...     def getRemoteStatus(self, id):
    ...         return "NEW"
    ...
    ...     def convertRemoteStatus(self, status):
    ...         return BugTaskStatus.NEW
    ...
    ...     def getRemoteImportance(self, id):
    ...         return "NONE"
    ...
    ...     def convertRemoteImportance(self, importance):
    ...         return BugTaskImportance.UNKNOWN
    ...
    ...     def getCommentIds(self, bug_watch):
    ...         print("getCommentIds() called")
    ...         return []
    ...
    ...     def fetchComments(self, bug_watch, comment_ids):
    ...         return []
    ...
    ...     def addRemoteComment(self, bug_watch, comment):
    ...         print("addRemoteComment() called.")
    ...         return 0
    ...
    ...     def getLaunchpadBugId(self, bug_id):
    ...         print("getLaunchpadBugId() called")
    ...         return None
    ...
    ...     def setLaunchpadBugId(self, bug_id, lp_bug_id, lp_bug_url):
    ...         print("setLaunchpadBugId() called")

We'll generate a bug watch with which to test this. The bug watch must
be associated with at least one bug task to enable syncing.

    >>> with dbuser("launchpad"):
    ...     login("foo.bar@canonical.com")
    ...     bug_tracker = factory.makeBugTracker()
    ...     bug_watch = factory.makeBugWatch(bugtracker=bug_tracker)
    ...     bug_watch.bug.default_bugtask.bugwatch = bug_watch
    ...

If we pass our UselessExternalBugTracker and the bug watch we just
generated to updateBugWatches we can see that its comments will be
synced and it will be linked to the remote bug.

    >>> updater = CheckwatchesMaster(transaction.manager)
    >>> transaction.commit()

    >>> remote_system = UselessExternalBugTracker("http://example.com")

    >>> updater.updateBugWatches(remote_system, [bug_watch], now=nowish)
    getCommentIds() called
    getLaunchpadBugId() called
    setLaunchpadBugId() called

If we mark the bug to which our bug watch is attached as a duplicate of
another bug, comments won't be synced and the bug won't be linked back
to the remote bug.

    >>> with dbuser("launchpad"):
    ...     bug_15 = getUtility(IBugSet).get(15)
    ...     bug_watch.bug.markAsDuplicate(bug_15)
    ...     updater.updateBugWatches(remote_system, [bug_watch], now=nowish)
    ...
