# Copyright 2022 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""CI builds."""

__all__ = [
    "CIBuild",
]

from datetime import timedelta
from operator import attrgetter, itemgetter

import pytz
from lazr.lifecycle.event import ObjectCreatedEvent
from storm.databases.postgres import JSON
from storm.locals import Bool, DateTime, Desc, Int, Reference, Store, Unicode
from storm.store import EmptyResultSet
from zope.component import getUtility
from zope.event import notify
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildQueueStatus,
    BuildStatus,
)
from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJob,
    SpecificBuildFarmJobSourceMixin,
)
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.buildmaster.model.packagebuild import PackageBuildMixin
from lp.code.errors import GitRepositoryBlobNotFound, GitRepositoryScanFault
from lp.code.interfaces.cibuild import (
    CannotFetchConfiguration,
    CannotParseConfiguration,
    CIBuildAlreadyRequested,
    CIBuildDisallowedArchitecture,
    ICIBuild,
    ICIBuildSet,
    MissingConfiguration,
)
from lp.code.interfaces.githosting import IGitHostingClient
from lp.code.interfaces.gitrepository import IGitRepository
from lp.code.interfaces.revisionstatus import (
    IRevisionStatusArtifactSet,
    IRevisionStatusReportSet,
)
from lp.code.model.gitref import GitRef
from lp.code.model.lpcraft import load_configuration
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.sourcepackage import SourcePackageType
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.config import config
from lp.services.database.bulk import load_related
from lp.services.database.constants import DEFAULT
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import IMasterStore, IStore
from lp.services.database.stormbase import StormBase
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.librarian.model import LibraryFileAlias, LibraryFileContent
from lp.services.macaroons.interfaces import (
    NO_USER,
    BadMacaroonContext,
    IMacaroonIssuer,
)
from lp.services.macaroons.model import MacaroonIssuerBase
from lp.services.propertycache import cachedproperty
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


def get_stages(configuration):
    """Extract the job stages for this configuration."""
    stages = []
    if not configuration.pipeline:
        raise CannotBuild("No pipeline stages defined")
    for stage in configuration.pipeline:
        jobs = []
        for job_name in stage:
            if job_name not in configuration.jobs:
                raise CannotBuild("No job definition for %r" % job_name)
            for i in range(len(configuration.jobs[job_name])):
                jobs.append((job_name, i))
        stages.append(jobs)
    return stages


def determine_DASes_to_build(configuration, logger=None):
    """Generate distroarchseries to build for this configuration."""
    architectures_by_series = {}
    for stage in configuration.pipeline:
        for job_name in stage:
            if job_name not in configuration.jobs:
                if logger is not None:
                    logger.error("No job definition for %r", job_name)
                continue
            for job in configuration.jobs[job_name]:
                for architecture in job["architectures"]:
                    architectures_by_series.setdefault(
                        job["series"], set()
                    ).add(architecture)
    # XXX cjwatson 2022-01-21: We have to hardcode Ubuntu for now, since
    # the .launchpad.yaml format doesn't currently support other
    # distributions (although nor does the Launchpad build farm).
    distribution = getUtility(ILaunchpadCelebrities).ubuntu
    for series_name, architecture_names in architectures_by_series.items():
        try:
            series = distribution[series_name]
        except NotFoundError:
            if logger is not None:
                logger.error("Unknown Ubuntu series name %s" % series_name)
            continue
        architectures = {
            das.architecturetag: das for das in series.buildable_architectures
        }
        for architecture_name in architecture_names:
            try:
                das = architectures[architecture_name]
            except KeyError:
                if logger is not None:
                    logger.error(
                        "%s is not a buildable architecture name in "
                        "Ubuntu %s" % (architecture_name, series_name)
                    )
                continue
            yield das


def get_all_commits_for_paths(git_repository, paths):
    return [
        ref.commit_sha1
        for ref in GitRef.findByReposAndPaths(
            [(git_repository, ref_path) for ref_path in paths]
        ).values()
    ]


def parse_configuration(git_repository, blob):
    try:
        return load_configuration(blob)
    except Exception as e:
        # Don't bother logging parsing errors from user-supplied YAML.
        raise CannotParseConfiguration(
            "Cannot parse .launchpad.yaml from %s: %s"
            % (git_repository.unique_name, e)
        )


