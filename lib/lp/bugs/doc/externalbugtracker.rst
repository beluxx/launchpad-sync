Generic ExternalBugTracker Tests
================================

ExternalBugTracker instances are used to communicate with remote bug
trackers. This document tests those features that are common to all
ExternalBugTracker instances.

Updating bug watches
--------------------

All the ExternalBugTrackers know how to update the status of a bug
watch. The method that updates the bug watches is
CheckwatchesMaster.updateBugWatches(), which expects an IExternalBugTracker
and the bug watches to update.


Initializing
............

Before updating the bug watches, the initializeRemoteBugDB() method on
the ExternalBugTracker is called. It gets the information for the bug
watches from the external bug tracker, and it's called outside a DB
transaction, since it doesn't need DB access.

    >>> from lp.bugs.tests.externalbugtracker import TestExternalBugTracker
    >>> class InitializingExternalBugTracker(TestExternalBugTracker):
    ...     def initializeRemoteBugDB(self, remote_bug_ids):
    ...         print(
    ...             "initializeRemoteBugDB() called: %s"
    ...             % (pretty(remote_bug_ids),)
    ...         )
    ...

    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.bugs.scripts.checkwatches import CheckwatchesMaster
    >>> bug_watch_updater = CheckwatchesMaster(
    ...     transaction, logger=FakeLogger()
    ... )
    >>> bug_watch_updater.updateBugWatches(
    ...     InitializingExternalBugTracker(), []
    ... )
    INFO Updating 0 watches for 0 bugs on http://example.com
    initializeRemoteBugDB() called: []


Choosing another ExternalBugTracker instance
............................................

Sometimes there is more than one ExternalBugTracker instance for a
single bug tracker type. For example, for different versions, for
instances having our Launchpad plugin installed, and so on. This is done
with the getExternalBugTrackerToUse() method, which returns the correct
instance.  Usually there is only one version, so the default for the
original instance is to return itself.

    >>> from lp.bugs.externalbugtracker import ExternalBugTracker
    >>> external_bugtracker = ExternalBugTracker("http://example.com/")
    >>> chosen_bugtracker = external_bugtracker.getExternalBugTrackerToUse()
    >>> chosen_bugtracker is external_bugtracker
    True

CheckwatchesMaster calls externalbugtracker.get_external_bugtracker(),
followed by ExternalBugTracker.getExternalBugTrackerToUse() to get the
correct ExternalBugTracker for a given BugTracker. It does this via the
private _getExternalBugTrackersAndWatches() method, which returns a set of
(ExternalBugTracker, bug_watches) tuples.

    >>> from lp.bugs.externalbugtracker import (
    ...     Bugzilla,
    ...     BUG_TRACKER_CLASSES,
    ... )
    >>> from lp.bugs.externalbugtracker.bugzilla import BugzillaAPI
    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> from lp.testing.factory import LaunchpadObjectFactory

    >>> factory = LaunchpadObjectFactory()
    >>> standard_bugzilla = factory.makeBugTracker()

    >>> class NonConnectingBugzilla(Bugzilla):
    ...     bug_tracker_to_use = Bugzilla
    ...
    ...     def getExternalBugTrackerToUse(self):
    ...         print("Getting external bugtracker to use")
    ...         return self.bug_tracker_to_use(self.baseurl)
    ...

We'll create a helper method to allow us to avoid having to connect to a
remote server.

    >>> def get_trackers_and_watches(bugtracker, watches):
    ...     transaction.commit()
    ...     try:
    ...         BUG_TRACKER_CLASSES[
    ...             BugTrackerType.BUGZILLA
    ...         ] = NonConnectingBugzilla
    ...         trackers_and_watches = (
    ...             bug_watch_updater._getExternalBugTrackersAndWatches(
    ...                 bugtracker, watches
    ...             )
    ...         )
    ...     finally:
    ...         BUG_TRACKER_CLASSES[BugTrackerType.BUGZILLA] = Bugzilla
    ...
    ...     return trackers_and_watches
    ...

    >>> trackers_and_watches = get_trackers_and_watches(standard_bugzilla, [])
    Getting external bugtracker to use

    >>> len(trackers_and_watches)
    1

    >>> chosen_bugtracker, watches = trackers_and_watches[0]
    >>> isinstance(chosen_bugtracker, Bugzilla)
    True

_getExternalBugTrackersAndWatches() also takes a list of bug watches as a
parameter. For most calls, this remains unaltered and only one
(ExternalBugTracker, bug_watches) tuple will be returned.

    >>> bug_watches = [
    ...     factory.makeBugWatch(bugtracker=standard_bugzilla)
    ...     for useless_int in range(10)
    ... ]

    >>> trackers_and_watches = get_trackers_and_watches(
    ...     standard_bugzilla, bug_watches
    ... )
    Getting external bugtracker to use

    >>> len(trackers_and_watches)
    1

    >>> chosen_bugtracker, watches = trackers_and_watches[0]
    >>> isinstance(chosen_bugtracker, Bugzilla)
    True

    >>> watches == bug_watches
    True

The only bug tracker for which _getExternalBugTrackersAndWatches() will
return more than one (ExternalBugTracker, bug_watches) tuple: the Gnome
Bugzilla. This is because the Gnome Bugzilla is a special case.

