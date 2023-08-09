# Copyright 2012-2021 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test views that manage sharing."""

import json

from fixtures import FakeLogger
from lazr.restful.interfaces import IJSONRequestCache
from lazr.restful.utils import get_current_web_service_request
from testtools.matchers import LessThan, MatchesException, Not, Raises
from zope.component import getUtility
from zope.traversing.browser.absoluteurl import absoluteURL

from lp.app.enums import InformationType
from lp.app.interfaces.services import IService
from lp.oci.interfaces.ocirecipe import OCI_RECIPE_ALLOW_CREATE
from lp.registry.enums import (
    BranchSharingPolicy,
    BugSharingPolicy,
    PersonVisibility,
    TeamMembershipPolicy,
)
from lp.registry.interfaces.accesspolicy import IAccessPolicyGrantFlatSource
from lp.registry.model.pillar import PillarPerson
from lp.services.beautifulsoup import BeautifulSoup
from lp.services.config import config
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.interfaces import StormRangeFactoryError
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    admin_logged_in,
    login_person,
    logout,
    normalize_whitespace,
    person_logged_in,
    record_two_runs,
)
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import extract_text, find_tag_by_id, setupBrowserForUser
from lp.testing.views import create_initialized_view, create_view


class SharingBaseTestCase(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    pillar_type = None

    def setUp(self):
        super().setUp()
        self.driver = self.factory.makePerson()
        self.owner = self.factory.makePerson()
        if self.pillar_type == "distribution":
            self.pillar = self.factory.makeDistribution(
                owner=self.owner, driver=self.driver
            )
        elif self.pillar_type == "product":
            self.pillar = self.factory.makeProduct(
                owner=self.owner,
                driver=self.driver,
                bug_sharing_policy=BugSharingPolicy.PUBLIC,
                branch_sharing_policy=BranchSharingPolicy.PUBLIC,
            )
        self.access_policy = self.factory.makeAccessPolicy(
            pillar=self.pillar, type=InformationType.PROPRIETARY
        )
        self.grantees = []

    def makeGrantee(self, name=None):
        grantee = self.factory.makePerson(name=name)
        self.factory.makeAccessPolicyGrant(self.access_policy, grantee)
        return grantee

    def makeArtifactGrantee(
        self,
        grantee=None,
        with_bug=True,
        with_branch=False,
        with_gitrepository=True,
        security=False,
    ):
        if grantee is None:
            grantee = self.factory.makePerson()

        branch = None
        gitrepository = None
        bug = None
        artifacts = []

        if with_branch and self.pillar_type == "product":
            branch = self.factory.makeBranch(
                product=self.pillar,
                owner=self.pillar.owner,
                information_type=InformationType.PRIVATESECURITY,
            )
            artifacts.append(self.factory.makeAccessArtifact(concrete=branch))

        if with_gitrepository and self.pillar_type == "product":
            gitrepository = self.factory.makeGitRepository(
                target=self.pillar,
                owner=self.pillar.owner,
                information_type=InformationType.PRIVATESECURITY,
            )
            artifacts.append(
                self.factory.makeAccessArtifact(concrete=gitrepository)
            )

        if with_bug:
            if security:
                owner = self.factory.makePerson()
            else:
                owner = self.pillar.owner
            bug = self.factory.makeBug(
                target=self.pillar,
                owner=owner,
                information_type=InformationType.USERDATA,
            )
            artifacts.append(self.factory.makeAccessArtifact(concrete=bug))

        for artifact in artifacts:
            self.factory.makeAccessArtifactGrant(
                artifact=artifact, grantee=grantee, grantor=self.pillar.owner
            )
        return grantee

    def setupSharing(self, grantees):
        with person_logged_in(self.owner):
            # Make grants in ascending order so we can slice off the first
            # elements in the pillar observer results to check batching.
            for x in range(10):
                self.makeArtifactGrantee()
                grantee = self.makeGrantee("name%s" % x)
                grantees.append(grantee)


class PillarSharingDetailsMixin:
    """Test the pillar sharing details view."""

    def getPillarPerson(self, person=None, security=False):
        person = self.makeArtifactGrantee(person, True, True, True, security)
        return PillarPerson(self.pillar, person)

    def test_view_filters_security_wisely(self):
        # There are bugs in the sharingdetails view that not everyone with
        # `launchpad.Driver` -- the permission level for the page -- should be
        # able to see.
        pillarperson = self.getPillarPerson(security=True)
        logout()
        login_person(self.driver)
        view = create_initialized_view(pillarperson, "+index")
        # The page loads
        self.assertEqual(pillarperson.person.displayname, view.page_title)
        # The bug, which is not shared with the driver, is not included.
        self.assertEqual(0, view.shared_bugs_count)

    def test_view_traverses_plus_sharingdetails(self):
        # The traversed url in the app is pillar/+sharing/person
        # We have to do some fun url hacking to force the traversal a user
        # encounters.
        pillarperson = self.getPillarPerson()
        expected = "Sharing details for %s : Sharing : %s" % (
            pillarperson.person.displayname,
            pillarperson.pillar.displayname,
        )
        url = "http://launchpad.test/%s/+sharing/%s" % (
            pillarperson.pillar.name,
            pillarperson.person.name,
        )
        browser = self.getUserBrowser(user=self.owner, url=url)
        self.assertEqual(expected, browser.title)

    def test_no_sharing_message(self):
        # If there is no sharing between pillar and person, a suitable message
        # is displayed.
        # We have to do some fun url hacking to force the traversal a user
        # encounters.
        pillarperson = PillarPerson(self.pillar, self.factory.makePerson())
        url = "http://launchpad.test/%s/+sharing/%s" % (
            pillarperson.pillar.name,
            pillarperson.person.name,
        )
        browser = self.getUserBrowser(user=self.owner, url=url)
        self.assertIn(
            "There are no shared bugs, Bazaar branches, Git repositories, "
            "snap recipes, OCI recipes or blueprints.",
            normalize_whitespace(browser.contents),
        )

    def test_init_works(self):
        # The view works with a feature flag.
        pillarperson = self.getPillarPerson()
        view = create_initialized_view(pillarperson, "+index")
        self.assertEqual(pillarperson.person.displayname, view.page_title)
        self.assertEqual(1, view.shared_bugs_count)

    def test_view_data_model(self):
        # Test that the json request cache contains the view data model.
        pillarperson = self.getPillarPerson()
        view = create_initialized_view(pillarperson, "+index")
        bugtask = list(view.bugtasks)[0]
        bug = bugtask.bug
        cache = IJSONRequestCache(view.request)
        request = get_current_web_service_request()
        self.assertEqual(
            {
                "self_link": absoluteURL(pillarperson.person, request),
                "displayname": pillarperson.person.displayname,
            },
            cache.objects.get("grantee"),
        )
        self.assertEqual(
            {
                "self_link": absoluteURL(pillarperson.pillar, request),
            },
            cache.objects.get("pillar"),
        )
        self.assertEqual(
            {
                "bug_id": bug.id,
                "bug_summary": bug.title,
                "bug_importance": bugtask.importance.title.lower(),
                "information_type": bug.information_type.title,
                "web_link": canonical_url(bugtask, path_only_if_possible=True),
                "self_link": absoluteURL(bug, request),
            },
            cache.objects.get("bugs")[0],
        )
        if self.pillar_type == "product":
            branch = list(view.branches)[0]
            self.assertEqual(
                {
                    "branch_id": branch.id,
                    "branch_name": branch.unique_name,
                    "information_type": branch.information_type.title,
                    "web_link": canonical_url(
                        branch, path_only_if_possible=True
                    ),
                    "self_link": absoluteURL(branch, request),
                },
                cache.objects.get("branches")[0],
            )
            gitrepository = list(view.gitrepositories)[0]
            self.assertEqual(
                {
                    "repository_id": gitrepository.id,
                    "repository_name": gitrepository.unique_name,
                    "information_type": gitrepository.information_type.title,
                    "web_link": canonical_url(
                        gitrepository, path_only_if_possible=True
                    ),
                    "self_link": absoluteURL(gitrepository, request),
                },
                cache.objects.get("gitrepositories")[0],
            )

    def test_view_query_count(self):
        # Test that the view bulk loads artifacts.
        person = self.factory.makePerson()
        pillarperson = PillarPerson(self.pillar, person)
        recorder1, recorder2 = record_two_runs(
            lambda: create_initialized_view(pillarperson, "+index"),
            lambda: self.makeArtifactGrantee(person, True, True, True, False),
            5,
            login_method=lambda: login_person(self.owner),
        )
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))


