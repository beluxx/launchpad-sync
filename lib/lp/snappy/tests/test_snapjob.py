# Copyright 2018-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for snap package jobs."""

__metaclass__ = type

from textwrap import dedent

import six
from testtools.matchers import (
    AfterPreprocessing,
    ContainsDict,
    Equals,
    GreaterThan,
    Is,
    LessThan,
    MatchesAll,
    MatchesSetwise,
    MatchesStructure,
    )

from lp.code.tests.helpers import GitHostingFixture
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.config import config
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import get_transaction_timestamp
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.runner import JobRunner
from lp.services.mail.sendmail import format_address_for_person
from lp.snappy.interfaces.snap import CannotParseSnapcraftYaml
from lp.snappy.interfaces.snapjob import (
    ISnapJob,
    ISnapRequestBuildsJob,
    )
from lp.snappy.model.snapjob import (
    SnapJob,
    SnapJobType,
    SnapRequestBuildsJob,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.layers import ZopelessDatabaseLayer


class TestSnapJob(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_provides_interface(self):
        # `SnapJob` objects provide `ISnapJob`.
        snap = self.factory.makeSnap()
        self.assertProvides(
            SnapJob(snap, SnapJobType.REQUEST_BUILDS, {}), ISnapJob)


class TestSnapRequestBuildsJob(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_provides_interface(self):
        # `SnapRequestBuildsJob` objects provide `ISnapRequestBuildsJob`."""
        snap = self.factory.makeSnap()
        archive = self.factory.makeArchive()
        job = SnapRequestBuildsJob.create(
            snap, snap.registrant, archive, PackagePublishingPocket.RELEASE,
            None)
        self.assertProvides(job, ISnapRequestBuildsJob)

    def test___repr__(self):
        # `SnapRequestBuildsJob` objects have an informative __repr__.
        snap = self.factory.makeSnap()
        archive = self.factory.makeArchive()
        job = SnapRequestBuildsJob.create(
            snap, snap.registrant, archive, PackagePublishingPocket.RELEASE,
            None)
        self.assertEqual(
            "<SnapRequestBuildsJob for ~%s/+snap/%s>" % (
                snap.owner.name, snap.name),
            repr(job))

    def makeSeriesAndProcessors(self, arch_tags):
        distro = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        processors = [
            self.factory.makeProcessor(
                name=arch_tag, supports_virtualized=True)
            for arch_tag in arch_tags]
        for processor in processors:
            das = self.factory.makeDistroArchSeries(
                distroseries=distroseries, architecturetag=processor.name,
                processor=processor)
            das.addOrUpdateChroot(self.factory.makeLibraryFileAlias(
                filename="fake_chroot.tar.gz", db_only=True))
        return distroseries, processors

    def test_run(self):
        # The job requests builds and records the result.
        distroseries, processors = self.makeSeriesAndProcessors(
            ["avr2001", "sparc64", "x32"])
        [git_ref] = self.factory.makeGitRefs()
        snap = self.factory.makeSnap(
            git_ref=git_ref, distroseries=distroseries, processors=processors)
        expected_date_created = get_transaction_timestamp(IStore(snap))
        job = SnapRequestBuildsJob.create(
            snap, snap.registrant, distroseries.main_archive,
            PackagePublishingPocket.RELEASE, {"core": "stable"})
        snapcraft_yaml = dedent("""\
            architectures:
              - build-on: avr2001
              - build-on: x32
            """)
        self.useFixture(GitHostingFixture(blob=snapcraft_yaml))
        with dbuser(config.ISnapRequestBuildsJobSource.dbuser):
            JobRunner([job]).runAll()
        now = get_transaction_timestamp(IStore(snap))
        self.assertEmailQueueLength(0)
        self.assertThat(job, MatchesStructure(
            job=MatchesStructure.byEquality(status=JobStatus.COMPLETED),
            date_created=Equals(expected_date_created),
            date_finished=MatchesAll(
                GreaterThan(expected_date_created), LessThan(now)),
            error_message=Is(None),
            builds=AfterPreprocessing(set, MatchesSetwise(*[
                MatchesStructure(
                    build_request=MatchesStructure.byEquality(id=job.job.id),
                    requester=Equals(snap.registrant),
                    snap=Equals(snap),
                    archive=Equals(distroseries.main_archive),
                    distro_arch_series=Equals(distroseries[arch]),
                    pocket=Equals(PackagePublishingPocket.RELEASE),
                    channels=Equals({"core": "stable"}))
                for arch in ("avr2001", "x32")]))))

    def test_run_with_architectures(self):
        # If the user explicitly requested architectures, the job passes
        # those through when requesting builds, intersecting them with other
        # constraints.
        distroseries, processors = self.makeSeriesAndProcessors(
            ["avr2001", "sparc64", "x32"])
        [git_ref] = self.factory.makeGitRefs()
        snap = self.factory.makeSnap(
            git_ref=git_ref, distroseries=distroseries, processors=processors)
        expected_date_created = get_transaction_timestamp(IStore(snap))
        job = SnapRequestBuildsJob.create(
            snap, snap.registrant, distroseries.main_archive,
            PackagePublishingPocket.RELEASE, {"core": "stable"},
            architectures=["sparc64", "x32"])
        snapcraft_yaml = dedent("""\
            architectures:
              - build-on: avr2001
              - build-on: x32
            """)
        self.useFixture(GitHostingFixture(blob=snapcraft_yaml))
        with dbuser(config.ISnapRequestBuildsJobSource.dbuser):
            JobRunner([job]).runAll()
        now = get_transaction_timestamp(IStore(snap))
        self.assertEmailQueueLength(0)
        self.assertThat(job, MatchesStructure(
            job=MatchesStructure.byEquality(status=JobStatus.COMPLETED),
            date_created=Equals(expected_date_created),
            date_finished=MatchesAll(
                GreaterThan(expected_date_created), LessThan(now)),
            error_message=Is(None),
            builds=AfterPreprocessing(set, MatchesSetwise(
                MatchesStructure(
                    build_request=MatchesStructure.byEquality(id=job.job.id),
                    requester=Equals(snap.registrant),
                    snap=Equals(snap),
                    archive=Equals(distroseries.main_archive),
                    distro_arch_series=Equals(distroseries["x32"]),
                    pocket=Equals(PackagePublishingPocket.RELEASE),
                    channels=Equals({"core": "stable"}))))))

    def test_run_failed(self):
        # A failed run sets the job status to FAILED and records the error
        # message.
        # The job requests builds and records the result.
        distroseries, processors = self.makeSeriesAndProcessors(
            ["avr2001", "sparc64", "x32"])
        [git_ref] = self.factory.makeGitRefs()
        snap = self.factory.makeSnap(
            git_ref=git_ref, distroseries=distroseries, processors=processors)
        expected_date_created = get_transaction_timestamp(IStore(snap))
        job = SnapRequestBuildsJob.create(
            snap, snap.registrant, distroseries.main_archive,
            PackagePublishingPocket.RELEASE, {"core": "stable"})
        self.useFixture(GitHostingFixture()).getBlob.failure = (
            CannotParseSnapcraftYaml("Nonsense on stilts"))
        with dbuser(config.ISnapRequestBuildsJobSource.dbuser):
            JobRunner([job]).runAll()
        now = get_transaction_timestamp(IStore(snap))
        [notification] = self.assertEmailQueueLength(1)
        self.assertThat(dict(notification), ContainsDict({
            "From": Equals(config.canonical.noreply_from_address),
            "To": Equals(format_address_for_person(snap.registrant)),
            "Subject": Equals(
                "Launchpad error while requesting builds of %s" % snap.name),
            }))
        self.assertEqual(
            "Launchpad encountered an error during the following operation: "
            "requesting builds of %s.  Nonsense on stilts" % snap.name,
            six.ensure_text(notification.get_payload(decode=True)))
        self.assertThat(job, MatchesStructure(
            job=MatchesStructure.byEquality(status=JobStatus.FAILED),
            date_created=Equals(expected_date_created),
            date_finished=MatchesAll(
                GreaterThan(expected_date_created), LessThan(now)),
            error_message=Equals("Nonsense on stilts"),
            builds=AfterPreprocessing(set, MatchesSetwise())))

    def test_run_failed_no_such_snap_base(self):
        # A run where the snap base does not exist sets the job status to
        # FAILED and records the error message.
        [git_ref] = self.factory.makeGitRefs()
        snap = self.factory.makeSnap(git_ref=git_ref)
        expected_date_created = get_transaction_timestamp(IStore(snap))
        job = SnapRequestBuildsJob.create(
            snap, snap.registrant, snap.distro_series.main_archive,
            PackagePublishingPocket.RELEASE, None)
        snapcraft_yaml = "base: nonexistent\n"
        self.useFixture(GitHostingFixture(blob=snapcraft_yaml))
        with dbuser(config.ISnapRequestBuildsJobSource.dbuser):
            JobRunner([job]).runAll()
        now = get_transaction_timestamp(IStore(snap))
        [notification] = self.assertEmailQueueLength(1)
        self.assertThat(dict(notification), ContainsDict({
            "From": Equals(config.canonical.noreply_from_address),
            "To": Equals(format_address_for_person(snap.registrant)),
            "Subject": Equals(
                "Launchpad error while requesting builds of %s" % snap.name),
            }))
        self.assertEqual(
            "Launchpad encountered an error during the following operation: "
            "requesting builds of %s.  No such base: "
            "'nonexistent'." % snap.name,
            six.ensure_text(notification.get_payload(decode=True)))
        self.assertThat(job, MatchesStructure(
            job=MatchesStructure.byEquality(status=JobStatus.FAILED),
            date_created=Equals(expected_date_created),
            date_finished=MatchesAll(
                GreaterThan(expected_date_created), LessThan(now)),
            error_message=Equals("No such base: 'nonexistent'."),
            builds=AfterPreprocessing(set, MatchesSetwise())))
