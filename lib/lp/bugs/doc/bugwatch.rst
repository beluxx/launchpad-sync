Bug Watches
===========

Malone is a bug tracker that understands the structure of the Open
Source world. It's there for people who want to use it, and take
advantage of this infrastructure.

But realistically, not everyone is going to switch to using Malone. To
workaround that in Malone, we have bug watches.

Bug watches watch bugs. More specifically, a bug watch watches a bug
in a bugtracker outside of Malone. By doing this, we can be kept aware
of the status of a bug that lives outside Malone for the benefit of
users and maintainers that are using Malone.


Retrieving Bug Watches
----------------------

Bug watches are accessed via a utility that provides IBugWatchSet.

    >>> from zope.component import getUtility
    >>> from lp.bugs.interfaces.bugwatch import IBugWatchSet
    >>> getUtility(IBugWatchSet).get(98765)
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: 98765
    >>> bugwatch = getUtility(IBugWatchSet).get(2)
    >>> print(bugwatch.remotebug)
    2000

The `url` property of the bugwatch produces the actual URL under which
that bug lives in the remote system.

    >>> print(bugwatch.bugtracker.baseurl)
    https://bugzilla.mozilla.org/
    >>> print(bugwatch.url)
    https://bugzilla.mozilla.org/show_bug.cgi?id=2000

It works regardless of whether the bugtracker's baseurl ends with a
slash or not:

    >>> bugwatch = getUtility(IBugWatchSet).get(4)
    >>> print(bugwatch.bugtracker.baseurl)
    http://bugzilla.gnome.org/bugs
    >>> print(bugwatch.url)
    http://bugzilla.gnome.org/bugs/show_bug.cgi?id=3224

    >>> bugwatch = getUtility(IBugWatchSet).get(6)
    >>> print(bugwatch.bugtracker.baseurl)
    http://bugzilla.ubuntu.com/bugs/
    >>> print(bugwatch.url)
    http://bugzilla.ubuntu.com/bugs/show_bug.cgi?id=1234

Watches of Email Address bugtrackers are slightly different: the `url`
property is always the same as the bugtracker baseurl property.

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> bugtrackerset = getUtility(IBugTrackerSet)

    >>> email_bugtracker = bugtrackerset['email']
    >>> email_bugwatch = (
    ...     getUtility(IBugWatchSet).createBugWatch(
    ...         getUtility(IBugSet).get(1), getUtility(IPersonSet).get(1),
    ...         email_bugtracker, 'remote-bug-id'))

    >>> print(email_bugwatch.remotebug)
    remote-bug-id
    >>> print(email_bugwatch.url)
    mailto:bugs@example.com
    >>> print(email_bugtracker.baseurl)
    mailto:bugs@example.com

Bug watches can also be accessed as a property of a bug tracker, with
the .watches attribute.

    >>> from operator import attrgetter
    >>> debbugs = bugtrackerset['debbugs']
    >>> for watch in sorted(
    ...         debbugs.watches, key=attrgetter('bug.id', 'remotebug')):
    ...     print('%d: %s' % (watch.bug.id, watch.remotebug))
    1: 304014
    2: 327452
    3: 327549
    7: 280883
    15: 308994
    >>> mozilla_bugtracker = bugtrackerset['mozilla.org']
    >>> for watch in sorted(
    ...         mozilla_bugtracker.watches,
    ...         key=attrgetter('bug.id', 'remotebug')):
    ...     print('%d: %s' % (watch.bug.id, watch.remotebug))
    1: 123543
    1: 2000
    1: 42
    2: 42

To get the latest 10 watches, use IBugTracker.latestwatches:

    >>> for watch in mozilla_bugtracker.latestwatches:
    ...     print('%d: %s' % (watch.bug.id, watch.remotebug))
    1: 2000
    1: 123543
    1: 42
    2: 42

We can retrieve the list of Launchpad bugs watching a particular
remote bug using getBugsWatching():

    >>> [bug.id for bug in mozilla_bugtracker.getBugsWatching('42')]
    [1, 2]

