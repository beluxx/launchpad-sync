# -*- coding: utf-8 -*-
# NOTE: The first line above must stay first; do not move the copyright
# notice to the top.  See http://www.python.org/dev/peps/pep-0263/.
#
# Copyright 2015-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git repositories."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
from functools import partial
import hashlib
import json

from breezy import urlutils
from fixtures import MockPatch
from lazr.lifecycle.event import ObjectModifiedEvent
from pymacaroons import Macaroon
import pytz
import six
from sqlobject import SQLObjectNotFound
from storm.exceptions import LostObjectError
from storm.store import Store
from testtools.matchers import (
    AnyMatch,
    ContainsDict,
    EndsWith,
    Equals,
    Is,
    IsInstance,
    LessThan,
    MatchesDict,
    MatchesListwise,
    MatchesSetwise,
    MatchesStructure,
    StartsWith,
    )
import transaction
from zope.component import getUtility
from zope.publisher.xmlrpc import TestRequest
from zope.security.interfaces import (
    ForbiddenAttribute,
    Unauthorized,
    )
from zope.security.proxy import removeSecurityProxy

from lp import _
from lp.app.enums import (
    InformationType,
    PRIVATE_INFORMATION_TYPES,
    PUBLIC_INFORMATION_TYPES,
    )
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.charms.interfaces.charmrecipe import CHARM_RECIPE_ALLOW_CREATE
from lp.code.enums import (
    BranchMergeProposalStatus,
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    GitGranteeType,
    GitListingSort,
    GitObjectType,
    GitRepositoryStatus,
    GitRepositoryType,
    TargetRevisionControlSystems,
    )
from lp.code.errors import (
    CannotDeleteGitRepository,
    CannotModifyNonHostedGitRepository,
    GitRepositoryCreatorNotMemberOfOwnerTeam,
    GitRepositoryCreatorNotOwner,
    GitRepositoryExists,
    GitTargetError,
    NoSuchGitReference,
    )
from lp.code.event.git import GitRefsUpdatedEvent
from lp.code.interfaces.branchmergeproposal import (
    BRANCH_MERGE_PROPOSAL_FINAL_STATES as FINAL_STATES,
    )
from lp.code.interfaces.codeimport import ICodeImportSet
from lp.code.interfaces.defaultgit import ICanHasDefaultGitRepository
from lp.code.interfaces.gitjob import (
    IGitRefScanJobSource,
    IGitRepositoryModifiedMailJobSource,
    )
from lp.code.interfaces.gitlookup import IGitLookup
from lp.code.interfaces.gitnamespace import (
    IGitNamespacePolicy,
    IGitNamespaceSet,
    )
from lp.code.interfaces.gitrepository import (
    IGitRepository,
    IGitRepositorySet,
    IGitRepositoryView,
    )
from lp.code.interfaces.gitrule import (
    IGitNascentRule,
    IGitNascentRuleGrant,
    )
from lp.code.interfaces.revision import IRevisionSet
from lp.code.model.branchmergeproposal import BranchMergeProposal
from lp.code.model.branchmergeproposaljob import (
    BranchMergeProposalJob,
    BranchMergeProposalJobType,
    UpdatePreviewDiffJob,
    )
from lp.code.model.codereviewcomment import CodeReviewComment
from lp.code.model.gitactivity import GitActivity
from lp.code.model.gitjob import (
    GitJob,
    GitJobType,
    GitRefScanJob,
    ReclaimGitRepositorySpaceJob,
    )
from lp.code.model.gitrepository import (
    ClearPrerequisiteRepository,
    DeleteCodeImport,
    DeletionCallable,
    DeletionOperation,
    GitRepository,
    )
from lp.code.tests.helpers import GitHostingFixture
from lp.code.xmlrpc.git import GitAPI
from lp.registry.enums import (
    BranchSharingPolicy,
    PersonVisibility,
    TeamMembershipPolicy,
    )
from lp.registry.interfaces.accesspolicy import (
    IAccessArtifactSource,
    IAccessPolicyArtifactSource,
    IAccessPolicySource,
    )
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.persondistributionsourcepackage import (
    IPersonDistributionSourcePackageFactory,
    )
from lp.registry.interfaces.personociproject import IPersonOCIProjectFactory
from lp.registry.interfaces.personproduct import IPersonProductFactory
from lp.registry.tests.test_accesspolicy import get_policies_for_artifact
from lp.services.authserver.xmlrpc import AuthServerAPIView
from lp.services.compat import message_from_bytes
from lp.services.config import config
from lp.services.database.constants import UTC_NOW
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import get_transaction_timestamp
from lp.services.features.testing import FeatureFixture
from lp.services.identity.interfaces.account import AccountStatus
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.services.job.runner import JobRunner
from lp.services.macaroons.interfaces import IMacaroonIssuer
from lp.services.macaroons.testing import (
    find_caveats_by_name,
    MacaroonTestMixin,
    )
from lp.services.mail import stub
from lp.services.openid.model.openididentifier import OpenIdIdentifier
from lp.services.propertycache import clear_property_cache
from lp.services.utils import seconds_since_epoch
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.interfaces import OAuthPermission
from lp.services.webapp.snapshot import notify_modified
from lp.snappy.interfaces.snap import SNAP_TESTING_FLAGS
from lp.testing import (
    admin_logged_in,
    ANONYMOUS,
    api_url,
    celebrity_logged_in,
    login_person,
    person_logged_in,
    record_two_runs,
    StormStatementRecorder,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.dbuser import dbuser
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.mail_helpers import pop_notifications
from lp.testing.matchers import (
    DoesNotSnapshot,
    HasQueryCount,
    )
from lp.testing.pages import webservice_for_person
from lp.xmlrpc import faults
from lp.xmlrpc.interfaces import IPrivateApplication


class TestGitRepository(TestCaseWithFactory):
    """Test basic properties about Launchpad database Git repositories."""

    layer = DatabaseFunctionalLayer

    def test_implements_IGitRepository(self):
        repository = self.factory.makeGitRepository()
        verifyObject(IGitRepository, repository)

    def test_avoids_large_snapshots(self):
        large_properties = [
            'refs',
            'branches',
            '_api_landing_targets',
            '_api_landing_candidates',
            'dependent_landings',
            ]
        self.assertThat(
            self.factory.makeGitRepository(),
            DoesNotSnapshot(large_properties, IGitRepositoryView))

    def test_git_repository_default_status(self):
        repository = self.factory.makeGitRepository()
        store = Store.of(repository)

        self.assertEqual(GitRepositoryStatus.AVAILABLE, repository.status)

        removeSecurityProxy(repository).status = GitRepositoryStatus.CREATING
        store.flush()
        self.assertEqual(GitRepositoryStatus.CREATING, repository.status)

    def test_git_repository_status_is_read_only(self):
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.owner):
            self.assertRaises(
                ForbiddenAttribute,
                setattr, repository, 'status', GitRepositoryStatus.CREATING)

    def test_unique_name_project(self):
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(target=project)
        self.assertEqual(
            "~%s/%s/+git/%s" % (
                repository.owner.name, project.name, repository.name),
            repository.unique_name)

    def test_unique_name_package(self):
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        self.assertEqual(
            "~%s/%s/+source/%s/+git/%s" % (
                repository.owner.name, dsp.distribution.name,
                dsp.sourcepackagename.name, repository.name),
            repository.unique_name)

    def test_unique_name_oci_project(self):
        oci_project = self.factory.makeOCIProject()
        repository = self.factory.makeGitRepository(target=oci_project)
        self.assertEqual(
            "~%s/%s/+oci/%s/+git/%s" % (
                repository.owner.name, oci_project.distribution.name,
                oci_project.ociprojectname.name, repository.name),
            repository.unique_name)

    def test_unique_name_personal(self):
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        self.assertEqual(
            "~%s/+git/%s" % (owner.name, repository.name),
            repository.unique_name)

    def test_target_project(self):
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(target=project)
        self.assertEqual(project, repository.target)

    def test_target_package(self):
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        self.assertEqual(dsp, repository.target)

    def test_target_ociproject(self):
        oci_project = self.factory.makeOCIProject()
        repository = self.factory.makeGitRepository(target=oci_project)
        self.assertEqual(oci_project, repository.target)

    def test_target_personal(self):
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        self.assertEqual(owner, repository.target)

    def test_code_import(self):
        self.useFixture(GitHostingFixture())
        code_import = self.factory.makeCodeImport(
            target_rcs_type=TargetRevisionControlSystems.GIT)
        repository = code_import.git_repository
        self.assertEqual(code_import, repository.code_import)
        getUtility(ICodeImportSet).delete(code_import)
        clear_property_cache(repository)
        self.assertIsNone(repository.code_import)

    def test_getMergeProposals(self):
        repository = self.factory.makeGitRepository()
        [ref] = self.factory.makeGitRefs(repository=repository)
        bmp = self.factory.makeBranchMergeProposalForGit(target_ref=ref)
        self.assertEqual([bmp], list(repository.getMergeProposals()))

    def test_findRuleGrantsByGrantee_person(self):
        requester = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=requester))

        rule = self.factory.makeGitRule(repository)
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=requester, can_push=True, can_create=True)

        results = repository.findRuleGrantsByGrantee(requester)
        self.assertEqual([grant], list(results))

    def test_findRuleGrantsByGrantee_team(self):
        requester = self.factory.makeTeam()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=requester))

        rule = self.factory.makeGitRule(repository)
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=requester, can_push=True, can_create=True)

        results = repository.findRuleGrantsByGrantee(requester)
        self.assertEqual([grant], list(results))

    def test_findRuleGrantsByGrantee_member_of_team(self):
        member = self.factory.makePerson()
        requester = self.factory.makeTeam(members=[member])
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=requester))

        rule = self.factory.makeGitRule(repository)
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=requester, can_push=True, can_create=True)

        results = repository.findRuleGrantsByGrantee(member)
        self.assertEqual([grant], list(results))

    def test_findRuleGrantsByGrantee_team_in_team(self):
        member = self.factory.makePerson()
        team = self.factory.makeTeam(owner=member, members=[member])
        top_level = removeSecurityProxy(self.factory.makeTeam())
        top_level.addMember(team, top_level.teamowner, force_team_add=True)

        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=top_level))

        rule = self.factory.makeGitRule(repository)
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=top_level, can_push=True, can_create=True)

        results = repository.findRuleGrantsByGrantee(member)
        self.assertEqual([grant], list(results))

    def test_findRuleGrantsByGrantee_team_in_team_not_owner(self):
        member = self.factory.makePerson()
        team = self.factory.makeTeam(owner=member, members=[member])
        top_level = removeSecurityProxy(self.factory.makeTeam())
        top_level.addMember(team, top_level.teamowner, force_team_add=True)

        repository = removeSecurityProxy(
            self.factory.makeGitRepository())

        rule = self.factory.makeGitRule(repository)
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=top_level, can_push=True, can_create=True)

        results = repository.findRuleGrantsByGrantee(member)
        self.assertEqual([grant], list(results))

    def test_findRuleGrantsByGrantee_not_owner(self):
        requester = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository())

        rule = self.factory.makeGitRule(repository)
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=requester, can_push=True, can_create=True)

        results = repository.findRuleGrantsByGrantee(requester)
        self.assertEqual([grant], list(results))

    def test_findRuleGrantsByGrantee_grantee_type(self):
        requester = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=requester))

        rule = self.factory.makeGitRule(repository)
        grant = self.factory.makeGitRuleGrant(
            rule=rule,
            grantee=GitGranteeType.REPOSITORY_OWNER,
            can_push=True,
            can_create=True)
        self.factory.makeGitRuleGrant(rule=rule)

        results = repository.findRuleGrantsByGrantee(
            GitGranteeType.REPOSITORY_OWNER)
        self.assertEqual([grant], list(results))

    def test_findRuleGrantsByGrantee_owner_and_other(self):
        requester = self.factory.makePerson()
        other = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=requester))

        rule = self.factory.makeGitRule(repository)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=other, can_push=True, can_create=True)

        results = repository.findRuleGrantsByGrantee(requester)
        self.assertEqual([], list(results))

    def test_findRuleGrantsByGrantee_owner_and_other_with_owner_grant(self):
        requester = self.factory.makePerson()
        other = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=requester))

        rule = self.factory.makeGitRule(repository)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=other, can_push=True, can_create=True)
        owner_grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=requester, can_push=True)

        results = repository.findRuleGrantsByGrantee(requester)
        self.assertEqual([owner_grant], list(results))

    def test_findRuleGrantsByGrantee_ref_pattern(self):
        requester = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=requester))
        [ref] = self.factory.makeGitRefs(repository=repository)

        exact_grant = self.factory.makeGitRuleGrant(
            repository=repository, ref_pattern=ref.path, grantee=requester)
        self.factory.makeGitRuleGrant(
            repository=repository, ref_pattern="refs/heads/*",
            grantee=requester)

        results = repository.findRuleGrantsByGrantee(
            requester, ref_pattern=ref.path)
        self.assertEqual([exact_grant], list(results))

    def test_findRuleGrantsByGrantee_exclude_transitive_person(self):
        requester = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=requester))

        rule = self.factory.makeGitRule(repository)
        grant = self.factory.makeGitRuleGrant(rule=rule, grantee=requester)

        results = repository.findRuleGrantsByGrantee(
            requester, include_transitive=False)
        self.assertEqual([grant], list(results))

    def test_findRuleGrantsByGrantee_exclude_transitive_team(self):
        team = self.factory.makeTeam()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=team))

        rule = self.factory.makeGitRule(repository)
        grant = self.factory.makeGitRuleGrant(rule=rule, grantee=team)

        results = repository.findRuleGrantsByGrantee(
            team, include_transitive=False)
        self.assertEqual([grant], list(results))

    def test_findRuleGrantsByGrantee_exclude_transitive_member_of_team(self):
        member = self.factory.makePerson()
        team = self.factory.makeTeam(members=[member])
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(owner=team))

        rule = self.factory.makeGitRule(repository)
        self.factory.makeGitRuleGrant(rule=rule, grantee=team)

        results = repository.findRuleGrantsByGrantee(
            member, include_transitive=False)
        self.assertEqual([], list(results))

    def test_findRuleGrantsByGrantee_no_owner_grant(self):
        repository = removeSecurityProxy(self.factory.makeGitRepository())

        rule = self.factory.makeGitRule(repository=repository)
        self.factory.makeGitRuleGrant(rule=rule)

        results = repository.findRuleGrantsByGrantee(
            GitGranteeType.REPOSITORY_OWNER)
        self.assertEqual([], list(results))

    def test_findRuleGrantsByGrantee_owner_grant(self):
        repository = removeSecurityProxy(self.factory.makeGitRepository())

        rule = self.factory.makeGitRule(repository=repository)
        grant = self.factory.makeGitRuleGrant(
            rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER)
        self.factory.makeGitRuleGrant(rule=rule)

        results = repository.findRuleGrantsByGrantee(
            GitGranteeType.REPOSITORY_OWNER)
        self.assertEqual([grant], list(results))

    def test_findRuleGrantsByGrantee_owner_ref_pattern(self):
        repository = removeSecurityProxy(self.factory.makeGitRepository())
        [ref] = self.factory.makeGitRefs(repository=repository)

        exact_grant = self.factory.makeGitRuleGrant(
            repository=repository, ref_pattern=ref.path,
            grantee=GitGranteeType.REPOSITORY_OWNER)
        self.factory.makeGitRuleGrant(
            repository=repository, ref_pattern="refs/heads/*",
            grantee=GitGranteeType.REPOSITORY_OWNER)

        results = ref.repository.findRuleGrantsByGrantee(
            GitGranteeType.REPOSITORY_OWNER, ref_pattern=ref.path)
        self.assertEqual([exact_grant], list(results))

    def test_findRuleGrantsByGrantee_owner_exclude_transitive(self):
        repository = removeSecurityProxy(self.factory.makeGitRepository())
        [ref] = self.factory.makeGitRefs(repository=repository)

        exact_grant = self.factory.makeGitRuleGrant(
            repository=repository, ref_pattern=ref.path,
            grantee=GitGranteeType.REPOSITORY_OWNER)
        self.factory.makeGitRuleGrant(
            rule=exact_grant.rule, grantee=repository.owner)
        wildcard_grant = self.factory.makeGitRuleGrant(
            repository=repository, ref_pattern="refs/heads/*",
            grantee=GitGranteeType.REPOSITORY_OWNER)

        results = ref.repository.findRuleGrantsByGrantee(
            GitGranteeType.REPOSITORY_OWNER, include_transitive=False)
        self.assertItemsEqual([exact_grant, wildcard_grant], list(results))
        results = ref.repository.findRuleGrantsByGrantee(
            GitGranteeType.REPOSITORY_OWNER, ref_pattern=ref.path,
            include_transitive=False)
        self.assertEqual([exact_grant], list(results))

    def test_getRefsPermission_query_count(self):
        repository = self.factory.makeGitRepository()
        owner = repository.owner
        grantees = [self.factory.makePerson() for _ in range(2)]

        ref_paths = ['refs/heads/master']

        def add_fake_refs_to_request():
            ref_paths.append(
                self.factory.getUniqueUnicode("refs/heads/branch"))

            with admin_logged_in():
                teams = [self.factory.makeTeam() for _ in range(2)]
                teams[0].addMember(grantees[0], teams[0].teamowner)
                teams[1].addMember(grantees[1], teams[1].teamowner)
            master_rule = self.factory.makeGitRule(
                repository=repository, ref_pattern=ref_paths[-1])
            self.factory.makeGitRuleGrant(
                rule=master_rule, grantee=teams[0], can_create=True)
            self.factory.makeGitRuleGrant(
                rule=master_rule, grantee=teams[1], can_push=True)

        def check_permissions():
            repository.checkRefPermissions(grantees[0], ref_paths)

        recorder1, recorder2 = record_two_runs(
            check_permissions, add_fake_refs_to_request, 1, 10,
            login_method=lambda: login_person(owner))

        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))
        self.assertEqual(7, recorder1.count)


