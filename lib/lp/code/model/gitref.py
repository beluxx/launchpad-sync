# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "GitRef",
    "GitRefDefault",
    "GitRefFrozen",
    "GitRefRemote",
]

import re
from datetime import timezone
from functools import partial
from urllib.parse import quote, quote_plus, urlsplit

import requests
from lazr.lifecycle.event import ObjectCreatedEvent
from storm.expr import And, Or
from storm.locals import DateTime, Int, Not, Reference, Store, Unicode
from zope.component import getUtility
from zope.event import notify
from zope.interface import implementer, provider
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.app.errors import NotFoundError
from lp.code.enums import (
    BranchMergeProposalStatus,
    GitObjectType,
    GitRepositoryType,
)
from lp.code.errors import (
    BranchMergeProposalExists,
    GitRepositoryBlobNotFound,
    GitRepositoryBlobUnsupportedRemote,
    GitRepositoryScanFault,
    InvalidBranchMergeProposal,
)
from lp.code.event.branchmergeproposal import (
    BranchMergeProposalNeedsReviewEvent,
)
from lp.code.interfaces.branch import WrongNumberOfReviewTypeArguments
from lp.code.interfaces.branchmergeproposal import (
    BRANCH_MERGE_PROPOSAL_FINAL_STATES,
)
from lp.code.interfaces.gitcollection import IAllGitRepositories
from lp.code.interfaces.githosting import IGitHostingClient
from lp.code.interfaces.gitlookup import IGitLookup
from lp.code.interfaces.gitref import (
    IGitRef,
    IGitRefRemote,
    IGitRefRemoteSet,
    IGitRefSet,
)
from lp.code.interfaces.gitrule import describe_git_permissions
from lp.code.model.branchmergeproposal import (
    BranchMergeProposal,
    BranchMergeProposalGetter,
)
from lp.code.model.gitrule import GitRule, GitRuleGrant
from lp.services.config import config
from lp.services.database.constants import UTC_NOW
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase
from lp.services.features import getFeatureFlag
from lp.services.memcache.interfaces import IMemcacheClient
from lp.services.timeout import TimeoutError, reduced_timeout, urlfetch
from lp.services.utils import seconds_since_epoch
from lp.services.webapp.interfaces import ILaunchBag


