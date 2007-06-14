# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for the Launchpad code hosting Bazaar transport."""

__metaclass__ = type

import unittest

from bzrlib import errors
from bzrlib.transport import get_transport, _get_protocol_handlers
from bzrlib.transport.memory import MemoryTransport
from bzrlib.tests import TestCaseInTempDir, TestCaseWithMemoryTransport

from canonical.authserver.interfaces import READ_ONLY, WRITABLE
from canonical.codehosting.tests.helpers import FakeLaunchpad
from canonical.codehosting.transport import LaunchpadServer
from canonical.testing import BzrlibLayer


class TestLaunchpadServer(TestCaseInTempDir):

    layer = BzrlibLayer

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = MemoryTransport()
        self.server = LaunchpadServer(
            self.authserver, self.user_id, self.backing_transport)

    def test_construct(self):
        self.assertEqual(self.backing_transport, self.server.backing_transport)
        self.assertEqual(self.user_id, self.server.user_id)
        self.assertEqual('testuser', self.server.user_name)
        self.assertEqual(self.authserver, self.server.authserver)

    def test_base_path_translation(self):
        # Branches are stored on the filesystem by branch ID. This allows users
        # to rename and re-assign branches without causing unnecessary disk
        # churn. The ID is converted to four-byte hexadecimal and split into
        # four path segments, to make sure that the directory tree doesn't get
        # too wide and cause ext3 to have conniptions.
        #
        # However, branches are _accessed_ using their
        # ~person/product/branch-name. The server knows how to map this unique
        # name to the branch's path on the filesystem.

        # We can map a branch owned by the user to its path.
        self.assertEqual(
            ('00/00/00/01/', WRITABLE),
            self.server.translate_virtual_path('/~testuser/firefox/baz'))

        # The '+junk' product doesn't actually exist. It is used for branches
        # which don't have a product assigned to them.
        self.assertEqual(
            ('00/00/00/03/', WRITABLE),
            self.server.translate_virtual_path('/~testuser/+junk/random'))
        # We can map a branch owned by a team that the user is in to its path.
        self.assertEqual(
            ('00/00/00/04/', WRITABLE),
            self.server.translate_virtual_path('/~testteam/firefox/qux'))

        self.assertEqual(
            '00/00/00/03/',
            self.server.translate_virtual_path('/~testuser/+junk/random'))

    def test_extend_path_translation(self):
        # More than just the branch name needs to be translated: transports
        # will ask for files beneath the branch. The server translates the
        # unique name of the branch (i.e. the ~user/product/branch-name part)
        # to the four-byte hexadecimal split ID described in
        # test_extend_path_translation and appends the remainder of the path.
        self.assertEqual(
            ('00/00/00/01/.bzr', WRITABLE),
            self.server.translate_virtual_path('/~testuser/firefox/baz/.bzr'))

    def test_setUp(self):
        # Setting up the server registers its schema with the protocol
        # handlers.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.assertTrue(self.server.scheme in _get_protocol_handlers().keys())

    def test_tearDown(self):
        # Setting up then tearing down the server removes its schema from the
        # protocol handlers.
        self.server.setUp()
        self.server.tearDown()
        self.assertFalse(self.server.scheme in _get_protocol_handlers().keys())

    def test_get_url(self):
        # The URL of the server is 'lp-<number>:///', where <number> is the
        # id() of the server object. Including the id allows for multiple
        # Launchpad servers to be running within a single process.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.assertEqual('lp-%d:///' % id(self.server), self.server.get_url())


