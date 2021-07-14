# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Charm recipes."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "CharmRecipe",
    "get_charm_recipe_privacy_filter",
    ]

from operator import (
    attrgetter,
    itemgetter,
    )

from lazr.lifecycle.event import ObjectCreatedEvent
import pytz
from storm.databases.postgres import JSON
from storm.locals import (
    And,
    Bool,
    DateTime,
    Desc,
    Int,
    Join,
    Not,
    Or,
    Reference,
    Select,
    Store,
    Unicode,
    )
import yaml
from zope.component import getUtility
from zope.event import notify
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import (
    FREE_INFORMATION_TYPES,
    InformationType,
    PUBLIC_INFORMATION_TYPES,
    )
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.buildmaster.model.builder import Builder
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.charms.adapters.buildarch import determine_instances_to_build
from lp.charms.interfaces.charmrecipe import (
    BadCharmRecipeSearchContext,
    CannotFetchCharmcraftYaml,
    CannotParseCharmcraftYaml,
    CHARM_RECIPE_ALLOW_CREATE,
    CHARM_RECIPE_BUILD_DISTRIBUTION,
    CHARM_RECIPE_PRIVATE_FEATURE_FLAG,
    CharmRecipeBuildAlreadyPending,
    CharmRecipeBuildDisallowedArchitecture,
    CharmRecipeBuildRequestStatus,
    CharmRecipeFeatureDisabled,
    CharmRecipeNotOwner,
    CharmRecipePrivacyMismatch,
    CharmRecipePrivateFeatureDisabled,
    DuplicateCharmRecipeName,
    ICharmRecipe,
    ICharmRecipeBuildRequest,
    ICharmRecipeSet,
    MissingCharmcraftYaml,
    NoSourceForCharmRecipe,
    NoSuchCharmRecipe,
    )
from lp.charms.interfaces.charmrecipebuild import ICharmRecipeBuildSet
from lp.charms.interfaces.charmrecipejob import (
    ICharmRecipeRequestBuildsJobSource,
    )
from lp.charms.model.charmrecipebuild import CharmRecipeBuild
from lp.charms.model.charmrecipejob import CharmRecipeJob
from lp.code.errors import (
    GitRepositoryBlobNotFound,
    GitRepositoryScanFault,
    )
from lp.code.interfaces.gitcollection import (
    IAllGitRepositories,
    IGitCollection,
    )
from lp.code.interfaces.gitref import IGitRef
from lp.code.interfaces.gitrepository import IGitRepository
from lp.code.model.gitcollection import GenericGitCollection
from lp.code.model.gitref import GitRef
from lp.code.model.gitrepository import GitRepository
from lp.registry.errors import PrivatePersonLinkageError
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    validate_public_person,
    )
from lp.registry.interfaces.product import IProduct
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.product import Product
from lp.registry.model.series import ACTIVE_STATUSES
from lp.services.database.bulk import load_related
from lp.services.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.stormbase import StormBase
from lp.services.database.stormexpr import (
    Greatest,
    NullsLast,
    )
from lp.services.features import getFeatureFlag
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.services.librarian.model import LibraryFileAlias
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.soyuz.model.distroarchseries import (
    DistroArchSeries,
    PocketChroot,
    )


def charm_recipe_modified(recipe, event):
    """Update the date_last_modified property when a charm recipe is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on charm recipes.
    """
    removeSecurityProxy(recipe).date_last_modified = UTC_NOW


