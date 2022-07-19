# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Common helpers for codehosting tests."""

__all__ = [
    "AvatarTestCase",
    "create_branch_with_one_revision",
    "force_stacked_on_url",
    "LoomTestMixin",
    "TestResultWrapper",
]

import os

from breezy.controldir import ControlDir
from breezy.errors import FileExists
from breezy.plugins.loom import branch as loom_branch
from breezy.tests import TestNotApplicable, TestSkipped
from testtools.twistedsupport import AsynchronousDeferredRunTest

from lp.testing import TestCase


class AvatarTestCase(TestCase):
    """Base class for tests that need a LaunchpadAvatar with some basic sample
    data.
    """

    run_tests_with = AsynchronousDeferredRunTest

    def setUp(self):
        super().setUp()
        # A basic user dict, 'alice' is a member of no teams (aside from the
        # user themself).
        self.aliceUserDict = {
            "id": 1,
            "name": "alice",
            "teams": [{"id": 1, "name": "alice"}],
            "initialBranches": [(1, [])],
        }


class LoomTestMixin:
    """Mixin to provide Bazaar test classes with limited loom support."""

    def loomify(self, branch):
        tree = branch.create_checkout("checkout")
        tree.lock_write()
        try:
            tree.branch.nick = "bottom-thread"
            loom_branch.loomify(tree.branch)
        finally:
            tree.unlock()
        loom_tree = tree.controldir.open_workingtree()
        loom_tree.lock_write()
        loom_tree.branch.new_thread("bottom-thread")
        loom_tree.commit("this is a commit", rev_id=b"commit-1")
        loom_tree.unlock()
        loom_tree.branch.record_loom("sample loom")
        self.get_transport().delete_tree("checkout")
        return loom_tree

    def makeLoomBranchAndTree(self, tree_directory):
        """Make a looms-enabled branch and working tree."""
        tree = self.make_branch_and_tree(tree_directory)
        tree.lock_write()
        try:
            tree.branch.nick = "bottom-thread"
            loom_branch.loomify(tree.branch)
        finally:
            tree.unlock()
        loom_tree = tree.controldir.open_workingtree()
        loom_tree.lock_write()
        loom_tree.branch.new_thread("bottom-thread")
        loom_tree.commit("this is a commit", rev_id=b"commit-1")
        loom_tree.unlock()
        loom_tree.branch.record_loom("sample loom")
        return loom_tree


def create_branch_with_one_revision(branch_dir, format=None):
    """Create a dummy Bazaar branch at the given directory."""
    if not os.path.exists(branch_dir):
        os.makedirs(branch_dir)
    try:
        tree = ControlDir.create_standalone_workingtree(branch_dir, format)
    except FileExists:
        return
    f = open(os.path.join(branch_dir, "hello"), "w")
    f.write("foo")
    f.close()
    tree.commit("message")
    return tree


def force_stacked_on_url(branch, url):
    """Set the stacked_on url of a branch without standard error-checking.

    Bazaar 1.17 and up make it harder to create branches with invalid
    stacking.  It's still worth testing that we don't blow up in the face of
    them, so this function lets us create them anyway.
    """
    branch.get_config().set_user_option("stacked_on_location", url)


class TestResultWrapper:
    """A wrapper for `TestResult` that knows about breezy's `TestSkipped`."""

    def __init__(self, result):
        self.result = result

    def addError(self, test_case, exc_info):
        if isinstance(exc_info[1], (TestSkipped, TestNotApplicable)):
            # If Bazaar says the test was skipped, or that it wasn't
            # applicable to this environment, then treat that like a success.
            # After all, it's not exactly an error, is it?
            self.result.addSuccess(test_case)
        else:
            self.result.addError(test_case, exc_info)

    def addFailure(self, test_case, exc_info):
        self.result.addFailure(test_case, exc_info)

    def addSuccess(self, test_case):
        self.result.addSuccess(test_case)

    def startTest(self, test_case):
        self.result.startTest(test_case)

    def stopTest(self, test_case):
        self.result.stopTest(test_case)
