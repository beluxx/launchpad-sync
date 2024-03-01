# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the SourcePackageRecipe content type."""

import textwrap
from datetime import datetime, timedelta, timezone

import transaction
from brzbuildrecipe.recipe import ForbiddenInstructionError
from lazr.restfulclient.errors import BadRequest
from storm.locals import Store
from testtools.matchers import Equals
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.buildmaster.enums import BuildQueueStatus, BuildStatus
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.code.errors import (
    BuildAlreadyPending,
    PrivateBranchRecipe,
    PrivateGitRepositoryRecipe,
    TooNewRecipeFormat,
)
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.code.interfaces.linkedbranch import ICanHasLinkedBranch
from lp.code.interfaces.sourcepackagerecipe import (
    MINIMAL_RECIPE_TEXT_BZR,
    MINIMAL_RECIPE_TEXT_GIT,
    ISourcePackageRecipe,
    ISourcePackageRecipeSource,
    ISourcePackageRecipeView,
)
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuild,
)
from lp.code.model.sourcepackagerecipe import (
    NonPPABuildRequest,
    SourcePackageRecipe,
)
from lp.code.model.sourcepackagerecipebuild import SourcePackageRecipeBuild
from lp.code.model.sourcepackagerecipedata import SourcePackageRecipeData
from lp.code.tests.helpers import recipe_parser_newest_version
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.database.bulk import load_referencing
from lp.services.database.constants import UTC_NOW
from lp.services.propertycache import clear_property_cache
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.publisher import canonical_url
from lp.services.webapp.snapshot import notify_modified
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.archive import (
    ArchiveDisabled,
    CannotUploadToArchive,
    InvalidPocketForPPA,
)
from lp.testing import (
    ANONYMOUS,
    StormStatementRecorder,
    TestCaseWithFactory,
    admin_logged_in,
    celebrity_logged_in,
    launchpadlib_for,
    login,
    login_person,
    person_logged_in,
    verifyObject,
    ws_object,
)
from lp.testing.layers import AppServerLayer, DatabaseFunctionalLayer
from lp.testing.matchers import DoesNotSnapshot, HasQueryCount
from lp.testing.pages import webservice_for_person


class BzrMixin:
    """Mixin for Bazaar-based recipe tests."""

    private_error = PrivateBranchRecipe
    branch_type = "branch"
    recipe_id = "bzr-builder"

    def makeBranch(self, **kwargs):
        return self.factory.makeAnyBranch(**kwargs)

    @staticmethod
    def getRepository(branch):
        return branch

    @staticmethod
    def getBranchRecipeText(branch):
        return branch.identity

    @staticmethod
    def setInformationType(branch, information_type):
        removeSecurityProxy(branch).information_type = information_type

    def makeRecipeText(self):
        branch = self.makeBranch()
        return MINIMAL_RECIPE_TEXT_BZR % branch.identity


class GitMixin:
    """Mixin for Git-based recipe tests."""

    private_error = PrivateGitRepositoryRecipe
    branch_type = "repository"
    recipe_id = "git-build-recipe"

    def makeBranch(self, **kwargs):
        return self.factory.makeGitRefs(**kwargs)[0]

    @staticmethod
    def getRepository(branch):
        return branch.repository

    @staticmethod
    def getBranchRecipeText(branch):
        return branch.identity

    @staticmethod
    def setInformationType(branch, information_type):
        removeSecurityProxy(branch).repository.information_type = (
            information_type
        )

    def makeRecipeText(self):
        branch = self.makeBranch()
        return MINIMAL_RECIPE_TEXT_GIT % (
            branch.repository.identity,
            branch.name,
        )


