# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for Git listing views."""

from zope.component import getUtility

from lp.app.enums import InformationType
from lp.code.enums import BranchMergeProposalStatus
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.registry.enums import VCSType
from lp.registry.interfaces.personociproject import IPersonOCIProjectFactory
from lp.registry.model.persondistributionsourcepackage import (
    PersonDistributionSourcePackage,
)
from lp.registry.model.personproduct import PersonProduct
from lp.services.beautifulsoup import BeautifulSoup
from lp.testing import (
    TestCaseWithFactory,
    admin_logged_in,
    anonymous_logged_in,
    person_logged_in,
)
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import BrowsesWithQueryLimit
from lp.testing.pages import find_tag_by_id
from lp.testing.views import create_initialized_view


class TestTargetGitListingView:
    layer = DatabaseFunctionalLayer

    def setDefaultRepository(self, target, repository):
        getUtility(IGitRepositorySet).setDefaultRepository(
            target=target, repository=repository
        )

    def test_rendering(self):
        main_repo = self.factory.makeGitRepository(
            owner=self.owner, target=self.target, name="foo"
        )
        self.factory.makeGitRefs(
            main_repo,
            paths=[
                "refs/heads/master",
                "refs/heads/1.0",
                "refs/heads/with#hash",
                "refs/heads/\N{SNOWMAN}",
                "refs/tags/1.1",
            ],
        )

        other_repo = self.factory.makeGitRepository(
            owner=self.factory.makePerson(name="contributor"),
            target=self.target,
            name="foo",
        )
        self.factory.makeGitRefs(other_repo, paths=["refs/heads/bug-1234"])
        self.factory.makeGitRepository(
            owner=self.factory.makePerson(name="random"),
            target=self.target,
            name="bar",
        )

        with admin_logged_in():
            self.setDefaultRepository(target=self.target, repository=main_repo)
            getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
                owner=other_repo.owner,
                target=self.target,
                repository=other_repo,
                user=other_repo.owner,
            )

        view = create_initialized_view(self.target, "+git")
        self.assertEqual(main_repo, view.default_git_repository)

        content = view()
        soup = BeautifulSoup(content)

        # Clone instructions for the default repo are present.
        self.assertEqual(
            "https://git.launchpad.test/%s" % self.target_path,
            soup.find(attrs={"class": "https-url"}).find(text=True),
        )
        self.assertEqual(
            "https://git.launchpad.test/%s" % self.target_path,
            soup.find(text="Browse the code").parent["href"],
        )

        # The default repo's branches are shown, but not its tags.
        table = soup.find("div", id="default-repository-branches").find(
            "table"
        )
        self.assertContentEqual(
            ["1.0", "master", "with#hash", "\N{SNOWMAN}"],
            [link.find(text=True) for link in table.find_all("a")],
        )
        self.assertEndsWith(
            table.find(text="1.0").parent["href"],
            "/~foowner/%s/+git/foo/+ref/1.0" % self.target_path,
        )
        self.assertEndsWith(
            table.find(text="with#hash").parent["href"],
            "/~foowner/%s/+git/foo/+ref/with%%23hash" % self.target_path,
        )
        self.assertEndsWith(
            table.find(text="\N{SNOWMAN}").parent["href"],
            "/~foowner/%s/+git/foo/+ref/%%E2%%98%%83" % self.target_path,
        )

        # Other repos are listed.
        table = soup.find("div", id="gitrepositories-table-listing").find(
            "table"
        )
        self.assertContentEqual(
            [
                "lp:%s" % self.target_path,
                "lp:~random/%s/+git/bar" % self.target_path,
                "lp:~contributor/%s" % self.target_path,
            ],
            [link.find(text=True) for link in table.find_all("a")],
        )
        self.assertEndsWith(
            table.find(text="lp:~contributor/%s" % self.target_path).parent[
                "href"
            ],
            "/~contributor/%s/+git/foo" % self.target_path,
        )

        # But not their branches.
        self.assertNotIn("bug-1234", content)

    def test_query_count(self):
        main_repo = self.factory.makeGitRepository(target=self.target)
        for i in range(10):
            self.factory.makeGitRefs(main_repo)

        for i in range(10):
            other_repo = self.factory.makeGitRepository(target=self.target)
            self.factory.makeGitRefs(other_repo)

        with admin_logged_in():
            self.setDefaultRepository(target=self.target, repository=main_repo)
            getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
                owner=other_repo.owner,
                target=self.target,
                repository=other_repo,
                user=other_repo.owner,
            )

        self.assertThat(
            self.target, BrowsesWithQueryLimit(38, self.owner, "+git")
        )

    def test_copes_with_no_default(self):
        self.factory.makeGitRepository(
            owner=self.factory.makePerson(name="contributor"),
            target=self.target,
            name="foo",
        )

        view = create_initialized_view(self.target, "+git")
        self.assertIs(None, view.default_git_repository)

        content = view()
        soup = BeautifulSoup(content)

        # No details about the non-existent default repo are shown.
        # XXX: This should show instructions to create one.
        self.assertNotIn("Branches", content)
        self.assertNotIn("Browse the code", content)
        self.assertNotIn("git clone", content)

        # Other repos are listed.
        table = soup.find("div", id="gitrepositories-table-listing").find(
            "table"
        )
        self.assertContentEqual(
            ["lp:~contributor/%s/+git/foo" % self.target_path],
            [link.find(text=True) for link in table.find_all("a")],
        )

    def test_copes_with_private_repos(self):
        invisible_repo = self.factory.makeGitRepository(
            owner=self.owner,
            target=self.target,
            information_type=InformationType.PRIVATESECURITY,
        )
        other_repo = self.factory.makeGitRepository(
            target=self.target, information_type=InformationType.PUBLIC
        )
        with admin_logged_in():
            self.setDefaultRepository(
                target=self.target, repository=invisible_repo
            )

        # An anonymous user can't see the default.
        with anonymous_logged_in():
            anon_view = create_initialized_view(self.target, "+git")
            self.assertIs(None, anon_view.default_git_repository)
            self.assertContentEqual(
                [other_repo], anon_view.repo_collection.getRepositories()
            )

        # Neither can a random unprivileged user.
        with person_logged_in(self.factory.makePerson()):
            anon_view = create_initialized_view(self.target, "+git")
            self.assertIs(None, anon_view.default_git_repository)
            self.assertContentEqual(
                [other_repo], anon_view.repo_collection.getRepositories()
            )

        # But someone who can see the repo gets the normal view.
        with person_logged_in(self.owner):
            owner_view = create_initialized_view(
                self.target, "+git", principal=self.owner
            )
            self.assertEqual(invisible_repo, owner_view.default_git_repository)
            self.assertContentEqual(
                [invisible_repo, other_repo],
                owner_view.repo_collection.getRepositories(),
            )

    def test_bzr_link(self):
        # With a fresh product there's no Bazaar link.
        view = create_initialized_view(self.target, "+git")
        self.assertNotIn("View Bazaar branches", view())

        # But it appears once we create a branch.
        self.factory.makeBranch(target=self.branch_target)
        view = create_initialized_view(self.target, "+git")
        self.assertIn("View Bazaar branches", view())


