# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for traversal from the root branch object."""

from zope.component import getMultiAdapter, getUtility
from zope.publisher.interfaces import NotFound
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.browser.launchpad import (
    LaunchpadRootNavigation,
    iter_view_registrations,
)
from lp.app.enums import InformationType
from lp.app.errors import GoneError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.interfaces.services import IService
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.code.interfaces.linkedbranch import ICanHasLinkedBranch
from lp.registry.enums import PersonVisibility, SharingPermission, VCSType
from lp.registry.interfaces.person import IPersonSet
from lp.services.identity.interfaces.account import AccountStatus
from lp.services.webapp import canonical_url
from lp.services.webapp.escaping import html_escape
from lp.services.webapp.interfaces import (
    BrowserNotificationLevel,
    ILaunchpadRoot,
)
from lp.services.webapp.servers import (
    LaunchpadTestRequest,
    WebServiceTestRequest,
)
from lp.services.webapp.url import urlappend
from lp.testing import (
    ANONYMOUS,
    TestCaseWithFactory,
    admin_logged_in,
    celebrity_logged_in,
    login,
    login_person,
    person_logged_in,
)
from lp.testing.layers import DatabaseFunctionalLayer, FunctionalLayer
from lp.testing.publication import test_traverse
from lp.testing.views import create_view

# We set the request header HTTP_REFERER  when we want to simulate navigation
# from a valid page. This is used in the assertDisplaysNotification check.
DEFAULT_REFERER = "http://launchpad.test"


class TraversalMixin:
    def _validateNotificationContext(
        self, request, notification=None, level=BrowserNotificationLevel.INFO
    ):
        """Check the browser notifications associated with the request.

        Ensure that the notification instances attached to the request match
        the expected values for text and type.

        :param notification: The exact notification text to validate. If None
            then we don't care what the notification text is, so long as there
            is some.
        : param level: the required notification level
        """

        notifications = request.notifications
        if notification is None:
            self.assertEqual(len(notifications), 0)
            return
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].level, level)
        self.assertEqual(notification, notifications[0].message)

    def assertDisplaysNotification(
        self, path, notification=None, level=BrowserNotificationLevel.INFO
    ):
        """Assert that an invalid path redirects back to referrer.

        The request object is expected to have a notification message to
        display to the user to explain the reason for the error.

        :param path: The path to check
        :param notification: The exact notification text to validate. If None
            then we don't care what the notification text is, so long as there
            is some.
        : param level: the required notification level
        """

        redirection = self.traverse(path)
        self.assertIs(redirection.target, DEFAULT_REFERER)
        self._validateNotificationContext(
            redirection.request, notification, level
        )

    def assertNotFound(self, path, use_default_referer=True):
        self.assertRaises(
            NotFound,
            self.traverse,
            path,
            use_default_referer=use_default_referer,
        )

    def assertRedirects(self, segments, url, webservice=False):
        redirection = self.traverse(segments, webservice=webservice)
        self.assertEqual(url, redirection.target)

    def traverse(
        self, path, first_segment, use_default_referer=True, webservice=False
    ):
        """Traverse to 'path' using a 'LaunchpadRootNavigation' object.

        Using the Zope traversal machinery, traverse to the path given by
        'segments', starting at a `LaunchpadRootNavigation` object.

        CAUTION: Prefer test_traverse to this method, because it correctly
        establishes the global request.

        :param path: A slash-delimited path.
        :param use_default_referer: If True, set the referer attribute in the
            request header to DEFAULT_REFERER = "http://launchpad.test"
            (otherwise it remains as None)
        :param webservice: If True, use a webservice-like request rather
            than a normal test request.
        :return: The object found.
        """
        # XXX: What's the difference between first_segment and path? -- mbp
        # 2011-06-27.
        extra = {"PATH_INFO": urlappend("/%s" % first_segment, path)}
        if use_default_referer:
            extra["HTTP_REFERER"] = DEFAULT_REFERER
        request_factory = (
            WebServiceTestRequest if webservice else LaunchpadTestRequest
        )
        request = request_factory(**extra)
        segments = reversed(path.split("/"))
        request.setTraversalStack(segments)
        traverser = LaunchpadRootNavigation(
            getUtility(ILaunchpadRoot), request=request
        )
        return traverser.publishTraverse(request, first_segment)