class TestSourcePackageRecipeMixin:
    """Tests for `SourcePackageRecipe` objects."""

    layer = DatabaseFunctionalLayer

    def makeSourcePackageRecipe(self, branches=(), recipe=None, **kwargs):
        if recipe is None and len(branches) == 0:
            branches = [self.makeBranch()]
        return self.factory.makeSourcePackageRecipe(
            branches=branches, recipe=recipe, **kwargs
        )

    def test_implements_interface(self):
        """SourcePackageRecipe implements ISourcePackageRecipe."""
        recipe = self.makeSourcePackageRecipe()
        verifyObject(ISourcePackageRecipe, recipe)

    def test_avoids_problematic_snapshots(self):
        problematic_properties = [
            "builds",
            "completed_builds",
            "pending_builds",
        ]
        self.assertThat(
            self.makeSourcePackageRecipe(),
            DoesNotSnapshot(problematic_properties, ISourcePackageRecipeView),
        )

    def makeRecipeComponents(self, branches=()):
        """Return a dict of values that can be used to make a recipe.

        Suggested use: provide as kwargs to ISourcePackageRecipeSource.new
        :param branches: The list of branches to use in the recipe.  (If
            unspecified, a branch will be autogenerated.)
        """
        registrant = self.factory.makePerson()
        return dict(
            registrant=registrant,
            owner=self.factory.makeTeam(owner=registrant),
            distroseries=[self.factory.makeDistroSeries()],
            name=self.factory.getUniqueString("recipe-name"),
            description=self.factory.getUniqueString("recipe-description"),
            recipe=self.factory.makeRecipeText(*branches),
        )

    def test_creation(self):
        # The metadata supplied when a SourcePackageRecipe is created is
        # present on the new object.
        components = self.makeRecipeComponents()
        recipe = getUtility(ISourcePackageRecipeSource).new(**components)
        transaction.commit()
        self.assertEqual(
            (
                components["registrant"],
                components["owner"],
                set(components["distroseries"]),
                components["name"],
            ),
            (
                recipe.registrant,
                recipe.owner,
                set(recipe.distroseries),
                recipe.name,
            ),
        )
        self.assertEqual(True, recipe.is_stale)

    def test_creation_private_base_branch(self):
        """An exception should be raised if the base branch is private."""
        owner = self.factory.makePerson()
        with person_logged_in(owner):
            branch = self.makeBranch(
                owner=owner, information_type=InformationType.USERDATA
            )
            components = self.makeRecipeComponents(branches=[branch])
            recipe_source = getUtility(ISourcePackageRecipeSource)
            e = self.assertRaises(
                self.private_error, recipe_source.new, **components
            )
            self.assertEqual(
                "Recipe may not refer to private %s: %s"
                % (self.branch_type, self.getRepository(branch).identity),
                str(e),
            )

    def test_creation_private_referenced_branch(self):
        """An exception should be raised if a referenced branch is private."""
        owner = self.factory.makePerson()
        with person_logged_in(owner):
            base_branch = self.makeBranch(owner=owner)
            referenced_branch = self.makeBranch(
                owner=owner, information_type=InformationType.USERDATA
            )
            branches = [base_branch, referenced_branch]
            components = self.makeRecipeComponents(branches=branches)
            recipe_source = getUtility(ISourcePackageRecipeSource)
            e = self.assertRaises(
                self.private_error, recipe_source.new, **components
            )
            self.assertEqual(
                "Recipe may not refer to private %s: %s"
                % (
                    self.branch_type,
                    self.getRepository(referenced_branch).identity,
                ),
                str(e),
            )

    def test_exists(self):
        # Test ISourcePackageRecipeSource.exists
        recipe = self.makeSourcePackageRecipe()

        self.assertTrue(
            getUtility(ISourcePackageRecipeSource).exists(
                recipe.owner, recipe.name
            )
        )

        self.assertFalse(
            getUtility(ISourcePackageRecipeSource).exists(
                recipe.owner, "daily"
            )
        )

    def test_source_implements_interface(self):
        # The SourcePackageRecipe class implements ISourcePackageRecipeSource.
        self.assertProvides(
            getUtility(ISourcePackageRecipeSource), ISourcePackageRecipeSource
        )

    def test_recipe_implements_interface(self):
        # SourcePackageRecipe objects implement ISourcePackageRecipe.
        recipe = self.makeSourcePackageRecipe()
        transaction.commit()
        with person_logged_in(recipe.owner):
            self.assertProvides(recipe, ISourcePackageRecipe)

    def test_base_branch(self):
        # When a recipe is created, we can access its base branch.
        branch = self.makeBranch()
        sp_recipe = self.makeSourcePackageRecipe(branches=[branch])
        transaction.commit()
        self.assertEqual(self.getRepository(branch), sp_recipe.base)

    def test_branch_links_created(self):
        # When a recipe is created, we can query it for links to the branch
        # it references.
        branch = self.makeBranch()
        sp_recipe = self.makeSourcePackageRecipe(branches=[branch])
        transaction.commit()
        self.assertEqual(
            [self.getRepository(branch)],
            list(sp_recipe.getReferencedBranches()),
        )

    def createSourcePackageRecipe(self, number_of_branches=2):
        branches = []
        for _ in range(number_of_branches):
            branches.append(self.makeBranch())
        sp_recipe = self.makeSourcePackageRecipe(branches=branches)
        transaction.commit()
        return sp_recipe, branches

    def test_multiple_branch_links_created(self):
        # If a recipe links to more than one branch, getReferencedBranches()
        # returns all of them.
        sp_recipe, [branch1, branch2] = self.createSourcePackageRecipe()
        self.assertContentEqual(
            [self.getRepository(branch1), self.getRepository(branch2)],
            sp_recipe.getReferencedBranches(),
        )

    def test_preLoadReferencedBranches(self):
        sp_recipe, unused = self.createSourcePackageRecipe()
        recipe_data = load_referencing(
            SourcePackageRecipeData, [sp_recipe], ["sourcepackage_recipe_id"]
        )[0]
        referenced_branches = sp_recipe.getReferencedBranches()
        clear_property_cache(recipe_data)
        SourcePackageRecipeData.preLoadReferencedBranches([recipe_data])
        self.assertContentEqual(
            referenced_branches, sp_recipe.getReferencedBranches()
        )

    def test_random_user_cant_edit(self):
        # An arbitrary user can't set attributes.
        branch1 = self.makeBranch()
        recipe_1 = self.factory.makeRecipeText(branch1)
        sp_recipe = self.makeSourcePackageRecipe(recipe=recipe_1)
        login_person(self.factory.makePerson())
        self.assertRaises(Unauthorized, getattr, sp_recipe, "setRecipeText")

    def test_set_recipe_text_resets_branch_references(self):
        # When the recipe_text is replaced, getReferencedBranches returns
        # (only) the branches referenced by the new recipe.
        branch1 = self.makeBranch()
        sp_recipe = self.makeSourcePackageRecipe(branches=[branch1])
        branch2 = self.makeBranch()
        new_recipe = self.factory.makeRecipeText(branch2)
        with person_logged_in(sp_recipe.owner):
            sp_recipe.setRecipeText(new_recipe)
        self.assertEqual(
            [self.getRepository(branch2)],
            list(sp_recipe.getReferencedBranches()),
        )

    def test_rejects_run_command(self):
        recipe_text = """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        run touch test
        """ % dict(
            recipe_id=self.recipe_id,
            base=self.getBranchRecipeText(self.makeBranch()),
        )
        recipe_text = textwrap.dedent(recipe_text)
        self.assertRaises(
            ForbiddenInstructionError,
            self.makeSourcePackageRecipe,
            recipe=recipe_text,
        )

    def test_run_rejected_without_mangling_recipe(self):
        sp_recipe = self.makeSourcePackageRecipe()
        old_branches = list(sp_recipe.getReferencedBranches())
        recipe_text = """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        run touch test
        """ % dict(
            recipe_id=self.recipe_id,
            base=self.getBranchRecipeText(self.makeBranch()),
        )
        recipe_text = textwrap.dedent(recipe_text)
        with person_logged_in(sp_recipe.owner):
            self.assertRaises(
                ForbiddenInstructionError, sp_recipe.setRecipeText, recipe_text
            )
        self.assertEqual(old_branches, list(sp_recipe.getReferencedBranches()))

    def test_nest_part(self):
        """nest-part instruction can be round-tripped."""
        base = self.makeBranch()
        nested = self.makeBranch()
        recipe_text = (
            "# %s format 0.3 deb-version 1\n"
            "%s revid:base_revid\n"
            "nest-part nested1 %s foo bar tag:foo\n"
            % (
                self.recipe_id,
                self.getRepository(base).identity,
                self.getRepository(nested).identity,
            )
        )
        recipe = self.makeSourcePackageRecipe(recipe=recipe_text)
        self.assertEqual(recipe_text, recipe.recipe_text)

    def test_nest_part_no_target(self):
        """nest-part instruction with no target-dir can be round-tripped."""
        base = self.makeBranch()
        nested = self.makeBranch()
        recipe_text = (
            "# %s format 0.3 deb-version 1\n"
            "%s revid:base_revid\n"
            "nest-part nested1 %s foo\n"
            % (
                self.recipe_id,
                self.getRepository(base).identity,
                self.getRepository(nested).identity,
            )
        )
        recipe = self.makeSourcePackageRecipe(recipe=recipe_text)
        self.assertEqual(recipe_text, recipe.recipe_text)

    def test_accept_format_0_3(self):
        """Recipe format 0.3 is accepted."""
        builder_recipe = self.factory.makeRecipe()
        builder_recipe.format = 0.3
        self.makeSourcePackageRecipe(recipe=str(builder_recipe))

    def test_reject_newer_formats(self):
        with recipe_parser_newest_version(145.115):
            builder_recipe = self.factory.makeRecipe()
            builder_recipe.format = 145.115
            self.assertRaises(
                TooNewRecipeFormat,
                self.makeSourcePackageRecipe,
                recipe=str(builder_recipe),
            )

    def test_requestBuild(self):
        recipe = self.makeSourcePackageRecipe()
        (distroseries,) = list(recipe.distroseries)
        ppa = self.factory.makeArchive()
        build = recipe.requestBuild(
            ppa, ppa.owner, distroseries, PackagePublishingPocket.RELEASE
        )
        with admin_logged_in():
            self.assertProvides(build, ISourcePackageRecipeBuild)
        self.assertEqual(build.archive, ppa)
        self.assertEqual(build.distroseries, distroseries)
        self.assertEqual(build.requester, ppa.owner)
        self.assertTrue(build.virtualized)
        store = Store.of(build)
        store.flush()
        build_queue = store.find(
            BuildQueue,
            BuildQueue._build_farm_job_id
            == removeSecurityProxy(build).build_farm_job_id,
        ).one()
        self.assertProvides(build_queue, IBuildQueue)
        self.assertTrue(build_queue.virtualized)
        self.assertEqual(build_queue.status, BuildQueueStatus.WAITING)

    def test_requestBuildRejectsNotPPA(self):
        recipe = self.makeSourcePackageRecipe()
        not_ppa = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        (distroseries,) = list(recipe.distroseries)
        self.assertRaises(
            NonPPABuildRequest,
            recipe.requestBuild,
            not_ppa,
            not_ppa.owner,
            distroseries,
            PackagePublishingPocket.RELEASE,
        )

    def test_requestBuildRejectsNoPermission(self):
        recipe = self.makeSourcePackageRecipe()
        ppa = self.factory.makeArchive()
        requester = self.factory.makePerson()
        (distroseries,) = list(recipe.distroseries)
        self.assertRaises(
            CannotUploadToArchive,
            recipe.requestBuild,
            ppa,
            requester,
            distroseries,
            PackagePublishingPocket.RELEASE,
        )

    def test_requestBuildRejectsInvalidPocket(self):
        recipe = self.makeSourcePackageRecipe()
        ppa = self.factory.makeArchive()
        (distroseries,) = list(recipe.distroseries)
        self.assertRaises(
            InvalidPocketForPPA,
            recipe.requestBuild,
            ppa,
            ppa.owner,
            distroseries,
            PackagePublishingPocket.BACKPORTS,
        )

    def test_requestBuildRejectsDisabledArchive(self):
        recipe = self.makeSourcePackageRecipe()
        ppa = self.factory.makeArchive()
        removeSecurityProxy(ppa).disable()
        (distroseries,) = list(recipe.distroseries)
        with person_logged_in(ppa.owner):
            self.assertRaises(
                ArchiveDisabled,
                recipe.requestBuild,
                ppa,
                ppa.owner,
                distroseries,
                PackagePublishingPocket.RELEASE,
            )

    def test_requestBuildScore(self):
        """Normal build requests have a relatively low queue score (2510)."""
        recipe = self.makeSourcePackageRecipe()
        build = recipe.requestBuild(
            recipe.daily_build_archive,
            recipe.owner,
            list(recipe.distroseries)[0],
            PackagePublishingPocket.RELEASE,
        )
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2510, queue_record.lastscore)

    def test_requestBuildManualScore(self):
        """Manual build requests have a score equivalent to binary builds."""
        recipe = self.makeSourcePackageRecipe()
        build = recipe.requestBuild(
            recipe.daily_build_archive,
            recipe.owner,
            list(recipe.distroseries)[0],
            PackagePublishingPocket.RELEASE,
            manual=True,
        )
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2610, queue_record.lastscore)

    def test_requestBuild_relative_build_score(self):
        """Offsets for archives are respected."""
        recipe = self.makeSourcePackageRecipe()
        archive = recipe.daily_build_archive
        removeSecurityProxy(archive).relative_build_score = 100
        build = recipe.requestBuild(
            archive,
            recipe.owner,
            list(recipe.distroseries)[0],
            PackagePublishingPocket.RELEASE,
            manual=True,
        )
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2710, queue_record.lastscore)

    def test_requestBuildRejectRepeats(self):
        """Reject build requests that are identical to pending builds."""
        recipe = self.makeSourcePackageRecipe()
        series = list(recipe.distroseries)[0]
        archive = self.factory.makeArchive(owner=recipe.owner)
        old_build = recipe.requestBuild(
            archive, recipe.owner, series, PackagePublishingPocket.RELEASE
        )
        self.assertRaises(
            BuildAlreadyPending,
            recipe.requestBuild,
            archive,
            recipe.owner,
            series,
            PackagePublishingPocket.RELEASE,
        )
        # Varying archive allows build.
        recipe.requestBuild(
            self.factory.makeArchive(owner=recipe.owner),
            recipe.owner,
            series,
            PackagePublishingPocket.RELEASE,
        )
        # Varying distroseries allows build.
        new_distroseries = self.factory.makeSourcePackageRecipeDistroseries(
            "hoary"
        )
        recipe.requestBuild(
            archive,
            recipe.owner,
            new_distroseries,
            PackagePublishingPocket.RELEASE,
        )
        # Changing status of old build allows new build.
        old_build.updateStatus(BuildStatus.FULLYBUILT)
        recipe.requestBuild(
            archive, recipe.owner, series, PackagePublishingPocket.RELEASE
        )

    def test_requestBuildPrivatePPAWithArchivePermission(self):
        """User is not in PPA owner team but has ArchivePermission.

        The case where the user is not in the PPA owner team but is allowed to
        upload to the PPA via an explicit ArchivePermission takes a different
        security path than if they were part of the team.
        """

        # Create a team private PPA.
        team_owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=team_owner)
        team_p3a = self.factory.makeArchive(
            owner=team, displayname="Private PPA", name="p3a", private=True
        )

        # Create a recipe with the team P3A as the build destination.
        recipe = self.makeSourcePackageRecipe()

        # Add upload component rights for the non-team person.
        with person_logged_in(team_owner):
            team_p3a.newComponentUploader(
                person=recipe.owner, component_name="main"
            )
        (distroseries,) = list(recipe.distroseries)

        # Try to request a build.  It should work.
        with person_logged_in(recipe.owner):
            build = recipe.requestBuild(
                team_p3a,
                recipe.owner,
                distroseries,
                PackagePublishingPocket.RELEASE,
            )
            self.assertEqual(build.archive, team_p3a)
            self.assertEqual(build.distroseries, distroseries)
            self.assertEqual(build.requester, recipe.owner)

    def test_sourcepackagerecipe_description(self):
        """Ensure that the SourcePackageRecipe has a proper description."""
        description = "The whoozits and whatzits."
        source_package_recipe = self.makeSourcePackageRecipe(
            description=description
        )
        self.assertEqual(description, source_package_recipe.description)

    def test_distroseries(self):
        """Test that the distroseries behaves as a set."""
        recipe = self.makeSourcePackageRecipe()
        distroseries = self.factory.makeDistroSeries()
        (old_distroseries,) = recipe.distroseries
        recipe.distroseries.add(distroseries)
        self.assertEqual(
            {distroseries, old_distroseries}, set(recipe.distroseries)
        )
        recipe.distroseries.remove(distroseries)
        self.assertEqual([old_distroseries], list(recipe.distroseries))
        recipe.distroseries.clear()
        self.assertEqual([], list(recipe.distroseries))

    def test_build_daily(self):
        """Test that build_daily behaves as a bool."""
        recipe = self.makeSourcePackageRecipe()
        self.assertFalse(recipe.build_daily)
        login_person(recipe.owner)
        recipe.build_daily = True
        self.assertTrue(recipe.build_daily)

    def test_view_public(self):
        """Anyone can view a recipe with public branches."""
        owner = self.factory.makePerson()
        branch = self.makeBranch(owner=owner)
        with person_logged_in(owner):
            recipe = self.makeSourcePackageRecipe(branches=[branch])
            self.assertTrue(check_permission("launchpad.View", recipe))
        with person_logged_in(self.factory.makePerson()):
            self.assertTrue(check_permission("launchpad.View", recipe))
        self.assertTrue(check_permission("launchpad.View", recipe))

    def test_view_private(self):
        """Recipes with private branches are restricted."""
        owner = self.factory.makePerson()
        branch = self.makeBranch(owner=owner)
        with person_logged_in(owner):
            recipe = self.makeSourcePackageRecipe(branches=[branch])
            self.assertTrue(check_permission("launchpad.View", recipe))
        self.setInformationType(branch, InformationType.USERDATA)
        with person_logged_in(self.factory.makePerson()):
            self.assertFalse(check_permission("launchpad.View", recipe))
        self.assertFalse(check_permission("launchpad.View", recipe))

    def test_edit(self):
        """Only the owner can edit a sourcepackagerecipe."""
        recipe = self.makeSourcePackageRecipe()
        self.assertFalse(check_permission("launchpad.Edit", recipe))
        with person_logged_in(self.factory.makePerson()):
            self.assertFalse(check_permission("launchpad.Edit", recipe))
        with person_logged_in(recipe.owner):
            self.assertTrue(check_permission("launchpad.Edit", recipe))

    def test_destroySelf(self):
        """Should destroy associated builds, distroseries, etc."""
        # Recipe should have at least one datainstruction.
        branches = [self.makeBranch() for count in range(2)]
        recipe = self.makeSourcePackageRecipe(branches=branches)
        pending_build = self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe
        )
        pending_build.queueBuild()
        past_build = self.factory.makeSourcePackageRecipeBuild(recipe=recipe)
        past_build.queueBuild()
        removeSecurityProxy(past_build).datebuilt = datetime.now(timezone.utc)
        with person_logged_in(recipe.owner):
            recipe.destroySelf()
        # Show no database constraints were violated
        Store.of(recipe).flush()

    def test_destroySelf_preserves_release(self):
        # Destroying a sourcepackagerecipe removes references to its builds
        # from their releases.
        recipe = self.makeSourcePackageRecipe()
        build = self.factory.makeSourcePackageRecipeBuild(recipe=recipe)
        release = self.factory.makeSourcePackageRelease(
            source_package_recipe_build=build
        )
        self.assertEqual(build, release.source_package_recipe_build)
        with person_logged_in(recipe.owner):
            recipe.destroySelf()
        self.assertIsNot(None, release.source_package_recipe_build)

    def test_destroySelf_retains_build(self):
        # Destroying a sourcepackagerecipe removes references to its builds
        # from their releases.
        recipe = self.makeSourcePackageRecipe()
        build = self.factory.makeSourcePackageRecipeBuild(recipe=recipe)
        store = Store.of(build)
        store.flush()
        build_id = build.id
        build = store.find(
            SourcePackageRecipeBuild, SourcePackageRecipeBuild.id == build_id
        ).one()
        self.assertIsNot(None, build)
        self.assertEqual(recipe, build.recipe)
        with person_logged_in(recipe.owner):
            recipe.destroySelf()
        build = store.find(
            SourcePackageRecipeBuild, SourcePackageRecipeBuild.id == build_id
        ).one()
        self.assertIsNot(None, build)
        self.assertIs(None, build.recipe)
        transaction.commit()

    def test_destroySelf_permissions(self):
        # Only the owner, registry experts, or admins can delete recipes.
        owner = self.factory.makePerson()
        recipe = self.makeSourcePackageRecipe(owner=owner)
        self.assertRaises(Unauthorized, getattr, recipe, "destroySelf")
        with person_logged_in(self.factory.makePerson()):
            self.assertRaises(Unauthorized, getattr, recipe, "destroySelf")
        with person_logged_in(owner):
            recipe.destroySelf()
        recipe = self.makeSourcePackageRecipe(owner=owner)
        with celebrity_logged_in("registry_experts"):
            recipe.destroySelf()
        recipe = self.makeSourcePackageRecipe(owner=owner)
        with admin_logged_in():
            recipe.destroySelf()

    def test_findStaleDailyBuilds(self):
        # Stale recipe not built daily.
        self.makeSourcePackageRecipe()
        # Daily build recipe not stale.
        self.makeSourcePackageRecipe(build_daily=True, is_stale=False)
        # Stale daily build.
        stale_daily = self.makeSourcePackageRecipe(
            build_daily=True, is_stale=True
        )
        self.assertContentEqual(
            [stale_daily], SourcePackageRecipe.findStaleDailyBuilds()
        )

    def test_findStaleDailyBuildsDistinct(self):
        # If a recipe has 2 builds due to 2 distroseries, it only returns
        # one recipe.
        recipe = self.makeSourcePackageRecipe(build_daily=True, is_stale=True)
        hoary = self.factory.makeSourcePackageRecipeDistroseries("hoary")
        recipe.distroseries.add(hoary)
        for series in recipe.distroseries:
            self.factory.makeSourcePackageRecipeBuild(
                recipe=recipe,
                archive=recipe.daily_build_archive,
                requester=recipe.owner,
                distroseries=series,
                pocket=PackagePublishingPocket.RELEASE,
                date_created=(
                    datetime.now(timezone.utc) - timedelta(hours=24, seconds=1)
                ),
            )
        stale_recipes = SourcePackageRecipe.findStaleDailyBuilds()
        self.assertEqual([recipe], list(stale_recipes))

    def test_getMedianBuildDuration(self):
        def set_duration(build, minutes):
            duration = timedelta(minutes=minutes)
            build.updateStatus(BuildStatus.BUILDING)
            build.updateStatus(
                BuildStatus.FULLYBUILT,
                date_finished=build.date_started + duration,
            )

        recipe = removeSecurityProxy(self.makeSourcePackageRecipe())
        self.assertIs(None, recipe.getMedianBuildDuration())
        build = self.factory.makeSourcePackageRecipeBuild(recipe=recipe)
        set_duration(build, 10)
        self.assertEqual(
            timedelta(minutes=10), recipe.getMedianBuildDuration()
        )

        def addBuild(minutes):
            build = self.factory.makeSourcePackageRecipeBuild(recipe=recipe)
            set_duration(build, minutes)

        addBuild(20)
        self.assertEqual(
            timedelta(minutes=10), recipe.getMedianBuildDuration()
        )
        addBuild(11)
        self.assertEqual(
            timedelta(minutes=11), recipe.getMedianBuildDuration()
        )

    def test_getBuilds(self):
        # Test the various getBuilds methods.
        recipe = self.makeSourcePackageRecipe()
        builds = [
            self.factory.makeSourcePackageRecipeBuild(recipe=recipe)
            for x in range(3)
        ]
        # We want the latest builds first.
        builds.reverse()

        self.assertEqual([], list(recipe.completed_builds))
        self.assertEqual(builds, list(recipe.pending_builds))
        self.assertEqual(builds, list(recipe.builds))

        # Change the status of one of the builds and retest.
        builds[0].updateStatus(BuildStatus.FULLYBUILT)
        self.assertEqual([builds[0]], list(recipe.completed_builds))
        self.assertEqual(builds[1:], list(recipe.pending_builds))
        self.assertEqual(builds, list(recipe.builds))

    def test_getPendingBuildInfo(self):
        """SourcePackageRecipe.getPendingBuildInfo() is as expected."""
        person = self.factory.makePerson()
        archives = [self.factory.makeArchive(owner=person) for x in range(4)]
        distroseries = self.factory.makeSourcePackageRecipeDistroseries()
        recipe = self.makeSourcePackageRecipe()

        build_info = []
        for archive in archives:
            recipe.requestBuild(archive, person, distroseries)
            build_info.insert(
                0,
                {
                    "distroseries": distroseries.displayname,
                    "archive": archive.reference,
                },
            )
        self.assertEqual(build_info, list(recipe.getPendingBuildInfo()))

    def test_getBuilds_cancelled(self):
        # Cancelled builds are not considered pending.
        recipe = self.makeSourcePackageRecipe()
        build = self.factory.makeSourcePackageRecipeBuild(recipe=recipe)
        with admin_logged_in():
            build.queueBuild()
            build.cancel()
        self.assertEqual([build], list(recipe.builds))
        self.assertEqual([build], list(recipe.completed_builds))
        self.assertEqual([], list(recipe.pending_builds))

    def test_getBuilds_cancelled_never_started_last(self):
        # A cancelled build that was never even started sorts to the end.
        recipe = self.makeSourcePackageRecipe()
        fullybuilt = self.factory.makeSourcePackageRecipeBuild(recipe=recipe)
        instacancelled = self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe
        )
        fullybuilt.updateStatus(BuildStatus.BUILDING)
        fullybuilt.updateStatus(BuildStatus.CANCELLED)
        instacancelled.updateStatus(BuildStatus.CANCELLED)
        self.assertEqual([fullybuilt, instacancelled], list(recipe.builds))
        self.assertEqual(
            [fullybuilt, instacancelled], list(recipe.completed_builds)
        )
        self.assertEqual([], list(recipe.pending_builds))

    def test_setRecipeText_private_base_branch(self):
        source_package_recipe = self.makeSourcePackageRecipe()
        with person_logged_in(source_package_recipe.owner):
            branch = self.makeBranch(
                owner=source_package_recipe.owner,
                information_type=InformationType.USERDATA,
            )
            recipe_text = self.factory.makeRecipeText(branch)
            e = self.assertRaises(
                self.private_error,
                source_package_recipe.setRecipeText,
                recipe_text,
            )
            self.assertEqual(
                "Recipe may not refer to private %s: %s"
                % (self.branch_type, self.getRepository(branch).identity),
                str(e),
            )

    def test_setRecipeText_private_referenced_branch(self):
        source_package_recipe = self.makeSourcePackageRecipe()
        with person_logged_in(source_package_recipe.owner):
            base_branch = self.makeBranch(owner=source_package_recipe.owner)
            referenced_branch = self.makeBranch(
                owner=source_package_recipe.owner,
                information_type=InformationType.USERDATA,
            )
            recipe_text = self.factory.makeRecipeText(
                base_branch, referenced_branch
            )
            e = self.assertRaises(
                self.private_error,
                source_package_recipe.setRecipeText,
                recipe_text,
            )
            self.assertEqual(
                "Recipe may not refer to private %s: %s"
                % (
                    self.branch_type,
                    self.getRepository(referenced_branch).identity,
                ),
                str(e),
            )

    def test_getBuilds_ignores_disabled_archive(self):
        # Builds into a disabled archive aren't returned.
        archive = self.factory.makeArchive()
        recipe = self.makeSourcePackageRecipe()
        self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe, archive=archive
        )
        with person_logged_in(archive.owner):
            archive.disable()
        self.assertEqual([], list(recipe.builds))
        self.assertEqual([], list(recipe.completed_builds))
        self.assertEqual([], list(recipe.pending_builds))

    def test_containsUnbuildableSeries(self):
        recipe = self.makeSourcePackageRecipe()
        self.assertFalse(
            recipe.containsUnbuildableSeries(recipe.daily_build_archive)
        )

    def test_containsUnbuildableSeries_with_obsolete_series(self):
        recipe = self.makeSourcePackageRecipe()
        warty = self.factory.makeSourcePackageRecipeDistroseries()
        removeSecurityProxy(warty).status = SeriesStatus.OBSOLETE
        self.assertTrue(
            recipe.containsUnbuildableSeries(recipe.daily_build_archive)
        )

    def test_performDailyBuild_filters_obsolete_series(self):
        recipe = self.makeSourcePackageRecipe()
        warty = self.factory.makeSourcePackageRecipeDistroseries()
        hoary = self.factory.makeSourcePackageRecipeDistroseries(name="hoary")
        with person_logged_in(recipe.owner):
            recipe.updateSeries((warty, hoary))
        removeSecurityProxy(warty).status = SeriesStatus.OBSOLETE
        builds = recipe.performDailyBuild()
        self.assertEqual([build.recipe for build in builds], [recipe])


