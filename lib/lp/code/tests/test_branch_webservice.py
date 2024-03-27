# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lazr.restfulclient.errors import BadRequest
from testtools.matchers import LessThan
from zope.component import getUtility
from zope.security.management import endInteraction
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.code.interfaces.branch import IBranchSet
from lp.code.interfaces.linkedbranch import ICanHasLinkedBranch
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    TestCaseWithFactory,
    admin_logged_in,
    api_url,
    launchpadlib_for,
    login_person,
    logout,
    person_logged_in,
    record_two_runs,
    run_with_login,
)
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import webservice_for_person


class TestBranch(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_landing_candidates_constant_queries(self):
        project = self.factory.makeProduct()
        with person_logged_in(project.owner):
            trunk = self.factory.makeBranch(target=project)
            trunk_url = api_url(trunk)
            webservice = webservice_for_person(
                project.owner, permission=OAuthPermission.WRITE_PRIVATE
            )

        def create_mp():
            with admin_logged_in():
                branch = self.factory.makeBranch(
                    target=project,
                    stacked_on=self.factory.makeBranch(
                        target=project,
                        information_type=InformationType.PRIVATESECURITY,
                    ),
                    information_type=InformationType.PRIVATESECURITY,
                )
                self.factory.makeBranchMergeProposal(
                    source_branch=branch, target_branch=trunk
                )

        def list_mps():
            webservice.get(trunk_url + "/landing_candidates")

        list_mps()
        recorder1, recorder2 = record_two_runs(list_mps, create_mp, 2)
        self.assertThat(recorder1, HasQueryCount(LessThan(30)))
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_landing_targets_constant_queries(self):
        project = self.factory.makeProduct()
        with person_logged_in(project.owner):
            source = self.factory.makeBranch(target=project)
            source_url = api_url(source)
            webservice = webservice_for_person(
                project.owner, permission=OAuthPermission.WRITE_PRIVATE
            )

        def create_mp():
            with admin_logged_in():
                branch = self.factory.makeBranch(
                    target=project,
                    stacked_on=self.factory.makeBranch(
                        target=project,
                        information_type=InformationType.PRIVATESECURITY,
                    ),
                    information_type=InformationType.PRIVATESECURITY,
                )
                self.factory.makeBranchMergeProposal(
                    source_branch=source, target_branch=branch
                )

        def list_mps():
            webservice.get(source_url + "/landing_targets")

        list_mps()
        recorder1, recorder2 = record_two_runs(list_mps, create_mp, 2)
        self.assertThat(recorder1, HasQueryCount(LessThan(30)))
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))