If we have a bug, we can query for a bug watch associated with that
bug. This method is useful for preventing duplicate bug watches from
being added.

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> mozilla_watch = bug_one.getBugWatch(mozilla_bugtracker, '2000')
    >>> mozilla_watch in bug_one.watches
    True
    >>> print(mozilla_watch.bugtracker.name)
    mozilla.org
    >>> print(mozilla_watch.remotebug)
    2000

If no matching bug watch can be found, None is returned.

    >>> bug_one.getBugWatch(mozilla_bugtracker, 'no-such-bug') is None
    True


Creating Bug Watches
--------------------

To create a bugwatch, use IBugWatchSet.createBugWatch:

    >>> from lp.registry.interfaces.person import IPersonSet

    >>> sample_person = getUtility(IPersonSet).get(12)
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> bugwatch = getUtility(IBugWatchSet).createBugWatch(
    ...     bug=bug_one, owner=sample_person, bugtracker=mozilla_bugtracker,
    ...     remotebug='1234')
    >>> print(bugwatch.url)
    https://bugzilla.mozilla.org/show_bug.cgi?id=1234
    >>> bugwatch.lastchecked is None
    True


Creating SF.net Bug Watches
---------------------------

SourceForge.net bug watch URLs are generated using the
"/support/tracker.php" script, which will redirect to the URL with the
group_id and aid arguments filled in:

    >>> sftracker = bugtrackerset['sf']
    >>> sample_person = getUtility(IPersonSet).get(12)
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> bugwatch = getUtility(IBugWatchSet).createBugWatch(
    ...     bug=bug_one, owner=sample_person, bugtracker=sftracker,
    ...     remotebug='1337833')
    >>> print(bugwatch.url)
    http://sourceforge.net/support/tracker.php?aid=1337833

Extracting Bug Watches From Text
--------------------------------

When you have a text, for example a bug comment, it can be useful to
extract all the possible bug watches from that text. To make this
easier you can use IBugWatchSet.fromText().

    >>> text = """
    ...     A Bugzilla URL:
    ...         http://some.bugzilla/show_bug.cgi?id=42
    ...     A Debbugs URL:
    ...         http://some.debbugs/cgi-bin/bugreport.cgi?bug=42
    ...     A Roundup URL:
    ...         http://some.roundup/issue42
    ...     A Trac URL:
    ...         http://some.trac/ticket/42
    ...     A Mantis URL:
    ...         http://some.mantis/mantis/view.php?id=50
    ...     A SourceForge URL:
    ...         http://some.sf/tracker/index.php?func=detail&aid=1568562&group_id=84122&atid=42
    ...     An unrecognised URL:
    ...         http://some.host/some/path
    ...     A mailto: URI:
    ...         mailto:foo.bar@canonical.com
    ...     A Google Code URL:
    ...         http://code.google.com/p/myproject/issues/detail?id=12345
    ... """  # noqa
    >>> bug_watches = getUtility(IBugWatchSet).fromText(
    ...     text, bug_one, sample_person)
    >>> bugs_and_types = [
    ...     (bug_watch.bugtracker.bugtrackertype, bug_watch.remotebug)
    ...     for bug_watch in bug_watches]
    >>> for bugtracker_type, remotebug in sorted(bugs_and_types):
    ...     print("%s: %s" % (bugtracker_type.name, remotebug))
    BUGZILLA: 42
    DEBBUGS: 42
    ROUNDUP: 42
    TRAC: 42
    SOURCEFORGE: 1568562
    MANTIS: 50
    GOOGLE_CODE: 12345