class GitRefMixin:
    """Methods and properties common to GitRef and GitRefFrozen.

    These can be derived solely from the repository and path, and so do not
    require a database record.
    """

    repository_url = None

    def __eq__(self, other):
        if not (
            IGitRef.providedBy(other)
            and not IGitRefRemote.providedBy(other)
            and self.repository == other.repository
            and self.repository_url == other.repository_url
            and self.path == other.path
        ):
            return False
        if isinstance(self, GitRefDefault) and isinstance(
            other, GitRefDefault
        ):
            # Two references to the default branch for the same repository
            # are equal.
            return True
        try:
            self_commit_sha1 = self.commit_sha1
            other_commit_sha1 = other.commit_sha1
        except NotFoundError:
            # Possible for GitRefDefault objects; an unresolvable default is
            # not equal to anything other than another GitRefDefault object
            # for the same repository.
            return False
        return self_commit_sha1 == other_commit_sha1

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        try:
            commit_sha1 = self.commit_sha1
        except NotFoundError:
            # Possible for GitRefDefault objects.
            commit_sha1 = None
        return hash(
            (self.repository, self.repository_url, self.path, commit_sha1)
        )

    @property
    def display_name(self):
        """See `IGitRef`."""
        return self.identity

    # For IHasMergeProposals views.
    displayname = display_name

    @property
    def name(self):
        """See `IGitRef`."""
        if self.path.startswith("refs/heads/"):
            return self.path[len("refs/heads/") :]
        else:
            return self.path

    @property
    def url_quoted_name(self):
        """See `IGitRef`."""
        return quote(self.name.encode("UTF-8"))

    @property
    def identity(self):
        """See `IGitRef`."""
        return "%s:%s" % (self.repository.shortened_path, self.name)

    @property
    def unique_name(self):
        """See `IGitRef`."""
        return "%s:%s" % (self.repository.unique_name, self.name)

    @property
    def repository_type(self):
        """See `IGitRef`."""
        return self.repository.repository_type

    @property
    def owner(self):
        """See `IGitRef`."""
        return self.repository.owner

    @property
    def target(self):
        """See `IGitRef`."""
        return self.repository.target

    @property
    def namespace(self):
        """See `IGitRef`."""
        return self.repository.namespace

    def getCodebrowseUrl(self):
        """See `IGitRef`."""
        return "%s?h=%s" % (
            self.repository.getCodebrowseUrl(),
            quote_plus(self.name.encode("UTF-8")),
        )

    def getCodebrowseUrlForRevision(self, commit):
        """See `IGitRef`."""
        return self.repository.getCodebrowseUrlForRevision(commit)

    def getStatusReports(self, commit_sha1):
        return self.repository.getStatusReports(commit_sha1)

    @property
    def information_type(self):
        """See `IGitRef`."""
        return self.repository.information_type

    @property
    def private(self):
        """See `IGitRef`."""
        return self.repository.private

    def visibleByUser(self, user):
        """See `IGitRef`."""
        return self.repository.visibleByUser(user)

    def transitionToInformationType(
        self, information_type, user, verify_policy=True
    ):
        return self.repository.transitionToInformationType(
            information_type, user, verify_policy=verify_policy
        )

    @property
    def reviewer(self):
        """See `IGitRef`."""
        # XXX cjwatson 2015-04-17: We should have ref-pattern-specific
        # reviewers.
        return self.repository.reviewer

    @property
    def code_reviewer(self):
        """See `IGitRef`."""
        # XXX cjwatson 2015-04-17: We should have ref-pattern-specific
        # reviewers.
        return self.repository.code_reviewer

    def isPersonTrustedReviewer(self, reviewer):
        """See `IGitRef`."""
        # XXX cjwatson 2015-04-17: We should have ref-pattern-specific
        # reviewers.
        return self.repository.isPersonTrustedReviewer(reviewer)

    @property
    def subscriptions(self):
        """See `IGitRef`."""
        return self.repository.subscriptions

    @property
    def subscribers(self):
        """See `IGitRef`."""
        return self.repository.subscribers

    def subscribe(
        self,
        person,
        notification_level,
        max_diff_lines,
        code_review_level,
        subscribed_by,
    ):
        """See `IGitRef`."""
        return self.repository.subscribe(
            person,
            notification_level,
            max_diff_lines,
            code_review_level,
            subscribed_by,
        )

    def getSubscription(self, person):
        """See `IGitRef`."""
        return self.repository.getSubscription(person)

    def unsubscribe(self, person, unsubscribed_by):
        """See `IGitRef`."""
        return self.repository.unsubscribe(person, unsubscribed_by)

    def getNotificationRecipients(self):
        """See `IGitRef`."""
        return self.repository.getNotificationRecipients()

    @property
    def landing_targets(self):
        """See `IGitRef`."""
        return Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.source_git_repository == self.repository,
            BranchMergeProposal.source_git_path == self.path,
        )

    def getPrecachedLandingTargets(self, user):
        """See `IGitRef`."""
        loader = partial(BranchMergeProposal.preloadDataForBMPs, user=user)
        return DecoratedResultSet(self.landing_targets, pre_iter_hook=loader)

    @property
    def _api_landing_targets(self):
        return self.getPrecachedLandingTargets(getUtility(ILaunchBag).user)

    @property
    def landing_candidates(self):
        """See `IGitRef`."""
        return Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.target_git_repository == self.repository,
            BranchMergeProposal.target_git_path == self.path,
            Not(
                BranchMergeProposal.queue_status.is_in(
                    BRANCH_MERGE_PROPOSAL_FINAL_STATES
                )
            ),
        )

    def getPrecachedLandingCandidates(self, user):
        """See `IGitRef`."""
        loader = partial(BranchMergeProposal.preloadDataForBMPs, user=user)
        return DecoratedResultSet(
            self.landing_candidates, pre_iter_hook=loader
        )

    @property
    def _api_landing_candidates(self):
        return self.getPrecachedLandingCandidates(getUtility(ILaunchBag).user)

    @property
    def dependent_landings(self):
        """See `IGitRef`."""
        return Store.of(self).find(
            BranchMergeProposal,
            BranchMergeProposal.prerequisite_git_repository == self.repository,
            BranchMergeProposal.prerequisite_git_path == self.path,
            Not(
                BranchMergeProposal.queue_status.is_in(
                    BRANCH_MERGE_PROPOSAL_FINAL_STATES
                )
            ),
        )

    def getMergeProposals(
        self,
        status=None,
        visible_by_user=None,
        merged_revision_ids=None,
        eager_load=False,
    ):
        """See `IGitRef`."""
        if not status:
            status = (
                BranchMergeProposalStatus.CODE_APPROVED,
                BranchMergeProposalStatus.NEEDS_REVIEW,
                BranchMergeProposalStatus.WORK_IN_PROGRESS,
            )

        collection = getUtility(IAllGitRepositories).visibleByUser(
            visible_by_user
        )
        return collection.getMergeProposals(
            status,
            target_repository=self.repository,
            target_path=self.path,
            merged_revision_ids=merged_revision_ids,
            eager_load=eager_load,
        )

    def getDependentMergeProposals(
        self, status=None, visible_by_user=None, eager_load=False
    ):
        """See `IGitRef`."""
        if not status:
            status = (
                BranchMergeProposalStatus.CODE_APPROVED,
                BranchMergeProposalStatus.NEEDS_REVIEW,
                BranchMergeProposalStatus.WORK_IN_PROGRESS,
            )

        collection = getUtility(IAllGitRepositories).visibleByUser(
            visible_by_user
        )
        return collection.getMergeProposals(
            status,
            prerequisite_repository=self.repository,
            prerequisite_path=self.path,
            eager_load=eager_load,
        )

    @property
    def pending_updates(self):
        """See `IGitRef`."""
        return self.repository.pending_updates

    def _getLog(
        self,
        start,
        limit=None,
        stop=None,
        union_repository=None,
        enable_hosting=None,
        enable_memcache=None,
        logger=None,
    ):
        if enable_hosting is None:
            enable_hosting = not getFeatureFlag("code.git.log.disable_hosting")
        if enable_memcache is None:
            enable_memcache = not getFeatureFlag(
                "code.git.log.disable_memcache"
            )
        path = self.repository.getInternalPath()
        if (
            union_repository is not None
            and union_repository != self.repository
        ):
            path = "%s:%s" % (union_repository.getInternalPath(), path)
        log = None
        if enable_memcache:
            memcache_client = getUtility(IMemcacheClient)
            instance_name = urlsplit(
                config.codehosting.internal_git_api_endpoint
            ).hostname
            memcache_key = "%s:git-log:%s:%s" % (instance_name, path, start)
            if limit is not None:
                memcache_key += ":limit=%s" % limit
            if stop is not None:
                memcache_key += ":stop=%s" % stop
            memcache_key = memcache_key.encode()

            description = "log information for %s:%s" % (path, start)
            log = memcache_client.get_json(memcache_key, logger, description)

        if log is None:
            if enable_hosting:
                hosting_client = getUtility(IGitHostingClient)
                log = removeSecurityProxy(
                    hosting_client.getLog(
                        path, start, limit=limit, stop=stop, logger=logger
                    )
                )
                if enable_memcache:
                    memcache_client.set_json(memcache_key, log, logger=logger)
            else:
                # Fall back to synthesising something reasonable based on
                # information in our own database.
                log = [
                    {
                        "sha1": self.commit_sha1,
                        "message": self.commit_message,
                        "author": (
                            None
                            if self.author is None
                            else {
                                "name": self.author.name_without_email,
                                "email": self.author.email,
                                "time": seconds_since_epoch(self.author_date),
                            }
                        ),
                        "committer": (
                            None
                            if self.committer is None
                            else {
                                "name": self.committer.name_without_email,
                                "email": self.committer.email,
                                "time": seconds_since_epoch(
                                    self.committer_date
                                ),
                            }
                        ),
                    }
                ]
        return log

    def getCommits(
        self,
        start,
        limit=None,
        stop=None,
        union_repository=None,
        start_date=None,
        end_date=None,
        handle_timeout=False,
        logger=None,
    ):
        # Circular import.
        from lp.code.model.gitrepository import parse_git_commits

        with reduced_timeout(1.0 if handle_timeout else 0.0):
            try:
                log = self._getLog(
                    start,
                    limit=limit,
                    stop=stop,
                    union_repository=union_repository,
                    logger=logger,
                )
                commit_oids = [
                    commit["sha1"] for commit in log if "sha1" in commit
                ]
                parsed_commits = parse_git_commits(log)
            except TimeoutError:
                if not handle_timeout:
                    raise
                if logger is not None:
                    logger.exception(
                        "Timeout fetching commits for %s" % self.identity
                    )
                # Synthesise a response based on what we have in the database.
                commit_oids = [self.commit_sha1]
                tip = {"sha1": self.commit_sha1, "synthetic": True}
                optional_fields = (
                    "author",
                    "author_date",
                    "committer",
                    "committer_date",
                    "commit_message",
                )
                for field in optional_fields:
                    if getattr(self, field) is not None:
                        tip[field] = getattr(self, field)
                parsed_commits = {self.commit_sha1: tip}
        commits = []
        for commit_oid in commit_oids:
            parsed_commit = parsed_commits[commit_oid]
            author_date = parsed_commit.get("author_date")
            if start_date is not None:
                if author_date is None or author_date < start_date:
                    continue
            if end_date is not None:
                if author_date is None or author_date > end_date:
                    continue
            commits.append(parsed_commit)
        return commits

    def getLatestCommits(
        self,
        quantity=10,
        extended_details=False,
        user=None,
        handle_timeout=False,
        logger=None,
    ):
        commits = self.getCommits(
            self.commit_sha1,
            limit=quantity,
            handle_timeout=handle_timeout,
            logger=logger,
        )
        if extended_details:
            # XXX cjwatson 2016-05-09: Add support for linked bugtasks once
            # those are supported for Git.
            collection = getUtility(IAllGitRepositories).visibleByUser(user)
            merge_proposals = collection.getMergeProposals(
                target_repository=self.repository,
                target_path=self.path,
                merged_revision_ids=[commit["sha1"] for commit in commits],
                statuses=[BranchMergeProposalStatus.MERGED],
            )
            merge_proposal_commits = {
                mp.merged_revision_id: mp for mp in merge_proposals
            }
            for commit in commits:
                commit["merge_proposal"] = merge_proposal_commits.get(
                    commit["sha1"]
                )
        return commits

    def getBlob(self, filename):
        """See `IGitRef`."""
        return self.repository.getBlob(filename, rev=self.path)

    @property
    def recipes(self):
        """See `IHasRecipes`."""
        from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
        from lp.code.model.sourcepackagerecipedata import (
            SourcePackageRecipeData,
        )

        revspecs = {self.path, self.name}
        if self.path == self.repository.default_branch:
            revspecs.add(None)
        recipes = SourcePackageRecipeData.findRecipes(
            self.repository, revspecs=list(revspecs)
        )
        hook = SourcePackageRecipe.preLoadDataForSourcePackageRecipes
        return DecoratedResultSet(recipes, pre_iter_hook=hook)

    def getGrants(self):
        """See `IGitRef`."""
        return list(
            Store.of(self).find(
                GitRuleGrant,
                GitRuleGrant.rule_id == GitRule.id,
                GitRule.repository_id == self.repository_id,
                GitRule.ref_pattern == self.path,
            )
        )

    def setGrants(self, grants, user):
        """See `IGitRef`."""
        rule = self.repository.getRule(self.path)
        if rule is None:
            # We don't need to worry about position, since this is an
            # exact-match rule and therefore has a canonical position.
            rule = self.repository.addRule(self.path, user)
        rule.setGrants(grants, user)

    def checkPermissions(self, person):
        """See `IGitRef`."""
        return describe_git_permissions(
            self.repository.checkRefPermissions(person, [self.path])[self.path]
        )

    def getLatestScanJob(self):
        """See `IGitRef`."""
        return self.repository.getLatestScanJob()

    def rescan(self):
        """See `IGitRef`."""
        return self.repository.rescan()