Bugzilla allows users to track bugs in more than one product. Launchpad
supports this functionality through the BugzillaAPI
ExternalBugTracker subclass. Since the Gnome Bugzilla contains a very
large number of bugs we only want to synchronise comments and bugs for
some products. For the others, we want to use the standard
ExternalBugTracker functionality, without tapping into the functionality
offered by the Bugzilla Launchpad plugin.

The Gnome Bugzilla is a celebrity in Launchpad.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> gnome_bugzilla = getUtility(ILaunchpadCelebrities).gnome_bugzilla

If the gnome_bugzilla doesn't have the Launchpad plugin installed, it
will behave exactly the same as any other bug tracker. Our
NonConnectingBugzilla class will behave as though the remote server
doesn't have the Launchpad plugin installed.

    >>> trackers_and_watches = get_trackers_and_watches(
    ...     gnome_bugzilla, bug_watches
    ... )
    Getting external bugtracker to use

    >>> len(trackers_and_watches)
    1

    >>> chosen_bugtracker, watches = trackers_and_watches[0]
    >>> isinstance(chosen_bugtracker, Bugzilla)
    True

    >>> watches == bug_watches
    True

However, if the Gnome Bugtracker does have the plugin installed,
_getExternalBugTrackersAndWatches() behaves slightly differently.
Firstly, we'll subclass BugzillaAPI so that we don't have to
connect to any servers.

    >>> class ProductQueryingBugzillaAPI(BugzillaAPI):
    ...
    ...     remote_bug_products = {
    ...         1: "HeartOfGold",
    ...         2: "InfiniteImprobabilityDrive",
    ...         3: "HeartOfGold",
    ...         4: "GPP",
    ...         5: "InfiniteImprobabilityDrive",
    ...     }
    ...
    ...     def getProductsForRemoteBugs(self, bug_ids):
    ...         print("Getting products for remote bugs")
    ...         mappings = {}
    ...         for bug_id in bug_ids:
    ...             if int(bug_id) in self.remote_bug_products:
    ...                 mappings[bug_id] = self.remote_bug_products[
    ...                     int(bug_id)
    ...                 ]
    ...         return mappings
    ...

Next we'll update our NonConnectingBugzilla class so that its
getExternalBugTrackerToUse() method will return an instance of our
BugzillaAPI subclass.

    >>> NonConnectingBugzilla.bug_tracker_to_use = ProductQueryingBugzillaAPI

For those bug watches whose remote bugs are on products that we want to
sync comments with, _getExternalBugTrackersAndWatches() will return
(BugzillaAPI, watches).

The checkwatches module contains a variable, SYNCABLE_GNOME_PRODUCTS,
which defines the products that we want to sync comments for.
CheckwatchesMaster keeps a local copy of this variable, which we can
override by passing a list of products to the CheckwatchesMaster
constructor.

    >>> from lp.bugs.scripts import checkwatches
    >>> (
    ...     bug_watch_updater._syncable_gnome_products
    ...     == checkwatches.core.SYNCABLE_GNOME_PRODUCTS
    ... )
    True

    >>> syncable_products = ["HeartOfGold"]
    >>> bug_watch_updater = CheckwatchesMaster(
    ...     transaction, syncable_gnome_products=syncable_products
    ... )

    >>> bug_watches = [
    ...     factory.makeBugWatch(
    ...         remote_bug=remote_bug_id, bugtracker=standard_bugzilla
    ...     )
    ...     for remote_bug_id in range(1, 6)
    ... ]

We only want to sync comments and bugs for the HeartOfGold product. Bug
watches against that product will be returned as a batch from
_getExternalBugTrackersAndWatches() along with a BugzillaAPI
instance. All the other bug watches will be returned as a batch with
another BugzillaAPI instance which has syncing disabled.

    >>> trackers_and_watches = get_trackers_and_watches(
    ...     gnome_bugzilla, bug_watches
    ... )
    Getting external bugtracker to use
    Getting products for remote bugs

    >>> len(trackers_and_watches)
    2

    >>> bugzilla_for_sync, sync_watches = trackers_and_watches[0]
    >>> isinstance(bugzilla_for_sync, BugzillaAPI)
    True
    >>> bugzilla_for_sync.sync_comments
    True

    >>> from operator import attrgetter
    >>> for watch in sorted(sync_watches, key=attrgetter("remotebug")):
    ...     print(watch.remotebug)
    ...
    1
    3

    >>> bugzilla_other, other_watches = trackers_and_watches[1]
    >>> isinstance(bugzilla_other, BugzillaAPI)
    True
    >>> bugzilla_other.sync_comments
    False

    >>> for watch in sorted(other_watches, key=attrgetter("remotebug")):
    ...     print(watch.remotebug)
    ...
    2
    4
    5

If we alter the SYNCABLE_GNOME_PRODUCTS list, different batches of bug
watches will be returned for the two Bugzilla ExternalBugTrackers.

    >>> syncable_products = [
    ...     "HeartOfGold",
    ...     "InfiniteImprobabilityDrive",
    ... ]
    >>> bug_watch_updater = CheckwatchesMaster(
    ...     transaction, syncable_gnome_products=syncable_products
    ... )

    >>> trackers_and_watches = get_trackers_and_watches(
    ...     gnome_bugzilla, bug_watches
    ... )
    Getting external bugtracker to use
    Getting products for remote bugs

    >>> len(trackers_and_watches)
    2

    >>> bugzilla_for_sync, sync_watches = trackers_and_watches[0]
    >>> bugzilla_other, other_watches = trackers_and_watches[1]

    >>> isinstance(bugzilla_for_sync, BugzillaAPI)
    True
    >>> bugzilla_for_sync.sync_comments
    True

    >>> isinstance(bugzilla_other, BugzillaAPI)
    True
    >>> bugzilla_other.sync_comments
    False

    >>> for watch in sorted(sync_watches, key=attrgetter("remotebug")):
    ...     print(watch.remotebug)
    ...
    1
    2
    3
    5

    >>> for watch in sorted(other_watches, key=attrgetter("remotebug")):
    ...     print(watch.remotebug)
    ...
    4