The bug trackers in the text above were automatically created. If the
bugwatch points to a bug tracker that already is registered in Launchpad
with the same URL, it won't be registered again. This is true even if
the URL is slightly different, for example https instead of https. It
doesn't handle the case where the same bug tracker is available through
different URLs, for example where the host name is different (e.g.,
bugs.gnome.org vs. bugzilla.gnome.org).

    >>> old_bugtracker_count = getUtility(IBugTrackerSet).count
    >>> gnome_bugzilla = getUtility(IBugTrackerSet).queryByBaseURL(
    ...     'http://bugzilla.gnome.org/bugs')
    >>> print(gnome_bugzilla.name)
    gnome-bugzilla
    >>> text = "https://bugzilla.gnome.org/bugs/show_bug.cgi?id=12345"
    >>> [gnome_bugwatch] = getUtility(IBugWatchSet).fromText(
    ...     text, bug_one, sample_person)
    >>> print(gnome_bugwatch.bugtracker.name)
    gnome-bugzilla
    >>> new_bugtracker_count = getUtility(IBugTrackerSet).count
    >>> old_bugtracker_count == new_bugtracker_count
    True

One special case when calling IBugWatchSet.fromText() is the
EMAILADDRESS BugTrackerType. URIs for this bug tracker type are in the
form mailto:emailaddress, however Launchpad does not automatically
create bug watches or bug trackers from such URIs if they are found in
the text passed to fromText().

    >>> text = "mailto:some.one@example.com"
    >>> bug_watches = getUtility(IBugWatchSet).fromText(text, bug_one,
    ...     sample_person)
    >>> bug_watches
    []


Syncing the Status with Linked Bugtasks
---------------------------------------

If the bug watch is linked to a bugtask, the bug watch can sync its
status with it. Before we do this we need to login as the Bug Watch
Updater and get a bug watch and a bugtask to test with.

    >>> login('bugwatch@bugs.launchpad.net')
    >>> bug_watch_updater_user = getUtility(ILaunchBag).user
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> bug_one.expireNotifications()
    >>> print(len(bug_one.bugtasks))
    3
    >>> debian_task = bug_one.bugtasks[2]
    >>> print(debian_task.bugtargetdisplayname)
    mozilla-firefox (Debian)

    >>> print(debian_task.status.title)
    Confirmed

    >>> debian_bugwatch = debian_task.bugwatch
    >>> old_remotestatus = debian_bugwatch.remotestatus

When a bugtask is modified, an ObjectModifiedEvent is fired off in
order to trigger mail notification. Let's register a listener, so that
we can confirm that an event is indeed fired off.

    >>> def print_bugtask_modified(bugtask, event):
    ...     old_bugtask = event.object_before_modification
    ...     if bugtask.status != old_bugtask.status:
    ...         print("%s => %s" % (old_bugtask.status.title,
    ...             bugtask.status.title))
    ...     if bugtask.importance != old_bugtask.importance:
    ...         print("%s => %s" % (old_bugtask.importance.title,
    ...             bugtask.importance.title))
    >>> from lazr.lifecycle.interfaces import IObjectModifiedEvent
    >>> from lp.bugs.interfaces.bugtask import IBugTask
    >>> from lp.testing.fixture import ZopeEventHandlerFixture
    >>> event_listener = ZopeEventHandlerFixture(
    ...     print_bugtask_modified, (IBugTask, IObjectModifiedEvent))
    >>> event_listener.setUp()

If we pass in a different Malone status than the existing one, an event
will be fired off, even though the remote status stays the same.

    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> old_lastchanged = debian_bugwatch.lastchanged
    >>> debian_bugwatch.updateStatus(
    ...     debian_bugwatch.remotestatus, BugTaskStatus.NEW)
    Confirmed => New

The lastchanged isn't updated, though, since it indicates when the
remotestatus changed. The bug watch can change the status of its bug
tasks even though its status didn't change in cases where we update the
status mapping.

    >>> debian_bugwatch.lastchanged == old_lastchanged
    True

    >>> debian_bugwatch.remotestatus == old_remotestatus
    True
    >>> print(debian_task.status.title)
    New

If only the remote status is changed, not the bugtask's status, no
event is fired off. The remote status is simply a string, it doesn't
have to be convertible to a real Malone status.

    >>> debian_bugwatch.updateStatus(u'some status', BugTaskStatus.NEW)

    >>> print(debian_bugwatch.remotestatus)
    some status
    >>> print(debian_task.status.title)
    New

