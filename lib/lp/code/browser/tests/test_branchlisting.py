# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for branch listing."""

import os
import re
from datetime import timedelta
from pprint import pformat

import soupmatchers
from lazr.uri import URI
from lxml import html
from testtools.matchers import Not
from zope.component import getUtility

from lp.app.enums import InformationType
from lp.app.interfaces.services import IService
from lp.code.browser.branchlisting import (
    GroupedDistributionSourcePackageBranchesView,
    SourcePackageBranchesView,
)
from lp.code.model.seriessourcepackagebranch import (
    SeriesSourcePackageBranchSet,
)
from lp.registry.enums import PersonVisibility, SharingPermission
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.personproduct import IPersonProductFactory
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.features.testing import FeatureFixture
from lp.services.webapp import canonical_url
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    BrowserTestCase,
    TestCaseWithFactory,
    admin_logged_in,
    login_person,
    normalize_whitespace,
    person_logged_in,
    time_counter,
)
from lp.testing.factory import remove_security_proxy_and_shout_at_engineer
from lp.testing.layers import DatabaseFunctionalLayer, LaunchpadFunctionalLayer
from lp.testing.matchers import DocTestMatches
from lp.testing.pages import extract_text, find_main_content, find_tag_by_id
from lp.testing.views import create_initialized_view, create_view


class AjaxBatchNavigationMixin:
    def _test_search_batch_request(
        self, context, user=None, view_name="+branches"
    ):
        # A search request with a 'batch_request' query parameter causes the
        # view to just render the next batch of results.
        view = create_initialized_view(
            context,
            name=view_name,
            rootsite="code",
            principal=user,
            query_string="batch_request=True",
        )
        content = view()
        self.assertIsNone(find_main_content(content))
        self.assertIsNotNone(find_tag_by_id(content, "branches-table-listing"))

    def _test_ajax_batch_navigation_feature_flag(
        self, context, user=None, view_name="+branches"
    ):
        # The Javascript to wire up the ajax batch navigation behaviour is
        # correctly hidden behind a feature flag.
        flags = {"ajax.batch_navigator.enabled": "true"}
        with FeatureFixture(flags):
            view = create_initialized_view(
                context, name=view_name, rootsite="code", principal=user
            )
            self.assertTrue(
                "Y.lp.app.batchnavigator.BatchNavigatorHooks" in view()
            )
        view = create_initialized_view(
            context, name=view_name, rootsite="code", principal=user
        )
        self.assertFalse(
            "Y.lp.app.batchnavigator.BatchNavigatorHooks" in view()
        )

    def _test_non_batch_template(self, context, expected_template):
        # The correct template is used for non batch requests.
        view = create_view(context, "+bugs")
        self.assertEqual(
            expected_template, os.path.basename(view.template.filename)
        )

    def _test_batch_template(self, context):
        # The correct template is used for batch requests.
        view = create_view(context, "+bugs", query_string="batch_request=True")
        self.assertEqual(
            view.bugtask_table_template.filename, view.template.filename
        )


