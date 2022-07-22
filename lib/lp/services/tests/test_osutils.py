# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.services.osutils."""

import errno
import os
import tempfile

from fixtures import MockPatch
from testtools.matchers import FileContains

from lp.services.osutils import (
    ensure_directory_exists,
    open_for_writing,
    process_exists,
    remove_tree,
    write_file,
)
from lp.testing import TestCase


class TestRemoveTree(TestCase):
    """Tests for remove_tree."""

    def test_removes_directory(self):
        # remove_tree deletes the directory.
        directory = tempfile.mkdtemp()
        remove_tree(directory)
        self.assertFalse(os.path.isdir(directory))
        self.assertFalse(os.path.exists(directory))

    def test_on_nonexistent_path_passes_silently(self):
        # remove_tree simply does nothing when called on a non-existent path.
        directory = tempfile.mkdtemp()
        nonexistent_tree = os.path.join(directory, "foo")
        remove_tree(nonexistent_tree)
        self.assertFalse(os.path.isdir(nonexistent_tree))
        self.assertFalse(os.path.exists(nonexistent_tree))

    def test_raises_on_file(self):
        # If remove_tree is pased a file, it raises an OSError.
        directory = tempfile.mkdtemp()
        filename = os.path.join(directory, "foo")
        fd = open(filename, "w")
        fd.write("data")
        fd.close()
        self.assertRaises(OSError, remove_tree, filename)


class TestEnsureDirectoryExists(TestCase):
    """Tests for 'ensure_directory_exists'."""

    def test_directory_exists(self):
        directory = self.makeTemporaryDirectory()
        self.assertFalse(ensure_directory_exists(directory))

    def test_directory_doesnt_exist(self):
        directory = os.path.join(self.makeTemporaryDirectory(), "foo/bar/baz")
        self.assertTrue(ensure_directory_exists(directory))
        self.assertTrue(os.path.isdir(directory))


class TestOpenForWriting(TestCase):
    """Tests for 'open_for_writing'."""

    def test_opens_for_writing(self):
        # open_for_writing opens a file for, umm, writing.
        directory = self.makeTemporaryDirectory()
        filename = os.path.join(directory, "foo")
        with open_for_writing(filename, "w") as fp:
            fp.write("Hello world!\n")
        with open(filename) as fp:
            self.assertEqual("Hello world!\n", fp.read())

    def test_opens_for_writing_append(self):
        # open_for_writing can also open to append.
        directory = self.makeTemporaryDirectory()
        filename = os.path.join(directory, "foo")
        with open_for_writing(filename, "w") as fp:
            fp.write("Hello world!\n")
        with open_for_writing(filename, "a") as fp:
            fp.write("Next line\n")
        with open(filename) as fp:
            self.assertEqual("Hello world!\nNext line\n", fp.read())

    def test_even_if_directory_doesnt_exist(self):
        # open_for_writing will open a file for writing even if the directory
        # doesn't exist.
        directory = self.makeTemporaryDirectory()
        filename = os.path.join(directory, "foo", "bar", "baz", "filename")
        with open_for_writing(filename, "w") as fp:
            fp.write("Hello world!\n")
        with open(filename) as fp:
            self.assertEqual("Hello world!\n", fp.read())

    def test_error(self):
        # open_for_writing passes through errors other than the directory
        # not existing.
        directory = self.makeTemporaryDirectory()
        os.chmod(directory, 0)
        filename = os.path.join(directory, "foo")
        self.assertRaises(IOError, open_for_writing, filename, "w")


class TestWriteFile(TestCase):
    def test_write_file(self):
        directory = self.makeTemporaryDirectory()
        filename = os.path.join(directory, "filename")
        content = self.factory.getUniqueUnicode()
        write_file(filename, content.encode("UTF-8"))
        self.assertThat(filename, FileContains(content))


class TestProcessExists(TestCase):
    def test_with_process_running(self):
        pid = os.getpid()
        self.assertTrue(process_exists(pid))

    def test_with_process_not_running(self):
        exception = OSError()
        exception.errno = errno.ESRCH
        self.useFixture(MockPatch("os.kill", side_effect=exception))
        self.assertFalse(process_exists(123))

    def test_with_unknown_error(self):
        exception = OSError()
        exception.errno = errno.ENOMEM
        self.useFixture(MockPatch("os.kill", side_effect=exception))
        self.assertRaises(OSError, process_exists, 123)
