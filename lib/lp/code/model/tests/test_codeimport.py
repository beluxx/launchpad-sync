# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for methods of CodeImport and CodeImportSet."""

from datetime import (
    datetime,
    timedelta,
    )
from functools import partial
import json

import pytz
from storm.store import Store
from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.code.enums import (
    CodeImportResultStatus,
    CodeImportReviewStatus,
    RevisionControlSystems,
    TargetRevisionControlSystems,
    )
from lp.code.errors import (
    BranchCreatorNotMemberOfOwnerTeam,
    CodeImportAlreadyRequested,
    CodeImportAlreadyRunning,
    CodeImportNotInReviewedState,
    GitRepositoryCreatorNotMemberOfOwnerTeam,
    )
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.code.interfaces.codeimportjob import ICodeImportJobWorkflow
from lp.code.model.codeimport import CodeImportSet
from lp.code.model.codeimportevent import CodeImportEvent
from lp.code.model.codeimportjob import (
    CodeImportJob,
    CodeImportJobSet,
    )
from lp.code.model.codeimportresult import CodeImportResult
from lp.code.tests.codeimporthelpers import make_running_import
from lp.code.tests.helpers import GitHostingFixture
from lp.registry.interfaces.person import IPersonSet
from lp.services.database.interfaces import IStore
from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    ANONYMOUS,
    api_url,
    login,
    login_person,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    time_counter,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.testing.pages import webservice_for_person


class TestCodeImportBase(WithScenarios, TestCaseWithFactory):

    scenarios = [
        ("Branch", {
            "target_rcs_type": TargetRevisionControlSystems.BZR,
            "supports_source_cvs": True,
            "supports_source_svn": True,
            "supports_source_bzr": True,
            "needs_git_hosting_fixture": False,
            }),
        ("GitRepository", {
            "target_rcs_type": TargetRevisionControlSystems.GIT,
            "supports_source_cvs": False,
            "supports_source_svn": False,
            "supports_source_bzr": False,
            "needs_git_hosting_fixture": True,
            }),
        ]

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        if self.needs_git_hosting_fixture:
            self.hosting_fixture = self.useFixture(GitHostingFixture())


