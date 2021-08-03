# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test BuildQueue features."""

from datetime import timedelta

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.errors import NotFoundError
from lp.buildmaster.enums import (
    BuildQueueStatus,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.services.database.interfaces import IStore
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )


def find_job(test, name, processor='386'):
    """Find build and queue instance for the given source and processor."""

    def processor_matches(bq):
        if processor is None:
            return (bq.processor is None)
        else:
            return (processor == bq.processor.name)

    for build in test.builds:
        bq = build.buildqueue_record
        source = None
        for attr in ('source_package_release', 'recipe'):
            source = getattr(build, attr, None)
            if source is not None:
                break
        if (source.name == name and processor_matches(bq)):
            return (build, bq)
    return (None, None)


class TestBuildCancellation(TestCaseWithFactory):
    """Test cases for cancelling builds."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestBuildCancellation, self).setUp()
        self.builder = self.factory.makeBuilder()

    def test_buildqueue_cancel_waiting(self):
        # Cancelling a WAITING BuildQueue immediately destroys it and
        # sets the build to CANCELLED.
        build = self.factory.makeBinaryPackageBuild()
        bq = build.queueBuild()
        self.assertEqual(bq, build.buildqueue_record)
        self.assertEqual(BuildQueueStatus.WAITING, bq.status)
        self.assertEqual(BuildStatus.NEEDSBUILD, build.status)
        bq.cancel()
        self.assertIs(None, build.buildqueue_record)
        self.assertEqual(BuildStatus.CANCELLED, build.status)

    def test_buildqueue_cancel_running(self):
        # Cancelling a RUNNING BuildQueue leaves it around but sets the
        # status to CANCELLING. SlaveScanner will destroy it and set the
        # build status to CANCELLED when the slave cancellation has
        # completed.
        build = self.factory.makeBinaryPackageBuild()
        bq = build.queueBuild()
        bq.markAsBuilding(self.factory.makeBuilder())
        self.assertEqual(bq, build.buildqueue_record)
        self.assertEqual(BuildQueueStatus.RUNNING, bq.status)
        self.assertEqual(BuildStatus.BUILDING, build.status)
        bq.cancel()
        self.assertEqual(bq, build.buildqueue_record)
        self.assertEqual(BuildQueueStatus.CANCELLING, bq.status)
        self.assertEqual(BuildStatus.CANCELLING, build.status)
        bq.markAsCancelled()
        self.assertIs(None, build.buildqueue_record)
        self.assertEqual(BuildStatus.CANCELLED, build.status)

    def assertCancelled(self, build, bq):
        self.assertEqual(BuildStatus.CANCELLED, build.status)
        self.assertRaises(NotFoundError, getUtility(IBuildQueueSet).get, bq.id)

    def test_binarypackagebuild_cancel(self):
        build = self.factory.makeBinaryPackageBuild()
        bq = build.queueBuild()
        bq.markAsBuilding(self.builder)
        bq.cancel()
        self.assertEqual(BuildStatus.CANCELLING, build.status)
        bq.markAsCancelled()
        self.assertCancelled(build, bq)

    def test_recipebuild_cancel(self):
        build = self.factory.makeSourcePackageRecipeBuild()
        bq = build.queueBuild()
        bq.markAsBuilding(self.builder)
        bq.cancel()
        self.assertEqual(BuildStatus.CANCELLING, build.status)
        bq.markAsCancelled()
        self.assertCancelled(build, bq)


class TestBuildQueueDuration(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def _makeBuildQueue(self):
        """Produce a `BuildQueue` object to test."""
        return self.factory.makeSourcePackageRecipeBuild().queueBuild()

    def test_current_build_duration_not_started(self):
        buildqueue = self._makeBuildQueue()
        self.assertEqual(None, buildqueue.current_build_duration)

    def test_current_build_duration(self):
        buildqueue = removeSecurityProxy(self._makeBuildQueue())
        now = buildqueue._now()
        buildqueue._now = FakeMethod(result=now)
        age = timedelta(minutes=3)
        buildqueue.date_started = now - age

        self.assertEqual(age, buildqueue.current_build_duration)


class TestPlatformData(TestCaseWithFactory):
    """Tests covering the processor/virtualized properties."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up a native x86 build for the test archive."""
        super(TestPlatformData, self).setUp()

        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # First mark all builds in the sample data as already built.
        sample_data = IStore(BinaryPackageBuild).find(BinaryPackageBuild)
        for build in sample_data:
            build.buildstate = BuildStatus.FULLYBUILT
        IStore(BinaryPackageBuild).flush()

        # We test builds that target a primary archive.
        self.non_ppa = self.factory.makeArchive(
            name="primary", purpose=ArchivePurpose.PRIMARY)
        self.non_ppa.require_virtualized = False

        self.builds = []
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())

    def test_JobPlatformSettings(self):
        """The `BuildQueue` instance shares the processor/virtualized
        properties with the associated `Build`."""
        build, bq = find_job(self, 'gedit')

        # Make sure the 'processor' properties are the same.
        self.assertEqual(
            bq.processor, build.processor,
            "The 'processor' property deviates.")

        # Make sure the 'virtualized' properties are the same.
        self.assertEqual(
            bq.virtualized, build.virtualized,
            "The 'virtualized' property deviates.")


class TestBuildQueueManual(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def _makeBuildQueue(self):
        """Produce a `BuildQueue` object to test."""
        return self.factory.makeSourcePackageRecipeBuild().queueBuild()

    def test_manualScore_prevents_rescoring(self):
        # Manually-set scores are fixed.
        buildqueue = self._makeBuildQueue()
        initial_score = buildqueue.lastscore
        buildqueue.manualScore(initial_score + 5000)
        buildqueue.score()
        self.assertEqual(initial_score + 5000, buildqueue.lastscore)
