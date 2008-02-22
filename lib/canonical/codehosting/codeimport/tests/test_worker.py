# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the code import worker."""

__metaclass__ = type

import os
import shutil
import tempfile
import time
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.errors import NoSuchFile
from bzrlib.tests import TestCaseWithTransport
from bzrlib.transport import get_transport
from bzrlib.urlutils import join as urljoin

from canonical.cachedproperty import cachedproperty
from canonical.codehosting.codeimport.worker import (
    BazaarBranchStore, ForeignTreeStore, ImportWorker,
    get_default_bazaar_branch_store, get_default_foreign_tree_store)
from canonical.codehosting.codeimport.tests.test_foreigntree import (
    CVSServer, SubversionServer)
from canonical.codehosting.tests.helpers import (
    create_branch_with_one_revision)
from canonical.config import config
from canonical.launchpad.interfaces import BranchType, BranchTypeError
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import LaunchpadScriptLayer

import pysvn


class WorkerTest(TestCaseWithTransport):
    """Base test case for things that test the code import worker.

    Provides Bazaar testing features, access to Launchpad objects and
    factories for some code import objects.
    """

    layer = LaunchpadScriptLayer

    def assertDirectoryTreesEqual(self, directory1, directory2):
        """Assert that `directory1` has the same structure as `directory2`.

        That is, assert that all of the files and directories beneath
        `directory1` are laid out in the same way as `directory2`.
        """
        def list_files(directory):
            for path, ignored, ignored in os.walk(directory):
                yield path[len(directory):]
        self.assertEqual(
            list(list_files(directory1)), list(list_files(directory2)))

    @cachedproperty
    def factory(self):
        return LaunchpadObjectFactory()

    def makeTemporaryDirectory(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(directory))
        return directory


class TestBazaarBranchStore(WorkerTest):
    """Tests for `BazaarBranchStore`."""

    def setUp(self):
        super(TestBazaarBranchStore, self).setUp()
        code_import = self.factory.makeCodeImport()
        self.temp_dir = self.makeTemporaryDirectory()
        self.branch = code_import.branch

    def makeBranchStore(self):
        return BazaarBranchStore(self.get_transport())

    def test_defaultStore(self):
        # The default store is at config.codeimport.bazaar_branch_store.
        store = get_default_bazaar_branch_store()
        self.assertEqual(
            store.transport.base.rstrip('/'),
            config.codeimport.bazaar_branch_store.rstrip('/'))

    def test_getNewBranch(self):
        # If there's no Bazaar branch for the code import object, then pull
        # creates a new Bazaar working tree.
        store = self.makeBranchStore()
        bzr_working_tree = store.pull(self.branch, self.temp_dir)
        self.assertEqual([], bzr_working_tree.branch.revision_history())

    def test_pushBranchThenPull(self):
        # After we've pushed up a branch to the store, we can then pull it
        # from the store.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.branch, tree)
        new_tree = store.pull(self.branch, self.temp_dir)
        self.assertEqual(
            tree.branch.last_revision(), new_tree.branch.last_revision())

    def test_pushTwiceThenPull(self):
        # We can push up a branch to the store twice and then pull it from the
        # store.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.branch, tree)
        store.push(self.branch, tree)
        new_tree = store.pull(self.branch, self.temp_dir)
        self.assertEqual(
            tree.branch.last_revision(), new_tree.branch.last_revision())

    def test_pushNonImportBranch(self):
        # push() raises a BranchTypeError if you try to push a non-imported
        # branch.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        db_branch = self.factory.makeBranch(BranchType.HOSTED)
        self.assertRaises(BranchTypeError, store.push, db_branch, tree)

    def test_pullNonImportBranch(self):
        # pull() raises a BranchTypeError if you try to pull a non-imported
        # branch.
        store = self.makeBranchStore()
        db_branch = self.factory.makeBranch(BranchType.HOSTED)
        self.assertRaises(BranchTypeError, store.pull, db_branch, 'tree')

    def fetchBranch(self, from_url, target_path):
        """Pull a branch from `from_url` to `target_path`.

        This uses the Bazaar API for pulling a branch, and is used to test
        that `push` indeed pushes a branch to a specific location.

        :return: The working tree of the branch.
        """
        bzr_dir = BzrDir.open(from_url)
        bzr_dir.sprout(target_path)
        return BzrDir.open(target_path).open_workingtree()

    def test_makesDirectories(self):
        # push() tries to create the base directory of the branch store if it
        # doesn't already exist.
        store = BazaarBranchStore(self.get_transport('doesntexist'))
        tree = create_branch_with_one_revision('original')
        store.push(self.branch, tree)
        self.assertIsDirectory('doesntexist', self.get_transport())

    def test_storedLocation(self):
        # push() puts the branch in a directory named after the branch ID on
        # the BazaarBranchStore's transport.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.branch, tree)
        new_tree = self.fetchBranch(
            urljoin(store.transport.base, '%08x' % self.branch.id),
            'new_tree')
        self.assertEqual(
            tree.branch.last_revision(), new_tree.branch.last_revision())

    def test_sftpPrefix(self):
        # Since branches are mirrored by importd via sftp, _getMirrorURL must
        # support sftp urls. There was once a bug that made it incorrect with
        # sftp.
        sftp_prefix = 'sftp://example/base/'
        store = BazaarBranchStore(get_transport(sftp_prefix))
        self.assertEqual(
            store._getMirrorURL(self.branch),
            sftp_prefix + '%08x' % self.branch.id)

    def test_sftpPrefixNoSlash(self):
        # If the prefix has no trailing slash, one should be added. It's very
        # easy to forget a trailing slash in the importd configuration.
        sftp_prefix_noslash = 'sftp://example/base'
        store = BazaarBranchStore(get_transport(sftp_prefix_noslash))
        self.assertEqual(
            store._getMirrorURL(self.branch),
            sftp_prefix_noslash + '/' + '%08x' % self.branch.id)