class TestSourcePackageRecipeBzr(
    TestSourcePackageRecipeMixin, BzrMixin, TestCaseWithFactory
):
    """Test `SourcePackageRecipe` objects for Bazaar."""


class TestSourcePackageRecipeGit(
    TestSourcePackageRecipeMixin, GitMixin, TestCaseWithFactory
):
    """Test `SourcePackageRecipe` objects for Git."""


class TestRecipeBranchRoundTrippingMixin:
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        self.base_branch = self.makeBranch()
        self.nested_branch = self.makeBranch()
        self.merged_branch = self.makeBranch()
        self.branch_identities = {
            "recipe_id": self.recipe_id,
            "base": self.getRepository(self.base_branch).identity,
            "nested": self.getRepository(self.nested_branch).identity,
            "merged": self.getRepository(self.merged_branch).identity,
        }

    def get_recipe(self, recipe_text):
        recipe_text = textwrap.dedent(recipe_text)
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam(owner=registrant)
        distroseries = self.factory.makeDistroSeries()
        name = self.factory.getUniqueString("recipe-name")
        description = self.factory.getUniqueString("recipe-description")
        recipe = getUtility(ISourcePackageRecipeSource).new(
            registrant=registrant,
            owner=owner,
            distroseries=[distroseries],
            name=name,
            description=description,
            recipe=recipe_text,
        )
        transaction.commit()
        return recipe

    def check_base_recipe_branch(
        self,
        branch,
        url,
        revspec=None,
        num_child_branches=0,
        revid=None,
        deb_version=None,
    ):
        self.check_recipe_branch(
            branch,
            None,
            url,
            revspec=revspec,
            num_child_branches=num_child_branches,
            revid=revid,
        )
        self.assertEqual(deb_version, branch.deb_version)

    def check_recipe_branch(
        self, branch, name, url, revspec=None, num_child_branches=0, revid=None
    ):
        self.assertEqual(name, branch.name)
        self.assertEqual(url, branch.url)
        self.assertEqual(revspec, branch.revspec)
        self.assertEqual(revid, branch.revid)
        self.assertEqual(num_child_branches, len(branch.child_branches))

    def test_builds_simplest_recipe(self):
        recipe_text = (
            """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        """
            % self.branch_identities
        )
        base_branch = self.get_recipe(recipe_text).builder_recipe
        self.check_base_recipe_branch(
            base_branch,
            self.getRepository(self.base_branch).identity,
            deb_version="0.1-{revno}",
        )

    def test_builds_recipe_with_merge(self):
        recipe_text = (
            """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        merge bar %(merged)s
        """
            % self.branch_identities
        )
        base_branch = self.get_recipe(recipe_text).builder_recipe
        self.check_base_recipe_branch(
            base_branch,
            self.getRepository(self.base_branch).identity,
            num_child_branches=1,
            deb_version="0.1-{revno}",
        )
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual(None, location)
        self.check_recipe_branch(
            child_branch,
            "bar",
            self.getRepository(self.merged_branch).identity,
        )

    def test_builds_recipe_with_nest(self):
        recipe_text = (
            """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        nest bar %(nested)s baz
        """
            % self.branch_identities
        )
        base_branch = self.get_recipe(recipe_text).builder_recipe
        self.check_base_recipe_branch(
            base_branch,
            self.getRepository(self.base_branch).identity,
            num_child_branches=1,
            deb_version="0.1-{revno}",
        )
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch,
            "bar",
            self.getRepository(self.nested_branch).identity,
        )

    def test_builds_recipe_with_nest_then_merge(self):
        recipe_text = (
            """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        nest bar %(nested)s baz
        merge zam %(merged)s
        """
            % self.branch_identities
        )
        base_branch = self.get_recipe(recipe_text).builder_recipe
        self.check_base_recipe_branch(
            base_branch,
            self.getRepository(self.base_branch).identity,
            num_child_branches=2,
            deb_version="0.1-{revno}",
        )
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch,
            "bar",
            self.getRepository(self.nested_branch).identity,
        )
        child_branch, location = base_branch.child_branches[1].as_tuple()
        self.assertEqual(None, location)
        self.check_recipe_branch(
            child_branch,
            "zam",
            self.getRepository(self.merged_branch).identity,
        )

    def test_builds_recipe_with_merge_then_nest(self):
        recipe_text = (
            """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        merge zam %(merged)s
        nest bar %(nested)s baz
        """
            % self.branch_identities
        )
        base_branch = self.get_recipe(recipe_text).builder_recipe
        self.check_base_recipe_branch(
            base_branch,
            self.getRepository(self.base_branch).identity,
            num_child_branches=2,
            deb_version="0.1-{revno}",
        )
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual(None, location)
        self.check_recipe_branch(
            child_branch,
            "zam",
            self.getRepository(self.merged_branch).identity,
        )
        child_branch, location = base_branch.child_branches[1].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch,
            "bar",
            self.getRepository(self.nested_branch).identity,
        )

    def test_builds_a_merge_in_to_a_nest(self):
        recipe_text = (
            """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        nest bar %(nested)s baz
          merge zam %(merged)s
        """
            % self.branch_identities
        )
        base_branch = self.get_recipe(recipe_text).builder_recipe
        self.check_base_recipe_branch(
            base_branch,
            self.getRepository(self.base_branch).identity,
            num_child_branches=1,
            deb_version="0.1-{revno}",
        )
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch,
            "bar",
            self.getRepository(self.nested_branch).identity,
            num_child_branches=1,
        )
        child_branch, location = child_branch.child_branches[0].as_tuple()
        self.assertEqual(None, location)
        self.check_recipe_branch(
            child_branch,
            "zam",
            self.getRepository(self.merged_branch).identity,
        )

    def tests_builds_nest_into_a_nest(self):
        nested2 = self.makeBranch()
        self.branch_identities["nested2"] = self.getRepository(
            nested2
        ).identity
        recipe_text = (
            """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        nest bar %(nested)s baz
          nest zam %(nested2)s zoo
        """
            % self.branch_identities
        )
        base_branch = self.get_recipe(recipe_text).builder_recipe
        self.check_base_recipe_branch(
            base_branch,
            self.getRepository(self.base_branch).identity,
            num_child_branches=1,
            deb_version="0.1-{revno}",
        )
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch,
            "bar",
            self.getRepository(self.nested_branch).identity,
            num_child_branches=1,
        )
        child_branch, location = child_branch.child_branches[0].as_tuple()
        self.assertEqual("zoo", location)
        self.check_recipe_branch(
            child_branch, "zam", self.getRepository(nested2).identity
        )

    def tests_builds_recipe_with_revspecs(self):
        recipe_text = (
            """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s revid:a
        nest bar %(nested)s baz tag:b
        merge zam %(merged)s 2
        """
            % self.branch_identities
        )
        base_branch = self.get_recipe(recipe_text).builder_recipe
        self.check_base_recipe_branch(
            base_branch,
            self.getRepository(self.base_branch).identity,
            num_child_branches=2,
            revspec="revid:a",
            deb_version="0.1-{revno}",
        )
        instruction = base_branch.child_branches[0]
        child_branch = instruction.recipe_branch
        location = instruction.nest_path
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch,
            "bar",
            self.getRepository(self.nested_branch).identity,
            revspec="tag:b",
        )
        child_branch, location = base_branch.child_branches[1].as_tuple()
        self.assertEqual(None, location)
        self.check_recipe_branch(
            child_branch,
            "zam",
            self.getRepository(self.merged_branch).identity,
            revspec="2",
        )

    def test_unsets_revspecs(self):
        # Changing a recipe's text to no longer include revspecs unsets
        # them from the stored copy.
        revspec_text = (
            """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s revid:a
        nest bar %(nested)s baz tag:b
        merge zam %(merged)s 2
        """
            % self.branch_identities
        )
        no_revspec_text = (
            """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        nest bar %(nested)s baz
        merge zam %(merged)s
        """
            % self.branch_identities
        )
        recipe = self.get_recipe(revspec_text)
        self.assertEqual(textwrap.dedent(revspec_text), recipe.recipe_text)
        with person_logged_in(recipe.owner):
            recipe.setRecipeText(textwrap.dedent(no_revspec_text))
        self.assertEqual(textwrap.dedent(no_revspec_text), recipe.recipe_text)

    def test_builds_recipe_without_debversion(self):
        recipe_text = (
            """\
        # %(recipe_id)s format 0.4
        %(base)s
        nest bar %(nested)s baz
        """
            % self.branch_identities
        )
        base_branch = self.get_recipe(recipe_text).builder_recipe
        self.check_base_recipe_branch(
            base_branch,
            self.getRepository(self.base_branch).identity,
            num_child_branches=1,
            deb_version=None,
        )
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch,
            "bar",
            self.getRepository(self.nested_branch).identity,
        )