class TestBranchTraversal(TestCaseWithFactory, TraversalMixin):
    """Branches are traversed to from IPersons. Test we can reach them.

    This class tests the `LaunchpadRootNavigation` class to see that we can
    traverse to branches from URLs of the form +branch/xxxx.
    """

    layer = DatabaseFunctionalLayer

    def assertDisplaysNotice(self, path, notification):
        """Assert that traversal redirects back with the specified notice."""
        self.assertDisplaysNotification(
            path, notification, BrowserNotificationLevel.INFO
        )

    def assertDisplaysError(self, path, notification):
        """Assert that traversal redirects back with the specified notice."""
        self.assertDisplaysNotification(
            path, notification, BrowserNotificationLevel.ERROR
        )

    def traverse(self, path, **kwargs):
        return super().traverse(path, "+branch", **kwargs)

    def test_unique_name_traversal(self):
        # Traversing to /+branch/<unique_name> redirects to the page for that
        # branch.
        branch = self.factory.makeAnyBranch()
        self.assertRedirects(branch.unique_name, canonical_url(branch))
        self.assertRedirects(
            branch.unique_name,
            canonical_url(branch, rootsite="api"),
            webservice=True,
        )

    def test_no_such_unique_name(self):
        # Traversing to /+branch/<unique_name> where 'unique_name' is for a
        # branch that doesn't exist will display an error message.
        branch = self.factory.makeAnyBranch()
        bad_name = branch.unique_name + "wibble"
        required_message = html_escape(
            "No such branch: '%s'." % (branch.name + "wibble")
        )
        self.assertDisplaysError(bad_name, required_message)

    def test_private_branch(self):
        # If an attempt is made to access a private branch, display an error.
        branch = self.factory.makeProductBranch(
            information_type=InformationType.USERDATA
        )
        branch_unique_name = removeSecurityProxy(branch).unique_name
        login(ANONYMOUS)
        required_message = html_escape(
            "No such branch: '%s'." % branch_unique_name
        )
        self.assertDisplaysError(branch_unique_name, required_message)

    def test_product_alias(self):
        # Traversing to /+branch/<product> redirects to the page for the
        # branch that is the development focus branch for that product.
        branch = self.factory.makeProductBranch()
        naked_product = removeSecurityProxy(branch.product)
        ICanHasLinkedBranch(naked_product).setBranch(branch)
        self.assertRedirects(naked_product.name, canonical_url(branch))

    def test_private_branch_for_product(self):
        # If the development focus of a product is private, display a
        # message telling the user there is no linked branch.
        branch = self.factory.makeProductBranch()
        naked_product = removeSecurityProxy(branch.product)
        ICanHasLinkedBranch(naked_product).setBranch(branch)
        removeSecurityProxy(branch).information_type = InformationType.USERDATA
        login(ANONYMOUS)
        requiredMessage = (
            "The target %s does not have a linked branch." % naked_product.name
        )
        self.assertDisplaysNotice(naked_product.name, requiredMessage)

    def test_nonexistent_product(self):
        # Traversing to /+branch/<no-such-product> displays an error message.
        non_existent = "non-existent"
        required_message = "No such product: '%s'." % non_existent
        self.assertDisplaysError(non_existent, html_escape(required_message))

    def test_nonexistent_product_without_referer(self):
        # Traversing to /+branch/<no-such-product> without a referer results
        # in a 404 error. This happens if the user hacks the URL rather than
        # navigating via a link
        self.assertNotFound("non-existent", use_default_referer=False)

    def test_private_without_referer(self):
        # If the development focus of a product is private and there is no
        # referer, we will get a 404 error. This happens if the user hacks
        # the URL rather than navigating via a link
        branch = self.factory.makeProductBranch()
        naked_product = removeSecurityProxy(branch.product)
        ICanHasLinkedBranch(naked_product).setBranch(branch)
        removeSecurityProxy(branch).information_type = InformationType.USERDATA
        login(ANONYMOUS)
        self.assertNotFound(naked_product.name, use_default_referer=False)

    def test_product_without_dev_focus(self):
        # Traversing to a product without a development focus displays a
        # user message on the same page.
        product = self.factory.makeProduct()
        requiredMessage = (
            "The target %s does not have a linked branch." % product.name
        )
        self.assertDisplaysNotice(product.name, requiredMessage)

    def test_distro_package_alias(self):
        # Traversing to /+branch/<distro>/<sourcepackage package> redirects
        # to the page for the branch that is the development focus branch
        # for that package.
        sourcepackage = self.factory.makeSourcePackage()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        distro_package = sourcepackage.distribution_sourcepackage
        registrant = distro_package.distribution.owner
        target = ICanHasLinkedBranch(distro_package)
        with person_logged_in(registrant):
            target.setBranch(branch, registrant)
        self.assertRedirects("%s" % target.bzr_path, canonical_url(branch))

    def test_private_branch_for_distro_package(self):
        # If the development focus of a distro package is private, display a
        # message telling the user there is no linked branch.
        sourcepackage = self.factory.makeSourcePackage()
        branch = self.factory.makePackageBranch(
            sourcepackage=sourcepackage,
            information_type=InformationType.USERDATA,
        )
        distro_package = sourcepackage.distribution_sourcepackage
        registrant = distro_package.distribution.owner
        with person_logged_in(registrant):
            ICanHasLinkedBranch(distro_package).setBranch(branch, registrant)
        login(ANONYMOUS)
        path = ICanHasLinkedBranch(distro_package).bzr_path
        requiredMessage = "The target %s does not have a linked branch." % path
        self.assertDisplaysNotice(path, requiredMessage)

    def test_trailing_path_redirect(self):
        # If there are any trailing path segments after the branch identifier,
        # these stick around at the redirected URL.
        branch = self.factory.makeAnyBranch()
        path = urlappend(branch.unique_name, "+edit")
        self.assertRedirects(path, canonical_url(branch, view_name="+edit"))

    def test_alias_trailing_path_redirect(self):
        # Redirects also support trailing path segments with aliases.
        branch = self.factory.makeProductBranch()
        with person_logged_in(branch.product.owner):
            branch.product.development_focus.branch = branch
        path = "%s/+edit" % branch.product.name
        self.assertRedirects(path, canonical_url(branch, view_name="+edit"))

    def test_product_series_redirect(self):
        # Traversing to /+branch/<product>/<series> redirects to the branch
        # for that series, if there is one.
        branch = self.factory.makeBranch()
        series = self.factory.makeProductSeries(branch=branch)
        self.assertRedirects(
            ICanHasLinkedBranch(series).bzr_path, canonical_url(branch)
        )

    def test_no_branch_for_series(self):
        # If there's no branch for a product series, display a
        # message telling the user there is no linked branch.
        series = self.factory.makeProductSeries()
        path = ICanHasLinkedBranch(series).bzr_path
        requiredMessage = "The target %s does not have a linked branch." % path
        self.assertDisplaysNotice(path, requiredMessage)

    def test_private_branch_for_series(self):
        # If the development focus of a product series is private, display a
        # message telling the user there is no linked branch.
        branch = self.factory.makeBranch(
            information_type=InformationType.USERDATA
        )
        series = self.factory.makeProductSeries(branch=branch)
        login(ANONYMOUS)
        path = ICanHasLinkedBranch(series).bzr_path
        requiredMessage = "The target %s does not have a linked branch." % path
        self.assertDisplaysNotice(path, requiredMessage)

    def test_too_short_branch_name(self):
        # error notification if the thing following +branch is a unique name
        # that's too short to be a real unique name.
        owner = self.factory.makePerson()
        requiredMessage = html_escape(
            "Cannot understand namespace name: '%s'" % owner.name
        )
        self.assertDisplaysError("~%s" % owner.name, requiredMessage)

    def test_invalid_product_name(self):
        # error notification if the thing following +branch has an invalid
        # product name.
        self.assertDisplaysError("_foo", "Invalid name for product: _foo.")

    def test_invalid_product_name_without_referer(self):
        # error notification if the thing following +branch has an invalid
        # product name.
        self.assertNotFound("_foo", use_default_referer=False)