If there are no syncable GNOME products, only one batch is returned,
and the remote system is never asked about product information.

    >>> bug_watch_updater = CheckwatchesMaster(
    ...     transaction, syncable_gnome_products=[]
    ... )

    >>> trackers_and_watches = get_trackers_and_watches(
    ...     gnome_bugzilla, bug_watches
    ... )
    Getting external bugtracker to use

    >>> len(trackers_and_watches)
    1


Checking the server DB time
...........................

Before initializeRemoteBugDB is called and we start importing
information from the remote bug tracker, we check what the bug tracker
thinks the current time is. Returning None means that we don't know what
the time is.

    >>> class TimeUnknownExternalBugTracker(InitializingExternalBugTracker):
    ...     def getCurrentDBTime(self):
    ...         print("getCurrentDBTime() called")
    ...         return None
    ...

    >>> bug_watch_updater.updateBugWatches(
    ...     TimeUnknownExternalBugTracker(), []
    ... )
    getCurrentDBTime() called
    initializeRemoteBugDB() called: []

If the difference between what we and the remote system think the time
is, an error is raised.

    >>> import pytz
    >>> from datetime import datetime, timedelta
    >>> utc_now = datetime.now(pytz.timezone("UTC"))
    >>> class PositiveTimeSkewExternalBugTracker(TestExternalBugTracker):
    ...     def getCurrentDBTime(self):
    ...         return utc_now + timedelta(minutes=20)
    ...

    >>> bug_watch_updater.updateBugWatches(
    ...     PositiveTimeSkewExternalBugTracker(), [], now=utc_now
    ... )
    Traceback (most recent call last):
    ...
    lp.bugs.scripts.checkwatches.core.TooMuchTimeSkew: ...

    >>> class NegativeTimeSkewExternalBugTracker(TestExternalBugTracker):
    ...     def getCurrentDBTime(self):
    ...         return utc_now - timedelta(minutes=20)
    ...

    >>> bug_watch_updater.updateBugWatches(
    ...     NegativeTimeSkewExternalBugTracker(), [], now=utc_now
    ... )
    Traceback (most recent call last):
    ...
    lp.bugs.scripts.checkwatches.core.TooMuchTimeSkew: ...

The error is in fact raised by the _getRemoteIdsToCheck() method of
CheckwatchesMaster, which is passed a server_time variable by
updateBugWatches(). updateBugWatches() is responsible for logging the
error and for setting the last_error_type on all affected BugWatches
before re-raising the error.

    >>> server_time = utc_now - timedelta(minutes=25)
    >>> bug_watch_updater._getRemoteIdsToCheck(
    ...     NegativeTimeSkewExternalBugTracker(), [], server_time, utc_now
    ... )
    Traceback (most recent call last):
    ...
    lp.bugs.scripts.checkwatches.core.TooMuchTimeSkew: ...

If it's only a little skewed, it won't raise an error.

    >>> class CorrectTimeExternalBugTracker(TestExternalBugTracker):
    ...     def getCurrentDBTime(self):
    ...         return utc_now + timedelta(minutes=1)
    ...
    >>> bug_watch_updater.updateBugWatches(
    ...     CorrectTimeExternalBugTracker(), [], now=utc_now
    ... )

If the timezone is known, the local time time should be returned, rather
than the UTC time.

    >>> class LocalTimeExternalBugTracker(TestExternalBugTracker):
    ...     def getCurrentDBTime(self):
    ...         local_time = utc_now.astimezone(pytz.timezone("US/Eastern"))
    ...         return local_time + timedelta(minutes=1)
    ...
    >>> bug_watch_updater.updateBugWatches(
    ...     LocalTimeExternalBugTracker(), [], now=utc_now
    ... )

If the remote server time is unknown, we will refuse to import any
comments from it. Bug watches will still be updated, but a warning is
logged saying that comments won't be imported.

    >>> from zope.interface import implementer
    >>> from lp.bugs.interfaces.externalbugtracker import (
    ...     ISupportsCommentImport,
    ... )
    >>> @implementer(ISupportsCommentImport)
    ... class CommentImportExternalBugTracker(TimeUnknownExternalBugTracker):
    ...     baseurl = "http://whatever.com"
    ...     sync_comments = True

    >>> checkwatches_master = CheckwatchesMaster(
    ...     transaction, syncable_gnome_products=[], logger=FakeLogger()
    ... )
    >>> remote_bug_updater = checkwatches_master.remote_bug_updater_factory(
    ...     checkwatches_master,
    ...     CommentImportExternalBugTracker(),
    ...     "1",
    ...     [],
    ...     [],
    ...     server_time=None,
    ... )
    WARNING Comment importing supported, but server time can't be
                trusted. No comments will be imported. (OOPS-...)


