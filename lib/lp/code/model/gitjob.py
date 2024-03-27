# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "describe_repository_delta",
    "GitJob",
    "GitJobType",
    "GitRefScanJob",
    "GitRepositoryModifiedMailJob",
    "ReclaimGitRepositorySpaceJob",
]


from lazr.delegates import delegate_to
from lazr.enum import DBEnumeratedType, DBItem
from storm.exceptions import LostObjectError
from storm.locals import JSON, SQL, Int, Reference, Store
from zope.component import getUtility
from zope.interface import implementer, provider

from lp.app.errors import NotFoundError
from lp.code.enums import GitActivityType, GitPermissionType
from lp.code.interfaces.githosting import IGitHostingClient
from lp.code.interfaces.gitjob import (
    IGitJob,
    IGitRefScanJob,
    IGitRefScanJobSource,
    IGitRepositoryModifiedMailJob,
    IGitRepositoryModifiedMailJobSource,
    IReclaimGitRepositorySpaceJob,
    IReclaimGitRepositorySpaceJobSource,
)
from lp.code.interfaces.gitrule import describe_git_permissions
from lp.code.mail.branch import BranchMailer
from lp.registry.interfaces.person import IPersonSet
from lp.services.config import config
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import IPrimaryStore, IStore
from lp.services.database.locking import (
    AdvisoryLockHeld,
    LockType,
    try_advisory_lock,
)
from lp.services.database.stormbase import StormBase
from lp.services.helpers import english_list
from lp.services.job.model.job import EnumeratedSubclass, Job
from lp.services.job.runner import BaseRunnableJob
from lp.services.mail.sendmail import format_address_for_person
from lp.services.scripts import log
from lp.services.utils import text_delta
from lp.services.webapp.publisher import canonical_url
from lp.services.webhooks.interfaces import IWebhookSet


class GitJobType(DBEnumeratedType):
    """Values that `IGitJob.job_type` can take."""

    REF_SCAN = DBItem(
        0,
        """
        Ref scan

        This job scans a repository for its current list of references.
        """,
    )

    RECLAIM_REPOSITORY_SPACE = DBItem(
        1,
        """
        Reclaim repository space

        This job removes a repository that has been deleted from the
        database from storage.
        """,
    )

    REPOSITORY_MODIFIED_MAIL = DBItem(
        2,
        """
        Repository modified mail

        This job runs against a repository to send emails about
        modifications.
        """,
    )


@implementer(IGitJob)
class GitJob(StormBase):
    """See `IGitJob`."""

    __storm_table__ = "GitJob"

    job_id = Int(name="job", primary=True, allow_none=False)
    job = Reference(job_id, "Job.id")

    repository_id = Int(name="repository", allow_none=True)
    repository = Reference(repository_id, "GitRepository.id")

    job_type = DBEnum(enum=GitJobType, allow_none=False)

    metadata = JSON("json_data")

    def __init__(self, repository, job_type, metadata, **job_args):
        """Constructor.

        Extra keyword arguments are used to construct the underlying Job
        object.

        :param repository: The database repository this job relates to.
        :param job_type: The `GitJobType` of this job.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        super().__init__()
        self.job = Job(**job_args)
        self.repository = repository
        self.job_type = job_type
        self.metadata = metadata
        if repository is not None:
            self.metadata["repository_name"] = repository.unique_name

    def makeDerived(self):
        return GitJobDerived.makeSubclass(self)


@delegate_to(IGitJob)
class GitJobDerived(BaseRunnableJob, metaclass=EnumeratedSubclass):
    def __init__(self, git_job):
        self.context = git_job
        self._cached_repository_name = self.metadata["repository_name"]

    def __repr__(self):
        """Returns an informative representation of the job."""
        return "<%s for %s>" % (
            self.__class__.__name__,
            self._cached_repository_name,
        )

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: The `GitJob` with the specified id, as the current
            `GitJobDerived` subclass.
        :raises: `NotFoundError` if there is no job with the specified id,
            or its `job_type` does not match the desired subclass.
        """
        git_job = IStore(GitJob).get(GitJob, job_id)
        if git_job.job_type != cls.class_job_type:
            raise NotFoundError(
                "No object found with id %d and type %s"
                % (job_id, cls.class_job_type.title)
            )
        return cls(git_job)

    @classmethod
    def iterReady(cls):
        """See `IJobSource`."""
        jobs = IPrimaryStore(GitJob).find(
            GitJob,
            GitJob.job_type == cls.class_job_type,
            GitJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs),
        )
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        oops_vars = super().getOopsVars()
        oops_vars.extend(
            [
                ("git_job_id", self.context.job.id),
                ("git_job_type", self.context.job_type.title),
            ]
        )
        if self.context.repository is not None:
            oops_vars.append(("git_repository_id", self.context.repository.id))
        if "repository_name" in self.metadata:
            oops_vars.append(
                ("git_repository_name", self.metadata["repository_name"])
            )
        return oops_vars

    def getErrorRecipients(self):
        if self.requester is None:
            return []
        return [format_address_for_person(self.requester)]