class MockForeignWorkingTree:
    """Working tree that records calls to checkout and update."""

    def __init__(self, local_path):
        self.local_path = local_path
        self.log = []

    def checkout(self):
        self.log.append('checkout')

    def update(self):
        self.log.append('update')


class TestForeignTreeStore(WorkerTest):
    """Tests for the `ForeignTreeStore` object."""

    def assertCheckedOut(self, tree):
        self.assertEqual(['checkout'], tree.log)

    def assertUpdated(self, tree):
        self.assertEqual(['update'], tree.log)

    def setUp(self):
        """Set up a code import job to import a SVN branch."""
        super(TestForeignTreeStore, self).setUp()
        self.code_import = self.factory.makeCodeImport()
        self.temp_dir = self.makeTemporaryDirectory()
        self._log = []

    def makeForeignTreeStore(self, transport=None):
        """Make a foreign branch store.

        The store is in a different directory to the local working directory.
        """
        def _getForeignBranch(code_import, target_path):
            return MockForeignWorkingTree(target_path)
        if transport is None:
            transport = self.get_transport('remote')
        store = ForeignTreeStore(transport)
        store._getForeignBranch = _getForeignBranch
        return store

    def test_getForeignBranchSubversion(self):
        # _getForeignBranch() returns a Subversion working tree for Subversion
        # code imports.
        store = ForeignTreeStore(None)
        svn_import = self.factory.makeCodeImport(
            svn_branch_url=self.factory.getUniqueURL())
        working_tree = store._getForeignBranch(svn_import, 'path')
        self.assertIsSameRealPath(working_tree.local_path, 'path')
        self.assertEqual(working_tree.remote_url, svn_import.svn_branch_url)

    def test_getForeignBranchCVS(self):
        # _getForeignBranch() returns a CVS working tree for CVS code imports.
        store = ForeignTreeStore(None)
        cvs_import = self.factory.makeCodeImport(
            cvs_root='root', cvs_module='module')
        working_tree = store._getForeignBranch(cvs_import, 'path')
        self.assertIsSameRealPath(working_tree.local_path, 'path')
        self.assertEqual(working_tree.root, cvs_import.cvs_root)
        self.assertEqual(working_tree.module, cvs_import.cvs_module)

    def test_defaultStore(self):
        # The default store is at config.codeimport.foreign_tree_store.
        store = get_default_foreign_tree_store()
        self.assertEqual(
            store.transport.base.rstrip('/'),
            config.codeimport.foreign_tree_store.rstrip('/'))

    def test_getNewBranch(self):
        # If the branch store doesn't have an archive of the foreign branch,
        # then fetching the branch actually pulls in from the original site.
        store = self.makeForeignTreeStore()
        tree = store.fetchFromSource(self.code_import, self.temp_dir)
        self.assertCheckedOut(tree)

    def test_archiveBranch(self):
        # Once we have a checkout of a foreign branch, we can archive it so
        # that we can retrieve it more reliably in the future.
        store = self.makeForeignTreeStore()
        foreign_branch = store.fetchFromSource(
            self.code_import, self.temp_dir)
        store.archive(self.code_import, foreign_branch)
        self.assertTrue(
            store.transport.has('%08x.tar.gz' % self.code_import.branch.id),
            "Couldn't find '%08x.tar.gz'" % self.code_import.branch.id)

    def test_makeDirectories(self):
        # archive() tries to create the base directory of the branch store if
        # it doesn't already exist.
        store = self.makeForeignTreeStore(self.get_transport('doesntexist'))
        foreign_branch = store.fetchFromSource(
            self.code_import, self.temp_dir)
        store.archive(self.code_import, foreign_branch)
        self.assertIsDirectory('doesntexist', self.get_transport())

    def test_fetchFromArchiveFailure(self):
        # If a branch has not been archived yet, but we try to retrieve it
        # from the archive, then we get a NoSuchFile error.
        store = self.makeForeignTreeStore()
        self.assertRaises(
            NoSuchFile,
            store.fetchFromArchive, self.code_import, self.temp_dir)

    def test_fetchFromArchive(self):
        # After archiving a branch, we can retrieve it from the store -- the
        # tarball gets downloaded and extracted.
        store = self.makeForeignTreeStore()
        foreign_branch = store.fetchFromSource(
            self.code_import, self.temp_dir)
        store.archive(self.code_import, foreign_branch)
        new_temp_dir = self.makeTemporaryDirectory()
        foreign_branch2 = store.fetchFromArchive(
            self.code_import, new_temp_dir)
        self.assertEqual(new_temp_dir, foreign_branch2.local_path)
        self.assertDirectoryTreesEqual(self.temp_dir, new_temp_dir)

    def test_fetchFromArchiveUpdates(self):
        # The local working tree is updated with changes from the remote
        # branch after it has been fetched from the archive.
        store = self.makeForeignTreeStore()
        foreign_branch = store.fetchFromSource(
            self.code_import, self.temp_dir)
        store.archive(self.code_import, foreign_branch)
        new_temp_dir = self.makeTemporaryDirectory()
        foreign_branch2 = store.fetchFromArchive(
            self.code_import, new_temp_dir)
        self.assertUpdated(foreign_branch2)