Limiting which bug watches to update
....................................

XXX: GavinPanella 2010-01-13 bug=507205: Move this section to
checkwatches-batching.rst.

In order to reduce the amount of data we have to transfer over the
network, each IExternalBugTracker has the ability to filter out bugs
that haven't been modified. The method responsible for this is
getModifiedRemoteBugs(), which accepts the set of bugs that should be
checked, as well as the oldest time any of the bugs were last checked.
The getModifiedRemoteBugs() is only called for bug trackers where we
know that their time is similar to ours.

    >>> class CheckModifiedExternalBugTracker(InitializingExternalBugTracker):
    ...     def getCurrentDBTime(self):
    ...         return datetime.now(pytz.timezone("UTC"))
    ...
    ...     def getModifiedRemoteBugs(self, remote_bug_ids, last_checked):
    ...         print("last_checked: %s" % last_checked)
    ...         print(
    ...             "getModifiedRemoteBugs() called: %s"
    ...             % (pretty(remote_bug_ids),)
    ...         )
    ...         return [remote_bug_ids[0], remote_bug_ids[-1]]
    ...
    ...     def getRemoteStatus(self, bug_id):
    ...         print("getRemoteStatus() called: %s" % pretty(bug_id))
    ...         return "UNKNOWN"
    ...

Only bugs that have been checked before are passed on to
getModifiedRemoteBugs(). I.e., if we have a set of newly created bug
watches, the getModifiedRemoteBugs() method won't be called.

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.bugwatch import IBugWatchSet
    >>> from lp.bugs.model.bugtracker import BugTracker
    >>> from lp.registry.interfaces.person import IPersonSet

    >>> sample_person = getUtility(IPersonSet).getByEmail(
    ...     "test@canonical.com"
    ... )

    >>> example_bug_tracker = BugTracker(
    ...     name="example-bugs",
    ...     title="Example.com Bug Tracker",
    ...     bugtrackertype=BugTrackerType.BUGZILLA,
    ...     baseurl="http://bugs.example.com",
    ...     summary="Contains bugs for Example.com",
    ...     contactdetails="foo.bar@example.com",
    ...     owner=sample_person,
    ... )
    >>> example_bug = getUtility(IBugSet).get(10)

    >>> bug_watches = [
    ...     getUtility(IBugWatchSet).createBugWatch(
    ...         example_bug, sample_person, example_bug_tracker, bug_id
    ...     )
    ...     for bug_id in ["1", "2", "3", "4"]
    ... ]
    >>> [
    ...     bug_watch.lastchecked
    ...     for bug_watch in bug_watches
    ...     if bug_watch.lastchecked is not None
    ... ]
    []

The method that determines which remote bug IDs need to be updated is
_getRemoteIdsToCheck(), which returns a dict containing three lists:

 * all_remote_ids: The list of all the remote IDs that were considered
   for checking in this run. This includes IDs which: have comments to
   be pushed, have never been checked or have not been checked for 24
   hours.
 * remote_ids_to_check: The subset of all_remote_ids that need to be checked.
   This list only includes those items from all_remote_ids that actually
   need checking. For many bug trackers this list and all_remote_ids
   will be the same, but for those bug trackers where Launchpad can
   check to see if a remote bug has changed since it was last checked
   this list will not include bugs that have not changed remotely (and
   so don't need checking). The difference between this list and
   all_remote_ids will be returned in unmodified_remote_ids.
 * unmodified_remote_ids: The subset of all_remote_ids that haven't changed
   on the remote server and so don't need to be checked.

    >>> transaction.commit()

    >>> external_bugtracker = CheckModifiedExternalBugTracker(
    ...     "http://example.com/"
    ... )
    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     bug_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ... )
    >>> for key in sorted(ids):
    ...     print("%s: %s" % (key, pretty(sorted(ids[key]))))
    ...
    all_remote_ids: ['1', '2', '3', '4']
    remote_ids_to_check: ['1', '2', '3', '4']
    unmodified_remote_ids: []

updateBugWatches() calls _getRemoteIdsToCheck() and passes its results
to the ExternalBugTracker's initializeRemoteBugDB() method.

    >>> bug_watch_updater.updateBugWatches(external_bugtracker, bug_watches)
    initializeRemoteBugDB() called: ['1', '2', '3', '4']
    getRemoteStatus() called: '1'
    getRemoteStatus() called: '2'
    getRemoteStatus() called: '3'
    getRemoteStatus() called: '4'

If the bug watches have the lastchecked attribute set, they will be
passed to getModifiedRemoteBugs(). Only the bugs that have been modified
will then be passed on to initializeRemoteBugDB().

    >>> some_time_ago = datetime(
    ...     2007, 3, 17, 16, 0, tzinfo=pytz.timezone("UTC")
    ... )
    >>> for bug_watch in bug_watches:
    ...     bug_watch.lastchecked = some_time_ago
    ...
    >>> transaction.commit()

    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     bug_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ... )
    last_checked: 2007-03-17 15:...:...

    >>> for key in sorted(ids):
    ...     print("%s: %s" % (key, pretty(sorted(ids[key]))))
    ...
    all_remote_ids: ['1', '2', '3', '4']
    remote_ids_to_check: ['1', '4']
    unmodified_remote_ids: ['2', '3']

    >>> bug_watch_updater.updateBugWatches(external_bugtracker, bug_watches)
    last_checked: 2007-03-17 15:...:...
    getModifiedRemoteBugs() called: ['1', '2', '3', '4']
    initializeRemoteBugDB() called: ['1', '4']
    getRemoteStatus() called: '1'
    getRemoteStatus() called: '4'