class TestPersonTargetGitListingView:
    layer = DatabaseFunctionalLayer

    def test_rendering(self):
        default_repo = self.factory.makeGitRepository(
            owner=self.owner, target=self.target, name="foo"
        )
        self.factory.makeGitRefs(
            default_repo, paths=["refs/heads/master", "refs/heads/bug-1234"]
        )

        other_repo = self.factory.makeGitRepository(
            owner=self.owner, target=self.target, name="bar"
        )
        self.factory.makeGitRefs(other_repo, paths=["refs/heads/bug-2468"])

        with admin_logged_in():
            getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
                owner=self.owner,
                target=self.target,
                repository=default_repo,
                user=self.owner,
            )

        view = create_initialized_view(self.owner_target, "+git")
        self.assertEqual(default_repo, view.default_git_repository)

        content = view()
        soup = BeautifulSoup(content)

        # Clone instructions for the default repo are present.
        self.assertEqual(
            "https://git.launchpad.test/~dev/%s" % self.target_path,
            soup.find(attrs={"class": "https-url"}).find(text=True),
        )
        self.assertEqual(
            "https://git.launchpad.test/~dev/%s" % self.target_path,
            soup.find(text="Browse the code").parent["href"],
        )

        # The default repo's branches are shown.
        table = soup.find("div", id="default-repository-branches").find(
            "table"
        )
        self.assertContentEqual(
            ["master", "bug-1234"],
            [link.find(text=True) for link in table.find_all("a")],
        )
        self.assertEndsWith(
            table.find(text="bug-1234").parent["href"],
            "/~dev/%s/+git/foo/+ref/bug-1234" % self.target_path,
        )

        # Other repos are listed.
        table = soup.find("div", id="gitrepositories-table-listing").find(
            "table"
        )
        self.assertContentEqual(
            [
                "lp:~dev/%s" % self.target_path,
                "lp:~dev/%s/+git/bar" % self.target_path,
            ],
            [link.find(text=True) for link in table.find_all("a")],
        )
        self.assertEndsWith(
            table.find(text="lp:~dev/%s/+git/bar" % self.target_path).parent[
                "href"
            ],
            "/~dev/%s/+git/bar" % self.target_path,
        )

        # But not their branches.
        self.assertNotIn("bug-2468", content)

    def test_copes_with_no_default(self):
        self.factory.makeGitRepository(
            owner=self.owner, target=self.target, name="foo"
        )

        view = create_initialized_view(self.owner_target, "+git")
        self.assertIs(None, view.default_git_repository)

        content = view()
        soup = BeautifulSoup(content)

        # No details about the non-existent default repo are shown.
        # XXX: This should show instructions to create one.
        self.assertNotIn("Branches", content)
        self.assertNotIn("Browse the code", content)
        self.assertNotIn("git clone", content)

        # Other repos are listed.
        table = soup.find("div", id="gitrepositories-table-listing").find(
            "table"
        )
        self.assertContentEqual(
            ["lp:~dev/%s/+git/foo" % self.target_path],
            [link.find(text=True) for link in table.find_all("a")],
        )

    def test_copes_with_private_repos(self):
        invisible_repo = self.factory.makeGitRepository(
            owner=self.owner,
            target=self.target,
            information_type=InformationType.PRIVATESECURITY,
        )
        other_repo = self.factory.makeGitRepository(
            owner=self.owner,
            target=self.target,
            information_type=InformationType.PUBLIC,
        )
        with admin_logged_in():
            getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
                owner=self.owner,
                target=self.target,
                repository=invisible_repo,
                user=self.owner,
            )

        # An anonymous user can't see the default.
        with anonymous_logged_in():
            anon_view = create_initialized_view(self.owner_target, "+git")
            self.assertIs(None, anon_view.default_git_repository)
            self.assertContentEqual(
                [other_repo], anon_view.repo_collection.getRepositories()
            )

        # Neither can a random unprivileged user.
        with person_logged_in(self.factory.makePerson()):
            anon_view = create_initialized_view(self.owner_target, "+git")
            self.assertIs(None, anon_view.default_git_repository)
            self.assertContentEqual(
                [other_repo], anon_view.repo_collection.getRepositories()
            )

        # But someone who can see the repo gets the normal view.
        with person_logged_in(self.owner):
            owner_view = create_initialized_view(
                self.owner_target, "+git", principal=self.owner
            )
            self.assertEqual(invisible_repo, owner_view.default_git_repository)
            self.assertContentEqual(
                [invisible_repo, other_repo],
                owner_view.repo_collection.getRepositories(),
            )

    def test_bzr_link(self):
        # With a fresh product there's no Bazaar link.
        view = create_initialized_view(self.owner_target, "+git")
        self.assertNotIn("View Bazaar branches", view())

        # But it appears once we create a branch.
        self.factory.makeBranch(owner=self.owner, target=self.branch_target)
        view = create_initialized_view(self.owner_target, "+git")
        self.assertIn("View Bazaar branches", view())


