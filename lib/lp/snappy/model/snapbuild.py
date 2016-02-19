# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'SnapBuild',
    'SnapFile',
    ]

from datetime import timedelta

import pytz
from storm.locals import (
    Bool,
    DateTime,
    Desc,
    Int,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from storm.store import EmptyResultSet
from zope.component import getUtility
from zope.component.interfaces import ObjectEvent
from zope.event import notify
from zope.interface import implementer

from lp.app.errors import NotFoundError
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.model.buildfarmjob import SpecificBuildFarmJobSourceMixin
from lp.buildmaster.model.packagebuild import PackageBuildMixin
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.person import Person
from lp.services.config import config
from lp.services.database.bulk import load_related
from lp.services.database.constants import DEFAULT
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.features import getFeatureFlag
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.librarian.model import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from lp.snappy.interfaces.snap import (
    ISnapSet,
    SNAP_FEATURE_FLAG,
    SnapFeatureDisabled,
    )
from lp.snappy.interfaces.snapbuild import (
    ISnapBuild,
    ISnapBuildSet,
    ISnapBuildStatusChangedEvent,
    ISnapFile,
    )
from lp.snappy.mail.snapbuild import SnapBuildMailer
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.distroarchseries import DistroArchSeries


@implementer(ISnapBuildStatusChangedEvent)
class SnapBuildStatusChangedEvent(ObjectEvent):
    """See `ISnapBuildStatusChangedEvent`."""


@implementer(ISnapFile)
class SnapFile(Storm):
    """See `ISnap`."""

    __storm_table__ = 'SnapFile'

    id = Int(name='id', primary=True)

    snapbuild_id = Int(name='snapbuild', allow_none=False)
    snapbuild = Reference(snapbuild_id, 'SnapBuild.id')

    libraryfile_id = Int(name='libraryfile', allow_none=False)
    libraryfile = Reference(libraryfile_id, 'LibraryFileAlias.id')

    def __init__(self, snapbuild, libraryfile):
        """Construct a `SnapFile`."""
        super(SnapFile, self).__init__()
        self.snapbuild = snapbuild
        self.libraryfile = libraryfile


@implementer(ISnapBuild)
class SnapBuild(PackageBuildMixin, Storm):
    """See `ISnapBuild`."""

    __storm_table__ = 'SnapBuild'

    job_type = BuildFarmJobType.SNAPBUILD

    id = Int(name='id', primary=True)

    build_farm_job_id = Int(name='build_farm_job', allow_none=False)
    build_farm_job = Reference(build_farm_job_id, 'BuildFarmJob.id')

    requester_id = Int(name='requester', allow_none=False)
    requester = Reference(requester_id, 'Person.id')

    snap_id = Int(name='snap', allow_none=False)
    snap = Reference(snap_id, 'Snap.id')

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    distro_arch_series_id = Int(name='distro_arch_series', allow_none=False)
    distro_arch_series = Reference(
        distro_arch_series_id, 'DistroArchSeries.id')

    pocket = DBEnum(enum=PackagePublishingPocket, allow_none=False)

    processor_id = Int(name='processor', allow_none=False)
    processor = Reference(processor_id, 'Processor.id')
    virtualized = Bool(name='virtualized')

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_started = DateTime(name='date_started', tzinfo=pytz.UTC)
    date_finished = DateTime(name='date_finished', tzinfo=pytz.UTC)
    date_first_dispatched = DateTime(
        name='date_first_dispatched', tzinfo=pytz.UTC)

    builder_id = Int(name='builder')
    builder = Reference(builder_id, 'Builder.id')

    status = DBEnum(name='status', enum=BuildStatus, allow_none=False)

    log_id = Int(name='log')
    log = Reference(log_id, 'LibraryFileAlias.id')

    upload_log_id = Int(name='upload_log')
    upload_log = Reference(upload_log_id, 'LibraryFileAlias.id')

    dependencies = Unicode(name='dependencies')

    failure_count = Int(name='failure_count', allow_none=False)

    def __init__(self, build_farm_job, requester, snap, archive,
                 distro_arch_series, pocket, processor, virtualized,
                 date_created):
        """Construct a `SnapBuild`."""
        if not getFeatureFlag(SNAP_FEATURE_FLAG):
            raise SnapFeatureDisabled
        super(SnapBuild, self).__init__()
        self.build_farm_job = build_farm_job
        self.requester = requester
        self.snap = snap
        self.archive = archive
        self.distro_arch_series = distro_arch_series
        self.pocket = pocket
        self.processor = processor
        self.virtualized = virtualized
        self.date_created = date_created
        self.status = BuildStatus.NEEDSBUILD

    @property
    def is_private(self):
        """See `IBuildFarmJob`."""
        return (
            self.snap.private or
            self.snap.owner.private or
            self.archive.private
        )

    @property
    def title(self):
        das = self.distro_arch_series
        name = self.snap.name
        return "%s build of %s snap package in %s %s" % (
            das.architecturetag, name, das.distroseries.distribution.name,
            das.distroseries.getSuite(self.pocket))

    @property
    def distribution(self):
        """See `IPackageBuild`."""
        return self.distro_arch_series.distroseries.distribution

    @property
    def distro_series(self):
        """See `IPackageBuild`."""
        return self.distro_arch_series.distroseries

    @property
    def current_component(self):
        component = self.archive.default_component
        if component is not None:
            return component
        else:
            # XXX cjwatson 2015-07-17: Hardcode to multiverse for the time
            # being.
            return getUtility(IComponentSet)["multiverse"]

    @property
    def score(self):
        """See `ISnapBuild`."""
        if self.buildqueue_record is None:
            return None
        else:
            return self.buildqueue_record.lastscore

    @property
    def can_be_rescored(self):
        """See `ISnapBuild`."""
        return (
            self.buildqueue_record is not None and
            self.status is BuildStatus.NEEDSBUILD)

    @property
    def can_be_cancelled(self):
        """See `ISnapBuild`."""
        if not self.buildqueue_record:
            return False

        cancellable_statuses = [
            BuildStatus.BUILDING,
            BuildStatus.NEEDSBUILD,
            ]
        return self.status in cancellable_statuses

    def rescore(self, score):
        """See `ISnapBuild`."""
        assert self.can_be_rescored, "Build %s cannot be rescored" % self.id
        self.buildqueue_record.manualScore(score)

    def cancel(self):
        """See `ISnapBuild`."""
        if not self.can_be_cancelled:
            return
        # BuildQueue.cancel() will decide whether to go straight to
        # CANCELLED, or go through CANCELLING to let buildd-manager clean up
        # the slave.
        self.buildqueue_record.cancel()

    def calculateScore(self):
        return 2505 + self.archive.relative_build_score

    def getMedianBuildDuration(self):
        """Return the median duration of our successful builds."""
        store = IStore(self)
        result = store.find(
            (SnapBuild.date_started, SnapBuild.date_finished),
            SnapBuild.snap == self.snap_id,
            SnapBuild.distro_arch_series == self.distro_arch_series_id,
            SnapBuild.status == BuildStatus.FULLYBUILT)
        result.order_by(Desc(SnapBuild.date_finished))
        durations = [row[1] - row[0] for row in result[:9]]
        if len(durations) == 0:
            return None
        durations.sort()
        return durations[len(durations) // 2]

    def estimateDuration(self):
        """See `IBuildFarmJob`."""
        median = self.getMedianBuildDuration()
        if median is not None:
            return median
        return timedelta(minutes=30)

    def getFiles(self):
        """See `ISnapBuild`."""
        result = Store.of(self).find(
            (SnapFile, LibraryFileAlias, LibraryFileContent),
            SnapFile.snapbuild == self.id,
            LibraryFileAlias.id == SnapFile.libraryfile_id,
            LibraryFileContent.id == LibraryFileAlias.contentID)
        return result.order_by([LibraryFileAlias.filename, SnapFile.id])

    def getFileByName(self, filename):
        """See `ISnapBuild`."""
        if filename.endswith(".txt.gz"):
            file_object = self.log
        elif filename.endswith("_log.txt"):
            file_object = self.upload_log
        else:
            file_object = Store.of(self).find(
                LibraryFileAlias,
                SnapFile.snapbuild == self.id,
                LibraryFileAlias.id == SnapFile.libraryfile_id,
                LibraryFileAlias.filename == filename).one()

        if file_object is not None and file_object.filename == filename:
            return file_object

        raise NotFoundError(filename)

    def addFile(self, lfa):
        """See `ISnapBuild`."""
        snapfile = SnapFile(snapbuild=self, libraryfile=lfa)
        IMasterStore(SnapFile).add(snapfile)
        return snapfile

    def verifySuccessfulUpload(self):
        """See `IPackageBuild`."""
        return not self.getFiles().is_empty()

    def updateStatus(self, status, builder=None, slave_status=None,
                     date_started=None, date_finished=None,
                     force_invalid_transition=False):
        """See `IBuildFarmJob`."""
        super(SnapBuild, self).updateStatus(
            status, builder=builder, slave_status=slave_status,
            date_started=date_started, date_finished=date_finished,
            force_invalid_transition=force_invalid_transition)
        notify(SnapBuildStatusChangedEvent(self))

    def notify(self, extra_info=None):
        """See `IPackageBuild`."""
        if not config.builddmaster.send_build_notification:
            return
        if self.status == BuildStatus.FULLYBUILT:
            return
        mailer = SnapBuildMailer.forStatus(self)
        mailer.sendAll()

    def lfaUrl(self, lfa):
        """Return the URL for a LibraryFileAlias in this context."""
        if lfa is None:
            return None
        return ProxiedLibraryFileAlias(lfa, self).http_url

    @property
    def log_url(self):
        """See `IBuildFarmJob`."""
        return self.lfaUrl(self.log)

    @property
    def upload_log_url(self):
        """See `IPackageBuild`."""
        return self.lfaUrl(self.upload_log)

    def getFileUrls(self):
        return [self.lfaUrl(lfa) for _, lfa, _ in self.getFiles()]


@implementer(ISnapBuildSet)
class SnapBuildSet(SpecificBuildFarmJobSourceMixin):

    def new(self, requester, snap, archive, distro_arch_series, pocket,
            date_created=DEFAULT):
        """See `ISnapBuildSet`."""
        store = IMasterStore(SnapBuild)
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            SnapBuild.job_type, BuildStatus.NEEDSBUILD, date_created, None,
            archive)
        snapbuild = SnapBuild(
            build_farm_job, requester, snap, archive, distro_arch_series,
            pocket, distro_arch_series.processor,
            not distro_arch_series.processor.supports_nonvirtualized
            or snap.require_virtualized or archive.require_virtualized,
            date_created)
        store.add(snapbuild)
        return snapbuild

    def getByID(self, build_id):
        """See `ISpecificBuildFarmJobSource`."""
        store = IMasterStore(SnapBuild)
        return store.get(SnapBuild, build_id)

    def getByBuildFarmJob(self, build_farm_job):
        """See `ISpecificBuildFarmJobSource`."""
        return Store.of(build_farm_job).find(
            SnapBuild, build_farm_job_id=build_farm_job.id).one()

    def preloadBuildsData(self, builds):
        # Circular import.
        from lp.snappy.model.snap import Snap
        load_related(Person, builds, ["requester_id"])
        load_related(LibraryFileAlias, builds, ["log_id"])
        archives = load_related(Archive, builds, ["archive_id"])
        load_related(Person, archives, ["ownerID"])
        distroarchseries = load_related(
            DistroArchSeries, builds, ['distro_arch_series_id'])
        distroseries = load_related(
            DistroSeries, distroarchseries, ['distroseriesID'])
        load_related(Distribution, distroseries, ['distributionID'])
        snaps = load_related(Snap, builds, ["snap_id"])
        getUtility(ISnapSet).preloadDataForSnaps(snaps)

    def getByBuildFarmJobs(self, build_farm_jobs):
        """See `ISpecificBuildFarmJobSource`."""
        if len(build_farm_jobs) == 0:
            return EmptyResultSet()
        rows = Store.of(build_farm_jobs[0]).find(
            SnapBuild, SnapBuild.build_farm_job_id.is_in(
                bfj.id for bfj in build_farm_jobs))
        return DecoratedResultSet(rows, pre_iter_hook=self.preloadBuildsData)