The bug watches that are deemed as not being modified are still marked
as being checked.

    >>> for bug_watch in bug_watches:
    ...     if bug_watch.lastchecked > some_time_ago:
    ...         print("Bug %s was marked checked" % bug_watch.remotebug)
    ...     else:
    ...         print("Bug %s was NOT marked checked" % bug_watch.remotebug)
    ...
    Bug 1 was marked checked
    Bug 2 was marked checked
    Bug 3 was marked checked
    Bug 4 was marked checked

The time being passed to getModifiedRemoteBugs() is the oldest one of the
bug watches' lastchecked attribute, minus the acceptable time skew, and
then some more just to be safe.

    >>> bug_watches[0].lastchecked = some_time_ago
    >>> bug_watches[1].lastchecked = some_time_ago + timedelta(days=1)
    >>> bug_watches[2].lastchecked = some_time_ago - timedelta(hours=1)
    >>> bug_watches[3].lastchecked = some_time_ago - timedelta(days=1)
    >>> transaction.commit()

    >>> bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     bug_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ... )
    last_checked: 2007-03-16 15:...:...

If some of the bug watches are new, they won't be passed on to
getModifiedRemoteBugs(), but they will still be passed to
initializeRemoteBugDB() since we do need to update them.

    >>> bug_watches[0].lastchecked = some_time_ago
    >>> bug_watches[1].lastchecked = None
    >>> bug_watches[2].lastchecked = None
    >>> bug_watches[3].lastchecked = some_time_ago - timedelta(days=1)
    >>> transaction.commit()
    >>> bug_watch_updater.updateBugWatches(
    ...     CheckModifiedExternalBugTracker(), bug_watches
    ... )
    last_checked: 2007-03-16 15:...:...
    getModifiedRemoteBugs() called: ['1', '4']
    initializeRemoteBugDB() called: ['1', '2', '3', '4']
    getRemoteStatus() called: '1'
    getRemoteStatus() called: '2'
    getRemoteStatus() called: '3'
    getRemoteStatus() called: '4'

As mentioned earlier, getModifiedRemoteBugs() is only called if we can
get the current time of the remote system. If the time is unknown, we
always update all the bug watches.

    >>> class TimeUnknownExternalBugTracker(CheckModifiedExternalBugTracker):
    ...     def getCurrentDBTime(self):
    ...         return None
    ...
    >>> for bug_watch in bug_watches:
    ...     bug_watch.lastchecked = some_time_ago
    ...
    >>> bug_watch_updater.updateBugWatches(
    ...     TimeUnknownExternalBugTracker(), bug_watches
    ... )
    initializeRemoteBugDB() called: ['1', '2', '3', '4']
    getRemoteStatus() called: '1'
    getRemoteStatus() called: '2'
    getRemoteStatus() called: '3'
    getRemoteStatus() called: '4'

The only exception to the rule of only updating modified bugs is the set
of bug watches which have comments that need to be pushed to the remote
server. _getRemoteIdsToCheck() will return these as needing to be
updated, regardless of whether they have been checked recently. This is
to ensure that new comments are pushed to the remote bugs as soon as
possible.

    >>> factory = LaunchpadObjectFactory()

    >>> class DummyExternalBugTracker(CheckModifiedExternalBugTracker):
    ...     def getModifiedRemoteBugs(self, remote_bug_ids, last_checked):
    ...         return []
    ...

    >>> external_bugtracker = DummyExternalBugTracker("http://example.com")
    >>> external_bugtracker.sync_comments = True
    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     bug_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ...     utc_now,
    ... )
    >>> print(sorted(ids["remote_ids_to_check"]))
    []

    >>> print(pretty(sorted(ids["unmodified_remote_ids"])))
    ['1', '2', '3', '4']

    >>> comment_message = factory.makeMessage(
    ...     "A test message", "That hasn't been pushed", owner=sample_person
    ... )
    >>> bug_message = bug_watches[-1].addComment(None, comment_message)

    >>> transaction.commit()

    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     bug_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ...     utc_now,
    ... )
    >>> print(pretty(sorted(ids["remote_ids_to_check"])))
    ['4']

Once the comment has been pushed it will no longer appear in the list of
IDs to be updated.

    >>> bug_message.remote_comment_id = "1"
    >>> transaction.commit()
    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     bug_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ...     utc_now,
    ... )
    >>> print(sorted(ids["remote_ids_to_check"]))
    []


Configuration Options
---------------------

All ExternalBugTrackers have a batch_query_threshold attribute which is
set by configuration options in launchpad-lazr.conf. This attribute is used
to decide whether or not bugs are exported from the remote server as a
batch (where possible) or individually.

The batch_query_threshold for a vanilla ExternalBugTracker should be the
same as that specified in launchpad-lazr.conf. We use a test version of
ExternalBugTracker here that doesn't actually do anything besides
fulfill the implementation requirements of IExternalBugTracker.

    >>> from lp.services.config import config
    >>> from lp.bugs.tests.externalbugtracker import TestExternalBugTracker
    >>> tracker = TestExternalBugTracker("http://example.com/")
    >>> (
    ...     tracker.batch_query_threshold
    ...     == config.checkwatches.batch_query_threshold
    ... )
    True