The lastchanged was updated, though.

    >>> debian_bugwatch.lastchanged > old_lastchanged
    True

The Bug Watch Updater didn't receive any karma for the changed bug
tasks, because it's not a valid person and only valid persons can get karma.

    >>> from lp.registry.model.karma import Karma
    >>> from lp.services.database.interfaces import IStore
    >>> IStore(Karma).find(Karma, person=bug_watch_updater_user).count()
    0

Finally, let's make sure that bug notifications were added:

    >>> from lp.bugs.model.bugnotification import BugNotification
    >>> unsent_notifications = IStore(BugNotification).find(
    ...     BugNotification, date_emailed=None).order_by(BugNotification.id)

    >>> for bug_notification in unsent_notifications:
    ...     print("Bug %s changed by %s:" % (
    ...         bug_notification.bug_id,
    ...         bug_notification.message.owner.displayname))
    ...     print(bug_notification.message.text_contents)
    Bug 1 changed by Bug Watch Updater:
    ** Changed in: mozilla-firefox (Debian)
           Status: Confirmed => New


Syncing Importance With Linked BugTasks
---------------------------------------

Similarly, the bug watch updater can modify the bug watch's importance.
Passing it a new Malone importance will fire off an event, which our
event listener will pick up. We reset the `lastchanged` field of the bug
watch so that we can demonstrate how it gets updated.

    >>> from lp.bugs.interfaces.bugtask import BugTaskImportance
    >>> debian_bugwatch.lastchanged = old_lastchanged
    >>> old_remote_importance = debian_bugwatch.remote_importance

    >>> debian_bugwatch.updateImportance(
    ...     debian_bugwatch.remote_importance, BugTaskImportance.CRITICAL)
    Low => Critical

As with updating Malone statuses, the bug watch's `lastchanged` field
doesn't get updated since the remote importance hasn't been changed.

    >>> debian_bugwatch.lastchanged == old_lastchanged
    True

    >>> debian_bugwatch.remote_importance == old_remote_importance
    True

    >>> print(debian_task.importance.title)
    Critical

If only the remote importance is changed, not the bugtask's importance,
no event is fired off. The remote importance is simply a string, it
doesn't necessarily have to be convertible to a real Malone status.

    >>> debian_bugwatch.updateImportance(u'some importance',
    ...     BugTaskImportance.CRITICAL)

    >>> print(debian_bugwatch.remote_importance)
    some importance
    >>> print(debian_task.importance.title)
    Critical

The `lastchanged` field was updated, though.

    >>> debian_bugwatch.lastchanged > old_lastchanged
    True

Changes to bug watch statuses will produce notifications in the usual
manner:

    >>> for bug_notification in unsent_notifications:
    ...     print("Bug %s changed by %s:" % (
    ...         bug_notification.bug.id,
    ...         bug_notification.message.owner.displayname))
    ...     print(bug_notification.message.text_contents)
    Bug 1 changed by Bug Watch Updater:
    ** Changed in: mozilla-firefox (Debian)
           Status: Confirmed => New
    Bug 1 changed by Bug Watch Updater:
    ** Changed in: mozilla-firefox (Debian)
       Importance: Low => Critical

    >>> event_listener.cleanUp()

The Bug Watch Updater can transition a bug to any status or importance:

    >>> for status in BugTaskStatus.items:
    ...     debian_bugwatch.updateStatus(u'nothing', status)

    >>> for importance in BugTaskImportance.items:
    ...     debian_bugwatch.updateImportance(u'nothing', importance)


BugWatches against BugTasks with conjoined primaries
----------------------------------------------------

