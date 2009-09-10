# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import shutil
from StringIO import StringIO
import tempfile
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.tests import TestCase
from bzrlib.transport import get_transport

from devscripts.sourcecode import (
    find_branches, interpret_config, parse_config_file, plan_update)


class TestParseConfigFile(unittest.TestCase):
    """Tests for the config file parser."""

    def makeFile(self, contents):
        return StringIO(contents)

    def test_empty(self):
        # Parsing an empty config file returns an empty sequence.
        empty_file = self.makeFile("")
        self.assertEqual([], list(parse_config_file(empty_file)))

    def test_single_value(self):
        # Parsing a file containing a single key=value pair returns a sequence
        # containing the (key, value) as a list.
        config_file = self.makeFile("key=value")
        self.assertEqual(
            [['key', 'value']], list(parse_config_file(config_file)))

    def test_comment_ignored(self):
        # If a line begins with a '#', then its a comment.
        comment_only = self.makeFile('# foo')
        self.assertEqual([], list(parse_config_file(comment_only)))

    def test_optional_value(self):
        # Lines in the config file can have a third optional entry.
        config_file = self.makeFile('key=value=optional')
        self.assertEqual(
            [['key', 'value', 'optional']],
            list(parse_config_file(config_file)))

    def test_whitespace_stripped(self):
        # Any whitespace around any of the tokens in the config file are
        # stripped out.
        config_file = self.makeFile('  key = value =  optional   ')
        self.assertEqual(
            [['key', 'value', 'optional']],
            list(parse_config_file(config_file)))


class TestInterpretConfiguration(unittest.TestCase):
    """Tests for the configuration interpreter."""

    def test_empty(self):
        # An empty configuration stream means no configuration.
        config = interpret_config([])
        self.assertEqual({}, config)

    def test_key_value(self):
        # A (key, value) pair without a third optional value is returned in
        # the configuration as a dictionary entry under 'key' with '(value,
        # False)' as its value.
        config = interpret_config([['key', 'value']])
        self.assertEqual({'key': ('value', False)}, config)

    def test_key_value_optional(self):
        # A (key, value, optional) entry is returned in the configuration as a
        # dictionary entry under 'key' with '(value, True)' as its value.
        config = interpret_config([['key', 'value', 'optional']])
        self.assertEqual({'key': ('value', True)}, config)


class TestPlanUpdate(unittest.TestCase):
    """Tests for how to plan the update."""

    def test_trivial(self):
        # In the trivial case, there are no existing branches and no
        # configured branches, so there are no branches to add, none to
        # update, and none to remove.
        new, existing, removed = plan_update([], {})
        self.assertEqual({}, new)
        self.assertEqual({}, existing)
        self.assertEqual(set(), removed)

    def test_all_new(self):
        # If there are no existing branches, then the all of the configured
        # branches are new, none are existing and none have been removed.
        new, existing, removed = plan_update([], {'a': ('b', False)})
        self.assertEqual({'a': ('b', False)}, new)
        self.assertEqual({}, existing)
        self.assertEqual(set(), removed)

    def test_all_old(self):
        # If there configuration is now empty, but there are existing
        # branches, then that means all the branches have been removed from
        # the configuration, none are new and none are updated.
        new, existing, removed = plan_update(['a', 'b', 'c'], {})
        self.assertEqual({}, new)
        self.assertEqual({}, existing)
        self.assertEqual(set(['a', 'b', 'c']), removed)

    def test_all_same(self):
        # If the set of existing branches is the same as the set of
        # non-existing branches, then they all need to be updated.
        config = {'a': ('b', False), 'c': ('d', True)}
        new, existing, removed = plan_update(config.keys(), config)
        self.assertEqual({}, new)
        self.assertEqual(config, existing)
        self.assertEqual(set(), removed)


class TestFindBranches(TestCase):
    """Tests the way that we find branches."""

    def makeBranch(self, path):
        transport = get_transport(path)
        transport.ensure_base()
        BzrDir.create_branch_convenience(
            transport.base, possible_transports=[transport])

    def makeDirectory(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        return directory

    def test_empty_directory_has_no_branches(self):
        # An empty directory has no branches.
        empty = self.makeDirectory()
        self.assertEqual([], list(find_branches(empty)))

    def test_directory_with_branches(self):
        # find_branches finds branches in the directory.
        directory = self.makeDirectory()
        self.makeBranch('%s/a' % directory)
        self.assertEqual(['a'], list(find_branches(directory)))

    def test_ignores_files(self):
        # find_branches ignores any files in the directory.
        directory = self.makeDirectory()
        some_file = open('%s/a' % directory, 'w')
        some_file.write('hello\n')
        some_file.close()
        self.assertEqual([], list(find_branches(directory)))


# XXX: Actually remove branches

# XXX: Update existing branches

# XXX: Branch new branches

# XXX: Should we parallelize? If so, how? Can we rely on Twisted being
# present.

# XXX: Find the sourcecode directory.

# XXX: Handle symlinks. Lots of people manage sourcecode via symlinks

# XXX: Actual storage location can be inferred from symlinks, since presumably
# they link into the actual store. However, some of the symlinks might differ
# (because of developers fiddling with things). We can take a survey of all of
# them, and choose the most popular.

# XXX: How to report errors?

# XXX: rocketfuel-get does stacking onto launchpad for some branches. Should
# we actually do this? It seems a bit silly if in a shared repo. (Although
# does the branch mask the shared repo bit?)

# XXX: Can we get rocketfuel-setup to use this?

# XXX: (unrelated). Finding the highest common ancestor is easy, but what if
# you have two (N?) trees? Is there a way to algorithmically find the two (N?)
# interesting HCAs? Can the question even be framed well?


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
