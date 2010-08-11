# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.scripts import FakeLogger
from lp.soyuz.scripts.ftpmaster import (
    ObsoleteDistroseries, SoyuzScriptError)
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory)
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.testing.fakemethod import FakeMethod
from canonical.testing import LaunchpadZopelessLayer


class TestObsoleteDistroseriesScript(unittest.TestCase):
    """Test the obsolete-distroseries.py script."""
    layer = LaunchpadZopelessLayer

    def runCopyPackage(self, extra_args=None):
        """Run obsolete-distroseries.py, returning the result and output.

        Return a tuple of the process's return code, stdout output and
        stderr output.
        """
        if extra_args is None:
            extra_args = []
        script = os.path.join(
            config.root, "scripts", "ftpmaster-tools",
            "obsolete-distroseries.py")
        args = [sys.executable, script, '-y']
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testSimpleRun(self):
        """Try a simple obsolete-distroseries.py run.

        This test ensures that the script starts up and runs.
        We'll try to obsolete a non-obsolete distroseries, so it will
        just exit without doing anything.
        """
        returncode, out, err = self.runCopyPackage(extra_args=['-s', 'warty'])
        # Need to print these or you can't see what happened if the
        # return code is bad:
        self.assertEqual(1, returncode)
        expected = "ERROR   warty is not at status OBSOLETE."
        assert expected in err, (
            "Expected %s, got %s" % (expected, err))


class TestObsoleteDistroseries(unittest.TestCase):
    """Test the ObsoleteDistroseries class."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up test data common to all test cases."""
        self.warty = getUtility(IDistributionSet)['ubuntu']['warty']

        # Re-process the returned list otherwise it ends up being a list
        # of zope proxy objects that sqlvalues cannot deal with.
        self.main_archive_ids = [
            id for id in self.warty.distribution.all_distro_archive_ids]

    def getObsoleter(self, suite='warty', distribution='ubuntu',
                     confirm_all=True):
        """Return an ObsoleteDistroseries instance.

        Allow tests to use a set of default options and pass an
        inactive logger to ObsoleteDistroseries.
        """
        test_args = [
            '-s', suite,
            '-d', distribution,
            ]

        if confirm_all:
            test_args.append('-y')

        obsoleter = ObsoleteDistroseries(
            name='obsolete-distroseries', test_args=test_args)
        # Swallow all log messages.
        obsoleter.logger = FakeLogger()
        obsoleter.logger.message = FakeMethod()
        obsoleter.setupLocation()
        return obsoleter

    def getPublicationsForDistroseries(self, distroseries=None):
        """Return a tuple of sources, binaries published in distroseries."""
        if distroseries is None:
            distroseries = self.warty
        published_sources = SourcePackagePublishingHistory.select("""
            distroseries = %s AND
            status = %s AND
            archive IN %s
            """ % sqlvalues(distroseries, PackagePublishingStatus.PUBLISHED,
                            self.main_archive_ids))
        published_binaries = BinaryPackagePublishingHistory.select("""
            BinaryPackagePublishingHistory.distroarchseries =
                DistroArchSeries.id AND
            DistroArchSeries.DistroSeries = DistroSeries.id AND
            DistroSeries.id = %s AND
            BinaryPackagePublishingHistory.status = %s AND
            BinaryPackagePublishingHistory.archive IN %s
            """ % sqlvalues(distroseries, PackagePublishingStatus.PUBLISHED,
                            self.main_archive_ids),
            clauseTables=["DistroArchSeries", "DistroSeries"])
        return (published_sources, published_binaries)

    def testNonObsoleteDistroseries(self):
        """Test running over a non-obsolete distroseries."""
        # Default to warty, which is not obsolete.
        self.assertTrue(self.warty.status != PackagePublishingStatus.OBSOLETE)
        obsoleter = self.getObsoleter(suite='warty')
        self.assertRaises(SoyuzScriptError, obsoleter.mainTask)

    def testNothingToDoCase(self):
        """When there is nothing to do, we expect an exception."""
        obsoleter = self.getObsoleter()
        self.warty.status = SeriesStatus.OBSOLETE

        # Get all the published sources in warty.
        published_sources, published_binaries = (
            self.getPublicationsForDistroseries())

        # Reset their status to OBSOLETE.
        for package in published_sources:
            package.status = PackagePublishingStatus.OBSOLETE
        for package in published_binaries:
            package.status = PackagePublishingStatus.OBSOLETE

        # Call the script and ensure it does nothing.
        self.layer.txn.commit()
        self.assertRaises(SoyuzScriptError, obsoleter.mainTask)

    def testObsoleteDistroseriesWorks(self):
        """Make sure the required publications are obsoleted."""
        obsoleter = self.getObsoleter()
        self.warty.status = SeriesStatus.OBSOLETE

        # Get all the published sources in warty.
        published_sources, published_binaries = (
            self.getPublicationsForDistroseries())

        # Assert that none of them is obsolete yet:
        self.assertTrue(published_sources.count() != 0)
        self.assertTrue(published_binaries.count() != 0)
        for source in published_sources:
            self.assertTrue(
                source.status == PackagePublishingStatus.PUBLISHED)
            self.assertTrue(source.scheduleddeletiondate is None)
        for binary in published_binaries:
            self.assertTrue(
                binary.status == PackagePublishingStatus.PUBLISHED)
            self.assertTrue(binary.scheduleddeletiondate is None)

        # Keep their DB IDs for later.
        source_ids = [source.id for source in published_sources]
        binary_ids = [binary.id for binary in published_binaries]

        # Make them obsolete.
        obsoleter.mainTask()
        self.layer.txn.commit()

        # Now see if the modified publications have been correctly obsoleted.
        # We need to re-fetch the published_sources and published_binaries
        # because the existing objects are not valid through a transaction.
        for id in source_ids:
            source = SourcePackagePublishingHistory.get(id)
            self.assertTrue(
                source.status == PackagePublishingStatus.OBSOLETE)
            self.assertTrue(source.scheduleddeletiondate is not None)
        for id in binary_ids:
            binary = BinaryPackagePublishingHistory.get(id)
            self.assertTrue(
                binary.status == PackagePublishingStatus.OBSOLETE)
            self.assertTrue(binary.scheduleddeletiondate is not None)

        # Make sure nothing else was obsoleted.  Subtract the set of
        # known OBSOLETE IDs from the set of all the IDs and assert that
        # the remainder are not OBSOLETE.
        all_sources = SourcePackagePublishingHistory.select(True)
        all_binaries = BinaryPackagePublishingHistory.select(True)
        all_source_ids = [source.id for source in all_sources]
        all_binary_ids = [binary.id for binary in all_binaries]

        remaining_source_ids = set(all_source_ids) - set(source_ids)
        remaining_binary_ids = set(all_binary_ids) - set(binary_ids)

        for id in remaining_source_ids:
            source = SourcePackagePublishingHistory.get(id)
            self.assertTrue(
                source.status != PackagePublishingStatus.OBSOLETE)
        for id in remaining_binary_ids:
            binary = BinaryPackagePublishingHistory.get(id)
            self.assertTrue(
                binary.status != PackagePublishingStatus.OBSOLETE)