Error Handling
--------------

When an error occurs during the updating of bug watches it will be
recorded against the bug watches themselves so that it can be displayed
to users. We can test this by using a test version of
ExternalBugTracker.

    >>> import transaction
    >>> from lp.bugs.tests.externalbugtracker import (
    ...     TestBrokenExternalBugTracker,
    ... )
    >>> external_bugtracker = TestBrokenExternalBugTracker(
    ...     "http://example.com"
    ... )
    >>> from lp.services.log.logger import BufferLogger
    >>> bug_watch_updater = CheckwatchesMaster(transaction, BufferLogger())

We'll create an example bug watch with which to test this. This will
be passed to external_bugtracker's updateBugWatches() method and should
have errors recorded against it. We log in as Sample Person to make
these changes since there's no particular need to use one Person over
another.

    >>> login("test@canonical.com")

    >>> example_bugwatch = example_bug.addWatch(
    ...     example_bug_tracker, "1", sample_person
    ... )

    >>> from lp.bugs.externalbugtracker import (
    ...     BugTrackerConnectError,
    ...     UnparsableBugData,
    ...     UnparsableBugTrackerVersion,
    ... )

TestBrokenExternalBugTracker allows us to force errors to occur, so we
can use it to check that bug watches' last_error_types are being set
correctly.

We start with those errors that may be raised by
ExternalBugTracker.initializeRemoteBugDB(). We suppress exceptions
because the bug watch's last error field will contain the data we need
for this test.

The bug watch's lastchecked field will also be updated, since not doing
so would mean that error-prone bug watches would be checked every time
checkwatches ran instead of just once every 24 hours like any other bug
watch.

    >>> for error in [
    ...     BugTrackerConnectError,
    ...     UnparsableBugData,
    ...     UnparsableBugTrackerVersion,
    ...     Exception,
    ... ]:
    ...     example_bugwatch.lastchecked = None
    ...     external_bugtracker.initialize_remote_bugdb_error = error
    ...     try:
    ...         bug_watch_updater.updateBugWatches(
    ...             external_bugtracker, [example_bugwatch]
    ...         )
    ...     except error:
    ...         pass
    ...     print(
    ...         "%s: %s"
    ...         % (
    ...             example_bugwatch.last_error_type.title,
    ...             example_bugwatch.lastchecked is not None,
    ...         )
    ...     )
    Connection Error: True
    Unparsable Bug: True
    Unparsable Bug Tracker Version: True
    Unknown: True

We can run the same test on getRemoteStatus(), which can raise different
errors. Errors in getRemoteStatus() also produce OOPS reports. The OOPS
reports all have URLs specified, set to the URL of the most recent
watches for which an update was attempted.