class TestCodeTraversal(TestCaseWithFactory, TraversalMixin):
    layer = DatabaseFunctionalLayer

    def traverse(self, path, **kwargs):
        return super().traverse(path, "+code", **kwargs)

    def test_project_bzr_branch(self):
        branch = self.factory.makeAnyBranch()
        self.assertRedirects(branch.unique_name, canonical_url(branch))
        self.assertRedirects(
            branch.unique_name,
            canonical_url(branch, rootsite="api"),
            webservice=True,
        )

    def test_project_git_branch(self):
        git_repo = self.factory.makeGitRepository()
        self.assertRedirects(git_repo.unique_name, canonical_url(git_repo))
        self.assertRedirects(
            git_repo.unique_name,
            canonical_url(git_repo, rootsite="api"),
            webservice=True,
        )

    def test_no_such_bzr_unique_name(self):
        branch = self.factory.makeAnyBranch()
        bad_name = branch.unique_name + "wibble"
        self.assertNotFound(bad_name)

    def test_no_such_git_unique_name(self):
        repo = self.factory.makeGitRepository()
        bad_name = repo.unique_name + "wibble"
        self.assertNotFound(bad_name)

    def test_private_bzr_branch(self):
        branch = self.factory.makeProductBranch(
            information_type=InformationType.USERDATA
        )
        branch_unique_name = removeSecurityProxy(branch).unique_name
        login(ANONYMOUS)
        self.assertNotFound(branch_unique_name)

    def test_private_git_branch(self):
        git_repo = self.factory.makeGitRepository(
            information_type=InformationType.USERDATA
        )
        repo_unique_name = removeSecurityProxy(git_repo).unique_name
        login(ANONYMOUS)
        self.assertNotFound(repo_unique_name)

    def test_product_alias_bzr(self):
        branch = self.factory.makeProductBranch()
        naked_product = removeSecurityProxy(branch.product)
        ICanHasLinkedBranch(naked_product).setBranch(branch)
        self.assertRedirects(naked_product.name, canonical_url(branch))

    def test_product_alias_git(self):
        project = self.factory.makeProduct()
        repo = self.factory.makeGitRepository(target=project)
        naked_project = removeSecurityProxy(project)
        with person_logged_in(repo.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repo.target, repo
            )
        self.assertRedirects(naked_project.name, canonical_url(repo))

    def test_private_bzr_branch_for_product(self):
        branch = self.factory.makeProductBranch()
        naked_product = removeSecurityProxy(branch.product)
        ICanHasLinkedBranch(naked_product).setBranch(branch)
        removeSecurityProxy(branch).information_type = InformationType.USERDATA
        login(ANONYMOUS)
        self.assertNotFound(naked_product.name)

    def test_private_git_branch_for_product(self):
        project = self.factory.makeProduct()
        repo = self.factory.makeGitRepository(target=project)
        with person_logged_in(repo.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repo.target, repo
            )

        removeSecurityProxy(repo).information_type = InformationType.USERDATA
        login(ANONYMOUS)

        naked_project = removeSecurityProxy(project)
        self.assertNotFound(naked_project.name)

    def test_nonexistent_product(self):
        non_existent = "non-existent"
        self.assertNotFound(non_existent)

    def test_product_without_dev_focus(self):
        product = self.factory.makeProduct()
        self.assertNotFound(product.name)

    def test_distro_package_alias_bzr(self):
        sourcepackage = self.factory.makeSourcePackage()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        distro_package = sourcepackage.distribution_sourcepackage
        registrant = distro_package.distribution.owner
        target = ICanHasLinkedBranch(distro_package)
        with person_logged_in(registrant):
            target.setBranch(branch, registrant)
        self.assertRedirects("%s" % target.bzr_path, canonical_url(branch))

    def test_distro_package_alias_git(self):
        sourcepackage = self.factory.makeSourcePackage()
        distro_package = sourcepackage.distribution_sourcepackage
        repo = self.factory.makeGitRepository(target=distro_package)

        with admin_logged_in():
            getUtility(IGitRepositorySet).setDefaultRepository(
                distro_package, repo
            )

        self.assertRedirects("%s" % repo.shortened_path, canonical_url(repo))

    def test_private_branch_for_distro_package_bzr(self):
        sourcepackage = self.factory.makeSourcePackage()
        branch = self.factory.makePackageBranch(
            sourcepackage=sourcepackage,
            information_type=InformationType.USERDATA,
        )
        distro_package = sourcepackage.distribution_sourcepackage
        registrant = distro_package.distribution.owner
        with person_logged_in(registrant):
            ICanHasLinkedBranch(distro_package).setBranch(branch, registrant)
        login(ANONYMOUS)
        path = ICanHasLinkedBranch(distro_package).bzr_path
        self.assertNotFound(path)

    def test_private_branch_for_distro_package_git(self):
        sourcepackage = self.factory.makeSourcePackage()
        distro_package = sourcepackage.distribution_sourcepackage
        repo = self.factory.makeGitRepository(
            target=distro_package, information_type=InformationType.USERDATA
        )
        with admin_logged_in():
            getUtility(IGitRepositorySet).setDefaultRepository(
                distro_package, repo
            )
        login(ANONYMOUS)
        path = removeSecurityProxy(repo).shortened_path
        self.assertNotFound(path)

    def test_trailing_path_redirect_bzr(self):
        branch = self.factory.makeAnyBranch()
        path = urlappend(branch.unique_name, "+edit")
        self.assertRedirects(path, canonical_url(branch, view_name="+edit"))

    def test_trailing_path_redirect_git(self):
        repo = self.factory.makeGitRepository()
        path = urlappend(repo.unique_name, "+edit")
        self.assertRedirects(path, canonical_url(repo, view_name="+edit"))

    def test_alias_trailing_path_redirect_bzr(self):
        branch = self.factory.makeProductBranch()
        with person_logged_in(branch.product.owner):
            branch.product.development_focus.branch = branch
        path = "%s/+edit" % branch.product.name
        self.assertRedirects(path, canonical_url(branch, view_name="+edit"))

    def test_alias_trailing_path_redirect_git(self):
        project = self.factory.makeProduct()
        repo = self.factory.makeGitRepository(target=project)
        with admin_logged_in():
            getUtility(IGitRepositorySet).setDefaultRepository(project, repo)
        path = "%s/+edit" % project.name
        self.assertRedirects(path, canonical_url(repo, view_name="+edit"))

    def test_product_series_redirect_bzr(self):
        branch = self.factory.makeBranch()
        series = self.factory.makeProductSeries(branch=branch)
        self.assertRedirects(
            ICanHasLinkedBranch(series).bzr_path, canonical_url(branch)
        )

    def test_no_branch_for_series(self):
        # If there's no branch for a product series, display a
        # message telling the user there is no linked branch.
        series = self.factory.makeProductSeries()
        path = ICanHasLinkedBranch(series).bzr_path
        self.assertNotFound(path)

    def test_private_branch_for_series(self):
        # If the development focus of a product series is private, display a
        # message telling the user there is no linked branch.
        branch = self.factory.makeBranch(
            information_type=InformationType.USERDATA
        )
        series = self.factory.makeProductSeries(branch=branch)
        login(ANONYMOUS)
        path = ICanHasLinkedBranch(series).bzr_path
        self.assertNotFound(path)

    def test_too_short_branch_name(self):
        owner = self.factory.makePerson()
        self.assertNotFound("~%s" % owner.name)

    def test_invalid_product_name(self):
        self.assertNotFound("_foo")

    def test_invalid_product_name_without_referer(self):
        self.assertNotFound("_foo", use_default_referer=False)

    def test_ambiguous_project_default_repo_bzr(self):
        project = self.factory.makeProduct()
        bzr_branch = self.factory.makeBranch(target=project)
        self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            ICanHasLinkedBranch(project).setBranch(bzr_branch, project.owner)

        self.assertRedirects(project.name, canonical_url(bzr_branch))

    def test_ambiguous_project_without_vcs_set(self):
        project = self.factory.makeProduct()
        bzr_branch = self.factory.makeBranch(target=project)
        repo = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            ICanHasLinkedBranch(project).setBranch(bzr_branch, project.owner)
            getUtility(IGitRepositorySet).setDefaultRepository(project, repo)

        self.assertNotFound(project.name)

    def test_ambiguous_project_with_vcs_set_to_git(self):
        project = self.factory.makeProduct()
        bzr_branch = self.factory.makeBranch(target=project)
        repo = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            ICanHasLinkedBranch(project).setBranch(bzr_branch, project.owner)
            getUtility(IGitRepositorySet).setDefaultRepository(project, repo)
            project.vcs = VCSType.GIT

        self.assertRedirects(project.name, canonical_url(repo))

    def test_ambiguous_project_with_vcs_set_to_bzr(self):
        project = self.factory.makeProduct()
        bzr_branch = self.factory.makeBranch(target=project)
        repo = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            ICanHasLinkedBranch(project).setBranch(bzr_branch, project.owner)
            getUtility(IGitRepositorySet).setDefaultRepository(project, repo)
            project.vcs = VCSType.BZR

        self.assertRedirects(project.name, canonical_url(bzr_branch))

    def test_personal_branch_bzr(self):
        person = self.factory.makePerson()
        branch = self.factory.makePersonalBranch(owner=person)
        self.assertRedirects(branch.unique_name, canonical_url(branch))

    def test_personal_branch_git(self):
        person = self.factory.makePerson()
        repo = self.factory.makeGitRepository(owner=person, target=person)
        self.assertRedirects(repo.unique_name, canonical_url(repo))