class FakeForeignTreeStore(ForeignTreeStore):
    """A ForeignTreeStore that always fetches fake foreign branches."""

    def __init__(self):
        ForeignTreeStore.__init__(self, None)

    def fetch(self, code_import, target_path):
        return MockForeignWorkingTree(target_path)


class TestWorkerCore(WorkerTest):
    """Tests for the core (VCS-independent) part of the code import worker."""

    def setUp(self):
        WorkerTest.setUp(self)
        code_import = self.factory.makeCodeImport()
        self.job = self.factory.makeCodeImportJob(code_import)

    def makeBazaarBranchStore(self):
        """Make a Bazaar branch store."""
        return BazaarBranchStore(self.get_transport('bazaar_branches'))

    def makeImportWorker(self):
        """Make an ImportWorker that only uses fake branches."""
        return ImportWorker(
            self.job.id, FakeForeignTreeStore(),
            self.makeBazaarBranchStore())

    def test_construct(self):
        # When we construct an ImportWorker, it has a CodeImportJob and a
        # working directory.
        worker = self.makeImportWorker()
        self.assertEqual(self.job.id, worker.job.id)
        self.assertEqual(True, os.path.isdir(worker.working_directory))

    def test_getBazaarWorkingTreeMakesEmptyTree(self):
        # getBazaarWorkingTree returns a brand-new working tree for an initial
        # import.
        worker = self.makeImportWorker()
        bzr_working_tree = worker.getBazaarWorkingTree()
        self.assertEqual([], bzr_working_tree.branch.revision_history())

    def test_bazaarWorkingTreeLocation(self):
        # getBazaarWorkingTree makes the working tree under the job's working
        # directory.
        worker = self.makeImportWorker()
        bzr_working_tree = worker.getBazaarWorkingTree()
        self.assertIsSameRealPath(
            os.path.join(
                worker.working_directory, worker.BZR_WORKING_TREE_PATH),
            os.path.abspath(bzr_working_tree.basedir))

    def test_getForeignBranch(self):
        # getForeignBranch returns an object that represents the 'foreign'
        # branch (i.e. a CVS or Subversion branch).
        worker = self.makeImportWorker()
        branch = worker.getForeignBranch()
        self.assertIsSameRealPath(
            os.path.join(
                worker.working_directory, worker.FOREIGN_WORKING_TREE_PATH),
            branch.local_path)