class TestProductGitListingView(TestTargetGitListingView, TestCaseWithFactory):
    def setUp(self):
        super().setUp()
        self.owner = self.factory.makePerson(name="foowner")
        self.target = self.factory.makeProduct(
            name="foo", owner=self.owner, vcs=VCSType.GIT
        )
        self.target_path = "foo"
        self.branch_target = self.target

    def test_active_reviews_link(self):
        main_repo = self.factory.makeGitRepository(
            owner=self.owner, target=self.target, name="foo"
        )
        git_refs = self.factory.makeGitRefs(
            main_repo,
            paths=["refs/heads/master", "refs/heads/1.0", "refs/tags/1.1"],
        )

        with admin_logged_in():
            self.setDefaultRepository(target=self.target, repository=main_repo)

        self.factory.makeBranchMergeProposalForGit(
            target_ref=git_refs[0],
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW,
        )
        view = create_initialized_view(self.target, "+git")
        self.assertIsNotNone(find_tag_by_id(view(), "active-review-count"))

    def test_all_merges_link(self):
        main_repo = self.factory.makeGitRepository(
            owner=self.owner, target=self.target, name="foo"
        )
        git_refs = self.factory.makeGitRefs(
            main_repo,
            paths=["refs/heads/master", "refs/heads/1.0", "refs/tags/1.1"],
        )

        with admin_logged_in():
            self.setDefaultRepository(target=self.target, repository=main_repo)

        self.factory.makeBranchMergeProposalForGit(
            target_ref=git_refs[0],
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW,
        )
        view = create_initialized_view(self.target, "+git")
        self.assertIsNotNone(find_tag_by_id(view(), "all-merges"))

    def test_personal_git_instructions_not_present(self):
        with person_logged_in(self.owner):
            view = create_initialized_view(
                self.target, "+git", principal=self.owner
            )
            self.assertIsNone(
                find_tag_by_id(view(), "personal-git-directions")
            )

    def test_personal_link(self):
        with person_logged_in(self.owner):
            view = create_initialized_view(
                self.target, "+git", principal=self.owner
            )
            self.assertFalse(view.show_personal_directions)


