# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BranchSet."""

from datetime import datetime, timezone

from testtools.matchers import LessThan
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.code.enums import BranchListingSort
from lp.code.interfaces.branch import IBranchSet
from lp.code.interfaces.branchcollection import IAllBranches
from lp.code.interfaces.linkedbranch import ICanHasLinkedBranch
from lp.code.model.branch import BranchSet
from lp.services.propertycache import clear_property_cache
from lp.testing import (
    RequestTimelineCollector,
    TestCaseWithFactory,
    login_person,
)
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import webservice_for_person


class TestBranchSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_provides_IBranchSet(self):
        # BranchSet instances provide IBranchSet.
        self.assertProvides(BranchSet(), IBranchSet)

    def test_getByUrls(self):
        # getByUrls returns a list of branches matching the list of URLs that
        # it's given.
        a = self.factory.makeAnyBranch()
        b = self.factory.makeAnyBranch()
        branches = BranchSet().getByUrls([a.bzr_identity, b.bzr_identity])
        self.assertEqual({a.bzr_identity: a, b.bzr_identity: b}, branches)

    def test_getByUrls_cant_find_url(self):
        # If a branch cannot be found for a URL, then None appears in the list
        # in place of the branch.
        url = "http://example.com/doesntexist"
        branches = BranchSet().getByUrls([url])
        self.assertEqual({url: None}, branches)

    def test_getByPath(self):
        branch = self.factory.makeProductBranch()
        self.assertEqual(branch, BranchSet().getByPath(branch.shortened_path))
        product = removeSecurityProxy(branch.product)
        ICanHasLinkedBranch(product).setBranch(branch)
        clear_property_cache(branch)
        self.assertEqual(product.name, branch.shortened_path)
        self.assertEqual(branch, BranchSet().getByPath(branch.shortened_path))
        self.assertIsNone(BranchSet().getByPath("nonexistent"))

    def test_getBranches_order_by(self):
        # We can get a collection of all branches with a given sort order.
        # Unscan branches from sampledata so that they don't get in our way.
        for branch in getUtility(IAllBranches).scanned().getBranches():
            removeSecurityProxy(branch).unscan(rescan=False)
        branches = [self.factory.makeProductBranch() for _ in range(5)]
        modified_dates = [
            datetime(2010, 1, 1, tzinfo=timezone.utc),
            datetime(2015, 1, 1, tzinfo=timezone.utc),
            datetime(2014, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2019, 1, 1, tzinfo=timezone.utc),
        ]
        for branch, modified_date in zip(branches, modified_dates):
            self.factory.makeRevisionsForBranch(branch)
            branch.date_last_modified = modified_date
        removeSecurityProxy(branches[0]).transitionToInformationType(
            InformationType.PRIVATESECURITY, branches[0].registrant
        )
        self.assertEqual(
            [branches[3], branches[4], branches[1], branches[2], branches[0]],
            list(
                getUtility(IBranchSet).getBranches(
                    branches[0].owner,
                    order_by=BranchListingSort.MOST_RECENTLY_CHANGED_FIRST,
                )
            ),
        )
        self.assertEqual(
            [branches[3], branches[4], branches[1]],
            list(
                getUtility(IBranchSet).getBranches(
                    branches[0].owner,
                    order_by=BranchListingSort.MOST_RECENTLY_CHANGED_FIRST,
                    modified_since_date=datetime(
                        2014, 12, 1, tzinfo=timezone.utc
                    ),
                )
            ),
        )
        self.assertEqual(
            [branches[3], branches[4], branches[1], branches[2]],
            list(
                getUtility(IBranchSet).getBranches(
                    None,
                    order_by=BranchListingSort.MOST_RECENTLY_CHANGED_FIRST,
                )
            ),
        )

    def test_api_branches_query_count(self):
        webservice = webservice_for_person(None)
        collector = RequestTimelineCollector()
        collector.register()
        self.addCleanup(collector.unregister)
        # Get 'all' of the 50 branches this collection is limited to - rather
        # than the default in-test-suite pagination size of 5.
        url = "/branches?ws.size=50"
        response = webservice.get(url, headers={"User-Agent": "AnonNeedsThis"})
        self.assertEqual(
            response.status,
            200,
            "Got %d for url %r with response %r"
            % (response.status, url, response.body),
        )
        self.assertThat(collector, HasQueryCount(LessThan(17)))

    def test_getBranchVisibilityInfo_empty_branch_names(self):
        """Test the test_getBranchVisibilityInfo API with no branch names."""
        person = self.factory.makePerson(name="fred")
        info = BranchSet().getBranchVisibilityInfo(
            person, person, branch_names=[]
        )
        self.assertEqual("Fred", info["person_name"])
        self.assertEqual([], info["visible_branches"])

    def test_getBranchVisibilityInfo(self):
        """Test the test_getBranchVisibilityInfo API."""
        person = self.factory.makePerson(name="fred")
        owner = self.factory.makePerson()
        visible_branch = self.factory.makeBranch()
        invisible_branch = self.factory.makeBranch(
            owner=owner, information_type=InformationType.USERDATA
        )
        invisible_name = removeSecurityProxy(invisible_branch).unique_name
        branches = [visible_branch.unique_name, invisible_name]

        login_person(owner)
        info = BranchSet().getBranchVisibilityInfo(
            owner, person, branch_names=branches
        )
        self.assertEqual("Fred", info["person_name"])
        self.assertEqual(
            [visible_branch.unique_name], info["visible_branches"]
        )

    def test_getBranchVisibilityInfo_unauthorised_user(self):
        """Test the test_getBranchVisibilityInfo API.

        If the user making the API request cannot see one of the branches,
        that branch is not included in the results.
        """
        person = self.factory.makePerson(name="fred")
        owner = self.factory.makePerson()
        visible_branch = self.factory.makeBranch()
        invisible_branch = self.factory.makeBranch(
            owner=owner, information_type=InformationType.USERDATA
        )
        invisible_name = removeSecurityProxy(invisible_branch).unique_name
        branches = [visible_branch.unique_name, invisible_name]

        someone = self.factory.makePerson()
        login_person(someone)
        info = BranchSet().getBranchVisibilityInfo(
            someone, person, branch_names=branches
        )
        self.assertEqual("Fred", info["person_name"])
        self.assertEqual(
            [visible_branch.unique_name], info["visible_branches"]
        )

    def test_getBranchVisibilityInfo_anonymous(self):
        """Test the test_getBranchVisibilityInfo API.

        Anonymous users are not allowed to see any branch visibility info,
        even if the branch they are querying about is public.
        """
        person = self.factory.makePerson(name="fred")
        owner = self.factory.makePerson()
        visible_branch = self.factory.makeBranch(owner=owner)
        branches = [visible_branch.unique_name]

        login_person(owner)
        info = BranchSet().getBranchVisibilityInfo(
            None, person, branch_names=branches
        )
        self.assertEqual({}, info)

    def test_getBranchVisibilityInfo_invalid_branch_name(self):
        """Test the test_getBranchVisibilityInfo API.

        If there is an invalid branch name specified, it is not included.
        """
        person = self.factory.makePerson(name="fred")
        owner = self.factory.makePerson()
        visible_branch = self.factory.makeBranch(owner=owner)
        branches = [visible_branch.unique_name, "invalid_branch_name"]

        login_person(owner)
        info = BranchSet().getBranchVisibilityInfo(
            owner, person, branch_names=branches
        )
        self.assertEqual("Fred", info["person_name"])
        self.assertEqual(
            [visible_branch.unique_name], info["visible_branches"]
        )