class TestPersonOwnedBranchesView(
    TestCaseWithFactory, AjaxBatchNavigationMixin
):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.user = self.factory.makePerson()
        login_person(self.user)

        self.barney = self.factory.makePerson(name="barney")
        self.bambam = self.factory.makeProduct(name="bambam")

        time_gen = time_counter(delta=timedelta(days=-1))
        self.branches = [
            self.factory.makeProductBranch(
                product=self.bambam,
                owner=self.barney,
                date_created=next(time_gen),
            )
            for i in range(10)
        ]
        self.bug = self.factory.makeBug()
        self.bug.linkBranch(self.branches[0], self.barney)
        self.spec = self.factory.makeSpecification()
        self.spec.linkBranch(self.branches[1], self.barney)

    def test_branch_ids_with_bug_links(self):
        # _branches_for_current_batch should return a list of all branches in
        # the current batch.
        branch_ids = {self.branches[0].id}

        view = create_initialized_view(
            self.barney, name="+branches", rootsite="code"
        )
        self.assertEqual(view.branches().branch_ids_with_bug_links, branch_ids)

    def test_branch_ids_with_spec_links(self):
        # _branches_for_current_batch should return a list of all branches in
        # the current batch.
        branch_ids = {self.branches[1].id}

        view = create_initialized_view(
            self.barney, name="+branches", rootsite="code"
        )
        self.assertEqual(
            view.branches().branch_ids_with_spec_links, branch_ids
        )

    def test_branch_ids_with_merge_propoasls(self):
        # _branches_for_current_batch should return a list of all branches in
        # the current batch.
        branch_ids = set()
        view = create_initialized_view(
            self.barney, name="+branches", rootsite="code"
        )
        self.assertEqual(
            view.branches().branch_ids_with_merge_proposals, branch_ids
        )

    def test_tip_revisions(self):
        # _branches_for_current_batch should return a list of all branches in
        # the current batch.
        # The batch size is 6
        branch_ids = [branch.id for branch in self.branches[:6]]
        tip_revisions = {}
        for branch_id in branch_ids:
            tip_revisions[branch_id] = None

        view = create_initialized_view(
            self.barney, name="+branches", rootsite="code"
        )
        self.assertEqual(view.branches().tip_revisions, tip_revisions)

    def test_search_batch_request(self):
        # A search request with a 'batch_request' query parameter causes the
        # view to just render the next batch of results.
        self._test_search_batch_request(self.barney, self.barney)

    def test_ajax_batch_navigation_feature_flag(self):
        # The Javascript to wire up the ajax batch navigation behaviour is
        # correctly hidden behind a feature flag.
        self._test_ajax_batch_navigation_feature_flag(self.barney, self.barney)

    def test_non_batch_template(self):
        # The correct template is used for non batch requests.
        self._test_non_batch_template(
            self.barney, "buglisting-embedded-advanced-search.pt"
        )

    def test_batch_template(self):
        # The correct template is used for batch requests.
        self._test_batch_template(self.barney)

    def test_proprietary_branch_for_series_user_has_artifact_grant(self):
        # A user can be the owner of a branch which is the series
        # branch of a proprietary product, and the user may only have
        # an access grant for the branch but no policy grant for the
        # product. In this case, the branch owner does get any information
        # about the series.
        product_owner = self.factory.makePerson()
        product = self.factory.makeProduct(
            owner=product_owner, information_type=InformationType.PROPRIETARY
        )
        branch_owner = self.factory.makePerson()
        sharing_service = getUtility(IService, "sharing")
        with person_logged_in(product_owner):
            # The branch owner needs to have a policy grant at first
            # so that they can create the branch.
            sharing_service.sharePillarInformation(
                product,
                branch_owner,
                product_owner,
                {InformationType.PROPRIETARY: SharingPermission.ALL},
            )
            proprietary_branch = self.factory.makeProductBranch(
                product,
                owner=branch_owner,
                name="special-branch",
                information_type=InformationType.PROPRIETARY,
            )
            series = self.factory.makeProductSeries(
                product=product, branch=proprietary_branch
            )
            sharing_service.deletePillarGrantee(
                product, branch_owner, product_owner
            )
        # Admin help is needed: Product owners do not have the
        # permission to create artifact grants for branches they
        # do not own, and the branch owner does have the permission
        # to issue grants related to the product.
        with admin_logged_in():
            sharing_service.ensureAccessGrants(
                [branch_owner], product_owner, branches=[proprietary_branch]
            )

        with person_logged_in(branch_owner):
            view = create_initialized_view(
                branch_owner,
                name="+branches",
                rootsite="code",
                principal=branch_owner,
            )
            self.assertIn(proprietary_branch, view.branches().batch)
            # The product series related to the branch is not returned
            # for the branch owner.
            self.assertEqual(
                [], view.branches().getProductSeries(proprietary_branch)
            )

        with person_logged_in(product_owner):
            # The product series related to the branch is returned
            # for the product owner.
            view = create_initialized_view(
                branch_owner,
                name="+branches",
                rootsite="code",
                principal=branch_owner,
            )
            self.assertEqual(
                [series], view.branches().getProductSeries(proprietary_branch)
            )


