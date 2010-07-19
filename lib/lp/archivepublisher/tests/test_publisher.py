# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for publisher class."""

__metaclass__ = type


import bz2
import gzip
import os
import shutil
import stat
import tempfile
import transaction
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.zeca.ftests.harness import ZecaTestSetup
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.diskpool import DiskPool
from lp.archivepublisher.publishing import Publisher, getPublisher
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.ftests.keys_for_tests import gpgkeysdir
from lp.soyuz.interfaces.archive import (
    ArchivePurpose, ArchiveStatus, IArchiveSet)
from lp.soyuz.interfaces.binarypackagerelease import (
    BinaryPackageFormat)
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.series import SeriesStatus
from canonical.launchpad.interfaces.gpghandler import IGPGHandler
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.archivepublisher.interfaces.archivesigningkey import (
    IArchiveSigningKey)
from lp.soyuz.tests.test_publishing import TestNativePublishingBase


class TestPublisherBase(TestNativePublishingBase):
    """Basic setUp for `TestPublisher` classes.

    Extends `TestNativePublishingBase` already.
    """

    def setUp(self):
        """Override cprov PPA distribution to 'ubuntutest'."""
        TestNativePublishingBase.setUp(self)

        # Override cprov's PPA distribution, because we can't publish
        # 'ubuntu' in the current sampledata.
        cprov = getUtility(IPersonSet).getByName('cprov')
        naked_archive = removeSecurityProxy(cprov.archive)
        naked_archive.distribution = self.ubuntutest