@implementer(IGitRef)
@provider(IGitRefSet)
class GitRef(GitRefMixin, StormBase):
    """See `IGitRef`."""

    __storm_table__ = "GitRef"
    __storm_primary__ = ("repository_id", "path")

    repository_id = Int(name="repository", allow_none=False)
    repository = Reference(repository_id, "GitRepository.id")

    path = Unicode(name="path", allow_none=False)

    commit_sha1 = Unicode(name="commit_sha1", allow_none=False)

    object_type = DBEnum(enum=GitObjectType, allow_none=False)

    author_id = Int(name="author", allow_none=True)
    author = Reference(author_id, "RevisionAuthor.id")
    author_date = DateTime(
        name="author_date", tzinfo=timezone.utc, allow_none=True
    )

    committer_id = Int(name="committer", allow_none=True)
    committer = Reference(committer_id, "RevisionAuthor.id")
    committer_date = DateTime(
        name="committer_date", tzinfo=timezone.utc, allow_none=True
    )

    commit_message = Unicode(name="commit_message", allow_none=True)

    @property
    def commit_message_first_line(self):
        if self.commit_message is not None:
            return self.commit_message.split("\n", 1)[0]
        else:
            return None

    @property
    def has_commits(self):
        return self.commit_message is not None

    def addLandingTarget(
        self,
        registrant,
        merge_target,
        merge_prerequisite=None,
        whiteboard=None,
        date_created=None,
        needs_review=None,
        description=None,
        review_requests=None,
        commit_message=None,
    ):
        """See `IGitRef`."""
        if not self.namespace.supports_merge_proposals:
            raise InvalidBranchMergeProposal(
                "%s repositories do not support merge proposals."
                % self.namespace.name
            )
        if self == merge_target:
            raise InvalidBranchMergeProposal(
                "Source and target references must be different."
            )
        if not merge_target.repository.isRepositoryMergeable(self.repository):
            raise InvalidBranchMergeProposal(
                "%s is not mergeable into %s"
                % (self.identity, merge_target.identity)
            )
        if merge_prerequisite is not None:
            if not merge_target.repository.isRepositoryMergeable(
                merge_prerequisite.repository
            ):
                raise InvalidBranchMergeProposal(
                    "%s is not mergeable into %s"
                    % (merge_prerequisite.identity, self.identity)
                )
            if self == merge_prerequisite:
                raise InvalidBranchMergeProposal(
                    "Source and prerequisite references must be different."
                )
            if merge_target == merge_prerequisite:
                raise InvalidBranchMergeProposal(
                    "Target and prerequisite references must be different."
                )

        getter = BranchMergeProposalGetter
        for existing_proposal in getter.activeProposalsForBranches(
            self, merge_target
        ):
            raise BranchMergeProposalExists(existing_proposal)

        if date_created is None:
            date_created = UTC_NOW

        if needs_review:
            queue_status = BranchMergeProposalStatus.NEEDS_REVIEW
            date_review_requested = date_created
        else:
            queue_status = BranchMergeProposalStatus.WORK_IN_PROGRESS
            date_review_requested = None

        if review_requests is None:
            review_requests = []

        # If no reviewer is specified, use the default for the branch.
        if len(review_requests) == 0:
            review_requests.append((merge_target.code_reviewer, None))

        kwargs = {}
        for prefix, obj in (
            ("source", self),
            ("target", merge_target),
            ("prerequisite", merge_prerequisite),
        ):
            if obj is not None:
                kwargs["%s_git_repository" % prefix] = obj.repository
                kwargs["%s_git_path" % prefix] = obj.path
                kwargs["%s_git_commit_sha1" % prefix] = obj.commit_sha1

        bmp = BranchMergeProposal(
            registrant=registrant,
            whiteboard=whiteboard,
            date_created=date_created,
            date_review_requested=date_review_requested,
            queue_status=queue_status,
            commit_message=commit_message,
            description=description,
            **kwargs,
        )

        for reviewer, review_type in review_requests:
            bmp.nominateReviewer(
                reviewer, registrant, review_type, _notify_listeners=False
            )

        notify(ObjectCreatedEvent(bmp, user=registrant))
        if needs_review:
            notify(BranchMergeProposalNeedsReviewEvent(bmp))

        return bmp

    def createMergeProposal(
        self,
        registrant,
        merge_target,
        merge_prerequisite=None,
        needs_review=True,
        initial_comment=None,
        commit_message=None,
        reviewers=None,
        review_types=None,
    ):
        """See `IGitRef`."""
        if reviewers is None:
            reviewers = []
        if review_types is None:
            review_types = []
        if len(reviewers) != len(review_types):
            raise WrongNumberOfReviewTypeArguments(
                "reviewers and review_types must be equal length."
            )
        review_requests = list(zip(reviewers, review_types))
        return self.addLandingTarget(
            registrant,
            merge_target,
            merge_prerequisite,
            needs_review=needs_review,
            description=initial_comment,
            commit_message=commit_message,
            review_requests=review_requests,
        )

    @classmethod
    def findByReposAndPaths(cls, repos_and_paths):
        """See `IGitRefSet`"""

        def full_path(path):
            if path.startswith("refs/heads/"):
                return path
            return "refs/heads/%s" % path

        clauses = []
        for repo, path in repos_and_paths:
            clauses.append(
                And(
                    GitRef.path.is_in([path, full_path(path)]),
                    (GitRef.repository_id == repo.id),
                )
            )
        if not clauses:
            return {}

        result = {}
        for row in IStore(GitRef).find(GitRef, Or(*clauses)):
            result[(row.repository_id, row.path)] = row

        return_value = {}
        for repo, path in repos_and_paths:
            if path == "HEAD":
                value = GitRefDefault(repo)
            else:
                key, full_key = [(repo.id, path), (repo.id, full_path(path))]
                value = result.get(key, result.get(full_key))
            if value is not None:
                return_value[(repo, path)] = value
        return return_value


