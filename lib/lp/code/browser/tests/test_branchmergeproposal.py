# Copyright 2009-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for BranchMergeProposals."""

from datetime import (
    datetime,
    timedelta,
    )
from difflib import (
    diff_bytes,
    unified_diff,
    )
import doctest
import hashlib
import re

from fixtures import FakeLogger
from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.restful.interfaces import IJSONRequestCache
import pytz
import simplejson
import six
from soupmatchers import (
    HTMLContains,
    Tag,
    Within,
    )
from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )
from testtools.matchers import (
    ContainsDict,
    DocTestMatches,
    Equals,
    Is,
    MatchesDict,
    MatchesListwise,
    MatchesRegex,
    MatchesSetwise,
    MatchesStructure,
    Not,
    )
import transaction
from zope.component import (
    getMultiAdapter,
    getUtility,
    )
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.code.browser.branch import RegisterBranchMergeProposalView
from lp.code.browser.branchmergeproposal import (
    BranchMergeProposalAddVoteView,
    BranchMergeProposalChangeStatusView,
    BranchMergeProposalContextMenu,
    BranchMergeProposalMergedView,
    BranchMergeProposalResubmitView,
    BranchMergeProposalVoteView,
    DecoratedCodeReviewVoteReference,
    ICodeReviewNewRevisions,
    latest_proposals_for_each_branch,
    )
from lp.code.browser.codereviewcomment import CodeReviewDisplayComment
from lp.code.browser.gitref import GitRefRegisterMergeProposalView
from lp.code.enums import (
    BranchMergeProposalStatus,
    CodeReviewVote,
    RevisionStatusResult,
    )
from lp.code.errors import (
    GitRepositoryScanFault,
    InvalidBranchMergeProposal,
    )
from lp.code.interfaces.branchjob import IBranchScanJobSource
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposal,
    IMergeProposalNeedsReviewEmailJobSource,
    IMergeProposalUpdatedEmailJobSource,
    )
from lp.code.interfaces.gitjob import IGitRefScanJobSource
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.code.model.branchmergeproposaljob import UpdatePreviewDiffJob
from lp.code.model.diff import PreviewDiff
from lp.code.tests.helpers import (
    add_revision_to_branch,
    GitHostingFixture,
    make_merge_proposal_without_reviewers,
    )
from lp.code.xmlrpc.git import GitAPI
from lp.coop.answersbugs.visibility import (
    TestHideMessageControlMixin,
    TestMessageVisibilityMixin,
    )
from lp.registry.enums import (
    PersonVisibility,
    TeamMembershipPolicy,
    )
from lp.services.compat import message_as_bytes
from lp.services.database.constants import UTC_NOW
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.services.librarian.interfaces.client import LibrarianServerError
from lp.services.messages.model.message import MessageSet
from lp.services.timeout import TimeoutError
from lp.services.utils import seconds_since_epoch
from lp.services.webapp import canonical_url
from lp.services.webapp.interfaces import BrowserNotificationLevel
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    admin_logged_in,
    BrowserTestCase,
    EventRecorder,
    feature_flags,
    login_person,
    monkey_patch,
    normalize_whitespace,
    person_logged_in,
    set_feature_flag,
    TestCaseWithFactory,
    time_counter,
    verifyObject,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.pages import (
    extract_text,
    find_main_content,
    find_tag_by_id,
    find_tags_by_class,
    first_tag_by_class,
    get_feedback_messages,
    )
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


class GitHostingClientMixin:

    def setUp(self):
        super().setUp()
        self.git_hosting_fixture = self.useFixture(GitHostingFixture())


class TestBranchMergeProposalContextMenu(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_add_comment_enabled_when_not_mergeable(self):
        """It should be possible to comment on an unmergeable proposal."""
        bmp = self.factory.makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.REJECTED)
        login_person(bmp.registrant)
        menu = BranchMergeProposalContextMenu(bmp)
        self.assertTrue(menu.add_comment().enabled)


class TestDecoratedCodeReviewVoteReference(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_commentEnabled(self):
        """It should be possible to review an unmergeable proposal."""
        request = self.factory.makeCodeReviewVoteReference()
        bmp = request.branch_merge_proposal
        bmp.rejectBranch(bmp.target_branch.owner, 'foo')
        d = DecoratedCodeReviewVoteReference(request, request.reviewer, None)
        self.assertTrue(d.user_can_review)
        self.assertTrue(d.can_change_review)


class TestBranchMergeProposalMergedViewMixin:
    """Tests for `BranchMergeProposalMergedView`."""

    layer = DatabaseFunctionalLayer

    def test_initial_values(self):
        # The default merged_revno is the head revno of the target branch.
        bmp = self.makeBranchMergeProposal()
        login_person(bmp.registrant)
        view = BranchMergeProposalMergedView(bmp, LaunchpadTestRequest())
        self.setBranchRevision(bmp.merge_source, self.arbitrary_revisions[0])
        self.setBranchRevision(bmp.merge_target, self.arbitrary_revisions[1])
        self.assertEqual(
            self.getBranchRevisionValues(bmp.merge_target),
            view.initial_values)

    def test_change_revision(self):
        bmp = self.makeBranchMergeProposal()
        login_person(bmp.registrant)
        target_identity = bmp.merge_target.identity
        bmp.markAsMerged(merge_reporter=bmp.registrant)
        browser = self.getViewBrowser(bmp, '+merged', user=bmp.registrant)
        browser.getControl(self.merged_revision_text).value = str(
            self.arbitrary_revisions[2])
        browser.getControl('Mark as Merged').click()
        self.assertEqual(
            ["The proposal's merged revision has been updated."],
            get_feedback_messages(browser.contents))
        self.assertIn(
            'Status:\nMerged\nMerged at revision:\n%s' % (
                self.arbitrary_revisions[2]),
            extract_text(find_tag_by_id(browser.contents, 'proposal-summary')))
        browser = self.getViewBrowser(bmp.merge_source, '+index')
        self.assertIn(
            'Merged into %s at revision %s' % (
                target_identity, self.arbitrary_revisions[2]),
            normalize_whitespace(extract_text(find_tag_by_id(
                browser.contents, 'landing-targets'))))

    def test_link_to_merged_revno(self):
        bmp = self.makeBranchMergeProposal()
        login_person(bmp.registrant)
        bmp.markAsMerged(merge_reporter=bmp.registrant)
        revision_link = bmp.merge_target.getCodebrowseUrlForRevision(
            self.arbitrary_revisions[2])
        revision_number = Tag('Revision number', 'a', {'href': revision_link})
        browser = self.getViewBrowser(bmp, '+merged', user=bmp.registrant)
        browser.getControl(self.merged_revision_text).value = str(
            self.arbitrary_revisions[2])
        browser.getControl('Mark as Merged').click()
        browser = self.getViewBrowser(bmp.merge_source, '+index')
        self.assertThat(browser.contents, HTMLContains(revision_number))

    def test_notifies_modification(self):
        bmp = self.makeBranchMergeProposal()
        registrant = bmp.registrant
        login_person(registrant)
        browser = self.getViewBrowser(bmp, '+merged', user=bmp.registrant)
        browser.getControl(self.merged_revision_text).value = str(
            self.arbitrary_revisions[2])
        with EventRecorder(propagate=True) as recorder:
            browser.getControl('Mark as Merged').click()
        login_person(registrant)
        events = [
            event for event in recorder.events
            if isinstance(event, ObjectModifiedEvent) and
               IBranchMergeProposal.providedBy(event.object)]
        self.assertThat(events, MatchesListwise([
            MatchesStructure(
                object_before_modification=MatchesStructure.byEquality(
                    queue_status=BranchMergeProposalStatus.WORK_IN_PROGRESS),
                object=MatchesStructure.byEquality(
                    queue_status=BranchMergeProposalStatus.MERGED))]))


class TestBranchMergeProposalMergedViewBzr(
    TestBranchMergeProposalMergedViewMixin, BrowserTestCase):
    """Tests for `BranchMergeProposalMergedView` for Bazaar."""

    arbitrary_revisions = (1, 2, 42)
    merged_revision_text = 'Merged revision number'

    def makeBranchMergeProposal(self):
        return self.factory.makeBranchMergeProposal()

    def setBranchRevision(self, branch, revision):
        removeSecurityProxy(branch).revision_count = revision

    def getBranchRevisionValues(self, branch):
        return {'merged_revno': branch.revision_count}


class TestBranchMergeProposalMergedViewGit(
    TestBranchMergeProposalMergedViewMixin, GitHostingClientMixin,
    BrowserTestCase):
    """Tests for `BranchMergeProposalMergedView` for Git."""

    arbitrary_revisions = ("0" * 40, "1" * 40, "2" * 40)
    merged_revision_text = 'Merged revision ID'

    def makeBranchMergeProposal(self):
        return self.factory.makeBranchMergeProposalForGit()

    def setBranchRevision(self, branch, revision):
        removeSecurityProxy(branch).commit_sha1 = revision

    def getBranchRevisionValues(self, branch):
        return {'merged_revision_id': branch.commit_sha1}

    def test_mp_page_with_git_hosting_issues(self):
        mp = self.makeBranchMergeProposal()
        self.git_hosting_fixture.getLog.result = None
        self.git_hosting_fixture.getLog.failure = GitRepositoryScanFault(":-(")

        canonical_url(mp)
        browser = self.getUserBrowser(canonical_url(mp))
        error_msg = (
            "There was an error fetching revisions from git servers. "
            "Please try again in a few minutes. If the problem persists, "
            'contact Launchpad support.')
        self.assertIn(
            error_msg, extract_text(find_main_content(browser.contents)))


class TestBranchMergeProposalAddVoteView(TestCaseWithFactory):
    """Test the AddVote view."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.bmp = self.factory.makeBranchMergeProposal()

    def _createView(self):
        # Construct the view and initialize it.
        view = BranchMergeProposalAddVoteView(
            self.bmp, LaunchpadTestRequest())
        view.initialize()
        return view

    def test_init_with_random_person(self):
        """Any random person ought to be able to vote."""
        login_person(self.factory.makePerson())
        self._createView()

    def test_init_with_anonymous(self):
        """Anonymous people cannot vote."""
        self.assertRaises(AssertionError, self._createView)


class TestBranchMergeProposalVoteView(TestCaseWithFactory):
    """Make sure that the votes are returned in the right order."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use an admin so we don't have to worry about launchpad.Edit
        # permissions on the merge proposals for adding comments, or
        # nominating reviewers.
        TestCaseWithFactory.setUp(self, user="admin@canonical.com")
        self.bmp = make_merge_proposal_without_reviewers(self.factory)
        self.date_generator = time_counter(delta=timedelta(days=1))

    def _createComment(self, reviewer, vote):
        """Create a comment on the merge proposal."""
        self.bmp.createComment(
            owner=reviewer,
            subject=self.factory.getUniqueString('subject'),
            vote=vote,
            _date_created=next(self.date_generator))

    def _nominateReviewer(self, reviewer, registrant):
        """Nominate a reviewer for the merge proposal."""
        self.bmp.nominateReviewer(
            reviewer=reviewer, registrant=registrant,
            _date_created=next(self.date_generator))

    def testNoVotes(self):
        # No votes should return empty lists
        login_person(self.factory.makePerson())
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertEqual([], view.current_reviews)
        self.assertEqual([], view.requested_reviews)
        # The vote table should not be shown, because there are no votes, and
        # the logged-in user cannot request reviews.
        self.assertFalse(view.show_table)

    def _createPrivateVotes(self, is_branch_visible=True):
        # Create a branch with a public and private reviewer.
        owner = self.bmp.source_branch.owner
        if not is_branch_visible:
            branch = self.bmp.source_branch
            branch.transitionToInformationType(InformationType.USERDATA, owner)

        # Set up some review requests.
        public_person1 = self.factory.makePerson()
        private_team1 = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE,
            membership_policy=TeamMembershipPolicy.MODERATED)
        self._nominateReviewer(public_person1, owner)
        self._nominateReviewer(private_team1, owner)

        return private_team1, public_person1

    def testPrivateVotesVisibleIfBranchVisible(self):
        # User can see votes for private teams if they can see the branch.
        private_team1, public_person1 = self._createPrivateVotes()
        login_person(self.factory.makePerson())
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())

        # Check the requested reviews.
        requested_reviews = view.requested_reviews
        self.assertEqual(2, len(requested_reviews))
        self.assertContentEqual(
            [public_person1, private_team1],
            [review.reviewer for review in requested_reviews])

    def testRequestedOrdering(self):
        # No votes should return empty lists
        # Request three reviews.
        albert = self.factory.makePerson(name='albert')
        bob = self.factory.makePerson(name='bob')
        charles = self.factory.makePerson(name='charles')

        owner = self.bmp.source_branch.owner

        self._nominateReviewer(albert, owner)
        self._nominateReviewer(bob, owner)
        self._nominateReviewer(charles, owner)

        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertEqual([], view.current_reviews)
        requested_reviews = view.requested_reviews
        self.assertEqual(3, len(requested_reviews))
        self.assertEqual(
            [charles, bob, albert],
            [review.reviewer for review in requested_reviews])

    def test_user_can_claim_self(self):
        """Someone cannot claim a review already assigned to them."""
        albert = self.factory.makePerson()
        owner = self.bmp.source_branch.owner
        self._nominateReviewer(albert, owner)
        login_person(albert)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertFalse(view.requested_reviews[0].user_can_claim)

    def test_user_can_claim_member(self):
        """Someone can claim a review already assigned to their team."""
        albert = self.factory.makePerson()
        review_team = self.factory.makeTeam()
        albert.join(review_team)
        owner = self.bmp.source_branch.owner
        self._nominateReviewer(review_team, owner)
        login_person(albert)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertTrue(view.requested_reviews[0].user_can_claim)

    def test_user_can_claim_nonmember(self):
        """A non-member cannot claim a team's review."""
        albert = self.factory.makePerson()
        review_team = self.factory.makeTeam()
        owner = self.bmp.source_branch.owner
        self._nominateReviewer(review_team, owner)
        login_person(albert)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertFalse(view.requested_reviews[0].user_can_claim)

    def makeReviewRequest(self, viewer=None, registrant=None):
        albert = self.factory.makePerson()
        if registrant is None:
            registrant = self.bmp.source_branch.owner
        self._nominateReviewer(albert, registrant)
        if viewer is None:
            viewer = albert
        login_person(viewer)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        return view.requested_reviews[0]

    def test_user_can_reassign_assignee(self):
        """The user can reassign if they are the assignee."""
        review_request = self.makeReviewRequest()
        self.assertTrue(review_request.user_can_reassign)

    def test_user_can_reassign_registrant(self):
        """The user can reassign if they are the registrant."""
        registrant = self.factory.makePerson()
        review_request = self.makeReviewRequest(registrant, registrant)
        self.assertTrue(review_request.user_can_reassign)

    def test_user_cannot_reassign_random_person(self):
        """Random people cannot reassign reviews."""
        viewer = self.factory.makePerson()
        review_request = self.makeReviewRequest(viewer)
        self.assertFalse(review_request.user_can_reassign)

    def testCurrentReviewOrdering(self):
        # Most recent first.
        # Request three reviews.
        albert = self.factory.makePerson(name='albert')
        bob = self.factory.makePerson(name='bob')
        charles = self.factory.makePerson(name='charles')
        self._createComment(albert, CodeReviewVote.APPROVE)
        self._createComment(bob, CodeReviewVote.ABSTAIN)
        self._createComment(charles, CodeReviewVote.DISAPPROVE)

        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())

        self.assertEqual(
            [charles, bob, albert],
            [review.reviewer for review in view.current_reviews])

    def testChangeOfVoteBringsToTop(self):
        # Changing the vote changes the vote date, so it comes to the top.
        # Request three reviews.
        albert = self.factory.makePerson(name='albert')
        bob = self.factory.makePerson(name='bob')
        self._createComment(albert, CodeReviewVote.ABSTAIN)
        self._createComment(bob, CodeReviewVote.APPROVE)
        self._createComment(albert, CodeReviewVote.APPROVE)

        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())

        self.assertEqual(
            [albert, bob],
            [review.reviewer for review in view.current_reviews])

    def addReviewTeam(self):
        review_team = self.factory.makeTeam(name='reviewteam')
        self.bmp.target_branch.reviewer = review_team

    def test_review_team_members_trusted(self):
        """Members of the target branch's review team are trusted."""
        self.addReviewTeam()
        albert = self.factory.makePerson(name='albert')
        albert.join(self.bmp.target_branch.reviewer)
        self._createComment(albert, CodeReviewVote.APPROVE)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertTrue(view.reviews[0].trusted)

    def test_review_team_nonmembers_untrusted(self):
        """Non-members of the target branch's review team are untrusted."""
        self.addReviewTeam()
        albert = self.factory.makePerson(name='albert')
        self._createComment(albert, CodeReviewVote.APPROVE)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertFalse(view.reviews[0].trusted)

    def test_no_review_team_untrusted(self):
        """If the target branch has no review team, everyone is untrusted."""
        albert = self.factory.makePerson(name='albert')
        self._createComment(albert, CodeReviewVote.APPROVE)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertFalse(view.reviews[0].trusted)

    def test_render_all_vote_types(self):
        # A smoke test that the view knows how to render all types of vote.
        for vote in CodeReviewVote.items:
            self._createComment(
                self.factory.makePerson(), vote)

        view = getMultiAdapter(
            (self.bmp, LaunchpadTestRequest()), name='+votes')
        self.assertTrue(
            isinstance(view, BranchMergeProposalVoteView),
            "The +votes page for a BranchMergeProposal is expected to be a "
            "BranchMergeProposalVoteView")
        # We just test that rendering does not raise.
        view.render()