class TestPublisher(TestPublisherBase):
    """Testing `Publisher` behaviour."""

    def assertDirtyPocketsContents(self, expected, dirty_pockets):
        contents = [(str(dr_name), pocket.name) for dr_name, pocket in
                    dirty_pockets]
        self.assertEqual(expected, contents)

    def testInstantiate(self):
        """Publisher should be instantiatable"""
        Publisher(self.logger, self.config, self.disk_pool,
                  self.ubuntutest.main_archive)

    def testPublishing(self):
        """Test the non-careful publishing procedure.

        With one PENDING record, respective pocket *dirtied*.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive)

        pub_source = self.getPubSource(filecontent='Hello world')

        publisher.A_publish(False)
        self.layer.txn.commit()

        pub_source.sync()
        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

        # file got published
        foo_path = "%s/main/f/foo/foo_666.dsc" % self.pool_dir
        self.assertEqual(open(foo_path).read().strip(), 'Hello world')

    def testDeletingPPA(self):
        """Test deleting a PPA"""
        ubuntu_team = getUtility(IPersonSet).getByName('ubuntu-team')
        test_archive = getUtility(IArchiveSet).new(
            distribution=self.ubuntutest, owner=ubuntu_team,
            purpose=ArchivePurpose.PPA)
        publisher = getPublisher(test_archive, None, self.logger)

        self.assertTrue(os.path.exists(publisher._config.archiveroot))

        # Create a file inside archiveroot to ensure we're recursive.
        open(os.path.join(
            publisher._config.archiveroot, 'test_file'), 'w').close()
        # And a meta file
        os.makedirs(publisher._config.metaroot)
        open(os.path.join(publisher._config.metaroot, 'test'), 'w').close()

        publisher.deleteArchive()
        root_dir = os.path.join(
            publisher._config.distroroot, test_archive.owner.name,
            test_archive.name)
        self.assertFalse(os.path.exists(root_dir))
        self.assertFalse(os.path.exists(publisher._config.metaroot))
        self.assertEqual(test_archive.status, ArchiveStatus.DELETED)
        self.assertEqual(test_archive.publish, False)

        # Trying to delete it again won't fail, in the corner case where
        # some admin manually deleted the repo.
        publisher.deleteArchive()

    def testDeletingPPAWithoutMetaData(self):
        ubuntu_team = getUtility(IPersonSet).getByName('ubuntu-team')
        test_archive = getUtility(IArchiveSet).new(
            distribution=self.ubuntutest, owner=ubuntu_team,
            purpose=ArchivePurpose.PPA)
        publisher = getPublisher(test_archive, None, self.logger)

        self.assertTrue(os.path.exists(publisher._config.archiveroot))

        # Create a file inside archiveroot to ensure we're recursive.
        open(os.path.join(
            publisher._config.archiveroot, 'test_file'), 'w').close()

        publisher.deleteArchive()
        root_dir = os.path.join(
            publisher._config.distroroot, test_archive.owner.name,
            test_archive.name)
        self.assertFalse(os.path.exists(root_dir))

    def testPublishPartner(self):
        """Test that a partner package is published to the right place."""
        archive = self.ubuntutest.getArchiveByComponent('partner')
        pub_config = getPubConfig(archive)
        pub_config.setupArchiveDirs()
        disk_pool = DiskPool(
            pub_config.poolroot, pub_config.temproot, self.logger)
        publisher = Publisher(
            self.logger, pub_config, disk_pool, archive)
        self.getPubSource(archive=archive, filecontent="I am partner")

        publisher.A_publish(False)

        # Did the file get published in the right place?
        self.assertEqual(pub_config.poolroot,
            "/var/tmp/archive/ubuntutest-partner/pool")
        foo_path = "%s/main/f/foo/foo_666.dsc" % pub_config.poolroot
        self.assertEqual(open(foo_path).read().strip(), "I am partner")

        # Check that the index is in the right place.
        publisher.C_writeIndexes(False)
        self.assertEqual(pub_config.distsroot,
            "/var/tmp/archive/ubuntutest-partner/dists")
        index_path = os.path.join(
            pub_config.distsroot, 'breezy-autotest', 'partner', 'source',
            'Sources.gz')
        self.assertTrue(open(index_path))

        # Check the release file is in the right place.
        publisher.D_writeReleaseFiles(False)
        release_file = os.path.join(
            pub_config.distsroot, 'breezy-autotest', 'Release')
        self.assertTrue(open(release_file))

    def testPartnerReleasePocketPublishing(self):
        """Test partner package RELEASE pocket publishing.

        Publishing partner packages to the RELEASE pocket in a stable
        distroseries is always allowed, so check for that here.
        """
        archive = self.ubuntutest.getArchiveByComponent('partner')
        self.ubuntutest['breezy-autotest'].status = SeriesStatus.CURRENT
        pub_config = getPubConfig(archive)
        pub_config.setupArchiveDirs()
        disk_pool = DiskPool(
            pub_config.poolroot, pub_config.temproot, self.logger)
        publisher = Publisher(self.logger, pub_config, disk_pool, archive)
        self.getPubSource(
            archive=archive, filecontent="I am partner",
            status=PackagePublishingStatus.PENDING)

        publisher.A_publish(force_publishing=False)

        # The pocket was dirtied:
        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        # The file was published:
        foo_path = "%s/main/f/foo/foo_666.dsc" % pub_config.poolroot
        self.assertEqual(open(foo_path).read().strip(), 'I am partner')

        # Nothing to test from these two calls other than that they don't blow
        # up as there is an assertion in the code to make sure it's not
        # publishing out of a release pocket in a stable distroseries,
        # excepting PPA and partner which are allowed to do that.
        publisher.C_writeIndexes(is_careful=False)
        publisher.D_writeReleaseFiles(is_careful=False)

    def testPublishingSpecificDistroSeries(self):
        """Test the publishing procedure with the suite argument.

        To publish a specific distroseries.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive,
            allowed_suites=[('hoary-test', PackagePublishingPocket.RELEASE)])

        pub_source = self.getPubSource(filecontent='foo')
        pub_source2 = self.getPubSource(
            sourcename='baz', filecontent='baz',
            distroseries=self.ubuntutest['hoary-test'])

        publisher.A_publish(force_publishing=False)
        self.layer.txn.commit()

        pub_source.sync()
        pub_source2.sync()
        self.assertDirtyPocketsContents(
            [('hoary-test', 'RELEASE')], publisher.dirty_pockets)
        self.assertEqual(pub_source2.status,
            PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)

    def testPublishingSpecificPocket(self):
        """Test the publishing procedure with the suite argument.

        To publish a specific pocket.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive,
            allowed_suites=[('breezy-autotest',
                             PackagePublishingPocket.UPDATES)])

        self.ubuntutest['breezy-autotest'].status = (
            SeriesStatus.CURRENT)

        pub_source = self.getPubSource(
            filecontent='foo',
            pocket=PackagePublishingPocket.UPDATES)

        pub_source2 = self.getPubSource(
            sourcename='baz', filecontent='baz',
            pocket=PackagePublishingPocket.BACKPORTS)

        publisher.A_publish(force_publishing=False)
        self.layer.txn.commit()

        pub_source.sync()
        pub_source2.sync()
        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'UPDATES')], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_source2.status, PackagePublishingStatus.PENDING)

    def testNonCarefulPublishing(self):
        """Test the non-careful publishing procedure.

        With one PUBLISHED record, no pockets *dirtied*.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive)

        self.getPubSource(status=PackagePublishingStatus.PUBLISHED)

        # a new non-careful publisher won't find anything to publish, thus
        # no pockets will be *dirtied*.
        publisher.A_publish(False)

        self.assertDirtyPocketsContents([], publisher.dirty_pockets)
        # nothing got published
        foo_path = "%s/main/f/foo/foo_666.dsc" % self.pool_dir
        self.assertEqual(False, os.path.exists(foo_path))

    def testCarefulPublishing(self):
        """Test the careful publishing procedure.

        With one PUBLISHED record, pocket gets *dirtied*.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive)

        self.getPubSource(
            filecontent='Hello world',
            status=PackagePublishingStatus.PUBLISHED)

        # A careful publisher run will re-publish the PUBLISHED records,
        # then we will have a corresponding dirty_pocket entry.
        publisher.A_publish(True)

        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        # file got published
        foo_path = "%s/main/f/foo/foo_666.dsc" % self.pool_dir
        self.assertEqual(open(foo_path).read().strip(), 'Hello world')

    def testPublishingOnlyConsidersOneArchive(self):
        """Publisher procedure should only consider the target archive.

        Ignore pending publishing records targeted to another archive.
        Nothing gets published, no pockets get *dirty*
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive)

        ubuntu_team = getUtility(IPersonSet).getByName('ubuntu-team')
        test_archive = getUtility(IArchiveSet).new(
            owner=ubuntu_team, purpose=ArchivePurpose.PPA)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo_1.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PENDING, archive=test_archive)

        publisher.A_publish(False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents([], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)

        # nothing got published
        foo_path = "%s/main/f/foo/foo_1.dsc" % self.pool_dir
        self.assertEqual(os.path.exists(foo_path), False)

    def testPublishingWorksForOtherArchives(self):
        """Publisher also works as expected for another archives."""
        ubuntu_team = getUtility(IPersonSet).getByName('ubuntu-team')
        test_archive = getUtility(IArchiveSet).new(
            distribution=self.ubuntutest, owner=ubuntu_team,
            purpose=ArchivePurpose.PPA)

        test_pool_dir = tempfile.mkdtemp()
        test_temp_dir = tempfile.mkdtemp()
        test_disk_pool = DiskPool(test_pool_dir, test_temp_dir, self.logger)

        publisher = Publisher(
            self.logger, self.config, test_disk_pool,
            test_archive)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo_1.dsc",
            filecontent='I am supposed to be a embargoed archive',
            status=PackagePublishingStatus.PENDING, archive=test_archive)

        publisher.A_publish(False)
        self.layer.txn.commit()

        pub_source.sync()
        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

        # nothing got published
        foo_path = "%s/main/f/foo/foo_1.dsc" % test_pool_dir
        self.assertEqual(
            open(foo_path).read().strip(),
            'I am supposed to be a embargoed archive',)

        # remove locally created dir
        shutil.rmtree(test_pool_dir)

    def testPublisherBuilderFunctions(self):
        """Publisher can be initialized via provided helper function.

        In order to simplify the top-level publication scripts, one for
        'main_archive' publication and other for 'PPA', we have a specific
        helper function: 'getPublisher'
        """
        # Stub parameters.
        allowed_suites = [
            ('breezy-autotest', PackagePublishingPocket.RELEASE)]
        distsroot = None

        distro_publisher = getPublisher(
            self.ubuntutest.main_archive, allowed_suites, self.logger,
            distsroot)

        # check the publisher context, pointing to the 'main_archive'
        self.assertEqual(
            self.ubuntutest.main_archive, distro_publisher.archive)
        self.assertEqual(
            '/var/tmp/archive/ubuntutest/dists',
            distro_publisher._config.distsroot)
        self.assertEqual(
            [('breezy-autotest', PackagePublishingPocket.RELEASE)],
            distro_publisher.allowed_suites)

        # Check that the partner archive is built in a different directory
        # to the primary archive.
        partner_archive = getUtility(IArchiveSet).getByDistroPurpose(
            self.ubuntutest, ArchivePurpose.PARTNER)
        distro_publisher = getPublisher(
            partner_archive, allowed_suites, self.logger, distsroot)
        self.assertEqual(partner_archive, distro_publisher.archive)
        self.assertEqual('/var/tmp/archive/ubuntutest-partner/dists',
            distro_publisher._config.distsroot)
        self.assertEqual('/var/tmp/archive/ubuntutest-partner/pool',
            distro_publisher._config.poolroot)

        # lets setup an Archive Publisher
        cprov = getUtility(IPersonSet).getByName('cprov')
        archive_publisher = getPublisher(
            cprov.archive, allowed_suites, self.logger)

        # check the publisher context, pointing to the given PPA archive
        self.assertEqual(
            cprov.archive, archive_publisher.archive)
        self.assertEqual(
            u'/var/tmp/ppa.test/cprov/ppa/ubuntutest/dists',
            archive_publisher._config.distsroot)
        self.assertEqual(
            [('breezy-autotest', PackagePublishingPocket.RELEASE)],
            archive_publisher.allowed_suites)

    def testPendingArchive(self):
        """Check Pending Archive Lookup.

        IArchiveSet.getPendingPPAs should only return the archives with
        publications in PENDING state.
        """
        archive_set = getUtility(IArchiveSet)
        person_set = getUtility(IPersonSet)
        ubuntu = getUtility(IDistributionSet)['ubuntu']

        spiv = person_set.getByName('spiv')
        archive_set.new(
            owner=spiv, distribution=ubuntu, purpose=ArchivePurpose.PPA)
        name16 = person_set.getByName('name16')
        archive_set.new(
            owner=name16, distribution=ubuntu, purpose=ArchivePurpose.PPA)

        self.getPubSource(
            sourcename="foo", filename="foo_1.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PENDING, archive=spiv.archive)

        self.getPubSource(
            sourcename="foo", filename="foo_1.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PUBLISHED, archive=name16.archive)

        self.assertEqual(4, ubuntu.getAllPPAs().count())

        pending_archives = ubuntu.getPendingPublicationPPAs()
        self.assertEqual(1, pending_archives.count())
        pending_archive = pending_archives[0]
        self.assertEqual(spiv.archive.id, pending_archive.id)

    def testDeletingArchive(self):
        # IArchiveSet.getPendingPPAs should return archives that have a
        # status of DELETING.
        ubuntu = getUtility(IDistributionSet)['ubuntu']

        archive = self.factory.makeArchive()
        old_num_pending_archives = ubuntu.getPendingPublicationPPAs().count()
        archive.status = ArchiveStatus.DELETING
        new_num_pending_archives = ubuntu.getPendingPublicationPPAs().count()
        self.assertEqual(
            1 + old_num_pending_archives, new_num_pending_archives)


    def _checkCompressedFile(self, archive_publisher, compressed_file_path,
                             uncompressed_file_path):
        """Assert that a compressed file is equal to its uncompressed version.

        Check that a compressed file, such as Packages.gz and Sources.gz,
        and bz2 variations, matches its uncompressed partner.  The file
        paths are relative to breezy-autotest/main under the
        archive_publisher's configured dist root. 'breezy-autotest' is
        our test distroseries name.

        The contents of the uncompressed file is returned as a list of lines
        in the file.
        """
        index_compressed_path = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest', 'main',
            compressed_file_path)
        index_path = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest', 'main',
            uncompressed_file_path)

        if index_compressed_path.endswith('.gz'):
            index_compressed_contents = gzip.GzipFile(
                filename=index_compressed_path).read().splitlines()
        elif index_compressed_path.endswith('.bz2'):
            index_compressed_contents = bz2.BZ2File(
                filename=index_compressed_path).read().splitlines()
        else:
            raise AssertionError(
                'Unsupported compression: %s' % compressed_file_path)

        index_file = open(index_path,'r')
        index_contents = index_file.read().splitlines()
        index_file.close()

        self.assertEqual(index_compressed_contents, index_contents)

        return index_contents

    def testPPAArchiveIndex(self):
        """Building Archive Indexes from PPA publications."""
        allowed_suites = []

        cprov = getUtility(IPersonSet).getByName('cprov')

        archive_publisher = getPublisher(
            cprov.archive, allowed_suites, self.logger)

        # Pending source and binary publications.
        # The binary description explores index formatting properties.
        pub_source = self.getPubSource(
            sourcename="foo", filename="foo_1.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PENDING, archive=cprov.archive)
        self.getPubBinaries(
            pub_source=pub_source,
            description="   My leading spaces are normalised to a single "
                        "space but not trailing.  \n    It does nothing, "
                        "though")[0]

        # Ignored (deleted) source publication that will not be listed in
        # the index and a pending 'udeb' binary package.
        ignored_source = self.getPubSource(
            status=PackagePublishingStatus.DELETED,
            archive=cprov.archive)
        self.getPubBinaries(
            pub_source=ignored_source, binaryname='bingo',
            description='nice udeb', format=BinaryPackageFormat.UDEB)[0]

        archive_publisher.A_publish(False)
        self.layer.txn.commit()
        archive_publisher.C_writeIndexes(False)

        # A compressed and uncompressed Sources file are written;
        # ensure that they are the same after uncompressing the former.
        index_contents = self._checkCompressedFile(
            archive_publisher, os.path.join('source', 'Sources.bz2'),
            os.path.join('source', 'Sources'))

        index_contents = self._checkCompressedFile(
            archive_publisher, os.path.join('source', 'Sources.gz'),
            os.path.join('source', 'Sources'))

        self.assertEqual(
            ['Package: foo',
             'Binary: foo-bin',
             'Version: 666',
             'Section: base',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Architecture: all',
             'Standards-Version: 3.6.2',
             'Format: 1.0',
             'Directory: pool/main/f/foo',
             'Files:',
             ' 3e25960a79dbc69b674cd4ec67a72c62 11 foo_1.dsc',
             ''],
            index_contents)

        # A compressed and an uncompressed Packages file are written;
        # ensure that they are the same after uncompressing the former.
        index_contents = self._checkCompressedFile(
            archive_publisher, os.path.join('binary-i386', 'Packages.bz2'),
            os.path.join('binary-i386', 'Packages'))

        index_contents = self._checkCompressedFile(
            archive_publisher, os.path.join('binary-i386', 'Packages.gz'),
            os.path.join('binary-i386', 'Packages'))

        self.assertEqual(
            ['Package: foo-bin',
             'Source: foo',
             'Priority: standard',
             'Section: base',
             'Installed-Size: 100',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Architecture: all',
             'Version: 666',
             'Filename: pool/main/f/foo/foo-bin_666_all.deb',
             'Size: 18',
             'MD5sum: 008409e7feb1c24a6ccab9f6a62d24c5',
             'SHA1: 30b7b4e583fa380772c5a40e428434628faef8cf',
             'Description: Foo app is great',
             ' My leading spaces are normalised to a single space but not '
             'trailing.  ',
             ' It does nothing, though',
             ''],
            index_contents)

        # A compressed and an uncompressed Packages file are written for
        # 'debian-installer' section for each architecture. It will list
        # the 'udeb' files.
        index_contents = self._checkCompressedFile(
            archive_publisher,
            os.path.join('debian-installer', 'binary-i386', 'Packages.bz2'),
            os.path.join('debian-installer', 'binary-i386', 'Packages'))

        index_contents = self._checkCompressedFile(
            archive_publisher,
            os.path.join('debian-installer', 'binary-i386', 'Packages.gz'),
            os.path.join('debian-installer', 'binary-i386', 'Packages'))

        self.assertEqual(
            ['Package: bingo',
             'Source: foo',
             'Priority: standard',
             'Section: base',
             'Installed-Size: 100',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Architecture: all',
             'Version: 666',
             'Filename: pool/main/f/foo/bingo_666_all.udeb',
             'Size: 18',
             'MD5sum: 008409e7feb1c24a6ccab9f6a62d24c5',
             'SHA1: 30b7b4e583fa380772c5a40e428434628faef8cf',
             'Description: Foo app is great',
             ' nice udeb',
             ''],
            index_contents)

        # Check if apt_handler.release_files_needed has the right requests.
        # 'source' & 'binary-i386' Release files should be regenerated
        # for all breezy-autotest components. Note that 'debian-installer'
        # indexes do not need Release files.

        # We always regenerate all Releases file for a given suite.
        self.checkAllRequestedReleaseFiles(archive_publisher)

        # remove PPA root
        shutil.rmtree(config.personalpackagearchive.root)

    def checkDirtyPockets(self, publisher, expected):
        """Check dirty_pockets contents of a given publisher."""
        sorted_dirty_pockets = sorted(list(publisher.dirty_pockets))
        self.assertEqual(sorted_dirty_pockets, expected)

    def testDirtyingPocketsWithDeletedPackages(self):
        """Test that dirtying pockets with deleted packages works.

        The publisher run should make dirty pockets where there are
        outstanding deletions, so that the domination process will
        work on the deleted publications.
        """
        allowed_suites = []
        distsroot = None
        publisher = getPublisher(
            self.ubuntutest.main_archive, allowed_suites, self.logger,
            distsroot)

        publisher.A2_markPocketsWithDeletionsDirty()
        self.checkDirtyPockets(publisher, expected=[])

        # Make a published source, a deleted source in the release
        # pocket, a source that's been removed from disk and one that's
        # waiting to be deleted, each in different pockets.  The deleted
        # source in the release pocket should not be processed.  We'll
        # also have a binary waiting to be deleted.
        self.getPubSource(
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED)

        self.getPubSource(
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.DELETED)

        self.getPubSource(
            scheduleddeletiondate=UTC_NOW,
            dateremoved=UTC_NOW,
            pocket=PackagePublishingPocket.UPDATES,
            status=PackagePublishingStatus.DELETED)

        self.getPubSource(
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.DELETED)

        self.getPubBinaries(
            pocket=PackagePublishingPocket.BACKPORTS,
            status=PackagePublishingStatus.DELETED)

        # Run the deletion detection.
        publisher.A2_markPocketsWithDeletionsDirty()

        # Only the pockets with pending deletions are marked as dirty.
        expected_dirty_pockets = [
            ('breezy-autotest', PackagePublishingPocket.RELEASE),
            ('breezy-autotest', PackagePublishingPocket.SECURITY),
            ('breezy-autotest', PackagePublishingPocket.BACKPORTS)
            ]
        self.checkDirtyPockets(publisher, expected=expected_dirty_pockets)

        # If the distroseries is CURRENT, then the release pocket is not
        # marked as dirty.
        self.ubuntutest['breezy-autotest'].status = (
            SeriesStatus.CURRENT)

        publisher.dirty_pockets = set()
        publisher.A2_markPocketsWithDeletionsDirty()

        expected_dirty_pockets = [
            ('breezy-autotest', PackagePublishingPocket.SECURITY),
            ('breezy-autotest', PackagePublishingPocket.BACKPORTS)
            ]
        self.checkDirtyPockets(publisher, expected=expected_dirty_pockets)

    def testDeletionDetectionRespectsAllowedSuites(self):
        """Check if the deletion detection mechanism respects allowed_suites.

        The deletion detection should not request publications of pockets
        that were not specified on the command-line ('allowed_suites').

        This issue is reported as bug #241452, when running the publisher
        only for a specific suite, in most of cases an urgent security
        release, only pockets with pending deletion that match the
        specified suites should be marked as dirty.
        """
        allowed_suites = [
            ('breezy-autotest', PackagePublishingPocket.SECURITY),
            ('breezy-autotest', PackagePublishingPocket.UPDATES),
            ]
        distsroot = None
        publisher = getPublisher(
            self.ubuntutest.main_archive, allowed_suites, self.logger,
            distsroot)

        publisher.A2_markPocketsWithDeletionsDirty()
        self.checkDirtyPockets(publisher, expected=[])

        # Create pending deletions in RELEASE, BACKPORTS, SECURITY and
        # UPDATES pockets.
        self.getPubSource(
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.DELETED)

        self.getPubBinaries(
            pocket=PackagePublishingPocket.BACKPORTS,
            status=PackagePublishingStatus.DELETED)[0]

        self.getPubSource(
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.DELETED)

        self.getPubBinaries(
            pocket=PackagePublishingPocket.UPDATES,
            status=PackagePublishingStatus.DELETED)[0]

        publisher.A2_markPocketsWithDeletionsDirty()
        # Only the pockets with pending deletions in the allowed suites
        # are marked as dirty.
        self.checkDirtyPockets(publisher, expected=allowed_suites)

    def assertReleaseFileRequested(self, publisher, suite_name,
                                   component_name, arch_name):
        """Assert the given context will have it's Release file regenerated.

        Check if a request for the given context is correctly stored in:
           publisher.apt_handler.release_files_needed
        """
        suite = publisher.apt_handler.release_files_needed.get(suite_name)
        self.assertTrue(
            suite is not None, 'Suite %s not requested' % suite_name)
        self.assertTrue(
            component_name in suite,
            'Component %s/%s not requested' % (suite_name, component_name))
        self.assertTrue(
            arch_name in suite[component_name],
            'Arch %s/%s/%s not requested' % (
            suite_name, component_name, arch_name))

    def checkAllRequestedReleaseFiles(self, publisher):
        """Check if all expected Release files are going to be regenerated.

        'source', 'binary-i386' and 'binary-hppa' Release Files should be
        requested for regeneration in all breezy-autotest components.
        """
        available_components = sorted([
            c.name for c in self.breezy_autotest.components])
        self.assertEqual(available_components,
                         ['main', 'multiverse', 'restricted', 'universe'])

        available_archs = ['binary-%s' % a.architecturetag
                           for a in self.breezy_autotest.architectures]
        self.assertEqual(available_archs, ['binary-hppa', 'binary-i386'])

        # XXX cprov 20071210: Include the artificial component 'source' as a
        # location to check for generated indexes. Ideally we should
        # encapsulate this task in publishing.py and this common method
        # in tests as well.
        dists = ['source'] + available_archs
        for component in available_components:
            for dist in dists:
                self.assertReleaseFileRequested(
                    publisher, 'breezy-autotest', component, dist)

    def _getReleaseFileOrigin(self, contents):
        origin_header = 'Origin: '
        [origin_line] = [
            line for line in contents.splitlines()
            if line.startswith(origin_header)]
        origin = origin_line.replace(origin_header, '')
        return origin

    def testReleaseFile(self):
        """Test release file writing.

        The release file should contain the MD5, SHA1 and SHA256 for each
        index created for a given distroseries.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive)

        self.getPubSource(filecontent='Hello world')

        publisher.A_publish(False)
        publisher.C_doFTPArchive(False)

        # We always regenerate all Releases file for a given suite.
        self.checkAllRequestedReleaseFiles(publisher)

        publisher.D_writeReleaseFiles(False)

        release_file = os.path.join(
            self.config.distsroot, 'breezy-autotest', 'Release')
        release_contents = open(release_file).read()

        # Primary archive distroseries Release 'Origin' contains
        # the distribution displayname.
        self.assertEqual(
            self._getReleaseFileOrigin(release_contents), 'ubuntutest')

        # XXX cprov 20090427: we should write a Release file parsing for
        # making tests less cryptic.
        release_contents = release_contents.splitlines()
        md5_header = 'MD5Sum:'
        self.assertTrue(md5_header in release_contents)
        md5_header_index = release_contents.index(md5_header)
        first_md5_line = release_contents[md5_header_index + 17]
        self.assertEqual(
            first_md5_line,
            (' a5e5742a193740f17705c998206e18b6              '
             '114 main/source/Release'))

        sha1_header = 'SHA1:'
        self.assertTrue(sha1_header in release_contents)
        sha1_header_index = release_contents.index(sha1_header)
        first_sha1_line = release_contents[sha1_header_index + 17]
        self.assertEqual(
            first_sha1_line,
            (' 6222b7e616bcc20a32ec227254ad9de8d4bd5557              '
             '114 main/source/Release'))

        sha256_header = 'SHA256:'
        self.assertTrue(sha256_header in release_contents)
        sha256_header_index = release_contents.index(sha256_header)
        first_sha256_line = release_contents[sha256_header_index + 17]
        self.assertEqual(
            first_sha256_line,
            (' 297125e9b0f5da85552691597c9c4920aafd187e18a4e01d2ba70d'
             '8d106a6338              114 main/source/Release'))

        # The Label: field should be set to the archive displayname
        self.assertEqual(release_contents[1], 'Label: ubuntutest')

        # Primary archive architecture Release files 'Origin' contain
        # the distribution displayname.
        arch_release_file = os.path.join(
            publisher._config.distsroot, 'breezy-autotest',
            'main/source/Release')
        arch_release_contents = open(arch_release_file).read()
        self.assertEqual(
            self._getReleaseFileOrigin(arch_release_contents), 'ubuntutest')

    def testReleaseFileForPPA(self):
        """Test release file writing for PPA

        The release file should contain the MD5, SHA1 and SHA256 for each
        index created for a given distroseries.

        Note that the individuals indexes have exactly the same content
        as the ones generated by apt-ftparchive (see previous test), however
        the position in the list is different (earlier) because we do not
        generate/list debian-installer (d-i) indexes in NoMoreAptFtpArchive
        approach.

        Another difference between the primary repositories and PPAs is that
        PPA Release files for the distroseries and its architectures have a
        distinct 'Origin:' value.  The origin is specific to each PPA, using
        the pattern 'LP-PPA-%(owner_name)s'.  This allows proper pinning of
        the PPA packages.
        """
        allowed_suites = []
        cprov = getUtility(IPersonSet).getByName('cprov')
        cprov.archive.displayname = u'PPA for Celso Provid\xe8lo'
        archive_publisher = getPublisher(
            cprov.archive, allowed_suites, self.logger)

        self.getPubSource(filecontent='Hello world', archive=cprov.archive)

        archive_publisher.A_publish(False)
        self.layer.txn.commit()
        archive_publisher.C_writeIndexes(False)
        archive_publisher.D_writeReleaseFiles(False)

        release_file = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest', 'Release')
        release_contents = open(release_file).read()
        self.assertEqual(
            self._getReleaseFileOrigin(release_contents), 'LP-PPA-cprov')

        # XXX cprov 20090427: we should write a Release file parsing for
        # making tests less cryptic.
        release_contents = release_contents.splitlines()
        md5_header = 'MD5Sum:'
        self.assertTrue(md5_header in release_contents)
        md5_header_index = release_contents.index(md5_header)

        plain_sources_md5_line = release_contents[md5_header_index + 15]
        self.assertEqual(
            plain_sources_md5_line,
            (' 7d9b0817f5ff4a1d3f53f97bcc9c7658              '
             '229 main/source/Sources'))
        release_md5_line = release_contents[md5_header_index + 17]
        self.assertEqual(
            release_md5_line,
            (' eadc1fbb1a878a2ee6dc66d7cd8d46dc              '
            '130 main/source/Release'))
        # We can't probe checksums of compressed files because they contain
        # timestamps, their checksum varies with time.
        bz2_sources_md5_line = release_contents[md5_header_index + 16]
        self.assertTrue('main/source/Sources.bz2' in bz2_sources_md5_line)
        gz_sources_md5_line = release_contents[md5_header_index + 18]
        self.assertTrue('main/source/Sources.gz' in gz_sources_md5_line)

        sha1_header = 'SHA1:'
        self.assertTrue(sha1_header in release_contents)
        sha1_header_index = release_contents.index(sha1_header)

        plain_sources_sha1_line = release_contents[sha1_header_index + 15]
        self.assertEqual(
            plain_sources_sha1_line,
            (' a2da1a8407fc4e2373266e56ccc7afadf8e08a3a              '
             '229 main/source/Sources'))
        release_sha1_line = release_contents[sha1_header_index + 17]
        self.assertEqual(
            release_sha1_line,
            (' 1a8d788a6d2d30e0cab002ab82e9f2921f7a2a61              '
             '130 main/source/Release'))
        # See above.
        bz2_sources_sha1_line = release_contents[sha1_header_index + 16]
        self.assertTrue('main/source/Sources.bz2' in bz2_sources_sha1_line)
        gz_sources_sha1_line = release_contents[sha1_header_index + 18]
        self.assertTrue('main/source/Sources.gz' in gz_sources_sha1_line)

        sha256_header = 'SHA256:'
        self.assertTrue(sha256_header in release_contents)
        sha256_header_index = release_contents.index(sha256_header)

        plain_sources_sha256_line = release_contents[sha256_header_index + 15]
        self.assertEqual(
            plain_sources_sha256_line,
            (' 979d959ead8ddc29e4347a64058a372d30df58a51a4615b43fb7499'
             '8a9e07c78              229 main/source/Sources'))
        release_sha256_line = release_contents[sha256_header_index + 17]
        self.assertEqual(
            release_sha256_line,
            (' 795a3f17d485cc1983f588c53fb8c163599ed191be9741e61ca411f'
             '1e2c505aa              130 main/source/Release'))
        # See above.
        bz2_sources_sha256_line = release_contents[sha256_header_index + 16]
        self.assertTrue('main/source/Sources.bz2' in bz2_sources_sha256_line)
        gz_sources_sha256_line = release_contents[sha256_header_index + 18]
        self.assertTrue('main/source/Sources.gz' in gz_sources_sha256_line)

        # The Label: field should be set to the archive displayname
        self.assertEqual(release_contents[1],
            'Label: PPA for Celso Provid\xc3\xa8lo')

        # Architecture Release files also have a distinct Origin: for PPAs.
        arch_release_file = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest',
            'main/source/Release')
        arch_release_contents = open(arch_release_file).read()
        self.assertEqual(
            self._getReleaseFileOrigin(arch_release_contents), 'LP-PPA-cprov')

    def testReleaseFileForNamedPPA(self):
        # Named PPA have a distint Origin: field, so packages from it can
        # be pinned if necessary.

        # Create a named-ppa for Celso.
        cprov = getUtility(IPersonSet).getByName('cprov')
        named_ppa = getUtility(IArchiveSet).new(
            owner=cprov, name='testing', distribution=self.ubuntutest,
            purpose=ArchivePurpose.PPA)

        # Setup the publisher for it and publish its repository.
        allowed_suites = []
        archive_publisher = getPublisher(
            named_ppa, allowed_suites, self.logger)
        self.getPubSource(filecontent='Hello world', archive=named_ppa)

        archive_publisher.A_publish(False)
        self.layer.txn.commit()
        archive_publisher.C_writeIndexes(False)
        archive_publisher.D_writeReleaseFiles(False)

        # Check the distinct Origin: field content in the main Release file
        # and the architecture specific one.
        release_file = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest', 'Release')
        release_contents = open(release_file).read()
        self.assertEqual(
            self._getReleaseFileOrigin(release_contents),
            'LP-PPA-cprov-testing')

        arch_release_file = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest',
            'main/source/Release')
        arch_release_contents = open(arch_release_file).read()
        self.assertEqual(
            self._getReleaseFileOrigin(arch_release_contents),
            'LP-PPA-cprov-testing')

    def testReleaseFileForPartner(self):
        """Test Release file writing for Partner archives.

        Signed Release files must reference an uncompressed Sources and
        Packages file.
        """
        archive = self.ubuntutest.getArchiveByComponent('partner')
        allowed_suites = []
        publisher = getPublisher(archive, allowed_suites, self.logger)

        self.getPubSource(filecontent='Hello world', archive=archive)

        publisher.A_publish(False)
        publisher.C_writeIndexes(False)
        publisher.D_writeReleaseFiles(False)

        # Open the release file that was just published inside the
        # 'breezy-autotest' distroseries.
        release_file = os.path.join(
            publisher._config.distsroot, 'breezy-autotest', 'Release')
        release_contents = open(release_file).read().splitlines()

        # The Release file must contain lines ending in "Packages",
        # "Packages.gz", "Sources" and "Sources.gz".
        stringified_contents = "\n".join(release_contents)
        self.assertTrue('Packages.gz\n' in stringified_contents)
        self.assertTrue('Packages\n' in stringified_contents)
        self.assertTrue('Sources.gz\n' in stringified_contents)
        self.assertTrue('Sources\n' in stringified_contents)

        # Partner archive architecture Release files 'Origin' contain
        # a string
        arch_release_file = os.path.join(
            publisher._config.distsroot, 'breezy-autotest',
            'partner/source/Release')
        arch_release_contents = open(arch_release_file).read()
        self.assertEqual(
            self._getReleaseFileOrigin(arch_release_contents),
            'Canonical')
        
        # The Label: field should be set to the archive displayname
        self.assertEqual(release_contents[1], 'Label: Partner archive')

    def testWorldAndGroupReadablePackagesAndSources(self):
        """Test Packages.gz and Sources.gz files are world and group readable.

        Packages.gz and Sources.gz files generated by NoMoreAF must be
        world and group readable.  We'll test this in the partner archive
        as that uses NoMoreAF. (No More Apt-Ftparchive)
        """
        archive = self.ubuntutest.getArchiveByComponent('partner')
        allowed_suites = []
        publisher = getPublisher(archive, allowed_suites, self.logger)
        self.getPubSource(filecontent='Hello world', archive=archive)
        publisher.A_publish(False)
        publisher.C_writeIndexes(False)

        # Find a Sources.gz and Packages.gz that were just published
        # in the breezy-autotest distroseries.
        sourcesgz_file = os.path.join(
            publisher._config.distsroot, 'breezy-autotest', 'partner',
            'source', 'Sources.gz')
        packagesgz_file = os.path.join(
            publisher._config.distsroot, 'breezy-autotest', 'partner',
            'binary-i386', 'Packages.gz')

        # What permissions are set on those files?
        for file in (sourcesgz_file, packagesgz_file):
            mode = stat.S_IMODE(os.stat(file).st_mode)
            self.assertEqual(
                (mode & (stat.S_IROTH | stat.S_IRGRP)),
                (stat.S_IROTH | stat.S_IRGRP),
                "%s is not world/group readable." % file)


class TestPublisherRepositorySignatures(TestPublisherBase):
    """Testing `Publisher` signature behaviour."""

    archive_publisher = None

    def tearDown(self):
        """Purge the archive root location. """
        if self.archive_publisher is not None:
            shutil.rmtree(self.archive_publisher._config.distsroot)

    def setupPublisher(self, archive):
        """Setup a `Publisher` instance for the given archive."""
        allowed_suites = []
        self.archive_publisher = getPublisher(
            archive, allowed_suites, self.logger)


    def _publishArchive(self, archive):
        """Publish a test source in the given archive.

        Publish files in pool, generate archive indexes and release files.
        """
        self.setupPublisher(archive)
        self.getPubSource(archive=archive)

        self.archive_publisher.A_publish(False)
        transaction.commit()
        self.archive_publisher.C_writeIndexes(False)
        self.archive_publisher.D_writeReleaseFiles(False)

    @property
    def suite_path(self):
        return os.path.join(
            self.archive_publisher._config.distsroot, 'breezy-autotest')

    @property
    def release_file_path(self):
        return os.path.join(self.suite_path, 'Release')

    @property
    def release_file_signature_path(self):
        return os.path.join(self.suite_path, 'Release.gpg')

    @property
    def public_key_path(self):
        return os.path.join(
            self.archive_publisher._config.distsroot, 'key.gpg')

    def testRepositorySignatureWithNoSigningKey(self):
        """Check publisher behaviour when signing repositories.

        Repository signing procedure is skipped for archive with no
        'signing_key'.
        """
        cprov = getUtility(IPersonSet).getByName('cprov')
        self.assertTrue(cprov.archive.signing_key is None)

        self._publishArchive(cprov.archive)

        # Release file exist but it doesn't have any signature.
        self.assertTrue(os.path.exists(self.release_file_path))
        self.assertFalse(os.path.exists(self.release_file_signature_path))

    def testRepositorySignatureWithSigningKey(self):
        """Check publisher behaviour when signing repositories.

        When the 'signing_key' is available every modified suite Release
        file gets signed with a detached signature name 'Release.gpg'.
        """
        cprov = getUtility(IPersonSet).getByName('cprov')
        self.assertTrue(cprov.archive.signing_key is None)

        # Start the test keyserver, so the signing_key can be uploaded.
        z = ZecaTestSetup()
        z.setUp()

        # Set a signing key for Celso's PPA.
        key_path = os.path.join(gpgkeysdir, 'ppa-sample@canonical.com.sec')
        IArchiveSigningKey(cprov.archive).setSigningKey(key_path)
        self.assertTrue(cprov.archive.signing_key is not None)

        self._publishArchive(cprov.archive)

        # Both, Release and Release.gpg exist.
        self.assertTrue(os.path.exists(self.release_file_path))
        self.assertTrue(os.path.exists(self.release_file_signature_path))

        # Release file signature is correct and was done by Celso's PPA
        # signing_key.
        signature = getUtility(IGPGHandler).getVerifiedSignature(
            open(self.release_file_path).read(),
            open(self.release_file_signature_path).read())
        self.assertEqual(
            signature.fingerprint, cprov.archive.signing_key.fingerprint)

        # All done, turn test-keyserver off.
        z.tearDown()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

