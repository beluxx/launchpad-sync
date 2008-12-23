# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the logging system of the sshserver."""

__metaclass__ = type

import codecs
import logging
from logging.handlers import TimedRotatingFileHandler
from StringIO import StringIO
import unittest
import sys

from bzrlib.tests import TestCase as BzrTestCase

from canonical.codehosting.sshserver.service import (
    get_codehosting_logger, set_up_logging)
from canonical.config import config
from canonical.launchpad.testing import TestCase
from canonical.testing import reset_logging


class TestLoggingBazaarInteraction(BzrTestCase):

    def setUp(self):
        BzrTestCase.setUp(self)

        # Trap stderr.
        self._real_stderr = sys.stderr
        sys.stderr = codecs.getwriter('utf8')(StringIO())

        # We want to use Bazaar's default logging -- not its test logging --
        # so here we disable the testing logging system (which restores
        # default logging).
        self._finishLogFile()

        # We don't use BaseLayer because we want to keep the amount of
        # pre-configured logging systems to an absolute minimum, in order to
        # make it easier to test this particular logging system.
        self.addCleanup(reset_logging)

    def tearDown(self):
        sys.stderr = self._real_stderr
        BzrTestCase.tearDown(self)

    def test_leaves_bzr_handlers_unchanged(self):
        # Bazaar's log handling is untouched by set_up_logging.
        root_handlers = logging.getLogger('').handlers
        bzr_handlers = logging.getLogger('bzr').handlers

        set_up_logging()

        self.assertEqual(root_handlers, logging.getLogger('').handlers)
        self.assertEqual(bzr_handlers, logging.getLogger('bzr').handlers)

    def test_codehosting_log_doesnt_go_to_stderr(self):
        # Once set_up_logging is called, any messages logged to the
        # codehosting logger should *not* be logged to stderr. If they are,
        # they will appear on the user's terminal.
        set_up_logging()

        # Make sure that a logged message does not go to stderr.
        get_codehosting_logger().info('Hello hello')
        self.assertEqual(sys.stderr.getvalue(), '')


class TestLoggingSetup(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        # We don't use BaseLayer because we want to keep the amount of
        # pre-configured logging systems to an absolute minimum, in order to
        # make it easier to test this particular logging system.
        self.addCleanup(reset_logging)

    def test_returns_codehosting_logger(self):
        # get_codehosting_logger returns the 'codehosting' logger.
        self.assertIs(
            logging.getLogger('codehosting'), get_codehosting_logger())

    def test_set_up_returns_codehosting_logger(self):
        # set_up_logging returns the codehosting logger.
        self.assertIs(get_codehosting_logger(), set_up_logging())

    def test_handlers(self):
        # set_up_logging installs a rotating log handler that logs output to
        # config.codehosting.access_log.
        set_up_logging()
        [handler] = get_codehosting_logger().handlers
        # XXX: JonathanLange 2008-12-23: Is TimedRotatingFileHandler really
        # what would be best for IS?
        self.assertIsInstance(handler, TimedRotatingFileHandler)
        self.assertEqual(config.codehosting.access_log, handler.baseFilename)
        self.assertEqual("MIDNIGHT", handler.when)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