@implementer(IGitRefScanJob)
@provider(IGitRefScanJobSource)
class GitRefScanJob(GitJobDerived):
    """A Job that scans a Git repository for its current list of references."""

    class_job_type = GitJobType.REF_SCAN

    max_retries = 5

    retry_error_types = (AdvisoryLockHeld,)

    config = config.IGitRefScanJobSource

    @classmethod
    def create(cls, repository):
        """See `IGitRefScanJobSource`."""
        git_job = GitJob(repository, cls.class_job_type, {})
        job = cls(git_job)
        job.celeryRunOnCommit()
        IStore(GitJob).flush()
        return job

    @staticmethod
    def composeWebhookPayload(
        repository, old_refs_commits, refs_to_upsert, refs_to_remove
    ):
        ref_changes = {}
        for ref in list(refs_to_upsert) + list(refs_to_remove):
            old = (
                {"commit_sha1": old_refs_commits[ref]}
                if ref in old_refs_commits
                else None
            )
            new = (
                {"commit_sha1": refs_to_upsert[ref]["sha1"]}
                if ref in refs_to_upsert
                else None
            )
            # planRefChanges can return an unchanged ref if the cached
            # commit details differ.
            if old != new:
                ref_changes[ref] = {"old": old, "new": new}
        return {
            "git_repository": canonical_url(repository, force_local_path=True),
            "git_repository_path": repository.shortened_path,
            "ref_changes": ref_changes,
        }

    def run(self):
        """See `IGitRefScanJob`."""
        try:
            with try_advisory_lock(
                LockType.GIT_REF_SCAN,
                self.repository.id,
                Store.of(self.repository),
            ):
                old_refs_commits = {
                    ref.path: ref.commit_sha1 for ref in self.repository.refs
                }
                upserted_refs, removed_refs = self.repository.scan(log=log)
                payload = self.composeWebhookPayload(
                    self.repository,
                    old_refs_commits,
                    upserted_refs,
                    removed_refs,
                )
                git_refs = list(payload["ref_changes"].keys())
                getUtility(IWebhookSet).trigger(
                    self.repository,
                    "git:push:0.1",
                    payload,
                    git_refs=git_refs,
                )
        except LostObjectError:
            log.info(
                "Skipping repository %s because it has been deleted."
                % self._cached_repository_name
            )


@implementer(IReclaimGitRepositorySpaceJob)
@provider(IReclaimGitRepositorySpaceJobSource)
class ReclaimGitRepositorySpaceJob(GitJobDerived):
    """A Job that deletes a repository from storage after it has been
    deleted from the database."""

    class_job_type = GitJobType.RECLAIM_REPOSITORY_SPACE

    config = config.IReclaimGitRepositorySpaceJobSource

    @classmethod
    def create(cls, repository_name, repository_path):
        "See `IReclaimGitRepositorySpaceJobSource`." ""
        metadata = {
            "repository_name": repository_name,
            "repository_path": repository_path,
        }
        # The GitJob has a repository of None, as there is no repository
        # left in the database to refer to.
        start = SQL("CURRENT_TIMESTAMP AT TIME ZONE 'UTC' + '7 days'")
        git_job = GitJob(
            None, cls.class_job_type, metadata, scheduled_start=start
        )
        job = cls(git_job)
        job.celeryRunOnCommit()
        IStore(GitJob).flush()
        return job

    @property
    def repository_path(self):
        return self.metadata["repository_path"]

    def run(self):
        getUtility(IGitHostingClient).delete(self.repository_path, logger=log)