A conjoined bugtask involves a primary and replica in a conjoined
relationship. The replica is a generic product or distribution task; the
primary is a series-specific task. If a BugWatch is linked to a BugTask
with a conjoined primary, that bug task will not be updated when the
BugWatch's status or importance are updated. We can demonstrate this by
creating a bug task with a conjoined primary.

    >>> from zope.component import getUtility
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> from lp.bugs.interfaces.bugtracker import (
    ...     BugTrackerType,
    ...     IBugTrackerSet,
    ...     )
    >>> from lp.registry.interfaces.distribution import IDistributionSet

    >>> ubuntu = getUtility(IDistributionSet).get(1)
    >>> firefox = ubuntu.getSourcePackage('mozilla-firefox')
    >>> bug = firefox.createBug(CreateBugParams(
    ...     owner=sample_person, title='Yet another test bug',
    ...     comment="A sample bug for conjoined primary tests."))

    >>> targeted_bugtask = getUtility(IBugTaskSet).createTask(
    ...     bug, sample_person, firefox.development_version)

    >>> targeted_bugtask.conjoined_primary is None
    True

    >>> targeted_bugtask.conjoined_replica == bug.bugtasks[0]
    True

We use ensureBugTracker() to populate in the parameters that we don't
specify, such as the bug tracker's name.

    >>> bug_tracker = getUtility(IBugTrackerSet).ensureBugTracker(
    ...     bugtrackertype=BugTrackerType.ROUNDUP,
    ...     owner=sample_person, baseurl='http://some.where')
    >>> bug_watch = bug.addWatch(
    ...     bugtracker=bug_tracker, remotebug='1', owner=sample_person)

    >>> bug.bugtasks[0].bugwatch = bug_watch
    >>> flush_database_updates()

Now that we have our conjoined bug tasks we can use a test
implementation of the Roundup ExternalBugTracker to try and update
them. In fact, updating the bug watch will do nothing to the bug task to
which it is linked since that bug task is a conjoined replica. Conjoined
replicas must be updated through their conjoined primary.

    >>> bug.bugtasks[0].status.title
    'New'

    >>> import transaction
    >>> from lp.bugs.tests.externalbugtracker import (
    ...     TestRoundup)
    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.bugs.scripts.checkwatches import CheckwatchesMaster
    >>> bug_watch_updater = CheckwatchesMaster(transaction, FakeLogger())
    >>> external_bugtracker = TestRoundup(bug_tracker.baseurl)
    >>> with external_bugtracker.responses():
    ...     bug_watch_updater.updateBugWatches(
    ...         external_bugtracker, [bug_watch])
    INFO Updating 1 watches for 1 bugs on http://some.where

    >>> bug.bugtasks[0].status.title
    'New'


Getting linked bug watches for a product
----------------------------------------

Product has a method, getLinkedBugWatches, for getting all the bug
watches that are linked to a bug task targeted to the Product.

    >>> product = factory.makeProduct(official_malone=False)
    >>> [bug_watch.remotebug for bug_watch in product.getLinkedBugWatches()]
    []

    >>> product = factory.makeProduct(official_malone=False)
    >>> bug_task = factory.makeBugTask(target=product)
    >>> bug_watch = factory.makeBugWatch(remote_bug='42')
    >>> bug_task.bugwatch = bug_watch
    >>> product.bugtracker = bug_watch.bugtracker
    >>> for bug_watch in product.getLinkedBugWatches():
    ...     print(bug_watch.remotebug)
    42

It's not uncommon to link to other bug trackers than the one the Product
is using officially, for example to link to related bugs. To avoid
errors, we ignore such bug watches.

    >>> product = factory.makeProduct(official_malone=False)
    >>> bug_task = factory.makeBugTask(target=product)
    >>> bug_watch = factory.makeBugWatch(remote_bug='84')
    >>> bug_task.bugwatch = bug_watch
    >>> product.bugtracker == bug_watch.bugtracker
    False
    >>> [bug_watch.remotebug for bug_watch in product.getLinkedBugWatches()]
    []

Bug watches can be removed using the removeWatch method.

    >>> bug_watch = factory.makeBugWatch(remote_bug='42')
    >>> bug = bug_watch.bug
    >>> for bug_watch in bug.watches:
    ...     print(bug_watch.remotebug)
    42
    >>> bug.removeWatch(bug_watch, factory.makePerson())
    >>> [bug_watch.remotebug for bug_watch in bug.watches]
    []