@implementer(ICIBuild)
class CIBuild(PackageBuildMixin, StormBase):
    """See `ICIBuild`."""

    __storm_table__ = "CIBuild"

    job_type = BuildFarmJobType.CIBUILD

    id = Int(name="id", primary=True)

    git_repository_id = Int(name="git_repository", allow_none=False)
    git_repository = Reference(git_repository_id, "GitRepository.id")

    commit_sha1 = Unicode(name="commit_sha1", allow_none=False)

    distro_arch_series_id = Int(name="distro_arch_series", allow_none=False)
    distro_arch_series = Reference(
        distro_arch_series_id, "DistroArchSeries.id"
    )

    processor_id = Int(name="processor", allow_none=False)
    processor = Reference(processor_id, "Processor.id")

    virtualized = Bool(name="virtualized", allow_none=False)

    date_created = DateTime(
        name="date_created", tzinfo=pytz.UTC, allow_none=False
    )
    date_started = DateTime(
        name="date_started", tzinfo=pytz.UTC, allow_none=True
    )
    date_finished = DateTime(
        name="date_finished", tzinfo=pytz.UTC, allow_none=True
    )
    date_first_dispatched = DateTime(
        name="date_first_dispatched", tzinfo=pytz.UTC, allow_none=True
    )

    builder_id = Int(name="builder", allow_none=True)
    builder = Reference(builder_id, "Builder.id")

    status = DBEnum(name="status", enum=BuildStatus, allow_none=False)

    log_id = Int(name="log", allow_none=True)
    log = Reference(log_id, "LibraryFileAlias.id")

    upload_log_id = Int(name="upload_log", allow_none=True)
    upload_log = Reference(upload_log_id, "LibraryFileAlias.id")

    dependencies = Unicode(name="dependencies", allow_none=True)

    failure_count = Int(name="failure_count", allow_none=False)

    build_farm_job_id = Int(name="build_farm_job", allow_none=False)
    build_farm_job = Reference(build_farm_job_id, "BuildFarmJob.id")

    _jobs = JSON(name="jobs", allow_none=True)

    def __init__(
        self,
        build_farm_job,
        git_repository,
        commit_sha1,
        distro_arch_series,
        processor,
        virtualized,
        stages,
        date_created=DEFAULT,
    ):
        """Construct a `CIBuild`."""
        super().__init__()
        self.build_farm_job = build_farm_job
        self.git_repository = git_repository
        self.commit_sha1 = commit_sha1
        self.distro_arch_series = distro_arch_series
        self.processor = processor
        self.virtualized = virtualized
        self._jobs = {"stages": stages}
        self.date_created = date_created
        self.status = BuildStatus.NEEDSBUILD

    @property
    def is_private(self):
        """See `IBuildFarmJob`."""
        return self.git_repository.private

    # See `IPrivacy`.
    private = is_private

    def __repr__(self):
        return "<CIBuild %s/+build/%s>" % (
            self.git_repository.unique_name,
            self.id,
        )

    @property
    def title(self):
        """See `IBuildFarmJob`."""
        return "%s CI build of %s:%s" % (
            self.distro_arch_series.architecturetag,
            self.git_repository.unique_name,
            self.commit_sha1,
        )

    @property
    def distribution(self):
        """See `IPackageBuild`."""
        return self.distro_arch_series.distroseries.distribution

    @property
    def distro_series(self):
        """See `IPackageBuild`."""
        return self.distro_arch_series.distroseries

    @property
    def pocket(self):
        """See `IPackageBuild`."""
        return PackagePublishingPocket.UPDATES

    @property
    def arch_tag(self):
        """See `ICIBuild`."""
        return self.distro_arch_series.architecturetag

    @property
    def archive(self):
        """See `IPackageBuild`."""
        return self.distribution.main_archive

    @property
    def score(self):
        """See `ICIBuild`."""
        if self.buildqueue_record is None:
            return None
        else:
            return self.buildqueue_record.lastscore

    @property
    def can_be_retried(self):
        """See `IBuildFarmJob`."""
        # First check that the behaviour would accept the build if it
        # succeeded.
        if self.distro_series.status == SeriesStatus.OBSOLETE:
            return False
        return super().can_be_retried

    def calculateScore(self):
        # Low latency is especially useful for CI builds, so score these
        # above bulky things like live filesystem builds, but below
        # important things like builds of proposed Ubuntu stable updates.
        # See https://help.launchpad.net/Packaging/BuildScores.
        return 2600

    def getMedianBuildDuration(self):
        """Return the median duration of our recent successful builds."""
        store = IStore(self)
        result = store.find(
            (CIBuild.date_started, CIBuild.date_finished),
            CIBuild.git_repository == self.git_repository_id,
            CIBuild.distro_arch_series == self.distro_arch_series_id,
            CIBuild.status == BuildStatus.FULLYBUILT,
        )
        result.order_by(Desc(CIBuild.date_finished))
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
        return timedelta(minutes=10)

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

    @cachedproperty
    def eta(self):
        """The datetime when the build job is estimated to complete.

        This is the BuildQueue.estimated_duration plus the
        Job.date_started or BuildQueue.getEstimatedJobStartTime.
        """
        if self.buildqueue_record is None:
            return None
        queue_record = self.buildqueue_record
        if queue_record.status == BuildQueueStatus.WAITING:
            start_time = queue_record.getEstimatedJobStartTime()
        else:
            start_time = queue_record.date_started
        if start_time is None:
            return None
        duration = queue_record.estimated_duration
        return start_time + duration

    @property
    def estimate(self):
        """If true, the date value is an estimate."""
        if self.date_finished is not None:
            return False
        return self.eta is not None

    @property
    def date(self):
        """The date when the build completed or is estimated to complete."""
        if self.estimate:
            return self.eta
        return self.date_finished

    def getConfiguration(self, logger=None):
        """See `ICIBuild`."""
        try:
            paths = (".launchpad.yaml",)
            for path in paths:
                try:
                    blob = self.git_repository.getBlob(
                        path, rev=self.commit_sha1
                    )
                    break
                except GitRepositoryBlobNotFound:
                    pass
            else:
                if logger is not None:
                    logger.exception(
                        "Cannot find .launchpad.yaml in %s"
                        % self.git_repository.unique_name
                    )
                raise MissingConfiguration(self.git_repository.unique_name)
        except GitRepositoryScanFault as e:
            msg = "Failed to get .launchpad.yaml from %s"
            if logger is not None:
                logger.exception(msg, self.git_repository.unique_name)
            raise CannotFetchConfiguration(
                "%s: %s" % (msg % self.git_repository.unique_name, e)
            )
        return parse_configuration(self.git_repository, blob)

    @property
    def stages(self):
        """See `ICIBuild`."""
        if self._jobs is None:
            return []
        return self._jobs.get("stages", [])

    @property
    def results(self):
        """See `ICIBuild`."""
        if self._jobs is None:
            return {}
        return self._jobs.get("results", {})

    @results.setter
    def results(self, results):
        """See `ICIBuild`."""
        if self._jobs is None:
            self._jobs = {}
        self._jobs["results"] = results

    def getOrCreateRevisionStatusReport(self, job_id):
        """See `ICIBuild`."""
        report = getUtility(IRevisionStatusReportSet).getByCIBuildAndTitle(
            self, job_id
        )
        if report is None:
            # The report should normally exist, since
            # lp.code.model.cibuild.CIBuildSet._tryToRequestBuild creates
            # report rows for the jobs it expects to run, but for robustness
            # it's a good idea to ensure its existence here.
            report = getUtility(IRevisionStatusReportSet).new(
                creator=self.git_repository.owner,
                title=job_id,
                git_repository=self.git_repository,
                commit_sha1=self.commit_sha1,
                ci_build=self,
            )
        return report

    def getFileByName(self, filename):
        """See `ICIBuild`."""
        if filename.endswith(".txt.gz"):
            file_object = self.log
        elif filename.endswith("_log.txt"):
            file_object = self.upload_log
        else:
            file_object = None

        if file_object is not None and file_object.filename == filename:
            return file_object

        raise NotFoundError(filename)

    def getFileUrls(self):
        artifacts = getUtility(IRevisionStatusArtifactSet).findByCIBuild(self)
        load_related(LibraryFileAlias, artifacts, ["library_file_id"])
        artifacts = sorted(
            artifacts, key=attrgetter("library_file.filename", "id")
        )
        return [
            ProxiedLibraryFileAlias(artifact.library_file, artifact).http_url
            for artifact in artifacts
        ]

    def verifySuccessfulUpload(self) -> bool:
        """See `IPackageBuild`."""
        # We have no interesting checks to perform here.
        return True

    def notify(self, extra_info=None):
        """See `IPackageBuild`."""
        from lp.code.mail.cibuild import CIBuildMailer

        if not config.builddmaster.send_build_notification:
            return
        if self.status == BuildStatus.FULLYBUILT:
            return
        mailer = CIBuildMailer.forStatus(self)
        mailer.sendAll()

    @property
    def sourcepackages(self):
        """See `ICIBuild`."""
        releases = IStore(SourcePackageRelease).find(
            (SourcePackageRelease, SourcePackageName),
            SourcePackageRelease.ci_build == self,
            SourcePackageRelease.sourcepackagename == SourcePackageName.id,
        )
        releases = releases.order_by(
            SourcePackageName.name, SourcePackageRelease.id
        )
        return DecoratedResultSet(releases, result_decorator=itemgetter(0))

    @property
    def binarypackages(self):
        """See `ICIBuild`."""
        releases = IStore(BinaryPackageRelease).find(
            (BinaryPackageRelease, BinaryPackageName),
            BinaryPackageRelease.ci_build == self,
            BinaryPackageRelease.binarypackagename == BinaryPackageName.id,
        )
        releases = releases.order_by(
            BinaryPackageName.name, BinaryPackageRelease.id
        )
        return DecoratedResultSet(releases, result_decorator=itemgetter(0))

    def createSourcePackageRelease(
        self,
        distroseries,
        sourcepackagename,
        version,
        creator=None,
        archive=None,
        user_defined_fields=None,
    ):
        """See `ICIBuild`."""
        return distroseries.createUploadedSourcePackageRelease(
            sourcepackagename=sourcepackagename,
            version=version,
            format=SourcePackageType.CI_BUILD,
            # This doesn't really make sense for SPRs created for CI builds,
            # but the column is NOT NULL.  The empty string will do though,
            # since nothing will use this.
            architecturehintlist="",
            creator=creator,
            archive=archive,
            ci_build=self,
            user_defined_fields=user_defined_fields,
        )

    def createBinaryPackageRelease(
        self,
        binarypackagename,
        version,
        summary,
        description,
        binpackageformat,
        architecturespecific,
        installedsize=None,
        homepage=None,
        user_defined_fields=None,
    ):
        """See `ICIBuild`."""
        return BinaryPackageRelease(
            ci_build=self,
            binarypackagename=binarypackagename,
            version=version,
            summary=summary,
            description=description,
            binpackageformat=binpackageformat,
            architecturespecific=architecturespecific,
            installedsize=installedsize,
            homepage=homepage,
            user_defined_fields=user_defined_fields,
        )