class TestActualImportMixin:
    """Mixin for tests that check the actual importing."""

    def setUpImport(self):
        """Set up the objects required for an import.

        This means a BazaarBranchStore, ForeignTreeStore, CodeImport and
        a CodeImportJob.
        """
        repository_path = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(repository_path))

        self.bazaar_store = BazaarBranchStore(
            self.get_transport('bazaar_store'))
        self.foreign_store = ForeignTreeStore(
            self.get_transport('foreign_store'))

        self.code_import = self.makeCodeImport(
            repository_path, 'trunk', [('README', 'Original contents')])
        self.job = self.factory.makeCodeImportJob(self.code_import)

    def commitInForeignTree(self, foreign_tree):
        """Commit a single revision to `foreign_tree`.

        Override this in your subclass.
        """
        raise NotImplementedError(
            "Override this with a VCS-specific implementation.")

    def makeCodeImport(self, repository_path, module_name, files):
        """Make a `CodeImport` that points to a real repository.

        Override this in your subclass.
        """
        raise NotImplementedError(
            "Override this with a VCS-specific implementation.")

    def makeImportWorker(self):
        """Make a new `ImportWorker`."""
        return ImportWorker(
            self.job.id, self.foreign_store, self.bazaar_store)

    def test_import(self):
        # Running the worker on a branch that hasn't been imported yet imports
        # the branch.
        worker = self.makeImportWorker()
        worker.run()
        bazaar_tree = worker.getBazaarWorkingTree()
        # XXX: JonathanLange 2008-02-22: This assumes that the branch that we
        # are importing has two revisions. Looking at the test, it's not
        # obvious why we make this assumption, hence the XXX. The two
        # revisions are from 1) making the repository and 2) adding a file.
        # The name of this test smell is "Mystery Guest".
        self.assertEqual(2, len(bazaar_tree.branch.revision_history()))

    def test_sync(self):
        # Do an import.
        worker = self.makeImportWorker()
        worker.run()
        bazaar_tree = worker.getBazaarWorkingTree()
        self.assertEqual(2, len(bazaar_tree.branch.revision_history()))

        # Change the remote branch.
        foreign_tree = worker.getForeignBranch()
        self.commitInForeignTree(foreign_tree)

        # Run the same worker again.
        worker.run()

        # Check that the new revisions are in the Bazaar branch.
        bazaar_tree = worker.getBazaarWorkingTree()
        self.assertEqual(3, len(bazaar_tree.branch.revision_history()))


class TestCVSImport(WorkerTest, TestActualImportMixin):
    """Tests for the worker importing and syncing a CVS module."""

    def setUp(self):
        super(TestCVSImport, self).setUp()
        self.setUpImport()

    def commitInForeignTree(self, foreign_tree):
        # If you write to a file in the same second as the previous commit,
        # CVS will not think that it has changed.
        time.sleep(1)
        self.build_tree_contents(
            [(os.path.join(foreign_tree.local_path, 'README'),
              'New content')])
        foreign_tree.commit()

    def makeCodeImport(self, repository_path, module_name, files):
        """Make a CVS `CodeImport` that points to a real CVS repository."""
        cvs_server = CVSServer(repository_path)
        cvs_server.setUp()
        self.addCleanup(cvs_server.tearDown)

        cvs_server.makeModule('trunk', [('README', 'original\n')])

        # Construct a CodeImportJob
        return self.factory.makeCodeImport(
            cvs_root=cvs_server.getRoot(), cvs_module='trunk')


class TestSubversionImport(WorkerTest, TestActualImportMixin):
    """Tests for the worker importing and syncing a Subversion branch."""

    def setUp(self):
        WorkerTest.setUp(self)
        self.setUpImport()

    def commitInForeignTree(self, foreign_tree):
        """Change the foreign tree, generating exactly one commit."""
        svn_url = foreign_tree.remote_url
        client = pysvn.Client()
        client.checkout(svn_url, 'working_tree')
        file = open('working_tree/newfile', 'w')
        file.write('No real content\n')
        file.close()
        client.add('working_tree/newfile')
        client.checkin('working_tree', 'Add a file', recurse=True)
        shutil.rmtree('working_tree')

    def makeCodeImport(self, repository_path, branch_name, files):
        """Make a Subversion `CodeImport` that points to a real SVN repo."""
        svn_server = SubversionServer(repository_path)
        svn_server.setUp()
        self.addCleanup(svn_server.tearDown)

        svn_branch_url = svn_server.makeBranch(branch_name, files)
        return self.factory.makeCodeImport(svn_branch_url)

    def test_bazaarBranchStored(self):
        # The worker stores the Bazaar branch after it has imported the new
        # revisions.
        # XXX: JonathanLange 2008-02-22: This test ought to be VCS-neutral.
        worker = self.makeImportWorker()
        worker.run()

        bazaar_tree = worker.bazaar_branch_store.pull(
            worker.job.code_import.branch, 'tmp-bazaar-tree')
        self.assertEqual(
            bazaar_tree.branch.last_revision(),
            worker.getBazaarWorkingTree().last_revision())

    def test_foreignTreeStored(self):
        # The worker archives the foreign tree after it has imported the new
        # revisions.
        # XXX: JonathanLange 2008-02-22: This test ought to be VCS-neutral.
        worker = self.makeImportWorker()
        worker.run()

        os.mkdir('tmp-foreign-tree')
        foreign_tree = worker.foreign_tree_store.fetchFromArchive(
            worker.job.code_import, 'tmp-foreign-tree')
        self.assertDirectoryTreesEqual(
            foreign_tree.local_path, worker.getForeignBranch().local_path)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