class TestGitIdentityMixin(TestCaseWithFactory):
    """Test the defaults and identities provided by GitIdentityMixin."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitIdentityMixin, self).setUp()
        self.repository_set = getUtility(IGitRepositorySet)

    def assertGitIdentity(self, repository, identity_path):
        """Assert that the Git identity of 'repository' is 'identity_path'.

        Actually, it'll be lp:<identity_path>.
        """
        self.assertEqual(
            identity_path, repository.shortened_path, "shortened path")
        self.assertEqual(
            "lp:%s" % identity_path, repository.git_identity, "git identity")

    def test_git_identity_default(self):
        # By default, the Git identity is the repository's unique name.
        repository = self.factory.makeGitRepository()
        self.assertGitIdentity(repository, repository.unique_name)

    def test_git_identity_default_for_project(self):
        # If a repository is the default for a project, then its Git
        # identity is the project name.
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(
            owner=project.owner, target=project)
        with person_logged_in(project.owner):
            self.repository_set.setDefaultRepository(project, repository)
        self.assertGitIdentity(repository, project.name)

    def test_git_identity_private_default_for_project(self):
        # Private repositories also have a short lp: URL.
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(
            target=project, information_type=InformationType.USERDATA)
        with admin_logged_in():
            self.repository_set.setDefaultRepository(project, repository)
            self.assertGitIdentity(repository, project.name)

    def test_git_identity_default_for_package(self):
        # If a repository is the default for a package, then its Git
        # identity uses the path to that package.
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        with admin_logged_in():
            self.repository_set.setDefaultRepository(dsp, repository)
        self.assertGitIdentity(
            repository,
            "%s/+source/%s" % (
                dsp.distribution.name, dsp.sourcepackagename.name))

    def test_git_identity_default_for_oci_project(self):
        # If a repository is the default for an OCI project, then its Git
        # identity uses the path to that OCI project.
        oci_project = self.factory.makeOCIProject()
        repository = self.factory.makeGitRepository(target=oci_project)
        with admin_logged_in():
            self.repository_set.setDefaultRepository(oci_project, repository)
        self.assertGitIdentity(
            repository,
            "%s/+oci/%s" % (oci_project.pillar.name, oci_project.name))

    def test_git_identity_owner_default_for_project(self):
        # If a repository is a person's default for a project, then its Git
        # identity is a combination of the person and project names.
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(target=project)
        with person_logged_in(repository.owner) as user:
            self.repository_set.setDefaultRepositoryForOwner(
                repository.owner, project, repository, user)
        self.assertGitIdentity(
            repository, "~%s/%s" % (repository.owner.name, project.name))

    def test_git_identity_owner_default_for_package(self):
        # If a repository is a person's default for a package, then its Git
        # identity is a combination of the person name and the package path.
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        with person_logged_in(repository.owner) as user:
            self.repository_set.setDefaultRepositoryForOwner(
                repository.owner, dsp, repository, user)
        self.assertGitIdentity(
            repository,
            "~%s/%s/+source/%s" % (
                repository.owner.name, dsp.distribution.name,
                dsp.sourcepackagename.name))

    def test_git_identity_owner_default_for_oci_project(self):
        # If a repository is a person's default for an OCI project, then its
        # Git identity is a combination of the person name and the OCI
        # project path.
        oci_project = self.factory.makeOCIProject()
        repository = self.factory.makeGitRepository(target=oci_project)
        with person_logged_in(repository.owner) as user:
            self.repository_set.setDefaultRepositoryForOwner(
                repository.owner, oci_project, repository, user)
        self.assertGitIdentity(
            repository,
            "~%s/%s/+oci/%s" % (
                repository.owner.name, oci_project.pillar.name,
                oci_project.name))

    def test_identities_no_defaults(self):
        # If there are no defaults, the only repository identity is the
        # unique name.
        repository = self.factory.makeGitRepository()
        self.assertEqual(
            [(repository.unique_name, repository)],
            repository.getRepositoryIdentities())

    def test_default_for_project(self):
        # If a repository is the default for a project, then that is the
        # preferred identity.  Target defaults are preferred over
        # owner-target defaults.
        eric = self.factory.makePerson(name="eric")
        fooix = self.factory.makeProduct(name="fooix", owner=eric)
        repository = self.factory.makeGitRepository(
            owner=eric, target=fooix, name="fooix-repo")
        with person_logged_in(fooix.owner) as user:
            self.repository_set.setDefaultRepositoryForOwner(
                repository.owner, fooix, repository, user)
            self.repository_set.setDefaultRepository(fooix, repository)
        eric_fooix = getUtility(IPersonProductFactory).create(eric, fooix)
        self.assertEqual(
            [ICanHasDefaultGitRepository(target)
             for target in (fooix, eric_fooix)],
            repository.getRepositoryDefaults())
        self.assertEqual(
            [("fooix", fooix), ("~eric/fooix", eric_fooix),
             ("~eric/fooix/+git/fooix-repo", repository)],
            repository.getRepositoryIdentities())

    def test_default_for_package(self):
        # If a repository is the default for a package, then that is the
        # preferred identity.  Target defaults are preferred over
        # owner-target defaults.
        mint = self.factory.makeDistribution(name="mint")
        eric = self.factory.makePerson(name="eric")
        mint_choc = self.factory.makeDistributionSourcePackage(
            distribution=mint, sourcepackagename="choc")
        repository = self.factory.makeGitRepository(
            owner=eric, target=mint_choc, name="choc-repo")
        dsp = repository.target
        with admin_logged_in():
            self.repository_set.setDefaultRepositoryForOwner(
                repository.owner, dsp, repository, repository.owner)
            self.repository_set.setDefaultRepository(dsp, repository)
        eric_dsp = getUtility(IPersonDistributionSourcePackageFactory).create(
            eric, dsp)
        self.assertEqual(
            [ICanHasDefaultGitRepository(target)
             for target in (dsp, eric_dsp)],
            repository.getRepositoryDefaults())
        self.assertEqual(
            [("mint/+source/choc", dsp),
             ("~eric/mint/+source/choc", eric_dsp),
             ("~eric/mint/+source/choc/+git/choc-repo", repository)],
            repository.getRepositoryIdentities())

    def test_default_for_oci_project(self):
        # If a repository is the default for an OCI project, then that is
        # the preferred identity.  Target defaults are preferred over
        # owner-target defaults.
        mint = self.factory.makeDistribution(name="mint")
        eric = self.factory.makePerson(name="eric")
        mint_choc = self.factory.makeOCIProject(
            pillar=mint, ociprojectname="choc")
        repository = self.factory.makeGitRepository(
            owner=eric, target=mint_choc, name="choc-repo")
        oci_project = repository.target
        with admin_logged_in():
            self.repository_set.setDefaultRepositoryForOwner(
                repository.owner, oci_project, repository, repository.owner)
            self.repository_set.setDefaultRepository(oci_project, repository)
        eric_oci_project = getUtility(IPersonOCIProjectFactory).create(
            eric, oci_project)
        self.assertEqual(
            [ICanHasDefaultGitRepository(target)
             for target in (oci_project, eric_oci_project)],
            repository.getRepositoryDefaults())
        self.assertEqual(
            [("mint/+oci/choc", oci_project),
             ("~eric/mint/+oci/choc", eric_oci_project),
             ("~eric/mint/+oci/choc/+git/choc-repo", repository)],
            repository.getRepositoryIdentities())


class TestGitRepositoryDeletion(TestCaseWithFactory):
    """Test the different cases that make a repository deletable or not."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestGitRepositoryDeletion, self).setUp()
        self.user = self.factory.makePerson()
        self.project = self.factory.makeProduct(owner=self.user)
        self.repository = self.factory.makeGitRepository(
            name="to-delete", owner=self.user, target=self.project)
        [self.ref] = self.factory.makeGitRefs(repository=self.repository)
        # The owner of the repository is subscribed to the repository when
        # it is created.  The tests here assume no initial connections, so
        # unsubscribe the repository owner here.
        self.repository.unsubscribe(
            self.repository.owner, self.repository.owner)
        # Make sure that the tests all flush the database changes.
        self.addCleanup(Store.of(self.repository).flush)
        login_person(self.user)

    def test_deletable(self):
        # A newly created repository can be deleted without any problems.
        self.assertTrue(
            self.repository.canBeDeleted(),
            "A newly created repository should be able to be deleted.")
        repository_id = self.repository.id
        self.repository.destroySelf()
        self.assertIsNone(
            getUtility(IGitLookup).get(repository_id),
            "The repository has not been deleted.")

    def test_subscription_does_not_disable_deletion(self):
        # A repository that has a subscription can be deleted.
        self.repository.subscribe(
            self.user, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.NOEMAIL, self.user)
        self.assertTrue(self.repository.canBeDeleted())
        repository_id = self.repository.id
        self.repository.destroySelf()
        self.assertIsNone(
            getUtility(IGitLookup).get(repository_id),
            "The repository has not been deleted.")

    def test_private_subscription_does_not_disable_deletion(self):
        # A private repository that has a subscription can be deleted.
        self.repository.transitionToInformationType(
            InformationType.USERDATA, self.repository.owner,
            verify_policy=False)
        self.repository.subscribe(
            self.user, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.NOEMAIL, self.user)
        self.assertTrue(self.repository.canBeDeleted())
        repository_id = self.repository.id
        self.repository.destroySelf()
        self.assertIsNone(
            getUtility(IGitLookup).get(repository_id),
            "The repository has not been deleted.")

    def test_code_import_does_not_disable_deletion(self):
        # A repository that has an attached code import can be deleted.
        self.useFixture(GitHostingFixture())
        code_import = self.factory.makeCodeImport(
            target_rcs_type=TargetRevisionControlSystems.GIT)
        repository = code_import.git_repository
        with celebrity_logged_in('vcs_imports'):
            self.assertTrue(repository.canBeDeleted())

    def test_landing_target_disables_deletion(self):
        # A repository with a landing target cannot be deleted.
        [merge_target] = self.factory.makeGitRefs(
            name="landing-target", owner=self.user, target=self.project)
        self.ref.addLandingTarget(self.user, merge_target)
        self.assertFalse(
            self.repository.canBeDeleted(),
            "A repository with a landing target is not deletable.")
        self.assertRaises(
            CannotDeleteGitRepository, self.repository.destroySelf)

    def test_landing_candidate_disables_deletion(self):
        # A repository with a landing candidate cannot be deleted.
        [merge_source] = self.factory.makeGitRefs(
            name="landing-candidate", owner=self.user, target=self.project)
        merge_source.addLandingTarget(self.user, self.ref)
        self.assertFalse(
            self.repository.canBeDeleted(),
             "A repository with a landing candidate is not deletable.")
        self.assertRaises(
            CannotDeleteGitRepository, self.repository.destroySelf)

    def test_prerequisite_repository_disables_deletion(self):
        # A repository that is a prerequisite repository cannot be deleted.
        [merge_source] = self.factory.makeGitRefs(
            name="landing-candidate", owner=self.user, target=self.project)
        [merge_target] = self.factory.makeGitRefs(
            name="landing-target", owner=self.user, target=self.project)
        merge_source.addLandingTarget(self.user, merge_target, self.ref)
        self.assertFalse(
            self.repository.canBeDeleted(),
            "A repository with a prerequisite target is not deletable.")
        self.assertRaises(
            CannotDeleteGitRepository, self.repository.destroySelf)

    def test_related_GitJobs_deleted(self):
        # A repository with an associated job will delete those jobs.
        with person_logged_in(self.repository.owner):
            GitAPI(None, None).notify(self.repository.getInternalPath(),
                                  {'loose_object_count': 5, 'pack_count': 2},
                                  {'uid': self.repository.owner.id})
        store = Store.of(self.repository)
        self.repository.destroySelf()
        # Need to commit the transaction to fire off the constraint checks.
        transaction.commit()
        jobs = store.find(GitJob, GitJob.job_type == GitJobType.REF_SCAN)
        self.assertEqual([], list(jobs))

    def test_creates_job_to_reclaim_space(self):
        # When a repository is deleted from the database, a job is created
        # to remove the repository from disk as well.
        repository_path = self.repository.getInternalPath()
        store = Store.of(self.repository)
        self.repository.destroySelf()
        jobs = store.find(
            GitJob,
            GitJob.job_type == GitJobType.RECLAIM_REPOSITORY_SPACE)
        self.assertEqual(
            [repository_path],
            [ReclaimGitRepositorySpaceJob(job).repository_path
             for job in jobs])

    def test_destroySelf_with_SourcePackageRecipe(self):
        # If repository is a base_git_repository in a recipe, it is deleted.
        recipe = self.factory.makeSourcePackageRecipe(
            branches=self.factory.makeGitRefs(owner=self.user))
        recipe.base_git_repository.destroySelf(break_references=True)

    def test_destroySelf_with_SourcePackageRecipe_as_non_base(self):
        # If repository is referred to by a recipe, it is deleted.
        [ref1] = self.factory.makeGitRefs(owner=self.user)
        [ref2] = self.factory.makeGitRefs(owner=self.user)
        self.factory.makeSourcePackageRecipe(branches=[ref1, ref2])
        ref2.repository.destroySelf(break_references=True)

    def test_destroySelf_with_inline_comments_draft(self):
        # Draft inline comments related to a deleted repository (source or
        # target MP repository) also get removed.
        merge_proposal = self.factory.makeBranchMergeProposalForGit(
            registrant=self.user, target_ref=self.ref)
        preview_diff = self.factory.makePreviewDiff(
            merge_proposal=merge_proposal)
        transaction.commit()
        merge_proposal.saveDraftInlineComment(
            previewdiff_id=preview_diff.id,
            person=self.user,
            comments={"1": "Should vanish."})
        self.repository.destroySelf(break_references=True)

    def test_destroySelf_with_inline_comments_published(self):
        # Published inline comments related to a deleted repository (source
        # or target MP repository) also get removed.
        merge_proposal = self.factory.makeBranchMergeProposalForGit(
            registrant=self.user, target_ref=self.ref)
        preview_diff = self.factory.makePreviewDiff(
            merge_proposal=merge_proposal)
        transaction.commit()
        merge_proposal.createComment(
            owner=self.user,
            subject="Delete me!",
            previewdiff_id=preview_diff.id,
            inline_comments={"1": "Must disappear."},
        )
        self.repository.destroySelf(break_references=True)

    def test_destroySelf_with_merge_proposal_within_self(self):
        # Deletion works if the repository has a merge proposal from one
        # branch to another within itself.
        [source_ref] = self.factory.makeGitRefs(repository=self.repository)
        [prerequisite_ref] = self.factory.makeGitRefs(
            repository=self.repository)
        self.factory.makeBranchMergeProposalForGit(
            registrant=self.user, target_ref=self.ref,
            prerequisite_ref=prerequisite_ref, source_ref=source_ref)
        self.repository.destroySelf(break_references=True)

    def test_related_webhooks_deleted(self):
        webhook = self.factory.makeWebhook(target=self.repository)
        webhook.ping()
        self.repository.destroySelf()
        transaction.commit()
        self.assertRaises(LostObjectError, getattr, webhook, 'target')

    def test_related_rules_and_grants_deleted(self):
        rule = self.factory.makeGitRule(repository=self.repository)
        grant = self.factory.makeGitRuleGrant(rule=rule)
        store = Store.of(self.repository)
        repository_id = self.repository.id
        activities = store.find(
            GitActivity, GitActivity.repository_id == repository_id)
        self.assertNotEqual([], list(activities))
        self.repository.destroySelf()
        transaction.commit()
        self.assertRaises(LostObjectError, getattr, grant, 'rule')
        self.assertRaises(LostObjectError, getattr, rule, 'repository')
        activities = store.find(
            GitActivity, GitActivity.repository_id == repository_id)
        self.assertEqual([], list(activities))


class TestGitRepositoryDeletionConsequences(TestCaseWithFactory):
    """Test determination and application of repository deletion
    consequences."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestGitRepositoryDeletionConsequences, self).setUp(
            user="test@canonical.com")
        self.repository = self.factory.makeGitRepository()
        [self.ref] = self.factory.makeGitRefs(repository=self.repository)
        # The owner of the repository is subscribed to the repository when
        # it is created.  The tests here assume no initial connections, so
        # unsubscribe the repository owner here.
        self.repository.unsubscribe(
            self.repository.owner, self.repository.owner)

    def test_plain_repository(self):
        # A fresh repository has no deletion requirements.
        self.assertEqual({}, self.repository.getDeletionRequirements())

    def makeMergeProposals(self):
        # Produce a merge proposal for testing purposes.
        [merge_target] = self.factory.makeGitRefs(target=self.ref.target)
        [merge_prerequisite] = self.factory.makeGitRefs(target=self.ref.target)
        # Remove the implicit subscriptions.
        merge_target.repository.unsubscribe(
            merge_target.owner, merge_target.owner)
        merge_prerequisite.repository.unsubscribe(
            merge_prerequisite.owner, merge_prerequisite.owner)
        merge_proposal1 = self.ref.addLandingTarget(
            self.ref.owner, merge_target, merge_prerequisite)
        # Disable this merge proposal, to allow creating a new identical one.
        lp_admins = getUtility(ILaunchpadCelebrities).admin
        merge_proposal1.rejectBranch(lp_admins, "null:")
        merge_proposal2 = self.ref.addLandingTarget(
            self.ref.owner, merge_target, merge_prerequisite)
        return merge_proposal1, merge_proposal2

    def test_repository_with_merge_proposal(self):
        # Ensure that deletion requirements with a merge proposal are right.
        #
        # Each repository related to the merge proposal is tested to ensure
        # it produces a unique, correct result.
        merge_proposal1, merge_proposal2 = self.makeMergeProposals()
        self.assertEqual(
            {
                merge_proposal1:
                ("delete",
                 _("This repository is the source repository of this merge "
                   "proposal.")),
                merge_proposal2:
                ("delete",
                 _("This repository is the source repository of this merge "
                   "proposal.")),
                },
            self.repository.getDeletionRequirements())
        target = merge_proposal1.target_git_repository
        self.assertEqual(
            {
                merge_proposal1:
                ("delete",
                 _("This repository is the target repository of this merge "
                   "proposal.")),
                merge_proposal2:
                ("delete",
                 _("This repository is the target repository of this merge "
                   "proposal.")),
                },
            target.getDeletionRequirements())
        prerequisite = merge_proposal1.prerequisite_git_repository
        self.assertEqual(
            {
                merge_proposal1:
                ("alter",
                 _("This repository is the prerequisite repository of this "
                   "merge proposal.")),
                merge_proposal2:
                ("alter",
                 _("This repository is the prerequisite repository of this "
                   "merge proposal.")),
                },
            prerequisite.getDeletionRequirements())

    def test_delete_merge_proposal_source(self):
        # Merge proposal source repositories can be deleted with
        # break_references.
        merge_proposal1, merge_proposal2 = self.makeMergeProposals()
        merge_proposal1_id = merge_proposal1.id
        BranchMergeProposal.get(merge_proposal1_id)
        self.repository.destroySelf(break_references=True)
        self.assertRaises(
            SQLObjectNotFound, BranchMergeProposal.get, merge_proposal1_id)

    def test_delete_merge_proposal_target(self):
        # Merge proposal target repositories can be deleted with
        # break_references.
        merge_proposal1, merge_proposal2 = self.makeMergeProposals()
        merge_proposal1_id = merge_proposal1.id
        BranchMergeProposal.get(merge_proposal1_id)
        merge_proposal1.target_git_repository.destroySelf(
            break_references=True)
        self.assertRaises(SQLObjectNotFound,
            BranchMergeProposal.get, merge_proposal1_id)

    def test_delete_merge_proposal_prerequisite(self):
        # Merge proposal prerequisite repositories can be deleted with
        # break_references.
        merge_proposal1, merge_proposal2 = self.makeMergeProposals()
        merge_proposal1.prerequisite_git_repository.destroySelf(
            break_references=True)
        self.assertIsNone(merge_proposal1.prerequisite_git_repository)

    def test_delete_source_CodeReviewComment(self):
        # Deletion of source repositories that have CodeReviewComments works.
        comment = self.factory.makeCodeReviewComment(git=True)
        comment_id = comment.id
        repository = comment.branch_merge_proposal.source_git_repository
        repository.destroySelf(break_references=True)
        self.assertIsNone(
            IStore(CodeReviewComment).get(CodeReviewComment, comment_id))

    def test_delete_target_CodeReviewComment(self):
        # Deletion of target repositories that have CodeReviewComments works.
        comment = self.factory.makeCodeReviewComment(git=True)
        comment_id = comment.id
        repository = comment.branch_merge_proposal.target_git_repository
        repository.destroySelf(break_references=True)
        self.assertIsNone(
            IStore(CodeReviewComment).get(CodeReviewComment, comment_id))

    def test_sourceBranchWithCodeReviewVoteReference(self):
        # break_references handles CodeReviewVoteReference source repository.
        merge_proposal = self.factory.makeBranchMergeProposalForGit()
        merge_proposal.nominateReviewer(
            self.factory.makePerson(), self.factory.makePerson())
        merge_proposal.source_git_repository.destroySelf(break_references=True)

    def test_targetBranchWithCodeReviewVoteReference(self):
        # break_references handles CodeReviewVoteReference target repository.
        merge_proposal = self.factory.makeBranchMergeProposalForGit()
        merge_proposal.nominateReviewer(
            self.factory.makePerson(), self.factory.makePerson())
        merge_proposal.target_git_repository.destroySelf(break_references=True)

    def test_code_import_requirements(self):
        # Code imports are not included explicitly in deletion requirements.
        self.useFixture(GitHostingFixture())
        code_import = self.factory.makeCodeImport(
            target_rcs_type=TargetRevisionControlSystems.GIT)
        # Remove the implicit repository subscription first.
        code_import.git_repository.unsubscribe(
            code_import.git_repository.owner, code_import.git_repository.owner)
        self.assertEqual(
            {}, code_import.git_repository.getDeletionRequirements())

    def test_code_import_deletion(self):
        # break_references allows deleting a code import repository.
        self.useFixture(GitHostingFixture())
        code_import = self.factory.makeCodeImport(
            target_rcs_type=TargetRevisionControlSystems.GIT)
        code_import_id = code_import.id
        code_import.git_repository.destroySelf(break_references=True)
        self.assertRaises(
            NotFoundError, getUtility(ICodeImportSet).get, code_import_id)

    def test_snap_requirements(self):
        # If a repository is used by a snap package, the deletion
        # requirements indicate this.
        [ref] = self.factory.makeGitRefs()
        self.factory.makeSnap(git_ref=ref)
        self.assertEqual(
            {None:
             ("alter", _("Some snap packages build from this repository."))},
            ref.repository.getDeletionRequirements())

    def test_snap_deletion(self):
        # break_references allows deleting a repository used by a snap package.
        repository = self.factory.makeGitRepository()
        [ref1, ref2] = self.factory.makeGitRefs(
            repository=repository, paths=["refs/heads/1", "refs/heads/2"])
        snap1 = self.factory.makeSnap(git_ref=ref1)
        snap2 = self.factory.makeSnap(git_ref=ref2)
        repository.destroySelf(break_references=True)
        transaction.commit()
        self.assertIsNone(snap1.git_repository)
        self.assertIsNone(snap1.git_path)
        self.assertIsNone(snap2.git_repository)
        self.assertIsNone(snap2.git_path)

    def test_charm_recipe_requirements(self):
        # If a repository is used by a charm recipe, the deletion
        # requirements indicate this.
        self.useFixture(FeatureFixture({CHARM_RECIPE_ALLOW_CREATE: "on"}))
        [ref] = self.factory.makeGitRefs()
        self.factory.makeCharmRecipe(git_ref=ref)
        self.assertEqual(
            {None:
             ("alter", _("Some charm recipes build from this repository."))},
            ref.repository.getDeletionRequirements())

    def test_charm_recipe_deletion(self):
        # break_references allows deleting a repository used by a charm
        # recipe.
        self.useFixture(FeatureFixture({CHARM_RECIPE_ALLOW_CREATE: "on"}))
        repository = self.factory.makeGitRepository()
        [ref1, ref2] = self.factory.makeGitRefs(
            repository=repository, paths=["refs/heads/1", "refs/heads/2"])
        recipe1 = self.factory.makeCharmRecipe(git_ref=ref1)
        recipe2 = self.factory.makeCharmRecipe(git_ref=ref2)
        repository.destroySelf(break_references=True)
        transaction.commit()
        self.assertIsNone(recipe1.git_repository)
        self.assertIsNone(recipe1.git_path)
        self.assertIsNone(recipe2.git_repository)
        self.assertIsNone(recipe2.git_path)

    def test_ClearPrerequisiteRepository(self):
        # ClearPrerequisiteRepository.__call__ must clear the prerequisite
        # repository.
        merge_proposal = removeSecurityProxy(self.makeMergeProposals()[0])
        with person_logged_in(
                merge_proposal.prerequisite_git_repository.owner):
            ClearPrerequisiteRepository(merge_proposal)()
        self.assertIsNone(merge_proposal.prerequisite_git_repository)

    def test_DeletionOperation(self):
        # DeletionOperation.__call__ is not implemented.
        self.assertRaises(NotImplementedError, DeletionOperation("a", "b"))

    def test_DeletionCallable(self):
        # DeletionCallable must invoke the callable.
        merge_proposal = self.factory.makeBranchMergeProposalForGit()
        merge_proposal_id = merge_proposal.id
        DeletionCallable(
            merge_proposal, "blah", merge_proposal.deleteProposal)()
        self.assertRaises(
            SQLObjectNotFound, BranchMergeProposal.get, merge_proposal_id)

    def test_DeleteCodeImport(self):
        # DeleteCodeImport.__call__ must delete the CodeImport.
        self.useFixture(GitHostingFixture())
        code_import = self.factory.makeCodeImport(
            target_rcs_type=TargetRevisionControlSystems.GIT)
        code_import_id = code_import.id
        DeleteCodeImport(code_import)()
        self.assertRaises(
            NotFoundError, getUtility(ICodeImportSet).get, code_import_id)

    def test_deletionRequirements_with_SourcePackageRecipe(self):
        # Recipes are listed as deletion requirements.
        recipe = self.factory.makeSourcePackageRecipe(
            branches=self.factory.makeGitRefs())
        self.assertEqual(
            {recipe: ("delete", "This recipe uses this repository.")},
            recipe.base_git_repository.getDeletionRequirements())


class TestGitRepositoryModifications(TestCaseWithFactory):
    """Tests for Git repository modifications."""

    layer = DatabaseFunctionalLayer

    def test_date_last_modified_initial_value(self):
        # The initial value of date_last_modified is date_created.
        repository = self.factory.makeGitRepository()
        self.assertEqual(
            repository.date_created, repository.date_last_modified)

    def test_modifiedevent_sets_date_last_modified(self):
        # When a GitRepository receives an object modified event, the last
        # modified date is set to UTC_NOW.
        repository = self.factory.makeGitRepository(
            date_created=datetime(2015, 2, 4, 17, 42, 0, tzinfo=pytz.UTC))
        with notify_modified(
                removeSecurityProxy(repository), ["name"],
                user=repository.owner):
            pass
        self.assertSqlAttributeEqualsDate(
            repository, "date_last_modified", UTC_NOW)

    def test_create_ref_sets_date_last_modified(self):
        repository = self.factory.makeGitRepository(
            date_created=datetime(2015, 6, 1, tzinfo=pytz.UTC))
        [ref] = self.factory.makeGitRefs(repository=repository)
        new_refs_info = {
            ref.path: {
                "sha1": "0000000000000000000000000000000000000000",
                "type": ref.object_type,
                },
            }
        repository.createOrUpdateRefs(new_refs_info)
        self.assertSqlAttributeEqualsDate(
            repository, "date_last_modified", UTC_NOW)

    def test_update_ref_sets_date_last_modified(self):
        repository = self.factory.makeGitRepository(
            date_created=datetime(2015, 6, 1, tzinfo=pytz.UTC))
        [ref] = self.factory.makeGitRefs(repository=repository)
        new_refs_info = {
            "refs/heads/new": {
                "sha1": ref.commit_sha1,
                "type": ref.object_type,
                },
            }
        repository.createOrUpdateRefs(new_refs_info)
        self.assertSqlAttributeEqualsDate(
            repository, "date_last_modified", UTC_NOW)

    def test_remove_ref_sets_date_last_modified(self):
        repository = self.factory.makeGitRepository(
            date_created=datetime(2015, 6, 1, tzinfo=pytz.UTC))
        [ref] = self.factory.makeGitRefs(repository=repository)
        repository.removeRefs(set([ref.path]))
        self.assertSqlAttributeEqualsDate(
            repository, "date_last_modified", UTC_NOW)


class TestGitRepositoryModificationNotifications(TestCaseWithFactory):
    """Tests for Git repository modification notifications."""

    layer = ZopelessDatabaseLayer

    def test_sends_notifications(self):
        # Attribute modifications send mail to subscribers.
        self.assertEqual(0, len(stub.test_emails))
        repository = self.factory.makeGitRepository(name="foo")
        subscriber = self.factory.makePerson()
        owner_address = (
            removeSecurityProxy(repository.owner.preferredemail).email)
        subscriber_address = (
            removeSecurityProxy(subscriber.preferredemail).email)
        transaction.commit()
        with person_logged_in(repository.owner):
            with notify_modified(repository, ["name"], user=repository.owner):
                repository.subscribe(
                    repository.owner,
                    BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
                    BranchSubscriptionDiffSize.NODIFF,
                    CodeReviewNotificationLevel.NOEMAIL,
                    repository.owner)
                repository.subscribe(
                    subscriber,
                    BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
                    BranchSubscriptionDiffSize.NODIFF,
                    CodeReviewNotificationLevel.NOEMAIL,
                    repository.owner)
                repository.setName("bar", repository.owner)
                repository.addRule("refs/heads/stable/*", repository.owner)
        with dbuser(config.IGitRepositoryModifiedMailJobSource.dbuser):
            JobRunner.fromReady(
                getUtility(IGitRepositoryModifiedMailJobSource)).runAll()
        bodies_by_recipient = {}
        for from_addr, to_addrs, message in stub.test_emails:
            body = message_from_bytes(message).get_payload(decode=True)
            for to_addr in to_addrs:
                bodies_by_recipient[to_addr] = six.ensure_text(body)
        # Both the owner and the unprivileged subscriber receive email.
        self.assertContentEqual(
            [owner_address, subscriber_address], bodies_by_recipient.keys())
        # The owner receives a message including details of permission
        # changes.
        self.assertEqual(
            "    Name: foo => bar\n"
            "    Git identity: lp:~{person}/{project}/+git/foo => "
            "lp:~{person}/{project}/+git/bar\n"
            "    Added protected ref: refs/heads/stable/*".format(
                person=repository.owner.name, project=repository.target.name),
            bodies_by_recipient[owner_address].split("\n\n--\n")[0])
        # The unprivileged subscriber receives a message omitting details of
        # permission changes.
        self.assertEqual(
            "    Name: foo => bar\n"
            "    Git identity: lp:~{person}/{project}/+git/foo => "
            "lp:~{person}/{project}/+git/bar".format(
                person=repository.owner.name, project=repository.target.name),
            bodies_by_recipient[subscriber_address].split("\n\n--\n")[0])

    # XXX cjwatson 2015-02-04: This will need to be expanded once Launchpad
    # actually notices any interesting kind of repository modifications.


class TestGitRepositoryURLs(TestCaseWithFactory):
    """Tests for Git repository URLs."""

    layer = DatabaseFunctionalLayer

    def test_codebrowse_url(self):
        # The basic codebrowse URL for a repository is an 'https' URL.
        repository = self.factory.makeGitRepository()
        expected_url = urlutils.join(
            config.codehosting.git_browse_root, repository.shortened_path)
        self.assertEqual(expected_url, repository.getCodebrowseUrl())

    def test_codebrowser_url_with_username_and_password(self):
        self.pushConfig(
            "codehosting", git_browse_root="http://git.launchpad.test:99")
        repository = self.factory.makeGitRepository()
        expected_url = lambda usr, passw: urlutils.join(
            "http://%s:%s@git.launchpad.test:99" % (usr, passw),
            repository.shortened_path)
        self.assertEqual(
            expected_url("foo", "bar"),
            repository.getCodebrowseUrl("foo", "bar"))
        self.assertEqual(
            expected_url("", "bar"),
            repository.getCodebrowseUrl(None, "bar"))
        self.assertEqual(
            expected_url("foo", ""),
            repository.getCodebrowseUrl("foo", ""))

    def test_codebrowse_url_for_default(self):
        # The codebrowse URL for the default repository for a target is an
        # 'https' URL based on the repository's shortened path.
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repository.target, repository)
        expected_url = urlutils.join(
            config.codehosting.git_browse_root, repository.shortened_path)
        self.assertEqual(expected_url, repository.getCodebrowseUrl())

    def test_git_https_url_for_public(self):
        # Public repositories have an anonymous URL, visible to anyone.
        repository = self.factory.makeGitRepository()
        expected_url = urlutils.join(
            config.codehosting.git_browse_root, repository.shortened_path)
        self.assertEqual(expected_url, repository.git_https_url)

    def test_anon_url_not_for_private(self):
        # Private repositories do not have an anonymous URL.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            self.assertIsNone(repository.git_https_url)

    def test_git_ssh_url_for_public(self):
        # Public repositories have an SSH URL.
        repository = self.factory.makeGitRepository()
        expected_url = urlutils.join(
            config.codehosting.git_ssh_root, repository.shortened_path)
        self.assertEqual(expected_url, repository.git_ssh_url)

    def test_ssh_url_for_private(self):
        # Private repositories have an SSH URL.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            expected_url = urlutils.join(
                config.codehosting.git_ssh_root, repository.shortened_path)
            self.assertEqual(expected_url, repository.git_ssh_url)

    def test_getCodebrowseUrlForRevision(self):
        # IGitRepository.getCodebrowseUrlForRevision gives the URL to the
        # browser for a specific commit of the code
        repository = self.factory.makeGitRepository()
        commit = '0' * 40
        urlByCommit = repository.getCodebrowseUrlForRevision(commit)
        url = repository.getCodebrowseUrl()
        self.assertEqual(urlByCommit, "%s/commit/?id=%s" % (url, commit))


class TestGitRepositoryNamespace(TestCaseWithFactory):
    """Test `IGitRepository.namespace`."""

    layer = DatabaseFunctionalLayer

    def test_namespace_personal(self):
        # The namespace attribute of a personal repository points to the
        # namespace that corresponds to ~owner.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        namespace = getUtility(IGitNamespaceSet).get(person=owner)
        self.assertEqual(namespace, repository.namespace)

    def test_namespace_project(self):
        # The namespace attribute of a project repository points to the
        # namespace that corresponds to ~owner/project.
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(target=project)
        namespace = getUtility(IGitNamespaceSet).get(
            person=repository.owner, project=project)
        self.assertEqual(namespace, repository.namespace)

    def test_namespace_package(self):
        # The namespace attribute of a package repository points to the
        # namespace that corresponds to
        # ~owner/distribution/+source/sourcepackagename.
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        namespace = getUtility(IGitNamespaceSet).get(
            person=repository.owner, distribution=dsp.distribution,
            sourcepackagename=dsp.sourcepackagename)
        self.assertEqual(namespace, repository.namespace)

    def test_namespace_oci_project(self):
        # The namespace attribute of an OCI project repository points to the
        # namespace that corresponds to
        # ~owner/distribution/+oci/ociprojectname.
        oci_project = self.factory.makeOCIProject()
        repository = self.factory.makeGitRepository(target=oci_project)
        namespace = getUtility(IGitNamespaceSet).get(
            person=repository.owner, oci_project=oci_project)
        self.assertEqual(namespace, repository.namespace)


class TestGitRepositoryPendingUpdates(TestCaseWithFactory):
    """Are there changes to this repository not reflected in the database?"""

    layer = LaunchpadFunctionalLayer

    def test_new_repository_no_updates(self):
        # New repositories have no pending updates.
        repository = self.factory.makeGitRepository()
        self.assertFalse(repository.pending_updates)

    def test_notify(self):
        # If the hosting service has just sent us a change notification,
        # then there are pending updates, but running the ref-scanning job
        # clears that flag.
        git_api = GitAPI(None, None)
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.owner):
            self.assertIsNone(git_api.notify(
                repository.getInternalPath(),
                {'loose_object_count': 5, 'pack_count': 2},
                {'uid': repository.owner.id}))
        self.assertTrue(repository.pending_updates)
        [job] = list(getUtility(IGitRefScanJobSource).iterReady())
        with dbuser("branchscanner"):
            JobRunner([job]).runAll()
        self.assertFalse(repository.pending_updates)


class TestGitRepositoryPrivacy(TestCaseWithFactory):
    """Tests for Git repository privacy."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use an admin user as we aren't checking edit permissions here.
        super(TestGitRepositoryPrivacy, self).setUp("admin@canonical.com")

    def test_personal_repositories_for_private_teams_are_private(self):
        team = self.factory.makeTeam(
            membership_policy=TeamMembershipPolicy.MODERATED,
            visibility=PersonVisibility.PRIVATE)
        repository = self.factory.makeGitRepository(owner=team, target=team)
        self.assertTrue(repository.private)
        self.assertEqual(
            InformationType.PROPRIETARY, repository.information_type)

    def test__reconcileAccess_for_project_repository(self):
        # _reconcileAccess uses a project policy for a project repository.
        repository = self.factory.makeGitRepository(
            information_type=InformationType.USERDATA)
        [artifact] = getUtility(IAccessArtifactSource).ensure([repository])
        getUtility(IAccessPolicyArtifactSource).deleteByArtifact([artifact])
        removeSecurityProxy(repository)._reconcileAccess()
        self.assertContentEqual(
            getUtility(IAccessPolicySource).find(
                [(repository.target, InformationType.USERDATA)]),
            get_policies_for_artifact(repository))

    def test__reconcileAccess_for_package_repository(self):
        # Git repository privacy isn't yet supported for distributions, so
        # no AccessPolicyArtifact is created for a package repository.
        repository = self.factory.makeGitRepository(
            target=self.factory.makeDistributionSourcePackage(),
            information_type=InformationType.USERDATA)
        removeSecurityProxy(repository)._reconcileAccess()
        self.assertEqual([], get_policies_for_artifact(repository))

    def test__reconcileAccess_for_oci_project_repository(self):
        # Git repository privacy isn't yet supported for OCI projects, so no
        # AccessPolicyArtifact is created for an OCI project repository.
        repository = self.factory.makeGitRepository(
            target=self.factory.makeOCIProject(),
            information_type=InformationType.USERDATA)
        removeSecurityProxy(repository)._reconcileAccess()
        self.assertEqual([], get_policies_for_artifact(repository))

    def test__reconcileAccess_for_personal_repository(self):
        # _reconcileAccess uses a person policy for a personal repository.
        team_owner = self.factory.makeTeam()
        repository = self.factory.makeGitRepository(
            owner=team_owner, target=team_owner,
            information_type=InformationType.USERDATA)
        removeSecurityProxy(repository)._reconcileAccess()
        self.assertContentEqual(
            getUtility(IAccessPolicySource).findByTeam([team_owner]),
            get_policies_for_artifact(repository))