class TestRecipeBranchRoundTrippingBzr(
    TestRecipeBranchRoundTrippingMixin, BzrMixin, TestCaseWithFactory
):
    def test_builds_recipe_with_ambiguous_git_repository(self):
        # Arrange for Bazaar and Git prefixes to match.
        self.pushConfig("codehosting", bzr_lp_prefix="lp:", lp_url_hosts="")
        project = self.base_branch.product
        repository = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            ICanHasLinkedBranch(project).setBranch(self.base_branch)
            getUtility(IGitRepositorySet).setDefaultRepository(
                project, repository
            )
        clear_property_cache(self.base_branch)
        recipe_text = """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        """ % {
            "recipe_id": self.recipe_id,
            "base": self.base_branch.identity,
        }
        recipe = self.get_recipe(recipe_text)
        self.assertEqual(self.base_branch, recipe.base_branch)


class TestRecipeBranchRoundTrippingGit(
    TestRecipeBranchRoundTrippingMixin, GitMixin, TestCaseWithFactory
):
    def test_builds_recipe_with_ambiguous_bzr_branch(self):
        # Arrange for Bazaar and Git prefixes to match.
        self.pushConfig("codehosting", bzr_lp_prefix="lp:", lp_url_hosts="")
        project = self.base_branch.target
        branch = self.factory.makeBranch(product=project)
        with person_logged_in(project.owner):
            ICanHasLinkedBranch(project).setBranch(branch)
            getUtility(IGitRepositorySet).setDefaultRepository(
                project, self.base_branch.repository
            )
        recipe_text = """\
        # %(recipe_id)s format 0.3 deb-version 0.1-{revno}
        %(base)s
        """ % {
            "recipe_id": self.recipe_id,
            "base": self.base_branch.repository.identity,
        }
        recipe = self.get_recipe(recipe_text)
        self.assertEqual(
            self.base_branch.repository, recipe.base_git_repository
        )


