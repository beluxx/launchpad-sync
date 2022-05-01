# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugWatchSet."""

from datetime import (
    datetime,
    timedelta,
    )
import re
from urllib.parse import urlunsplit

from lazr.lifecycle.snapshot import Snapshot
from pytz import utc
from storm.store import Store
from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.interfaces.bugtracker import (
    BugTrackerType,
    IBugTrackerSet,
    )
from lp.bugs.interfaces.bugwatch import (
    BugWatchActivityStatus,
    IBugWatchSet,
    NoBugTrackerFound,
    UnrecognizedBugTrackerURL,
    )
from lp.bugs.model.bugwatch import (
    BugWatchDeletionError,
    get_bug_watch_ids,
    )
from lp.bugs.scripts.checkwatches.scheduler import MAX_SAMPLE_SIZE
from lp.registry.interfaces.person import IPersonSet
from lp.scripts.garbo import BugWatchActivityPruner
from lp.services.database.constants import UTC_NOW
from lp.services.log.logger import BufferLogger
from lp.services.webapp import urlsplit
from lp.testing import (
    ANONYMOUS,
    login,
    login_celebrity,
    login_person,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import switch_dbuser
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class ExtractBugTrackerAndBugTest(WithScenarios, TestCase):
    """Test BugWatchSet.extractBugTrackerAndBug."""

    scenarios = [
        ('Mantis', {
            'bugtracker_type': BugTrackerType.MANTIS,
            'bug_url': 'http://some.host/bugs/view.php?id=3224',
            'base_url': 'http://some.host/bugs/',
            'bug_id': '3224',
            }),
        ('Bugzilla', {
            'bugtracker_type': BugTrackerType.BUGZILLA,
            'bug_url': 'http://some.host/bugs/show_bug.cgi?id=3224',
            'base_url': 'http://some.host/bugs/',
            'bug_id': '3224',
            }),
        # Issuezilla is practically the same as Bugzilla, so we treat it as
        # a normal BUGZILLA type.
        ('Issuezilla', {
            'bugtracker_type': BugTrackerType.BUGZILLA,
            'bug_url': 'http://some.host/bugs/show_bug.cgi?issue=3224',
            'base_url': 'http://some.host/bugs/',
            'bug_id': '3224',
            }),
        ('RoundUp', {
            'bugtracker_type': BugTrackerType.ROUNDUP,
            'bug_url': 'http://some.host/some/path/issue377',
            'base_url': 'http://some.host/some/path/',
            'bug_id': '377',
            }),
        ('Trac', {
            'bugtracker_type': BugTrackerType.TRAC,
            'bug_url': 'http://some.host/some/path/ticket/42',
            'base_url': 'http://some.host/some/path/',
            'bug_id': '42',
            }),
        ('Debbugs', {
            'bugtracker_type': BugTrackerType.DEBBUGS,
            'bug_url': (
                'http://some.host/some/path/cgi-bin/bugreport.cgi?bug=42'),
            'base_url': 'http://some.host/some/path/',
            'bug_id': '42',
            }),
        ('DebbugsShorthand', {
            'bugtracker_type': BugTrackerType.DEBBUGS,
            'bug_url': 'http://bugs.debian.org/42',
            'base_url': 'http://bugs.debian.org/',
            'bug_id': '42',
            'already_registered': True,
            }),
        # SourceForge-like URLs, though not actually SourceForge itself.
        ('XForge', {
            'bugtracker_type': BugTrackerType.SOURCEFORGE,
            'bug_url': (
                'http://gforge.example.com/tracker/index.php'
                '?func=detail&aid=90812&group_id=84122&atid=575154'),
            'base_url': 'http://gforge.example.com/',
            'bug_id': '90812',
            }),
        ('RT', {
            'bugtracker_type': BugTrackerType.RT,
            'bug_url': 'http://some.host/Ticket/Display.html?id=2379',
            'base_url': 'http://some.host/',
            'bug_id': '2379',
            }),
        ('CPAN', {
            'bugtracker_type': BugTrackerType.RT,
            'bug_url': 'http://rt.cpan.org/Public/Bug/Display.html?id=2379',
            'base_url': 'http://rt.cpan.org/',
            'bug_id': '2379',
            }),
        ('Savannah', {
            'bugtracker_type': BugTrackerType.SAVANE,
            'bug_url': 'http://savannah.gnu.org/bugs/?22003',
            'base_url': 'http://savannah.gnu.org/',
            'bug_id': '22003',
            'already_registered': True,
            }),
        ('SavannahWithParameters', {
            'bugtracker_type': BugTrackerType.SAVANE,
            'bug_url': (
                'http://savannah.gnu.org/bugs/index.php'
                '?func=detailitem&item_id=22003'),
            'base_url': 'http://savannah.gnu.org/',
            'bug_id': '22003',
            'already_registered': True,
            }),
        ('Savane', {
            'bugtracker_type': BugTrackerType.SAVANE,
            'bug_url': 'http://savane.example.com/bugs/?12345',
            'base_url': 'http://savane.example.com/',
            'bug_id': '12345',
            }),
        ('PHPProject', {
            'bugtracker_type': BugTrackerType.PHPPROJECT,
            'bug_url': 'http://phptracker.example.com/bug.php?id=12345',
            'base_url': 'http://phptracker.example.com/',
            'bug_id': '12345',
            }),
        ('GoogleCode', {
            'bugtracker_type': BugTrackerType.GOOGLE_CODE,
            'bug_url': (
                'http://code.google.com/p/myproject/issues/detail?id=12345'),
            'base_url': 'http://code.google.com/p/myproject/issues',
            'bug_id': '12345',
            }),
        ('GitHub', {
            'bugtracker_type': BugTrackerType.GITHUB,
            'bug_url': 'https://github.com/user/repository/issues/12345',
            'base_url': 'https://github.com/user/repository/issues',
            'bug_id': '12345',
            }),
        ('GitLab', {
            'bugtracker_type': BugTrackerType.GITLAB,
            'bug_url': 'https://gitlab.com/user/repository/issues/12345',
            'base_url': 'https://gitlab.com/user/repository/issues',
            'bug_id': '12345',
            }),
        ]

    layer = LaunchpadFunctionalLayer

    # A URL to an unregistered bug tracker.
    base_url = None

    # The bug tracker type to be tested.
    bugtracker_type = None

    # A sample URL to a bug in the bug tracker.
    bug_url = None

    # The bug id in the sample bug_url.
    bug_id = None

    # True if the bug tracker is already registered in sampledata.
    already_registered = False

    def setUp(self):
        super().setUp()
        login(ANONYMOUS)
        self.bugwatch_set = getUtility(IBugWatchSet)
        self.bugtracker_set = getUtility(IBugTrackerSet)
        self.sample_person = getUtility(IPersonSet).getByEmail(
            'test@canonical.com')

    def test_unknown_baseurl(self):
        # extractBugTrackerAndBug raises an exception if it can't even
        # decide what kind of bug tracker the bug URL points to.
        self.assertRaises(
            UnrecognizedBugTrackerURL,
            self.bugwatch_set.extractBugTrackerAndBug,
            'http://no.such/base/url/42')

    def test_registered_tracker_url(self):
        # If extractBugTrackerAndBug can extract a base URL, and there is a
        # bug tracker registered with that URL, the registered bug
        # tracker will be returned, together with the bug id that was
        # extracted from the bug URL.
        expected_tracker = self.bugtracker_set.ensureBugTracker(
             self.base_url, self.sample_person, self.bugtracker_type)
        bugtracker, bug = self.bugwatch_set.extractBugTrackerAndBug(
            self.bug_url)
        self.assertEqual(bugtracker, expected_tracker)
        self.assertEqual(bug, self.bug_id)

    def test_unregistered_tracker_url(self):
        # A NoBugTrackerFound exception is raised if extractBugTrackerAndBug
        # can extract a base URL and bug id from the URL but there's no
        # such bug tracker registered in Launchpad.
        if self.already_registered:
            return
        self.assertIsNone(self.bugtracker_set.queryByBaseURL(self.base_url))
        try:
            bugtracker, bug = self.bugwatch_set.extractBugTrackerAndBug(
                self.bug_url)
        except NoBugTrackerFound as error:
            # The raised exception should contain enough information so
            # that we can register a new bug tracker.
            self.assertEqual(error.base_url, self.base_url)
            self.assertEqual(error.remote_bug, self.bug_id)
            self.assertEqual(error.bugtracker_type, self.bugtracker_type)
        else:
            self.fail(
                "NoBugTrackerFound wasn't raised by extractBugTrackerAndBug")

    def test_invalid_bug_number(self):
        # Replace the second digit of the remote bug id with an E, which all
        # parsers will reject as invalid.
        invalid_url = re.sub(r'(\d)\d', r'\1E', self.bug_url, count=1)
        self.assertRaises(
            UnrecognizedBugTrackerURL,
            self.bugwatch_set.extractBugTrackerAndBug, invalid_url)


class SFExtractBugTrackerAndBugTest(ExtractBugTrackerAndBugTest):
    """Ensure BugWatchSet.extractBugTrackerAndBug works with SF URLs.

    We have only one SourceForge tracker registered in Launchpad, so we
    don't care about the aid and group_id, only about atid which is the
    bug id.
    """

    scenarios = [
        # We have only one SourceForge tracker registered in Launchpad, so
        # we don't care about the aid and group_id, only about atid which is
        # the bug id.
        ('SourceForge', {
            'bugtracker_type': BugTrackerType.SOURCEFORGE,
            'bug_url': (
                'http://sourceforge.net/tracker/index.php'
                '?func=detail&aid=1568562&group_id=84122&atid=575154'),
            'base_url': 'http://sourceforge.net/',
            'bug_id': '1568562',
            }),
        # New SF tracker URLs.
        ('SourceForgeTracker2', {
            'bugtracker_type': BugTrackerType.SOURCEFORGE,
            'bug_url': (
                'http://sourceforge.net/tracker2/'
                '?func=detail&aid=1568562&group_id=84122&atid=575154'),
            'base_url': 'http://sourceforge.net/',
            'bug_id': '1568562',
            }),
        ]

    # The SourceForge tracker is always registered.
    already_registered = True

    def test_aliases(self):
        """Test that parsing SourceForge URLs works with the SF aliases."""
        original_bug_url = self.bug_url
        original_base_url = self.base_url
        url_bits = urlsplit(original_bug_url)
        sf_bugtracker = self.bugtracker_set.getByName(name='sf')

        # Carry out all the applicable tests for each alias.
        for alias in sf_bugtracker.aliases:
            alias_bits = urlsplit(alias)
            self.base_url = alias

            bug_url_bits = (
                alias_bits[0],
                alias_bits[1],
                url_bits[2],
                url_bits[3],
                url_bits[4],
                )

            self.bug_url = urlunsplit(bug_url_bits)

            self.test_registered_tracker_url()
            self.test_unknown_baseurl()

        self.bug_url = original_bug_url
        self.base_url = original_base_url


class EmailAddressExtractBugTrackerAndBugTest(ExtractBugTrackerAndBugTest):
    """Ensure BugWatchSet.extractBugTrackerAndBug works with email addresses.
    """

    scenarios = None
    bugtracker_type = BugTrackerType.EMAILADDRESS
    bug_url = 'mailto:foo.bar@example.com'
    base_url = 'mailto:foo.bar@example.com'
    bug_id = ''

    def test_extract_bug_tracker_and_bug_rejects_invalid_email_address(self):
        # BugWatch.extractBugTrackerAndBug() will reject invalid email
        # addresses.
        self.assertRaises(UnrecognizedBugTrackerURL,
            self.bugwatch_set.extractBugTrackerAndBug,
            url=r'this\.is@@a.bad.email.address')

    def test_invalid_bug_number(self):
        # Test does not make sense for email addresses.
        pass


class TestBugWatch(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_bugtasks_to_update(self):
        # The bugtasks_to_update property should yield the linked bug
        # tasks which are not conjoined and for which the bug is not a
        # duplicate.
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(target=product, owner=product.owner)
        product_task = bug.getBugTask(product)
        watch = self.factory.makeBugWatch(bug=bug)
        product_task.bugwatch = watch
        # For a single-task bug the bug task is eligible for update.
        self.assertEqual(
            [product_task], list(
                removeSecurityProxy(watch).bugtasks_to_update))
        # If we add a task such that the existing task becomes a
        # conjoined replica, only the primary task will be eligible for
        # update.
        product_series_task = self.factory.makeBugTask(
            bug=bug, target=product.development_focus)
        product_series_task.bugwatch = watch
        self.assertEqual(
            [product_series_task], list(
                removeSecurityProxy(watch).bugtasks_to_update))
        # But once the bug is marked as a duplicate,
        # bugtasks_to_update yields nothing.
        bug.markAsDuplicate(
            self.factory.makeBug(target=product, owner=product.owner))
        self.assertEqual(
            [], list(removeSecurityProxy(watch).bugtasks_to_update))

    def test_updateStatus_with_duplicate_bug(self):
        # Calling BugWatch.updateStatus() will not update the status
        # of a task that is part of a duplicate bug.
        bug = self.factory.makeBug()
        bug.markAsDuplicate(self.factory.makeBug())
        login_person(bug.owner)
        bug_task = bug.default_bugtask
        bug_task.bugwatch = self.factory.makeBugWatch()
        bug_task_initial_status = bug_task.status
        self.assertNotEqual(BugTaskStatus.INPROGRESS, bug_task.status)
        bug_task.bugwatch.updateStatus('foo', BugTaskStatus.INPROGRESS)
        self.assertEqual(bug_task_initial_status, bug_task.status)
        # Once the task is no longer linked to a duplicate bug, the
        # status will get updated.
        bug.markAsDuplicate(None)
        bug_task.bugwatch.updateStatus('foo', BugTaskStatus.INPROGRESS)
        self.assertEqual(BugTaskStatus.INPROGRESS, bug_task.status)

    def test_updateImportance_with_duplicate_bug(self):
        # Calling BugWatch.updateImportance() will not update the
        # importance of a task that is part of a duplicate bug.
        bug = self.factory.makeBug()
        bug.markAsDuplicate(self.factory.makeBug())
        login_person(bug.owner)
        bug_task = bug.default_bugtask
        bug_task.bugwatch = self.factory.makeBugWatch()
        bug_task_initial_importance = bug_task.importance
        self.assertNotEqual(BugTaskImportance.HIGH, bug_task.importance)
        bug_task.bugwatch.updateImportance('foo', BugTaskImportance.HIGH)
        self.assertEqual(bug_task_initial_importance, bug_task.importance)
        # Once the task is no longer linked to a duplicate bug, the
        # importance will get updated.
        bug.markAsDuplicate(None)
        bug_task.bugwatch.updateImportance('foo', BugTaskImportance.HIGH)
        self.assertEqual(BugTaskImportance.HIGH, bug_task.importance)

    def test_get_bug_watch_ids(self):
        # get_bug_watch_ids() yields the IDs for the given bug
        # watches.
        bug_watches = [self.factory.makeBugWatch()]
        self.assertEqual(
            [bug_watch.id for bug_watch in bug_watches],
            list(get_bug_watch_ids(bug_watches)))

    def test_get_bug_watch_ids_with_iterator(self):
        # get_bug_watch_ids() can also accept an iterator.
        bug_watches = [self.factory.makeBugWatch()]
        self.assertEqual(
            [bug_watch.id for bug_watch in bug_watches],
            list(get_bug_watch_ids(iter(bug_watches))))

    def test_get_bug_watch_ids_with_id_list(self):
        # If something resembling an ID is found, get_bug_watch_ids()
        # yields it unaltered.
        bug_watches = [1, 2, 3]
        self.assertEqual(
            bug_watches, list(get_bug_watch_ids(bug_watches)))

    def test_get_bug_watch_ids_with_mixed_list(self):
        # get_bug_watch_ids() does the right thing when the given
        # objects are a mix of bug watches and IDs.
        bug_watch = self.factory.makeBugWatch()
        bug_watches = [1234, bug_watch]
        self.assertEqual(
            [1234, bug_watch.id], list(get_bug_watch_ids(bug_watches)))

    def test_get_bug_watch_ids_with_others_in_list(self):
        # get_bug_watch_ids() asserts that all arguments are bug
        # watches or resemble IDs.
        self.assertRaises(
            AssertionError, list, get_bug_watch_ids(['fred']))

    def test_destroySelf_raise_error_when_linked_to_a_task(self):
        # It's not possible to delete a bug watch that's linked to a
        # task. Trying will result in a BugWatchDeletionError.
        bug_watch = self.factory.makeBugWatch()
        bug = bug_watch.bug
        bug.default_bugtask.bugwatch = bug_watch
        self.assertRaises(BugWatchDeletionError, bug_watch.destroySelf)

    def test_deleting_bugwatch_deletes_bugwatchactivity(self):
        # Deleting a bug watch will also delete all its
        # BugWatchActivity entries.
        bug_watch = self.factory.makeBugWatch()
        for i in range(5):
            bug_watch.addActivity(message="Activity %s" % i)
        store = Store.of(bug_watch)
        watch_activity_query = (
            "SELECT id FROM BugWatchActivity WHERE bug_watch = %s" %
            bug_watch.id)
        self.assertNotEqual(0, store.execute(watch_activity_query).rowcount)
        bug_watch.destroySelf()
        self.assertEqual(0, store.execute(watch_activity_query).rowcount)


class TestBugWatchSet(TestCaseWithFactory):
    """Tests for the bugwatch updating system."""

    layer = LaunchpadZopelessLayer

    def test_getBugWatchesForRemoteBug(self):
        # getBugWatchesForRemoteBug() returns bug watches from that
        # refer to the remote bug.
        bug_watches_alice = [
            self.factory.makeBugWatch(remote_bug="alice"),
            ]
        bug_watches_bob = [
            self.factory.makeBugWatch(remote_bug="bob"),
            self.factory.makeBugWatch(remote_bug="bob"),
            ]
        bug_watch_set = getUtility(IBugWatchSet)
        # Passing in the remote bug ID gets us every bug watch that
        # refers to that remote bug.
        self.assertEqual(
            set(bug_watches_alice),
            set(bug_watch_set.getBugWatchesForRemoteBug('alice')))
        self.assertEqual(
            set(bug_watches_bob),
            set(bug_watch_set.getBugWatchesForRemoteBug('bob')))
        # The search can be narrowed by passing in a list or other
        # iterable collection of bug watch IDs.
        bug_watches_limited = bug_watches_alice + bug_watches_bob[:1]
        self.assertEqual(
            set(bug_watches_bob[:1]),
            set(bug_watch_set.getBugWatchesForRemoteBug('bob', [
                        bug_watch.id for bug_watch in bug_watches_limited])))


class TestBugWatchSetBulkOperations(TestCaseWithFactory):
    """Tests for the bugwatch updating system."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super().setUp()
        self.bug_watches = [
            self.factory.makeBugWatch(remote_bug='alice'),
            self.factory.makeBugWatch(remote_bug='bob'),
            ]
        for bug_watch in self.bug_watches:
            bug_watch.lastchecked = None
            bug_watch.last_error_type = None
            bug_watch.next_check = UTC_NOW

    def _checkStatusOfBugWatches(
        self, last_checked_is_null, next_check_is_null, last_error_type):
        for bug_watch in self.bug_watches:
            self.assertEqual(
                last_checked_is_null, bug_watch.lastchecked is None)
            self.assertEqual(
                next_check_is_null, bug_watch.next_check is None)
            self.assertEqual(
                last_error_type, bug_watch.last_error_type)

    def test_bulkSetError(self):
        # Called with only bug watches, bulkSetError() marks the
        # watches as checked without error, and unscheduled.
        getUtility(IBugWatchSet).bulkSetError(self.bug_watches)
        self._checkStatusOfBugWatches(False, True, None)

    def test_bulkSetError_with_error(self):
        # Called with bug watches and an error, bulkSetError() marks
        # the watches with the given error, and unschedules them.
        error = BugWatchActivityStatus.BUG_NOT_FOUND
        getUtility(IBugWatchSet).bulkSetError(self.bug_watches, error)
        self._checkStatusOfBugWatches(False, True, error)

    def _checkActivityForBugWatches(self, result, message, oops_id):
        for bug_watch in self.bug_watches:
            latest_activity = bug_watch.activity.first()
            self.assertEqual(result, latest_activity.result)
            self.assertEqual(message, latest_activity.message)
            self.assertEqual(oops_id, latest_activity.oops_id)

    def test_bulkAddActivity(self):
        # Called with only bug watches, bulkAddActivity() adds
        # successful activity records for the given bug watches.
        getUtility(IBugWatchSet).bulkAddActivity(self.bug_watches)
        self._checkActivityForBugWatches(
            BugWatchActivityStatus.SYNC_SUCCEEDED, None, None)

    def test_bulkAddActivity_with_error(self):
        # Called with additional error information, bulkAddActivity()
        # adds appropriate and identical activity records for each of
        # the given bug watches.
        error = BugWatchActivityStatus.PRIVATE_REMOTE_BUG
        getUtility(IBugWatchSet).bulkAddActivity(
            self.bug_watches, error, "OOPS-1234")
        self._checkActivityForBugWatches(error, None, "OOPS-1234")

    def test_bulkAddActivity_with_id_list(self):
        # The ids of bug watches can be passed in.
        getUtility(IBugWatchSet).bulkAddActivity(
            [bug_watch.id for bug_watch in self.bug_watches])
        self._checkActivityForBugWatches(
            BugWatchActivityStatus.SYNC_SUCCEEDED, None, None)

    def test_bulkAddActivity_with_mixed_list(self):
        # The list passed in can contain a mix of bug watches and
        # their ids.
        getUtility(IBugWatchSet).bulkAddActivity(
            [bug_watch.id for bug_watch in self.bug_watches[::2]] +
            [bug_watch for bug_watch in self.bug_watches[1::2]])
        self._checkActivityForBugWatches(
            BugWatchActivityStatus.SYNC_SUCCEEDED, None, None)

    def test_bulkAddActivity_with_iterator(self):
        # Any iterator can be passed in.
        getUtility(IBugWatchSet).bulkAddActivity(
            bug_watch for bug_watch in self.bug_watches)
        self._checkActivityForBugWatches(
            BugWatchActivityStatus.SYNC_SUCCEEDED, None, None)


class TestBugWatchBugTasks(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp('test@canonical.com')
        self.bug_watch = self.factory.makeBugWatch()

    def test_bugtasks(self):
        # BugWatch.bugtasks is always a list.
        self.assertIsInstance(
            self.bug_watch.bugtasks, list)


class TestBugWatchActivityPruner(TestCaseWithFactory):
    """TestCase for the BugWatchActivityPruner."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super().setUp('foo.bar@canonical.com')
        self.bug_watch = self.factory.makeBugWatch()
        for i in range(MAX_SAMPLE_SIZE + 1):
            self.bug_watch.addActivity()
        transaction.commit()

    def test_pruneBugWatchActivity_leaves_most_recent(self):
        # BugWatchActivityPruner.pruneBugWatchActivity() will delete all
        # but the n most recent BugWatchActivity items for a bug watch,
        # where n is determined by checkwatches.scheduler.MAX_SAMPLE_SIZE.
        for i in range(5):
            self.bug_watch.addActivity(message="Activity %s" % i)

        switch_dbuser('garbo')
        self.pruner = BugWatchActivityPruner(BufferLogger())
        self.addCleanup(self.pruner.cleanUp)

        # MAX_SAMPLE_SIZE + 1 created in setUp(), and 5 more created
        # just above.
        self.assertEqual(MAX_SAMPLE_SIZE + 6, self.bug_watch.activity.count())

        # Run the pruner
        while not self.pruner.isDone():
            self.pruner(chunk_size=3)

        # Only MAX_SAMPLE_SIZE items should be left.
        self.assertEqual(MAX_SAMPLE_SIZE, self.bug_watch.activity.count())

        # They should be the most recent items - the ones created at the
        # start of this test.
        messages = [activity.message for activity in self.bug_watch.activity]
        for i in range(MAX_SAMPLE_SIZE):
            self.assertIn("Activity %s" % i, messages)


class TestBugWatchResetting(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super().setUp(user=ADMIN_EMAIL)
        self.bug_watch = self.factory.makeBugWatch()
        naked = removeSecurityProxy(self.bug_watch)
        naked.last_error_type = BugWatchActivityStatus.BUG_NOT_FOUND
        naked.lastchanged = datetime.now(utc) - timedelta(days=1)
        naked.lastchecked = datetime.now(utc) - timedelta(days=1)
        naked.next_check = datetime.now(utc) + timedelta(days=7)
        naked.remote_importance = 'IMPORTANT'
        naked.remotestatus = 'FIXED'
        self.default_bug_watch_fields = [
            'last_error_type',
            'lastchanged',
            'lastchecked',
            'next_check',
            'remote_importance',
            'remotestatus',
            ]
        self.original_bug_watch = Snapshot(
            self.bug_watch, self.default_bug_watch_fields)

    def _assertBugWatchHasBeenChanged(self, expected_changes=None):
        """Assert that a bug watch has been changed.

        :param expected_changes: A list of the attribute names that are
            expected to have changed. If supplied, an assertion error
            will be raised if one of the expected_changes members has
            not changed *or* an attribute not in expected_changes has
            changed. If not supplied, *all* attributes are expected to
            have changed.
        """
        if expected_changes is None:
            expected_changes = self.default_bug_watch_fields

        actual_changes = []
        has_changed = True
        for expected_change in expected_changes:
            original_value = getattr(self.original_bug_watch, expected_change)
            current_value = getattr(self.bug_watch, expected_change)
            if original_value != current_value:
                has_changed = has_changed and True
                actual_changes.append(expected_change)
            else:
                has_changed = False

        self.assertTrue(
            has_changed,
            "Bug watch did not change as expected.\n"
            "Expected changes: %s\n"
            "Actual changes: %s" % (expected_changes, actual_changes))

    def test_reset_resets(self):
        # Calling reset() on a watch resets all of the attributes of the
        # bug watch.
        admin_user = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        login_person(admin_user)
        self.bug_watch.reset()
        self._assertBugWatchHasBeenChanged()

    def test_unprivileged_user_cant_reset_watches(self):
        # An unprivileged user can't call the reset() method on a bug
        # watch.
        unprivileged_user = self.factory.makePerson()
        login_person(unprivileged_user)
        self.assertRaises(Unauthorized, getattr, self.bug_watch, 'reset')

    def test_registry_expert_can_reset_watches(self):
        # A registry expert can call the reset() method on a bug watch.
        login_celebrity("registry_experts")
        self.bug_watch.reset()
        self._assertBugWatchHasBeenChanged()


load_tests = load_tests_apply_scenarios