class GitRefDatabaseBackedMixin(GitRefMixin):
    """A mixin for virtual Git references backed by a database record."""

    @property
    def _non_database_attributes(self):
        """A sequence of attributes not backed by the database."""
        raise NotImplementedError()

    @property
    def _self_in_database(self):
        """Return the equivalent database-backed record of self."""
        raise NotImplementedError()

    def __getattr__(self, name):
        return getattr(self._self_in_database, name)

    def __setattr__(self, name, value):
        if name in self._non_database_attributes:
            self.__dict__[name] = value
        else:
            setattr(self._self_in_database, name, value)

    # zope.interface tries to use this during adaptation (e.g. to
    # ITraversable), and we don't want that to attempt a database lookup via
    # __getattr__.
    __conform__ = None


@implementer(IGitRef)
class GitRefDefault(GitRefDatabaseBackedMixin):
    """A reference to the default branch in a Git repository.

    This always refers to whatever the default branch currently is, even if
    it changes later.
    """

    def __init__(self, repository):
        self.repository_id = repository.id
        self.repository = repository
        self.path = "HEAD"

    _non_database_attributes = ("repository_id", "repository", "path")

    @property
    def _self_in_database(self):
        """See `GitRefDatabaseBackedMixin`."""
        path = self.repository.default_branch
        if path is None:
            raise NotFoundError(
                "Repository '%s' has no default branch" % self.repository
            )
        ref = IStore(GitRef).get(GitRef, (self.repository_id, path))
        if ref is None:
            raise NotFoundError(
                "Repository '%s' has default branch '%s', but there is no "
                "such reference" % (self.repository, path)
            )
        return ref