class RecipeDateLastModified(TestCaseWithFactory):
    """Exercises the situations where date_last_modified is updated."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, "test@canonical.com")
        date_created = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
        self.recipe = self.factory.makeSourcePackageRecipe(
            date_created=date_created
        )

    def test_initialValue(self):
        """Initially the date_last_modified is the date_created."""
        self.assertEqual(
            self.recipe.date_last_modified, self.recipe.date_created
        )

    def test_modifiedevent_sets_date_last_updated(self):
        # We publish an object modified event to check that the last modified
        # date is set to UTC_NOW.
        with notify_modified(removeSecurityProxy(self.recipe), ["name"]):
            pass
        self.assertSqlAttributeEqualsDate(
            self.recipe, "date_last_modified", UTC_NOW
        )


class TestWebserviceMixin:
    layer = AppServerLayer

    def makeRecipe(
        self, user=None, owner=None, recipe_text=None, version="devel"
    ):
        # rockstar 21 Jul 2010 - This function does more commits than I'd
        # like, but it's the result of the fact that the webservice runs in a
        # separate thread so doesn't get the database updates without those
        # commits.
        if user is None:
            user = self.factory.makePerson()
        if owner is None:
            owner = user
        db_distroseries = self.factory.makeSourcePackageRecipeDistroseries()
        if recipe_text is None:
            recipe_text = self.makeRecipeText()
        db_archive = self.factory.makeArchive(owner=owner, name="recipe-ppa")
        transaction.commit()
        launchpad = launchpadlib_for(
            "test",
            user,
            version=version,
            service_root=self.layer.appserver_root_url("api"),
        )
        login(ANONYMOUS)
        distroseries = ws_object(launchpad, db_distroseries)
        ws_owner = ws_object(launchpad, owner)
        ws_archive = ws_object(launchpad, db_archive)
        recipe = ws_owner.createRecipe(
            name="toaster-1",
            description="a recipe",
            recipe_text=recipe_text,
            distroseries=[distroseries.self_link],
            build_daily=True,
            daily_build_archive=ws_archive,
        )
        # at the moment, distroseries is not exposed in the API.
        transaction.commit()
        db_recipe = owner.getRecipe(name="toaster-1")
        self.assertEqual({db_distroseries}, set(db_recipe.distroseries))
        return recipe, ws_owner, launchpad

    def test_createRecipe(self):
        """Ensure recipe creation works."""
        team = self.factory.makeTeam()
        recipe_text = self.makeRecipeText()
        recipe, user = self.makeRecipe(
            user=team.teamowner, owner=team, recipe_text=recipe_text
        )[:2]
        self.assertEqual(team.name, recipe.owner.name)
        self.assertEqual(team.teamowner.name, recipe.registrant.name)
        self.assertEqual("toaster-1", recipe.name)
        self.assertEqual(recipe_text, recipe.recipe_text)
        self.assertTrue(recipe.build_daily)
        self.assertEqual("recipe-ppa", recipe.daily_build_archive.name)

    def test_recipe_text(self):
        recipe_text2 = self.makeRecipeText()
        recipe = self.makeRecipe()[0]
        recipe.recipe_text = recipe_text2
        recipe.lp_save()
        self.assertEqual(recipe_text2, recipe.recipe_text)

    def test_recipe_text_setRecipeText_not_in_devel(self):
        recipe = self.makeRecipe()[0]
        method = getattr(recipe, "setRecipeText", None)
        self.assertIs(None, method)

    def test_recipe_text_setRecipeText_in_one_zero(self):
        recipe_text2 = self.makeRecipeText()
        recipe = self.makeRecipe(version="1.0")[0]
        recipe.setRecipeText(recipe_text=recipe_text2)
        self.assertEqual(recipe_text2, recipe.recipe_text)

    def test_is_stale(self):
        """is_stale is exported and is read-only."""
        recipe = self.makeRecipe()[0]
        self.assertTrue(recipe.is_stale)
        recipe.is_stale = False
        self.assertRaises(BadRequest, recipe.lp_save)

    def test_getRecipe(self):
        """Person.getRecipe returns the named recipe."""
        recipe, user = self.makeRecipe()[:-1]
        self.assertEqual(recipe, user.getRecipe(name=recipe.name))

    def test_recipes(self):
        """Person.recipes works as expected."""
        recipe, user = self.makeRecipe()[:-1]
        [ws_recipe] = user.recipes
        self.assertEqual(recipe, ws_recipe)

    def test_requestBuild(self):
        """Build requests can be performed and last_build works."""
        person = self.factory.makePerson()
        archive = self.factory.makeArchive(owner=person)
        distroseries = self.factory.makeSourcePackageRecipeDistroseries()

        recipe, user, launchpad = self.makeRecipe(person)
        distroseries = ws_object(launchpad, distroseries)
        archive = ws_object(launchpad, archive)
        build = recipe.requestBuild(
            archive=archive,
            distroseries=distroseries,
            pocket=PackagePublishingPocket.RELEASE.title,
        )
        self.assertEqual(build, recipe.last_build)

    def test_requestBuildRejectRepeat(self):
        """Build requests are rejected if already pending."""
        person = self.factory.makePerson()
        archive = self.factory.makeArchive(owner=person)
        distroseries = self.factory.makeSourcePackageRecipeDistroseries()

        recipe, user, launchpad = self.makeRecipe(person)
        distroseries = ws_object(launchpad, distroseries)
        archive = ws_object(launchpad, archive)
        recipe.requestBuild(
            archive=archive,
            distroseries=distroseries,
            pocket=PackagePublishingPocket.RELEASE.title,
        )
        e = self.assertRaises(
            Exception,
            recipe.requestBuild,
            archive=archive,
            distroseries=distroseries,
            pocket=PackagePublishingPocket.RELEASE.title,
        )
        self.assertIn(
            "An identical build of this recipe is already pending.", str(e)
        )

    def test_requestBuildRejectUnsupportedDistroSeries(self):
        """Build requests are rejected if they have a bad distroseries."""
        person = self.factory.makePerson()
        archives = [self.factory.makeArchive(owner=person) for x in range(6)]
        distroseries = self.factory.makeDistroSeries()

        recipe, user, launchpad = self.makeRecipe(person)
        distroseries = ws_object(launchpad, distroseries)
        archive = ws_object(launchpad, archives[-1])

        e = self.assertRaises(
            Exception,
            recipe.requestBuild,
            archive=archive,
            distroseries=distroseries,
            pocket=PackagePublishingPocket.RELEASE.title,
        )
        self.assertIn("build against this distro is not allowed", str(e))

    def test_getBuilds(self):
        """SourcePackageRecipe.[pending_|completed_]builds is as expected."""
        person = self.factory.makePerson()
        archives = [self.factory.makeArchive(owner=person) for x in range(4)]
        distroseries = self.factory.makeSourcePackageRecipeDistroseries()

        recipe, user, launchpad = self.makeRecipe(person)
        distroseries = ws_object(launchpad, distroseries)

        builds = []
        for archive in archives:
            archive = ws_object(launchpad, archive)
            build = recipe.requestBuild(
                archive=archive,
                distroseries=distroseries,
                pocket=PackagePublishingPocket.RELEASE.title,
            )
            builds.insert(0, build)
        self.assertEqual(builds, list(recipe.pending_builds))
        self.assertEqual(builds, list(recipe.builds))
        self.assertEqual([], list(recipe.completed_builds))

    def test_getPendingBuildInfo(self):
        """SourcePackageRecipe.getPendingBuildInfo() is as expected."""
        person = self.factory.makePerson()
        archives = [self.factory.makeArchive(owner=person) for x in range(4)]
        distroseries = self.factory.makeSourcePackageRecipeDistroseries()

        recipe, user, launchpad = self.makeRecipe(person)
        ws_distroseries = ws_object(launchpad, distroseries)

        build_info = []
        for archive in archives:
            ws_archive = ws_object(launchpad, archive)
            recipe.requestBuild(
                archive=ws_archive,
                distroseries=ws_distroseries,
                pocket=PackagePublishingPocket.RELEASE.title,
            )
            build_info.insert(
                0,
                {
                    "distroseries": distroseries.displayname,
                    "archive": archive.reference,
                },
            )
        self.assertEqual(build_info, list(recipe.getPendingBuildInfo()))

    def test_query_count_of_webservice_recipe(self):
        owner = self.factory.makePerson()
        recipe = self.factory.makeSourcePackageRecipe(owner=owner)
        webservice = webservice_for_person(owner)
        with person_logged_in(owner):
            url = canonical_url(recipe, force_local_path=True)
        store = Store.of(recipe)
        store.flush()
        store.invalidate()
        with StormStatementRecorder() as recorder:
            webservice.get(url)
        self.assertThat(recorder, HasQueryCount(Equals(25)))


class TestWebserviceBzr(TestWebserviceMixin, BzrMixin, TestCaseWithFactory):
    pass


class TestWebserviceGit(TestWebserviceMixin, GitMixin, TestCaseWithFactory):
    pass