class TestSimplifiedPersonBranchesView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super().setUp()
        self.user = self.factory.makePerson()
        self.person = self.factory.makePerson(name="barney")
        self.team = self.factory.makeTeam(owner=self.person)
        self.product = self.factory.makeProduct(name="bambam")

        self.code_base_url = "http://code.launchpad.test/~barney"
        self.base_url = "http://launchpad.test/~barney"
        self.default_target = self.person

    def makeABranch(self):
        return self.factory.makeAnyBranch(owner=self.person)

    def get_branch_list_page(self, target=None, page_name="+branches"):
        if target is None:
            target = self.default_target
        with person_logged_in(self.user):
            return create_initialized_view(
                target, page_name, rootsite="code", principal=self.user
            )()

    def test_branch_list_empty(self):
        page = self.get_branch_list_page()
        empty_message_matcher = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "Empty message",
                "div",
                text="There are no branches related to Barney "
                "in Launchpad today.",
            )
        )
        self.assertThat(page, empty_message_matcher)

    def test_branch_list_branches_link(self):
        # The link to the owned branches is always displayed.
        branches_matcher = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "Branches link",
                "a",
                text="Branches",
                attrs={"href": self.code_base_url},
            )
        )
        page = self.get_branch_list_page(page_name="+branches")
        self.assertThat(page, branches_matcher)

    def test_branch_list_activereviews_link(self):
        # The link to the active reviews is always displayed.
        active_review_matcher = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "Active reviews link",
                "a",
                text="Active reviews",
                attrs={"href": self.base_url + "/+activereviews"},
            )
        )
        page = self.get_branch_list_page()
        self.assertThat(page, active_review_matcher)

    def test_branch_list_recipes_link(self):
        # The link to the source package recipes is always displayed.
        page = self.get_branch_list_page()
        recipes_matcher = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "Source package recipes link",
                "a",
                text="Source package recipes",
                attrs={"href": self.base_url + "/+recipes"},
            )
        )
        if IPerson.providedBy(self.default_target):
            self.assertThat(page, recipes_matcher)
        else:
            self.assertThat(page, Not(recipes_matcher))

    def test_branch_list_snaps_link(self):
        # The link to the snap packages is always displayed.
        snaps_matcher = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "Snap packages link",
                "a",
                text="Snap packages",
                attrs={"href": self.base_url + "/+snaps"},
            )
        )
        page = self.get_branch_list_page()
        if IPerson.providedBy(self.default_target):
            self.assertThat(page, snaps_matcher)
        else:
            self.assertThat(page, Not(snaps_matcher))


class TestSimplifiedPersonProductBranchesView(
    TestSimplifiedPersonBranchesView
):
    def setUp(self):
        super().setUp()
        self.person_product = getUtility(IPersonProductFactory).create(
            self.person, self.product
        )
        self.team_product = getUtility(IPersonProductFactory).create(
            self.team, self.product
        )
        self.code_base_url = "http://code.launchpad.test/~barney/bambam"
        self.base_url = "http://launchpad.test/~barney/bambam"
        self.default_target = self.person_product

    def makeABranch(self):
        return self.factory.makeAnyBranch(
            owner=self.person, product=self.product
        )

    def test_branch_list_h1(self):
        self.makeABranch()
        page = self.get_branch_list_page()
        h1_matcher = soupmatchers.HTMLContains(
            soupmatchers.Tag("Title", "h1", text="Branches of Bambam")
        )
        self.assertThat(page, h1_matcher)

    def test_branch_list_empty(self):
        page = self.get_branch_list_page()
        empty_message_matcher = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "Empty message",
                "div",
                text="There are no branches of Bambam for Barney "
                "in Launchpad today.",
            )
        )
        self.assertThat(page, empty_message_matcher)

    def test_git_link(self):
        page = self.get_branch_list_page()
        self.assertNotIn("View Git repositories", page)

        self.factory.makeGitRepository(owner=self.person, target=self.product)
        page = self.get_branch_list_page()
        self.assertIn("View Git repositories", page)


class TestSourcePackageBranchesView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_distroseries_links(self):
        # There are some links at the bottom of the page to other
        # distroseries.
        distro = self.factory.makeDistribution()
        sourcepackagename = self.factory.makeSourcePackageName()
        packages = {}
        for version in ("1.0", "2.0", "3.0"):
            series = self.factory.makeDistroSeries(
                distribution=distro, version=version
            )
            package = self.factory.makeSourcePackage(
                distroseries=series, sourcepackagename=sourcepackagename
            )
            packages[version] = package
        request = LaunchpadTestRequest()
        view = SourcePackageBranchesView(packages["2.0"], request)
        self.assertEqual(
            [
                dict(
                    series_name=packages["3.0"].distroseries.displayname,
                    package=packages["3.0"],
                    linked=True,
                    num_branches="0 branches",
                    dev_focus_css="sourcepackage-dev-focus",
                ),
                dict(
                    series_name=packages["2.0"].distroseries.displayname,
                    package=packages["2.0"],
                    linked=False,
                    num_branches="0 branches",
                    dev_focus_css="sourcepackage-not-dev-focus",
                ),
                dict(
                    series_name=packages["1.0"].distroseries.displayname,
                    package=packages["1.0"],
                    linked=True,
                    num_branches="0 branches",
                    dev_focus_css="sourcepackage-not-dev-focus",
                ),
            ],
            list(view.series_links),
        )