We temporarily silence the logging from this function because we're not
interested in it. Again, the watch's lastchecked field will also be
updated.

    >>> external_bugtracker.initialize_remote_bugdb_error = None
    >>> for error in [UnparsableBugData, Exception]:
    ...     example_bugwatch.lastchecked = None
    ...     external_bugtracker.get_remote_status_error = error
    ...     bug_watch_updater.updateBugWatches(
    ...         external_bugtracker, [example_bugwatch]
    ...     )
    ...     oops = oops_capture.oopses[-1]
    ...     print(
    ...         "%s: %s (%s; %s)"
    ...         % (
    ...             example_bugwatch.last_error_type.title,
    ...             example_bugwatch.lastchecked is not None,
    ...             oops["id"],
    ...             oops["url"],
    ...         )
    ...     )
    ...
    Unparsable Bug: True (OOPS-...; http://bugs.example.com/show_bug.cgi?id=1)
    Unknown: True (OOPS-...; http://bugs.example.com/show_bug.cgi?id=1)


Using `LookupTree` to map statuses
----------------------------------

Most of the status conversions are assisted by a customized LookupTree
class.

    >>> from lp.bugs.externalbugtracker import LookupTree

This is flexible enough to cover all current mapping scenarios with
minimal preparation from `convertRemoteStatus`. Crucially, it also
lets us generate documentation directory from the status mapping
rules.

First, we need a tree to document.

    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> tree = LookupTree(
    ...     ("ASSIGNED", "STARTED", BugTaskStatus.INPROGRESS),
    ...     ("NEEDINFO", "WAITING", "SUSPENDED", BugTaskStatus.INCOMPLETE),
    ...     ("PENDINGUPLOAD", "RELEASE_PENDING", BugTaskStatus.FIXCOMMITTED),
    ...     ("REJECTED", BugTaskStatus.INVALID),
    ...     (
    ...         "RESOLVED",
    ...         "CLOSED",
    ...         LookupTree(
    ...             ("ERRATA", "FIXED", BugTaskStatus.FIXRELEASED),
    ...             ("WONTFIX", BugTaskStatus.WONTFIX),
    ...             (BugTaskStatus.INVALID,),
    ...         ),
    ...     ),
    ...     ("REOPENED", "NEW", "DEFERRED", BugTaskStatus.CONFIRMED),
    ...     ("UNCONFIRMED", BugTaskStatus.NEW),
    ...     (BugTaskStatus.UNKNOWN,),
    ... )

The customized LookupTree instance has a method to generate a MoinMoin
compatible table that describes the paths through the tree. The result
is always assumed to be a member of `BugTaskStatus`.

    >>> for line in tree.moinmoin_table():
    ...     print(line)
    ...
    || ASSIGNED '''or''' STARTED || - (''ignored'') || In Progress ||
    || NEEDINFO '''or''' WAITING '''or''' SUSPENDED || - (''ignored'') ...
    || PENDINGUPLOAD '''or''' RELEASE_PENDING || - (''ignored'') || Fix...
    || REJECTED || - (''ignored'') || Invalid ||
    || RESOLVED '''or''' CLOSED || ERRATA '''or''' FIXED || Fix Released ||
    ||  || WONTFIX || Won't Fix ||
    ||  || * (''any'') || Invalid ||
    || REOPENED '''or''' NEW '''or''' DEFERRED || - (''ignored'') || Co...
    || UNCONFIRMED || - (''ignored'') || New ||
    || * (''any'') || - (''ignored'') || Unknown ||

Titles can also be provided for the table.

    >>> titles = ("Status", "Resolution", "LP status")
    >>> for line in tree.moinmoin_table(titles):
    ...     print(line)
    ...
    || '''Status''' || '''Resolution''' || '''LP status''' ||
    || ASSIGNED '''or''' STARTED || - (''ignored'') || In Progress ||
    || NEEDINFO '''or''' WAITING '''or''' SUSPENDED || - (''ignored'') ...
    ...

It will complain if you don't provide a suitable number of titles.

    >>> titles = ("Status", "Resolution")
    >>> for line in tree.moinmoin_table(titles):
    ...     print(line)
    ...
    Traceback (most recent call last):
    ...
    ValueError: Table of 3 columns needs 3 titles, but 2 given.

When constructing a status mapping tree, you are forced to choose a
valid Launchpad status as the result of any lookup. This goes some way
to ensuring that the tree is valid, and that `moinmoin_table` is safe
to make that assumption.

    >>> tree = LookupTree(
    ...     ("ASSIGNED", BugTaskStatus.INPROGRESS),
    ...     ("NEEDSINFO", "Not a BugTaskStatus"),
    ... )
    Traceback (most recent call last):
    ...
    TypeError: Result is not a member of BugTaskStatus: 'Not a BugTaskStatus'


Getting the remote product from a remote bug
--------------------------------------------

Some ExternalBugTrackers offer a method by which can be used to get the
remote product for a given remote bug.

IExternalBugTracker defines a method, getRemoteProduct(), which can be
used to get the remote product from a given bug. The "remote product" in
this case is the identifier that the remote bug tracker gives to a given
project or package. Launchpad can use this to offer users links to the
relevant bug filing and search forms on upstream bug trackers. For those
bug trackers that track more than one project, the remote product value
is used to pre-fill the upstream bug filing and search forms with the
correct project, reducing the need for the users to have to think about
where to file the bug upstream.

    >>> from lp.bugs.interfaces.externalbugtracker import IExternalBugTracker
    >>> from lp.testing import verifyObject

    >>> external_bugtracker = TestExternalBugTracker("http://example.com")
    >>> verifyObject(IExternalBugTracker, external_bugtracker)
    True

The basic implementation of getRemoteProduct() provided by the basic
ExternalBugTracker class will only ever return None. Since most bug
trackers only track one product it makes more sense to implement this
here and override it in cases where an ExternalBugTracker subclass is
capable of dealing with multiple remote products.

    >>> basic_external_bugtracker = ExternalBugTracker("http://example.com")
    >>> print(basic_external_bugtracker.getRemoteProduct(1))
    None


Prioritisation of watches
-------------------------

_getRemoteIdsToCheck() prioritizes the IDs it returns. Bug watches which have
comments to push or which have never been checked will always be returned in
the remote_ids_to_check list, limited only by the batch_size of the bug
tracker (see "Batched BugWatch Updating" in doc/checkwatches.rst).

We'll create some example unchecked watches as well as some watches with
comments to push in order to demonstrate this.

    >>> class SmallBatchExternalBugTracker(TimeUnknownExternalBugTracker):
    ...
    ...     batch_size = 5
    ...
    >>> external_bugtracker = SmallBatchExternalBugTracker(
    ...     "http://example.com"
    ... )
    >>> external_bugtracker.sync_comments = True

The watches on remote bugs 0 - 4 haven't been checked.

    >>> unchecked_watches = [
    ...     factory.makeBugWatch(
    ...         remote_bug=i,
    ...         bugtracker=standard_bugzilla,
    ...         bug=example_bug,
    ...         owner=sample_person,
    ...     )
    ...     for i in range(5)
    ... ]

The watches on remote bugs 5 - 7 have comments that need pushing.

    >>> watches_with_comments = [
    ...     factory.makeBugWatch(
    ...         remote_bug=i,
    ...         bugtracker=standard_bugzilla,
    ...         bug=example_bug,
    ...         owner=sample_person,
    ...     )
    ...     for i in range(5, 8)
    ... ]
    >>> for watch in watches_with_comments:
    ...     watch.lastchecked = some_time_ago
    ...     bug_message = watch.addComment(
    ...         None, factory.makeMessage(owner=sample_person)
    ...     )
    ...

All of the watches that need pushing will be included in remote_ids_to_check.
However, only some of the bug watches that have never been checked will
be included. This is because it's less important to deal with bug
watches that have never been updated than it is to push comments to the
remote server.

    >>> transaction.commit()

    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     unchecked_watches + watches_with_comments,
    ...     external_bugtracker.getCurrentDBTime(),
    ...     utc_now,
    ... )
    >>> print(pretty(sorted(ids["remote_ids_to_check"])))
    ['0', '1', '5', '6', '7']

Previously-checked bug watches that need updating will only be included if
there is enough room for them in the batch. If the number of new watches plus
the number of watches with comments is greater than the batch size old watches
will be ignored altogether.

Watches on remote bugs 8 and 9 have been checked before and need to be
checked again.

    >>> old_watches = []
    >>> for i in range(8, 10):
    ...     watch = factory.makeBugWatch(
    ...         remote_bug=i,
    ...         bugtracker=standard_bugzilla,
    ...         bug=example_bug,
    ...         owner=sample_person,
    ...     )
    ...     watch.lastchecked = some_time_ago
    ...     old_watches.append(watch)
    ...

    >>> transaction.commit()

    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     unchecked_watches + watches_with_comments + old_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ...     utc_now,
    ... )
    >>> print(pretty(sorted(ids["remote_ids_to_check"])))
    ['0', '1', '5', '6', '7']