@implementer(IGitRef)
class GitRefFrozen(GitRefDatabaseBackedMixin):
    """A frozen Git reference.

    This is like a GitRef, but is frozen at a particular commit, even if the
    real reference has moved on or has been deleted.  It isn't necessarily
    backed by a real database object, and will retrieve columns from the
    database when required.  Use this when you have a
    repository/path/commit_sha1 that you want to pass around as a single
    object, but don't necessarily know that the ref still exists.
    """

    def __init__(self, repository, path, commit_sha1):
        self.repository_id = repository.id
        self.repository = repository
        self.path = path
        self.commit_sha1 = commit_sha1

    _non_database_attributes = (
        "repository_id",
        "repository",
        "path",
        "commit_sha1",
    )

    @property
    def _self_in_database(self):
        """See `GitRefDatabaseBackedMixin`."""
        ref = IStore(GitRef).get(GitRef, (self.repository_id, self.path))
        if ref is None:
            raise NotFoundError(
                "Repository '%s' does not currently contain a reference named "
                "'%s'" % (self.repository, self.path)
            )
        return ref


def _fetch_blob_from_github(repository_url, ref_path, filename):
    repo_path = urlsplit(repository_url).path.strip("/")
    if repo_path.endswith(".git"):
        repo_path = repo_path[: -len(".git")]
    try:
        response = urlfetch(
            "https://raw.githubusercontent.com/%s/%s/%s"
            % (
                repo_path,
                # GitHub supports either branch or tag names here, but both
                # must be shortened.  (If both a branch and a tag exist with
                # the same name, it appears to pick the branch.)
                quote(re.sub(r"^refs/(?:heads|tags)/", "", ref_path)),
                quote(filename),
            ),
            use_proxy=True,
        )
    except requests.RequestException as e:
        if (
            e.response is not None
            and e.response.status_code == requests.codes.NOT_FOUND
        ):
            raise GitRepositoryBlobNotFound(
                repository_url, filename, rev=ref_path
            )
        else:
            raise GitRepositoryScanFault(
                "Failed to get file from Git repository at %s: %s"
                % (repository_url, str(e))
            )
    return response.content