class TestDistributionBranchesView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_git_link(self):
        dsp = self.factory.makeDistributionSourcePackage()
        page = create_initialized_view(dsp.distribution, "+branches")()
        self.assertNotIn("View Git repositories", page)

        self.factory.makeGitRepository(target=dsp)
        page = create_initialized_view(dsp.distribution, "+branches")()
        self.assertIn("View Git repositories", page)


class TestGroupedDistributionSourcePackageBranchesView(TestCaseWithFactory):
    """Test the groups for the branches of distribution source packages."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        # Make a distro with some series, a source package name, and a distro
        # source package.
        self.distro = self.factory.makeDistribution()
        for version in ("1.0", "2.0", "3.0"):
            self.factory.makeDistroSeries(
                distribution=self.distro, version=version
            )
        self.sourcepackagename = self.factory.makeSourcePackageName()
        self.distro_source_package = (
            self.factory.makeDistributionSourcePackage(
                distribution=self.distro,
                sourcepackagename=self.sourcepackagename,
            )
        )

    def test_groups_with_no_branches(self):
        # If there are no branches for a series, the groups are not there.
        view = GroupedDistributionSourcePackageBranchesView(
            self.distro_source_package, LaunchpadTestRequest()
        )
        self.assertEqual([], view.groups)

    def makeBranches(self, branch_count, official_count=0):
        """Make some package branches.

        Make `branch_count` branches, and make `official_count` of those
        official branches.
        """
        distroseries = self.distro.series[0]
        # Make the branches created in the past in order.
        time_gen = time_counter(delta=timedelta(days=-1))
        branches = [
            self.factory.makePackageBranch(
                distroseries=distroseries,
                sourcepackagename=self.sourcepackagename,
                date_created=next(time_gen),
            )
            for i in range(branch_count)
        ]

        official = []
        # Sort the pocket items so RELEASE is last, and thus first popped.
        pockets = sorted(PackagePublishingPocket.items, reverse=True)
        for i in range(official_count):
            branch = branches.pop()
            pocket = pockets.pop()
            SeriesSourcePackageBranchSet.new(
                distroseries,
                pocket,
                self.sourcepackagename,
                branch,
                branch.owner,
            )
            official.append(branch)

        return distroseries, branches, official

    def assertMoreBranchCount(self, expected, series):
        """Check that the more-branch-count is the expected value."""
        view = GroupedDistributionSourcePackageBranchesView(
            self.distro_source_package, LaunchpadTestRequest()
        )
        series_group = view.groups[0]
        self.assertEqual(expected, series_group["more-branch-count"])

    def test_more_branch_count_zero(self):
        # If there are less than six branches, the more-branch-count is zero.
        series, ignored, ignored = self.makeBranches(5)
        self.assertMoreBranchCount(0, series)

    def test_more_branch_count_nonzero(self):
        # If there are more than five branches, the more-branch-count is the
        # total branch count less five.
        series, ignored, ignored = self.makeBranches(8)
        self.assertMoreBranchCount(3, series)

    def assertGroupBranchesEqual(self, expected, series):
        """Check that the branches part of the series dict match."""
        view = GroupedDistributionSourcePackageBranchesView(
            self.distro_source_package, LaunchpadTestRequest()
        )
        series_group = view.groups[0]
        branches = series_group["branches"]
        self.assertEqual(
            len(expected),
            len(branches),
            "%s different length to %s"
            % (pformat(expected), pformat(branches)),
        )
        for b1, b2 in zip(expected, branches):
            # Since one is a branch and the other is a decorated branch,
            # just check the ids.
            self.assertEqual(b1.id, b2.id)

    def test_series_branch_order_no_official(self):
        # If there are no official branches, then the branches are in most
        # recently modified order, with at most five in the list.
        series, branches, official = self.makeBranches(8)
        self.assertGroupBranchesEqual(branches[:5], series)

    def test_series_branch_order_official_first(self):
        # If there is an official branch, it comes first in the list.
        series, branches, official = self.makeBranches(8, 1)
        expected = official + branches[:4]
        self.assertGroupBranchesEqual(expected, series)

    def test_series_branch_order_two_three(self):
        # If there are more than two official branches, and there are three or
        # more user branches, then only two of the official branches will be
        # shown, ordered by pocket.
        series, branches, official = self.makeBranches(8, 3)
        expected = official[:2] + branches[:3]
        self.assertGroupBranchesEqual(expected, series)

    def test_series_branch_order_three_two(self):
        # If there are more than two official branches, but there are less
        # than three user branches, then official branches are added in until
        # there are at most five branches.
        series, branches, official = self.makeBranches(6, 4)
        expected = official[:3] + branches
        self.assertGroupBranchesEqual(expected, series)

    def test_distributionsourcepackage_branch(self):
        source_package = self.factory.makeSourcePackage()
        dsp = source_package.distribution.getSourcePackage(
            source_package.sourcepackagename
        )
        branch = self.factory.makeBranch(sourcepackage=source_package)
        view = create_initialized_view(dsp, name="+branches", rootsite="code")
        root = html.fromstring(view())
        [series_branches_table] = root.cssselect("table#series-branches")
        series_branches_last_row = series_branches_table.cssselect("tr")[-1]
        self.assertThat(
            series_branches_last_row.text_content(),
            DocTestMatches("%s ... ago" % branch.displayname),
        )

    def test_git_link(self):
        page = create_initialized_view(
            self.distro_source_package, name="+branches", rootsite="code"
        )()
        self.assertNotIn("View Git repositories", page)

        self.factory.makeGitRepository(target=self.distro_source_package)
        page = create_initialized_view(
            self.distro_source_package, name="+branches", rootsite="code"
        )()
        self.assertIn("View Git repositories", page)


class TestDevelopmentFocusPackageBranches(TestCaseWithFactory):
    """Make sure that the bzr_identity of the branches are correct."""

    layer = DatabaseFunctionalLayer

    def test_package_development_focus(self):
        # Check the bzr_identity of a development focus package branch.
        branch = self.factory.makePackageBranch()
        SeriesSourcePackageBranchSet.new(
            branch.distroseries,
            PackagePublishingPocket.RELEASE,
            branch.sourcepackagename,
            branch,
            branch.owner,
        )
        identity = "lp://dev/%s/%s" % (
            branch.distribution.name,
            branch.sourcepackagename.name,
        )
        self.assertEqual(identity, branch.bzr_identity)
        # Now confirm that we get the same through the view.
        view = create_initialized_view(
            branch.distribution, name="+branches", rootsite="code"
        )
        # There is only one branch.
        batch = view.branches()
        [view_branch] = batch.branches
        self.assertStatementCount(0, getattr, view_branch, "bzr_identity")
        self.assertEqual(identity, view_branch.bzr_identity)


class TestProductSeriesTemplate(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_product_series_link(self):
        # The link from a series branch's listing to the series goes to the
        # series on the main site, not the code site.
        branch = self.factory.makeProductBranch()
        series = self.factory.makeProductSeries(product=branch.product)
        series_name = series.name
        remove_security_proxy_and_shout_at_engineer(series).branch = branch
        browser = self.getUserBrowser(
            canonical_url(branch.product, rootsite="code")
        )
        link = browser.getLink(re.compile("^" + series_name + "$"))
        self.assertEqual("launchpad.test", URI(link.url).host)


class TestPersonBranchesPage(BrowserTestCase):
    """Tests for the person branches page.

    This is the default page shown for a person on the code subdomain.
    """

    layer = DatabaseFunctionalLayer

    def _make_branch_for_private_team(self):
        owner = self.factory.makePerson()
        private_team = self.factory.makeTeam(
            name="shh",
            displayname="Shh",
            owner=owner,
            visibility=PersonVisibility.PRIVATE,
        )
        member = self.factory.makePerson(email="member@example.com")
        with person_logged_in(owner):
            private_team.addMember(member, owner)
            branch = self.factory.makeProductBranch(owner=private_team)
        return private_team, member, branch

    def test_private_team_membership_for_team_member(self):
        # If the logged in user can see the private teams, they are shown in
        # the related 'Branches owned by' section at the bottom of the page.
        private_team, member, branch = self._make_branch_for_private_team()
        browser = self.getUserBrowser(
            canonical_url(member, rootsite="code"), member
        )
        branches = find_tag_by_id(browser.contents, "portlet-team-branches")
        text = extract_text(branches)
        self.assertTextMatchesExpressionIgnoreWhitespace(
            "Branches owned by Shh", text
        )

    def test_private_team_membership_for_non_member(self):
        # Make sure that private teams are not shown (or attempted to be
        # shown) for people who can not see the private teams.
        private_team, member, branch = self._make_branch_for_private_team()
        browser = self.getUserBrowser(canonical_url(member, rootsite="code"))
        branches = find_tag_by_id(browser.contents, "portlet-team-branches")
        # Since there are no teams with branches that the user can see, the
        # portlet isn't shown.
        self.assertIs(None, branches)

    def test_branch_listing_last_modified(self):
        branch = self.factory.makeProductBranch()
        view = create_initialized_view(
            branch.product, name="+branches", rootsite="code"
        )
        self.assertIn("a moment ago", view())

    def test_no_branch_message_escaped(self):
        # make sure we escape any information put into the no branch message
        badname = "<script>Test</script>"
        escapedname = "no branches related to &lt;script&gt;Test"
        baduser = self.factory.makePerson(displayname=badname)
        browser = self.getViewBrowser(baduser, rootsite="code")
        # the content should not appear in tact because it's been escaped
        self.assertTrue(badname not in browser.contents)
        self.assertTrue(escapedname in browser.contents)

    def test_git_link(self):
        person = self.factory.makePerson()
        page = create_initialized_view(person, "+branches")()
        self.assertNotIn("View Git repositories", page)

        self.factory.makeGitRepository(owner=person)
        page = create_initialized_view(person, "+branches")()
        self.assertIn("View Git repositories", page)


class TestProjectGroupBranches(TestCaseWithFactory, AjaxBatchNavigationMixin):
    """Test for the project group branches page."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        self.projectgroup = self.factory.makeProject()

    def test_no_branches_gets_message_not_listing(self):
        # If there are no product branches on the project's products, then
        # the view shows the no code hosting message instead of a listing.
        self.factory.makeProduct(projectgroup=self.projectgroup)
        view = create_initialized_view(
            self.projectgroup, name="+branches", rootsite="code"
        )
        displayname = self.projectgroup.displayname
        expected_text = normalize_whitespace(
            "Launchpad does not know where any of %s's "
            "projects host their code." % displayname
        )
        no_branch_div = find_tag_by_id(view(), "no-branchtable")
        text = normalize_whitespace(extract_text(no_branch_div))
        self.assertEqual(expected_text, text)

    def test_branches_get_listing(self):
        # If a product has a branch, then the project group view has a
        # branch listing.
        product = self.factory.makeProduct(projectgroup=self.projectgroup)
        self.factory.makeProductBranch(product=product)
        view = create_initialized_view(
            self.projectgroup, name="+branches", rootsite="code"
        )
        table = find_tag_by_id(view(), "branchtable")
        self.assertIsNot(None, table)

    def test_search_batch_request(self):
        # A search request with a 'batch_request' query parameter causes the
        # view to just render the next batch of results.
        product = self.factory.makeProduct(projectgroup=self.projectgroup)
        self._test_search_batch_request(product, view_name="+branches")

    def test_ajax_batch_navigation_feature_flag(self):
        # The Javascript to wire up the ajax batch navigation behaviour is
        # correctly hidden behind a feature flag.
        product = self.factory.makeProduct(projectgroup=self.projectgroup)
        for i in range(10):
            self.factory.makeProductBranch(product=product)
        self._test_ajax_batch_navigation_feature_flag(
            product, view_name="+branches"
        )

    def test_non_batch_template(self):
        # The correct template is used for non batch requests.
        product = self.factory.makeProduct(projectgroup=self.projectgroup)
        self._test_non_batch_template(product, "buglisting-default.pt")

    def test_batch_template(self):
        # The correct template is used for batch requests.
        product = self.factory.makeProduct(projectgroup=self.projectgroup)
        self._test_batch_template(product)