class TestCodeImportCreation(TestCodeImportBase):
    """Test the creation of CodeImports."""

    layer = DatabaseFunctionalLayer

    def test_new_svn_import_svn_scheme(self):
        """A subversion import can use the svn:// scheme."""
        create_func = partial(
            CodeImportSet().new,
            registrant=self.factory.makePerson(),
            context=self.factory.makeProduct(),
            branch_name='imported',
            rcs_type=RevisionControlSystems.BZR_SVN,
            target_rcs_type=self.target_rcs_type,
            url=self.factory.getUniqueURL(scheme="svn"))
        if self.supports_source_svn:
            code_import = create_func()
            self.assertEqual(
                CodeImportReviewStatus.REVIEWED,
                code_import.review_status)
            # No job is created for the import.
            self.assertIsNot(None, code_import.import_job)
        else:
            self.assertRaises(AssertionError, create_func)

    def test_reviewed_svn_import(self):
        """A specific review status can be set for a new import."""
        create_func = partial(
            CodeImportSet().new,
            registrant=self.factory.makePerson(),
            context=self.factory.makeProduct(),
            branch_name='imported',
            rcs_type=RevisionControlSystems.BZR_SVN,
            target_rcs_type=self.target_rcs_type,
            url=self.factory.getUniqueURL(),
            review_status=None)
        if self.supports_source_svn:
            code_import = create_func()
            self.assertEqual(
                CodeImportReviewStatus.REVIEWED,
                code_import.review_status)
            # A job is created for the import.
            self.assertIsNot(None, code_import.import_job)
        else:
            self.assertRaises(AssertionError, create_func)

    def test_cvs_import_reviewed(self):
        """A new CVS code import should have REVIEWED status."""
        create_func = partial(
            CodeImportSet().new,
            registrant=self.factory.makePerson(),
            context=self.factory.makeProduct(),
            branch_name='imported',
            rcs_type=RevisionControlSystems.CVS,
            target_rcs_type=self.target_rcs_type,
            cvs_root=self.factory.getUniqueURL(),
            cvs_module='module',
            review_status=None)
        if self.supports_source_cvs:
            code_import = create_func()
            self.assertEqual(
                CodeImportReviewStatus.REVIEWED,
                code_import.review_status)
            # A job is created for the import.
            self.assertIsNot(None, code_import.import_job)
        else:
            self.assertRaises(AssertionError, create_func)

    def test_git_import_git_scheme(self):
        """A git import can have a git:// style URL."""
        code_import = CodeImportSet().new(
            registrant=self.factory.makePerson(),
            context=self.factory.makeProduct(),
            branch_name='imported',
            rcs_type=RevisionControlSystems.GIT,
            target_rcs_type=self.target_rcs_type,
            url=self.factory.getUniqueURL(scheme="git"),
            review_status=None)
        self.assertEqual(
            CodeImportReviewStatus.REVIEWED,
            code_import.review_status)
        # A job is created for the import.
        self.assertIsNot(None, code_import.import_job)
        if self.needs_git_hosting_fixture:
            # The repository is created on the hosting service.
            self.assertEqual(
                (code_import.git_repository.getInternalPath(),),
                self.hosting_fixture.create.extract_args()[0])

    def test_git_import_reviewed(self):
        """A new git import is always reviewed by default."""
        code_import = CodeImportSet().new(
            registrant=self.factory.makePerson(),
            context=self.factory.makeProduct(),
            branch_name='imported',
            rcs_type=RevisionControlSystems.GIT,
            target_rcs_type=self.target_rcs_type,
            url=self.factory.getUniqueURL(),
            review_status=None)
        self.assertEqual(
            CodeImportReviewStatus.REVIEWED,
            code_import.review_status)
        # A job is created for the import.
        self.assertIsNot(None, code_import.import_job)
        if self.needs_git_hosting_fixture:
            # The repository is created on the hosting service.
            self.assertEqual(
                (code_import.git_repository.getInternalPath(),),
                self.hosting_fixture.create.extract_args()[0])

    def test_bzr_import_reviewed(self):
        """A new bzr import is always reviewed by default."""
        create_func = partial(
            CodeImportSet().new,
            registrant=self.factory.makePerson(),
            context=self.factory.makeProduct(),
            branch_name='mirrored',
            rcs_type=RevisionControlSystems.BZR,
            target_rcs_type=self.target_rcs_type,
            url=self.factory.getUniqueURL(),
            review_status=None)
        if self.supports_source_bzr:
            code_import = create_func()
            self.assertEqual(
                CodeImportReviewStatus.REVIEWED,
                code_import.review_status)
            # A job is created for the import.
            self.assertIsNot(None, code_import.import_job)
        else:
            self.assertRaises(AssertionError, create_func)

    def test_junk_code_import_rejected(self):
        """You are not allowed to create code imports targetting +junk."""
        registrant = self.factory.makePerson()
        self.assertRaises(AssertionError, CodeImportSet().new,
            registrant=registrant,
            context=registrant,
            branch_name='imported',
            rcs_type=RevisionControlSystems.GIT,
            target_rcs_type=self.target_rcs_type,
            url=self.factory.getUniqueURL(),
            review_status=None)

    def test_create_source_package_import(self):
        """Test that we can create an import targetting a source package."""
        registrant = self.factory.makePerson()
        source_package = self.factory.makeSourcePackage()
        if self.target_rcs_type == TargetRevisionControlSystems.BZR:
            context = source_package
        else:
            context = source_package.distribution_sourcepackage
        code_import = CodeImportSet().new(
            registrant=registrant,
            context=context,
            branch_name='imported',
            rcs_type=RevisionControlSystems.GIT,
            target_rcs_type=self.target_rcs_type,
            url=self.factory.getUniqueURL(),
            review_status=None)
        code_import = removeSecurityProxy(code_import)
        self.assertEqual(registrant, code_import.registrant)
        if self.target_rcs_type == TargetRevisionControlSystems.BZR:
            self.assertEqual(registrant, code_import.branch.owner)
            self.assertEqual(IBranchTarget(context), code_import.branch.target)
            self.assertEqual(source_package, code_import.branch.sourcepackage)
        else:
            self.assertEqual(registrant, code_import.git_repository.owner)
            self.assertEqual(context, code_import.git_repository.target)
        # And a job is still created
        self.assertIsNot(None, code_import.import_job)

    def test_set_owner(self):
        """Test that we can create an import owned by someone else."""
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam()
        removeSecurityProxy(registrant).join(owner)
        source_package = self.factory.makeSourcePackage()
        if self.target_rcs_type == TargetRevisionControlSystems.BZR:
            context = source_package
        else:
            context = source_package.distribution_sourcepackage
        code_import = CodeImportSet().new(
            registrant=registrant,
            context=context,
            branch_name='imported',
            rcs_type=RevisionControlSystems.GIT,
            target_rcs_type=self.target_rcs_type,
            url=self.factory.getUniqueURL(),
            review_status=None, owner=owner)
        code_import = removeSecurityProxy(code_import)
        self.assertEqual(registrant, code_import.registrant)
        if self.target_rcs_type == TargetRevisionControlSystems.BZR:
            self.assertEqual(owner, code_import.branch.owner)
            self.assertEqual(registrant, code_import.branch.registrant)
            self.assertEqual(IBranchTarget(context), code_import.branch.target)
            self.assertEqual(source_package, code_import.branch.sourcepackage)
        else:
            self.assertEqual(owner, code_import.git_repository.owner)
            self.assertEqual(registrant, code_import.git_repository.registrant)
            self.assertEqual(context, code_import.git_repository.target)
        # And a job is still created
        self.assertIsNot(None, code_import.import_job)

    def test_registrant_must_be_in_owner(self):
        """Test that we can't create an import for an arbitrary team."""
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam()
        source_package = self.factory.makeSourcePackage()
        if self.target_rcs_type == TargetRevisionControlSystems.BZR:
            context = source_package
            expected_exception = BranchCreatorNotMemberOfOwnerTeam
        else:
            context = source_package.distribution_sourcepackage
            expected_exception = GitRepositoryCreatorNotMemberOfOwnerTeam
        self.assertRaises(
            expected_exception,
            CodeImportSet().new,
            registrant=registrant,
            context=context,
            branch_name='imported',
            rcs_type=RevisionControlSystems.GIT,
            target_rcs_type=self.target_rcs_type,
            url=self.factory.getUniqueURL(),
            review_status=None, owner=owner)