class TestLaunchpadTransport(TestCaseWithMemoryTransport):

    layer = BzrlibLayer

    def setUp(self):
        TestCaseWithMemoryTransport.setUp(self)
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = self.get_transport()
        self.server = LaunchpadServer(
            self.authserver, self.user_id, self.backing_transport)
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.backing_transport.mkdir_multi(
            ['00', '00/00', '00/00/00', '00/00/00/01'])
        self.backing_transport.put_bytes(
            '00/00/00/01/hello.txt', 'Hello World!')

    def test_get_transport(self):
        # When the server is set up, getting a transport for the server URL
        # returns a LaunchpadTransport pointing at that URL. That is, the
        # transport is registered once the server is set up.
        transport = get_transport(self.server.get_url())
        self.assertEqual(self.server.get_url(), transport.base)

    def test_get_mapped_file(self):
        # Getting a file from a public branch URL gets the file as stored on
        # the base transport.
        transport = get_transport(self.server.get_url())
        self.assertEqual(
            'Hello World!',
            transport.get_bytes('~testuser/firefox/baz/hello.txt'))

    def test_put_mapped_file(self):
        # Putting a file from a public branch URL stores the file in the mapped
        # URL on the base transport.
        transport = get_transport(self.server.get_url())
        transport.put_bytes('~testuser/firefox/baz/goodbye.txt', "Goodbye")
        self.assertEqual(
            "Goodbye",
            self.backing_transport.get_bytes('00/00/00/01/goodbye.txt'))

    def test_cloning_updates_base(self):
        # A transport can be constructed using a path relative to another
        # transport by using 'clone'. When this happens, it's necessary for the
        # newly constructed transport to preserve the non-relative path
        # information from the transport being cloned. It's necessary because
        # the transport needs to have the '~user/product/branch-name' in order
        # to translate paths.
        transport = get_transport(self.server.get_url())
        self.assertEqual(self.server.get_url(), transport.base)
        transport = transport.clone('~testuser')
        self.assertEqual(self.server.get_url() + '~testuser', transport.base)

    def test_abspath_without_schema(self):
        # _abspath returns the absolute path for a given relative path, but
        # without the schema part of the URL that is included by abspath.
        transport = get_transport(self.server.get_url())
        self.assertEqual(
            '/~testuser/firefox/baz',
            transport._abspath('~testuser/firefox/baz'))
        transport = transport.clone('~testuser')
        self.assertEqual(
            '/~testuser/firefox/baz', transport._abspath('firefox/baz'))

    def test_cloning_preserves_path_mapping(self):
        # The public branch URL -> filesystem mapping uses the base URL to do
        # its mapping, thus ensuring that clones map correctly.
        transport = get_transport(self.server.get_url())
        transport = transport.clone('~testuser')
        self.assertEqual(
            'Hello World!', transport.get_bytes('firefox/baz/hello.txt'))

    def test_abspath(self):
        # abspath for a relative path is the same as the base URL for a clone
        # for that relative path.
        transport = get_transport(self.server.get_url())
        self.assertEqual(
            transport.clone('~testuser').base, transport.abspath('~testuser'))

    def test_incomplete_path_not_found(self):
        # For a branch URL to be complete, it needs to have a person, product
        # and branch. Trying to perform operations on an incomplete URL raises
        # an error. Which kind of error is not particularly important.
        transport = get_transport(self.server.get_url())
        self.assertRaises(
            errors.NoSuchFile, transport.get, '~testuser')

    def test_complete_non_existent_path_not_found(self):
        # Bazaar looks for files inside a branch directory before it looks for
        # the branch itself. If the branch doesn't exist, any files it asks for
        # are not found. i.e. we raise NoSuchFile
        transport = get_transport(self.server.get_url())
        self.assertRaises(
            errors.NoSuchFile,
            transport.get, '~testuser/firefox/new-branch/.bzr/branch-format')

    def test_rename(self):
        # We can use the transport to rename files where both the source and
        # target are virtual paths.
        transport = get_transport(self.server.get_url())
        transport.rename(
            '~testuser/firefox/baz/hello.txt',
            '~testuser/firefox/baz/goodbye.txt')
        self.assertEqual(
            ['goodbye.txt'], transport.list_dir('~testuser/firefox/baz'))
        self.assertEqual(['goodbye.txt'],
                         self.backing_transport.list_dir('00/00/00/01'))

    def test_iter_files_recursive(self):
        # iter_files_recursive doesn't take a relative path but still needs to
        # do a path-based operation on the backing transport, so the
        # implementation can't just be a shim to the backing transport.
        transport = get_transport(self.server.get_url())
        files = list(
            transport.clone('~testuser/firefox/baz').iter_files_recursive())
        backing_transport = self.backing_transport.clone('00/00/00/01')
        self.assertEqual(list(backing_transport.iter_files_recursive()), files)

    def test_make_two_directories(self):
        # Bazaar doesn't have a makedirs() facility for transports, so we need
        # to make sure that we can make a directory on the backing transport if
        # its parents exist and if they don't exist.
        transport = get_transport(self.server.get_url())
        transport.mkdir('~testuser/thunderbird/banana')
        transport.mkdir('~testuser/thunderbird/orange')
        self.assertTrue(transport.has('~testuser/thunderbird/banana'))
        self.assertTrue(transport.has('~testuser/thunderbird/orange'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