class TestRegisterBranchMergeProposalViewMixin:
    """Test the merge proposal registration view."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super().setUp()
        self.source_branch = self._makeBranch()
        self.user = self.factory.makePerson()
        login_person(self.user)

    def _makeTargetBranchWithReviewer(self):
        albert = self.factory.makePerson(name='albert')
        target_branch = self._makeTargetBranch(reviewer=albert)
        return target_branch, albert

    def _getSourceProposal(self, target_branch):
        # There will only be one proposal.
        landing_targets = list(self.source_branch.landing_targets)
        self.assertEqual(1, len(landing_targets))
        proposal = landing_targets[0]
        self.assertEqual(target_branch, proposal.merge_target)
        return proposal

    def assertOnePendingReview(self, proposal, reviewer, review_type=None):
        # There should be one pending vote for the reviewer with the specified
        # review type.
        votes = list(proposal.votes)
        self.assertEqual(1, len(votes))
        self.assertEqual(reviewer, votes[0].reviewer)
        self.assertEqual(self.user, votes[0].registrant)
        self.assertIs(None, votes[0].comment)
        if review_type is None:
            self.assertIs(None, votes[0].review_type)
        else:
            self.assertEqual(review_type, votes[0].review_type)

    def test_register_simplest_case(self):
        # This simplest case is where the user only specifies the target
        # branch, and not an initial comment or reviewer. The reviewer will
        # therefore be set to the branch owner.
        target_branch = self._makeTargetBranch()
        view = self._createView()
        view.register_action.success(self._getFormValues(
            target_branch, {'needs_review': True}))
        proposal = self._getSourceProposal(target_branch)
        self.assertOnePendingReview(proposal, target_branch.owner)
        self.assertIs(None, proposal.description)

    def test_register_ajax_request_with_no_confirmation(self):
        # Ajax submits where there is no confirmation required return a 201
        # with the new location.
        owner = self.factory.makePerson()
        target_branch = self._makeTargetBranch()
        reviewer = self.factory.makePerson()
        extra = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        request = LaunchpadTestRequest(method='POST', **extra)
        request.setPrincipal(owner)
        view = self._createView(request=request)
        with person_logged_in(owner):
            result_data = view.register_action.success(self._getFormValues(
                target_branch, {
                    'reviewer': reviewer,
                    'needs_review': True,
                    }))
        self.assertEqual(None, result_data)
        self.assertEqual(201, view.request.response.getStatus())
        mp = target_branch.getMergeProposals()[0]
        self.assertEqual(
            canonical_url(mp), view.request.response.getHeader('Location'))

    def test_register_work_in_progress(self):
        # The needs review checkbox can be unchecked to create a work in
        # progress proposal.
        target_branch = self._makeTargetBranch()
        view = self._createView()
        view.register_action.success(self._getFormValues(
            target_branch, {'needs_review': False}))
        proposal = self._getSourceProposal(target_branch)
        self.assertEqual(
            BranchMergeProposalStatus.WORK_IN_PROGRESS,
            proposal.queue_status)

    def test_register_with_commit_message(self):
        # A commit message can also be set during the register process.
        target_branch = self._makeTargetBranch()
        view = self._createView()
        view.register_action.success(self._getFormValues(
            target_branch, {
                'needs_review': True,
                'commit_message': 'Fixed the bug!',
                }))
        proposal = self._getSourceProposal(target_branch)
        self.assertEqual('Fixed the bug!', proposal.commit_message)

    def test_register_initial_comment(self):
        # If the user specifies a description, this is recorded on the
        # proposal.
        target_branch = self._makeTargetBranch()
        view = self._createView()
        view.register_action.success(self._getFormValues(
            target_branch, {
                'comment': "This is the description.",
                'needs_review': True,
                }))

        proposal = self._getSourceProposal(target_branch)
        self.assertOnePendingReview(proposal, target_branch.owner)
        self.assertEqual(proposal.description, "This is the description.")

    def test_register_request_reviewer(self):
        # If the user requests a reviewer, then a pending vote is added to the
        # proposal.
        target_branch = self._makeTargetBranch()
        reviewer = self.factory.makePerson()
        view = self._createView()
        view.register_action.success(self._getFormValues(
            target_branch, {
                'reviewer': reviewer,
                'needs_review': True,
                }))

        proposal = self._getSourceProposal(target_branch)
        self.assertOnePendingReview(proposal, reviewer)
        self.assertIs(None, proposal.description)

    def test_register_request_review_type(self):
        # We can request a specific review type of the reviewer.  If we do, it
        # is recorded along with the pending review.
        target_branch = self._makeTargetBranch()
        reviewer = self.factory.makePerson()
        view = self._createView()
        view.register_action.success(self._getFormValues(
            target_branch, {
                'reviewer': reviewer,
                'review_type': 'god-like',
                'needs_review': True,
                }))

        proposal = self._getSourceProposal(target_branch)
        self.assertOnePendingReview(proposal, reviewer, 'god-like')
        self.assertIs(None, proposal.description)

    def test_register_comment_and_review(self):
        # The user can give a description and request a review from
        # someone.
        target_branch = self._makeTargetBranch()
        reviewer = self.factory.makePerson()
        view = self._createView()
        view.register_action.success(self._getFormValues(
            target_branch, {
                'reviewer': reviewer,
                'review_type': 'god-like',
                'comment': "This is the description.",
                'needs_review': True,
                }))

        proposal = self._getSourceProposal(target_branch)
        self.assertOnePendingReview(proposal, reviewer, 'god-like')
        self.assertEqual(proposal.description, "This is the description.")

    def test_register_for_target_with_default_reviewer(self):
        # A simple case is where the user only specifies the target
        # branch, and not an initial comment or reviewer. The target branch
        # has a reviewer so that reviewer should be used
        target_branch, reviewer = self._makeTargetBranchWithReviewer()
        view = self._createView()
        view.register_action.success(self._getFormValues(
            target_branch, {'needs_review': True}))
        proposal = self._getSourceProposal(target_branch)
        self.assertOnePendingReview(proposal, reviewer)
        self.assertIs(None, proposal.description)

    def test_register_request_review_type_branch_reviewer(self):
        # We can ask for a specific review type. The target branch has a
        # reviewer so that reviewer should be used.
        target_branch, reviewer = self._makeTargetBranchWithReviewer()
        view = self._createView()
        view.register_action.success(self._getFormValues(
            target_branch, {
                'review_type': 'god-like',
                'needs_review': True,
                }))
        proposal = self._getSourceProposal(target_branch)
        self.assertOnePendingReview(proposal, reviewer, 'god-like')
        self.assertIs(None, proposal.description)

    def test_register_reviewer_not_hidden(self):
        branch = self._makeBranch()
        browser = self.getViewBrowser(branch, '+register-merge')
        extra = Tag(
            'extra', 'fieldset', attrs={'id': 'mergeproposal-extra-options'})
        reviewer = Tag('reviewer', 'input', attrs={'id': 'field.reviewer'})
        matcher = Not(HTMLContains(reviewer.within(extra)))
        self.assertThat(browser.contents, matcher)

    def test_branch_visibility_notification(self):
        # If the reviewer cannot see the source and/or target branches, a
        # notification message is displayed.
        owner = self.factory.makePerson()
        target_branch = self._makeTargetBranch(
            owner=owner, information_type=InformationType.USERDATA)
        reviewer = self.factory.makePerson()
        with person_logged_in(owner):
            view = self._createView()
            view.register_action.success(self._getFormValues(
                target_branch, {
                    'reviewer': reviewer,
                    'needs_review': True,
                    }))

        (notification,) = view.request.response.notifications
        self.assertThat(
            notification.message, MatchesRegex(
                'To ensure visibility, .* is now subscribed to:.*'))
        self.assertEqual(BrowserNotificationLevel.INFO, notification.level)


class TestRegisterBranchMergeProposalViewBzr(
    TestRegisterBranchMergeProposalViewMixin, BrowserTestCase):
    """Test the merge proposal registration view for Bazaar."""

    def _makeBranch(self):
        return self.factory.makeProductBranch()

    def _makeTargetBranch(self, **kwargs):
        return self.factory.makeProductBranch(
            product=self.source_branch.product, **kwargs)

    def _makeTargetBranchWithReviewer(self):
        albert = self.factory.makePerson(name='albert')
        target_branch = self._makeTargetBranch(reviewer=albert)
        return target_branch, albert

    def _createView(self, request=None):
        # Construct the view and initialize it.
        if not request:
            request = LaunchpadTestRequest()
        view = RegisterBranchMergeProposalView(self.source_branch, request)
        view.initialize()
        return view

    @staticmethod
    def _getFormValues(target_branch, extras):
        values = {'target_branch': target_branch}
        values.update(extras)
        return values

    def test_register_ajax_request_with_confirmation(self):
        # Ajax submits return json data containing info about what the visible
        # branches are if they are not all visible to the reviewer.

        # Make a branch the reviewer cannot see.
        owner = self.factory.makePerson()
        target_branch = self._makeTargetBranch(
            owner=owner, information_type=InformationType.USERDATA)
        reviewer = self.factory.makePerson()
        extra = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        request = LaunchpadTestRequest(method='POST', **extra)
        request.setPrincipal(owner)
        view = self._createView(request=request)
        with person_logged_in(owner):
            branches_to_check = [self.source_branch.unique_name,
                target_branch.unique_name]
            expected_data = {
                'person_name': reviewer.displayname,
                'branches_to_check': branches_to_check,
                'visible_branches': [self.source_branch.unique_name]}
            result_data = view.register_action.success(self._getFormValues(
                target_branch, {
                    'reviewer': reviewer,
                    'needs_review': True,
                    }))
        self.assertEqual(
            '400 Branch Visibility',
            view.request.response.getStatusString())
        self.assertEqual(expected_data, simplejson.loads(result_data))

    def test_register_ajax_request_with_validation_errors(self):
        # Ajax submits where there is a validation error in the submitted data
        # return the expected json response containing the error info.
        owner = self.factory.makePerson()
        target_branch = self._makeTargetBranch(
            owner=owner, information_type=InformationType.USERDATA)
        extra = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        with person_logged_in(owner):
            request = LaunchpadTestRequest(
                method='POST',
                form={
                    'field.actions.register': 'Propose Merge',
                    'field.target_branch.target_branch':
                        target_branch.unique_name},
                **extra)
            request.setPrincipal(owner)
            transaction.commit()
            view = create_initialized_view(
                target_branch,
                name='+register-merge',
                request=request)
        self.assertEqual(
            '400 Validation', view.request.response.getStatusString())
        self.assertEqual(
            {'error_summary': 'There is 1 error.',
            'errors': {
                'field.target_branch':
                    ('The target branch cannot be the same as the '
                    'source branch.')},
            'form_wide_errors': []},
            simplejson.loads(view.form_result))


class TestRegisterBranchMergeProposalViewGit(
    TestRegisterBranchMergeProposalViewMixin, BrowserTestCase):
    """Test the merge proposal registration view for Git."""

    def _makeBranch(self):
        return self.factory.makeGitRefs()[0]

    def _makeTargetBranch(self, **kwargs):
        return self.factory.makeGitRefs(
            target=self.source_branch.target, **kwargs)[0]

    def _createView(self, request=None):
        # Construct the view and initialize it.
        if not request:
            request = LaunchpadTestRequest()
        view = GitRefRegisterMergeProposalView(self.source_branch, request)
        view.initialize()
        return view

    @staticmethod
    def _getFormValues(target_branch, extras):
        values = {'target_git_ref': target_branch}
        values.update(extras)
        return values

    def test_default_branch(self):
        with admin_logged_in():
            target_branch = self._makeTargetBranch(target_default=True)
        removeSecurityProxy(
            target_branch.repository)._default_branch = target_branch.path
        view = self._createView()
        self.assertEqual(
            target_branch.repository.default_branch.split('/')[-1],
            view.widgets['target_git_ref'].path_widget._getCurrentValue())

    def test_default_branch_no_default_set(self):
        with admin_logged_in():
            self._makeTargetBranch(target_default=True)
        view = self._createView()
        self.assertIsNone(
            view.widgets['target_git_ref'].path_widget._getCurrentValue())

    def test_default_branch_no_target(self):
        view = self._createView()
        self.assertIsNone(
            view.widgets['target_git_ref'].path_widget._getCurrentValue())

    def test_register_ajax_request_with_confirmation(self):
        # Ajax submits return json data containing info about what the visible
        # repositories are if they are not all visible to the reviewer.

        # Make a branch the reviewer cannot see.
        owner = self.factory.makePerson()
        target_branch = self._makeTargetBranch(
            owner=owner, information_type=InformationType.USERDATA)
        reviewer = self.factory.makePerson()
        extra = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        request = LaunchpadTestRequest(method='POST', **extra)
        request.setPrincipal(owner)
        view = self._createView(request=request)
        with person_logged_in(owner):
            repositories_to_check = [
                self.source_branch.repository.unique_name,
                target_branch.repository.unique_name]
            expected_data = {
                'person_name': reviewer.displayname,
                'repositories_to_check': repositories_to_check,
                'visible_repositories':
                    [self.source_branch.repository.unique_name]}
            result_data = view.register_action.success(self._getFormValues(
                target_branch, {
                    'reviewer': reviewer,
                    'needs_review': True,
                    }))
        self.assertEqual(
            '400 Repository Visibility',
            view.request.response.getStatusString())
        self.assertEqual(expected_data, simplejson.loads(result_data))

    def test_register_ajax_request_with_validation_errors(self):
        # Ajax submits where there is a validation error in the submitted data
        # return the expected json response containing the error info.
        owner = self.factory.makePerson()
        target_branch = self._makeTargetBranch(
            owner=owner, information_type=InformationType.USERDATA)
        extra = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        with person_logged_in(owner):
            request = LaunchpadTestRequest(
                method='POST',
                form={
                    'field.actions.register': 'Propose Merge',
                    'field.target_git_ref.repository':
                        target_branch.repository.unique_name,
                    'field.target_git_ref.path': target_branch.path,
                    },
                **extra)
            request.setPrincipal(owner)
            view = create_initialized_view(
                target_branch,
                name='+register-merge',
                request=request)
        self.assertEqual(
            '400 Validation', view.request.response.getStatusString())
        self.assertEqual(
            {'error_summary': 'There is 1 error.',
            'errors': {
                'field.target_git_ref':
                    ('The target repository and path together cannot be the '
                     'same as the source repository and path.')},
            'form_wide_errors': []},
            simplejson.loads(view.form_result))

    def test_register_ajax_request_with_missing_target_git_repository(self):
        # A missing target_git_repository is a validation error.
        owner = self.factory.makePerson()
        extra = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        with person_logged_in(owner):
            request = LaunchpadTestRequest(
                method='POST',
                form={
                    'field.actions.register': 'Propose Merge',
                    'field.target_git_ref.repository': '',
                    'field.target_git_ref.repository-empty-marker': '1',
                    'field.target_git_ref.path': 'master',
                    },
                **extra)
            request.setPrincipal(owner)
            view = create_initialized_view(
                self.source_branch,
                name='+register-merge',
                request=request)
        self.assertEqual(
            '400 Validation', view.request.response.getStatusString())
        self.assertEqual(
            {'error_summary': 'There is 1 error.',
            'errors': {
                'field.target_git_ref': 'Required input is missing.',
                },
            'form_wide_errors': []},
            simplejson.loads(view.form_result))

    def test_register_ajax_request_with_missing_target_git_path(self):
        # A missing target_git_path is a validation error.
        owner = self.factory.makePerson()
        target_branch = self._makeTargetBranch(
            owner=owner, information_type=InformationType.USERDATA)
        transaction.commit()
        extra = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        with person_logged_in(owner):
            request = LaunchpadTestRequest(
                method='POST',
                form={
                    'field.actions.register': 'Propose Merge',
                    'field.target_git_ref.repository':
                        target_branch.repository.unique_name,
                    },
                **extra)
            request.setPrincipal(owner)
            view = create_initialized_view(
                self.source_branch,
                name='+register-merge',
                request=request)
        self.assertEqual(
            '400 Validation', view.request.response.getStatusString())
        self.assertEqual(
            {'error_summary': 'There is 1 error.',
            'errors': {
                'field.target_git_ref':
                    'Please enter a Git branch path.'},
            'form_wide_errors': []},
            simplejson.loads(view.form_result))

    def test_register_ajax_request_with_missing_prerequisite_git_path(self):
        # A missing prerequisite_git_path is a validation error if
        # prerequisite_git_repository is present.
        owner = self.factory.makePerson()
        target_branch = self._makeTargetBranch(
            owner=owner, information_type=InformationType.USERDATA)
        prerequisite_branch = self._makeTargetBranch(
            owner=owner, information_type=InformationType.USERDATA)
        transaction.commit()
        extra = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        with person_logged_in(owner):
            request = LaunchpadTestRequest(
                method='POST',
                form={
                    'field.actions.register': 'Propose Merge',
                    'field.target_git_ref.repository':
                        target_branch.repository.unique_name,
                    'field.target_git_ref.path': target_branch.path,
                    'field.prerequisite_git_ref.repository':
                        prerequisite_branch.repository.unique_name,
                    },
                **extra)
            request.setPrincipal(owner)
            view = create_initialized_view(
                self.source_branch,
                name='+register-merge',
                request=request)
        self.assertEqual(
            '400 Validation', view.request.response.getStatusString())
        self.assertEqual(
            {'error_summary': 'There is 1 error.',
            'errors': {
                'field.prerequisite_git_ref':
                    'Please enter a Git branch path.'},
            'form_wide_errors': []},
            simplejson.loads(view.form_result))


class TestBranchMergeProposalRequestReviewViewMixin:
    """Test `BranchMergeProposalRequestReviewView`."""

    layer = DatabaseFunctionalLayer

    def test_notifies_modification(self):
        bmp = self.makeBranchMergeProposal()
        registrant = bmp.registrant
        self.factory.makePerson(name='test-reviewer')
        login_person(registrant)
        browser = self.getViewBrowser(
            bmp, '+request-review', user=bmp.registrant)
        browser.getControl('Reviewer').value = 'test-reviewer'
        with EventRecorder(propagate=True) as recorder:
            browser.getControl('Request Review').click()
        login_person(registrant)
        events = [
            event for event in recorder.events
            if isinstance(event, ObjectModifiedEvent) and
               IBranchMergeProposal.providedBy(event.object)]
        self.assertThat(events, MatchesListwise([
            MatchesStructure(
                object_before_modification=MatchesStructure.byEquality(
                    queue_status=BranchMergeProposalStatus.WORK_IN_PROGRESS),
                object=MatchesStructure.byEquality(
                    queue_status=BranchMergeProposalStatus.NEEDS_REVIEW))]))


class TestBranchMergeProposalRequestReviewViewBzr(
    TestBranchMergeProposalRequestReviewViewMixin, BrowserTestCase):
    """Test `BranchMergeProposalRequestReviewView` for Bazaar."""

    def makeBranchMergeProposal(self):
        return self.factory.makeBranchMergeProposal()


class TestBranchMergeProposalRequestReviewViewGit(
    TestBranchMergeProposalRequestReviewViewMixin, GitHostingClientMixin,
    BrowserTestCase):
    """Test `BranchMergeProposalRequestReviewView` for Git."""

    def makeBranchMergeProposal(self):
        return self.factory.makeBranchMergeProposalForGit()


class TestBranchMergeProposalResubmitViewMixin:
    """Test BranchMergeProposalResubmitView."""

    layer = DatabaseFunctionalLayer

    def createView(self):
        """Create the required view."""
        context = self._makeBranchMergeProposal()
        self.useContext(person_logged_in(context.registrant))
        view = BranchMergeProposalResubmitView(
            context, LaunchpadTestRequest())
        view.initialize()
        return view

    def test_resubmit_action(self):
        """resubmit_action resubmits the proposal."""
        view = self.createView()
        context = view.context
        new_proposal = view.resubmit_action.success(self._getFormValues(
            context.merge_source, context.merge_target,
            context.merge_prerequisite, {
                'commit_message': None,
                'description': None,
                'break_link': False,
                }))
        self.assertEqual(new_proposal.supersedes, context)
        self.assertEqual(new_proposal.merge_source, context.merge_source)
        self.assertEqual(new_proposal.merge_target, context.merge_target)
        self.assertEqual(
            new_proposal.merge_prerequisite, context.merge_prerequisite)

    def test_resubmit_action_change_branches(self):
        """Changing the branches changes the branches in the new proposal."""
        view = self.createView()
        new_source = self._makeBranchWithSameTarget(view.context.merge_source)
        new_target = self._makeBranchWithSameTarget(view.context.merge_source)
        new_prerequisite = self._makeBranchWithSameTarget(
            view.context.merge_source)
        new_proposal = view.resubmit_action.success(self._getFormValues(
            new_source, new_target, new_prerequisite, {
                'commit_message': 'a commit',
                'description': 'description',
                'break_link': False,
                }))
        self.assertEqual(new_proposal.supersedes, view.context)
        self.assertEqual(new_proposal.merge_source, new_source)
        self.assertEqual(new_proposal.merge_target, new_target)
        self.assertEqual(new_proposal.merge_prerequisite, new_prerequisite)

    def test_resubmit_action_break_link(self):
        """Enabling break_link prevents linking the old and new proposals."""
        view = self.createView()
        new_proposal = self.resubmitDefault(view, break_link=True)
        self.assertIs(None, new_proposal.supersedes)

    @classmethod
    def resubmitDefault(cls, view, break_link=False, merge_prerequisite=None):
        context = view.context
        if merge_prerequisite is None:
            merge_prerequisite = context.merge_prerequisite
        return view.resubmit_action.success(cls._getFormValues(
            context.merge_source, context.merge_target, merge_prerequisite, {
                'commit_message': None,
                'description': None,
                'break_link': break_link,
                }))

    def test_resubmit_existing(self):
        """Resubmitting a proposal when another is active is a user error."""
        view = self.createView()
        first_bmp = view.context
        with person_logged_in(first_bmp.merge_target.owner):
            first_bmp.resubmit(first_bmp.registrant)
        self.resubmitDefault(view)
        (notification,) = view.request.response.notifications
        self.assertThat(
            notification.message, MatchesRegex('Cannot resubmit because'
            ' <a href=.*>a similar merge proposal</a> is already active.'))
        self.assertEqual(BrowserNotificationLevel.ERROR, notification.level)

    def test_notifies_modification(self):
        view = self.createView()
        with EventRecorder(propagate=True) as recorder:
            self.resubmitDefault(view)
        events = [
            event for event in recorder.events
            if isinstance(event, ObjectModifiedEvent) and
               IBranchMergeProposal.providedBy(event.object)]
        self.assertThat(events, MatchesListwise([
            MatchesStructure(
                object_before_modification=MatchesStructure.byEquality(
                    queue_status=BranchMergeProposalStatus.WORK_IN_PROGRESS),
                object=MatchesStructure.byEquality(
                    queue_status=BranchMergeProposalStatus.SUPERSEDED))]))

    def test_mail_jobs(self):
        """Resubmitting sends mail about the changed old MP and the new MP."""
        view = self.createView()
        new_proposal = self.resubmitDefault(view)
        updated_job_source = getUtility(IMergeProposalUpdatedEmailJobSource)
        [updated_job] = list(
            removeSecurityProxy(updated_job_source).iterReady())
        self.assertThat(updated_job, MatchesStructure.byEquality(
            branch_merge_proposal=view.context,
            metadata={
                'delta_text': '    Status: Work in progress => Superseded',
                'editor': view.context.registrant.name,
                }))
        needs_review_job_source = getUtility(
            IMergeProposalNeedsReviewEmailJobSource)
        [needs_review_job] = list(
            removeSecurityProxy(needs_review_job_source).iterReady())
        self.assertThat(needs_review_job, MatchesStructure.byEquality(
            branch_merge_proposal=new_proposal,
            metadata={}))


class TestBranchMergeProposalResubmitViewBzr(
    TestBranchMergeProposalResubmitViewMixin, TestCaseWithFactory):
    """Test BranchMergeProposalResubmitView for Bazaar."""

    def _makeBranchMergeProposal(self):
        bmp = self.factory.makeBranchMergeProposal()
        # Pretend to have a revision so that
        # BranchMergeProposalJobDerived.iterReady will consider this
        # proposal.
        removeSecurityProxy(bmp.source_branch).revision_count = 1
        return bmp

    @staticmethod
    def _getFormValues(source_branch, target_branch, prerequisite_branch,
                       extras):
        values = {
            'source_branch': source_branch,
            'target_branch': target_branch,
            'prerequisite_branch': prerequisite_branch,
            }
        values.update(extras)
        return values

    def _makeBranchWithSameTarget(self, branch):
        return self.factory.makeBranchTargetBranch(branch.target)

    def test_resubmit_same_target_prerequisite(self):
        """User error if same branch is target and prerequisite."""
        view = self.createView()
        first_bmp = view.context
        self.resubmitDefault(view, merge_prerequisite=first_bmp.merge_target)
        self.assertEqual(
            view.errors,
            ['Target and prerequisite branches must be different.'])


class TestBranchMergeProposalResubmitViewGit(
    TestBranchMergeProposalResubmitViewMixin, TestCaseWithFactory):
    """Test BranchMergeProposalResubmitView for Git."""

    def _makeBranchMergeProposal(self):
        return self.factory.makeBranchMergeProposalForGit()

    @staticmethod
    def _getFormValues(source_branch, target_branch, prerequisite_branch,
                       extras):
        values = {
            'source_git_ref': source_branch,
            'target_git_ref': target_branch
            }
        if prerequisite_branch is not None:
            values.update({
                'prerequisite_git_ref': prerequisite_branch
                })
        else:
            values.update({
                'prerequisite_git_repository': None,
                'prerequisite_git_path': '',
                })
        values.update(extras)
        return values

    def _makeBranchWithSameTarget(self, branch):
        return self.factory.makeGitRefs(target=branch.target)[0]

    def test_resubmit_same_target_prerequisite(self):
        """User error if same branch is target and prerequisite."""
        view = self.createView()
        first_bmp = view.context
        self.resubmitDefault(view, merge_prerequisite=first_bmp.merge_target)
        self.assertEqual(
            view.errors,
            ['Target and prerequisite references must be different.'])


class TestResubmitBrowserBzr(BrowserTestCase):
    """Browser tests for resubmitting branch merge proposals for Bazaar."""

    layer = DatabaseFunctionalLayer

    def test_resubmit_text(self):
        """The text of the resubmit page is as expected."""
        bmp = self.factory.makeBranchMergeProposal(registrant=self.user)
        text = self.getMainText(bmp, '+resubmit')
        expected = (
            'Resubmit proposal to merge.*'
            'Source branch:.*'
            'Target branch:.*'
            'Prerequisite branch:.*'
            'Description.*'
            'Start afresh.*')
        self.assertTextMatchesExpressionIgnoreWhitespace(expected, text)

    def test_resubmit_controls(self):
        """Proposals can be resubmitted using the browser."""
        bmp = self.factory.makeBranchMergeProposal(registrant=self.user)
        browser = self.getViewBrowser(bmp, '+resubmit')
        browser.getControl('Description').value = 'flibble'
        browser.getControl('Resubmit').click()
        with person_logged_in(self.user):
            self.assertEqual('flibble', bmp.superseded_by.description)


class TestResubmitBrowserGit(GitHostingClientMixin, BrowserTestCase):
    """Browser tests for resubmitting branch merge proposals for Git."""

    layer = DatabaseFunctionalLayer

    def test_resubmit_text(self):
        """The text of the resubmit page is as expected."""
        bmp = self.factory.makeBranchMergeProposalForGit(registrant=self.user)
        text = self.getMainText(bmp, '+resubmit')
        self.assertTextMatchesExpressionIgnoreWhitespace(r"""
            Resubmit proposal to merge.*
            Source Git branch:.*
            Repository: \(Find…\) Branch: \(Find…\)
            Target Git branch:.*
            Repository: \(Find…\) Branch: \(Find…\)
            Prerequisite Git branch:.*
            Repository: \(Find…\) Branch: \(Find…\)
            Description.*
            Start afresh.*
            """, text)

    def test_resubmit_controls(self):
        """Proposals can be resubmitted using the browser."""
        bmp = self.factory.makeBranchMergeProposalForGit(registrant=self.user)
        browser = self.getViewBrowser(bmp, '+resubmit')
        browser.getControl('Commit message').value = 'dribble'
        browser.getControl('Description').value = 'flibble'
        browser.getControl('Resubmit').click()
        with person_logged_in(self.user):
            self.assertEqual('dribble', bmp.superseded_by.commit_message)
            self.assertEqual('flibble', bmp.superseded_by.description)


class TestBranchMergeProposalView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.user = self.factory.makePerson()
        self.bmp = self.factory.makeBranchMergeProposal(registrant=self.user)
        login_person(self.user)

    def makeTeamReview(self):
        owner = self.bmp.source_branch.owner
        review_team = self.factory.makeTeam()
        return self.bmp.nominateReviewer(review_team, owner)

    def test_claim_action_team_member(self):
        """Claiming a review works for members of the requested team."""
        review = self.makeTeamReview()
        albert = self.factory.makePerson()
        removeSecurityProxy(albert).join(review.reviewer)
        login_person(albert)
        view = create_initialized_view(self.bmp, '+index')
        view.claim_action.success({'review_id': review.id})
        self.assertEqual(albert, review.reviewer)

    def test_claim_action_non_member(self):
        """Claiming a review does not work for non-members."""
        review = self.makeTeamReview()
        albert = self.factory.makePerson()
        login_person(albert)
        view = create_initialized_view(self.bmp, '+index')
        self.assertRaises(Unauthorized, view.claim_action.success,
                          {'review_id': review.id})

    def test_claim_no_oops(self):
        """"An invalid attempt to claim a review should not oops."""
        review = self.factory.makeCodeReviewVoteReference()
        view = create_initialized_view(review.branch_merge_proposal, '+index')
        view.claim_action.success({'review_id': review.id})
        self.assertEqual(
            ['Cannot claim non-team reviews.'],
            [n.message for n in view.request.response.notifications])

    def test_preview_diff_text_with_no_diff(self):
        """preview_diff_text should be None if context has no preview_diff."""
        view = create_initialized_view(self.bmp, '+index')
        self.assertIs(None, view.preview_diff_text)

    def test_preview_diff_utf8(self):
        """A preview_diff in utf-8 should be decoded as utf-8."""
        text = ''.join(chr(x) for x in range(255))
        diff = ''.join(unified_diff([''], [text])).encode('utf-8')
        self.setPreviewDiff(diff)
        transaction.commit()
        view = create_initialized_view(self.bmp, '+index')
        self.assertEqual(diff.decode('utf-8'), view.preview_diff_text)
        self.assertTrue(view.diff_available)

    def test_preview_diff_all_chars(self):
        """preview_diff should work on diffs containing all possible bytes."""
        text = b''.join(bytes((x,)) for x in range(255))
        diff = b''.join(diff_bytes(unified_diff, [b''], [text]))
        self.setPreviewDiff(diff)
        transaction.commit()
        view = create_initialized_view(self.bmp, '+index')
        self.assertEqual(diff.decode('windows-1252', 'replace'),
                         view.preview_diff_text)
        self.assertTrue(view.diff_available)

    def test_preview_diff_timeout(self):
        # The preview_diff will recover from a timeout set to get the
        # librarian content.
        text = b''.join(bytes((x,)) for x in range(255))
        diff = b''.join(diff_bytes(unified_diff, [b''], [text]))
        preview_diff = self.setPreviewDiff(diff)
        transaction.commit()

        def fake_open(*args):
            raise LibrarianServerError

        lfa = preview_diff.diff.diff_text
        with monkey_patch(lfa, open=fake_open):
            view = create_initialized_view(preview_diff, '+diff')
            self.assertEqual('', view.preview_diff_text)
            self.assertFalse(view.diff_available)
            markup = view()
            self.assertIn('The diff is not available at this time.', markup)

    def test_preview_diff_lookup_error(self):
        # The preview_diff will recover from a LookupError while getting the
        # librarian content.  (This can happen e.g. on staging replicas of
        # the production database.)
        text = b''.join(bytes((x,)) for x in range(255))
        diff = b''.join(diff_bytes(unified_diff, [b''], [text]))
        preview_diff = self.setPreviewDiff(diff)
        transaction.commit()

        def fake_open(*args):
            raise LookupError

        lfa = preview_diff.diff.diff_text
        with monkey_patch(lfa, open=fake_open):
            view = create_initialized_view(preview_diff, '+diff')
            self.assertEqual('', view.preview_diff_text)
            self.assertFalse(view.diff_available)
            markup = view()
            self.assertIn('The diff is not available at this time.', markup)

    def setPreviewDiff(self, preview_diff_bytes):
        return PreviewDiff.create(
            self.bmp, preview_diff_bytes, 'a', 'b', None, '')

    def test_linked_bugtasks_excludes_mutual_bugs(self):
        """List bugs that are linked to the source only."""
        bug = self.factory.makeBug()
        self.bmp.source_branch.linkBug(bug, self.bmp.registrant)
        self.bmp.target_branch.linkBug(bug, self.bmp.registrant)
        view = create_initialized_view(self.bmp, '+index')
        self.assertEqual([], view.linked_bugtasks)

    def test_linked_bugtasks_excludes_private_bugs(self):
        """List bugs that are linked to the source only."""
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        private_bug = self.factory.makeBug(
            owner=person, information_type=InformationType.USERDATA)
        self.bmp.source_branch.linkBug(bug, self.bmp.registrant)
        with person_logged_in(person):
            self.bmp.source_branch.linkBug(private_bug, self.bmp.registrant)
        view = create_initialized_view(self.bmp, '+index')
        self.assertEqual([bug.default_bugtask], view.linked_bugtasks)

    def test_linked_bugtasks_includes_direct_links(self):
        # linked_bugtasks includes bugs that are linked directly to the
        # merge proposal, as is the case for Git-based MPs.
        bug = self.factory.makeBug()
        bmp = self.factory.makeBranchMergeProposalForGit(registrant=self.user)
        bmp.linkBug(bug, bmp.registrant)
        view = create_initialized_view(bmp, '+index')
        self.assertEqual([bug.default_bugtask], view.linked_bugtasks)

    def makeRevisionGroups(self):
        review_date = datetime(2009, 9, 10, tzinfo=pytz.UTC)
        bmp = self.factory.makeBranchMergeProposal(
            date_created=review_date)
        first_commit = datetime(2009, 9, 9, tzinfo=pytz.UTC)
        add_revision_to_branch(
            self.factory, bmp.source_branch, first_commit)
        login_person(bmp.registrant)
        bmp.requestReview(review_date)
        revision_date = review_date + timedelta(days=1)
        revisions = []
        for date in range(2):
            revisions.append(
                add_revision_to_branch(
                    self.factory, bmp.source_branch, revision_date))
            revisions.append(
                add_revision_to_branch(
                    self.factory, bmp.source_branch, revision_date))
            revision_date += timedelta(days=1)
        return bmp, revisions

    def test_getRevisionsIncludesIncrementalDiffs(self):
        bmp, revisions = self.makeRevisionGroups()
        diff = self.factory.makeIncrementalDiff(merge_proposal=bmp,
                old_revision=revisions[1].revision.getLefthandParent(),
                new_revision=revisions[3].revision)
        self.useContext(feature_flags())
        set_feature_flag('code.incremental_diffs.enabled', 'enabled')
        view = create_initialized_view(bmp, '+index')
        comments = view.conversation.comments
        self.assertEqual(
            [diff],
            [comment.diff for comment in comments])

    def test_CodeReviewNewRevisions_implements_interface_bzr(self):
        # The browser helper class implements its interface.
        review_date = datetime(2009, 9, 10, tzinfo=pytz.UTC)
        revision_date = review_date + timedelta(days=1)
        bmp = self.factory.makeBranchMergeProposal(
            date_created=review_date)
        add_revision_to_branch(self.factory, bmp.source_branch, revision_date)

        view = create_initialized_view(bmp, '+index')
        new_revisions = view.conversation.comments[0]

        self.assertTrue(verifyObject(ICodeReviewNewRevisions, new_revisions))

    def test_CodeReviewNewRevisions_implements_interface_git(self):
        # The browser helper class implements its interface.
        review_date = datetime(2009, 9, 10, tzinfo=pytz.UTC)
        author = self.factory.makePerson()
        with person_logged_in(author):
            author_email = author.preferredemail.email
        review_date = self.factory.getUniqueDate()
        commit_date = self.factory.getUniqueDate()
        bmp = self.factory.makeBranchMergeProposalForGit(
            date_created=review_date)
        self.useFixture(GitHostingFixture(log=[
            {
                'sha1': six.ensure_text(hashlib.sha1(b'0').hexdigest()),
                'message': '0',
                'author': {
                    'name': author.display_name,
                    'email': author_email,
                    'time': int(seconds_since_epoch(commit_date)),
                    },
                }
            ]))

        view = create_initialized_view(bmp, '+index')
        new_commits = view.conversation.comments[0]

        self.assertTrue(verifyObject(ICodeReviewNewRevisions, new_commits))

    def test_include_superseded_comments(self):
        for x, time in zip(range(3), time_counter()):
            if x != 0:
                self.bmp = self.bmp.resubmit(self.user)
            self.bmp.createComment(
                self.user, 'comment %d' % x, _date_created=time)
        view = create_initialized_view(self.bmp, '+index')
        self.assertEqual(
            ['comment 0', 'comment 1', 'comment 2'],
            [comment.comment.message.subject for comment
             in view.conversation.comments])
        self.assertFalse(view.conversation.comments[2].from_superseded)
        self.assertTrue(view.conversation.comments[1].from_superseded)
        self.assertTrue(view.conversation.comments[0].from_superseded)

    def test_pending_diff_with_pending_branch(self):
        bmp = self.factory.makeBranchMergeProposal()
        bmp.next_preview_diff_job.start()
        bmp.next_preview_diff_job.fail()
        view = create_initialized_view(bmp, '+index')
        self.assertFalse(view.pending_diff)
        with person_logged_in(bmp.source_branch.owner):
            bmp.source_branch.branchChanged(None, 'rev-1', None, None, None)
        self.assertTrue(view.pending_diff)

    def test_pending_diff_with_pending_git_repository(self):
        bmp = self.factory.makeBranchMergeProposalForGit()
        bmp.next_preview_diff_job.start()
        bmp.next_preview_diff_job.fail()
        view = create_initialized_view(bmp, '+index')
        self.assertFalse(view.pending_diff)
        git_api = GitAPI(None, None)
        self.assertIsNone(
            git_api.notify(bmp.source_git_repository.getInternalPath(),
                           {'loose_object_count': 5, 'pack_count': 2},
                           {'uid': bmp.source_git_repository.owner.id}))
        self.assertTrue(view.pending_diff)

    def test_description_is_meta_description(self):
        description = (
            "I'd like to make the bmp description appear as the meta "
            "description: this does that "
            + "abcdef " * 300)
        bmp = self.factory.makeBranchMergeProposal(
            description=description)
        browser = self.getUserBrowser(
            canonical_url(bmp, rootsite='code'))
        expected_meta = Tag(
            'meta description',
            'meta', attrs=dict(
                name='description',
                content=description[:497] + '...'))
        self.assertThat(browser.contents, HTMLContains(expected_meta))

    def test_revisionStatusReports_display(self):
        bmp = self.factory.makeBranchMergeProposalForGit()
        sha1 = six.ensure_text(hashlib.sha1(b'0').hexdigest())
        commit_date = datetime(2015, 1, 1, tzinfo=pytz.UTC)
        report1 = self.factory.makeRevisionStatusReport(
            user=bmp.source_git_repository.owner,
            git_repository=bmp.source_git_repository,
            title="CI", commit_sha1=sha1,
            result_summary="120/120 tests passed",
            url="https://foo.com",
            result=RevisionStatusResult.SUCCEEDED)

        self.useFixture(GitHostingFixture(log=[
            {
                'sha1': sha1,
                'message': 'Sample message',
                'author': {
                    'name': 'Example Person',
                    'email': 'person@example.org',
                    'time': int(seconds_since_epoch(commit_date)),
                    },
                }
            ]))

        browser = self.getUserBrowser(canonical_url(bmp, rootsite='code'),
                                      user=bmp.source_git_repository.owner)

        reports_section = find_tags_by_class(browser.contents,
                                             "status-reports-table")
        with person_logged_in(bmp.source_git_repository.owner):
            self.assertThat(
                reports_section[0],
                Within(
                    Tag("first report title", "td"),
                    Tag(
                        "first report link", "a", text=report1.title,
                        attrs={"href": report1.url})))

            self.assertThat(
                reports_section[0],
                Tag(
                    "first report summary", "td",
                    text=report1.result_summary))

            # Ensure we don't display an empty expander for those commits
            # that do not have status reports created for them - means we
            # should only see one entry with class 'status-reports-table'
            # on the page: reports_section[0]
            self.assertTrue(len(reports_section) == 1)

    def test_unmerged_commits_from_deleted_git_ref(self):
        # Even if the source Git ref has been deleted, we still know its tip
        # SHA-1 and can ask the repository for its unmerged commits.
        bmp = self.factory.makeBranchMergeProposalForGit()
        sha1 = six.ensure_text(hashlib.sha1(b'0').hexdigest())
        commit_date = datetime(2015, 1, 1, tzinfo=pytz.UTC)
        self.useFixture(GitHostingFixture(log=[
            {
                'sha1': sha1,
                'message': 'Sample message',
                'author': {
                    'name': 'Example Person',
                    'email': 'person@example.org',
                    'time': int(seconds_since_epoch(commit_date)),
                    },
                }
            ]))
        bmp.source_git_repository.removeRefs([bmp.source_git_path])
        browser = self.getUserBrowser(canonical_url(bmp, rootsite='code'),
                                      user=bmp.source_git_repository.owner)
        tag = first_tag_by_class(browser.contents, 'commit-details')
        self.assertEqual(
            "%.7s...\nby\nExample Person &lt;person@example.org&gt;\n"
            "on 2015-01-01" % sha1, extract_text(tag))

    def test_client_cache_bzr(self):
        # For Bazaar, the client cache contains the branch name and a link
        # to the Loggerhead diff via the webapp.
        bmp = self.factory.makeBranchMergeProposal()
        view = create_initialized_view(bmp, '+index')
        cache = IJSONRequestCache(view.request)
        self.assertThat(cache.objects, ContainsDict({
            'branch_name': Equals(bmp.source_branch.name),
            'branch_diff_link': Equals(
                'http://code.launchpad.test/%s/+diff/' %
                bmp.source_branch.unique_name),
            }))

    def test_client_cache_bzr_proxy_feature_disabled(self):
        # For Bazaar, a feature flag can be set to cause the client cache to
        # contain a direct link to the Loggerhead diff rather than via the
        # webapp.  (This only works for public branches.)
        self.useFixture(
            FeatureFixture({'code.bzr.diff.disable_proxy': 'on'}))
        bmp = self.factory.makeBranchMergeProposal()
        view = create_initialized_view(bmp, '+index')
        cache = IJSONRequestCache(view.request)
        self.assertThat(cache.objects, ContainsDict({
            'branch_name': Equals(bmp.source_branch.name),
            'branch_diff_link': Equals(
                'https://code.launchpad.test/+loggerhead/%s/diff/' %
                bmp.source_branch.unique_name),
            }))

    def test_client_cache_git(self):
        # For Git, the client cache contains the ref name and a webapp-based
        # diff link.
        bmp = self.factory.makeBranchMergeProposalForGit()
        view = create_initialized_view(bmp, '+index')
        cache = IJSONRequestCache(view.request)
        self.assertThat(cache.objects, ContainsDict({
            'branch_name': Equals(bmp.source_git_ref.name),
            'branch_diff_link': Equals(
                'http://code.launchpad.test/%s/+diff/' %
                bmp.source_git_repository.unique_name),
            }))

    def test_breadcrumbs_bzr(self):
        bmp = self.factory.makeBranchMergeProposal()
        view = create_view(bmp, '+index', principal=self.user)
        # To test the breadcrumbs we need a correct traversal stack.
        view.request.traversed_objects = [bmp.source_branch, bmp, view]
        view.initialize()
        breadcrumbs_tag = Tag(
            'breadcrumbs', 'ol', attrs={'class': 'breadcrumbs'})
        self.assertThat(
            view(),
            HTMLContains(
                Within(
                    breadcrumbs_tag,
                    Tag(
                        'branch breadcrumb', 'a', text=bmp.source_branch.name,
                        attrs={
                            'href': 'http://code.launchpad.test/%s' % (
                                bmp.source_branch.unique_name)})),
                Within(
                    breadcrumbs_tag,
                    Tag(
                        'merge proposal breadcrumb', 'li',
                        text=re.compile(
                            r'\sMerge into %s\s' %
                            re.escape(bmp.target_branch.name))))))

    def test_breadcrumbs_git(self):
        self.useFixture(GitHostingFixture())
        bmp = self.factory.makeBranchMergeProposalForGit()
        view = create_view(bmp, '+index', principal=self.user)
        # To test the breadcrumbs we need a correct traversal stack.
        view.request.traversed_objects = [bmp.source_git_repository, bmp, view]
        view.initialize()
        breadcrumbs_tag = Tag(
            'breadcrumbs', 'ol', attrs={'class': 'breadcrumbs'})
        self.assertThat(
            view(),
            HTMLContains(
                Within(
                    breadcrumbs_tag,
                    Tag(
                        'git collection breadcrumb', 'a', text='Git',
                        attrs={'href': re.compile(r'/\+git$')})),
                Within(
                    breadcrumbs_tag,
                    Tag(
                        'git repository breadcrumb', 'a',
                        text=bmp.source_git_repository.git_identity,
                        attrs={
                            'href': 'http://code.launchpad.test/%s' % (
                                bmp.source_git_repository.unique_name)})),
                Within(
                    breadcrumbs_tag,
                    Tag(
                        'git ref breadcrumb', 'a',
                        text=bmp.source_git_ref.name,
                        attrs={
                            'href': 'http://code.launchpad.test/%s/+ref/%s' % (
                                bmp.source_git_repository.unique_name,
                                bmp.source_git_ref.name)})),
                Within(
                    breadcrumbs_tag,
                    Tag(
                        'merge proposal breadcrumb', 'li',
                        text=re.compile(
                            r'\sMerge into %s\s' %
                            re.escape(bmp.target_git_ref.name))))))