@implementer(ICharmRecipeBuildRequest)
class CharmRecipeBuildRequest:
    """See `ICharmRecipeBuildRequest`.

    This is not directly backed by a database table; instead, it is a
    webservice-friendly view of an asynchronous build request.
    """

    def __init__(self, recipe, id):
        self.recipe = recipe
        self.id = id

    @classmethod
    def fromJob(cls, job):
        """See `ICharmRecipeBuildRequest`."""
        request = cls(job.recipe, job.job_id)
        get_property_cache(request)._job = job
        return request

    @cachedproperty
    def _job(self):
        job_source = getUtility(ICharmRecipeRequestBuildsJobSource)
        return job_source.getByRecipeAndID(self.recipe, self.id)

    @property
    def date_requested(self):
        """See `ICharmRecipeBuildRequest`."""
        return self._job.date_created

    @property
    def date_finished(self):
        """See `ICharmRecipeBuildRequest`."""
        return self._job.date_finished

    @property
    def status(self):
        """See `ICharmRecipeBuildRequest`."""
        status_map = {
            JobStatus.WAITING: CharmRecipeBuildRequestStatus.PENDING,
            JobStatus.RUNNING: CharmRecipeBuildRequestStatus.PENDING,
            JobStatus.COMPLETED: CharmRecipeBuildRequestStatus.COMPLETED,
            JobStatus.FAILED: CharmRecipeBuildRequestStatus.FAILED,
            JobStatus.SUSPENDED: CharmRecipeBuildRequestStatus.PENDING,
            }
        return status_map[self._job.job.status]

    @property
    def error_message(self):
        """See `ICharmRecipeBuildRequest`."""
        return self._job.error_message

    @property
    def builds(self):
        """See `ICharmRecipeBuildRequest`."""
        return self._job.builds

    @property
    def requester(self):
        """See `ICharmRecipeBuildRequest`."""
        return self._job.requester

    @property
    def channels(self):
        """See `ICharmRecipeBuildRequest`."""
        return self._job.channels

    @property
    def architectures(self):
        """See `ICharmRecipeBuildRequest`."""
        return self._job.architectures


