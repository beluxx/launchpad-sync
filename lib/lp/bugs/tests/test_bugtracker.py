# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
from doctest import (
    DocTestSuite,
    ELLIPSIS,
    NORMALIZE_WHITESPACE,
    )
import unittest

from lazr.lifecycle.snapshot import Snapshot
from pytz import utc
import responses
from six.moves.urllib_parse import urlencode
from testtools.matchers import (
    Equals,
    MatchesListwise,
    MatchesStructure,
    )
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.externalbugtracker import (
    BugTrackerConnectError,
    Mantis,
    )
from lp.bugs.interfaces.bugtracker import (
    BugTrackerType,
    IBugTracker,
    )
from lp.bugs.model.bugtracker import (
    BugTrackerSet,
    make_bugtracker_name,
    make_bugtracker_title,
    )
from lp.registry.interfaces.person import IPersonSet
from lp.testing import (
    login,
    login_celebrity,
    login_person,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class TestBugTrackerSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_trackers(self):
        tracker = self.factory.makeBugTracker()
        trackers = BugTrackerSet()
        # Active trackers are in all trackers,
        self.assertTrue(tracker in trackers.getAllTrackers())
        # and active,
        self.assertTrue(tracker in trackers.getAllTrackers(active=True))
        # But not inactive.
        self.assertFalse(tracker in trackers.getAllTrackers(active=False))
        login(ADMIN_EMAIL)
        tracker.active = False
        # Inactive trackers are in all trackers
        self.assertTrue(tracker in trackers.getAllTrackers())
        # and inactive,
        self.assertTrue(tracker in trackers.getAllTrackers(active=False))
        # but not in active.
        self.assertFalse(tracker in trackers.getAllTrackers(active=True))

    def test_inactive_products_in_pillars(self):
        # the list of pillars should only contain active
        # products and projects
        tracker = self.factory.makeBugTracker()
        trackers = BugTrackerSet()
        product1 = self.factory.makeProduct()
        product2 = self.factory.makeProduct()
        project1 = self.factory.makeProject()
        project2 = self.factory.makeProject()
        login_celebrity('admin')
        product1.bugtracker = tracker
        product2.bugtracker = tracker
        project1.bugtracker = tracker
        project2.bugtracker = tracker
        pillars = trackers.getPillarsForBugtrackers(trackers)
        self.assertContentEqual(
            [product1, product2, project1, project2], pillars[tracker])
        product1.active = False
        project2.active = False
        pillars = trackers.getPillarsForBugtrackers(trackers)
        self.assertContentEqual(
            [product2, project1], pillars[tracker])


class BugTrackerTestCase(TestCaseWithFactory):
    """Unit tests for the `BugTracker` class."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(BugTrackerTestCase, self).setUp()
        self.bug_tracker = self.factory.makeBugTracker()
        for i in range(5):
            self.factory.makeBugWatch(bugtracker=self.bug_tracker)

        self.now = datetime.now(utc)

    def test_multi_product_constraints_observed(self):
        """BugTrackers for which multi_product=True should return None
        when no remote product is passed to getBugFilingURL().

        BugTrackers for which multi_product=False should still return a
        URL even when getBugFilingURL() is passed no remote product.
        """
        for type in BugTrackerType.items:
            bugtracker = self.factory.makeBugTracker(bugtrackertype=type)

            bugtracker_urls = bugtracker.getBugFilingAndSearchLinks(None)
            bug_filing_url = bugtracker_urls['bug_filing_url']
            bug_search_url = bugtracker_urls['bug_search_url']

            if bugtracker.multi_product:
                self.assertTrue(
                    bug_filing_url is None,
                    "getBugFilingAndSearchLinks() should return a "
                    "bug_filing_url of None for BugTrackers of type %s when "
                    "no remote product is passed." %
                    type.title)
                self.assertTrue(
                    bug_search_url is None,
                    "getBugFilingAndSearchLinks() should return a "
                    "bug_search_url of None for BugTrackers of type %s when "
                    "no remote product is passed." %
                    type.title)
            else:
                self.assertTrue(
                    bug_filing_url is not None,
                    "getBugFilingAndSearchLinks() should not return a "
                    "bug_filing_url of None for BugTrackers of type %s when "
                    "no remote product is passed." %
                    type.title)
                self.assertTrue(
                    bug_search_url is not None,
                    "getBugFilingAndSearchLinks() should not return a "
                    "bug_search_url of None for BugTrackers of type %s when "
                    "no remote product is passed." %
                    type.title)

    def test_attributes_not_in_snapshot(self):
        # A snapshot of an IBugTracker will not contain a copy of
        # several attributes.
        marker = object()
        original = self.factory.makeBugTracker()
        attributes = [
            'watches',
            'watches_needing_update',
            'watches_ready_to_check',
            'watches_with_unpushed_comments',
            ]
        for attribute in attributes:
            self.assertTrue(
                getattr(original, attribute, marker) is not marker,
                "Attribute %s missing from bug tracker." % attribute)
        snapshot = Snapshot(original, providing=IBugTracker)
        for attribute in attributes:
            self.assertTrue(
                getattr(snapshot, attribute, marker) is marker,
                "Attribute %s not missing from snapshot." % attribute)

    def test_watches_ready_to_check(self):
        bug_tracker = self.factory.makeBugTracker()
        # Initially there are no watches, so none need to be checked.
        self.assertTrue(bug_tracker.watches_ready_to_check.is_empty())
        # A bug watch without a next_check set is not ready either.
        bug_watch = self.factory.makeBugWatch(bugtracker=bug_tracker)
        removeSecurityProxy(bug_watch).next_check = None
        self.assertTrue(bug_tracker.watches_ready_to_check.is_empty())
        # If we set its next_check date, it will be ready.
        removeSecurityProxy(bug_watch).next_check = (
            datetime.now(utc) - timedelta(hours=1))
        self.assertTrue(1, bug_tracker.watches_ready_to_check.count())
        self.assertEqual(bug_watch, bug_tracker.watches_ready_to_check.one())

    def test_watches_with_unpushed_comments(self):
        bug_tracker = self.factory.makeBugTracker()
        # Initially there are no watches, so there are no unpushed
        # comments.
        self.assertTrue(bug_tracker.watches_with_unpushed_comments.is_empty())
        # A new bug watch has no comments, so the same again.
        bug_watch = self.factory.makeBugWatch(bugtracker=bug_tracker)
        self.assertTrue(bug_tracker.watches_with_unpushed_comments.is_empty())
        # A comment linked to the bug watch will be found.
        login_person(bug_watch.bug.owner)
        message = self.factory.makeMessage(owner=bug_watch.owner)
        bug_message = bug_watch.bug.linkMessage(message, bug_watch)
        self.assertTrue(1, bug_tracker.watches_with_unpushed_comments.count())
        self.assertEqual(
            bug_watch, bug_tracker.watches_with_unpushed_comments.one())
        # Once the comment has been pushed, it will no longer be found.
        removeSecurityProxy(bug_message).remote_comment_id = 'brains'
        self.assertTrue(bug_tracker.watches_with_unpushed_comments.is_empty())

    def _assertBugWatchesAreCheckedInTheFuture(self):
        """Check the dates of all self.bug_tracker.watches.

        Raise an error if:
         * The next_check dates aren't in the future.
         * The next_check dates aren't <= 1 day in the future.
         * The lastcheck dates are not None
         * The last_error_types are not None.
        """
        for watch in self.bug_tracker.watches:
            self.assertTrue(
                watch.next_check is not None,
                "BugWatch next_check time should not be None.")
            self.assertTrue(
                watch.next_check >= self.now,
                "BugWatch next_check time should be in the future.")
            self.assertTrue(
                watch.next_check <= self.now + timedelta(days=1),
                "BugWatch next_check time should be one day or less in "
                "the future.")
            self.assertTrue(
                watch.lastchecked is None,
                "BugWatch lastchecked should be None.")
            self.assertTrue(
                watch.last_error_type is None,
                "BugWatch last_error_type should be None.")

    def test_unprivileged_user_cant_reset_watches(self):
        # It isn't possible for a user who isn't an admin or a member of
        # the Launchpad Developers team to reset the watches for a bug
        # tracker.
        unprivileged_user = self.factory.makePerson()
        login_person(unprivileged_user)
        self.assertRaises(
            Unauthorized, getattr, self.bug_tracker, 'resetWatches',
            "Unprivileged users should not be allowed to reset a "
            "tracker's watches.")

    def test_admin_can_reset_watches(self):
        # Launchpad admins can reset the watches on a bugtracker.
        admin_user = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        login_person(admin_user)
        self.bug_tracker.resetWatches()
        self._assertBugWatchesAreCheckedInTheFuture()

    def test_registry_can_reset_watches(self):
        # Registry experts can reset the watches on a bugtracker.
        login_celebrity("registry_experts")
        self.bug_tracker.resetWatches()
        self._assertBugWatchesAreCheckedInTheFuture()

    def test_janitor_can_reset_watches(self):
        # The Janitor can reset the watches on a bug tracker.
        janitor = getUtility(ILaunchpadCelebrities).janitor
        login_person(janitor)
        self.bug_tracker.resetWatches()
        self._assertBugWatchesAreCheckedInTheFuture()


class TestMantis(TestCaseWithFactory):
    """Tests for the Mantis-specific bug tracker code."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestMantis, self).setUp()
        # We need to commit to avoid there being errors from the
        # checkwatches isolation protection code.
        transaction.commit()

    @responses.activate
    def test_mantis_login_redirects(self):
        # The Mantis bug tracker needs a special HTTP redirect handler
        # in order to login in. Ensure that redirects to the page with
        # the login form are indeed changed to redirects the form submit
        # URL.
        location = '/login_page.php?' + urlencode({'return': '/some/page'})
        responses.add(
            'GET', 'http://mantis.example.com/some/page',
            status=302, headers={'Location': location})
        responses.add(
            'GET',
            'http://mantis.example.com/login.php?'
            'username=guest&password=guest&return=%2Fsome%2Fpage',
            match_querystring=True, status=200, body='sentinel')
        tracker = Mantis('http://mantis.example.com')
        response = tracker.makeRequest(
            'GET', 'http://mantis.example.com/some/page')
        self.assertEqual(200, response.status_code)
        self.assertEqual(b'sentinel', response.content)
        # The request visited the original URL followed by the URL rewritten
        # by mantis_login_hook.
        self.assertThat(response.history, MatchesListwise([
            MatchesStructure(
                status_code=Equals(302),
                request=MatchesStructure.byEquality(
                    url='http://mantis.example.com/some/page')),
            ]))
        self.assertEqual(
            'http://mantis.example.com/login.php?'
            'username=guest&password=guest&return=%2Fsome%2Fpage',
            response.request.url)

    @responses.activate
    def test_mantis_makeRequest_can_handle_cookies(self):
        # Ensure that the makeRequest method of the Mantis bug tracker
        # handles cookies.
        responses.add(
            'GET', 'http://mantis.example.com/', status=200,
            headers={'Set-Cookie': 'foo=bar'})
        tracker = Mantis('http://mantis.example.com')
        tracker.makeRequest('GET', 'http://mantis.example.com/')
        self.assertThat(tracker._cookie_jar, MatchesListwise([
            MatchesStructure.byEquality(name='foo', value='bar'),
            ]))

    @responses.activate
    def test_mantis_csv_file_http_500_error(self):
        # If a Mantis bug tracker returns a HTTP 500 error when the
        # URL for CSV data is accessed, we treat this as an
        # indication that we should screen scrape the bug data and
        # thus set csv_data to None.
        responses.add(
            'POST', 'http://mantis.example.com/view_all_set.php', status=200)
        responses.add(
            'GET', 'http://mantis.example.com/csv_export.php', status=500)
        tracker = Mantis('http://mantis.example.com')
        self.assertIsNone(tracker.csv_data)

    @responses.activate
    def test_mantis_csv_file_other_http_errors(self):
        # If the Mantis server returns other HTTP errors than 500,
        # they appear as BugTrackerConnectErrors.
        responses.add(
            'POST', 'http://mantis.example.com/view_all_set.php', status=200)
        responses.add(
            'GET', 'http://mantis.example.com/csv_export.php', status=503)
        tracker = Mantis('http://mantis.example.com')
        self.assertRaises(BugTrackerConnectError, tracker._csv_data)

        responses.remove('GET', 'http://mantis.example.com/csv_export.php')
        responses.add(
            'GET', 'http://mantis.example.com/csv_export.php', status=404)
        self.assertRaises(BugTrackerConnectError, tracker._csv_data)


class TestSourceForge(TestCaseWithFactory):
    """Tests for SourceForge-specific BugTracker code."""

    layer = DatabaseFunctionalLayer

    def test_getBugFilingAndSearchLinks_handles_bad_data_correctly(self):
        # It's possible for Product.remote_product to contain data
        # that's not valid for SourceForge BugTrackers.
        # getBugFilingAndSearchLinks() will return None if it encounters
        # bad data in the remote_product field.
        remote_product = "this is not valid"
        bug_tracker = self.factory.makeBugTracker(
            bugtrackertype=BugTrackerType.SOURCEFORGE)
        self.assertIs(
            None, bug_tracker.getBugFilingAndSearchLinks(remote_product))


class TestMakeBugtrackerName(TestCase):
    """Tests for make_bugtracker_name."""

    def test_url(self):
        self.assertEqual(
            'auto-bugs.example.com',
            make_bugtracker_name('http://bugs.example.com/shrubbery'))

    def test_email_address(self):
        self.assertEqual(
            'auto-foo.bar',
            make_bugtracker_name('mailto:foo.bar@somewhere.com'))

    def test_sanitises_forbidden_characters(self):
        self.assertEqual(
            'auto-foobar',
            make_bugtracker_name('mailto:foo_bar@somewhere.com'))

    def test_github(self):
        self.assertEqual(
            'auto-github-user-repository',
            make_bugtracker_name('https://github.com/user/repository/issues'))
        self.assertEqual(
            'auto-github-user-repository',
            make_bugtracker_name('https://github.com/user/Repository/issues'))
        # Invalid on the GitHub side, but let's make sure these don't blow up.
        self.assertEqual(
            'auto-github-user',
            make_bugtracker_name('https://github.com/user/issues'))
        self.assertEqual(
            'auto-github-user-foo-bar',
            make_bugtracker_name('https://github.com/user/foo/bar/issues'))

    def test_gitlab(self):
        self.assertEqual(
            'auto-gitlab.com-user-repository',
            make_bugtracker_name('https://gitlab.com/user/repository/issues'))
        self.assertEqual(
            'auto-gitlab.com-user-repository',
            make_bugtracker_name('https://gitlab.com/user/Repository/issues'))
        self.assertEqual(
            'auto-salsa.debian.org-user-repository',
            make_bugtracker_name(
                'https://salsa.debian.org/user/repository/issues'))
        self.assertEqual(
            'auto-salsa.debian.org-user-repository',
            make_bugtracker_name(
                'https://salsa.debian.org/user/Repository/issues'))
        # Invalid on the GitLab side, but let's make sure these don't blow up.
        self.assertEqual(
            'auto-gitlab.com-user',
            make_bugtracker_name('https://gitlab.com/user/issues'))
        self.assertEqual(
            'auto-gitlab.com-user-foo-bar',
            make_bugtracker_name('https://gitlab.com/user/foo/bar/issues'))


class TestMakeBugtrackerTitle(TestCase):
    """Tests for make_bugtracker_title."""

    def test_url(self):
        self.assertEqual(
            'bugs.example.com/shrubbery',
            make_bugtracker_title('http://bugs.example.com/shrubbery'))

    def test_email_address(self):
        self.assertEqual(
            'Email to foo.bar@somewhere',
            make_bugtracker_title('mailto:foo.bar@somewhere.com'))


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    doctest_suite = DocTestSuite(
        'lp.bugs.model.bugtracker',
        optionflags=NORMALIZE_WHITESPACE | ELLIPSIS)
    suite.addTest(doctest_suite)
    return suite