class TestCodeImportDeletion(TestCodeImportBase):
    """Test the deletion of CodeImports."""

    layer = LaunchpadFunctionalLayer

    def test_delete(self):
        """Ensure CodeImport objects can be deleted via CodeImportSet."""
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        CodeImportSet().delete(code_import)

    def test_deleteIncludesJob(self):
        """Ensure deleting CodeImport objects deletes associated jobs."""
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        login_person(getUtility(ILaunchpadCelebrities).vcs_imports.teamowner)
        job_id = code_import.import_job.id
        CodeImportJobSet().getById(job_id)
        job = CodeImportJobSet().getById(job_id)
        assert job is not None
        CodeImportSet().delete(code_import)
        job = CodeImportJobSet().getById(job_id)
        assert job is None

    def test_deleteIncludesEvent(self):
        """Ensure deleting CodeImport objects deletes associated events."""
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        code_import_event = self.factory.makeCodeImportEvent(
            code_import=code_import)
        code_import_event_id = code_import_event.id
        CodeImportSet().delete(code_import_event.code_import)
        store = Store.of(code_import_event)
        store.invalidate(code_import_event)
        self.assertIsNone(store.get(CodeImportEvent, code_import_event_id))

    def test_deleteIncludesResult(self):
        """Ensure deleting CodeImport objects deletes associated results."""
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        code_import_result = self.factory.makeCodeImportResult(
            code_import=code_import)
        code_import_result_id = code_import_result.id
        CodeImportSet().delete(code_import_result.code_import)
        store = Store.of(code_import_result)
        store.invalidate(code_import_result)
        self.assertIsNone(store.get(CodeImportResult, code_import_result_id))


