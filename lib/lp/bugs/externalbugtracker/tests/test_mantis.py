# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Mantis BugTracker."""

import responses
from six.moves.urllib_parse import urljoin
from testtools.matchers import (
    Equals,
    Is,
    )

from lp.bugs.externalbugtracker import UnparsableBugData
from lp.bugs.externalbugtracker.mantis import (
    Mantis,
    MantisBugBatchParser,
    )
from lp.services.log.logger import BufferLogger
from lp.testing import TestCase
from lp.testing.layers import ZopelessLayer


class TestMantisBugBatchParser(TestCase):
    """Test the MantisBugBatchParser class."""

    def setUp(self):
        super().setUp()
        self.logger = BufferLogger()

    def test_empty(self):
        data = []
        parser = MantisBugBatchParser(data, self.logger)
        exc = self.assertRaises(
            UnparsableBugData,
            parser.getBugs)
        self.assertThat(
            str(exc), Equals("Missing header line"))

    def test_missing_headers(self):
        data = ['some,headers']
        parser = MantisBugBatchParser(data, self.logger)
        exc = self.assertRaises(
            UnparsableBugData,
            parser.getBugs)
        self.assertThat(
            str(exc),
            Equals("CSV header ['some', 'headers'] missing fields:"
                   " ['id', 'status', 'resolution']"))

    def test_missing_some_headers(self):
        data = ['some,headers,status,resolution']
        parser = MantisBugBatchParser(data, self.logger)
        exc = self.assertRaises(
            UnparsableBugData,
            parser.getBugs)
        self.assertThat(
            str(exc),
            Equals("CSV header ['some', 'headers', 'status', 'resolution'] "
                   "missing fields: ['id']"))

    def test_no_bugs(self):
        data = ['other,fields,id,status,resolution']
        parser = MantisBugBatchParser(data, self.logger)
        self.assertThat(parser.getBugs(), Equals({}))

    def test_passing(self):
        data = [
            'ignored,id,resolution,status',
            'foo,42,not,complete',
            'boo,13,,confirmed',
            ]
        parser = MantisBugBatchParser(data, self.logger)
        bug_42 = dict(
            id=42, status='complete', resolution='not', ignored='foo')
        bug_13 = dict(
            id=13, status='confirmed', resolution='', ignored='boo')
        self.assertThat(parser.getBugs(), Equals({42: bug_42, 13: bug_13}))

    def test_incomplete_line(self):
        data = [
            'ignored,id,resolution,status',
            '42,not,complete',
            ]
        parser = MantisBugBatchParser(data, self.logger)
        self.assertThat(parser.getBugs(), Equals({}))
        log = self.logger.getLogBuffer()
        self.assertThat(
            log,
            Equals("WARNING Line ['42', 'not', 'complete'] incomplete.\n"))

    def test_non_integer_id(self):
        data = [
            'ignored,id,resolution,status',
            'foo,bar,not,complete',
            ]
        parser = MantisBugBatchParser(data, self.logger)
        self.assertThat(parser.getBugs(), Equals({}))
        log = self.logger.getLogBuffer()
        self.assertThat(
            log, Equals("WARNING Encountered invalid bug ID: 'bar'.\n"))


class TestMantisBugTracker(TestCase):
    """Tests for various methods of the Mantis bug tracker."""

    layer = ZopelessLayer

    @responses.activate
    def test_csv_data_on_post_404(self):
        # If the 'view_all_set.php' request raises a 404, then the csv_data
        # attribute is None.
        base_url = "http://example.com/"
        responses.add(
            "POST", urljoin(base_url, "view_all_set.php?f=3"), status=404)
        bugtracker = Mantis(base_url)
        self.assertThat(bugtracker.csv_data, Is(None))