class TestPersonProductGitListingView(
    TestPersonTargetGitListingView, TestCaseWithFactory
):
    def setUp(self):
        super().setUp()
        self.owner = self.factory.makePerson(name="dev")
        self.target = self.factory.makeProduct(name="foo")
        self.target_path = "foo"
        self.owner_target = PersonProduct(self.owner, self.target)
        self.branch_target = self.target


class TestDistributionSourcePackageGitListingView(
    TestTargetGitListingView, TestCaseWithFactory
):
    def setUp(self):
        super().setUp()
        self.owner = self.factory.makePerson(name="foowner")
        distro = self.factory.makeDistribution(name="foo", owner=self.owner)
        self.target = self.factory.makeDistributionSourcePackage(
            distribution=distro, sourcepackagename="bar"
        )
        self.target_path = "foo/+source/bar"
        self.factory.makeDistroSeries(distribution=distro)
        self.branch_target = self.target.development_version


class TestPersonDistributionSourcePackageGitListingView(
    TestPersonTargetGitListingView, TestCaseWithFactory
):
    def setUp(self):
        super().setUp()
        self.owner = self.factory.makePerson(name="dev")
        distro = self.factory.makeDistribution(name="foo", owner=self.owner)
        self.target = self.factory.makeDistributionSourcePackage(
            distribution=distro, sourcepackagename="bar"
        )
        self.target_path = "foo/+source/bar"
        self.owner_target = PersonDistributionSourcePackage(
            self.owner, self.target
        )
        self.factory.makeDistroSeries(distribution=distro)
        self.branch_target = self.target.development_version

    def test_bzr_link(self):
        # With a fresh target there's no Bazaar link.
        view = create_initialized_view(self.owner_target, "+git")
        self.assertNotIn("View Bazaar branches", view())

        # As a special case for PersonDistributionSourcePackage, no link
        # appears even if there is a branch. There's no PersonDSP:+branches.
        self.factory.makeBranch(owner=self.owner, target=self.branch_target)
        view = create_initialized_view(self.owner_target, "+git")
        self.assertNotIn("View Bazaar branches", view())


class TestOCIProjectGitListingView(
    TestTargetGitListingView, TestCaseWithFactory
):
    def setUp(self):
        super().setUp()
        self.owner = self.factory.makePerson(name="foowner")
        distro = self.factory.makeDistribution(name="foo", owner=self.owner)
        self.target = self.factory.makeOCIProject(
            pillar=distro, ociprojectname="bar"
        )
        self.target_path = "foo/+oci/bar"

    def test_bzr_link(self):
        # There's no OCIProject:+branches, nor any ability to create Bazaar
        # branches for OCI projects.
        view = create_initialized_view(self.target, "+git")
        self.assertNotIn("View Bazaar branches", view())


class TestPersonOCIProjectGitListingView(
    TestPersonTargetGitListingView, TestCaseWithFactory
):
    def setUp(self):
        super().setUp()
        self.owner = self.factory.makePerson(name="dev")
        distro = self.factory.makeDistribution(name="foo", owner=self.owner)
        self.target = self.factory.makeOCIProject(
            pillar=distro, ociprojectname="bar"
        )
        self.target_path = "foo/+oci/bar"
        self.owner_target = getUtility(IPersonOCIProjectFactory).create(
            self.owner, self.target
        )

    def test_bzr_link(self):
        # There's no PersonOCIProject:+branches, nor any ability to create
        # Bazaar branches for OCI projects.
        view = create_initialized_view(self.owner_target, "+git")
        self.assertNotIn("View Bazaar branches", view())