@implementer(ICharmRecipe)
class CharmRecipe(StormBase):
    """See `ICharmRecipe`."""

    __storm_table__ = "CharmRecipe"

    id = Int(primary=True)

    date_created = DateTime(
        name="date_created", tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name="date_last_modified", tzinfo=pytz.UTC, allow_none=False)

    registrant_id = Int(name="registrant", allow_none=False)
    registrant = Reference(registrant_id, "Person.id")

    def _validate_owner(self, attr, value):
        if not self.private:
            try:
                validate_public_person(self, attr, value)
            except PrivatePersonLinkageError:
                raise CharmRecipePrivacyMismatch(
                    "A public charm recipe cannot have a private owner.")
        return value

    owner_id = Int(name="owner", allow_none=False, validator=_validate_owner)
    owner = Reference(owner_id, "Person.id")

    project_id = Int(name="project", allow_none=False)
    project = Reference(project_id, "Product.id")

    name = Unicode(name="name", allow_none=False)

    description = Unicode(name="description", allow_none=True)

    def _validate_git_repository(self, attr, value):
        if not self.private and value is not None:
            if IStore(GitRepository).get(GitRepository, value).private:
                raise CharmRecipePrivacyMismatch(
                    "A public charm recipe cannot have a private repository.")
        return value

    git_repository_id = Int(
        name="git_repository", allow_none=True,
        validator=_validate_git_repository)
    git_repository = Reference(git_repository_id, "GitRepository.id")

    git_path = Unicode(name="git_path", allow_none=True)

    build_path = Unicode(name="build_path", allow_none=True)

    require_virtualized = Bool(name="require_virtualized")

    def _valid_information_type(self, attr, value):
        if not getUtility(ICharmRecipeSet).isValidInformationType(
                value, self.owner, self.git_ref):
            raise CharmRecipePrivacyMismatch
        return value

    information_type = DBEnum(
        enum=InformationType, default=InformationType.PUBLIC,
        name="information_type", validator=_valid_information_type,
        allow_none=False)

    auto_build = Bool(name="auto_build", allow_none=False)

    auto_build_channels = JSON("auto_build_channels", allow_none=True)

    is_stale = Bool(name="is_stale", allow_none=False)

    store_upload = Bool(name="store_upload", allow_none=False)

    store_name = Unicode(name="store_name", allow_none=True)

    store_secrets = JSON("store_secrets", allow_none=True)

    _store_channels = JSON("store_channels", allow_none=True)

    def __init__(self, registrant, owner, project, name, description=None,
                 git_ref=None, build_path=None, require_virtualized=True,
                 information_type=InformationType.PUBLIC, auto_build=False,
                 auto_build_channels=None, store_upload=False,
                 store_name=None, store_secrets=None, store_channels=None,
                 date_created=DEFAULT):
        """Construct a `CharmRecipe`."""
        if not getFeatureFlag(CHARM_RECIPE_ALLOW_CREATE):
            raise CharmRecipeFeatureDisabled()
        super(CharmRecipe, self).__init__()

        # Set this first for use by other validators.
        self.information_type = information_type

        self.date_created = date_created
        self.date_last_modified = date_created
        self.registrant = registrant
        self.owner = owner
        self.project = project
        self.name = name
        self.description = description
        self.git_ref = git_ref
        self.build_path = build_path
        self.require_virtualized = require_virtualized
        self.auto_build = auto_build
        self.auto_build_channels = auto_build_channels
        self.store_upload = store_upload
        self.store_name = store_name
        self.store_secrets = store_secrets
        self.store_channels = store_channels

    def __repr__(self):
        return "<CharmRecipe ~%s/%s/+charm/%s>" % (
            self.owner.name, self.project.name, self.name)

    @property
    def private(self):
        """See `ICharmRecipe`."""
        return self.information_type not in PUBLIC_INFORMATION_TYPES

    @cachedproperty
    def _git_ref(self):
        if self.git_repository is not None:
            return self.git_repository.getRefByPath(self.git_path)
        else:
            return None

    @property
    def git_ref(self):
        """See `ICharmRecipe`."""
        return self._git_ref

    @git_ref.setter
    def git_ref(self, value):
        """See `ICharmRecipe`."""
        if value is not None:
            self.git_repository = value.repository
            self.git_path = value.path
        else:
            self.git_repository = None
            self.git_path = None
        get_property_cache(self)._git_ref = value

    @property
    def source(self):
        """See `ICharmRecipe`."""
        return self.git_ref

    @property
    def store_channels(self):
        """See `ICharmRecipe`."""
        return self._store_channels or []

    @store_channels.setter
    def store_channels(self, value):
        """See `ICharmRecipe`."""
        self._store_channels = value or None

    @cachedproperty
    def _default_distribution(self):
        """See `ICharmRecipe`."""
        # Use the default distribution set by this feature rule, or Ubuntu
        # if none is set.
        distro_name = getFeatureFlag(CHARM_RECIPE_BUILD_DISTRIBUTION)
        if not distro_name:
            return getUtility(ILaunchpadCelebrities).ubuntu
        distro = getUtility(IDistributionSet).getByName(distro_name)
        if not distro:
            raise ValueError(
                "'%s' is not a valid value for feature rule '%s'" % (
                    distro_name, CHARM_RECIPE_BUILD_DISTRIBUTION))
        return distro

    @cachedproperty
    def _default_distro_series(self):
        """See `ICharmRecipe`."""
        # Use the series set by this feature rule, or the current series of
        # the default distribution if the feature rule is not set.
        series_name = getFeatureFlag(
            "charm.default_build_series.%s" % self._default_distribution.name)
        if series_name:
            return self._default_distribution.getSeries(series_name)
        else:
            return self._default_distribution.currentseries

    def getAllowedInformationTypes(self, user):
        """See `ICharmRecipe`."""
        # XXX cjwatson 2021-05-26: Only allow free information types until
        # we have more privacy infrastructure in place.
        return FREE_INFORMATION_TYPES

    def visibleByUser(self, user):
        """See `ICharmRecipe`."""
        if self.information_type in PUBLIC_INFORMATION_TYPES:
            return True
        if user is None:
            return False
        return not IStore(CharmRecipe).find(
            CharmRecipe,
            CharmRecipe.id == self.id,
            get_charm_recipe_privacy_filter(user)).is_empty()

    def _isBuildableArchitectureAllowed(self, das):
        """Check whether we may build for a buildable `DistroArchSeries`.

        The caller is assumed to have already checked that a suitable chroot
        is available (either directly or via
        `DistroSeries.buildable_architectures`).
        """
        return (
            das.enabled
            and (
                das.processor.supports_virtualized
                or not self.require_virtualized))

    def _isArchitectureAllowed(self, das):
        """Check whether we may build for a `DistroArchSeries`."""
        return (
            das.getChroot() is not None
            and self._isBuildableArchitectureAllowed(das))

    def getAllowedArchitectures(self):
        """See `IOCIRecipe`."""
        store = Store.of(self)
        origin = [
            DistroArchSeries,
            Join(DistroSeries,
                 DistroArchSeries.distroseries == DistroSeries.id),
            Join(Distribution, DistroSeries.distribution == Distribution.id),
            Join(PocketChroot,
                 PocketChroot.distroarchseries == DistroArchSeries.id),
            Join(LibraryFileAlias,
                 PocketChroot.chroot == LibraryFileAlias.id),
            ]
        # Preload DistroSeries and Distribution, since we'll need those in
        # determine_architectures_to_build.
        results = store.using(*origin).find(
            (DistroArchSeries, DistroSeries, Distribution),
            DistroSeries.status.is_in(ACTIVE_STATUSES)).config(distinct=True)
        all_buildable_dases = DecoratedResultSet(results, itemgetter(0))
        return [
            das for das in all_buildable_dases
            if self._isBuildableArchitectureAllowed(das)]

    def _checkRequestBuild(self, requester):
        """May `requester` request builds of this charm recipe?"""
        if not requester.inTeam(self.owner):
            raise CharmRecipeNotOwner(
                "%s cannot create charm recipe builds owned by %s." %
                (requester.display_name, self.owner.display_name))

    def requestBuild(self, build_request, distro_arch_series, channels=None):
        """Request a single build of this charm recipe.

        This method is for internal use; external callers should use
        `requestBuilds` instead.

        :param build_request: The `ICharmRecipeBuildRequest` job being
            processed.
        :param distro_arch_series: The architecture to build for.
        :param channels: A dictionary mapping snap names to channels to use
            for this build.
        :return: `ICharmRecipeBuild`.
        """
        self._checkRequestBuild(build_request.requester)
        if not self._isArchitectureAllowed(distro_arch_series):
            raise CharmRecipeBuildDisallowedArchitecture(distro_arch_series)

        if not channels:
            channels_clause = Or(
                CharmRecipeBuild.channels == None,
                CharmRecipeBuild.channels == {})
        else:
            channels_clause = CharmRecipeBuild.channels == channels
        pending = IStore(self).find(
            CharmRecipeBuild,
            CharmRecipeBuild.recipe == self,
            CharmRecipeBuild.processor == distro_arch_series.processor,
            channels_clause,
            CharmRecipeBuild.status == BuildStatus.NEEDSBUILD)
        if pending.any() is not None:
            raise CharmRecipeBuildAlreadyPending

        build = getUtility(ICharmRecipeBuildSet).new(
            build_request, self, distro_arch_series, channels=channels)
        build.queueBuild()
        notify(ObjectCreatedEvent(build, user=build_request.requester))
        return build

    def requestBuilds(self, requester, channels=None, architectures=None):
        """See `ICharmRecipe`."""
        self._checkRequestBuild(requester)
        job = getUtility(ICharmRecipeRequestBuildsJobSource).create(
            self, requester, channels=channels, architectures=architectures)
        return self.getBuildRequest(job.job_id)

    def requestBuildsFromJob(self, build_request, channels=None,
                             architectures=None, allow_failures=False,
                             logger=None):
        """See `ICharmRecipe`."""
        try:
            try:
                charmcraft_data = removeSecurityProxy(
                    getUtility(ICharmRecipeSet).getCharmcraftYaml(self))
            except MissingCharmcraftYaml:
                # charmcraft doesn't currently require charmcraft.yaml, and
                # we have reasonable defaults without it.
                charmcraft_data = {}

            # Sort by (Distribution.id, DistroSeries.id, Processor.id) for
            # determinism.  This is chosen to be a similar order as in
            # BinaryPackageBuildSet.createForSource, to minimize confusion.
            supported_arches = [
                das for das in sorted(
                    self.getAllowedArchitectures(),
                    key=attrgetter(
                        "distroseries.distribution.id", "distroseries.id",
                        "processor.id"))
                if (architectures is None or
                    das.architecturetag in architectures)]
            instances_to_build = determine_instances_to_build(
                charmcraft_data, supported_arches, self._default_distro_series)
        except Exception as e:
            if not allow_failures:
                raise
            elif logger is not None:
                logger.exception(
                    " - %s/%s/%s: %s",
                    self.owner.name, self.project.name, self.name, e)

        builds = []
        for das in instances_to_build:
            try:
                build = self.requestBuild(
                    build_request, das, channels=channels)
                if logger is not None:
                    logger.debug(
                        " - %s/%s/%s %s/%s/%s: Build requested.",
                        self.owner.name, self.project.name, self.name,
                        das.distroseries.distribution.name,
                        das.distroseries.name, das.architecturetag)
                builds.append(build)
            except CharmRecipeBuildAlreadyPending:
                pass
            except Exception as e:
                if not allow_failures:
                    raise
                elif logger is not None:
                    logger.exception(
                        " - %s/%s/%s %s/%s/%s: %s",
                        self.owner.name, self.project.name, self.name,
                        das.distroseries.distribution.name,
                        das.distroseries.name, das.architecturetag, e)
        return builds

    def getBuildRequest(self, job_id):
        """See `ICharmRecipe`."""
        return CharmRecipeBuildRequest(self, job_id)

    @property
    def pending_build_requests(self):
        """See `ICharmRecipe`."""
        job_source = getUtility(ICharmRecipeRequestBuildsJobSource)
        # The returned jobs are ordered by descending ID.
        jobs = job_source.findByRecipe(
            self, statuses=(JobStatus.WAITING, JobStatus.RUNNING))
        return DecoratedResultSet(
            jobs, result_decorator=CharmRecipeBuildRequest.fromJob)

    @property
    def failed_build_requests(self):
        """See `ICharmRecipe`."""
        job_source = getUtility(ICharmRecipeRequestBuildsJobSource)
        # The returned jobs are ordered by descending ID.
        jobs = job_source.findByRecipe(self, statuses=(JobStatus.FAILED,))
        return DecoratedResultSet(
            jobs, result_decorator=CharmRecipeBuildRequest.fromJob)

    def _getBuilds(self, filter_term, order_by):
        """The actual query to get the builds."""
        query_args = [
            CharmRecipeBuild.recipe == self,
            ]
        if filter_term is not None:
            query_args.append(filter_term)
        result = Store.of(self).find(CharmRecipeBuild, *query_args)
        result.order_by(order_by)

        def eager_load(rows):
            getUtility(ICharmRecipeBuildSet).preloadBuildsData(rows)
            getUtility(IBuildQueueSet).preloadForBuildFarmJobs(rows)
            load_related(Builder, rows, ["builder_id"])

        return DecoratedResultSet(result, pre_iter_hook=eager_load)

    @property
    def builds(self):
        """See `ICharmRecipe`."""
        order_by = (
            NullsLast(Desc(Greatest(
                CharmRecipeBuild.date_started,
                CharmRecipeBuild.date_finished))),
            Desc(CharmRecipeBuild.date_created),
            Desc(CharmRecipeBuild.id))
        return self._getBuilds(None, order_by)

    @property
    def _pending_states(self):
        """All the build states we consider pending (non-final)."""
        return [
            BuildStatus.NEEDSBUILD,
            BuildStatus.BUILDING,
            BuildStatus.UPLOADING,
            BuildStatus.CANCELLING,
            ]

    @property
    def completed_builds(self):
        """See `ICharmRecipe`."""
        filter_term = Not(CharmRecipeBuild.status.is_in(self._pending_states))
        order_by = (
            NullsLast(Desc(Greatest(
                CharmRecipeBuild.date_started,
                CharmRecipeBuild.date_finished))),
            Desc(CharmRecipeBuild.id))
        return self._getBuilds(filter_term, order_by)

    @property
    def pending_builds(self):
        """See `ICharmRecipe`."""
        filter_term = (CharmRecipeBuild.status.is_in(self._pending_states))
        # We want to order by date_created but this is the same as ordering
        # by id (since id increases monotonically) and is less expensive.
        order_by = Desc(CharmRecipeBuild.id)
        return self._getBuilds(filter_term, order_by)

    def destroySelf(self):
        """See `ICharmRecipe`."""
        store = IStore(self)
        # Remove build jobs.  There won't be many queued builds, so we can
        # afford to do this the safe but slow way via BuildQueue.destroySelf
        # rather than in bulk.
        buildqueue_records = store.find(
            BuildQueue,
            BuildQueue._build_farm_job_id ==
                CharmRecipeBuild.build_farm_job_id,
            CharmRecipeBuild.recipe == self)
        for buildqueue_record in buildqueue_records:
            buildqueue_record.destroySelf()
        build_farm_job_ids = list(store.find(
            CharmRecipeBuild.build_farm_job_id,
            CharmRecipeBuild.recipe == self))
        store.execute("""
            DELETE FROM CharmFile
            USING CharmRecipeBuild
            WHERE
                CharmFile.build = CharmRecipeBuild.id AND
                CharmRecipeBuild.recipe = ?
            """, (self.id,))
        store.find(CharmRecipeBuild, CharmRecipeBuild.recipe == self).remove()
        affected_jobs = Select(
            [CharmRecipeJob.job_id],
            And(CharmRecipeJob.job == Job.id, CharmRecipeJob.recipe == self))
        store.find(Job, Job.id.is_in(affected_jobs)).remove()
        store.remove(self)
        store.find(
            BuildFarmJob, BuildFarmJob.id.is_in(build_farm_job_ids)).remove()


