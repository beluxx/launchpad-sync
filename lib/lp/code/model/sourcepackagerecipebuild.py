# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation code for source package builds."""

__all__ = [
    'SourcePackageRecipeBuild',
    ]

from datetime import timedelta
import logging

from psycopg2 import ProgrammingError
import pytz
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Storm,
    Unicode,
    )
from storm.store import (
    EmptyResultSet,
    Store,
    )
from zope.component import getUtility
from zope.interface import (
    implementer,
    provider,
    )

from lp.app.errors import NotFoundError
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJob,
    SpecificBuildFarmJobSourceMixin,
    )
from lp.buildmaster.model.packagebuild import PackageBuildMixin
from lp.code.errors import (
    BuildAlreadyPending,
    BuildNotAllowedForDistro,
    )
from lp.code.interfaces.sourcepackagerecipe import (
    IRecipeBranchSource,
    ISourcePackageRecipeDataSource,
    )
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuild,
    ISourcePackageRecipeBuildSource,
    )
from lp.code.mail.sourcepackagerecipebuild import (
    SourcePackageRecipeBuildMailer,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.person import Person
from lp.services.database.bulk import load_related
from lp.services.database.constants import UTC_NOW
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.soyuz.interfaces.archive import CannotUploadToArchive
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


@implementer(ISourcePackageRecipeBuild)
@provider(ISourcePackageRecipeBuildSource)
class SourcePackageRecipeBuild(SpecificBuildFarmJobSourceMixin,
                               PackageBuildMixin, Storm):

    __storm_table__ = 'SourcePackageRecipeBuild'

    job_type = BuildFarmJobType.RECIPEBRANCHBUILD

    id = Int(primary=True)

    build_farm_job_id = Int(name='build_farm_job', allow_none=False)
    build_farm_job = Reference(build_farm_job_id, BuildFarmJob.id)

    @property
    def binary_builds(self):
        """See `ISourcePackageRecipeBuild`."""
        return Store.of(self).find(
            BinaryPackageBuild,
            BinaryPackageBuild.source_package_release ==
                SourcePackageRelease.id,
            SourcePackageRelease.source_package_recipe_build == self.id)

    @property
    def current_component(self):
        # Only PPAs currently have a sane default component at the
        # moment, but we only support recipes for PPAs.
        component = self.archive.default_component
        assert component is not None
        return component

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    distroseries_id = Int(name='distroseries', allow_none=True)
    distroseries = Reference(distroseries_id, 'DistroSeries.id')
    distro_series = distroseries

    pocket = DBEnum(
        name='pocket', enum=PackagePublishingPocket, allow_none=False)

    @property
    def distribution(self):
        """See `IPackageBuild`."""
        return self.distroseries.distribution

    recipe_id = Int(name='recipe')
    recipe = Reference(recipe_id, 'SourcePackageRecipe.id')

    requester_id = Int(name='requester', allow_none=False)
    requester = Reference(requester_id, 'Person.id')

    upload_log_id = Int(name='upload_log')
    upload_log = Reference(upload_log_id, 'LibraryFileAlias.id')

    dependencies = Unicode(name='dependencies')

    processor_id = Int(name='processor')
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

    failure_count = Int(name='failure_count', allow_none=False)

    manifest = Reference(
        id, 'SourcePackageRecipeData.sourcepackage_recipe_build_id',
        on_remote=True)

    def setManifestText(self, text):
        if text is None:
            if self.manifest is not None:
                IStore(self.manifest).remove(self.manifest)
        elif self.manifest is None:
            getUtility(ISourcePackageRecipeDataSource).createManifestFromText(
                text, self)
        else:
            parsed, recipe_branch_type = (
                getUtility(IRecipeBranchSource).getParsedRecipe(text))
            self.manifest.setRecipe(parsed, recipe_branch_type)

    def getManifestText(self):
        if self.manifest is None:
            return None
        return str(self.manifest.getRecipe())

    @property
    def source_package_release(self):
        """See `ISourcePackageRecipeBuild`."""
        return Store.of(self).find(
            SourcePackageRelease, source_package_recipe_build=self).one()

    @property
    def title(self):
        if self.recipe is None:
            branch_name = 'deleted'
        else:
            branch_name = self.recipe.base.unique_name
        return '%s recipe build in %s %s' % (
            branch_name, self.distribution.name, self.distroseries.name)

    def __init__(self, build_farm_job, distroseries, recipe, requester,
                 archive, pocket, date_created):
        """Construct a SourcePackageRecipeBuild."""
        processor = distroseries.nominatedarchindep.processor
        super(SourcePackageRecipeBuild, self).__init__()
        self.build_farm_job = build_farm_job
        self.distroseries = distroseries
        self.recipe = recipe
        self.requester = requester
        self.archive = archive
        self.pocket = pocket
        self.status = BuildStatus.NEEDSBUILD
        self.processor = processor
        self.virtualized = True
        if date_created is not None:
            self.date_created = date_created

    @classmethod
    def new(cls, distroseries, recipe, requester, archive, pocket=None,
            date_created=None, duration=None):
        """See `ISourcePackageRecipeBuildSource`."""
        store = IMasterStore(SourcePackageRecipeBuild)
        if pocket is None:
            pocket = PackagePublishingPocket.RELEASE
        if date_created is None:
            date_created = UTC_NOW
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            cls.job_type, BuildStatus.NEEDSBUILD, date_created, None, archive)
        spbuild = cls(
            build_farm_job, distroseries, recipe, requester, archive, pocket,
            date_created)
        store.add(spbuild)
        return spbuild

    @staticmethod
    def makeDailyBuilds(logger=None):
        from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
        recipes = SourcePackageRecipe.findStaleDailyBuilds()
        if logger is None:
            logger = logging.getLogger()
        builds = []
        for recipe in recipes:
            recipe.is_stale = False
            logger.debug(
                'Recipe %s/%s is stale', recipe.owner.name, recipe.name)
            if recipe.daily_build_archive is None:
                logger.debug(' - No daily build archive specified.')
                continue
            for distroseries in recipe.distroseries:
                series_name = distroseries.named_version
                try:
                    build = recipe.requestBuild(
                        recipe.daily_build_archive, recipe.owner,
                        distroseries, PackagePublishingPocket.RELEASE)
                except BuildAlreadyPending:
                    logger.debug(
                        ' - build already pending for %s', series_name)
                    continue
                except CannotUploadToArchive as e:
                    # This will catch all PPA related issues -
                    # disabled, security, wrong pocket etc
                    logger.debug(
                        ' - daily build failed for %s: %s',
                        series_name, repr(e))
                except BuildNotAllowedForDistro:
                    logger.debug(
                        ' - cannot build against %s.' % series_name)
                except ProgrammingError:
                    raise
                except Exception:
                    logger.exception(' - problem with %s', series_name)
                else:
                    logger.debug(' - build requested for %s', series_name)
                    builds.append(build)
        return builds

    @property
    def can_be_rescored(self):
        """See `IBuild`."""
        return self.status is BuildStatus.NEEDSBUILD

    @property
    def can_be_cancelled(self):
        """See `ISourcePackageRecipeBuild`."""
        if not self.buildqueue_record:
            return False

        cancellable_statuses = [
            BuildStatus.BUILDING,
            BuildStatus.NEEDSBUILD,
            ]
        return self.status in cancellable_statuses

    def cancel(self):
        """See `ISourcePackageRecipeBuild`."""
        if not self.can_be_cancelled:
            return
        # BuildQueue.cancel() will decide whether to go straight to
        # CANCELLED, or go through CANCELLING to let buildd-manager
        # clean up the slave.
        self.buildqueue_record.cancel()

    def destroySelf(self):
        if self.buildqueue_record is not None:
            self.buildqueue_record.destroySelf()
        store = Store.of(self)
        releases = store.find(
            SourcePackageRelease,
            SourcePackageRelease.source_package_recipe_build == self.id)
        for release in releases:
            release.source_package_recipe_build = None
        store.remove(self)
        store.remove(self.build_farm_job)

    def calculateScore(self):
        return 2510 + self.archive.relative_build_score

    @classmethod
    def getByID(cls, build_id):
        """See `ISourcePackageRecipeBuildSource`."""
        store = IMasterStore(SourcePackageRecipeBuild)
        return store.find(cls, cls.id == build_id).one()

    @classmethod
    def getByBuildFarmJob(cls, build_farm_job):
        """See `ISpecificBuildFarmJobSource`."""
        return Store.of(build_farm_job).find(
            cls, build_farm_job_id=build_farm_job.id).one()

    @classmethod
    def preloadBuildsData(cls, builds):
        # Circular imports.
        from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
        from lp.registry.model.distribution import Distribution
        from lp.registry.model.distroseries import DistroSeries
        from lp.services.librarian.model import LibraryFileAlias
        load_related(LibraryFileAlias, builds, ['log_id'])
        archives = load_related(Archive, builds, ['archive_id'])
        load_related(Person, archives, ['ownerID'])
        distroseries = load_related(DistroSeries, builds, ['distroseries_id'])
        load_related(Distribution, distroseries, ['distributionID'])
        sprs = load_related(SourcePackageRecipe, builds, ['recipe_id'])
        SourcePackageRecipe.preLoadDataForSourcePackageRecipes(sprs)

    @classmethod
    def getByBuildFarmJobs(cls, build_farm_jobs):
        """See `ISpecificBuildFarmJobSource`."""
        if len(build_farm_jobs) == 0:
            return EmptyResultSet()
        rows = Store.of(build_farm_jobs[0]).find(
            cls, cls.build_farm_job_id.is_in(
                bfj.id for bfj in build_farm_jobs))
        return DecoratedResultSet(rows, pre_iter_hook=cls.preloadBuildsData)

    def estimateDuration(self):
        """See `IPackageBuild`."""
        median = self.recipe.getMedianBuildDuration()
        if median is not None:
            return median
        return timedelta(minutes=10)

    def verifySuccessfulUpload(self):
        return self.source_package_release is not None

    def notify(self, extra_info=None):
        """See `IPackageBuild`."""
        # If our recipe has been deleted, any notification will fail.
        if self.recipe is None:
            return
        if self.status == BuildStatus.FULLYBUILT:
            # Don't send mail for successful recipe builds; it can be just
            # too much.
            return
        mailer = SourcePackageRecipeBuildMailer.forStatus(self)
        mailer.sendAll()

    def lfaUrl(self, lfa):
        """Return the URL for a LibraryFileAlias, in the context of self.
        """
        if lfa is None:
            return None
        return ProxiedLibraryFileAlias(lfa, self).http_url

    @property
    def log_url(self):
        """See `IPackageBuild`.

        Overridden here so that it uses the SourcePackageRecipeBuild as
        context.
        """
        return self.lfaUrl(self.log)

    @property
    def upload_log_url(self):
        """See `IPackageBuild`.

        Overridden here so that it uses the SourcePackageRecipeBuild as
        context.
        """
        return self.lfaUrl(self.upload_log)

    def getFileByName(self, filename):
        """See `ISourcePackageRecipeBuild`."""
        files = dict((lfa.filename, lfa)
                     for lfa in [self.log, self.upload_log]
                     if lfa is not None)
        try:
            return files[filename]
        except KeyError:
            raise NotFoundError(filename)

    def getUploader(self, changes):
        """See `IPackageBuild`."""
        return self.requester