class TestCodeImportStatusUpdate(TestCodeImportBase):
    """Test the status updates of CodeImports."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Log in a VCS Imports member.
        super().setUp('david.allouche@canonical.com')
        self.import_operator = getUtility(IPersonSet).getByEmail(
            'david.allouche@canonical.com')
        # Remove existing jobs.
        for job in IStore(CodeImportJob).find(CodeImportJob):
            job.destroySelf()

    def makeApprovedImportWithPendingJob(self):
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.REVIEWED},
            self.import_operator)
        return code_import

    def makeApprovedImportWithRunningJob(self):
        code_import = self.makeApprovedImportWithPendingJob()
        job = CodeImportJobSet().getJobForMachine('machine', 10)
        self.assertEqual(code_import.import_job, job)
        return code_import

    def test_approve(self):
        # Approving a code import will create a job for it.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.REVIEWED},
            self.import_operator)
        self.assertIsNot(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.REVIEWED, code_import.review_status)

    def test_suspend_no_job(self):
        # Suspending a new import has no impact on jobs.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.SUSPENDED},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.SUSPENDED, code_import.review_status)

    def test_suspend_pending_job(self):
        # Suspending an approved import with a pending job, removes job.
        code_import = self.makeApprovedImportWithPendingJob()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.SUSPENDED},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.SUSPENDED, code_import.review_status)

    def test_suspend_running_job(self):
        # Suspending an approved import with a running job leaves job.
        code_import = self.makeApprovedImportWithRunningJob()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.SUSPENDED},
            self.import_operator)
        self.assertIsNot(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.SUSPENDED, code_import.review_status)

    def test_invalidate_no_job(self):
        # Invalidating a new import has no impact on jobs.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.INVALID},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.INVALID, code_import.review_status)

    def test_invalidate_pending_job(self):
        # Invalidating an approved import with a pending job, removes job.
        code_import = self.makeApprovedImportWithPendingJob()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.INVALID},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.INVALID, code_import.review_status)

    def test_invalidate_running_job(self):
        # Invalidating an approved import with a running job leaves job.
        code_import = self.makeApprovedImportWithRunningJob()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.INVALID},
            self.import_operator)
        self.assertIsNot(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.INVALID, code_import.review_status)

    def test_markFailing_no_job(self):
        # Marking a new import as failing has no impact on jobs.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.FAILING},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.FAILING, code_import.review_status)

    def test_markFailing_pending_job(self):
        # Marking an import with a pending job as failing, removes job.
        code_import = self.makeApprovedImportWithPendingJob()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.FAILING},
            self.import_operator)
        self.assertIs(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.FAILING, code_import.review_status)

    def test_markFailing_running_job(self):
        # Marking an import with a running job as failing leaves job.
        code_import = self.makeApprovedImportWithRunningJob()
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.FAILING},
            self.import_operator)
        self.assertIsNot(None, code_import.import_job)
        self.assertEqual(
            CodeImportReviewStatus.FAILING, code_import.review_status)


class TestCodeImportResultsAttribute(TestCodeImportBase):
    """Test the results attribute of a CodeImport."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super().setUp()
        self.code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)

    def tearDown(self):
        super().tearDown()
        logout()

    def test_no_results(self):
        # Initially a new code import will have no results.
        self.assertEqual([], list(self.code_import.results))

    def test_single_result(self):
        # A result associated with the code import can be accessed directly
        # from the code import object.
        import_result = self.factory.makeCodeImportResult(self.code_import)
        results = list(self.code_import.results)
        self.assertEqual(1, len(results))
        self.assertEqual(import_result, results[0])

    def test_result_ordering(self):
        # The results query will order the results by job started time, with
        # the most recent import first.
        when = time_counter(
            origin=datetime(2007, 9, 9, 12, tzinfo=pytz.UTC),
            delta=timedelta(days=1))
        first = self.factory.makeCodeImportResult(
            self.code_import, date_started=next(when))
        second = self.factory.makeCodeImportResult(
            self.code_import, date_started=next(when))
        third = self.factory.makeCodeImportResult(
            self.code_import, date_started=next(when))
        self.assertTrue(first.date_job_started < second.date_job_started)
        self.assertTrue(second.date_job_started < third.date_job_started)
        results = list(self.code_import.results)
        self.assertEqual(third, results[0])
        self.assertEqual(second, results[1])
        self.assertEqual(first, results[2])

    def test_result_ordering_paranoia(self):
        # Similar to test_result_ordering, but with results created in reverse
        # order (this wouldn't really happen) but it shows that the id of the
        # import result isn't used to sort by.
        when = time_counter(
            origin=datetime(2007, 9, 11, 12, tzinfo=pytz.UTC),
            delta=timedelta(days=-1))
        first = self.factory.makeCodeImportResult(
            self.code_import, date_started=next(when))
        second = self.factory.makeCodeImportResult(
            self.code_import, date_started=next(when))
        third = self.factory.makeCodeImportResult(
            self.code_import, date_started=next(when))
        self.assertTrue(first.date_job_started > second.date_job_started)
        self.assertTrue(second.date_job_started > third.date_job_started)
        results = list(self.code_import.results)
        self.assertEqual(first, results[0])
        self.assertEqual(second, results[1])
        self.assertEqual(third, results[2])


