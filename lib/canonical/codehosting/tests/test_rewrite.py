# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the dynamic RewriteMap used to serve branches over HTTP."""

__metaclass__ = type

import os
import signal
import subprocess
import unittest

from canonical.codehosting.branchfs import branch_id_to_path
from canonical.codehosting.inmemory import InMemoryFrontend, XMLRPCWrapper
from canonical.codehosting.rewrite import BranchRewriter
from canonical.config import config
from canonical.launchpad.testing import TestCase, TestCaseWithFactory
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.testing.layers import ZopelessAppServerLayer


class TestBranchRewriter(TestCase):

    def setUp(self):
        frontend = InMemoryFrontend()
        self._branchfs = frontend.getFilesystemEndpoint()
        self.factory = frontend.getLaunchpadObjectFactory()

    def makeRewriter(self):
        return BranchRewriter(
            QuietFakeLogger(), XMLRPCWrapper(self._branchfs))

    def test_translateLine_found_dot_bzr(self):
        # Requests for /$branch_name/.bzr/... are redirected to where the
        # branches are served from by ID.
        rewriter = self.makeRewriter()
        branch = self.factory.makeBranch()
        line = rewriter.rewriteLine("/%s/.bzr/README" % branch.unique_name)
        self.assertEqual(
            'http://bazaar-internal.launchpad.dev/%s/.bzr/README'
            % branch_id_to_path(branch.id),
            line)

    def test_translateLine_found_not_dot_bzr(self):
        # Requests for /$branch_name/... that are not to .bzr directories are
        # redirected to codebrowse.
        rewriter = self.makeRewriter()
        branch = self.factory.makeBranch()
        output = rewriter.rewriteLine("/%s/changes" % branch.unique_name)
        self.assertEqual(
            'http://localhost:8080/%s/changes' % branch.unique_name,
            output)

    def test_translateLine_not_found(self):
        # If the branch behind a request is not foudn, rewriteLine returns
        # "NULL", the way of saying "I don't know how to rewrite this" to
        # Apache.
        rewriter = self.makeRewriter()
        output = rewriter.rewriteLine("/~nouser/noproduct/nobranch/changes")
        self.assertEqual("NULL", output)


class TestBranchRewriterScript(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_script(self):
        branch = self.factory.makeBranch()
        input = "/%s/.bzr/README\n" % branch.unique_name
        expected = (
            "http://bazaar-internal.launchpad.dev/%s/.bzr/README\n"
            % branch_id_to_path(branch.id))
        self.layer.txn.commit()
        script_file = os.path.join(
            config.root, 'scripts', 'branch-rewrite.py')
        proc = subprocess.Popen(
            [script_file], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0)
        proc.stdin.write(input)
        output = proc.stdout.readline()
        os.kill(proc.pid, signal.SIGINT)
        err = proc.stderr.read()
        self.assertEqual(expected, output)
        # XXX MichaelHudson, bug=309240: The script currently logs to stderr,
        # which it shouldn't do.
        #self.assertEqual('', err)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