@implementer(ICIBuildSet)
class CIBuildSet(SpecificBuildFarmJobSourceMixin):
    def new(
        self,
        git_repository,
        commit_sha1,
        distro_arch_series,
        stages,
        date_created=DEFAULT,
    ):
        """See `ICIBuildSet`."""
        store = IMasterStore(CIBuild)
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            CIBuild.job_type, BuildStatus.NEEDSBUILD, date_created
        )
        cibuild = CIBuild(
            build_farm_job,
            git_repository,
            commit_sha1,
            distro_arch_series,
            distro_arch_series.processor,
            virtualized=True,
            stages=stages,
            date_created=date_created,
        )
        store.add(cibuild)
        store.flush()
        return cibuild

    def _findByGitRepositoryClauses(self, git_repository, commit_sha1s=None):
        """Return a list of Storm clauses to find builds for a repository."""
        clauses = [CIBuild.git_repository == git_repository]
        if commit_sha1s is not None:
            clauses.append(CIBuild.commit_sha1.is_in(commit_sha1s))
        return clauses

    def findByGitRepository(self, git_repository, commit_sha1s=None):
        """See `ICIBuildSet`."""
        clauses = self._findByGitRepositoryClauses(
            git_repository, commit_sha1s=commit_sha1s
        )
        return IStore(CIBuild).find(CIBuild, *clauses)

    def _isBuildableArchitectureAllowed(self, das):
        """Check whether we may build for a buildable `DistroArchSeries`.

        The caller is assumed to have already checked that a suitable chroot
        is available (either directly or via
        `DistroSeries.buildable_architectures`).
        """
        return (
            das.enabled
            # We only support builds on virtualized builders at the moment.
            and das.processor.supports_virtualized
        )

    def _isArchitectureAllowed(self, das, pocket, snap_base=None):
        return das.getChroot(
            pocket=pocket
        ) is not None and self._isBuildableArchitectureAllowed(das)

    def requestBuild(
        self, git_repository, commit_sha1, distro_arch_series, stages
    ):
        """See `ICIBuildSet`."""
        pocket = PackagePublishingPocket.UPDATES
        if not self._isArchitectureAllowed(distro_arch_series, pocket):
            raise CIBuildDisallowedArchitecture(distro_arch_series, pocket)

        result = IStore(CIBuild).find(
            CIBuild,
            CIBuild.git_repository == git_repository,
            CIBuild.commit_sha1 == commit_sha1,
            CIBuild.distro_arch_series == distro_arch_series,
        )
        if not result.is_empty():
            raise CIBuildAlreadyRequested

        build = self.new(
            git_repository, commit_sha1, distro_arch_series, stages
        )
        build.queueBuild()
        notify(ObjectCreatedEvent(build))
        return build

    def _tryToRequestBuild(
        self, git_repository, commit_sha1, configuration, das, stages, logger
    ):
        try:
            if logger is not None:
                logger.info(
                    "Requesting CI build for %s on %s/%s",
                    commit_sha1,
                    das.distroseries.name,
                    das.architecturetag,
                )
            build = self.requestBuild(git_repository, commit_sha1, das, stages)
            # Create reports for each individual job in this build so that
            # they show up as pending in the web UI.  The job names
            # generated here should match those generated by
            # lpbuildd.ci._make_job_id in launchpad-buildd;
            # lp.archiveuploader.ciupload looks for this report and attaches
            # artifacts to it.
            for stage in stages:
                for job_name, i in stage:
                    # XXX cjwatson 2022-03-17: It would be better if we
                    # could set some kind of meaningful description as well.
                    build.getOrCreateRevisionStatusReport(
                        "%s:%s" % (job_name, i)
                    )
        except CIBuildAlreadyRequested:
            pass
        except Exception as e:
            if logger is not None:
                logger.error(
                    "Failed to request CI build for %s on %s/%s: %s",
                    commit_sha1,
                    das.distroseries.name,
                    das.architecturetag,
                    e,
                )

    def requestBuildsForRefs(self, git_repository, ref_paths, logger=None):
        """See `ICIBuildSet`."""
        commit_sha1s = get_all_commits_for_paths(git_repository, ref_paths)
        # getCommits performs a web request!
        commits = getUtility(IGitHostingClient).getCommits(
            git_repository.getInternalPath(),
            commit_sha1s,
            # XXX cjwatson 2022-01-19: We should also fetch
            # debian/.launchpad.yaml (or perhaps make the path a property of
            # the repository) once lpcraft and launchpad-buildd support
            # using alternative paths for builds.
            filter_paths=[".launchpad.yaml"],
            logger=logger,
        )
        for commit in commits:
            try:
                configuration = parse_configuration(
                    git_repository, commit["blobs"][".launchpad.yaml"]
                )
            except CannotParseConfiguration as e:
                if logger is not None:
                    logger.error(e)
                continue
            try:
                stages = get_stages(configuration)
            except CannotBuild as e:
                if logger is not None:
                    logger.error(
                        "Failed to request CI builds for %s: %s",
                        commit["sha1"],
                        e,
                    )
                continue
            for das in determine_DASes_to_build(configuration, logger=logger):
                self._tryToRequestBuild(
                    git_repository,
                    commit["sha1"],
                    configuration,
                    das,
                    stages,
                    logger,
                )

    def getByID(self, build_id):
        """See `ISpecificBuildFarmJobSource`."""
        store = IMasterStore(CIBuild)
        return store.get(CIBuild, build_id)

    def getByBuildFarmJob(self, build_farm_job):
        """See `ISpecificBuildFarmJobSource`."""
        return (
            Store.of(build_farm_job)
            .find(CIBuild, build_farm_job_id=build_farm_job.id)
            .one()
        )

    def preloadBuildsData(self, builds):
        lfas = load_related(LibraryFileAlias, builds, ["log_id"])
        load_related(LibraryFileContent, lfas, ["contentID"])
        distroarchseries = load_related(
            DistroArchSeries, builds, ["distro_arch_series_id"]
        )
        distroseries = load_related(
            DistroSeries, distroarchseries, ["distroseriesID"]
        )
        load_related(Distribution, distroseries, ["distributionID"])

    def getByBuildFarmJobs(self, build_farm_jobs):
        """See `ISpecificBuildFarmJobSource`."""
        if len(build_farm_jobs) == 0:
            return EmptyResultSet()
        rows = Store.of(build_farm_jobs[0]).find(
            CIBuild,
            CIBuild.build_farm_job_id.is_in(bfj.id for bfj in build_farm_jobs),
        )
        return DecoratedResultSet(rows, pre_iter_hook=self.preloadBuildsData)

    def deleteByGitRepository(self, git_repository):
        """See `ICIBuildSet`."""
        # Remove build jobs.  There won't be many queued builds, so we can
        # afford to do this the safe but slow way via BuildQueue.destroySelf
        # rather than in bulk.
        build_clauses = self._findByGitRepositoryClauses(git_repository)
        store = IStore(CIBuild)
        buildqueue_records = store.find(
            BuildQueue,
            BuildQueue._build_farm_job_id == CIBuild.build_farm_job_id,
            *build_clauses,
        )
        for buildqueue_record in buildqueue_records:
            buildqueue_record.destroySelf()
        build_farm_job_ids = list(
            store.find(CIBuild.build_farm_job_id, *build_clauses)
        )
        self.findByGitRepository(git_repository).remove()
        if build_farm_job_ids:
            store.find(
                BuildFarmJob, BuildFarmJob.id.is_in(build_farm_job_ids)
            ).remove()