class TestConsecutiveFailureCount(TestCodeImportBase):
    """Tests for `ICodeImport.consecutive_failure_count`."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super().setUp()
        login('no-priv@canonical.com')
        self.machine = self.factory.makeCodeImportMachine()
        self.machine.setOnline()

    def makeRunningJob(self, code_import):
        """Make and return a CodeImportJob object with state==RUNNING.

        This is suitable for passing into finishJob().
        """
        if code_import.import_job is None:
            job = self.factory.makeCodeImportJob(code_import)
        else:
            job = code_import.import_job
        getUtility(ICodeImportJobWorkflow).startJob(job, self.machine)
        return job

    def failImport(self, code_import):
        """Create if necessary a job for `code_import` and have it fail."""
        running_job = self.makeRunningJob(code_import)
        getUtility(ICodeImportJobWorkflow).finishJob(
            running_job, CodeImportResultStatus.FAILURE, None)

    def succeedImport(self, code_import,
                      status=CodeImportResultStatus.SUCCESS):
        """Create if necessary a job for `code_import` and have it succeed."""
        if status not in CodeImportResultStatus.successes:
            raise AssertionError(
                "succeedImport() should be called with a successful status!")
        running_job = self.makeRunningJob(code_import)
        getUtility(ICodeImportJobWorkflow).finishJob(
            running_job, status, None)

    def test_consecutive_failure_count_zero_initially(self):
        # A new code import has a consecutive_failure_count of 0.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        self.assertEqual(0, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_succeed(self):
        # A code import that has succeeded once has a
        # consecutive_failure_count of 0.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        self.succeedImport(code_import)
        self.assertEqual(0, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_fail(self):
        # A code import that has failed once has a consecutive_failure_count
        # of 1.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        self.failImport(code_import)
        self.assertEqual(1, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_succeed_succeed_no_changes(self):
        # A code import that has succeeded then succeeded with no changes has
        # a consecutive_failure_count of 0.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        self.succeedImport(code_import)
        self.succeedImport(
            code_import, CodeImportResultStatus.SUCCESS_NOCHANGE)
        self.assertEqual(0, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_succeed_succeed_partial(self):
        # A code import that has succeeded then succeeded with no changes has
        # a consecutive_failure_count of 0.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        self.succeedImport(code_import)
        self.succeedImport(
            code_import, CodeImportResultStatus.SUCCESS_NOCHANGE)
        self.assertEqual(0, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_fail_fail(self):
        # A code import that has failed twice has a consecutive_failure_count
        # of 2.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        self.failImport(code_import)
        self.failImport(code_import)
        self.assertEqual(2, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_fail_fail_succeed(self):
        # A code import that has failed twice then succeeded has a
        # consecutive_failure_count of 0.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        self.failImport(code_import)
        self.failImport(code_import)
        self.succeedImport(code_import)
        self.assertEqual(0, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_fail_succeed_fail(self):
        # A code import that has failed then succeeded then failed again has a
        # consecutive_failure_count of 1.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        self.failImport(code_import)
        self.succeedImport(code_import)
        self.failImport(code_import)
        self.assertEqual(1, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_succeed_fail_succeed(self):
        # A code import that has succeeded then failed then succeeded again
        # has a consecutive_failure_count of 0.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        self.succeedImport(code_import)
        self.failImport(code_import)
        self.succeedImport(code_import)
        self.assertEqual(0, code_import.consecutive_failure_count)

    def test_consecutive_failure_count_other_import_non_interference(self):
        # The failure or success of other code imports does not affect
        # consecutive_failure_count.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        other_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        self.failImport(code_import)
        self.assertEqual(1, code_import.consecutive_failure_count)
        self.failImport(other_import)
        self.assertEqual(1, code_import.consecutive_failure_count)
        self.succeedImport(code_import)
        self.assertEqual(0, code_import.consecutive_failure_count)
        self.succeedImport(other_import)
        self.assertEqual(0, code_import.consecutive_failure_count)
        self.failImport(code_import)
        self.assertEqual(1, code_import.consecutive_failure_count)
        self.failImport(other_import)
        self.assertEqual(1, code_import.consecutive_failure_count)


class TestTryFailingImportAgain(TestCodeImportBase):
    """Tests for `ICodeImport.tryFailingImportAgain`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Log in a VCS Imports member.
        super().setUp()
        login_person(getUtility(ILaunchpadCelebrities).vcs_imports.teamowner)

    def test_mustBeFailing(self):
        # tryFailingImportAgain only succeeds for imports that are FAILING.
        outcomes = {}
        for status in CodeImportReviewStatus.items:
            code_import = self.factory.makeCodeImport(
                target_rcs_type=self.target_rcs_type,
                review_status=CodeImportReviewStatus.NEW)
            code_import.updateFromData(
                {'review_status': status}, self.factory.makePerson())
            try:
                code_import.tryFailingImportAgain(self.factory.makePerson())
            except AssertionError:
                outcomes[status] = 'failed'
            else:
                outcomes[status] = 'succeeded'
        self.assertEqual(
            {CodeImportReviewStatus.NEW: 'failed',
             CodeImportReviewStatus.REVIEWED: 'failed',
             CodeImportReviewStatus.SUSPENDED: 'failed',
             CodeImportReviewStatus.INVALID: 'failed',
             CodeImportReviewStatus.FAILING: 'succeeded'},
            outcomes)

    def test_resetsStatus(self):
        # tryFailingImportAgain sets the review_status of the import back to
        # REVIEWED.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.FAILING},
            self.factory.makePerson())
        code_import.tryFailingImportAgain(self.factory.makePerson())
        self.assertEqual(
            CodeImportReviewStatus.REVIEWED,
            code_import.review_status)

    def test_requestsImport(self):
        # tryFailingImportAgain requests an import.
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type)
        code_import.updateFromData(
            {'review_status': CodeImportReviewStatus.FAILING},
            self.factory.makePerson())
        requester = self.factory.makePerson()
        code_import.tryFailingImportAgain(requester)
        self.assertEqual(
            requester, code_import.import_job.requesting_user)