class TestPersonTraversal(TestCaseWithFactory, TraversalMixin):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        self.any_user = self.factory.makePerson()
        self.admin = getUtility(IPersonSet).getByName("name16")
        self.registry_expert = self.factory.makePerson()
        registry = getUtility(ILaunchpadCelebrities).registry_experts
        with person_logged_in(registry.teamowner):
            registry.addMember(self.registry_expert, registry.teamowner)

    def test_person(self):
        # Verify a user is returned.
        name = "active-person"
        person = self.factory.makePerson(name=name)
        segment = "~%s" % name
        traversed = self.traverse(segment, segment)
        self.assertEqual(person, traversed)

    def test_suspended_person_visibility(self):
        # Verify a suspended user is only traversable by an admin.
        name = "suspended-person"
        person = self.factory.makePerson(name=name)
        login_person(self.admin)
        person.setAccountStatus(AccountStatus.SUSPENDED, None, "Go away")
        segment = "~%s" % name
        # Admins can see the suspended user.
        traversed = self.traverse(segment, segment)
        self.assertEqual(person, traversed)
        # Registry experts can see the suspended user.
        login_person(self.registry_expert)
        traversed = self.traverse(segment, segment)
        # Regular users cannot see the suspended user.
        login_person(self.any_user)
        self.assertRaises(GoneError, self.traverse, segment, segment)

    def test_placeholder_person_visibility(self):
        # Verify a placeholder user is only traversable by an admin.
        name = "placeholder-person"
        person = getUtility(IPersonSet).createPlaceholderPerson(name, name)
        login_person(self.admin)
        segment = "~%s" % name
        # Admins can see the placeholder user.
        traversed = self.traverse(segment, segment)
        self.assertEqual(person, traversed)
        # Registry experts can see the placeholder user.
        login_person(self.registry_expert)
        traversed = self.traverse(segment, segment)
        self.assertEqual(person, traversed)
        # Regular users cannot see the placeholder user.
        login_person(self.any_user)
        self.assertRaises(NotFound, self.traverse, segment, segment)

    def test_public_team(self):
        # Verify a public team is returned.
        name = "public-team"
        team = self.factory.makeTeam(name=name)
        segment = "~%s" % name
        traversed = self.traverse(segment, segment)
        self.assertEqual(team, traversed)

    def test_private_team_visible_to_admin_and_members_only(self):
        # Verify a private team is  team is returned.
        name = "private-team"
        team = self.factory.makeTeam(name=name)
        login_person(self.admin)
        team.visibility = PersonVisibility.PRIVATE
        segment = "~%s" % name
        # Admins can traverse to the team.
        traversed = self.traverse(segment, segment)
        self.assertEqual(team, traversed)
        # Members can traverse to the team.
        login_person(team.teamowner)
        traversed = self.traverse(segment, segment)
        self.assertEqual(team, traversed)
        # All other user cannot traverse to the team.
        login_person(self.any_user)
        self.assertRaises(NotFound, self.traverse, segment, segment)

    def test_self_url_traversal(self):
        # Just /~/ expands to the current user.  (Bug 785800).
        person = self.factory.makePerson()
        login_person(person)
        obj, view, req = test_traverse("http://launchpad.test/~")
        view = removeSecurityProxy(view)
        self.assertEqual(canonical_url(person), view.target.rstrip("/"))

    def test_self_url_not_logged_in(self):
        # /~/ when not logged in asks you to log in.
        self.assertRaises(
            Unauthorized, test_traverse, "http://launchpad.test/~"
        )

    def test_self_url_pathinfo(self):
        # You can traverse below /~/.
        person = self.factory.makePerson()
        login_person(person)
        obj, view, req = test_traverse("http://launchpad.test/~/+editsshkeys")
        view = removeSecurityProxy(view)
        self.assertEqual(canonical_url(person) + "/+editsshkeys", view.target)

    def test_self_url_app_domain(self):
        # You can traverse below /~/.
        person = self.factory.makePerson()
        login_person(person)
        obj, view, req = test_traverse("http://bugs.launchpad.test/~")
        view = removeSecurityProxy(view)
        self.assertEqual(
            canonical_url(person, rootsite="bugs"), view.target.rstrip("/")
        )