activity_descriptions = {
    GitActivityType.RULE_ADDED: "Added protected ref: {new[ref_pattern]}",
    GitActivityType.RULE_CHANGED: (
        "Changed protected ref: {old[ref_pattern]} => {new[ref_pattern]}"
    ),
    GitActivityType.RULE_REMOVED: "Removed protected ref: {old[ref_pattern]}",
    GitActivityType.RULE_MOVED: (
        "Moved rule for protected ref {new[ref_pattern]}: "
        "position {old[position]} => {new[position]}"
    ),
    GitActivityType.GRANT_ADDED: (
        "Added access for {changee} to {new[ref_pattern]}: {new_grants}"
    ),
    GitActivityType.GRANT_CHANGED: (
        "Changed access for {changee} to {new[ref_pattern]}: "
        "{old_grants} => {new_grants}"
    ),
    GitActivityType.GRANT_REMOVED: (
        "Removed access for {changee} to {old[ref_pattern]}: {old_grants}"
    ),
}


_activity_permissions = {
    "can_create": GitPermissionType.CAN_CREATE,
    "can_push": GitPermissionType.CAN_PUSH,
    "can_force_push": GitPermissionType.CAN_FORCE_PUSH,
}


def describe_grants(activity_value):
    if activity_value is not None:
        output = describe_git_permissions(
            {
                permission
                for attr, permission in _activity_permissions.items()
                if activity_value.get(attr)
            }
        )
    else:
        output = []
    return english_list(output)


def describe_repository_delta(repository_delta):
    output = text_delta(
        repository_delta,
        repository_delta.delta_values,
        repository_delta.new_values,
        repository_delta.interface,
    ).split("\n")
    if output and not output[-1]:  # text_delta returned empty string
        output.pop()
    # Parts of the delta are only visible to people who can edit the
    # repository.
    output_for_editors = list(output)
    indent = " " * 4
    for activity in repository_delta.activities:
        if activity.what_changed in activity_descriptions:
            description = activity_descriptions[activity.what_changed].format(
                old=activity.old_value,
                new=activity.new_value,
                changee=activity.changee_description,
                old_grants=describe_grants(activity.old_value),
                new_grants=describe_grants(activity.new_value),
            )
            output_for_editors.append(indent + description)
    return "\n".join(output), "\n".join(output_for_editors)


@implementer(IGitRepositoryModifiedMailJob)
@provider(IGitRepositoryModifiedMailJobSource)
class GitRepositoryModifiedMailJob(GitJobDerived):
    """A Job that sends email about repository modifications."""

    class_job_type = GitJobType.REPOSITORY_MODIFIED_MAIL

    config = config.IGitRepositoryModifiedMailJobSource

    @classmethod
    def create(cls, repository, user, repository_delta):
        """See `IGitRepositoryModifiedMailJobSource`."""
        delta, delta_for_editors = describe_repository_delta(repository_delta)
        metadata = {
            "user": user.id,
            "repository_delta": delta,
            "repository_delta_for_editors": delta_for_editors,
        }
        git_job = GitJob(repository, cls.class_job_type, metadata)
        job = cls(git_job)
        job.celeryRunOnCommit()
        IStore(GitJob).flush()
        return job

    @property
    def user(self):
        return getUtility(IPersonSet).get(self.metadata["user"])

    @property
    def repository_delta(self):
        return self.metadata["repository_delta"]

    @property
    def repository_delta_for_editors(self):
        return self.metadata["repository_delta_for_editors"]

    def getMailer(self):
        """Return a `BranchMailer` for this job."""
        return BranchMailer.forBranchModified(
            self.repository,
            self.user,
            self.repository_delta,
            delta_for_editors=self.repository_delta_for_editors,
        )

    def run(self):
        """See `IGitRepositoryModifiedMailJob`."""
        self.getMailer().sendAll()
