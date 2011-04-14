# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from storm.exceptions import IntegrityError
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import flush_database_caches
from canonical.launchpad.scripts.tests import run_script
from canonical.testing import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.distributionjob import (
    IInitialiseDistroSeriesJobSource,
    )
from lp.soyuz.interfaces.packageset import IPackagesetSet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.initialisedistroseriesjob import InitialiseDistroSeriesJob
from lp.soyuz.scripts.initialise_distroseries import InitialisationError
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class InitialiseDistroSeriesJobTests(TestCaseWithFactory):
    """Test case for InitialiseDistroSeriesJob."""

    layer = DatabaseFunctionalLayer

    @property
    def job_source(self):
        return getUtility(IInitialiseDistroSeriesJobSource)

    def test_getOopsVars(self):
        parent = self.factory.makeDistroSeries()
        distroseries = self.factory.makeDistroSeries()
        job = self.job_source.create(parent, distroseries)
        vars = job.getOopsVars()
        naked_job = removeSecurityProxy(job)
        self.assertIn(
            ('distribution_id', distroseries.distribution.id), vars)
        self.assertIn(('distroseries_id', distroseries.id), vars)
        self.assertIn(('distribution_job_id', naked_job.context.id), vars)
        self.assertIn(('parent_distroseries_id', parent.id), vars)

    def _getJobs(self):
        """Return the pending InitialiseDistroSeriesJobs as a list."""
        return list(InitialiseDistroSeriesJob.iterReady())

    def _getJobCount(self):
        """Return the number of InitialiseDistroSeriesJobs in the
        queue."""
        return len(self._getJobs())

    def test_create_only_creates_one(self):
        parent = self.factory.makeDistroSeries()
        distroseries = self.factory.makeDistroSeries()
        # If there's already a InitialiseDistroSeriesJob for a
        # DistroSeries, InitialiseDistroSeriesJob.create() won't create
        # a new one.
        self.job_source.create(parent, distroseries)
        self.job_source.create(parent, distroseries)
        self.assertRaises(IntegrityError, flush_database_caches)

    def test_run_with_parent_series_already_set(self):
        # InitialisationError is raised if the parent series is already set on
        # the child.
        parent = self.factory.makeDistroSeries()
        distroseries = self.factory.makeDistroSeries(parent_series=parent)
        job = self.job_source.create(parent, distroseries)
        expected_message = (
            "DistroSeries {child.name} has been initialized; it already "
            "derives from {parent.distribution.name}/{parent.name}.").format(
            parent=parent, child=distroseries)
        self.assertRaisesWithContent(
            InitialisationError, expected_message, job.run)

    def test_arguments(self):
        """Test that InitialiseDistroSeriesJob specified with arguments can
        be gotten out again."""
        parent = self.factory.makeDistroSeries()
        distroseries = self.factory.makeDistroSeries()
        arches = (u'i386', u'amd64')
        packagesets = (u'foo', u'bar', u'baz')

        job = self.job_source.create(
            parent, distroseries, arches, packagesets)

        naked_job = removeSecurityProxy(job)
        self.assertEqual(naked_job.distroseries, distroseries)
        self.assertEqual(naked_job.arches, arches)
        self.assertEqual(naked_job.packagesets, packagesets)
        self.assertEqual(naked_job.rebuild, False)
        self.assertEqual(naked_job.metadata["parent"], parent.id)

    def test_parent(self):
        parent = self.factory.makeDistroSeries()
        distroseries = self.factory.makeDistroSeries()
        job = self.job_source.create(parent, distroseries)
        naked_job = removeSecurityProxy(job)
        self.assertEqual(parent, naked_job.parent)


class InitialiseDistroSeriesJobTestsWithPackages(TestCaseWithFactory):
    """Test case for InitialiseDistroSeriesJob."""

    layer = LaunchpadZopelessLayer

    @property
    def job_source(self):
        return getUtility(IInitialiseDistroSeriesJobSource)

    def _create_child(self):
        pf = self.factory.makeProcessorFamily()
        pf.addProcessor('x86', '', '')
        parent = self.factory.makeDistroSeries()
        parent_das = self.factory.makeDistroArchSeries(
            distroseries=parent, processorfamily=pf)
        lf = self.factory.makeLibraryFileAlias()
        # Since the LFA needs to be in the librarian, commit.
        transaction.commit()
        parent_das.addOrUpdateChroot(lf)
        parent_das.supports_virtualized = True
        parent.nominatedarchindep = parent_das
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        packages = {'udev': '0.1-1', 'libc6': '2.8-1'}
        for package in packages.keys():
            publisher.getPubBinaries(
                distroseries=parent, binaryname=package,
                version=packages[package],
                status=PackagePublishingStatus.PUBLISHED)
        test1 = getUtility(IPackagesetSet).new(
            u'test1', u'test 1 packageset', parent.owner,
            distroseries=parent)
        test1.addSources('udev')
        parent.updatePackageCount()
        child = self.factory.makeDistroSeries()
        # Make sure everything hits the database, switching db users aborts.
        transaction.commit()
        return parent, child

    def test_job(self):
        parent, child = self._create_child()
        job = self.job_source.create(parent, child)
        self.layer.switchDbUser('initialisedistroseries')

        job.run()
        child.updatePackageCount()
        self.assertEqual(parent.sourcecount, child.sourcecount)
        self.assertEqual(parent.binarycount, child.binarycount)

    def test_job_with_arguments(self):
        parent, child = self._create_child()
        arch = parent.nominatedarchindep.architecturetag
        job = self.job_source.create(
            parent, child, packagesets=('test1',), arches=(arch,),
            rebuild=True)
        self.layer.switchDbUser('initialisedistroseries')

        job.run()
        child.updatePackageCount()
        builds = child.getBuildRecords(
            build_state=BuildStatus.NEEDSBUILD,
            pocket=PackagePublishingPocket.RELEASE)
        self.assertEqual(child.sourcecount, 1)
        self.assertEqual(child.binarycount, 0)
        self.assertEqual(builds.count(), 1)

    def test_cronscript(self):
        run_script(
            'cronscripts/run_jobs.py', ['-v', 'initialisedistroseries'])