class TestBranchMergeProposalBrowserView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        self.hosting_fixture = self.useFixture(GitHostingFixture())

    def test_prerequisite_bzr(self):
        # A prerequisite branch is rendered in the Bazaar case.
        branch = self.factory.makeProductBranch()
        identity = branch.identity
        bmp = self.factory.makeBranchMergeProposal(prerequisite_branch=branch)
        text = self.getMainText(bmp, '+index')
        self.assertTextMatchesExpressionIgnoreWhitespace(
            'Prerequisite: ' + re.escape(identity), text)

    def test_prerequisite_git(self):
        # A prerequisite reference is rendered in the Git case.
        self.useFixture(GitHostingFixture())
        [ref] = self.factory.makeGitRefs()
        identity = ref.identity
        bmp = self.factory.makeBranchMergeProposalForGit(prerequisite_ref=ref)
        text = self.getMainText(bmp, '+index')
        self.assertTextMatchesExpressionIgnoreWhitespace(
            'Prerequisite: ' + re.escape(identity), text)

    def test_git_hosting_calls(self):
        # Rendering a Git-based merge proposal makes the correct calls to
        # the hosting service, including requesting cross-repository
        # information.
        hosting_fixture = self.useFixture(GitHostingFixture())
        bmp = self.factory.makeBranchMergeProposalForGit()
        self.getMainText(bmp, '+index')
        self.assertThat(hosting_fixture.getLog.calls, MatchesSetwise(
            # _getNewerRevisions
            MatchesListwise([
                Equals((
                    '%s:%s' % (
                        bmp.target_git_repository.getInternalPath(),
                        bmp.source_git_repository.getInternalPath()),
                    bmp.source_git_commit_sha1,
                    )),
                MatchesDict({
                    'stop': Equals(bmp.target_git_commit_sha1),
                    'limit': Is(None),
                    'logger': Is(None),
                    }),
                ]),
            # getUnlandedSourceBranchRevisions
            MatchesListwise([
                Equals((
                    '%s:%s' % (
                        bmp.target_git_repository.getInternalPath(),
                        bmp.source_git_repository.getInternalPath()),
                    bmp.source_git_commit_sha1,
                    )),
                MatchesDict({
                    'stop': Equals(bmp.target_git_commit_sha1),
                    'limit': Equals(10),
                    'logger': Is(None),
                    }),
                ]),
            ))

    def test_merge_guidelines_package(self):
        # Repository is the default for a package
        mint = self.factory.makeDistribution(name="mint")
        eric = self.factory.makePerson(name="eric")
        other_user = self.factory.makePerson()
        source_owner = self.factory.makePerson()

        mint_choc = self.factory.makeDistributionSourcePackage(
            distribution=mint, sourcepackagename="choc")
        repository = self.factory.makeGitRepository(
            owner=eric, target=mint_choc, name="choc-repo")
        source_repository = self.factory.makeGitRepository(
            owner=source_owner, target=mint_choc, name="choc-repo")
        [ref] = self.factory.makeGitRefs(repository=repository,
                                         paths=["refs/heads/master"])
        [source_ref] = self.factory.makeGitRefs(repository=source_repository,
                                         paths=["refs/heads/branch"])
        dsp = repository.target
        self.repository_set = getUtility(IGitRepositorySet)
        with admin_logged_in():
            self.repository_set.setDefaultRepositoryForOwner(
                repository.owner, dsp, repository, repository.owner)
            self.repository_set.setDefaultRepository(dsp, repository)
        bmp = self.factory.makeBranchMergeProposalForGit(
            source_ref=source_ref,
            target_ref=ref)
        login_person(other_user)
        view = create_initialized_view(bmp, "+index", principal=other_user)
        git_add_remote_match = HTMLContains(Tag(
            'Git remote add text', 'tt',
            attrs={"id": "remote-add"},
            text=("git remote add %s "
                  "git+ssh://%s@git.launchpad.test/~%s/%s/+source/choc/+git/%s"
                  ) % (source_owner.name,
                       other_user.name,
                       source_owner.name,
                       mint.name,
                       repository.name)))
        git_remote_update_match = HTMLContains(
            Tag(
                'Git remote update text', 'tt',
                attrs={"id": "remote-update"},
                text=("git remote update %s" % source_owner.name)))
        git_checkout_match = HTMLContains(
            Tag(
                'Checkout command text', 'tt',
                attrs={"id": "checkout-cmd"},
                text="git checkout %s" % bmp.merge_target.name))
        git_merge_match = HTMLContains(
            Tag(
                'Merge command text', 'tt',
                attrs={"id": "merge-cmd"},
                text="git merge %s/branch" % source_owner.name))

        with person_logged_in(other_user):
            rendered_view = view.render()
            self.assertThat(rendered_view, git_add_remote_match)
            self.assertThat(rendered_view, git_remote_update_match)
            self.assertThat(rendered_view, git_checkout_match)
            self.assertThat(rendered_view, git_merge_match)

    def test_merge_guidelines_project(self):
        # Repository is the default for a project
        eric = self.factory.makePerson(name="eric")
        other_user = self.factory.makePerson()
        source_owner = self.factory.makePerson()
        fooix = self.factory.makeProduct(name="fooix", owner=eric)
        repository = self.factory.makeGitRepository(
            owner=eric, target=fooix, name="fooix-repo")
        source_repository = self.factory.makeGitRepository(
            owner=source_owner, target=fooix, name="fooix-repo")
        [ref] = self.factory.makeGitRefs(repository=repository,
                                         paths=["refs/heads/master"])
        [source_ref] = self.factory.makeGitRefs(repository=source_repository,
                                         paths=["refs/heads/branch"])

        self.repository_set = getUtility(IGitRepositorySet)
        with person_logged_in(fooix.owner) as user:
            self.repository_set.setDefaultRepositoryForOwner(
                repository.owner, fooix, repository, user)
            self.repository_set.setDefaultRepository(fooix, repository)
        bmp = self.factory.makeBranchMergeProposalForGit(
            source_ref=source_ref,
            target_ref=ref)
        login_person(other_user)
        view = create_initialized_view(bmp, "+index", principal=other_user)
        git_add_remote_match = HTMLContains(Tag(
            'Git remote add text', 'tt',
            attrs={"id": "remote-add"},
            text=("git remote add %s "
                  "git+ssh://%s@git.launchpad.test/~%s/%s/+git/%s"
                  ) % (source_owner.name,
                       other_user.name,
                       source_owner.name,
                       fooix.name,
                       repository.name)))
        git_remote_update_match = HTMLContains(
            Tag(
                'Git remote update text', 'tt',
                attrs={"id": "remote-update"},
                text=("git remote update %s" % source_owner.name)))
        git_checkout_match = HTMLContains(
            Tag(
                'Checkout command text', 'tt',
                attrs={"id": "checkout-cmd"},
                text="git checkout %s" % bmp.merge_target.name))
        git_merge_match = HTMLContains(
            Tag(
                'Merge command text', 'tt',
                attrs={"id": "merge-cmd"},
                text="git merge %s/branch" % source_owner.name))

        with person_logged_in(other_user):
            rendered_view = view.render()
            self.assertThat(rendered_view, git_add_remote_match)
            self.assertThat(rendered_view, git_remote_update_match)
            self.assertThat(rendered_view, git_checkout_match)
            self.assertThat(rendered_view, git_merge_match)

    def test_merge_guidelines_anonymous_view(self):
        # Merge guidelines are mainly intended for maintainers merging
        # contributions, they might be a bit noisy otherwise, therefore
        # we do not show them on anonymous views.
        # There is of course the permissions aspect involved here that you can
        # do a local merge using only read permissions on the source branch.
        team = self.factory.makeTeam()
        self.factory.makePerson()
        other_user = self.factory.makePerson()
        fooix = self.factory.makeProduct(name="fooix")
        repository = self.factory.makeGitRepository(
            owner=team, target=fooix, name="fooix-repo")
        source_repository = self.factory.makeGitRepository(
            owner=other_user, target=fooix, name="fooix-repo")
        [ref] = self.factory.makeGitRefs(repository=repository,
                                         paths=["refs/heads/master"])
        [source_ref] = self.factory.makeGitRefs(repository=source_repository,
                                         paths=["refs/heads/branch"])
        bmp = self.factory.makeBranchMergeProposalForGit(
            source_ref=source_ref,
            target_ref=ref)
        with person_logged_in(other_user):
            view = create_initialized_view(bmp, "+index", principal=other_user)
        git_add_remote_match = HTMLContains(
            Tag(
                'Git remote add text', 'tt',
                attrs={"id": "remote-add"}))
        git_remote_update_match = HTMLContains(
            Tag(
                'Git remote update text', 'tt',
                attrs={"id": "remote-update"}))
        git_checkout_match = HTMLContains(
            Tag(
                'Checkout command text', 'tt',
                attrs={"id": "checkout-cmd"},
                text="git checkout %s" % bmp.merge_target.name))
        git_merge_match = HTMLContains(
            Tag(
                'Merge command text', 'tt',
                attrs={"id": "merge-cmd"}))

        rendered_view = view.render()
        self.assertThat(rendered_view, Not(git_add_remote_match))
        self.assertThat(rendered_view, Not(git_remote_update_match))
        self.assertThat(rendered_view, Not(git_checkout_match))
        self.assertThat(rendered_view, Not(git_merge_match))

    def test_merge_guidelines_personal(self):
        # Attempting to create an MP between personal projects
        # will fail.
        repository = self.factory.makeGitRepository(
            owner=self.user, target=self.user)
        [ref] = self.factory.makeGitRefs(repository=repository,
                                         paths=["refs/heads/master"])
        other_user = self.factory.makePerson()
        other_repository = self.factory.makeGitRepository(
            owner=other_user, target=other_user)
        [other_ref] = self.factory.makeGitRefs(repository=other_repository,
                                               paths=["refs/heads/branch"])
        self.assertRaises(InvalidBranchMergeProposal,
                          self.factory.makeBranchMergeProposalForGit,
                          source_ref=other_ref, target_ref=ref)