class TestGitRepositoryRefs(TestCaseWithFactory):
    """Tests for ref handling."""

    layer = DatabaseFunctionalLayer

    def test__convertRefInfo(self):
        # _convertRefInfo converts a valid info dictionary.
        sha1 = six.ensure_text(hashlib.sha1(b"").hexdigest())
        info = {"object": {"sha1": sha1, "type": "commit"}}
        expected_info = {"sha1": sha1, "type": GitObjectType.COMMIT}
        self.assertEqual(expected_info, GitRepository._convertRefInfo(info))

    def test__convertRefInfo_requires_object(self):
        self.assertRaisesWithContent(
            ValueError, 'ref info does not contain "object" key',
            GitRepository._convertRefInfo, {})

    def test__convertRefInfo_requires_object_sha1(self):
        self.assertRaisesWithContent(
            ValueError, 'ref info object does not contain "sha1" key',
            GitRepository._convertRefInfo, {"object": {}})

    def test__convertRefInfo_requires_object_type(self):
        info = {
            "object": {"sha1": "0000000000000000000000000000000000000000"},
            }
        self.assertRaisesWithContent(
            ValueError, 'ref info object does not contain "type" key',
            GitRepository._convertRefInfo, info)

    def test__convertRefInfo_bad_sha1(self):
        info = {"object": {"sha1": "x", "type": "commit"}}
        self.assertRaisesWithContent(
            ValueError, 'ref info sha1 is not a 40-character string',
            GitRepository._convertRefInfo, info)

    def test__convertRefInfo_bad_type(self):
        info = {
            "object": {
                "sha1": "0000000000000000000000000000000000000000",
                "type": "nonsense",
                },
            }
        self.assertRaisesWithContent(
            ValueError, 'ref info type is not a recognised object type',
            GitRepository._convertRefInfo, info)

    def assertRefsMatch(self, refs, repository, paths):
        matchers = [
            MatchesStructure.byEquality(
                repository=repository,
                path=path,
                commit_sha1=six.ensure_text(hashlib.sha1(
                    path.encode("UTF-8")).hexdigest()),
                object_type=GitObjectType.COMMIT)
            for path in paths]
        self.assertThat(refs, MatchesSetwise(*matchers))

    def test_create(self):
        repository = self.factory.makeGitRepository()
        self.assertEqual([], list(repository.refs))
        paths = ("refs/heads/master", "refs/tags/1.0")
        self.factory.makeGitRefs(repository=repository, paths=paths)
        self.assertRefsMatch(repository.refs, repository, paths)
        master_ref = repository.getRefByPath("refs/heads/master")
        new_refs_info = {
            "refs/tags/1.1": {
                "sha1": master_ref.commit_sha1,
                "type": master_ref.object_type,
                },
            }
        repository.createOrUpdateRefs(new_refs_info)
        self.assertRefsMatch(
            [ref for ref in repository.refs if ref.path != "refs/tags/1.1"],
            repository, paths)
        self.assertThat(
            repository.getRefByPath("refs/tags/1.1"),
            MatchesStructure.byEquality(
                repository=repository,
                path="refs/tags/1.1",
                commit_sha1=master_ref.commit_sha1,
                object_type=master_ref.object_type,
                ))

    def test_remove(self):
        repository = self.factory.makeGitRepository()
        paths = ("refs/heads/master", "refs/heads/branch", "refs/tags/1.0")
        self.factory.makeGitRefs(repository=repository, paths=paths)
        self.assertRefsMatch(repository.refs, repository, paths)
        repository.removeRefs(["refs/heads/branch", "refs/tags/1.0"])
        self.assertRefsMatch(
            repository.refs, repository, ["refs/heads/master"])

    def test_update(self):
        repository = self.factory.makeGitRepository()
        paths = ("refs/heads/master", "refs/tags/1.0")
        self.factory.makeGitRefs(repository=repository, paths=paths)
        self.assertRefsMatch(repository.refs, repository, paths)
        new_info = {
            "sha1": "0000000000000000000000000000000000000000",
            "type": GitObjectType.BLOB,
            }
        repository.createOrUpdateRefs({"refs/tags/1.0": new_info})
        self.assertRefsMatch(
            [ref for ref in repository.refs if ref.path != "refs/tags/1.0"],
            repository, ["refs/heads/master"])
        self.assertThat(
            repository.getRefByPath("refs/tags/1.0"),
            MatchesStructure.byEquality(
                repository=repository,
                path="refs/tags/1.0",
                commit_sha1="0000000000000000000000000000000000000000",
                object_type=GitObjectType.BLOB,
                ))

    def _getWaitingUpdatePreviewDiffJobs(self, repository):
        jobs = Store.of(repository).find(
            BranchMergeProposalJob,
            BranchMergeProposalJob.job_type ==
                BranchMergeProposalJobType.UPDATE_PREVIEW_DIFF,
            BranchMergeProposalJob.job == Job.id,
            Job._status == JobStatus.WAITING)
        return [UpdatePreviewDiffJob(job) for job in jobs]

    def test_update_schedules_diff_update(self):
        repository = self.factory.makeGitRepository()
        [ref] = self.factory.makeGitRefs(repository=repository)
        self.assertRefsMatch(repository.refs, repository, [ref.path])
        bmp = self.factory.makeBranchMergeProposalForGit(source_ref=ref)
        jobs = self._getWaitingUpdatePreviewDiffJobs(repository)
        self.assertEqual([bmp], [job.branch_merge_proposal for job in jobs])
        new_info = {
            "sha1": "0000000000000000000000000000000000000000",
            "type": GitObjectType.BLOB,
            }
        repository.createOrUpdateRefs({ref.path: new_info})
        jobs = self._getWaitingUpdatePreviewDiffJobs(repository)
        self.assertEqual(
            [bmp, bmp], [job.branch_merge_proposal for job in jobs])
        self.assertEqual(
            "0000000000000000000000000000000000000000",
            bmp.source_git_commit_sha1)

    def test_getRefByPath_without_leading_refs_heads(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/master"])
        self.assertEqual(
            ref, ref.repository.getRefByPath("refs/heads/master"))
        self.assertEqual(ref, ref.repository.getRefByPath("master"))
        self.assertIsNone(ref.repository.getRefByPath("other"))

    def test_getRefByPath_HEAD(self):
        # The special ref path "HEAD" always refers to the current default
        # branch.
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/master"])
        ref_HEAD = ref.repository.getRefByPath("HEAD")
        self.assertEqual(ref.repository, ref_HEAD.repository)
        self.assertEqual("HEAD", ref_HEAD.path)
        self.assertRaises(NotFoundError, getattr, ref_HEAD, "commit_sha1")
        removeSecurityProxy(ref.repository)._default_branch = (
            "refs/heads/missing")
        self.assertRaises(NotFoundError, getattr, ref_HEAD, "commit_sha1")
        removeSecurityProxy(ref.repository)._default_branch = ref.path
        self.assertEqual(ref.commit_sha1, ref_HEAD.commit_sha1)

    def test_planRefChanges(self):
        # planRefChanges copes with planning changes to refs in a repository
        # where some refs have been created, some deleted, and some changed.
        repository = self.factory.makeGitRepository()
        paths = ("refs/heads/master", "refs/heads/foo", "refs/heads/bar")
        self.factory.makeGitRefs(repository=repository, paths=paths)
        self.assertRefsMatch(repository.refs, repository, paths)
        master_sha1 = repository.getRefByPath("refs/heads/master").commit_sha1
        foo_sha1 = repository.getRefByPath("refs/heads/foo").commit_sha1
        self.useFixture(GitHostingFixture(refs={
            "refs/heads/master": {
                "object": {
                    "sha1": "1111111111111111111111111111111111111111",
                    "type": "commit",
                    },
                },
            "refs/heads/foo": {
                "object": {
                    "sha1": foo_sha1,
                    "type": "commit",
                    },
                },
            "refs/tags/1.0": {
                "object": {
                    "sha1": master_sha1,
                    "type": "commit",
                    },
                },
            }))
        refs_to_upsert, refs_to_remove = repository.planRefChanges("dummy")

        expected_upsert = {
            "refs/heads/master": {
                "sha1": "1111111111111111111111111111111111111111",
                "type": GitObjectType.COMMIT,
                },
            "refs/heads/foo": {
                "sha1": six.ensure_text(
                    hashlib.sha1(b"refs/heads/foo").hexdigest()),
                "type": GitObjectType.COMMIT,
                },
            "refs/tags/1.0": {
                "sha1": six.ensure_text(
                    hashlib.sha1(b"refs/heads/master").hexdigest()),
                "type": GitObjectType.COMMIT,
                },
            }
        self.assertEqual(expected_upsert, refs_to_upsert)
        self.assertEqual(set(["refs/heads/bar"]), refs_to_remove)

    def test_planRefChanges_skips_non_commits(self):
        # planRefChanges does not attempt to update refs that point to
        # non-commits.
        repository = self.factory.makeGitRepository()
        blob_sha1 = six.ensure_text(
            hashlib.sha1(b"refs/heads/blob").hexdigest())
        refs_info = {
            "refs/heads/blob": {
                "sha1": blob_sha1,
                "type": GitObjectType.BLOB,
                },
            }
        repository.createOrUpdateRefs(refs_info)
        self.useFixture(GitHostingFixture(refs={
            "refs/heads/blob": {
                "object": {
                    "sha1": blob_sha1,
                    "type": "blob",
                    },
                },
            }))
        self.assertEqual(({}, set()), repository.planRefChanges("dummy"))

    def test_planRefChanges_includes_unfetched_commits(self):
        # planRefChanges plans updates to refs pointing to commits for which
        # we haven't yet fetched detailed metadata.
        repository = self.factory.makeGitRepository()
        paths = ("refs/heads/master", "refs/heads/foo")
        self.factory.makeGitRefs(repository=repository, paths=paths)
        author_addr = (
            removeSecurityProxy(repository.owner).preferredemail.email)
        [author] = getUtility(IRevisionSet).acquireRevisionAuthors(
            [author_addr]).values()
        naked_master = removeSecurityProxy(
            repository.getRefByPath("refs/heads/master"))
        naked_master.author_id = naked_master.committer_id = author.id
        naked_master.author_date = naked_master.committer_date = (
            datetime.now(pytz.UTC))
        naked_master.commit_message = "message"
        self.useFixture(GitHostingFixture(refs={
            path: {
                "object": {
                    "sha1": repository.getRefByPath(path).commit_sha1,
                    "type": "commit",
                    },
                }
            for path in paths}))
        refs_to_upsert, refs_to_remove = repository.planRefChanges("dummy")

        expected_upsert = {
            "refs/heads/foo": {
                "sha1": repository.getRefByPath("refs/heads/foo").commit_sha1,
                "type": GitObjectType.COMMIT,
                },
            }
        self.assertEqual(expected_upsert, refs_to_upsert)
        self.assertEqual(set(), refs_to_remove)

    def test_planRefChanges_excludes_configured_prefixes(self):
        # planRefChanges excludes some ref prefixes by default, and can be
        # configured otherwise.
        repository = self.factory.makeGitRepository()
        hosting_fixture = self.useFixture(GitHostingFixture())
        repository.planRefChanges("dummy")
        self.assertEqual(
            [{"exclude_prefixes": ["refs/changes/"]}],
            hosting_fixture.getRefs.extract_kwargs())
        hosting_fixture.getRefs.calls = []
        self.pushConfig(
            "codehosting", git_exclude_ref_prefixes="refs/changes/ refs/pull/")
        repository.planRefChanges("dummy")
        self.assertEqual(
            [{"exclude_prefixes": ["refs/changes/", "refs/pull/"]}],
            hosting_fixture.getRefs.extract_kwargs())

    def test_fetchRefCommits(self):
        # fetchRefCommits fetches detailed tip commit metadata for the
        # requested refs.
        master_sha1 = six.ensure_text(
            hashlib.sha1(b"refs/heads/master").hexdigest())
        foo_sha1 = six.ensure_text(hashlib.sha1(b"refs/heads/foo").hexdigest())
        author = self.factory.makePerson()
        with person_logged_in(author):
            author_email = author.preferredemail.email
        author_date = datetime(2015, 1, 1, tzinfo=pytz.UTC)
        committer_date = datetime(2015, 1, 2, tzinfo=pytz.UTC)
        hosting_fixture = self.useFixture(GitHostingFixture(commits=[
            {
                "sha1": master_sha1,
                "message": "tip of master",
                "author": {
                    "name": author.displayname,
                    "email": author_email,
                    "time": int(seconds_since_epoch(author_date)),
                    },
                "committer": {
                    "name": "New Person",
                    "email": "new-person@example.org",
                    "time": int(seconds_since_epoch(committer_date)),
                    },
                "parents": [],
                "tree": six.ensure_text(hashlib.sha1(b"").hexdigest()),
                }]))
        refs = {
            "refs/heads/master": {
                "sha1": master_sha1,
                "type": GitObjectType.COMMIT,
                },
            "refs/heads/foo": {
                "sha1": foo_sha1,
                "type": GitObjectType.COMMIT,
                },
            }
        GitRepository.fetchRefCommits("dummy", refs)

        expected_oids = [master_sha1, foo_sha1]
        [(_, observed_oids)] = hosting_fixture.getCommits.extract_args()
        self.assertContentEqual(expected_oids, observed_oids)
        expected_author_addr = "%s <%s>" % (author.displayname, author_email)
        [expected_author] = getUtility(IRevisionSet).acquireRevisionAuthors(
            [expected_author_addr]).values()
        expected_committer_addr = "New Person <new-person@example.org>"
        [expected_committer] = getUtility(IRevisionSet).acquireRevisionAuthors(
            [expected_committer_addr]).values()
        expected_refs = {
            "refs/heads/master": {
                "sha1": master_sha1,
                "type": GitObjectType.COMMIT,
                "author": expected_author,
                "author_addr": expected_author_addr,
                "author_date": author_date,
                "committer": expected_committer,
                "committer_addr": expected_committer_addr,
                "committer_date": committer_date,
                "commit_message": "tip of master",
                },
            "refs/heads/foo": {
                "sha1": foo_sha1,
                "type": GitObjectType.COMMIT,
                },
            }
        self.assertEqual(expected_refs, refs)

    def test_fetchRefCommits_empty(self):
        # If given an empty refs dictionary, fetchRefCommits returns early
        # without contacting the hosting service.
        hosting_fixture = self.useFixture(GitHostingFixture())
        GitRepository.fetchRefCommits("dummy", {})
        self.assertEqual([], hosting_fixture.getCommits.calls)

    def test_synchroniseRefs(self):
        # synchroniseRefs copes with synchronising a repository where some
        # refs have been created, some deleted, and some changed.
        repository = self.factory.makeGitRepository()
        paths = ("refs/heads/master", "refs/heads/foo", "refs/heads/bar")
        self.factory.makeGitRefs(repository=repository, paths=paths)
        self.assertRefsMatch(repository.refs, repository, paths)
        refs_to_upsert = {
            "refs/heads/master": {
                "sha1": "1111111111111111111111111111111111111111",
                "type": GitObjectType.COMMIT,
                },
            "refs/heads/foo": {
                "sha1": repository.getRefByPath("refs/heads/foo").commit_sha1,
                "type": GitObjectType.COMMIT,
                },
            "refs/tags/1.0": {
                "sha1": repository.getRefByPath(
                    "refs/heads/master").commit_sha1,
                "type": GitObjectType.COMMIT,
                },
            }
        refs_to_remove = set(["refs/heads/bar"])
        repository.synchroniseRefs(refs_to_upsert, refs_to_remove)
        expected_sha1s = [
            ("refs/heads/master", "1111111111111111111111111111111111111111"),
            ("refs/heads/foo",
             six.ensure_text(hashlib.sha1(b"refs/heads/foo").hexdigest())),
            ("refs/tags/1.0",
             six.ensure_text(hashlib.sha1(b"refs/heads/master").hexdigest())),
            ]
        matchers = [
            MatchesStructure.byEquality(
                repository=repository,
                path=path,
                commit_sha1=sha1,
                object_type=GitObjectType.COMMIT,
                ) for path, sha1 in expected_sha1s]
        self.assertThat(repository.refs, MatchesSetwise(*matchers))

    def test_set_default_branch(self):
        hosting_fixture = self.useFixture(GitHostingFixture())
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRefs(
            repository=repository,
            paths=("refs/heads/master", "refs/heads/new"))
        removeSecurityProxy(repository)._default_branch = "refs/heads/master"
        with person_logged_in(repository.owner):
            repository.default_branch = "new"
        self.assertEqual(
            [((repository.getInternalPath(),),
             {"default_branch": "refs/heads/new"})],
            hosting_fixture.setProperties.calls)
        self.assertEqual("refs/heads/new", repository.default_branch)

    def test_set_default_branch_unchanged(self):
        hosting_fixture = self.useFixture(GitHostingFixture())
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRefs(
            repository=repository, paths=["refs/heads/master"])
        removeSecurityProxy(repository)._default_branch = "refs/heads/master"
        with person_logged_in(repository.owner):
            repository.default_branch = "master"
        self.assertEqual([], hosting_fixture.setProperties.calls)
        self.assertEqual("refs/heads/master", repository.default_branch)

    def test_set_default_branch_imported(self):
        hosting_fixture = self.useFixture(GitHostingFixture())
        repository = self.factory.makeGitRepository(
            repository_type=GitRepositoryType.IMPORTED)
        self.factory.makeGitRefs(
            repository=repository,
            paths=("refs/heads/master", "refs/heads/new"))
        removeSecurityProxy(repository)._default_branch = "refs/heads/master"
        with person_logged_in(repository.owner):
            self.assertRaisesWithContent(
                CannotModifyNonHostedGitRepository,
                "Cannot modify non-hosted Git repository %s." %
                    repository.display_name,
                setattr, repository, "default_branch", "new")
        self.assertEqual([], hosting_fixture.setProperties.calls)
        self.assertEqual("refs/heads/master", repository.default_branch)

    def test_exception_unset_default_branch(self):
        # attempting to set the default branch to None
        # should raise NoSuchGitReference
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.owner):
            self.assertRaisesWithContent(
                NoSuchGitReference,
                "The repository at %s does not contain "
                "a reference named 'None'." %
                    repository.display_name,
                setattr, repository, "default_branch", None)

    def test_exception_set_default_branch_nonexistent_ref(self):
        # Attempting to set the default branch
        # to a ref path that doesn't exist in the repository
        # should raise NoSuchGitReference
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRefs(
            repository=repository,
            paths=("refs/heads/master", "refs/heads/new"))
        removeSecurityProxy(repository)._default_branch = "refs/heads/master"
        with person_logged_in(repository.owner):
            self.assertRaisesWithContent(
                NoSuchGitReference,
                "The repository at %s does not contain "
                "a reference named 'refs/heads/nonexistent'." %
                    repository.display_name,
                setattr, repository,
                "default_branch", "refs/heads/nonexistent")
        self.assertEqual("refs/heads/master", repository.default_branch)