def _fetch_blob_from_gitlab(repository_url, ref_path, filename):
    repo_url = repository_url.strip("/")
    if repo_url.endswith(".git"):
        repo_url = repo_url[: -len(".git")]
    try:
        response = urlfetch(
            "%s/-/raw/%s/%s"
            % (
                repo_url,
                # GitLab supports either branch or tag names here, but both
                # must be shortened.  (If both a branch and a tag exist with
                # the same name, it appears to pick the tag.)
                quote(re.sub(r"^refs/(?:heads|tags)/", "", ref_path)),
                quote(filename),
            ),
            use_proxy=True,
        )
    except requests.RequestException as e:
        if (
            e.response is not None
            and e.response.status_code == requests.codes.NOT_FOUND
        ):
            raise GitRepositoryBlobNotFound(
                repository_url, filename, rev=ref_path
            )
        else:
            raise GitRepositoryScanFault(
                "Failed to get file from Git repository at %s: %s"
                % (repository_url, str(e))
            )
    return response.content


# Some well-known GitLab instances.  This is certainly not comprehensive.
# XXX cjwatson 2023-11-02: This should probably use a feature rule so that
# it can be extended more easily.
_gitlab_hostnames = {
    "gitlab.com",
    "gitlab.eclipse.org",
    "gitlab.freedesktop.org",
    "gitlab.gnome.org",
    "invent.kde.org",
    "salsa.debian.org",
}