class TestRequestImport(TestCodeImportBase):
    """Tests for `ICodeImport.requestImport`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # We have to be logged in to request imports
        super().setUp(user='no-priv@canonical.com')

    def test_requestsJob(self):
        code_import = self.factory.makeCodeImport(
            git_repo_url=self.factory.getUniqueURL(),
            target_rcs_type=self.target_rcs_type)
        requester = self.factory.makePerson()
        old_date = code_import.import_job.date_due
        code_import.requestImport(requester)
        self.assertEqual(requester, code_import.import_job.requesting_user)
        self.assertTrue(code_import.import_job.date_due <= old_date)

    def test_noop_if_already_requested(self):
        code_import = self.factory.makeCodeImport(
            git_repo_url=self.factory.getUniqueURL(),
            target_rcs_type=self.target_rcs_type)
        requester = self.factory.makePerson()
        code_import.requestImport(requester)
        old_date = code_import.import_job.date_due
        code_import.requestImport(requester)
        # The checks don't matter so much, it's more that we don't get
        # an exception.
        self.assertEqual(requester, code_import.import_job.requesting_user)
        self.assertEqual(old_date, code_import.import_job.date_due)

    def test_optional_error_if_already_requested(self):
        code_import = self.factory.makeCodeImport(
            git_repo_url=self.factory.getUniqueURL(),
            target_rcs_type=self.target_rcs_type)
        requester = self.factory.makePerson()
        code_import.requestImport(requester)
        e = self.assertRaises(
            CodeImportAlreadyRequested, code_import.requestImport, requester,
            error_if_already_requested=True)
        self.assertEqual(requester, e.requesting_user)

    def test_exception_on_disabled(self):
        # get an SVN/Git (as appropriate) request which is suspended
        if self.supports_source_svn:
            kwargs = {"svn_branch_url": self.factory.getUniqueURL()}
        else:
            kwargs = {"git_repo_url": self.factory.getUniqueURL()}
        code_import = self.factory.makeCodeImport(
            target_rcs_type=self.target_rcs_type,
            review_status=CodeImportReviewStatus.SUSPENDED, **kwargs)
        requester = self.factory.makePerson()
        # which leads to an exception if we try and ask for an import
        self.assertRaises(
            CodeImportNotInReviewedState, code_import.requestImport,
            requester)

    def test_exception_if_already_running(self):
        code_import = self.factory.makeCodeImport(
            git_repo_url=self.factory.getUniqueURL(),
            target_rcs_type=self.target_rcs_type)
        code_import = make_running_import(factory=self.factory,
            code_import=code_import)
        requester = self.factory.makePerson()
        self.assertRaises(
            CodeImportAlreadyRunning, code_import.requestImport,
            requester)


class TestCodeImportWebservice(TestCodeImportBase):
    """Tests for the web service."""

    layer = DatabaseFunctionalLayer

    def test_codeimport_owner_can_set_url(self):
        # Repository owner can set the code import URL.
        owner_db = self.factory.makePerson()
        initial_import_url = self.factory.getUniqueURL()
        code_import = self.factory.makeCodeImport(
            owner=owner_db,
            registrant=owner_db,
            git_repo_url=initial_import_url,
            rcs_type=RevisionControlSystems.GIT,
            target_rcs_type=self.target_rcs_type,
        )
        webservice = webservice_for_person(
            owner_db, permission=OAuthPermission.WRITE_PRIVATE)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            code_import_url = api_url(code_import)

        new_url = "https://example.com/foo/bar.git"
        response = webservice.patch(
            code_import_url, "application/json",
            json.dumps({"url": new_url})
        )
        self.assertEqual(209, response.status)
        code_import_json = webservice.get(code_import_url).jsonBody()
        self.assertEqual(new_url, code_import_json['url'])

    def test_codeimport_users_without_permission_cannot_set_url(self):
        # The users without the launchpad.Edit permission cannot set the
        # code import URL.
        owner_db = self.factory.makePerson()
        code_import = self.factory.makeCodeImport(
            owner=owner_db,
            registrant=owner_db,
            target_rcs_type=self.target_rcs_type
        )
        another_person = self.factory.makePerson()
        webservice = webservice_for_person(
            another_person, permission=OAuthPermission.WRITE_PRIVATE)
        webservice.default_api_version = "devel"

        with person_logged_in(ANONYMOUS):
            code_import_url = api_url(code_import)

        new_url = "https://example.com/foo/bar.git"
        response = webservice.patch(
            code_import_url, "application/json",
            json.dumps({"url": new_url}),
        )
        self.assertEqual(401, response.status)


load_tests = load_tests_apply_scenarios