@implementer(ICharmRecipeSet)
class CharmRecipeSet:
    """See `ICharmRecipeSet`."""

    def new(self, registrant, owner, project, name, description=None,
            git_ref=None, build_path=None, require_virtualized=True,
            information_type=InformationType.PUBLIC, auto_build=False,
            auto_build_channels=None, store_upload=False, store_name=None,
            store_secrets=None, store_channels=None, date_created=DEFAULT):
        """See `ICharmRecipeSet`."""
        if not registrant.inTeam(owner):
            if owner.is_team:
                raise CharmRecipeNotOwner(
                    "%s is not a member of %s." %
                    (registrant.displayname, owner.displayname))
            else:
                raise CharmRecipeNotOwner(
                    "%s cannot create charm recipes owned by %s." %
                    (registrant.displayname, owner.displayname))

        if git_ref is None:
            raise NoSourceForCharmRecipe
        if self.exists(owner, project, name):
            raise DuplicateCharmRecipeName

        # The relevant validators will do their own checks as well, but we
        # do a single up-front check here in order to avoid an
        # IntegrityError due to exceptions being raised during object
        # creation and to ensure that everything relevant is in the Storm
        # cache.
        if not self.isValidInformationType(
                information_type, owner, git_ref):
            raise CharmRecipePrivacyMismatch

        store = IMasterStore(CharmRecipe)
        recipe = CharmRecipe(
            registrant, owner, project, name, description=description,
            git_ref=git_ref, build_path=build_path,
            require_virtualized=require_virtualized,
            information_type=information_type, auto_build=auto_build,
            auto_build_channels=auto_build_channels,
            store_upload=store_upload, store_name=store_name,
            store_secrets=store_secrets, store_channels=store_channels,
            date_created=date_created)
        store.add(recipe)

        return recipe

    def _getByName(self, owner, project, name):
        return IStore(CharmRecipe).find(
            CharmRecipe, owner=owner, project=project, name=name).one()

    def exists(self, owner, project, name):
        """See `ICharmRecipeSet`."""
        return self._getByName(owner, project, name) is not None

    def getByName(self, owner, project, name):
        """See `ICharmRecipeSet`."""
        recipe = self._getByName(owner, project, name)
        if recipe is None:
            raise NoSuchCharmRecipe(name)
        return recipe

    def _getRecipesFromCollection(self, collection, owner=None,
                                  visible_by_user=None):
        id_column = CharmRecipe.git_repository_id
        ids = collection.getRepositoryIds()
        expressions = [id_column.is_in(ids._get_select())]
        if owner is not None:
            expressions.append(CharmRecipe.owner == owner)
        expressions.append(get_charm_recipe_privacy_filter(visible_by_user))
        return IStore(CharmRecipe).find(CharmRecipe, *expressions)

    def findByPerson(self, person, visible_by_user=None):
        """See `ICharmRecipeSet`."""
        def _getRecipes(collection):
            collection = collection.visibleByUser(visible_by_user)
            owned = self._getRecipesFromCollection(
                collection.ownedBy(person), visible_by_user=visible_by_user)
            packaged = self._getRecipesFromCollection(
                collection, owner=person, visible_by_user=visible_by_user)
            return owned.union(packaged)

        git_collection = removeSecurityProxy(getUtility(IAllGitRepositories))
        git_recipes = _getRecipes(git_collection)
        return git_recipes

    def findByProject(self, project, visible_by_user=None):
        """See `ICharmRecipeSet`."""
        def _getRecipes(collection):
            return self._getRecipesFromCollection(
                collection.visibleByUser(visible_by_user),
                visible_by_user=visible_by_user)

        recipes_for_project = IStore(CharmRecipe).find(
            CharmRecipe,
            CharmRecipe.project == project,
            get_charm_recipe_privacy_filter(visible_by_user))
        git_collection = removeSecurityProxy(IGitCollection(project))
        return recipes_for_project.union(_getRecipes(git_collection))

    def findByGitRepository(self, repository, paths=None,
                            visible_by_user=None, check_permissions=True):
        """See `ICharmRecipeSet`."""
        clauses = [CharmRecipe.git_repository == repository]
        if paths is not None:
            clauses.append(CharmRecipe.git_path.is_in(paths))
        if check_permissions:
            clauses.append(get_charm_recipe_privacy_filter(visible_by_user))
        return IStore(CharmRecipe).find(CharmRecipe, *clauses)

    def findByGitRef(self, ref, visible_by_user=None):
        """See `ICharmRecipeSet`."""
        return IStore(CharmRecipe).find(
            CharmRecipe,
            CharmRecipe.git_repository == ref.repository,
            CharmRecipe.git_path == ref.path,
            get_charm_recipe_privacy_filter(visible_by_user))

    def findByContext(self, context, visible_by_user=None, order_by_date=True):
        """See `ICharmRecipeSet`."""
        if IPerson.providedBy(context):
            recipes = self.findByPerson(
                context, visible_by_user=visible_by_user)
        elif IProduct.providedBy(context):
            recipes = self.findByProject(
                context, visible_by_user=visible_by_user)
        elif IGitRepository.providedBy(context):
            recipes = self.findByGitRepository(
                context, visible_by_user=visible_by_user)
        elif IGitRef.providedBy(context):
            recipes = self.findByGitRef(
                context, visible_by_user=visible_by_user)
        else:
            raise BadCharmRecipeSearchContext(context)
        if order_by_date:
            recipes = recipes.order_by(Desc(CharmRecipe.date_last_modified))
        return recipes

    def isValidInformationType(self, information_type, owner, git_ref=None):
        """See `ICharmRecipeSet`."""
        private = information_type not in PUBLIC_INFORMATION_TYPES
        if private:
            # If appropriately enabled via feature flag.
            if not getFeatureFlag(CHARM_RECIPE_PRIVATE_FEATURE_FLAG):
                raise CharmRecipePrivateFeatureDisabled
            return True

        # Public charm recipes with private sources are not allowed.
        if git_ref is not None and git_ref.private:
            return False

        # Public charm recipes owned by private teams are not allowed.
        if owner is not None and owner.private:
            return False

        return True

    def preloadDataForRecipes(self, recipes, user=None):
        """See `ICharmRecipeSet`."""
        recipes = [removeSecurityProxy(recipe) for recipe in recipes]

        load_related(Product, recipes, ["project_id"])

        person_ids = set()
        for recipe in recipes:
            person_ids.add(recipe.registrant_id)
            person_ids.add(recipe.owner_id)

        repositories = load_related(
            GitRepository, recipes, ["git_repository_id"])
        if repositories:
            GenericGitCollection.preloadDataForRepositories(repositories)

        git_refs = GitRef.findByReposAndPaths(
            [(recipe.git_repository, recipe.git_path) for recipe in recipes])
        for recipe in recipes:
            git_ref = git_refs.get((recipe.git_repository, recipe.git_path))
            if git_ref is not None:
                get_property_cache(recipe)._git_ref = git_ref

        # Add repository owners to the list of pre-loaded persons.  We need
        # the target repository owner as well, since repository unique names
        # aren't trigger-maintained.
        person_ids.update(repository.owner_id for repository in repositories)

        list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            person_ids, need_validity=True))

    def getCharmcraftYaml(self, context, logger=None):
        """See `ICharmRecipeSet`."""
        if ICharmRecipe.providedBy(context):
            recipe = context
            source = context.git_ref
        else:
            recipe = None
            source = context
        if source is None:
            raise CannotFetchCharmcraftYaml("Charm source is not defined")
        try:
            path = "charmcraft.yaml"
            if recipe is not None and recipe.build_path is not None:
                path = "/".join((recipe.build_path, path))
            try:
                blob = source.getBlob(path)
            except GitRepositoryBlobNotFound:
                if logger is not None:
                    logger.exception(
                        "Cannot find charmcraft.yaml in %s",
                        source.unique_name)
                raise MissingCharmcraftYaml(source.unique_name)
        except GitRepositoryScanFault as e:
            msg = "Failed to get charmcraft.yaml from %s"
            if logger is not None:
                logger.exception(msg, source.unique_name)
            raise CannotFetchCharmcraftYaml(
                "%s: %s" % (msg % source.unique_name, e))

        try:
            charmcraft_data = yaml.safe_load(blob)
        except Exception as e:
            # Don't bother logging parsing errors from user-supplied YAML.
            raise CannotParseCharmcraftYaml(
                "Cannot parse charmcraft.yaml from %s: %s" %
                (source.unique_name, e))

        if not isinstance(charmcraft_data, dict):
            raise CannotParseCharmcraftYaml(
                "The top level of charmcraft.yaml from %s is not a mapping" %
                source.unique_name)

        return charmcraft_data

    def detachFromGitRepository(self, repository):
        """See `ICharmRecipeSet`."""
        recipes = self.findByGitRepository(repository)
        for recipe in recipes:
            get_property_cache(recipe)._git_ref = None
        recipes.set(
            git_repository_id=None, git_path=None, date_last_modified=UTC_NOW)


def get_charm_recipe_privacy_filter(user):
    """Return a Storm query filter to find charm recipes visible to `user`."""
    public_filter = CharmRecipe.information_type.is_in(
        PUBLIC_INFORMATION_TYPES)

    # XXX cjwatson 2021-06-07: Flesh this out once we have more privacy
    # infrastructure.
    return [public_filter]
