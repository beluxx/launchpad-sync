# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the script run on the remote server."""

__metaclass__ = type

import gzip
import os
from StringIO import StringIO
import sys
import tempfile
import unittest

from testtools import TestCase

from devscripts.ec2test.remote import (
    FlagFallStream,
    gzip_file,
    remove_pidfile,
    SummaryResult,
    write_pidfile,
    )


class TestFlagFallStream(TestCase):
    """Tests for `FlagFallStream`."""

    def test_doesnt_write_before_flag(self):
        # A FlagFallStream does not forward any writes before it sees the
        # 'flag'.
        stream = StringIO()
        flag = self.getUniqueString('flag')
        flagfall = FlagFallStream(stream, flag)
        flagfall.write('foo')
        flagfall.flush()
        self.assertEqual('', stream.getvalue())

    def test_writes_after_flag(self):
        # After a FlagFallStream sees the flag, it forwards all writes.
        stream = StringIO()
        flag = self.getUniqueString('flag')
        flagfall = FlagFallStream(stream, flag)
        flagfall.write('foo')
        flagfall.write(flag)
        flagfall.write('bar')
        self.assertEqual('%sbar' % (flag,), stream.getvalue())

    def test_mixed_write(self):
        # If a single call to write has pre-flagfall and post-flagfall data in
        # it, then only the post-flagfall data is forwarded to the stream.
        stream = StringIO()
        flag = self.getUniqueString('flag')
        flagfall = FlagFallStream(stream, flag)
        flagfall.write('foo%sbar' % (flag,))
        self.assertEqual('%sbar' % (flag,), stream.getvalue())


class TestSummaryResult(TestCase):
    """Tests for `SummaryResult`."""

    def makeException(self, factory=None, *args, **kwargs):
        if factory is None:
            factory = RuntimeError
        try:
            raise factory(*args, **kwargs)
        except:
            return sys.exc_info()

    def test_formatError(self):
        # SummaryResult._formatError() combines the name of the test, the kind
        # of error and the details of the error in a nicely-formatted way.
        result = SummaryResult(None)
        output = result._formatError('FOO', 'test', 'error')
        expected = '%s\nFOO: test\n%s\nerror\n' % (
            result.double_line, result.single_line)
        self.assertEqual(expected, output)

    def test_addError(self):
        # SummaryResult.addError doesn't write immediately.
        stream = StringIO()
        test = self
        error = self.makeException()
        result = SummaryResult(stream)
        expected = result._formatError(
            'ERROR', test, result._exc_info_to_string(error, test))
        result.addError(test, error)
        self.assertEqual(expected, stream.getvalue())

    def test_addFailure_does_not_write_immediately(self):
        # SummaryResult.addFailure doesn't write immediately.
        stream = StringIO()
        test = self
        error = self.makeException()
        result = SummaryResult(stream)
        expected = result._formatError(
            'FAILURE', test, result._exc_info_to_string(error, test))
        result.addFailure(test, error)
        self.assertEqual(expected, stream.getvalue())


class TestPidfileHelpers(TestCase):
    """Tests for `write_pidfile` and `remove_pidfile`."""

    def test_write_pidfile(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.unlink, path)
        os.close(fd)
        write_pidfile(path)
        self.assertEqual(os.getpid(), int(open(path, 'r').read()))

    def test_remove_pidfile(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        write_pidfile(path)
        remove_pidfile(path)
        self.assertEqual(False, os.path.exists(path))

    def test_remove_nonexistent_pidfile(self):
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, 'doesntexist')
        remove_pidfile(path)
        self.assertEqual(False, os.path.exists(path))


class TestGzipFile(TestCase):
    """Tests for `gzip_file`."""

    def test_gzip_file(self):
        fd, path = tempfile.mkstemp()
        contents = 'foobarbaz\n'
        os.write(fd, contents)
        os.close(fd)
        gz_file = gzip_file(path)
        self.assertEqual(contents, gzip.open(gz_file, 'r').read())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