class TestPlainGitListingView:
    layer = DatabaseFunctionalLayer

    def test_rendering(self):
        some_repo = self.factory.makeGitRepository(
            owner=self.owner, target=self.target, name="foo"
        )
        self.factory.makeGitRefs(
            some_repo, paths=["refs/heads/master", "refs/heads/bug-1234"]
        )

        other_repo = self.factory.makeGitRepository(
            owner=self.owner, target=self.target, name="bar"
        )
        self.factory.makeGitRefs(other_repo, paths=["refs/heads/bug-2468"])

        view = create_initialized_view(self.context, "+git")
        self.assertIs(None, view.default_git_repository)

        content = view()
        soup = BeautifulSoup(content)

        # No details about the default repo are shown, as a person
        # without a target doesn't have a default repo
        self.assertNotIn("Branches", content)
        self.assertNotIn("Browse the code", content)
        self.assertNotIn("git clone", content)
        self.assertNotIn("bug-1234", content)

        # All owned repos are listed.
        table = soup.find("div", id="gitrepositories-table-listing").find(
            "table"
        )
        self.assertContentEqual(
            [some_repo.git_identity, other_repo.git_identity],
            [link.find(text=True) for link in table.find_all("a")],
        )

    def test_copes_with_private_repos(self):
        # XXX wgrant 2015-06-12: owner is self.user instead of
        # self.owner here so the Distribution tests work.
        # GitRepository._reconcileAccess doesn't handle distro repos
        # properly, so an AccessPolicyGrant isn't sufficient.
        invisible_repo = self.factory.makeGitRepository(
            owner=self.user,
            target=self.target,
            information_type=InformationType.PRIVATESECURITY,
        )
        other_repo = self.factory.makeGitRepository(
            owner=self.owner,
            target=self.target,
            information_type=InformationType.PUBLIC,
        )

        # An anonymous user can't see the private branch.
        with anonymous_logged_in():
            anon_view = create_initialized_view(self.context, "+git")
            self.assertContentEqual(
                [other_repo], anon_view.repo_collection.getRepositories()
            )

        # Neither can a random unprivileged user.
        with person_logged_in(self.factory.makePerson()):
            anon_view = create_initialized_view(self.context, "+git")
            self.assertContentEqual(
                [other_repo], anon_view.repo_collection.getRepositories()
            )

        # But someone who can see the repo gets the full view.
        with person_logged_in(self.user):
            owner_view = create_initialized_view(
                self.context, "+git", principal=self.user
            )
            self.assertContentEqual(
                [invisible_repo, other_repo],
                owner_view.repo_collection.getRepositories(),
            )

    def test_bzr_link(self):
        # With a fresh product there's no Bazaar link.
        view = create_initialized_view(self.context, "+git")
        self.assertNotIn("View Bazaar branches", view())

        # But it appears once we create a branch.
        self.factory.makeBranch(owner=self.owner, target=self.branch_target)
        view = create_initialized_view(self.context, "+git")
        self.assertIn("View Bazaar branches", view())


class TestPersonGitListingView(TestPlainGitListingView, TestCaseWithFactory):
    def setUp(self):
        super().setUp()
        self.context = self.user = self.owner = self.factory.makePerson()
        self.target = self.branch_target = None

    def test_personal_git_instructions_present(self):
        with person_logged_in(self.owner):
            view = create_initialized_view(
                self.owner, "+git", principal=self.owner
            )
            self.assertIsNotNone(
                find_tag_by_id(view(), "personal-git-directions")
            )

    def test_personal_link(self):
        with person_logged_in(self.owner):
            view = create_initialized_view(
                self.owner, "+git", principal=self.owner
            )
            self.assertTrue(view.show_personal_directions)


class TestDistributionGitListingView(
    TestPlainGitListingView, TestCaseWithFactory
):
    def setUp(self):
        super().setUp()
        self.target = self.factory.makeDistributionSourcePackage()
        self.factory.makeDistroSeries(distribution=self.target.distribution)
        self.branch_target = self.target.development_version
        self.context = self.target.distribution
        self.user = self.target.distribution.owner
        self.owner = None