class TestErrorViews(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_GoneError(self):
        error = GoneError("User is suspended")
        view = create_view(error, "index.html")
        self.assertEqual("Error: Page gone", view.page_title)
        self.assertEqual(410, view.request.response.getStatus())


class ExceptionHierarchyTestCase(TestCaseWithFactory):
    layer = FunctionalLayer

    def test_exception(self):
        view = create_view(IndexError("test"), "+hierarchy")
        view.request.traversed_objects = [getUtility(ILaunchpadRoot)]
        self.assertEqual([], view.objects)

    def test_zope_exception(self):
        view = create_view(Unauthorized("test"), "+hierarchy")
        view.request.traversed_objects = [getUtility(ILaunchpadRoot)]
        self.assertEqual([], view.objects)

    def test_launchapd_exception(self):
        view = create_view(NotFound(None, "test"), "+hierarchy")
        view.request.traversed_objects = [getUtility(ILaunchpadRoot)]
        self.assertEqual([], view.objects)


class TestIterViewRegistrations(TestCaseWithFactory):
    layer = FunctionalLayer

    def test_iter_view_registrations(self):
        """iter_view_registrations provides only registrations of class."""
        macros = getMultiAdapter(
            (object(), LaunchpadTestRequest()), name="+base-layout-macros"
        )
        names = {reg.name for reg in iter_view_registrations(macros.__class__)}
        self.assertIn("+base-layout-macros", names)
        self.assertNotIn("+related-pages", names)


class TestProductTraversal(TestCaseWithFactory, TraversalMixin):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        self.active_public_product = self.factory.makeProduct()
        self.inactive_public_product = self.factory.makeProduct()
        removeSecurityProxy(self.inactive_public_product).active = False
        self.proprietary_product_owner = self.factory.makePerson()
        self.active_proprietary_product = self.factory.makeProduct(
            owner=self.proprietary_product_owner,
            information_type=InformationType.PROPRIETARY,
        )
        self.inactive_proprietary_product = self.factory.makeProduct(
            owner=self.proprietary_product_owner,
            information_type=InformationType.PROPRIETARY,
        )
        removeSecurityProxy(self.inactive_proprietary_product).active = False

    def traverse_to_active_public_product(self):
        segment = self.active_public_product.name
        self.traverse(segment, segment)

    def traverse_to_inactive_public_product(self):
        segment = removeSecurityProxy(self.inactive_public_product).name
        self.traverse(segment, segment)

    def traverse_to_active_proprietary_product(self):
        segment = removeSecurityProxy(self.active_proprietary_product).name
        self.traverse(segment, segment)

    def traverse_to_inactive_proprietary_product(self):
        segment = removeSecurityProxy(self.inactive_proprietary_product).name
        self.traverse(segment, segment)

    def test_access_for_anon(self):
        # Anonymous users can see only public active products.
        with person_logged_in(ANONYMOUS):
            self.traverse_to_active_public_product()
            # Access to other products raises a NotFound error.
            self.assertRaises(
                NotFound, self.traverse_to_inactive_public_product
            )
            self.assertRaises(
                NotFound, self.traverse_to_active_proprietary_product
            )
            self.assertRaises(
                NotFound, self.traverse_to_inactive_proprietary_product
            )

    def test_access_for_ordinary_users(self):
        # Ordinary logged in users can see only public active products.
        with person_logged_in(self.factory.makePerson()):
            self.traverse_to_active_public_product()
            # Access to other products raises a NotFound error.
            self.assertRaises(
                NotFound, self.traverse_to_inactive_public_product
            )
            self.assertRaises(
                NotFound, self.traverse_to_active_proprietary_product
            )
            self.assertRaises(
                NotFound, self.traverse_to_inactive_proprietary_product
            )

    def test_access_for_person_with_pillar_grant(self):
        # Persons with a policy grant for a proprietary product can
        # access this product, if it is active.
        user = self.factory.makePerson()
        with person_logged_in(self.proprietary_product_owner):
            getUtility(IService, "sharing").sharePillarInformation(
                self.active_proprietary_product,
                user,
                self.proprietary_product_owner,
                {InformationType.PROPRIETARY: SharingPermission.ALL},
            )
            getUtility(IService, "sharing").sharePillarInformation(
                self.inactive_proprietary_product,
                user,
                self.proprietary_product_owner,
                {InformationType.PROPRIETARY: SharingPermission.ALL},
            )
        with person_logged_in(user):
            self.traverse_to_active_public_product()
            self.assertRaises(
                NotFound, self.traverse_to_inactive_public_product
            )
            self.traverse_to_active_proprietary_product()
            self.assertRaises(
                NotFound, self.traverse_to_inactive_proprietary_product
            )

    def test_access_for_persons_with_artifact_grant(self):
        # Persons with an artifact grant related to a private product
        # can traverse the product.
        user = self.factory.makePerson()
        with person_logged_in(self.proprietary_product_owner):
            bug = self.factory.makeBug(
                target=self.active_proprietary_product,
                information_type=InformationType.PROPRIETARY,
            )
            getUtility(IService, "sharing").ensureAccessGrants(
                [user], self.proprietary_product_owner, bugs=[bug]
            )
        with person_logged_in(user):
            self.traverse_to_active_proprietary_product()

    def check_admin_access(self):
        self.traverse_to_active_public_product()
        self.traverse_to_inactive_public_product()
        self.traverse_to_active_proprietary_product()
        self.traverse_to_inactive_proprietary_product()

    def test_access_for_persons_with_special_permissions(self):
        # Admins have access all products, including inactive and propretary
        # products.
        with celebrity_logged_in("admin"):
            self.check_admin_access()
        # Commercial admins have access to all products.
        with celebrity_logged_in("commercial_admin"):
            self.check_admin_access()