class TestBranchOperations(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_createMergeProposal_fails_if_reviewers_and_types_mismatch(self):
        source = self.factory.makeBranch(name="rock")
        source_url = api_url(source)

        target = self.factory.makeBranch(
            owner=source.owner, product=source.product, name="roll"
        )
        target_url = api_url(target)

        lp = launchpadlib_for("test", source.owner.name)
        source = lp.load(source_url)
        target = lp.load(target_url)

        exception = self.assertRaises(
            BadRequest,
            source.createMergeProposal,
            target_branch=target,
            initial_comment="Merge\nit!",
            needs_review=True,
            commit_message="It was merged!\n",
            reviewers=[source.owner.self_link],
            review_types=[],
        )
        self.assertEqual(
            exception.content,
            b"reviewers and review_types must be equal length.",
        )

    def test_getBranchVisibilityInfo(self):
        """Test the test_getBranchVisibilityInfo API."""
        self.factory.makePerson(name="fred")
        owner = self.factory.makePerson()
        visible_branch = self.factory.makeBranch()
        visible_name = visible_branch.unique_name
        invisible_branch = self.factory.makeBranch(
            owner=owner, information_type=InformationType.USERDATA
        )
        invisible_name = removeSecurityProxy(invisible_branch).unique_name
        branches = [visible_branch.unique_name, invisible_name]
        endInteraction()

        lp = launchpadlib_for("test", person=owner)
        person = lp.people["fred"]
        info = lp.branches.getBranchVisibilityInfo(
            person=person, branch_names=branches
        )
        self.assertEqual("Fred", info["person_name"])
        self.assertEqual([visible_name], info["visible_branches"])

    def test_createMergeProposal_fails_if_source_and_target_are_equal(self):
        source = self.factory.makeBranch()
        source_url = api_url(source)
        lp = launchpadlib_for("test", source.owner.name)
        source = lp.load(source_url)
        exception = self.assertRaises(
            BadRequest,
            source.createMergeProposal,
            target_branch=source,
            initial_comment="Merge\nit!",
            needs_review=True,
            commit_message="It was merged!\n",
        )
        self.assertEqual(
            exception.content, b"Source and target branches must be different."
        )

    def test_setOwner(self):
        """Test setOwner via the web API does not raise a 404."""
        branch_owner = self.factory.makePerson(name="fred")
        product = self.factory.makeProduct(name="myproduct")
        self.factory.makeProductBranch(
            name="mybranch", product=product, owner=branch_owner
        )
        self.factory.makeTeam(name="barney", owner=branch_owner)
        endInteraction()

        lp = launchpadlib_for("test", person=branch_owner)
        ws_branch = lp.branches.getByUniqueName(
            unique_name="~fred/myproduct/mybranch"
        )
        ws_new_owner = lp.people["barney"]
        ws_branch.setOwner(new_owner=ws_new_owner)
        # Check the result.
        renamed_branch = lp.branches.getByUniqueName(
            unique_name="~barney/myproduct/mybranch"
        )
        self.assertIsNotNone(renamed_branch)
        self.assertEqual(
            "~barney/myproduct/mybranch", renamed_branch.unique_name
        )


class TestBranchDeletes(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        self.branch_owner = self.factory.makePerson(name="jimhenson")
        self.branch = self.factory.makeBranch(
            owner=self.branch_owner,
            product=self.factory.makeProduct(name="fraggle"),
            name="rock",
        )
        self.lp = launchpadlib_for("test", self.branch.owner.name)

    def test_delete_branch_without_artifacts(self):
        # A branch unencumbered by links or stacked branches deletes.
        target_branch = self.lp.branches.getByUniqueName(
            unique_name="~jimhenson/fraggle/rock"
        )
        target_branch.lp_delete()

        login_person(self.branch_owner)
        branch_set = getUtility(IBranchSet)
        self.assertIs(
            None, branch_set.getByUniqueName("~jimhenson/fraggle/rock")
        )

    def test_delete_branch_with_stacked_branch_errors(self):
        # When trying to delete a branch that cannot be deleted, the
        # error is raised across the webservice instead of oopsing.
        login_person(self.branch_owner)
        self.factory.makeBranch(
            stacked_on=self.branch, owner=self.branch_owner
        )
        logout()
        target_branch = self.lp.branches.getByUniqueName(
            unique_name="~jimhenson/fraggle/rock"
        )
        api_error = self.assertRaises(BadRequest, target_branch.lp_delete)
        self.assertIn(b"Cannot delete", api_error.content)


class TestSlashBranches(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_renders_with_source_package_branch(self):
        mint = self.factory.makeDistribution(name="mint")
        dev = self.factory.makeDistroSeries(
            distribution=mint, version="1.0", name="dev"
        )
        eric = self.factory.makePerson(name="eric")
        branch = self.factory.makePackageBranch(
            distroseries=dev, sourcepackagename="choc", name="tip", owner=eric
        )
        dsp = self.factory.makeDistributionSourcePackage("choc", mint)
        development_package = dsp.development_version
        suite_sourcepackage = development_package.getSuiteSourcePackage(
            PackagePublishingPocket.RELEASE
        )
        suite_sp_link = ICanHasLinkedBranch(suite_sourcepackage)

        registrant = suite_sourcepackage.distribution.owner
        run_with_login(registrant, suite_sp_link.setBranch, branch, registrant)
        branch.updateScannedDetails(None, 0)
        logout()
        lp = launchpadlib_for("test")
        list(lp.branches)

    def test_renders_with_product_branch(self):
        branch = self.factory.makeBranch()
        login_person(branch.product.owner)
        branch.product.development_focus.branch = branch
        branch.updateScannedDetails(None, 0)
        logout()
        lp = launchpadlib_for("test")
        list(lp.branches)