The old IDs that aren't checked aren't included in the unmodified_remote_ids
list, since they still need checking and shouldn't be marked as having been
checked already.

    >>> print(sorted(ids["unmodified_remote_ids"]))
    []

However, if there's room in the batch, old IDs that need checking will
also be included, up to the batch_size limit.

    >>> external_bugtracker.batch_size = 9
    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     unchecked_watches + watches_with_comments + old_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ...     utc_now,
    ... )
    >>> print(pretty(sorted(ids["remote_ids_to_check"])))
    ['0', '1', '2', '3', '4', '5', '6', '7', '8']

If there's no batch_size set, all the bugs that should be checked are
returned.

    >>> external_bugtracker.batch_size = None
    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     unchecked_watches + watches_with_comments + old_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ...     utc_now,
    ... )
    >>> print(pretty(sorted(ids["remote_ids_to_check"])))
    ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']


Setting the batch size
----------------------

It's possible to set the batch size for a particular checkwatches run by
passing a batch_size parameter to _getRemoteIdsToCheck(). This overrides
the batch_size set by a given ExternalBugTracker instance.

With a batch_size of 5 on the ExternalBugTracker instance and a batch_size
of 2 passed as a parameter to _getExternalBugTrackersAndWatches(), only two
results will be returned.

    >>> external_bugtracker.batch_size = 5
    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     unchecked_watches + watches_with_comments + old_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ...     utc_now,
    ...     batch_size=2,
    ... )
    >>> print(pretty(sorted(ids["remote_ids_to_check"])))
    ['5', '6']

If the batch_size parameter is set to None (the default value), the
ExternalBugTracker's batch_size is used to decide the number of IDs returned.

    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     unchecked_watches + watches_with_comments + old_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ...     utc_now,
    ...     batch_size=None,
    ... )
    >>> print(pretty(sorted(ids["remote_ids_to_check"])))
    ['0', '1', '5', '6', '7']

_getRemoteIdsToCheck() will interpret a batch_size parameter of 0 as an
instruction to ignore the batch size limitation altogether and just return all
the IDs that need checking. The constant BATCH_SIZE_UNLIMITED should
be used in place of using 0 verbatim.

    >>> from lp.bugs.externalbugtracker import BATCH_SIZE_UNLIMITED

    >>> ids = bug_watch_updater._getRemoteIdsToCheck(
    ...     external_bugtracker,
    ...     unchecked_watches + watches_with_comments + old_watches,
    ...     external_bugtracker.getCurrentDBTime(),
    ...     utc_now,
    ...     batch_size=BATCH_SIZE_UNLIMITED,
    ... )
    >>> print(pretty(sorted(ids["remote_ids_to_check"])))
    ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

batch_size can be passed to _getRemoteIdsToCheck() via updateBugWatches(),
too.

    >>> bug_watch_updater.updateBugWatches(
    ...     external_bugtracker, unchecked_watches, utc_now, batch_size=2
    ... )
    initializeRemoteBugDB() called: ['0', '1']
    getRemoteStatus() called: '0'
    getRemoteStatus() called: '1'

It can also be passed via updateBugTracker() (which will in turn pass it to
updateBugWatches()).  In order to prevent it from attempting to connect to the
outside world we'll subclass it to make sure it uses our non-connecting
external_bugtracker.

    >>> class NonConnectingCheckwatchesMaster(CheckwatchesMaster):
    ...     def _getExternalBugTrackersAndWatches(
    ...         self, bug_trackers, bug_watches
    ...     ):
    ...         return [(external_bugtracker, bug_watches)]
    ...

    >>> bug_watch_updater = NonConnectingCheckwatchesMaster(
    ...     transaction, BufferLogger()
    ... )
    >>> transaction.commit()
    >>> bug_watch_updater._updateBugTracker(standard_bugzilla, batch_size=2)
    initializeRemoteBugDB() called: ['5', '6']
    getRemoteStatus() called: '5'
    getRemoteStatus() called: '6'

The default entry point into CheckwatchesMaster for the checkwatches script is
the updateBugTrackers() method. This, too, takes a batch_size parameter, which
allows it to be passed as a command-line option when the checkwatches script
is run.