class TestGitRepositoryGetAllowedInformationTypes(TestCaseWithFactory):
    """Test `IGitRepository.getAllowedInformationTypes`."""

    layer = DatabaseFunctionalLayer

    def test_normal_user_sees_namespace_types(self):
        # An unprivileged user sees the types allowed by the namespace.
        repository = self.factory.makeGitRepository()
        policy = IGitNamespacePolicy(repository.namespace)
        self.assertContentEqual(
            policy.getAllowedInformationTypes(),
            repository.getAllowedInformationTypes(repository.owner))
        self.assertNotIn(
            InformationType.PROPRIETARY,
            repository.getAllowedInformationTypes(repository.owner))
        self.assertNotIn(
            InformationType.EMBARGOED,
            repository.getAllowedInformationTypes(repository.owner))

    def test_admin_sees_namespace_types(self):
        # An admin sees all the types, since they occasionally need to
        # override the namespace rules.  This is hopefully temporary, and
        # can go away once the new sharing rules (granting non-commercial
        # projects limited use of private repositories) are deployed.
        repository = self.factory.makeGitRepository()
        admin = self.factory.makeAdministrator()
        self.assertContentEqual(
            PUBLIC_INFORMATION_TYPES + PRIVATE_INFORMATION_TYPES,
            repository.getAllowedInformationTypes(admin))
        self.assertIn(
            InformationType.PROPRIETARY,
            repository.getAllowedInformationTypes(admin))


class TestGitRepositoryModerate(TestCaseWithFactory):
    """Test that project owners and commercial admins can moderate Git
    repositories."""

    layer = DatabaseFunctionalLayer

    def test_moderate_permission(self):
        # Test the ModerateGitRepository security checker.
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            self.assertTrue(check_permission("launchpad.Moderate", repository))
        with celebrity_logged_in("commercial_admin"):
            self.assertTrue(check_permission("launchpad.Moderate", repository))
        with person_logged_in(self.factory.makePerson()):
            self.assertFalse(
                check_permission("launchpad.Moderate", repository))

    def test_methods_smoketest(self):
        # Users with launchpad.Moderate can call transitionToInformationType.
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            project.setBranchSharingPolicy(BranchSharingPolicy.PUBLIC)
            repository.transitionToInformationType(
                InformationType.PRIVATESECURITY, project.owner)
            self.assertEqual(
                InformationType.PRIVATESECURITY, repository.information_type)

    def test_attribute_smoketest(self):
        # Users with launchpad.Moderate can set attributes.
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            repository.description = "something"
            repository.reviewer = project.owner
        self.assertEqual("something", repository.description)
        self.assertEqual(project.owner, repository.reviewer)


class TestGitRepositoryIsPersonTrustedReviewer(TestCaseWithFactory):
    """Test the `IGitRepository.isPersonTrustedReviewer` method."""

    layer = DatabaseFunctionalLayer

    def assertTrustedReviewer(self, repository, person):
        """Assert that `person` is a trusted reviewer for the `repository`."""
        self.assertTrue(repository.isPersonTrustedReviewer(person))

    def assertNotTrustedReviewer(self, repository, person):
        """Assert that `person` is not a trusted reviewer for the
        `repository`.
        """
        self.assertFalse(repository.isPersonTrustedReviewer(person))

    def test_none_is_not_trusted(self):
        # If None is passed in as the person, the method returns false.
        repository = self.factory.makeGitRepository()
        self.assertNotTrustedReviewer(repository, None)

    def test_repository_owner_is_trusted(self):
        # The repository owner is a trusted reviewer.
        repository = self.factory.makeGitRepository()
        self.assertTrustedReviewer(repository, repository.owner)

    def test_non_repository_owner_is_not_trusted(self):
        # Someone other than the repository owner is not a trusted reviewer.
        repository = self.factory.makeGitRepository()
        reviewer = self.factory.makePerson()
        self.assertNotTrustedReviewer(repository, reviewer)

    def test_lp_admins_always_trusted(self):
        # Launchpad admins are special, and as such, are trusted.
        repository = self.factory.makeGitRepository()
        admins = getUtility(ILaunchpadCelebrities).admin
        # Grab a random admin, the teamowner is good enough here.
        self.assertTrustedReviewer(repository, admins.teamowner)

    def test_member_of_team_owned_repository(self):
        # If the repository is owned by a team, any team member is a trusted
        # reviewer.
        team = self.factory.makeTeam()
        repository = self.factory.makeGitRepository(owner=team)
        self.assertTrustedReviewer(repository, team.teamowner)

    def test_review_team_member_is_trusted(self):
        # If the reviewer is a member of the review team, but not the owner
        # they are still trusted.
        team = self.factory.makeTeam()
        repository = self.factory.makeGitRepository(reviewer=team)
        self.assertTrustedReviewer(repository, team.teamowner)

    def test_repository_owner_not_review_team_member_is_trusted(self):
        # If the owner of the repository is not in the review team,
        #they are still trusted.
        team = self.factory.makeTeam()
        repository = self.factory.makeGitRepository(reviewer=team)
        self.assertFalse(repository.owner.inTeam(team))
        self.assertTrustedReviewer(repository, repository.owner)

    def test_community_reviewer(self):
        # If the reviewer is not a member of the owner, or the review team,
        # they are not trusted reviewers.
        team = self.factory.makeTeam()
        repository = self.factory.makeGitRepository(reviewer=team)
        reviewer = self.factory.makePerson()
        self.assertNotTrustedReviewer(repository, reviewer)


class TestGitRepositorySetName(TestCaseWithFactory):
    """Test `IGitRepository.setName`."""

    layer = DatabaseFunctionalLayer

    def test_not_owner(self):
        # A non-owner non-admin user cannot rename a repository.
        repository = self.factory.makeGitRepository()
        with person_logged_in(self.factory.makePerson()):
            self.assertRaises(Unauthorized, getattr, repository, "setName")

    def test_name_clash(self):
        # Name clashes are refused.
        repository = self.factory.makeGitRepository(name="foo")
        self.factory.makeGitRepository(
            owner=repository.owner, target=repository.target, name="bar")
        with person_logged_in(repository.owner):
            self.assertRaises(
                GitRepositoryExists, repository.setName,
                "bar", repository.owner)

    def test_rename(self):
        # A non-clashing rename request works.
        repository = self.factory.makeGitRepository(name="foo")
        with person_logged_in(repository.owner):
            repository.setName("bar", repository.owner)
        self.assertEqual("bar", repository.name)


class TestGitRepositorySetOwner(TestCaseWithFactory):
    """Test `IGitRepository.setOwner`."""

    layer = DatabaseFunctionalLayer

    def test_owner_sets_team(self):
        # The owner of the repository can set the owner of the repository to
        # be a team they are a member of.
        repository = self.factory.makeGitRepository()
        team = self.factory.makeTeam(owner=repository.owner)
        with person_logged_in(repository.owner):
            repository.setOwner(team, repository.owner)
        self.assertEqual(team, repository.owner)

    def test_owner_cannot_set_nonmember_team(self):
        # The owner of the repository cannot set the owner to be a team they
        # are not a member of.
        repository = self.factory.makeGitRepository()
        team = self.factory.makeTeam()
        with person_logged_in(repository.owner):
            self.assertRaises(
                GitRepositoryCreatorNotMemberOfOwnerTeam,
                repository.setOwner, team, repository.owner)

    def test_owner_cannot_set_other_user(self):
        # The owner of the repository cannot set the new owner to be another
        # person.
        repository = self.factory.makeGitRepository()
        person = self.factory.makePerson()
        with person_logged_in(repository.owner):
            self.assertRaises(
                GitRepositoryCreatorNotOwner,
                repository.setOwner, person, repository.owner)

    def test_admin_can_set_any_team_or_person(self):
        # A Launchpad admin can set the repository to be owned by any team
        # or person.
        repository = self.factory.makeGitRepository()
        team = self.factory.makeTeam()
        # To get a random administrator, choose the admin team owner.
        admin = getUtility(ILaunchpadCelebrities).admin.teamowner
        with person_logged_in(admin):
            repository.setOwner(team, admin)
            self.assertEqual(team, repository.owner)
            person = self.factory.makePerson()
            repository.setOwner(person, admin)
            self.assertEqual(person, repository.owner)

    def test_private_personal_forbidden_for_public_teams(self):
        # Only private teams can have private personal repositories.
        person = self.factory.makePerson()
        private_team = self.factory.makeTeam(
            owner=person, membership_policy=TeamMembershipPolicy.MODERATED,
            visibility=PersonVisibility.PRIVATE)
        public_team = self.factory.makeTeam(owner=person)
        with person_logged_in(person):
            repository = self.factory.makeGitRepository(
                owner=private_team, target=private_team,
                information_type=InformationType.USERDATA)
            self.assertRaises(
                GitTargetError, repository.setOwner, public_team, person)

    def test_private_personal_allowed_for_private_teams(self):
        # Only private teams can have private personal repositories.
        person = self.factory.makePerson()
        private_team_1 = self.factory.makeTeam(
            owner=person, membership_policy=TeamMembershipPolicy.MODERATED,
            visibility=PersonVisibility.PRIVATE)
        private_team_2 = self.factory.makeTeam(
            owner=person, membership_policy=TeamMembershipPolicy.MODERATED,
            visibility=PersonVisibility.PRIVATE)
        with person_logged_in(person):
            repository = self.factory.makeGitRepository(
                owner=private_team_1, target=private_team_1,
                information_type=InformationType.USERDATA)
            repository.setOwner(private_team_2, person)
            self.assertEqual(private_team_2, repository.owner)
            self.assertEqual(private_team_2, repository.target)

    def test_reconciles_access(self):
        # setOwner calls _reconcileAccess to make the sharing schema correct
        # when changing the owner of a private personal repository.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=person, visibility=PersonVisibility.PRIVATE)
        with person_logged_in(person):
            repository = self.factory.makeGitRepository(
                owner=person, target=person,
                information_type=InformationType.USERDATA)
            repository.setOwner(team, person)
        self.assertEqual(
            team, get_policies_for_artifact(repository)[0].person)


class TestGitRepositorySetTarget(TestCaseWithFactory):
    """Test `IGitRepository.setTarget`."""

    layer = DatabaseFunctionalLayer

    def test_personal_to_other_personal(self):
        # A personal repository can be moved to a different owner.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        repository = self.factory.makeGitRepository(
            owner=person, target=person)
        with person_logged_in(person):
            repository.setTarget(target=team, user=repository.owner)
        self.assertEqual(team, repository.owner)
        self.assertEqual(team, repository.target)

    def test_personal_to_project(self):
        # A personal repository can be moved to a project.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        project = self.factory.makeProduct()
        with person_logged_in(owner):
            repository.setTarget(target=project, user=owner)
        self.assertEqual(project, repository.target)

    def test_personal_to_package(self):
        # A personal repository can be moved to a package.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        dsp = self.factory.makeDistributionSourcePackage()
        with person_logged_in(owner):
            repository.setTarget(target=dsp, user=owner)
        self.assertEqual(dsp, repository.target)

    def test_personal_to_oci_project(self):
        # A personal repository can be moved to an OCI project.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        oci_project = self.factory.makeOCIProject()
        with person_logged_in(owner):
            repository.setTarget(target=oci_project, user=owner)
        self.assertEqual(oci_project, repository.target)

    def test_project_to_other_project(self):
        # Move a repository from one project to another.
        repository = self.factory.makeGitRepository()
        project = self.factory.makeProduct()
        with person_logged_in(repository.owner):
            repository.setTarget(target=project, user=repository.owner)
        self.assertEqual(project, repository.target)

    def test_project_to_package(self):
        # Move a repository from a project to a package.
        repository = self.factory.makeGitRepository()
        dsp = self.factory.makeDistributionSourcePackage()
        with person_logged_in(repository.owner):
            repository.setTarget(target=dsp, user=repository.owner)
        self.assertEqual(dsp, repository.target)

    def test_project_to_oci_project(self):
        # Move a repository from a project to an OCI project.
        repository = self.factory.makeGitRepository()
        oci_project = self.factory.makeOCIProject()
        with person_logged_in(repository.owner):
            repository.setTarget(target=oci_project, user=repository.owner)
        self.assertEqual(oci_project, repository.target)

    def test_project_to_personal(self):
        # Move a repository from a project to a personal namespace.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner)
        with person_logged_in(owner):
            repository.setTarget(target=owner, user=owner)
        self.assertEqual(owner, repository.target)

    def test_package_to_other_package(self):
        # Move a repository from one package to another.
        repository = self.factory.makeGitRepository(
            target=self.factory.makeDistributionSourcePackage())
        dsp = self.factory.makeDistributionSourcePackage()
        with person_logged_in(repository.owner):
            repository.setTarget(target=dsp, user=repository.owner)
        self.assertEqual(dsp, repository.target)

    def test_package_to_project(self):
        # Move a repository from a package to a project.
        repository = self.factory.makeGitRepository(
            target=self.factory.makeDistributionSourcePackage())
        project = self.factory.makeProduct()
        with person_logged_in(repository.owner):
            repository.setTarget(target=project, user=repository.owner)
        self.assertEqual(project, repository.target)

    def test_package_to_oci_project(self):
        # Move a repository from a package to an OCI project.
        repository = self.factory.makeGitRepository(
            target=self.factory.makeDistributionSourcePackage())
        oci_project = self.factory.makeOCIProject()
        with person_logged_in(repository.owner):
            repository.setTarget(target=oci_project, user=repository.owner)
        self.assertEqual(oci_project, repository.target)

    def test_package_to_personal(self):
        # Move a repository from a package to a personal namespace.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=owner, target=self.factory.makeDistributionSourcePackage())
        with person_logged_in(owner):
            repository.setTarget(target=owner, user=owner)
        self.assertEqual(owner, repository.target)

    def test_oci_project_to_other_package(self):
        # Move a repository from one OCI project to another.
        repository = self.factory.makeGitRepository(
            target=self.factory.makeOCIProject())
        oci_project = self.factory.makeOCIProject()
        with person_logged_in(repository.owner):
            repository.setTarget(target=oci_project, user=repository.owner)
        self.assertEqual(oci_project, repository.target)

    def test_oci_project_to_project(self):
        # Move a repository from an OCI project to a project.
        repository = self.factory.makeGitRepository(
            target=self.factory.makeOCIProject())
        project = self.factory.makeProduct()
        with person_logged_in(repository.owner):
            repository.setTarget(target=project, user=repository.owner)
        self.assertEqual(project, repository.target)

    def test_oci_project_to_oci_project(self):
        # Move a repository from an OCI project to an OCI project.
        repository = self.factory.makeGitRepository(
            target=self.factory.makeOCIProject())
        oci_project = self.factory.makeOCIProject()
        with person_logged_in(repository.owner):
            repository.setTarget(target=oci_project, user=repository.owner)
        self.assertEqual(oci_project, repository.target)

    def test_oci_project_to_personal(self):
        # Move a repository from an OCI project to a personal namespace.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=owner, target=self.factory.makeOCIProject())
        with person_logged_in(owner):
            repository.setTarget(target=owner, user=owner)
        self.assertEqual(owner, repository.target)

    def test_private_personal_forbidden_for_public_teams(self):
        # Only private teams can have private personal repositories.
        owner = self.factory.makeTeam()
        repository = self.factory.makeGitRepository(
            owner=owner, information_type=InformationType.USERDATA)
        with admin_logged_in():
            self.assertRaises(
                GitTargetError, repository.setTarget, target=owner, user=owner)

    def test_private_personal_allowed_for_private_teams(self):
        # Only private teams can have private personal repositories.
        owner = self.factory.makeTeam(visibility=PersonVisibility.PRIVATE)
        with person_logged_in(owner):
            repository = self.factory.makeGitRepository(
                owner=owner, information_type=InformationType.USERDATA)
            repository.setTarget(target=owner, user=owner)
            self.assertEqual(owner, repository.target)

    def test_reconciles_access(self):
        # setTarget calls _reconcileAccess to make the sharing schema
        # match the new target.
        repository = self.factory.makeGitRepository(
            information_type=InformationType.USERDATA)
        new_project = self.factory.makeProduct()
        with admin_logged_in():
            repository.setTarget(target=new_project, user=repository.owner)
        self.assertEqual(
            new_project, get_policies_for_artifact(repository)[0].pillar)

    def test_reconciles_access_personal(self):
        # setTarget calls _reconcileAccess to make the sharing schema
        # correct for a private personal repository.
        owner = self.factory.makeTeam(visibility=PersonVisibility.PRIVATE)
        with person_logged_in(owner):
            repository = self.factory.makeGitRepository(
                owner=owner,
                information_type=InformationType.USERDATA)
            repository.setTarget(target=owner, user=owner)
        self.assertEqual(
            owner, get_policies_for_artifact(repository)[0].person)

    def test_public_to_proprietary_only_project(self):
        # A repository cannot be moved to a target where the sharing policy
        # does not allow it.
        owner = self.factory.makePerson()
        commercial_project = self.factory.makeProduct(
            owner=owner, branch_sharing_policy=BranchSharingPolicy.PROPRIETARY)
        repository = self.factory.makeGitRepository(
            owner=owner, information_type=InformationType.PUBLIC)
        with admin_logged_in():
            self.assertRaises(
                GitTargetError, repository.setTarget,
                target=commercial_project, user=owner)


