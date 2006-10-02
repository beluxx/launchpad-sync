# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Tests for BugWatchSet."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.launchpad.interfaces import (
    IBugTaskSet, IBugTrackerSet, IBugWatchSet, IPersonSet, NoBugTrackerFound)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.lp.dbschema import BugTrackerType


class ExtractBugTrackerAndBugTestBase(LaunchpadFunctionalTestCase):
    """Test base for testing BugWatchSet.extractBugTrackerAndBug."""

    # A URL to an unregistered bug tracker.
    base_url = None

    # The bug tracker type to be tested.
    bugtracker_type = None

    # A sample URL to a bug in the bug tracker.
    bug_url = None

    # The bug id in the sample bug_url.
    bug_id = None

    def setUp(self):
        LaunchpadFunctionalTestCase.setUp(self)
        login(ANONYMOUS)
        self.bugwatch_set = getUtility(IBugWatchSet)
        self.bugtracker_set = getUtility(IBugTrackerSet)
        self.sample_person = getUtility(IPersonSet).getByEmail(
            'test@canonical.com')

    def test_unknown_baseurl(self):
        # extractBugTrackerAndBug returns None if it can't even decide
        # what kind of bug tracker the bug URL points to.
        remote_data = self.bugwatch_set.extractBugTrackerAndBug(
            'http://no.such/base/url/42')
        self.assertEqual(remote_data, None)

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
        self.failUnless(
            self.bugtracker_set.queryByBaseURL(self.base_url) is None)
        try:
            bugtracker, bug = self.bugwatch_set.extractBugTrackerAndBug(
                self.bug_url)
        except NoBugTrackerFound, error:
            # The raised exception should contain enough information so
            # that we can register a new bug tracker.
            self.assertEqual(error.base_url, self.base_url)
            self.assertEqual(error.remote_bug, self.bug_id)
            self.assertEqual(error.bugtracker_type, self.bugtracker_type)
        else:
            self.fail(
                "NoBugTrackerFound wasn't raised by extractBugTrackerAndBug")


class BugzillaExtractBugTrackerAndBugTest(ExtractBugTrackerAndBugTestBase):
    """Make sure BugWatchSet.extractBugTrackerAndBug works with Bugzilla URLs."""

    bugtracker_type = BugTrackerType.BUGZILLA
    bug_url = 'http://some.host/bugs/show_bug.cgi?id=3224'
    base_url = 'http://some.host/bugs/'
    bug_id = '3224'


class RoundUpExtractBugTrackerAndBugTest(ExtractBugTrackerAndBugTestBase):
    """Make sure BugWatchSet.extractBugTrackerAndBug works with RoundUp URLs."""

    bugtracker_type = BugTrackerType.ROUNDUP
    bug_url = 'http://some.host/some/path/issue377'
    base_url = 'http://some.host/some/path/'
    bug_id = '377'


class TracExtractBugTrackerAndBugTest(ExtractBugTrackerAndBugTestBase):
    """Make sure BugWatchSet.extractBugTrackerAndBug works with Trac URLs."""

    bugtracker_type = BugTrackerType.TRAC
    bug_url = 'http://some.host/some/path/ticket/42'
    base_url = 'http://some.host/some/path/'
    bug_id = '42'


class DebbugsExtractBugTrackerAndBugTest(ExtractBugTrackerAndBugTestBase):
    """Make sure BugWatchSet.extractBugTrackerAndBug works with Trac URLs."""

    bugtracker_type = BugTrackerType.DEBBUGS
    bug_url = 'http://some.host/some/path/cgi-bin/bugreport.cgi?bug=42'
    base_url = 'http://some.host/some/path/'
    bug_id = '42'


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BugzillaExtractBugTrackerAndBugTest))
    suite.addTest(unittest.makeSuite(RoundUpExtractBugTrackerAndBugTest))
    suite.addTest(unittest.makeSuite(TracExtractBugTrackerAndBugTest))
    suite.addTest(unittest.makeSuite(DebbugsExtractBugTrackerAndBugTest))
    return suite


if __name__ == '__main__':
    unittest.main()