@implementer(IMacaroonIssuer)
class CIBuildMacaroonIssuer(MacaroonIssuerBase):

    identifier = "ci-build"
    issuable_via_authserver = True

    def checkIssuingContext(self, context, **kwargs):
        """See `MacaroonIssuerBase`.

        For issuing, the context is an `ICIBuild`.
        """
        if not ICIBuild.providedBy(context):
            raise BadMacaroonContext(context)
        return removeSecurityProxy(context).id

    def checkVerificationContext(self, context, **kwargs):
        """See `MacaroonIssuerBase`."""
        if not IGitRepository.providedBy(context):
            raise BadMacaroonContext(context)
        return context

    def verifyPrimaryCaveat(
        self, verified, caveat_value, context, user=None, **kwargs
    ):
        """See `MacaroonIssuerBase`.

        For verification, the context is an `IGitRepository`.  We check that
        the repository or archive is needed to build the `ICIBuild` that is
        the context of the macaroon, and that the context build is currently
        building.
        """
        # CI builds only support free-floating macaroons for Git
        # authentication, not ones bound to a user.
        if user:
            return False
        verified.user = NO_USER

        if context is None:
            # We're only verifying that the macaroon could be valid for some
            # context.
            return True
        if not IGitRepository.providedBy(context):
            return False

        try:
            build_id = int(caveat_value)
        except ValueError:
            return False
        clauses = [
            CIBuild.id == build_id,
            CIBuild.status == BuildStatus.BUILDING,
            CIBuild.git_repository == context,
        ]
        return not IStore(CIBuild).find(CIBuild, *clauses).is_empty()