class TestGitRepositoryRescan(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_rescan(self):
        repository = self.factory.makeGitRepository()
        job_source = getUtility(IGitRefScanJobSource)
        self.assertEqual([], list(job_source.iterReady()))
        with person_logged_in(repository.owner):
            repository.rescan()
        [job] = list(job_source.iterReady())
        self.assertEqual(repository, job.repository)

    def test_getLatestScanJob(self):
        complete_date = datetime.now(pytz.UTC)

        repository = self.factory.makeGitRepository()
        failed_job = GitRefScanJob.create(repository)
        failed_job.job._status = JobStatus.FAILED
        failed_job.job.date_finished = complete_date
        completed_job = GitRefScanJob.create(repository)
        completed_job.job._status = JobStatus.COMPLETED
        completed_job.job.date_finished = complete_date - timedelta(seconds=10)
        result = removeSecurityProxy(repository.getLatestScanJob())
        self.assertEqual(failed_job.job_id, result.job_id)

    def test_getLatestScanJob_no_scans(self):
        repository = self.factory.makeGitRepository()
        result = repository.getLatestScanJob()
        self.assertIsNone(result)

    def test_getLatestScanJob_correct_branch(self):
        complete_date = datetime.now(pytz.UTC)

        main_repository = self.factory.makeGitRepository()
        second_repository = self.factory.makeGitRepository()
        failed_job = GitRefScanJob.create(second_repository)
        failed_job.job._status = JobStatus.FAILED
        failed_job.job.date_finished = complete_date
        completed_job = GitRefScanJob.create(main_repository)
        completed_job.job._status = JobStatus.COMPLETED
        completed_job.job.date_finished = complete_date - timedelta(seconds=10)
        result = removeSecurityProxy(main_repository.getLatestScanJob())
        self.assertEqual(completed_job.job_id, result.job_id)

    def test_getLatestScanJob_without_completion_date(self):
        repository = self.factory.makeGitRepository()
        failed_job = GitRefScanJob.create(repository)
        failed_job.job._status = JobStatus.FAILED
        result = repository.getLatestScanJob()
        self.assertTrue(result)
        self.assertIsNone(result.job.date_finished)


class TestGitRepositoryUpdateMergeCommitIDs(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_updates_proposals(self):
        # `updateMergeCommitIDs` updates proposals for specified refs.
        repository = self.factory.makeGitRepository()
        paths = ["refs/heads/1", "refs/heads/2", "refs/heads/3"]
        [ref1, ref2, ref3] = self.factory.makeGitRefs(
            repository=repository, paths=paths)
        bmp1 = self.factory.makeBranchMergeProposalForGit(
            target_ref=ref1, source_ref=ref2)
        bmp2 = self.factory.makeBranchMergeProposalForGit(
            target_ref=ref1, source_ref=ref3, prerequisite_ref=ref2)
        removeSecurityProxy(ref1).commit_sha1 = "0" * 40
        removeSecurityProxy(ref2).commit_sha1 = "1" * 40
        removeSecurityProxy(ref3).commit_sha1 = "2" * 40
        self.assertNotEqual(ref1, bmp1.target_git_ref)
        self.assertNotEqual(ref2, bmp1.source_git_ref)
        self.assertNotEqual(ref1, bmp2.target_git_ref)
        self.assertNotEqual(ref3, bmp2.source_git_ref)
        self.assertNotEqual(ref2, bmp2.prerequisite_git_ref)
        self.assertContentEqual(
            [bmp1.id, bmp2.id], repository.updateMergeCommitIDs(paths))
        self.assertEqual(ref1, bmp1.target_git_ref)
        self.assertEqual(ref2, bmp1.source_git_ref)
        self.assertEqual(ref1, bmp2.target_git_ref)
        self.assertIsNone(bmp1.prerequisite_git_ref)
        self.assertEqual(ref3, bmp2.source_git_ref)
        self.assertEqual(ref2, bmp2.prerequisite_git_ref)

    def test_skips_unspecified_refs(self):
        # `updateMergeCommitIDs` skips unspecified refs.
        repository1 = self.factory.makeGitRepository()
        paths = ["refs/heads/1", "refs/heads/2"]
        [ref1_1, ref1_2] = self.factory.makeGitRefs(
            repository=repository1, paths=paths)
        bmp1 = self.factory.makeBranchMergeProposalForGit(
            target_ref=ref1_1, source_ref=ref1_2)
        repository2 = self.factory.makeGitRepository(target=repository1.target)
        [ref2_1, ref2_2] = self.factory.makeGitRefs(
            repository=repository2, paths=paths)
        bmp2 = self.factory.makeBranchMergeProposalForGit(
            target_ref=ref2_1, source_ref=ref2_2)
        removeSecurityProxy(ref1_1).commit_sha1 = "0" * 40
        removeSecurityProxy(ref1_2).commit_sha1 = "1" * 40
        removeSecurityProxy(ref2_1).commit_sha1 = "2" * 40
        removeSecurityProxy(ref2_2).commit_sha1 = "3" * 40
        self.assertNotEqual(ref1_1, bmp1.target_git_ref)
        self.assertNotEqual(ref1_2, bmp1.source_git_ref)
        self.assertNotEqual(ref2_1, bmp2.target_git_ref)
        self.assertNotEqual(ref2_2, bmp2.source_git_ref)
        self.assertContentEqual(
            [bmp1.id], repository1.updateMergeCommitIDs([paths[0]]))
        self.assertEqual(ref1_1, bmp1.target_git_ref)
        self.assertNotEqual(ref1_2, bmp1.source_git_ref)
        self.assertNotEqual(ref2_1, bmp2.target_git_ref)
        self.assertNotEqual(ref2_2, bmp2.source_git_ref)


class TestGitRepositoryUpdateLandingTargets(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_schedules_diff_updates(self):
        """Create jobs for all merge proposals."""
        bmp1 = self.factory.makeBranchMergeProposalForGit()
        bmp2 = self.factory.makeBranchMergeProposalForGit(
            source_ref=bmp1.source_git_ref)
        jobs = bmp1.source_git_repository.updateLandingTargets(
            [bmp1.source_git_path])
        self.assertEqual(2, len(jobs))
        bmps_to_update = [
            removeSecurityProxy(job).branch_merge_proposal for job in jobs]
        self.assertContentEqual([bmp1, bmp2], bmps_to_update)

    def test_ignores_final(self):
        """Diffs for proposals in final states aren't updated."""
        [source_ref] = self.factory.makeGitRefs()
        for state in FINAL_STATES:
            bmp = self.factory.makeBranchMergeProposalForGit(
                source_ref=source_ref, set_state=state)
        # Creating a superseded proposal has the side effect of creating a
        # second proposal.  Delete the second proposal.
        for bmp in source_ref.landing_targets:
            if bmp.queue_status not in FINAL_STATES:
                removeSecurityProxy(bmp).deleteProposal()
        jobs = source_ref.repository.updateLandingTargets([source_ref.path])
        self.assertEqual(0, len(jobs))


class TestGitRepositoryMarkRecipesStale(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_base_repository_recipe(self):
        # On ref changes, recipes where this ref is the base become stale.
        [ref] = self.factory.makeGitRefs()
        recipe = self.factory.makeSourcePackageRecipe(branches=[ref])
        removeSecurityProxy(recipe).is_stale = False
        ref.repository.createOrUpdateRefs(
            {ref.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertTrue(recipe.is_stale)

    def test_base_repository_different_ref_recipe(self):
        # On ref changes, recipes where a different ref in the same
        # repository is the base are left alone.
        ref1, ref2 = self.factory.makeGitRefs(
            paths=["refs/heads/a", "refs/heads/b"])
        recipe = self.factory.makeSourcePackageRecipe(branches=[ref1])
        removeSecurityProxy(recipe).is_stale = False
        ref1.repository.createOrUpdateRefs(
            {ref2.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertFalse(recipe.is_stale)

    def test_base_repository_default_branch_recipe(self):
        # On ref changes to the default branch, recipes where this
        # repository is the base with no explicit revspec become stale.
        repository = self.factory.makeGitRepository()
        ref1, ref2 = self.factory.makeGitRefs(
            repository=repository, paths=["refs/heads/a", "refs/heads/b"])
        removeSecurityProxy(repository)._default_branch = "refs/heads/a"
        recipe = self.factory.makeSourcePackageRecipe(branches=[repository])
        removeSecurityProxy(recipe).is_stale = False
        repository.createOrUpdateRefs(
            {ref2.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertFalse(recipe.is_stale)
        repository.createOrUpdateRefs(
            {ref1.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertTrue(recipe.is_stale)

    def test_instruction_repository_recipe(self):
        # On ref changes, recipes including this ref become stale.
        [base_ref] = self.factory.makeGitRefs()
        [ref] = self.factory.makeGitRefs()
        recipe = self.factory.makeSourcePackageRecipe(branches=[base_ref, ref])
        removeSecurityProxy(recipe).is_stale = False
        ref.repository.createOrUpdateRefs(
            {ref.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertTrue(recipe.is_stale)

    def test_instruction_repository_different_ref_recipe(self):
        # On ref changes, recipes including a different ref in the same
        # repository are left alone.
        [base_ref] = self.factory.makeGitRefs()
        ref1, ref2 = self.factory.makeGitRefs(
            paths=["refs/heads/a", "refs/heads/b"])
        recipe = self.factory.makeSourcePackageRecipe(
            branches=[base_ref, ref1])
        removeSecurityProxy(recipe).is_stale = False
        ref1.repository.createOrUpdateRefs(
            {ref2.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertFalse(recipe.is_stale)

    def test_instruction_repository_default_branch_recipe(self):
        # On ref changes to the default branch, recipes including this
        # repository with no explicit revspec become stale.
        [base_ref] = self.factory.makeGitRefs()
        repository = self.factory.makeGitRepository()
        ref1, ref2 = self.factory.makeGitRefs(
            repository=repository, paths=["refs/heads/a", "refs/heads/b"])
        removeSecurityProxy(repository)._default_branch = "refs/heads/a"
        recipe = self.factory.makeSourcePackageRecipe(
            branches=[base_ref, repository])
        removeSecurityProxy(recipe).is_stale = False
        repository.createOrUpdateRefs(
            {ref2.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertFalse(recipe.is_stale)
        repository.createOrUpdateRefs(
            {ref1.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertTrue(recipe.is_stale)

    def test_unrelated_repository_recipe(self):
        # On ref changes, unrelated recipes are left alone.
        [ref] = self.factory.makeGitRefs()
        recipe = self.factory.makeSourcePackageRecipe(
            branches=self.factory.makeGitRefs())
        removeSecurityProxy(recipe).is_stale = False
        ref.repository.createOrUpdateRefs(
            {ref.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertFalse(recipe.is_stale)


class TestGitRepositoryMarkSnapsStale(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_same_repository(self):
        # On ref changes, snap packages using this ref become stale.
        [ref] = self.factory.makeGitRefs()
        snap = self.factory.makeSnap(git_ref=ref)
        removeSecurityProxy(snap).is_stale = False
        ref.repository.createOrUpdateRefs(
            {ref.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertTrue(snap.is_stale)

    def test_same_repository_different_ref(self):
        # On ref changes, snap packages using a different ref in the same
        # repository are left alone.
        ref1, ref2 = self.factory.makeGitRefs(
            paths=["refs/heads/a", "refs/heads/b"])
        snap = self.factory.makeSnap(git_ref=ref1)
        removeSecurityProxy(snap).is_stale = False
        ref1.repository.createOrUpdateRefs(
            {ref2.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertFalse(snap.is_stale)

    def test_different_repository(self):
        # On ref changes, unrelated snap packages are left alone.
        [ref] = self.factory.makeGitRefs()
        snap = self.factory.makeSnap(git_ref=self.factory.makeGitRefs()[0])
        removeSecurityProxy(snap).is_stale = False
        ref.repository.createOrUpdateRefs(
            {ref.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertFalse(snap.is_stale)

    def test_private_snap(self):
        # A private snap should be able to be marked stale
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))
        [ref] = self.factory.makeGitRefs()
        snap = self.factory.makeSnap(git_ref=ref, private=True)
        removeSecurityProxy(snap).is_stale = False
        ref.repository.createOrUpdateRefs(
            {ref.path: {"sha1": "0" * 40, "type": GitObjectType.COMMIT}})
        self.assertTrue(snap.is_stale)


class TestGitRepositoryFork(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitRepositoryFork, self).setUp()
        self.hosting_fixture = self.useFixture(GitHostingFixture())

    def test_fork(self):
        repo = self.factory.makeGitRepository()
        with person_logged_in(repo.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repo.target, repo)
        another_person = self.factory.makePerson()
        another_team = self.factory.makeTeam(members=[another_person])

        forked_repo = getUtility(IGitRepositorySet).fork(
            repo, another_person, another_team)
        self.assertThat(forked_repo, MatchesStructure(
            registrant=Equals(another_person),
            owner=Equals(another_team),
            target=Equals(repo.target),
            name=Equals(repo.name),
            owner_default=Is(True),
            target_default=Is(False)))
        self.assertEqual(
            [((forked_repo.getInternalPath(),),
              {"clone_from": repo.getInternalPath(), "async_create": True})],
            self.hosting_fixture.create.calls)

    def test_fork_not_owner_default(self):
        repo = self.factory.makeGitRepository()
        with person_logged_in(repo.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repo.target, repo)
        # The person forking the repo already has another repo which is the
        # owner-default for that owner & target.
        previous_repo = self.factory.makeGitRepository(target=repo.target)
        previous_repo.setOwnerDefault(True)

        forked_repo = getUtility(IGitRepositorySet).fork(
            repo, previous_repo.owner, previous_repo.owner)
        self.assertThat(forked_repo, MatchesStructure(
            registrant=Equals(previous_repo.owner),
            owner=Equals(previous_repo.owner),
            target=Equals(repo.target),
            name=Equals(repo.name),
            owner_default=Is(False),
            target_default=Is(False)))
        self.assertEqual(
            [((forked_repo.getInternalPath(),),
              {"clone_from": repo.getInternalPath(), "async_create": True})],
            self.hosting_fixture.create.calls)

    def test_fork_same_name(self):
        repo = self.factory.makeGitRepository()
        with person_logged_in(repo.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repo.target, repo)

        person = self.factory.makePerson()
        self.factory.makeGitRepository(
            owner=person, registrant=person,
            name=repo.name, target=repo.target)

        forked_repo = getUtility(IGitRepositorySet).fork(repo, person, person)
        self.assertThat(forked_repo, MatchesStructure(
            registrant=Equals(person),
            owner=Equals(person),
            target=Equals(repo.target),
            name=Equals("%s-1" % repo.name),
            owner_default=Is(True),
            target_default=Is(False)))
        self.assertEqual(
            [((forked_repo.getInternalPath(),),
              {"clone_from": repo.getInternalPath(), "async_create": True})],
            self.hosting_fixture.create.calls)

    def test_fork_non_default_origin(self):
        project = self.factory.makeProduct()
        default_repo = self.factory.makeGitRepository(target=project)
        non_default_repo = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                project, default_repo)
        person = self.factory.makePerson()

        forked_repo = getUtility(IGitRepositorySet).fork(
            non_default_repo, person, person)
        self.assertThat(forked_repo, MatchesStructure(
            registrant=Equals(person),
            owner=Equals(person),
            target=Equals(project),
            owner_default=Is(False),
            target_default=Is(False)))
        self.assertEqual(
            [((forked_repo.getInternalPath(),),
              {"clone_from": non_default_repo.getInternalPath(),
               "async_create": True})],
            self.hosting_fixture.create.calls)


class TestGitRepositoryDetectMerges(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_markProposalMerged(self):
        # A merge proposal that is merged is marked as such.
        proposal = self.factory.makeBranchMergeProposalForGit()
        self.assertNotEqual(
            BranchMergeProposalStatus.MERGED, proposal.queue_status)
        proposal.target_git_repository._markProposalMerged(
            proposal, proposal.target_git_commit_sha1)
        self.assertEqual(
            BranchMergeProposalStatus.MERGED, proposal.queue_status)
        job = IStore(proposal).find(
            BranchMergeProposalJob,
            BranchMergeProposalJob.branch_merge_proposal == proposal,
            BranchMergeProposalJob.job_type ==
            BranchMergeProposalJobType.MERGE_PROPOSAL_UPDATED).one()
        derived_job = job.makeDerived()
        derived_job.run()
        notifications = pop_notifications()
        self.assertIn(
            "Work in progress => Merged",
            notifications[0].get_payload(decode=True).decode("UTF-8"))
        self.assertEqual(
            config.canonical.noreply_from_address, notifications[0]["From"])
        recipients = set(msg["x-envelope-to"] for msg in notifications)
        expected = set(
            [proposal.source_git_repository.registrant.preferredemail.email,
             proposal.target_git_repository.registrant.preferredemail.email])
        self.assertEqual(expected, recipients)

    def test_update_detects_merges(self):
        # Pushing changes to a branch causes a check whether any active
        # merge proposals with that branch as the target have been merged.
        repository = self.factory.makeGitRepository()
        [target_1, target_2, source_1, source_2] = self.factory.makeGitRefs(
            repository, paths=[
                "refs/heads/target-1",
                "refs/heads/target-2",
                "refs/heads/source-1",
                "refs/heads/source-2",
                ])
        bmp1 = self.factory.makeBranchMergeProposalForGit(
            target_ref=target_1, source_ref=source_1)
        bmp2 = self.factory.makeBranchMergeProposalForGit(
            target_ref=target_1, source_ref=source_2)
        bmp3 = self.factory.makeBranchMergeProposalForGit(
            target_ref=target_2, source_ref=source_1)
        hosting_fixture = self.useFixture(GitHostingFixture(
            merges={source_1.commit_sha1: "0" * 40}))
        refs_info = {
            "refs/heads/target-1": {
                "sha1": "0" * 40,
                "type": GitObjectType.COMMIT,
                },
            "refs/heads/target-2": {
                "sha1": "1" * 40,
                "type": GitObjectType.COMMIT,
                },
            }
        expected_events = [
            ObjectModifiedEvent, ObjectModifiedEvent, GitRefsUpdatedEvent]
        _, events = self.assertNotifies(
            expected_events, True, repository.createOrUpdateRefs, refs_info)
        expected_args = [
            (repository.getInternalPath(), target_1.commit_sha1,
             set([source_1.commit_sha1, source_2.commit_sha1])),
            (repository.getInternalPath(), target_2.commit_sha1,
             set([source_1.commit_sha1])),
            ]
        self.assertContentEqual(
            expected_args, hosting_fixture.detectMerges.extract_args())
        self.assertEqual(BranchMergeProposalStatus.MERGED, bmp1.queue_status)
        self.assertEqual("0" * 40, bmp1.merged_revision_id)
        self.assertEqual(
            BranchMergeProposalStatus.WORK_IN_PROGRESS, bmp2.queue_status)
        self.assertEqual(BranchMergeProposalStatus.MERGED, bmp3.queue_status)
        self.assertEqual("0" * 40, bmp3.merged_revision_id)
        # The two ObjectModifiedEvents indicate the queue_status changes.
        self.assertContentEqual(
            [bmp1, bmp3], [event.object for event in events[:2]])
        self.assertContentEqual(
            [(BranchMergeProposalStatus.WORK_IN_PROGRESS,
              BranchMergeProposalStatus.MERGED)],
            set((event.object_before_modification.queue_status,
                 event.object.queue_status)
                for event in events[:2]))


class TestGitRepositoryGetBlob(TestCaseWithFactory):
    """Tests for retrieving files from a Git repository."""

    layer = DatabaseFunctionalLayer

    def test_getBlob_with_default_rev(self):
        repository = self.factory.makeGitRepository()
        self.useFixture(GitHostingFixture(blob=b'Some text'))
        ret = repository.getBlob('src/README.txt')
        self.assertEqual(b'Some text', ret)

    def test_getBlob_with_rev(self):
        repository = self.factory.makeGitRepository()
        self.useFixture(GitHostingFixture(blob=b'Some text'))
        ret = repository.getBlob('src/README.txt', 'some-rev')
        self.assertEqual(b'Some text', ret)


class TestGitRepositoryRules(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_rules(self):
        repository = self.factory.makeGitRepository()
        other_repository = self.factory.makeGitRepository()
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*")
        self.factory.makeGitRule(
            repository=other_repository, ref_pattern="refs/heads/*")
        self.assertThat(list(repository.rules), MatchesListwise([
            MatchesStructure.byEquality(
                repository=repository,
                ref_pattern="refs/heads/*"),
            MatchesStructure.byEquality(
                repository=repository,
                ref_pattern="refs/heads/stable/*"),
            ]))

    def test_getRule(self):
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRefs(
            repository=repository, paths=["refs/heads/master"])
        other_repository = self.factory.makeGitRepository()
        master_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/master")
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        self.factory.makeGitRule(
            repository=other_repository, ref_pattern="refs/heads/master")
        self.assertEqual(master_rule, repository.getRule("refs/heads/master"))
        self.assertIsNone(repository.getRule("refs/heads/other"))

    def test_addRule_append(self):
        repository = self.factory.makeGitRepository()
        initial_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        self.assertEqual(0, initial_rule.position)
        with person_logged_in(repository.owner):
            new_rule = repository.addRule(
                "refs/heads/stable/*", repository.owner)
        self.assertEqual(1, new_rule.position)
        self.assertEqual([initial_rule, new_rule], list(repository.rules))

    def test_addRule_insert(self):
        repository = self.factory.makeGitRepository()
        initial_rules = [
            self.factory.makeGitRule(
                repository=repository, ref_pattern="refs/heads/*"),
            self.factory.makeGitRule(
                repository=repository, ref_pattern="refs/heads/protected/*"),
            self.factory.makeGitRule(
                repository=repository, ref_pattern="refs/heads/another/*"),
            ]
        self.assertEqual([0, 1, 2], [rule.position for rule in initial_rules])
        with person_logged_in(repository.owner):
            new_rule = repository.addRule(
                "refs/heads/stable/*", repository.owner, position=1)
        self.assertEqual(1, new_rule.position)
        self.assertEqual([0, 2, 3], [rule.position for rule in initial_rules])
        self.assertEqual(
            [initial_rules[0], new_rule, initial_rules[1], initial_rules[2]],
            list(repository.rules))

    def test_addRule_exact_first(self):
        repository = self.factory.makeGitRepository()
        initial_rules = [
            self.factory.makeGitRule(
                repository=repository, ref_pattern="refs/heads/exact"),
            self.factory.makeGitRule(
                repository=repository, ref_pattern="refs/heads/*"),
            ]
        self.assertEqual([0, 1], [rule.position for rule in initial_rules])
        with person_logged_in(repository.owner):
            exact_rule = repository.addRule(
                "refs/heads/exact-2", repository.owner)
        self.assertEqual(
            [initial_rules[0], exact_rule, initial_rules[1]],
            list(repository.rules))
        with person_logged_in(repository.owner):
            wildcard_rule = repository.addRule(
                "refs/heads/wildcard/*", repository.owner, position=0)
        self.assertEqual(
            [initial_rules[0], exact_rule, wildcard_rule, initial_rules[1]],
            list(repository.rules))

    def test_moveRule(self):
        repository = self.factory.makeGitRepository()
        rules = [
            self.factory.makeGitRule(
                repository=repository,
                ref_pattern=self.factory.getUniqueUnicode(
                    prefix="refs/heads/*/"))
            for _ in range(5)]
        with person_logged_in(repository.owner):
            self.assertEqual(rules, list(repository.rules))
            repository.moveRule(rules[0], 4, repository.owner)
            self.assertEqual(rules[1:] + [rules[0]], list(repository.rules))
            repository.moveRule(rules[0], 0, repository.owner)
            self.assertEqual(rules, list(repository.rules))
            repository.moveRule(rules[2], 1, repository.owner)
            self.assertEqual(
                [rules[0], rules[2], rules[1], rules[3], rules[4]],
                list(repository.rules))

    def test_moveRule_non_negative(self):
        rule = self.factory.makeGitRule()
        with person_logged_in(rule.repository.owner):
            self.assertRaises(
                ValueError, rule.repository.moveRule,
                rule, -1, rule.repository.owner)

    def test_grants(self):
        repository = self.factory.makeGitRepository()
        other_repository = self.factory.makeGitRepository()
        rule = self.factory.makeGitRule(repository=repository)
        other_rule = self.factory.makeGitRule(repository=other_repository)
        grants = [
            self.factory.makeGitRuleGrant(
                rule=rule, grantee=self.factory.makePerson())
            for _ in range(2)
            ]
        self.factory.makeGitRuleGrant(
            rule=other_rule, grantee=self.factory.makePerson())
        self.assertContentEqual(grants, repository.grants)

    def test_getRules_query_count(self):
        repository = self.factory.makeGitRepository()
        owner = repository.owner

        def create_rule_and_grants():
            with person_logged_in(owner):
                rule = self.factory.makeGitRule(
                    repository=repository,
                    ref_pattern=self.factory.getUniqueUnicode(
                        prefix="refs/heads/"))
                for i in range(2):
                    self.factory.makeGitRuleGrant(rule=rule)

        def get_rules():
            with person_logged_in(owner):
                return repository.getRules()

        recorder1, recorder2 = record_two_runs(
            get_rules, create_rule_and_grants, 2)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test__validateRules_ok(self):
        repository = self.factory.makeGitRepository()
        rules = [
            IGitNascentRule({
                "ref_pattern": "refs/heads/*",
                "grants": [],
                }),
            IGitNascentRule({
                "ref_pattern": "refs/heads/stable/*",
                "grants": [],
                }),
            ]
        removeSecurityProxy(repository)._validateRules(rules)

    def test__validateRules_duplicate_ref_pattern(self):
        repository = self.factory.makeGitRepository()
        rules = [
            IGitNascentRule({
                "ref_pattern": "refs/heads/*",
                "grants": [],
                }),
            IGitNascentRule({
                "ref_pattern": "refs/heads/*",
                "grants": [],
                }),
            ]
        self.assertRaisesWithContent(
            ValueError,
            "New rules may not contain duplicate ref patterns "
            "(e.g. refs/heads/*)",
            removeSecurityProxy(repository)._validateRules, rules)

    def test_setRules_add(self):
        owner = self.factory.makeTeam()
        member = self.factory.makePerson(member_of=[owner])
        repository = self.factory.makeGitRepository(owner=owner)
        grantee = self.factory.makePerson()
        with person_logged_in(member):
            repository.setRules([
                IGitNascentRule({
                    "ref_pattern": "refs/heads/stable/*",
                    "grants": [
                        IGitNascentRuleGrant({
                            "grantee_type": GitGranteeType.REPOSITORY_OWNER,
                            "can_create": True,
                            "can_force_push": True,
                            }),
                        ],
                    }),
                IGitNascentRule({
                    "ref_pattern": "refs/heads/*",
                    "grants": [
                        IGitNascentRuleGrant({
                            "grantee_type": GitGranteeType.PERSON,
                            "grantee": grantee,
                            "can_push": True,
                            }),
                        ],
                    }),
                ], member)
        self.assertThat(list(repository.rules), MatchesListwise([
            MatchesStructure(
                repository=Equals(repository),
                ref_pattern=Equals("refs/heads/stable/*"),
                creator=Equals(member),
                grants=MatchesSetwise(
                    MatchesStructure(
                        grantor=Equals(member),
                        grantee_type=Equals(GitGranteeType.REPOSITORY_OWNER),
                        grantee=Is(None),
                        can_create=Is(True),
                        can_push=Is(False),
                        can_force_push=Is(True)))),
            MatchesStructure(
                repository=Equals(repository),
                ref_pattern=Equals("refs/heads/*"),
                creator=Equals(member),
                grants=MatchesSetwise(
                    MatchesStructure(
                        grantor=Equals(member),
                        grantee_type=Equals(GitGranteeType.PERSON),
                        grantee=Equals(grantee),
                        can_create=Is(False),
                        can_push=Is(True),
                        can_force_push=Is(False)))),
            ]))

    def test_setRules_move(self):
        owner = self.factory.makeTeam()
        members = [
            self.factory.makePerson(member_of=[owner]) for _ in range(2)]
        repository = self.factory.makeGitRepository(owner=owner)
        for ref_pattern in (
                "refs/heads/stable/*", "refs/heads/*/next", "refs/heads/*"):
            self.factory.makeGitRule(
                repository=repository, ref_pattern=ref_pattern,
                creator=members[0])
        date_created = get_transaction_timestamp(Store.of(repository))
        with person_logged_in(members[1]):
            repository.setRules([
                IGitNascentRule({
                    "ref_pattern": "refs/heads/*/next",
                    "grants": [],
                    }),
                IGitNascentRule({
                    "ref_pattern": "refs/heads/stable/*",
                    "grants": [],
                    }),
                IGitNascentRule({
                    "ref_pattern": "refs/heads/*",
                    "grants": [],
                    }),
                ], members[1])
            date_modified = get_transaction_timestamp(Store.of(repository))
        self.assertThat(list(repository.rules), MatchesListwise([
            MatchesStructure(
                repository=Equals(repository),
                ref_pattern=Equals("refs/heads/*/next"),
                creator=Equals(members[0]),
                date_created=Equals(date_created),
                date_last_modified=Equals(date_modified)),
            MatchesStructure(
                repository=Equals(repository),
                ref_pattern=Equals("refs/heads/stable/*"),
                creator=Equals(members[0]),
                date_created=Equals(date_created),
                date_last_modified=Equals(date_created)),
            MatchesStructure(
                repository=Equals(repository),
                ref_pattern=Equals("refs/heads/*"),
                creator=Equals(members[0]),
                date_created=Equals(date_created),
                date_last_modified=Equals(date_created)),
            ]))

    def test_setRules_canonicalises_expected_ordering(self):
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.owner):
            repository.setRules([
                IGitNascentRule({
                    "ref_pattern": "refs/heads/master-next",
                    "grants": [],
                    }),
                IGitNascentRule({
                    "ref_pattern": "refs/heads/master",
                    "grants": [],
                    }),
                ], repository.owner)

    def test_setRules_modify_grants(self):
        owner = self.factory.makeTeam()
        members = [
            self.factory.makePerson(member_of=[owner]) for _ in range(2)]
        repository = self.factory.makeGitRepository(owner=owner)
        stable_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*",
            creator=members[0])
        grantee = self.factory.makePerson()
        self.factory.makeGitRuleGrant(
            rule=stable_rule, grantee=grantee, grantor=members[0],
            can_push=True)
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*",
            creator=members[0])
        date_created = get_transaction_timestamp(Store.of(repository))
        transaction.commit()
        with person_logged_in(members[1]):
            repository.setRules([
                IGitNascentRule({
                    "ref_pattern": "refs/heads/stable/*",
                    "grants": [
                        IGitNascentRuleGrant({
                            "grantee_type": GitGranteeType.REPOSITORY_OWNER,
                            "can_create": True,
                            }),
                        IGitNascentRuleGrant({
                            "grantee_type": GitGranteeType.PERSON,
                            "grantee": grantee,
                            "can_push": True,
                            "can_force_push": True,
                            }),
                        ],
                    }),
                IGitNascentRule({
                    "ref_pattern": "refs/heads/*",
                    "grants": [],
                    }),
                ], members[1])
            date_modified = get_transaction_timestamp(
                Store.of(repository))
        self.assertThat(list(repository.rules), MatchesListwise([
            MatchesStructure(
                repository=Equals(repository),
                ref_pattern=Equals("refs/heads/stable/*"),
                creator=Equals(members[0]),
                date_created=Equals(date_created),
                date_last_modified=Equals(date_created),
                grants=MatchesSetwise(
                    MatchesStructure(
                        grantor=Equals(members[1]),
                        grantee_type=Equals(GitGranteeType.REPOSITORY_OWNER),
                        grantee=Is(None),
                        can_create=Is(True),
                        can_push=Is(False),
                        can_force_push=Is(False),
                        date_created=Equals(date_modified),
                        date_last_modified=Equals(date_modified)),
                    MatchesStructure(
                        grantor=Equals(members[0]),
                        grantee_type=Equals(GitGranteeType.PERSON),
                        grantee=Equals(grantee),
                        can_create=Is(False),
                        can_push=Is(True),
                        can_force_push=Is(True),
                        date_created=Equals(date_created),
                        date_last_modified=Equals(date_modified)))),
            MatchesStructure(
                repository=Equals(repository),
                ref_pattern=Equals("refs/heads/*"),
                creator=Equals(members[0]),
                date_created=Equals(date_created),
                date_last_modified=Equals(date_created),
                grants=MatchesSetwise()),
            ]))

    def test_setRules_remove(self):
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*")
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        date_created = get_transaction_timestamp(Store.of(repository))
        transaction.commit()
        with person_logged_in(repository.owner):
            repository.setRules([
                IGitNascentRule({
                    "ref_pattern": "refs/heads/*",
                    "grants": [],
                    }),
                ], repository.owner)
        self.assertThat(list(repository.rules), MatchesListwise([
            MatchesStructure(
                repository=Equals(repository),
                ref_pattern=Equals("refs/heads/*"),
                date_created=Equals(date_created),
                date_last_modified=Equals(date_created),
                grants=MatchesSetwise()),
            ]))


class TestGitRepositorySet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitRepositorySet, self).setUp()
        self.repository_set = getUtility(IGitRepositorySet)

    def test_new(self):
        # By default, GitRepositorySet.new creates a new repository in the
        # database but not on the hosting service.
        hosting_fixture = self.useFixture(GitHostingFixture())
        owner = self.factory.makePerson()
        target = self.factory.makeProduct()
        name = self.factory.getUniqueUnicode()
        repository = self.repository_set.new(
            GitRepositoryType.HOSTED, owner, owner, target, name)
        self.assertThat(repository, MatchesStructure.byEquality(
            registrant=owner, owner=owner, target=target, name=name))
        self.assertEqual(0, hosting_fixture.create.call_count)

    def test_new_with_hosting(self):
        # GitRepositorySet.new(with_hosting=True) creates a new repository
        # in both the database and the hosting service.
        hosting_fixture = self.useFixture(GitHostingFixture())
        owner = self.factory.makePerson()
        target = self.factory.makeProduct()
        name = self.factory.getUniqueUnicode()
        repository = self.repository_set.new(
            GitRepositoryType.HOSTED, owner, owner, target, name,
            with_hosting=True)
        self.assertThat(repository, MatchesStructure.byEquality(
            registrant=owner, owner=owner, target=target, name=name))
        self.assertEqual(
            [((repository.getInternalPath(),),
              {'async_create': False, "clone_from": None})],
            hosting_fixture.create.calls)

    def test_provides_IGitRepositorySet(self):
        # GitRepositorySet instances provide IGitRepositorySet.
        verifyObject(IGitRepositorySet, self.repository_set)

    def test_getByPath(self):
        # getByPath returns a repository matching the path that it's given.
        a = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        repository = self.repository_set.getByPath(a.owner, a.shortened_path)
        self.assertEqual(a, repository)

    def test_getByPath_not_found(self):
        # If a repository cannot be found for a path, then getByPath returns
        # None.
        person = self.factory.makePerson()
        self.assertIsNone(self.repository_set.getByPath(person, "nonexistent"))

    def test_getByPath_inaccessible(self):
        # If the given user cannot view the matched repository, then
        # getByPath returns None.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            path = repository.shortened_path
        self.assertEqual(
            repository, self.repository_set.getByPath(owner, path))
        self.assertIsNone(
            self.repository_set.getByPath(self.factory.makePerson(), path))

    def test_getRepositories(self):
        # getRepositories returns a collection of repositories for the given
        # target.
        project = self.factory.makeProduct()
        repositories = [
            self.factory.makeGitRepository(target=project) for _ in range(5)]
        self.assertContentEqual(
            repositories, self.repository_set.getRepositories(None, project))

    def test_getRepositories_inaccessible(self):
        # getRepositories only returns repositories that the given user can
        # see.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        public_repositories = [
            self.factory.makeGitRepository(owner=person, target=project)
            for _ in range(3)]
        other_person = self.factory.makePerson()
        private_repository = self.factory.makeGitRepository(
            owner=other_person, target=project,
            information_type=InformationType.USERDATA)
        self.assertContentEqual(
            public_repositories,
            self.repository_set.getRepositories(None, project))
        self.assertContentEqual(
            public_repositories,
            self.repository_set.getRepositories(person, project))
        self.assertContentEqual(
            public_repositories + [private_repository],
            self.repository_set.getRepositories(other_person, project))

    def test_getRepositories_order_by(self):
        # We can get a collection of all repositories with a given sort order.
        repositories = [self.factory.makeGitRepository() for _ in range(5)]
        modified_dates = [
            datetime(2010, 1, 1, tzinfo=pytz.UTC),
            datetime(2015, 1, 1, tzinfo=pytz.UTC),
            datetime(2014, 1, 1, tzinfo=pytz.UTC),
            datetime(2020, 1, 1, tzinfo=pytz.UTC),
            datetime(2019, 1, 1, tzinfo=pytz.UTC),
            ]
        for repository, modified_date in zip(repositories, modified_dates):
            removeSecurityProxy(repository).date_last_modified = modified_date
        removeSecurityProxy(repositories[0]).transitionToInformationType(
            InformationType.PRIVATESECURITY, repositories[0].registrant)
        self.assertEqual(
            [repositories[3], repositories[4], repositories[1],
             repositories[2], repositories[0]],
            list(self.repository_set.getRepositories(
                repositories[0].owner,
                order_by=GitListingSort.MOST_RECENTLY_CHANGED_FIRST)))
        self.assertEqual(
            [repositories[3], repositories[4], repositories[1]],
            list(self.repository_set.getRepositories(
                repositories[0].owner,
                order_by=GitListingSort.MOST_RECENTLY_CHANGED_FIRST,
                modified_since_date=datetime(2014, 12, 1, tzinfo=pytz.UTC))))
        self.assertEqual(
            [repositories[3], repositories[4], repositories[1],
             repositories[2]],
            list(self.repository_set.getRepositories(
                None, order_by=GitListingSort.MOST_RECENTLY_CHANGED_FIRST)))

    def test_getRepositoryVisibilityInfo_empty_repository_names(self):
        # If repository_names is empty, getRepositoryVisibilityInfo returns
        # an empty visible_repositories list.
        person = self.factory.makePerson(name="fred")
        info = self.repository_set.getRepositoryVisibilityInfo(
            person, person, repository_names=[])
        self.assertEqual("Fred", info["person_name"])
        self.assertEqual([], info["visible_repositories"])

    def test_getRepositoryVisibilityInfo(self):
        person = self.factory.makePerson(name="fred")
        owner = self.factory.makePerson()
        visible_repository = self.factory.makeGitRepository()
        invisible_repository = self.factory.makeGitRepository(
            owner=owner, information_type=InformationType.USERDATA)
        invisible_name = removeSecurityProxy(invisible_repository).unique_name
        repositories = [visible_repository.unique_name, invisible_name]

        with person_logged_in(owner):
            info = self.repository_set.getRepositoryVisibilityInfo(
                owner, person, repository_names=repositories)
        self.assertEqual("Fred", info["person_name"])
        self.assertEqual(
            [visible_repository.unique_name], info["visible_repositories"])

    def test_getRepositoryVisibilityInfo_unauthorised_user(self):
        # If the user making the API request cannot see one of the
        # repositories, that repository is not included in the results.
        person = self.factory.makePerson(name="fred")
        owner = self.factory.makePerson()
        visible_repository = self.factory.makeGitRepository()
        invisible_repository = self.factory.makeGitRepository(
            owner=owner, information_type=InformationType.USERDATA)
        invisible_name = removeSecurityProxy(invisible_repository).unique_name
        repositories = [visible_repository.unique_name, invisible_name]

        someone = self.factory.makePerson()
        with person_logged_in(someone):
            info = self.repository_set.getRepositoryVisibilityInfo(
                someone, person, repository_names=repositories)
        self.assertEqual("Fred", info["person_name"])
        self.assertEqual(
            [visible_repository.unique_name], info["visible_repositories"])

    def test_getRepositoryVisibilityInfo_anonymous(self):
        # Anonymous users are not allowed to see any repository visibility
        # information, even if the repository they are querying about is
        # public.
        person = self.factory.makePerson(name="fred")
        owner = self.factory.makePerson()
        visible_repository = self.factory.makeGitRepository(owner=owner)
        repositories = [visible_repository.unique_name]

        with person_logged_in(owner):
            info = self.repository_set.getRepositoryVisibilityInfo(
                None, person, repository_names=repositories)
        self.assertEqual({}, info)

    def test_getRepositoryVisibilityInfo_invalid_repository_name(self):
        # If an invalid repository name is specified, it is not included.
        person = self.factory.makePerson(name="fred")
        owner = self.factory.makePerson()
        visible_repository = self.factory.makeGitRepository(owner=owner)
        repositories = [
            visible_repository.unique_name,
            "invalid_repository_name"]

        with person_logged_in(owner):
            info = self.repository_set.getRepositoryVisibilityInfo(
                owner, person, repository_names=repositories)
        self.assertEqual("Fred", info["person_name"])
        self.assertEqual(
            [visible_repository.unique_name], info["visible_repositories"])

    def test_setDefaultRepository_refuses_person(self):
        # setDefaultRepository refuses if the target is a person.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=person)
        with person_logged_in(person):
            self.assertRaises(
                GitTargetError, self.repository_set.setDefaultRepository,
                person, repository)

    def test_setDefaultRepositoryForOwner_refuses_person(self):
        # setDefaultRepositoryForOwner refuses if the target is a person.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=person)
        with person_logged_in(person) as user:
            self.assertRaises(
                GitTargetError,
                self.repository_set.setDefaultRepositoryForOwner,
                person, person, repository, user)

    def test_setDefaultRepositoryForOwner_noop(self):
        # If a repository is already the target owner default, setting
        # the default again should no-op.
        owner = self.factory.makePerson()
        target = self.factory.makeProduct()
        repo = self.factory.makeGitRepository(owner=owner, target=target)
        with person_logged_in(owner):
            self.repository_set.setDefaultRepositoryForOwner(
                owner, target, repo, owner)
            self.assertEqual(
                repo,
                self.repository_set.getDefaultRepositoryForOwner(
                    owner, target))
            self.repository_set.setDefaultRepositoryForOwner(
                owner, target, repo, owner)
            self.assertEqual(
                repo,
                self.repository_set.getDefaultRepositoryForOwner(
                    owner, target))

    def test_setDefaultRepositoryForOwner_replaces_old(self):
        # If another repository is already the target owner default,
        # setting it overwrites.
        owner = self.factory.makePerson()
        target = self.factory.makeProduct()
        repo1 = self.factory.makeGitRepository(owner=owner, target=target)
        repo2 = self.factory.makeGitRepository(owner=owner, target=target)
        with person_logged_in(owner):
            self.repository_set.setDefaultRepositoryForOwner(
                owner, target, repo1, owner)
            self.assertEqual(
                repo1,
                self.repository_set.getDefaultRepositoryForOwner(
                    owner, target))
            self.assertTrue(repo1.owner_default)
            self.assertFalse(repo2.owner_default)
            self.repository_set.setDefaultRepositoryForOwner(
                owner, target, repo2, owner)
            self.assertEqual(
                repo2,
                self.repository_set.getDefaultRepositoryForOwner(
                    owner, target))
            self.assertFalse(repo1.owner_default)
            self.assertTrue(repo2.owner_default)

    def test_setDefaultRepository_noop(self):
        # If a repository is already the target default, setting the
        # default again should no-op.
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            self.repository_set.setDefaultRepository(project, repository)
            self.assertEqual(
                repository, self.repository_set.getDefaultRepository(project))
            self.repository_set.setDefaultRepository(project, repository)
            self.assertEqual(
                repository, self.repository_set.getDefaultRepository(project))

    def test_setDefaultRepository_replaces_old(self):
        # If another repository is already the target default, setting
        # it overwrites.
        project = self.factory.makeProduct()
        repo1 = self.factory.makeGitRepository(target=project)
        repo2 = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            self.repository_set.setDefaultRepository(project, repo1)
            self.assertEqual(
                repo1, self.repository_set.getDefaultRepository(project))
            self.assertTrue(repo1.target_default)
            self.assertFalse(repo2.target_default)
            self.repository_set.setDefaultRepository(project, repo2)
            self.assertEqual(
                repo2, self.repository_set.getDefaultRepository(project))
            self.assertFalse(repo1.target_default)
            self.assertTrue(repo2.target_default)


class TestGitRepositorySetDefaultsMixin:

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitRepositorySetDefaultsMixin, self).setUp()
        self.repository_set = getUtility(IGitRepositorySet)
        self.get_method = self.repository_set.getDefaultRepository
        self.set_method = (lambda target, repository, user:
            self.repository_set.setDefaultRepository(target, repository))

    def makeGitRepository(self, target):
        return self.factory.makeGitRepository(target=target)

    def test_default_repository_round_trip(self):
        # A target's default Git repository set using setDefaultRepository*
        # can be retrieved using getDefaultRepository*.
        target = self.makeTarget()
        repository = self.makeGitRepository(target)
        self.assertIsNone(self.get_method(target))
        with person_logged_in(self.getPersonForLogin(target)) as user:
            self.set_method(target, repository, user)
        self.assertEqual(repository, self.get_method(target))

    def test_set_default_repository_None(self):
        # setDefaultRepository*(target, None) clears the default.
        target = self.makeTarget()
        repository = self.makeGitRepository(target)
        with person_logged_in(self.getPersonForLogin(target)) as user:
            self.set_method(target, repository, user)
            self.set_method(target, None, user)
        self.assertIsNone(self.get_method(target))

    def test_set_default_repository_different_target(self):
        # setDefaultRepository* refuses if the repository is attached to a
        # different target.
        target = self.makeTarget()
        other_target = self.makeTarget(template=target)
        repository = self.makeGitRepository(other_target)
        with person_logged_in(self.getPersonForLogin(target)) as user:
            self.assertRaises(
                GitTargetError, self.set_method, target, repository, user)


class TestGitRepositorySetDefaultsProject(
    TestGitRepositorySetDefaultsMixin, TestCaseWithFactory):

    def makeTarget(self, template=None):
        return self.factory.makeProduct()

    @staticmethod
    def getPersonForLogin(target):
        return target.owner


class TestGitRepositorySetDefaultsPackage(
    TestGitRepositorySetDefaultsMixin, TestCaseWithFactory):

    def makeTarget(self, template=None):
        kwargs = {}
        if template is not None:
            kwargs["distribution"] = template.distribution
        return self.factory.makeDistributionSourcePackage(**kwargs)

    @staticmethod
    def getPersonForLogin(target):
        return target.distribution.owner


class TestGitRepositorySetDefaultsOCIProject(
    TestGitRepositorySetDefaultsMixin, TestCaseWithFactory):

    def makeTarget(self, template=None):
        kwargs = {}
        if template is not None:
            kwargs["pillar"] = template.pillar
        return self.factory.makeOCIProject(**kwargs)

    @staticmethod
    def getPersonForLogin(target):
        return target.pillar.owner


class TestGitRepositorySetDefaultsOwnerMixin(
    TestGitRepositorySetDefaultsMixin):

    def setUp(self):
        super(TestGitRepositorySetDefaultsOwnerMixin, self).setUp()
        self.person = self.factory.makePerson()
        self.get_method = partial(
            self.repository_set.getDefaultRepositoryForOwner, self.person)
        self.set_method = partial(
            self.repository_set.setDefaultRepositoryForOwner, self.person)

    def makeGitRepository(self, target):
        return self.factory.makeGitRepository(owner=self.person, target=target)

    def getPersonForLogin(self, target):
        return self.person

    def test_set_default_repository_for_owner_team_member(self):
        # A member of the owner team can use setDefaultRepositoryForOwner.
        target = self.makeTarget()
        team = self.factory.makeTeam(members=[self.person])
        repository = self.factory.makeGitRepository(owner=team, target=target)
        self.assertIsNone(
            self.repository_set.getDefaultRepositoryForOwner(team, target))
        with person_logged_in(self.person) as user:
            self.repository_set.setDefaultRepositoryForOwner(
                team, target, repository, user)
        self.assertEqual(
            repository,
            self.repository_set.getDefaultRepositoryForOwner(team, target))

    def test_set_default_repository_for_owner_not_team_member(self):
        # A non-member of the owner team cannot use
        # setDefaultRepositoryForOwner.
        target = self.makeTarget()
        team = self.factory.makeTeam()
        repository = self.factory.makeGitRepository(owner=team, target=target)
        self.assertIsNone(
            self.repository_set.getDefaultRepositoryForOwner(team, target))
        with person_logged_in(self.person) as user:
            self.assertRaises(
                Unauthorized, self.repository_set.setDefaultRepositoryForOwner,
                team, target, repository, user)


class TestGitRepositorySetDefaultsOwnerProject(
    TestGitRepositorySetDefaultsOwnerMixin,
    TestGitRepositorySetDefaultsProject):
    pass


class TestGitRepositorySetDefaultsOwnerPackage(
    TestGitRepositorySetDefaultsOwnerMixin,
    TestGitRepositorySetDefaultsPackage):
    pass


class TestGitRepositorySetDefaultsOwnerOCIProject(
    TestGitRepositorySetDefaultsOwnerMixin,
    TestGitRepositorySetDefaultsOCIProject):
    pass


class TestGitRepositoryWebservice(TestCaseWithFactory):
    """Tests for the webservice."""

    layer = DatabaseFunctionalLayer

    def test_repackRepository_owner(self):
        # Repository owner cannot repack
        hosting_fixture = self.useFixture(GitHostingFixture())
        owner_db = self.factory.makePerson()
        repository_db = self.factory.makeGitRepository(
            owner=owner_db, name="repository")

        with person_logged_in(owner_db):
            self.assertRaises(
                Unauthorized, getattr, repository_db, 'repackRepository')
        self.assertEqual(0, hosting_fixture.repackRepository.call_count)

    def test_repackRepository_admin(self):
        # Admins can trigger a repack
        hosting_fixture = self.useFixture(GitHostingFixture())
        owner_db = self.factory.makePerson()
        repository_db = self.factory.makeGitRepository(
            owner=owner_db, name="repository")
        admin = getUtility(ILaunchpadCelebrities).admin.teamowner
        with person_logged_in(admin):
            repository_db.repackRepository()
        self.assertEqual(
            [((repository_db.getInternalPath(),), {})],
            hosting_fixture.repackRepository.calls)
        self.assertEqual(1, hosting_fixture.repackRepository.call_count)

    def test_repackRepository_registry_expert(self):
        # Registry experts can trigger a repack
        hosting_fixture = self.useFixture(GitHostingFixture())
        admin = getUtility(ILaunchpadCelebrities).admin.teamowner
        person = self.factory.makePerson()
        owner_db = self.factory.makePerson()
        repository_db = self.factory.makeGitRepository(
            owner=owner_db, name="repository")
        with admin_logged_in():
            getUtility(ILaunchpadCelebrities).registry_experts.addMember(
                person, admin)
        with person_logged_in(person):
            repository_db.repackRepository()
        self.assertEqual(
            [((repository_db.getInternalPath(),), {})],
            hosting_fixture.repackRepository.calls)
        self.assertEqual(1, hosting_fixture.repackRepository.call_count)

    def test_repack_data(self):
        owner_db = self.factory.makePerson(name="person")
        project_db = self.factory.makeProduct(name="project")
        repository_db = self.factory.makeGitRepository(
            owner=owner_db, target=project_db, name="repository")
        webservice = webservice_for_person(
            repository_db.owner, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(repository_db)
        repository = webservice.get(repository_url).jsonBody()
        self.assertThat(repository, ContainsDict({
            'loose_object_count': Is(None),
            'pack_count': Is(None),
            'date_last_repacked': Is(None),
            'date_last_scanned': Is(None),
            }))

        repository_db = removeSecurityProxy(repository_db)
        repository_db.loose_object_count = 45
        repository_db.pack_count = 523
        repository_db.date_last_repacked = UTC_NOW
        repository_db.date_last_scanned = UTC_NOW

        repository = webservice.get(repository_url).jsonBody()

        self.assertThat(repository, ContainsDict({
            'loose_object_count': Equals(45),
            'pack_count': Equals(523),
            'date_last_repacked': Equals(UTC_NOW),
            'date_last_scanned': Equals(UTC_NOW),
            }))

    def test_git_gc_owner(self):
        # Repository owner cannot request a git GC run
        hosting_fixture = self.useFixture(GitHostingFixture())
        owner_db = self.factory.makePerson()
        repository_db = self.factory.makeGitRepository(
            owner=owner_db, name="repository")

        with person_logged_in(owner_db):
            self.assertRaises(
                Unauthorized, getattr, repository_db, 'collectGarbage')
        self.assertEqual(0, hosting_fixture.collectGarbage.call_count)

    def test_git_gc_admin(self):
        # Admins can trigger a git GC run
        hosting_fixture = self.useFixture(GitHostingFixture())
        owner_db = self.factory.makePerson()
        repository_db = self.factory.makeGitRepository(
            owner=owner_db, name="repository")
        admin = getUtility(ILaunchpadCelebrities).admin.teamowner
        with person_logged_in(admin):
            repository_db.collectGarbage()
        self.assertEqual(
            [((repository_db.getInternalPath(),), {})],
            hosting_fixture.collectGarbage.calls)
        self.assertEqual(1, hosting_fixture.collectGarbage.call_count)

    def test_git_gc_registry_expert(self):
        # Registry experts can trigger a Git GC run
        hosting_fixture = self.useFixture(GitHostingFixture())
        admin = getUtility(ILaunchpadCelebrities).admin.teamowner
        person = self.factory.makePerson()
        owner_db = self.factory.makePerson()
        repository_db = self.factory.makeGitRepository(
            owner=owner_db, name="repository")
        with admin_logged_in():
            getUtility(ILaunchpadCelebrities).registry_experts.addMember(
                person, admin)
        with person_logged_in(person):
            repository_db.collectGarbage()
        self.assertEqual(
            [((repository_db.getInternalPath(),), {})],
            hosting_fixture.collectGarbage.calls)
        self.assertEqual(1, hosting_fixture.collectGarbage.call_count)

    def test_urls(self):
        owner_db = self.factory.makePerson(name="person")
        project_db = self.factory.makeProduct(name="project")
        repository_db = self.factory.makeGitRepository(
            owner=owner_db, target=project_db, name="repository")
        webservice = webservice_for_person(
            repository_db.owner, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(repository_db)
        repository = webservice.get(repository_url).jsonBody()
        self.assertEqual(
            "https://git.launchpad.test/~person/project/+git/repository",
            repository["git_https_url"])
        self.assertEqual(
            "git+ssh://git.launchpad.test/~person/project/+git/repository",
            repository["git_ssh_url"])

    def assertNewWorks(self, target_db):
        hosting_fixture = self.useFixture(GitHostingFixture())
        if IPerson.providedBy(target_db):
            owner_db = target_db
        else:
            owner_db = self.factory.makePerson()
        owner_url = api_url(owner_db)
        target_url = api_url(target_db)
        name = "repository"
        webservice = webservice_for_person(
            owner_db, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            "/+git", "new", owner=owner_url, target=target_url, name=name)
        self.assertEqual(201, response.status)
        repository = webservice.get(response.getHeader("Location")).jsonBody()
        self.assertThat(repository, ContainsDict({
            "id": IsInstance(int),
            "repository_type": Equals("Hosted"),
            "registrant_link": EndsWith(owner_url),
            "owner_link": EndsWith(owner_url),
            "target_link": EndsWith(target_url),
            "name": Equals(name),
            "owner_default": Is(False),
            "target_default": Is(False),
            }))
        self.assertEqual(1, hosting_fixture.create.call_count)

    def test_new_project(self):
        self.assertNewWorks(self.factory.makeProduct())

    def test_new_package(self):
        self.assertNewWorks(self.factory.makeDistributionSourcePackage())

    def test_new_person(self):
        self.assertNewWorks(self.factory.makePerson())

    def test_new_repo_not_owner(self):
        non_ascii_name = u'André Luís Lopes'
        other_user = self.factory.makePerson(displayname=non_ascii_name)
        owner_url = api_url(other_user)
        webservice_user = self.factory.makePerson()
        name = "repository"
        webservice = webservice_for_person(
            webservice_user, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            "/+git", "new", owner=owner_url, target=owner_url, name=name)
        self.assertEqual(400, response.status)
        self.assertIn(u'cannot create Git repositories owned by'
                      u' André Luís Lopes', response.body.decode('utf-8'))

    def assertGetRepositoriesWorks(self, target_db):
        if IPerson.providedBy(target_db):
            owner_db = target_db
        else:
            owner_db = self.factory.makePerson()
        owner_url = api_url(owner_db)
        target_url = api_url(target_db)

        repos_db = []
        repos_url = []

        webservice = webservice_for_person(
            owner_db, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"

        def create_repository():
            with admin_logged_in():
                repo = self.factory.makeGitRepository(
                    target=target_db, owner=owner_db)
                repos_db.append(repo)
                repos_url.append(api_url(repo))

        def verify_getRepositories():
            response = webservice.named_get(
                "/+git", "getRepositories", user=owner_url, target=target_url)
            self.assertEqual(200, response.status)
            self.assertContentEqual(
                [webservice.getAbsoluteUrl(url) for url in repos_url],
                [entry["self_link"]
                 for entry in response.jsonBody()["entries"]])

        verify_getRepositories()
        recorder1, recorder2 = record_two_runs(
            verify_getRepositories, create_repository, 2)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_getRepositories_project(self):
        self.assertGetRepositoriesWorks(self.factory.makeProduct())

    def test_getRepositories_package(self):
        self.assertGetRepositoriesWorks(
            self.factory.makeDistributionSourcePackage())

    def test_getRepositories_personal(self):
        self.assertGetRepositoriesWorks(self.factory.makePerson())

    def test_getRepositoriesForRepack(self):
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_get(
            "/+git", "getRepositoriesForRepack", limit=3)
        self.assertEqual(200, response.status)
        self.assertEqual([], response.jsonBody())
        with person_logged_in(person):
            repo = []
            for i in range(5):
                repo.append(self.factory.makeGitRepository())
            for i in range(3):
                removeSecurityProxy(repo[i]).loose_object_count = 7000 + i
                removeSecurityProxy(repo[i]).pack_count = 43

        # We have a total of 3 candidates now
        response = webservice.named_get(
            "/+git", "getRepositoriesForRepack", limit=10)
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [7002, 7001, 7000],
            [entry['loose_object_count']
             for entry in response.jsonBody()])

        # When we have 5 repack candidates but limit at 4
        # we should only get back 4 repos from the query.
        removeSecurityProxy(repo[3]).loose_object_count = 7003
        removeSecurityProxy(repo[4]).loose_object_count = 7004
        response = webservice.named_get(
            "/+git", "getRepositoriesForRepack", limit=4)
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            [7004, 7003, 7002, 7001],
            [entry['loose_object_count']
             for entry in response.jsonBody()])

    def test_getNumberRepositoriesForRepack(self):
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_get(
            "/+git", "countRepositoriesForRepack")
        self.assertEqual(200, response.status)
        self.assertEqual(0, response.jsonBody())
        with person_logged_in(person):
            for _ in range(5):
                self.factory.makeGitRepository()
            for _ in range(3):
                repo = self.factory.makeGitRepository()
                removeSecurityProxy(repo).loose_object_count = 7000
                removeSecurityProxy(repo).pack_count = 43

        # We have a total of 3 candidates now
        response = webservice.named_get(
            "/+git", "countRepositoriesForRepack")
        self.assertEqual(200, response.status)
        self.assertEqual(3, response.jsonBody())

    def test_get_without_default_branch(self):
        # Ensure we're not getting an error when calling
        # GET on the Webservice when a Git Repo exists in the DB
        # with a NULL default branch
        repository = self.factory.makeGitRepository()
        webservice = webservice_for_person(
            repository.owner, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(repository)
        response = webservice.get(repository_url).jsonBody()
        self.assertIsNone(response["default_branch"])

    def test_set_information_type(self):
        # The repository owner can change the information type.
        repository_db = self.factory.makeGitRepository()
        webservice = webservice_for_person(
            repository_db.owner, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(repository_db)
        response = webservice.patch(
            repository_url, "application/json",
            json.dumps({"information_type": "Public Security"}))
        self.assertEqual(209, response.status)
        with person_logged_in(ANONYMOUS):
            self.assertEqual(
                InformationType.PUBLICSECURITY, repository_db.information_type)

    def test_set_information_type_other_person(self):
        # An unrelated user cannot change the information type.
        repository_db = self.factory.makeGitRepository()
        webservice = webservice_for_person(
            self.factory.makePerson(), permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(repository_db)
        response = webservice.patch(
            repository_url, "application/json",
            json.dumps({"information_type": "Public Security"}))
        self.assertEqual(401, response.status)
        with person_logged_in(ANONYMOUS):
            self.assertEqual(
                InformationType.PUBLIC, repository_db.information_type)

    def test_set_target(self):
        # The repository owner can move the repository to another target;
        # this redirects to the new location.
        repository_db = self.factory.makeGitRepository()
        new_project_db = self.factory.makeProduct()
        webservice = webservice_for_person(
            repository_db.owner, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(repository_db)
            new_project_url = api_url(new_project_db)
        response = webservice.patch(
            repository_url, "application/json",
            json.dumps({"target_link": new_project_url}))
        self.assertEqual(301, response.status)
        with person_logged_in(ANONYMOUS):
            self.assertEqual(
                webservice.getAbsoluteUrl(api_url(repository_db)),
                response.getHeader("Location"))
            self.assertEqual(new_project_db, repository_db.target)

    def test_set_target_other_person(self):
        # An unrelated person cannot change the target.
        project_db = self.factory.makeProduct()
        repository_db = self.factory.makeGitRepository(target=project_db)
        new_project_db = self.factory.makeProduct()
        webservice = webservice_for_person(
            self.factory.makePerson(), permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(repository_db)
            new_project_url = api_url(new_project_db)
        response = webservice.patch(
            repository_url, "application/json",
            json.dumps({"target_link": new_project_url}))
        self.assertEqual(401, response.status)
        with person_logged_in(ANONYMOUS):
            self.assertEqual(project_db, repository_db.target)

    def test_set_owner(self):
        # The repository owner can reassign the repository to a team they're
        # a member of; this redirects to the new location.
        repository_db = self.factory.makeGitRepository()
        new_owner_db = self.factory.makeTeam(members=[repository_db.owner])
        webservice = webservice_for_person(
            repository_db.owner, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(repository_db)
            new_owner_url = api_url(new_owner_db)
        response = webservice.patch(
            repository_url, "application/json",
            json.dumps({"owner_link": new_owner_url}))
        self.assertEqual(301, response.status)
        with person_logged_in(ANONYMOUS):
            self.assertEqual(
                webservice.getAbsoluteUrl(api_url(repository_db)),
                response.getHeader("Location"))
            self.assertEqual(new_owner_db, repository_db.owner)

    def test_set_owner_other_person(self):
        # An unrelated person cannot change the owner.
        owner_db = self.factory.makePerson()
        repository_db = self.factory.makeGitRepository(owner=owner_db)
        new_owner_db = self.factory.makeTeam()
        webservice = webservice_for_person(
            new_owner_db.teamowner, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(repository_db)
            new_owner_url = api_url(new_owner_db)
        response = webservice.patch(
            repository_url, "application/json",
            json.dumps({"owner_link": new_owner_url}))
        self.assertEqual(401, response.status)
        with person_logged_in(ANONYMOUS):
            self.assertEqual(owner_db, repository_db.owner)

    def test_getRefByPath(self):
        repository_db = self.factory.makeGitRepository()
        ref_dbs = self.factory.makeGitRefs(
            repository=repository_db, paths=["refs/heads/a", "refs/heads/b"])
        removeSecurityProxy(repository_db)._default_branch = "refs/heads/a"
        repository_url = api_url(repository_db)
        ref_urls = [api_url(ref_db) for ref_db in ref_dbs]
        webservice = webservice_for_person(
            repository_db.owner, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        for path, expected_ref_url in (
                ("a", ref_urls[0]),
                ("refs/heads/a", ref_urls[0]),
                ("b", ref_urls[1]),
                ("refs/heads/b", ref_urls[1]),
                ("HEAD", "%s/+ref/HEAD" % repository_url),
                ):
            response = webservice.named_get(
                repository_url, "getRefByPath", path=path)
            self.assertEqual(200, response.status)
            self.assertEqual(
                webservice.getAbsoluteUrl(expected_ref_url),
                response.jsonBody()["self_link"])
        response = webservice.named_get(
            repository_url, "getRefByPath", path="c")
        self.assertEqual(200, response.status)
        self.assertIsNone(response.jsonBody())

    def test_getRefByPath_query_count(self):
        repository_db = self.factory.makeGitRepository()
        ref_dbs = self.factory.makeGitRefs(
            repository=repository_db, paths=[
                "refs/heads/devel", "refs/heads/master"])

        with StormStatementRecorder() as recorder:
            ref = repository_db.getRefByPath("master")
            self.assertEqual(ref_dbs[1], ref)
            self.assertEqual(1, recorder.count)

    def test_subscribe(self):
        # A user can subscribe to a repository.
        repository_db = self.factory.makeGitRepository()
        subscriber_db = self.factory.makePerson()
        webservice = webservice_for_person(
            subscriber_db, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(repository_db)
            subscriber_url = api_url(subscriber_db)
        response = webservice.named_post(
            repository_url, "subscribe", person=subscriber_url,
            notification_level="Branch attribute notifications only",
            max_diff_lines="Don't send diffs", code_review_level="No email")
        self.assertEqual(200, response.status)
        with person_logged_in(ANONYMOUS):
            subscription_db = repository_db.getSubscription(subscriber_db)
            self.assertIsNotNone(subscription_db)
            self.assertThat(
                response.jsonBody()["self_link"],
                EndsWith(api_url(subscription_db)))

    def _makeSubscription(self, repository, subscriber):
        with person_logged_in(subscriber):
            return repository.subscribe(
                person=subscriber,
                notification_level=(
                    BranchSubscriptionNotificationLevel.ATTRIBUTEONLY),
                max_diff_lines=BranchSubscriptionDiffSize.NODIFF,
                code_review_level=CodeReviewNotificationLevel.NOEMAIL,
                subscribed_by=subscriber)

    def test_getSubscription(self):
        # It is possible to get a single subscription via the webservice.
        repository_db = self.factory.makeGitRepository()
        subscriber_db = self.factory.makePerson()
        subscription_db = self._makeSubscription(repository_db, subscriber_db)
        with person_logged_in(subscriber_db):
            repository_url = api_url(repository_db)
            subscriber_url = api_url(subscriber_db)
            subscription_url = api_url(subscription_db)
        webservice = webservice_for_person(
            subscriber_db, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_get(
            repository_url, "getSubscription", person=subscriber_url)
        self.assertEqual(200, response.status)
        self.assertThat(
            response.jsonBody()["self_link"], EndsWith(subscription_url))

    def test_edit_subscription(self):
        # An existing subscription can be edited via the webservice, by
        # subscribing the same person again with different details.
        repository_db = self.factory.makeGitRepository()
        subscriber_db = self.factory.makePerson()
        self._makeSubscription(repository_db, subscriber_db)
        with person_logged_in(subscriber_db):
            repository_url = api_url(repository_db)
            subscriber_url = api_url(subscriber_db)
        webservice = webservice_for_person(
            subscriber_db, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            repository_url, "subscribe", person=subscriber_url,
            notification_level="No email",
            max_diff_lines="Send entire diff",
            code_review_level="Status changes only")
        self.assertEqual(200, response.status)
        with person_logged_in(subscriber_db):
            self.assertThat(
                repository_db.getSubscription(subscriber_db),
                MatchesStructure.byEquality(
                    person=subscriber_db,
                    notification_level=(
                        BranchSubscriptionNotificationLevel.NOEMAIL),
                    max_diff_lines=BranchSubscriptionDiffSize.WHOLEDIFF,
                    review_level=CodeReviewNotificationLevel.STATUS,
                    ))
        repository = webservice.get(repository_url).jsonBody()
        subscribers = webservice.get(
            repository["subscribers_collection_link"]).jsonBody()
        self.assertEqual(2, len(subscribers["entries"]))
        with person_logged_in(subscriber_db):
            self.assertContentEqual(
                [repository_db.owner.name, subscriber_db.name],
                [subscriber["name"] for subscriber in subscribers["entries"]])

    def test_unsubscribe(self):
        # It is possible to unsubscribe via the webservice.
        repository_db = self.factory.makeGitRepository()
        subscriber_db = self.factory.makePerson()
        self._makeSubscription(repository_db, subscriber_db)
        with person_logged_in(subscriber_db):
            repository_url = api_url(repository_db)
            subscriber_url = api_url(subscriber_db)
        webservice = webservice_for_person(
            subscriber_db, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            repository_url, "unsubscribe", person=subscriber_url)
        self.assertEqual(200, response.status)
        with person_logged_in(subscriber_db):
            self.assertNotIn(subscriber_db, repository_db.subscribers)

    def test_landing_candidates(self):
        bmp_db = self.factory.makeBranchMergeProposalForGit()
        with person_logged_in(bmp_db.registrant):
            bmp_url = api_url(bmp_db)
            repository_url = api_url(bmp_db.target_git_repository)
        webservice = webservice_for_person(
            bmp_db.registrant, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        repository = webservice.get(repository_url).jsonBody()
        landing_candidates = webservice.get(
            repository["landing_candidates_collection_link"]).jsonBody()
        self.assertEqual(1, len(landing_candidates["entries"]))
        self.assertThat(
            landing_candidates["entries"][0]["self_link"], EndsWith(bmp_url))

    def test_landing_candidates_constant_queries(self):
        project = self.factory.makeProduct()
        with person_logged_in(project.owner):
            repository = self.factory.makeGitRepository(target=project)
            repository_url = api_url(repository)
            webservice = webservice_for_person(
                project.owner, permission=OAuthPermission.WRITE_PRIVATE)

        def create_mp():
            with admin_logged_in():
                [target] = self.factory.makeGitRefs(repository=repository)
                [source] = self.factory.makeGitRefs(
                    target=project,
                    information_type=InformationType.PRIVATESECURITY)
                self.factory.makeBranchMergeProposalForGit(
                    source_ref=source, target_ref=target)

        def list_mps():
            webservice.get(repository_url + "/landing_candidates")

        list_mps()
        recorder1, recorder2 = record_two_runs(list_mps, create_mp, 2)
        self.assertThat(recorder1, HasQueryCount(LessThan(40)))
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_landing_targets(self):
        bmp_db = self.factory.makeBranchMergeProposalForGit()
        with person_logged_in(bmp_db.registrant):
            bmp_url = api_url(bmp_db)
            repository_url = api_url(bmp_db.source_git_repository)
        webservice = webservice_for_person(
            bmp_db.registrant, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        repository = webservice.get(repository_url).jsonBody()
        landing_targets = webservice.get(
            repository["landing_targets_collection_link"]).jsonBody()
        self.assertEqual(1, len(landing_targets["entries"]))
        self.assertThat(
            landing_targets["entries"][0]["self_link"], EndsWith(bmp_url))

    def test_landing_targets_constant_queries(self):
        project = self.factory.makeProduct()
        with person_logged_in(project.owner):
            repository = self.factory.makeGitRepository(target=project)
            repository_url = api_url(repository)
            webservice = webservice_for_person(
                project.owner, permission=OAuthPermission.WRITE_PRIVATE)

        def create_mp():
            with admin_logged_in():
                [source] = self.factory.makeGitRefs(repository=repository)
                [target] = self.factory.makeGitRefs(
                    target=project,
                    information_type=InformationType.PRIVATESECURITY)
                self.factory.makeBranchMergeProposalForGit(
                    source_ref=source, target_ref=target)

        def list_mps():
            webservice.get(repository_url + "/landing_targets")

        list_mps()
        recorder1, recorder2 = record_two_runs(list_mps, create_mp, 2)
        self.assertThat(recorder1, HasQueryCount(LessThan(30)))
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_dependent_landings(self):
        [ref] = self.factory.makeGitRefs()
        bmp_db = self.factory.makeBranchMergeProposalForGit(
            prerequisite_ref=ref)
        with person_logged_in(bmp_db.registrant):
            bmp_url = api_url(bmp_db)
            repository_url = api_url(ref.repository)
        webservice = webservice_for_person(
            bmp_db.registrant, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        repository = webservice.get(repository_url).jsonBody()
        dependent_landings = webservice.get(
            repository["dependent_landings_collection_link"]).jsonBody()
        self.assertEqual(1, len(dependent_landings["entries"]))
        self.assertThat(
            dependent_landings["entries"][0]["self_link"], EndsWith(bmp_url))

    def test_getRules(self):
        repository = self.factory.makeGitRepository()
        rules = [
            self.factory.makeGitRule(
                repository=repository, ref_pattern="refs/heads/stable/*"),
            self.factory.makeGitRule(
                repository=repository, ref_pattern="refs/heads/*"),
            ]
        self.factory.makeGitRuleGrant(
            rule=rules[0], grantee=GitGranteeType.REPOSITORY_OWNER,
            can_create=True, can_force_push=True)
        grantees = [self.factory.makePerson() for _ in range(2)]
        for grantee in grantees:
            self.factory.makeGitRuleGrant(
                rule=rules[1], grantee=grantee, can_push=True)
        with person_logged_in(repository.owner):
            repository_url = api_url(repository)
            grantee_urls = [api_url(grantee) for grantee in grantees]
        webservice = webservice_for_person(
            repository.owner, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_get(repository_url, "getRules")
        self.assertThat(response.jsonBody(), MatchesListwise([
            MatchesDict({
                "ref_pattern": Equals("refs/heads/stable/*"),
                "grants": MatchesSetwise(
                    MatchesDict({
                        "grantee_type": Equals("Repository owner"),
                        "grantee_link": Is(None),
                        "can_create": Is(True),
                        "can_push": Is(False),
                        "can_force_push": Is(True),
                        }),
                    ),
                }),
            MatchesDict({
                "ref_pattern": Equals("refs/heads/*"),
                "grants": MatchesSetwise(*(
                    MatchesDict({
                        "grantee_type": Equals("Person"),
                        "grantee_link": Equals(
                            webservice.getAbsoluteUrl(grantee_url)),
                        "can_create": Is(False),
                        "can_push": Is(True),
                        "can_force_push": Is(False),
                        })
                    for grantee_url in grantee_urls)),
                }),
            ]))

    def test_setRules(self):
        repository = self.factory.makeGitRepository()
        owner = repository.owner
        grantee = self.factory.makePerson()
        with person_logged_in(owner):
            repository_url = api_url(repository)
            grantee_url = api_url(grantee)
        webservice = webservice_for_person(
            owner, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            repository_url, "setRules",
            rules=[
                {
                    "ref_pattern": "refs/heads/stable/*",
                    "grants": [
                        {
                            "grantee_type": "Repository owner",
                            "can_create": True,
                            "can_force_push": True,
                            },
                        ],
                    },
                {
                    "ref_pattern": "refs/heads/*",
                    "grants": [
                        {
                            "grantee_type": "Person",
                            "grantee_link": grantee_url,
                            "can_push": True,
                            },
                        ],
                    },
                ])
        self.assertEqual(200, response.status)
        with person_logged_in(owner):
            self.assertThat(list(repository.rules), MatchesListwise([
                MatchesStructure(
                    repository=Equals(repository),
                    ref_pattern=Equals("refs/heads/stable/*"),
                    creator=Equals(owner),
                    grants=MatchesSetwise(
                        MatchesStructure(
                            grantor=Equals(owner),
                            grantee_type=Equals(
                                GitGranteeType.REPOSITORY_OWNER),
                            grantee=Is(None),
                            can_create=Is(True),
                            can_push=Is(False),
                            can_force_push=Is(True)))),
                MatchesStructure(
                    repository=Equals(repository),
                    ref_pattern=Equals("refs/heads/*"),
                    creator=Equals(owner),
                    grants=MatchesSetwise(
                        MatchesStructure(
                            grantor=Equals(owner),
                            grantee_type=Equals(GitGranteeType.PERSON),
                            grantee=Equals(grantee),
                            can_create=Is(False),
                            can_push=Is(True),
                            can_force_push=Is(False)))),
                ]))

    def test_checkRefPermissions(self):
        repository = self.factory.makeGitRepository()
        owner = repository.owner
        grantees = [self.factory.makePerson() for _ in range(2)]
        master_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/master")
        self.factory.makeGitRuleGrant(
            rule=master_rule, grantee=grantees[0], can_create=True)
        self.factory.makeGitRuleGrant(
            rule=master_rule, grantee=grantees[1], can_push=True)
        self.factory.makeGitRuleGrant(
            repository=repository, ref_pattern="refs/heads/*",
            grantee=grantees[1], can_force_push=True)
        with person_logged_in(owner):
            repository_url = api_url(repository)
            owner_url = api_url(owner)
            grantee_urls = [api_url(grantee) for grantee in grantees]
        webservice = webservice_for_person(
            owner, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_get(
            repository_url, "checkRefPermissions", person=owner_url,
            paths=["refs/heads/master", "refs/heads/next", "refs/other"])
        self.assertThat(response.jsonBody(), MatchesDict({
            "refs/heads/master": Equals(["create", "push"]),
            "refs/heads/next": Equals(["create", "push"]),
            "refs/other": Equals(["create", "push", "force-push"]),
            }))
        response = webservice.named_get(
            repository_url, "checkRefPermissions", person=grantee_urls[0],
            paths=["refs/heads/master", "refs/heads/next", "refs/other"])
        self.assertThat(response.jsonBody(), MatchesDict({
            "refs/heads/master": Equals(["create"]),
            "refs/heads/next": Equals([]),
            "refs/other": Equals([]),
            }))
        response = webservice.named_get(
            repository_url, "checkRefPermissions", person=grantee_urls[1],
            paths=["refs/heads/master", "refs/heads/next", "refs/other"])
        self.assertThat(response.jsonBody(), MatchesDict({
            "refs/heads/master": Equals(["push"]),
            "refs/heads/next": Equals(["push", "force-push"]),
            "refs/other": Equals([]),
            }))

    def test_issueAccessToken(self):
        # A user can request an access token via the webservice API.
        self.pushConfig("codehosting", git_macaroon_secret_key="some-secret")
        repository = self.factory.makeGitRepository()
        # Write access to the repository isn't checked at this stage
        # (although the access token will only be useful if the user has
        # some kind of write access).
        requester = self.factory.makePerson()
        with person_logged_in(requester):
            repository_url = api_url(repository)
        webservice = webservice_for_person(
            requester, permission=OAuthPermission.WRITE_PUBLIC,
            default_api_version="devel")
        response = webservice.named_post(repository_url, "issueAccessToken")
        self.assertEqual(200, response.status)
        macaroon = Macaroon.deserialize(response.jsonBody())
        with person_logged_in(ANONYMOUS):
            self.assertThat(macaroon, MatchesStructure(
                location=Equals(config.vhost.mainsite.hostname),
                identifier=Equals("git-repository"),
                caveats=MatchesListwise([
                    MatchesStructure.byEquality(
                        caveat_id="lp.git-repository %s" % repository.id),
                    MatchesStructure(
                        caveat_id=StartsWith(
                            "lp.principal.openid-identifier ")),
                    MatchesStructure(caveat_id=StartsWith("lp.expires ")),
                    ])))

    def test_issueAccessToken_anonymous(self):
        # An anonymous user cannot request an access token via the
        # webservice API.
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.owner):
            repository_url = api_url(repository)
        webservice = webservice_for_person(None, default_api_version="devel")
        response = webservice.named_post(repository_url, "issueAccessToken")
        self.assertEqual(401, response.status)
        self.assertEqual(
            b"git-repository macaroons may only be issued for a logged-in "
            b"user.", response.body)


class TestGitRepositoryMacaroonIssuer(MacaroonTestMixin, TestCaseWithFactory):
    """Test GitRepository macaroon issuing and verification."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitRepositoryMacaroonIssuer, self).setUp()
        self.pushConfig("codehosting", git_macaroon_secret_key="some-secret")

    def test_issueMacaroon_refuses_branch(self):
        branch = self.factory.makeAnyBranch()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        self.assertRaises(
            ValueError, removeSecurityProxy(issuer).issueMacaroon,
            branch, user=branch.owner)

    def test_issueMacaroon_good(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        naked_account = removeSecurityProxy(repository.owner).account
        identifier = naked_account.openid_identifiers.any().identifier
        macaroon = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        now = get_transaction_timestamp(Store.of(repository))
        expires = now + timedelta(days=7)
        self.assertThat(macaroon, MatchesStructure(
            location=Equals(config.vhost.mainsite.hostname),
            identifier=Equals("git-repository"),
            caveats=MatchesListwise([
                MatchesStructure.byEquality(
                    caveat_id="lp.git-repository %s" % repository.id),
                MatchesStructure.byEquality(
                    caveat_id=(
                        "lp.principal.openid-identifier %s" % identifier)),
                MatchesStructure.byEquality(
                    caveat_id="lp.expires %s" % (
                        expires.strftime("%Y-%m-%dT%H:%M:%S.%f"))),
                ])))

    def test_issueMacaroon_expiry_feature_flag(self):
        self.useFixture(FeatureFixture(
            {"code.git.access_token_expiry": "3600"}))
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        macaroon = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        now = get_transaction_timestamp(Store.of(repository))
        expires = now + timedelta(hours=1)
        self.assertThat(macaroon, MatchesStructure(
            caveats=AnyMatch(
                MatchesStructure.byEquality(
                    caveat_id="lp.expires %s" % (
                        expires.strftime("%Y-%m-%dT%H:%M:%S.%f"))))))

    def test_issueMacaroon_no_user(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        self.assertRaises(
            Unauthorized,
            removeSecurityProxy(issuer).issueMacaroon, repository)

    def test_issueMacaroon_not_via_authserver(self):
        repository = self.factory.makeGitRepository()
        private_root = getUtility(IPrivateApplication)
        authserver = AuthServerAPIView(private_root.authserver, TestRequest())
        self.assertEqual(
            faults.PermissionDenied(),
            authserver.issueMacaroon(
                "git-repository", "GitRepository", repository))

    def test_verifyMacaroon_good(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        macaroon = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        self.assertMacaroonVerifies(
            issuer, macaroon, repository, user=repository.owner)

    def test_verifyMacaroon_wrong_location(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        macaroon = Macaroon(
            location="another-location",
            key=removeSecurityProxy(issuer)._root_secret)
        self.assertMacaroonDoesNotVerify(
            ["Macaroon has unknown location 'another-location'."],
            issuer, macaroon, repository, user=repository.owner)

    def test_verifyMacaroon_wrong_key(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        macaroon = Macaroon(
            location=config.vhost.mainsite.hostname, key="another-secret")
        self.assertMacaroonDoesNotVerify(
            ["Signatures do not match"],
            issuer, macaroon, repository, user=repository.owner)

    def test_verifyMacaroon_wrong_repository(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        macaroon = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        self.assertMacaroonDoesNotVerify(
            ["Caveat check for 'lp.git-repository %s' failed." %
             repository.id],
            issuer, macaroon, self.factory.makeGitRepository(),
            user=repository.owner)

    def test_verifyMacaroon_multiple_repository_caveats(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        macaroon = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        macaroon.add_first_party_caveat("lp.git-repository another")
        self.assertMacaroonDoesNotVerify(
            ["Multiple 'lp.git-repository' caveats are not allowed."],
            issuer, macaroon, repository, user=repository.owner)

    def test_verifyMacaroon_wrong_user(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        naked_account = removeSecurityProxy(repository.owner).account
        identifier = naked_account.openid_identifiers.any().identifier
        macaroon = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        self.assertMacaroonDoesNotVerify(
            ["Caveat check for 'lp.principal.openid-identifier %s' failed." %
             identifier],
            issuer, macaroon, repository, user=self.factory.makePerson())

    def test_verifyMacaroon_inactive_account(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        macaroon = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        naked_account = removeSecurityProxy(repository.owner).account
        identifier = naked_account.openid_identifiers.any().identifier
        with admin_logged_in():
            repository.owner.setAccountStatus(
                AccountStatus.SUSPENDED, None, "Bye")
        self.assertMacaroonDoesNotVerify(
            ["Caveat check for 'lp.principal.openid-identifier %s' failed." %
             identifier],
            issuer, macaroon, repository, user=repository.owner)

    def test_verifyMacaroon_closed_account(self):
        # A closed account no longer has an OpenID identifier, so the
        # corresponding caveat doesn't match.
        repository = self.factory.makeGitRepository()
        owner = repository.owner
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        naked_account = removeSecurityProxy(owner).account
        identifier = naked_account.openid_identifiers.any().identifier
        macaroon = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=owner)
        IStore(OpenIdIdentifier).find(
            OpenIdIdentifier,
            OpenIdIdentifier.account_id == owner.account.id).remove()
        self.assertMacaroonDoesNotVerify(
            ["Caveat check for 'lp.principal.openid-identifier %s' failed." %
             identifier],
            issuer, macaroon, repository, user=owner)

    def test_verifyMacaroon_multiple_openid_identifier_caveats(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        macaroon = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        macaroon.add_first_party_caveat(
            "lp.principal.openid-identifier another")
        self.assertMacaroonDoesNotVerify(
            ["Multiple 'lp.principal.openid-identifier' caveats are not "
             "allowed."],
            issuer, macaroon, repository, user=repository.owner)

    def test_verifyMacaroon_expired(self):
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        macaroon = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        now = get_transaction_timestamp(Store.of(repository))
        self.useFixture(MockPatch(
            "lp.code.model.gitrepository.get_transaction_timestamp",
            lambda _: now + timedelta(days=8)))
        self.assertMacaroonDoesNotVerify(
            ["Caveat check for '%s' failed." %
             find_caveats_by_name(macaroon, "lp.expires")[0].caveat_id],
            issuer, macaroon, repository, user=repository.owner)

    def test_verifyMacaroon_multiple_expires_caveats(self):
        # If somebody attaches another expires caveat to the macaroon,
        # that's OK; we just take the strictest.
        repository = self.factory.makeGitRepository()
        issuer = getUtility(IMacaroonIssuer, "git-repository")
        macaroon1 = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        macaroon2 = removeSecurityProxy(issuer).issueMacaroon(
            repository, user=repository.owner)
        now = get_transaction_timestamp(Store.of(repository))
        expires1 = now + timedelta(days=1)
        expires2 = now + timedelta(days=14)
        macaroon1.add_first_party_caveat(
            "lp.expires " + expires1.strftime("%Y-%m-%dT%H:%M:%S.%f"))
        macaroon2.add_first_party_caveat(
            "lp.expires " + expires2.strftime("%Y-%m-%dT%H:%M:%S.%f"))
        self.assertMacaroonVerifies(
            issuer, macaroon1, repository, user=repository.owner)
        self.assertMacaroonVerifies(
            issuer, macaroon2, repository, user=repository.owner)
        with MockPatch(
                "lp.code.model.gitrepository.get_transaction_timestamp",
                lambda _: now + timedelta(days=4)):
            self.assertMacaroonDoesNotVerify(
                ["Caveat check for '%s' failed." %
                 find_caveats_by_name(macaroon1, "lp.expires")[1].caveat_id],
                issuer, macaroon1, repository, user=repository.owner)
            self.assertMacaroonVerifies(
                issuer, macaroon2, repository, user=repository.owner)
        with MockPatch(
                "lp.code.model.gitrepository.get_transaction_timestamp",
                lambda _: now + timedelta(days=8)):
            self.assertMacaroonDoesNotVerify(
                ["Caveat check for '%s' failed." %
                 find_caveats_by_name(macaroon1, "lp.expires")[0].caveat_id,
                 "Caveat check for '%s' failed." %
                 find_caveats_by_name(macaroon1, "lp.expires")[1].caveat_id],
                issuer, macaroon1, repository, user=repository.owner)
            self.assertMacaroonDoesNotVerify(
                ["Caveat check for '%s' failed." %
                 find_caveats_by_name(macaroon2, "lp.expires")[0].caveat_id],
                issuer, macaroon2, repository, user=repository.owner)