class TestProductSharingDetailsView(
    SharingBaseTestCase, PillarSharingDetailsMixin
):
    pillar_type = "product"

    def setUp(self):
        super().setUp()
        login_person(self.owner)


class TestDistributionSharingDetailsView(
    SharingBaseTestCase, PillarSharingDetailsMixin
):
    pillar_type = "distribution"

    def setUp(self):
        super().setUp()
        login_person(self.owner)


class PillarSharingViewTestMixin:
    """Test the PillarSharingView."""

    def test_sharing_menu(self):
        url = canonical_url(self.pillar)
        sharing_url = canonical_url(self.pillar, view_name="+sharing")
        browser = setupBrowserForUser(user=self.driver)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        sharing_menu = soup.find("a", {"href": sharing_url})
        self.assertIsNotNone(sharing_menu)

    def test_picker_config(self):
        # Test the config passed to the disclosure sharing picker.
        view = create_view(self.pillar, name="+sharing")
        picker_config = json.loads(view.json_sharing_picker_config)
        self.assertTrue("vocabulary_filters" in picker_config)
        self.assertEqual("Share project information", picker_config["header"])
        self.assertEqual(
            "Search for user or exclusive team with whom to share",
            picker_config["steptitle"],
        )
        self.assertEqual("NewPillarGrantee", picker_config["vocabulary"])

    def test_view_data_model(self):
        # Test that the json request cache contains the view data model.
        view = create_initialized_view(self.pillar, name="+sharing")
        cache = IJSONRequestCache(view.request)
        self.assertIsNotNone(cache.objects.get("information_types"))
        self.assertIsNotNone(cache.objects.get("branch_sharing_policies"))
        self.assertIsNotNone(cache.objects.get("bug_sharing_policies"))
        self.assertIsNotNone(cache.objects.get("sharing_permissions"))
        self.assertIsNotNone(
            cache.objects.get("specification_sharing_policies")
        )
        batch_size = config.launchpad.default_batch_size
        apgfs = getUtility(IAccessPolicyGrantFlatSource)
        grantees = apgfs.findGranteePermissionsByPolicy(
            [self.access_policy], self.grantees[:batch_size]
        )
        sharing_service = getUtility(IService, "sharing")
        grantee_data = sharing_service.jsonGranteeData(grantees)
        self.assertContentEqual(
            grantee_data, cache.objects.get("grantee_data")
        )

    def test_view_batch_data(self):
        # Test the expected batching data is in the json request cache.
        view = create_initialized_view(self.pillar, name="+sharing")
        cache = IJSONRequestCache(view.request)
        # Test one expected data value (there are many).
        next_batch = view.grantees().batch.nextBatch()
        self.assertContentEqual(
            next_batch.range_memo, cache.objects.get("next")["memo"]
        )

    def test_view_range_factory(self):
        # Test the view range factory is properly configured.
        view = create_initialized_view(self.pillar, name="+sharing")
        range_factory = view.grantees().batch.range_factory

        def test_range_factory():
            row = range_factory.resultset.get_plain_result_set()[0]
            range_factory.getOrderValuesFor(row)

        self.assertThat(
            test_range_factory,
            Not(Raises(MatchesException(StormRangeFactoryError))),
        )

    def test_view_query_count(self):
        # Test the query count is within expected limit.
        view = create_view(self.pillar, name="+sharing")
        with StormStatementRecorder() as recorder:
            view.initialize()
        self.assertThat(recorder, HasQueryCount(LessThan(11)))

    def test_view_invisible_information_types(self):
        # Test the expected invisible information type  data is in the
        # json request cache.
        with person_logged_in(self.pillar.owner):
            getUtility(IService, "sharing").deletePillarGrantee(
                self.pillar, self.pillar.owner, self.pillar.owner
            )
        view = create_initialized_view(self.pillar, name="+sharing")
        cache = IJSONRequestCache(view.request)
        self.assertContentEqual(
            ["Private Security", "Private"],
            cache.objects.get("invisible_information_types"),
        )

    def run_sharing_message_test(self, pillar, owner, public):
        with person_logged_in(owner):
            public_pillar_sharing_info = (
                "Everyone can see %s's public information."
                % pillar.displayname
            )
            url = canonical_url(pillar, view_name="+sharing")
        browser = setupBrowserForUser(user=owner)
        browser.open(url)
        if public:
            self.assertTrue(public_pillar_sharing_info in browser.contents)
            self.assertFalse(
                "This project has no public information." in browser.contents
            )
        else:
            self.assertFalse(public_pillar_sharing_info in browser.contents)
            self.assertTrue(
                "This project has no public information." in browser.contents
            )

    def test_who_its_shared_with__public_pillar(self):
        # For public projects and distributions, the sharing page
        # shows the message "Everyone can see project's public
        # information".
        self.run_sharing_message_test(
            self.pillar, self.pillar.owner, public=True
        )

    def test_shared_with_normally_invisible_private_team(self):
        # If a pillar is shared with a private team, then we disclose
        # information about the share to users who can see +sharing even if
        # they can't normally see that private team.
        self.pushConfig("launchpad", default_batch_size=75)
        with admin_logged_in():
            team = self.factory.makeTeam(visibility=PersonVisibility.PRIVATE)
            team_name = team.name
            self.factory.makeAccessPolicyGrant(self.access_policy, team)
        with person_logged_in(self.pillar.owner):
            view = create_initialized_view(self.pillar, name="+sharing")
            cache = IJSONRequestCache(view.request)
            self.assertIn(
                team_name,
                [grantee["name"] for grantee in cache.objects["grantee_data"]],
            )

    def test_pillar_person_sharing_with_team(self):
        self.useFixture(FeatureFixture({OCI_RECIPE_ALLOW_CREATE: "on"}))
        team = self.factory.makeTeam(
            membership_policy=TeamMembershipPolicy.MODERATED
        )
        # Add 4 members to the team, so we should have the team owner + 4
        # other members with access to the artifacts.
        for i in range(4):
            self.factory.makePerson(member_of=[team])

        items = [
            self.factory.makeOCIRecipe(
                owner=self.owner,
                registrant=self.owner,
                information_type=InformationType.USERDATA,
                oci_project=self.factory.makeOCIProject(pillar=self.pillar),
            )
        ]
        expected_text = (
            """
            5 team members can view these artifacts.
            Shared with %s:
            1 OCI recipes
            """
            % team.displayname
        )

        if self.pillar_type == "product":
            items.append(
                self.factory.makeSnap(
                    information_type=InformationType.USERDATA,
                    owner=self.owner,
                    registrant=self.owner,
                    project=self.pillar,
                )
            )
            expected_text += "\n1 snap recipes"

        with person_logged_in(self.owner):
            for item in items:
                item.subscribe(team, self.owner)

        pillarperson = PillarPerson(self.pillar, team)
        url = "http://launchpad.test/%s/+sharing/%s" % (
            pillarperson.pillar.name,
            pillarperson.person.name,
        )
        browser = self.getUserBrowser(user=self.owner, url=url)
        content = extract_text(
            find_tag_by_id(browser.contents, "observer-summary")
        )

        self.assertTextMatchesExpressionIgnoreWhitespace(
            expected_text, content
        )

    def test_pillar_person_sharing(self):
        self.useFixture(FeatureFixture({OCI_RECIPE_ALLOW_CREATE: "on"}))
        person = self.factory.makePerson()
        items = [
            self.factory.makeOCIRecipe(
                owner=self.owner,
                registrant=self.owner,
                information_type=InformationType.USERDATA,
                oci_project=self.factory.makeOCIProject(pillar=self.pillar),
            )
        ]
        expected_text = (
            """
        Shared with %s:
        1 OCI recipes
        """
            % person.displayname
        )

        if self.pillar_type == "product":
            items.append(
                self.factory.makeSnap(
                    information_type=InformationType.USERDATA,
                    owner=self.owner,
                    registrant=self.owner,
                    project=self.pillar,
                )
            )
            expected_text += "\n1 snap recipes"

        with person_logged_in(self.owner):
            for item in items:
                item.subscribe(person, self.owner)

        pillarperson = PillarPerson(self.pillar, person)
        url = "http://launchpad.test/%s/+sharing/%s" % (
            pillarperson.pillar.name,
            pillarperson.person.name,
        )
        browser = self.getUserBrowser(user=self.owner, url=url)
        content = extract_text(
            find_tag_by_id(browser.contents, "observer-summary")
        )

        self.assertTextMatchesExpressionIgnoreWhitespace(
            expected_text, content
        )