def _fetch_blob_from_launchpad(repository_url, ref_path, filename):
    repo_path = urlsplit(repository_url).path.strip("/")
    try:
        response = urlfetch(
            "https://git.launchpad.net/%s/plain/%s"
            % (repo_path, quote(filename)),
            params={"h": ref_path},
        )
    except requests.RequestException as e:
        if (
            e.response is not None
            and e.response.status_code == requests.codes.NOT_FOUND
        ):
            raise GitRepositoryBlobNotFound(
                repository_url, filename, rev=ref_path
            )
        else:
            raise GitRepositoryScanFault(
                "Failed to get file from Git repository at %s: %s"
                % (repository_url, str(e))
            )
    return response.content


@implementer(IGitRef, IGitRefRemote)
@provider(IGitRefRemoteSet)
class GitRefRemote(GitRefMixin):
    """A reference in a remotely-hosted Git repository.

    We can do very little with these - for example, we don't know their tip
    commit ID - but it's useful to be able to pass the repository URL and
    path around as a unit.
    """

    def __init__(self, repository_url, path):
        self.repository_url = repository_url
        self.path = path

    @classmethod
    def new(cls, repository_url, path):
        """See `IGitRefRemoteSet`."""
        return cls(repository_url, path)

    def __eq__(self, other):
        return (
            IGitRefRemote.providedBy(other)
            and self.repository_url == other.repository_url
            and self.path == other.path
        )

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.repository_url, self.path))

    def _unimplemented(self, *args, **kwargs):
        raise NotImplementedError("Not implemented for remote repositories.")

    repository = None
    commit_sha1 = property(_unimplemented)
    object_type = property(_unimplemented)
    author = None
    author_date = None
    committer = None
    committer_date = None
    commit_message = None
    commit_message_first_line = property(_unimplemented)

    @property
    def identity(self):
        """See `IGitRef`."""
        return "%s %s" % (self.repository_url, self.name)

    @property
    def unique_name(self):
        """See `IGitRef`."""
        return "%s %s" % (self.repository_url, self.name)

    repository_type = GitRepositoryType.REMOTE
    owner = property(_unimplemented)
    target = property(_unimplemented)
    namespace = property(_unimplemented)
    getCodebrowseUrl = _unimplemented
    getCodebrowseUrlForRevision = _unimplemented
    information_type = InformationType.PUBLIC
    private = False

    def visibleByUser(self, user):
        """See `IGitRef`."""
        return True

    transitionToInformationType = _unimplemented
    reviewer = property(_unimplemented)
    code_reviewer = property(_unimplemented)
    isPersonTrustedReviewer = _unimplemented

    @property
    def subscriptions(self):
        """See `IGitRef`."""
        return []

    @property
    def subscribers(self):
        """See `IGitRef`."""
        return []

    subscribe = _unimplemented
    getSubscription = _unimplemented
    unsubscribe = _unimplemented
    getNotificationRecipients = _unimplemented
    landing_targets = property(_unimplemented)
    landing_candidates = property(_unimplemented)
    dependent_landings = property(_unimplemented)
    addLandingTarget = _unimplemented
    createMergeProposal = _unimplemented
    getMergeProposals = _unimplemented
    getDependentMergeProposals = _unimplemented
    pending_updates = False

    def getCommits(self, *args, **kwargs):
        """See `IGitRef`."""
        return []

    def getLatestCommits(self, *args, **kwargs):
        """See `IGitRef`."""
        return []

    def getBlob(self, filename):
        """See `IGitRef`."""
        # In general, we can't easily get hold of a blob from a remote
        # repository without cloning the whole thing.  In future we might
        # dispatch a build job or a code import or something like that to do
        # so.  For now, we just special-case some providers where we know
        # how to fetch a blob on its own.
        url = urlsplit(self.repository_url)
        if (
            url.hostname == "github.com"
            and len(url.path.strip("/").split("/")) == 2
        ):
            return _fetch_blob_from_github(
                self.repository_url, self.path, filename
            )
        if url.hostname in _gitlab_hostnames:
            return _fetch_blob_from_gitlab(
                self.repository_url, self.path, filename
            )
        if (
            url.hostname == "git.launchpad.net"
            and config.vhost.mainsite.hostname != "launchpad.net"
        ):
            # Even if this isn't launchpad.net, we can still retrieve files
            # from git.launchpad.net by URL, as a QA convenience.  (We check
            # config.vhost.mainsite.hostname rather than
            # config.codehosting.git_*_root because the dogfood instance
            # points git_*_root to git.launchpad.net but doesn't share the
            # production database.)
            return _fetch_blob_from_launchpad(
                self.repository_url, self.path, filename
            )
        codehosting_host = urlsplit(config.codehosting.git_anon_root).hostname
        if url.hostname == codehosting_host:
            repository = getUtility(IGitLookup).getByUrl(self.repository_url)
            if repository is not None:
                # This is one of our own repositories.  Doing this by URL
                # seems gratuitously complex, but apparently we already have
                # some examples of this on production.
                return repository.getBlob(filename, rev=self.path)
        raise GitRepositoryBlobUnsupportedRemote(self.repository_url)

    @property
    def recipes(self):
        """See `IHasRecipes`."""
        return []

    def getGrants(self):
        """See `IGitRef`."""
        return []

    setGrants = _unimplemented
    checkPermissions = _unimplemented