Checking if a watch can be rescheduled
--------------------------------------

IBugWatch provides an attribute, can_be_rescheduled, which indicates
whether or not the watch can be rescheduled. For a new bug watch this
will be False.

    >>> schedulable_watch = factory.makeBugWatch()
    >>> schedulable_watch.next_check = None
    >>> schedulable_watch.can_be_rescheduled
    False

If there's been activity on the watch but it's always been successful,
can_be_rescheduled will be False.

    >>> schedulable_watch.addActivity()
    >>> schedulable_watch.can_be_rescheduled
    False

If the watch's updates have failed less than 60% of the time,
can_be_rescheduled will be True

    >>> import transaction
    >>> from lp.bugs.interfaces.bugwatch import BugWatchActivityStatus

    >>> transaction.commit()
    >>> schedulable_watch.addActivity(
    ...     result=BugWatchActivityStatus.BUG_NOT_FOUND)
    >>> schedulable_watch.can_be_rescheduled
    True

If the watch is rescheduled, can_be_rescheduled will be False, since the
next_check time for the watch will be in the past (or in this case is
now) and therefore it will be checked with the next checkwatches run.

    >>> from datetime import datetime
    >>> from pytz import utc
    >>> schedulable_watch.next_check = datetime.now(utc)
    >>> schedulable_watch.can_be_rescheduled
    False

However, if the watch has failed more than 60% of the time
can_be_rescheduled will be False, since it's assumed that the watch
needs attention in order for it to be able to work again.

    >>> schedulable_watch.next_check = None
    >>> transaction.commit()
    >>> schedulable_watch.addActivity(
    ...     result=BugWatchActivityStatus.BUG_NOT_FOUND)
    >>> schedulable_watch.can_be_rescheduled
    False

If the watch has run and failed only once, can_be_rescheduled will be
true.

    >>> from datetime import timedelta
    >>> run_once_failed_once_watch = factory.makeBugWatch()
    >>> run_once_failed_once_watch.next_check = (
    ...     datetime.now(utc) + timedelta(days=7))
    >>> run_once_failed_once_watch.addActivity(
    ...     result=BugWatchActivityStatus.BUG_NOT_FOUND)
    >>> run_once_failed_once_watch.can_be_rescheduled
    True

If the most recent update on the watch succeeded, can_be_rescheduled will
be False, regardless of the ratio of failures to successes.

    >>> transaction.commit()
    >>> run_once_failed_once_watch.addActivity()
    >>> run_once_failed_once_watch.can_be_rescheduled
    False


Rescheduling a watch
--------------------

The rescheduling of a watch is done via IBugWatch.setNextCheck(). This
is to ensure that watches are only rescheduled when can_be_rescheduled
is True (note that the BugWatch Scheduler bypasses setNextCheck() and
sets next_check directly because it has admin privileges).

The schedulable_watch that we used in the previous test cannot currently
be rescheduled.

    >>> schedulable_watch = factory.makeBugWatch()
    >>> schedulable_watch.next_check = None
    >>> schedulable_watch.can_be_rescheduled
    False

Calling setNextCheck() on this watch will cause an Exception,
BugWatchCannotBeRescheduled, to be raised.

    >>> schedulable_watch.setNextCheck(datetime.now(utc))
    Traceback (most recent call last):
      ...
    lp.bugs.interfaces.bugwatch.BugWatchCannotBeRescheduled

If we add some activity to the watch, to make its can_be_rescheduled
property become True, setNextCheck() will succeed.

    >>> schedulable_watch.addActivity(
    ...     result=BugWatchActivityStatus.BUG_NOT_FOUND)
    >>> schedulable_watch.can_be_rescheduled
    True

    >>> next_check = datetime.now(utc)
    >>> schedulable_watch.setNextCheck(next_check)
    >>> schedulable_watch.next_check == next_check
    True