class TestBranchMergeProposalChangeStatusView(TestCaseWithFactory):
    """Test the +edit-status view."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.user = self.factory.makePerson()
        login_person(self.user)
        self.proposal = self.factory.makeBranchMergeProposal(
            registrant=self.user)

    def _createView(self, form=None):
        # Construct the view and initialize it.
        view = BranchMergeProposalChangeStatusView(
            self.proposal, LaunchpadTestRequest(form=form))
        view.initialize()
        return view

    def assertStatusVocabTokens(self, tokens, user):
        # Assert that the tokens specified are the only tokens in the
        # generated vocabulary.
        login_person(user)
        vocabulary = self._createView()._createStatusVocabulary()
        vocab_tokens = sorted(term.token for term in vocabulary)
        self.assertEqual(
            sorted(tokens), vocab_tokens)

    def assertAllStatusesAvailable(self, user, except_for=None):
        # All options should be available to the user, except for SUPERSEDED,
        # which is only provided through resubmit.
        desired_statuses = {
            'WORK_IN_PROGRESS', 'NEEDS_REVIEW', 'MERGED', 'CODE_APPROVED',
            'REJECTED'}
        if except_for is not None:
            desired_statuses -= set(except_for)
        self.assertStatusVocabTokens(desired_statuses, user)

    def test_createStatusVocabulary_non_reviewer(self):
        # Neither the source branch owner nor the registrant should be
        # able to approve or reject their own code (assuming they don't have
        # rights on the target branch).
        status_options = [
            'WORK_IN_PROGRESS', 'NEEDS_REVIEW', 'MERGED']
        self.assertStatusVocabTokens(
            status_options, user=self.proposal.source_branch.owner)
        self.assertStatusVocabTokens(
            status_options, user=self.proposal.registrant)

    def test_createStatusVocabulary_reviewer(self):
        # The registrant should not be able to approve or reject
        # their own code (assuming they don't have rights on the target
        # branch).
        self.assertAllStatusesAvailable(self.proposal.target_branch.owner)

    def test_createStatusVocabulary_non_reviewer_approved(self):
        # Once the branch has been approved, the source owner or the
        # registrant can queue the branch.
        self.proposal.approveBranch(
            self.proposal.target_branch.owner, 'some-revision')
        status_options = [
            'WORK_IN_PROGRESS', 'NEEDS_REVIEW', 'CODE_APPROVED', 'MERGED']
        self.assertStatusVocabTokens(
            status_options, user=self.proposal.source_branch.owner)
        self.assertStatusVocabTokens(
            status_options, user=self.proposal.registrant)

    def test_createStatusVocabulary_reviewer_approved(self):
        # The target branch owner's options are not changed by whether or not
        # the proposal is currently approved.
        self.proposal.approveBranch(
            self.proposal.target_branch.owner, 'some-revision')
        self.assertAllStatusesAvailable(
            user=self.proposal.target_branch.owner)

    def test_createStatusVocabulary_rejected(self):
        # Only reviewers can change rejected proposals to approved.  All other
        # options for rejected proposals are the same regardless of user.
        self.proposal.rejectBranch(
            self.proposal.target_branch.owner, 'some-revision')
        self.assertAllStatusesAvailable(
            user=self.proposal.source_branch.owner,
            except_for=['CODE_APPROVED'])
        self.assertAllStatusesAvailable(user=self.proposal.registrant,
            except_for=['CODE_APPROVED'])
        self.assertAllStatusesAvailable(
            user=self.proposal.target_branch.owner)

    def test_notifies_modification(self):
        view = self._createView(form={'revno': '1'})
        with EventRecorder(propagate=True) as recorder:
            view.update_action.success(
                {'queue_status': BranchMergeProposalStatus.NEEDS_REVIEW})
        events = [
            event for event in recorder.events
            if isinstance(event, ObjectModifiedEvent) and
               IBranchMergeProposal.providedBy(event.object)]
        self.assertThat(events, MatchesListwise([
            MatchesStructure(
                object_before_modification=MatchesStructure.byEquality(
                    queue_status=BranchMergeProposalStatus.WORK_IN_PROGRESS),
                object=MatchesStructure.byEquality(
                    queue_status=BranchMergeProposalStatus.NEEDS_REVIEW))]))

    def test_source_revid_bzr(self):
        view = self._createView()
        self.assertEqual(
            self.proposal.merge_source.last_scanned_id, view.source_revid)

    def test_source_revid_git(self):
        git_proposal = self.factory.makeBranchMergeProposalForGit()
        view = BranchMergeProposalChangeStatusView(
            git_proposal, LaunchpadTestRequest())
        self.assertEqual(
            git_proposal.merge_source.commit_sha1, view.source_revid)


class TestCodeReviewCommentVisibility(
        WithScenarios, BrowserTestCase, TestMessageVisibilityMixin):

    layer = DatabaseFunctionalLayer

    scenarios = [
        ('bzr', {'git': False}),
        ('git', {'git': True}),
        ]

    def makeHiddenMessage(self, comment_owner=None):
        """See `TestMessageVisibilityMixin`."""
        if self.git:
            self.useFixture(GitHostingFixture())
        comment = self.factory.makeCodeReviewComment(
            sender=comment_owner, body=self.comment_text, git=self.git)
        with admin_logged_in():
            comment.message.visible = False
        return comment.branch_merge_proposal

    def getView(self, context, user=None, no_login=False):
        """See `TestMessageVisibilityMixin`."""
        return self.getViewBrowser(
            context=context, user=user, no_login=no_login)


class TestCodeReviewCommentHideControls(
        WithScenarios, BrowserTestCase, TestHideMessageControlMixin):

    layer = DatabaseFunctionalLayer

    scenarios = [
        ('bzr', {'git': False}),
        ('git', {'git': True}),
        ]

    def getContext(self, comment_owner=None):
        """See `TestHideMessageControlMixin`."""
        if self.git:
            self.useFixture(GitHostingFixture())
        comment = self.factory.makeCodeReviewComment(
            sender=comment_owner, git=self.git)
        self.control_text = 'mark-spam-%d' % comment.id
        return comment.branch_merge_proposal

    def getView(self, context, user=None, no_login=False):
        """See `TestHideMessageControlMixin`."""
        return self.getViewBrowser(
            context=context, user=user, no_login=no_login)

    def test_comment_owner_sees_hide_control(self):
        user = self.factory.makePerson()
        context = self.getContext(comment_owner=user)
        view = self.getView(context=context, user=user)
        hide_link = find_tag_by_id(view.contents, self.control_text)
        self.assertIsNot(None, hide_link)


class TestCommentAttachmentRendering(TestCaseWithFactory):
    """Test diff attachments are rendered correctly."""

    layer = LaunchpadFunctionalLayer

    def _makeCommentFromEmailWithAttachment(self, attachment_body):
        # Make an email message with an attachment, and create a code
        # review comment from it.
        bmp = self.factory.makeBranchMergeProposal()
        login_person(bmp.registrant)
        msg = self.factory.makeEmailMessage(
            body='testing',
            attachments=[('test.diff', 'text/plain', attachment_body)])
        message = MessageSet().fromEmail(message_as_bytes(msg))
        return CodeReviewDisplayComment(
            bmp.createCommentFromMessage(message, None, None, msg))

    def test_nonascii_in_attachment_renders(self):
        # The view should render without errors.
        comment = self._makeCommentFromEmailWithAttachment(b'\xe2\x98\x95')
        # Need to commit in order to read the diff out of the librarian.
        transaction.commit()
        view = create_initialized_view(comment, '+comment-body')
        view()

    def test_nonascii_in_attachment_decoded(self):
        # The diff_text should be a unicode string.
        comment = self._makeCommentFromEmailWithAttachment(b'\xe2\x98\x95')
        # Need to commit in order to read the diff out of the librarian.
        transaction.commit()
        view = create_initialized_view(comment, '+comment-body')
        [diff_attachment] = view.comment.display_attachments
        self.assertEqual('\u2615', diff_attachment.diff_text)


class TestBranchMergeCandidateView(TestCaseWithFactory):
    """Test the status title for the view."""

    layer = DatabaseFunctionalLayer

    def test_needs_review_title(self):
        # No title is set for a proposal needing review.
        bmp = self.factory.makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        view = create_initialized_view(bmp, '+link-summary')
        self.assertEqual('', view.status_title)

    def test_approved_shows_reviewer(self):
        # If the proposal is approved, the approver is shown in the title
        # along with when they approved it.
        bmp = self.factory.makeBranchMergeProposal()
        owner = bmp.target_branch.owner
        login_person(bmp.target_branch.owner)
        owner.display_name = 'Eric'
        bmp.approveBranch(owner, 'some-rev', datetime(
                year=2008, month=9, day=10, tzinfo=pytz.UTC))
        view = create_initialized_view(bmp, '+link-summary')
        self.assertEqual('Eric on 2008-09-10', view.status_title)

    def test_rejected_shows_reviewer(self):
        # If the proposal is rejected, the approver is shown in the title
        # along with when they approved it.
        bmp = self.factory.makeBranchMergeProposal()
        owner = bmp.target_branch.owner
        login_person(bmp.target_branch.owner)
        owner.display_name = 'Eric'
        bmp.rejectBranch(owner, 'some-rev', datetime(
                year=2008, month=9, day=10, tzinfo=pytz.UTC))
        view = create_initialized_view(bmp, '+link-summary')
        self.assertEqual('Eric on 2008-09-10', view.status_title)


class TestBranchMergeProposal(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def test_conversation(self):
        source_branch = self.factory.makeBranch()
        parent = add_revision_to_branch(self.factory, source_branch,
            self.factory.getUniqueDate()).revision
        bmp = self.factory.makeBranchMergeProposal(registrant=self.user,
            date_created=self.factory.getUniqueDate(),
            source_branch=source_branch)
        revision = add_revision_to_branch(self.factory, bmp.source_branch,
            self.factory.getUniqueDate()).revision
        diff = self.factory.makeDiff()
        bmp.generateIncrementalDiff(parent, revision, diff)
        self.useContext(feature_flags())
        set_feature_flag('code.incremental_diffs.enabled', 'enabled')
        browser = self.getViewBrowser(bmp)
        assert 'unf_pbasyvpgf' in browser.contents

    def test_short_conversation_comments_not_truncated(self):
        """Short comments should not be truncated."""
        comment = self.factory.makeCodeReviewComment(body='x y' * 100)
        browser = self.getViewBrowser(comment.branch_merge_proposal)
        self.assertIn('x y' * 100, browser.contents)

    def has_read_more(self, comment):
        url = canonical_url(comment, force_local_path=True)
        read_more = Tag(
            'Read more link', 'a', {'href': url}, text='Read more...')
        return HTMLContains(read_more)

    def test_long_conversation_comments_truncated(self):
        """Long comments in a conversation should be truncated."""
        comment = self.factory.makeCodeReviewComment(body='x y' * 2000)
        has_read_more = self.has_read_more(comment)
        browser = self.getViewBrowser(comment.branch_merge_proposal)
        txt = extract_text(
            find_tags_by_class(browser.contents, "comment-text")[0])
        self.assertNotIn('x y' * 2000, txt)
        self.assertThat(browser.contents, has_read_more)

    def test_short_conversation_comments_no_download(self):
        """Short comments should not have a download link."""
        comment = self.factory.makeCodeReviewComment(body='x y' * 100)
        download_url = canonical_url(comment, view_name='+download')
        browser = self.getViewBrowser(comment.branch_merge_proposal)
        body = Tag(
            'Download', 'a', {'href': download_url},
            text='Download full text')
        self.assertThat(browser.contents, Not(HTMLContains(body)))

    def test_long_conversation_comments_download_link(self):
        """Long comments in a conversation should be truncated."""
        comment = self.factory.makeCodeReviewComment(body='x y' * 2000)
        download_url = canonical_url(comment, view_name='+download')
        browser = self.getViewBrowser(comment.branch_merge_proposal)
        body = Tag(
            'Download', 'a', {'href': download_url},
            text='Download full text')
        self.assertThat(browser.contents, HTMLContains(body))

    def test_excessive_conversation_comments_no_redirect(self):
        """An excessive comment does not force a redict on proposal page."""
        comment = self.factory.makeCodeReviewComment(body='x' * 10001)
        mp_url = canonical_url(comment.branch_merge_proposal)
        has_read_more = self.has_read_more(comment)
        browser = self.getUserBrowser(mp_url)
        self.assertThat(browser.contents, Not(has_read_more))
        self.assertEqual(mp_url, browser.url)

    def test_timeout(self):
        """The page renders even if fetching revisions times out."""
        self.useFixture(FakeLogger())
        bmp = self.factory.makeBranchMergeProposalForGit()
        comment = self.factory.makeCodeReviewComment(
            body='x y' * 100, merge_proposal=bmp)
        hosting_fixture = self.useFixture(GitHostingFixture())
        hosting_fixture.getLog.failure = TimeoutError
        browser = self.getViewBrowser(comment.branch_merge_proposal)
        self.assertIn('x y' * 100, browser.contents)

    def test_show_diff_update_link(self):
        bmp = self.factory.makeBranchMergeProposal()
        job = removeSecurityProxy(bmp.getLatestDiffUpdateJob())
        job.job._status = JobStatus.FAILED
        view = create_initialized_view(bmp, '+index')
        result = view.show_diff_update_link
        self.assertTrue(result)

    def test_show_diff_update_link_no_failures(self):
        bmp = self.factory.makeBranchMergeProposal()
        job = removeSecurityProxy(bmp.getLatestDiffUpdateJob())
        job.job._status = JobStatus.COMPLETED
        job.job.date_finished = UTC_NOW
        view = create_initialized_view(bmp, '+index')
        result = view.show_diff_update_link
        self.assertFalse(result)

    def test_show_diff_update_link_latest_didnt_fail(self):
        bmp = self.factory.makeBranchMergeProposal()
        job = removeSecurityProxy(bmp.getLatestDiffUpdateJob())
        job.job._status = JobStatus.FAILED
        job = UpdatePreviewDiffJob.create(bmp)
        job.job._status = JobStatus.COMPLETED
        view = create_initialized_view(bmp, '+index')
        result = view.show_diff_update_link
        self.assertTrue(result)

    def test_show_rescan_link_git(self):
        bmp = self.factory.makeBranchMergeProposalForGit()
        target_job = getUtility(IGitRefScanJobSource).create(
            bmp.target_git_repository)
        removeSecurityProxy(target_job).job._status = JobStatus.FAILED
        view = create_initialized_view(bmp, '+index')
        self.assertTrue(view.show_rescan_link)

    def test_show_rescan_link_bzr(self):
        bmp = self.factory.makeBranchMergeProposal()
        target_job = getUtility(IBranchScanJobSource).create(
            bmp.target_branch)
        removeSecurityProxy(target_job).job._status = JobStatus.FAILED
        view = create_initialized_view(bmp, '+index')
        self.assertTrue(view.show_rescan_link)

    def test_show_rescan_link_both_failed(self):
        bmp = self.factory.makeBranchMergeProposalForGit()
        target_job = getUtility(IGitRefScanJobSource).create(
            bmp.target_git_repository)
        removeSecurityProxy(target_job).job._status = JobStatus.FAILED
        source_job = getUtility(IGitRefScanJobSource).create(
            bmp.source_git_repository)
        removeSecurityProxy(source_job).job._status = JobStatus.FAILED
        view = create_initialized_view(bmp, '+index')
        self.assertTrue(view.show_rescan_link)

    def test_show_rescan_link_latest_didnt_fail(self):
        bmp = self.factory.makeBranchMergeProposalForGit()
        target_job = getUtility(IGitRefScanJobSource).create(
            bmp.target_git_repository)
        removeSecurityProxy(target_job).job._status = JobStatus.COMPLETED
        source_job = getUtility(IGitRefScanJobSource).create(
            bmp.source_git_repository)
        removeSecurityProxy(source_job).job._status = JobStatus.COMPLETED
        view = create_initialized_view(bmp, '+index')
        self.assertFalse(view.show_rescan_link)

    def test_opengraph_description_is_commit(self):
        bmp = self.factory.makeBranchMergeProposalForGit()
        target_job = getUtility(IGitRefScanJobSource).create(
            bmp.target_git_repository)
        removeSecurityProxy(target_job).job._status = JobStatus.COMPLETED
        source_job = getUtility(IGitRefScanJobSource).create(
            bmp.source_git_repository)
        removeSecurityProxy(source_job).job._status = JobStatus.COMPLETED
        view = create_initialized_view(bmp, '+index')
        self.assertEqual(
            view.opengraph_description, view.context.commit_message)
        self.assertEqual(
            view.page_description, bmp.description)


class TestBranchMergeProposalRescanView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def test_rescan_with_git(self):
        bmp = self.factory.makeBranchMergeProposalForGit()
        source_job = getUtility(IGitRefScanJobSource).create(
            bmp.source_git_repository)
        removeSecurityProxy(source_job).job._status = JobStatus.FAILED

        with person_logged_in(bmp.merge_source.owner):
            request = LaunchpadTestRequest(
                method='POST',
                form={
                    'field.actions.rescan': 'Rescan',
                    })
            request.setPrincipal(bmp.merge_source.owner)
            view = create_initialized_view(
                bmp,
                name='+rescan',
                request=request)

        self.assertEqual(
            'Rescan scheduled',
            view.request.response.notifications[0].message
        )

    def test_rescan_with_bzr(self):
        bmp = self.factory.makeBranchMergeProposal()
        source_job = getUtility(IBranchScanJobSource).create(
            bmp.source_branch)
        removeSecurityProxy(source_job).job._status = JobStatus.FAILED

        with person_logged_in(bmp.merge_source.owner):
            request = LaunchpadTestRequest(
                method='POST',
                form={
                    'field.actions.rescan': 'Rescan',
                    })
            request.setPrincipal(bmp.merge_source.owner)
            view = create_initialized_view(
                bmp,
                name='+rescan',
                request=request)

        self.assertEqual(
            'Rescan scheduled',
            view.request.response.notifications[0].message
        )


class TestLatestProposalsForEachBranchMixin:
    """Confirm that the latest branch is returned."""

    layer = DatabaseFunctionalLayer

    def test_newest_first(self):
        # If each proposal targets a different branch, each will be returned.
        bmp1 = self._makeBranchMergeProposal(
            date_created=(
                datetime(year=2008, month=9, day=10, tzinfo=pytz.UTC)))
        bmp2 = self._makeBranchMergeProposal(
            date_created=(
                datetime(year=2008, month=10, day=10, tzinfo=pytz.UTC)))
        self.assertEqual(
            [bmp2, bmp1], latest_proposals_for_each_branch([bmp1, bmp2]))

    def test_visible_filtered_out(self):
        # If the proposal is not visible to the user, they are not returned.
        bmp1 = self._makeBranchMergeProposal(
            date_created=(
                datetime(year=2008, month=9, day=10, tzinfo=pytz.UTC)))
        bmp2 = self._makeBranchMergeProposal(
            date_created=(
                datetime(year=2008, month=10, day=10, tzinfo=pytz.UTC)))
        self._setBranchInvisible(bmp2.merge_source)
        self.assertEqual(
            [bmp1], latest_proposals_for_each_branch([bmp1, bmp2]))

    def test_same_target(self):
        # If the proposals target the same branch, then the most recent is
        # returned.
        bmp1 = self._makeBranchMergeProposal(
            date_created=(
                datetime(year=2008, month=9, day=10, tzinfo=pytz.UTC)))
        bmp2 = self._makeBranchMergeProposal(
            merge_target=bmp1.merge_target,
            date_created=(
                datetime(year=2008, month=10, day=10, tzinfo=pytz.UTC)))
        self.assertEqual(
            [bmp2], latest_proposals_for_each_branch([bmp1, bmp2]))


class TestLatestProposalsForEachBranchBzr(
    TestLatestProposalsForEachBranchMixin, TestCaseWithFactory):
    """Confirm that the latest branch is returned for Bazaar."""

    def _makeBranchMergeProposal(self, merge_target=None, **kwargs):
        return self.factory.makeBranchMergeProposal(
            target_branch=merge_target, **kwargs)

    @staticmethod
    def _setBranchInvisible(branch):
        removeSecurityProxy(branch).transitionToInformationType(
            InformationType.USERDATA, branch.owner, verify_policy=False)


class TestLatestProposalsForEachBranchGit(
    TestLatestProposalsForEachBranchMixin, TestCaseWithFactory):
    """Confirm that the latest branch is returned for Bazaar."""

    def _makeBranchMergeProposal(self, merge_target=None, **kwargs):
        return self.factory.makeBranchMergeProposalForGit(
            target_ref=merge_target, **kwargs)

    @staticmethod
    def _setBranchInvisible(branch):
        removeSecurityProxy(branch.repository).transitionToInformationType(
            InformationType.USERDATA, branch.owner, verify_policy=False)


class TestBranchMergeProposalLinkBugViewMixin:

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super().setUp()
        self.bmp = self._makeBranchMergeProposal()

    def test_anonymous(self):
        # The "Link a bug report" link on BranchMergeProposal:+index is
        # visible to all, but anonymous users will need to log in to use it.
        self.useFixture(FakeLogger())
        browser = self.getViewBrowser(
            self.bmp, view_name="+index", no_login=True)
        self.assertRaises(
            Unauthorized, browser.getLink("Link a bug report").click)

    def test_logged_in(self):
        # Any logged-in user can use the "Link a bug report" link.
        browser = self.getViewBrowser(self.bmp, view_name="+index")
        browser.getLink("Link a bug report").click()
        self.assertStartsWith(browser.title, "Link a bug report")

    def assertBugLinks(self, bugtasks, browser):
        expected_text = []
        for bugtask in bugtasks:
            expected_text.append(
                "Bug #%d: %s\n%s\n%s" % (
                    bugtask.bug.id, bugtask.bug.title,
                    bugtask.importance.title, bugtask.status.title))
        self.assertEqual(
            expected_text,
            [extract_text(tag) for tag in find_tags_by_class(
                 browser.contents, "buglink-summary")])

    def test_link(self):
        # A user can enter a bug number to link from an MP to a bug.
        bug = self.factory.makeBug()
        bugtask = bug.default_bugtask
        browser = self.getViewBrowser(self.bmp, view_name="+linkbug")
        browser.getControl("Bug ID").value = str(bug.id)
        browser.getControl("Link").click()
        with person_logged_in(self.user):
            self.assertBugLinks([bugtask], browser)

    def test_same_link_twice(self):
        # Attempting to link to the same bug twice only creates a single
        # link.
        bug = self.factory.makeBug()
        bugtask = bug.default_bugtask
        with person_logged_in(self.user):
            self.bmp.linkBug(bug, self.user)
        browser = self.getViewBrowser(self.bmp, view_name="+linkbug")
        browser.getControl("Bug ID").value = str(bug.id)
        browser.getControl("Link").click()
        with person_logged_in(self.user):
            self.assertBugLinks([bugtask], browser)


class TestBranchMergeProposalLinkBugViewBzr(
    TestBranchMergeProposalLinkBugViewMixin, BrowserTestCase):

    def _makeBranchMergeProposal(self):
        return self.factory.makeBranchMergeProposal()


class TestBranchMergeProposalLinkBugViewGit(
    TestBranchMergeProposalLinkBugViewMixin, GitHostingClientMixin,
    BrowserTestCase):

    def _makeBranchMergeProposal(self):
        return self.factory.makeBranchMergeProposalForGit()

    def assertMergeProposalLinks(self, mps, browser):
        matchers = []
        for mp in mps:
            matchers.append(DocTestMatches(
                "%s\n...\nfor merging\ninto\n%s\n..." % (
                    mp.merge_source.identity, mp.merge_target.identity),
                flags=doctest.ELLIPSIS))
        self.assertThat(
            [extract_text(tag) for tag in find_tags_by_class(
                 browser.contents, "buglink-summary")],
            MatchesListwise(matchers))

    def test_bug_page_shows_link(self):
        # The bug-MP link is shown on the bug page.
        bug = self.factory.makeBug()
        title = bug.title
        with person_logged_in(self.user):
            self.bmp.linkBug(bug, self.user)
        browser = self.getViewBrowser(self.bmp)
        browser.getLink(title).click()
        with person_logged_in(self.user):
            self.assertMergeProposalLinks([self.bmp], browser)

    def test_link_to_private_bug_only_shown_if_visible(self):
        # The MP page only shows links to private bugs if the user can see
        # the bugs in question.
        bug = self.factory.makeBug(information_type=InformationType.USERDATA)
        with admin_logged_in() as admin:
            bugtask = bug.default_bugtask
            self.bmp.linkBug(bug, admin)
        admin_browser = self.getViewBrowser(self.bmp, user=admin)
        with admin_logged_in():
            self.assertBugLinks([bugtask], admin_browser)
        user_browser = self.getViewBrowser(self.bmp)
        self.assertBugLinks([], user_browser)

    def test_unlink_from_merge_proposal(self):
        # The MP page has a delete button to unlink the bug.
        bug = self.factory.makeBug()
        with person_logged_in(self.user):
            self.bmp.linkBug(bug, self.user)
        browser = self.getViewBrowser(self.bmp)
        browser.getLink(url="+unlinkbug").click()
        self.assertBugLinks([], browser)

    def test_unlink_from_bug(self):
        # The bug page has a delete button to unlink the MP.
        bug = self.factory.makeBug()
        with person_logged_in(self.user):
            self.bmp.linkBug(bug, self.user)
        browser = self.getViewBrowser(bug)
        browser.getLink(url="+unlinkbug").click()
        self.assertMergeProposalLinks([], browser)


class TestBranchMergeProposalDeleteViewMixin:
    """Test the BranchMergeProposal deletion view."""

    layer = DatabaseFunctionalLayer

    def test_links(self):
        bmp = self._makeBranchMergeProposal()
        view = create_initialized_view(
            bmp, "+delete", principal=bmp.registrant)
        content = view()
        self.assertEqual(
            canonical_url(bmp.merge_source),
            find_tag_by_id(content, "source-link").find("a")["href"])
        self.assertEqual(
            canonical_url(bmp.merge_target),
            find_tag_by_id(content, "target-link").find("a")["href"])

    def test_deletion_works(self):
        registrant = self.factory.makePerson()
        bmp = self._makeBranchMergeProposal(registrant=registrant)
        target = bmp.merge_target
        with person_logged_in(registrant):
            self.assertEqual([bmp], list(target.landing_candidates))
        browser = self.getViewBrowser(bmp, "+delete", user=bmp.registrant)
        browser.getControl("Delete proposal").click()
        with person_logged_in(registrant):
            self.assertEqual([], list(target.landing_candidates))


class TestBranchMergeProposalDeleteViewBzr(
    TestBranchMergeProposalDeleteViewMixin, BrowserTestCase):
    """Test the BranchMergeProposal deletion view for Bazaar."""

    def _makeBranchMergeProposal(self, **kwargs):
        return self.factory.makeBranchMergeProposal(**kwargs)


class TestBranchMergeProposalDeleteViewGit(
    TestBranchMergeProposalDeleteViewMixin, GitHostingClientMixin,
    BrowserTestCase):
    """Test the BranchMergeProposal deletion view for Git."""

    def _makeBranchMergeProposal(self, **kwargs):
        return self.factory.makeBranchMergeProposalForGit(**kwargs)


load_tests = load_tests_apply_scenarios