class TestProductSharingView(PillarSharingViewTestMixin, SharingBaseTestCase):
    """Test the PillarSharingView with products."""

    pillar_type = "product"

    def setUp(self):
        super().setUp()
        self.setupSharing(self.grantees)
        login_person(self.driver)
        # Use a FakeLogger fixture to prevent Memcached warnings to be
        # printed to stdout while browsing pages.
        self.useFixture(FakeLogger())

    def test_view_contents_non_commercial_project(self):
        # Non commercial projects are rendered with the correct text.
        url = canonical_url(self.pillar, view_name="+sharing")
        browser = setupBrowserForUser(user=self.driver)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        commercial_text = soup.find("p", {"id": "commercial-project-text"})
        non_commercial_text = soup.find(
            "p", {"id": "non-commercial-project-text"}
        )
        self.assertIsNone(commercial_text)
        self.assertIsNotNone(non_commercial_text)

    def test_view_contents_commercial_project(self):
        # Commercial projects are rendered with the correct text.
        self.factory.makeCommercialSubscription(self.pillar)
        url = canonical_url(self.pillar, view_name="+sharing")
        browser = setupBrowserForUser(user=self.driver)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        commercial_text = soup.find("p", {"id": "commercial-project-text"})
        non_commercial_text = soup.find(
            "p", {"id": "non-commercial-project-text"}
        )
        self.assertIsNotNone(commercial_text)
        self.assertIsNone(non_commercial_text)

    def test_who_its_shared_with__proprietary_product(self):
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(
            owner=owner, information_type=InformationType.PROPRIETARY
        )
        self.run_sharing_message_test(product, owner, public=False)


class TestDistributionSharingView(
    PillarSharingViewTestMixin, SharingBaseTestCase
):
    """Test the PillarSharingView with distributions."""

    pillar_type = "distribution"

    def setUp(self):
        super().setUp()
        self.setupSharing(self.grantees)
        login_person(self.driver)

    def test_view_contents(self):
        # Distributions are rendered with the correct text.
        url = canonical_url(self.pillar, view_name="+sharing")
        browser = setupBrowserForUser(user=self.driver)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        commercial_text = soup.find("p", {"id": "commercial-project-text"})
        non_commercial_text = soup.find(
            "p", {"id": "non-commercial-project-text"}
        )
        self.assertIsNone(commercial_text)
        self.assertIsNone(non_commercial_text)
