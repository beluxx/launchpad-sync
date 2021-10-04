# Copyright 2015-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git reference ("ref") interfaces."""

__all__ = [
    'IGitRef',
    'IGitRefBatchNavigator',
    'IGitRefRemote',
    'IGitRefRemoteSet',
    'IGitRefSet',
    ]

from textwrap import dedent

from lazr.restful.declarations import (
    call_with,
    export_factory_operation,
    export_read_operation,
    export_write_operation,
    exported,
    exported_as_webservice_entry,
    operation_for_version,
    operation_parameters,
    operation_returns_collection_of,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    ReferenceChoice,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    List,
    Text,
    TextLine,
    )

from lp import _
from lp.app.interfaces.informationtype import IInformationType
from lp.app.interfaces.launchpad import IPrivacy
from lp.code.enums import (
    BranchMergeProposalStatus,
    GitObjectType,
    )
from lp.code.interfaces.hasbranches import IHasMergeProposals
from lp.code.interfaces.hasrecipes import IHasRecipes
from lp.registry.interfaces.person import IPerson
from lp.services.fields import InlineObject
from lp.services.webapp.interfaces import ITableBatchNavigator


class IGitRefView(IHasMergeProposals, IHasRecipes, IPrivacy, IInformationType):
    """IGitRef attributes that require launchpad.View permission."""

    repository = exported(ReferenceChoice(
        title=_("Repository"), required=True, readonly=True,
        vocabulary="GitRepository",
        # Really IGitRepository, patched in _schema_circular_imports.py.
        schema=Interface,
        description=_("The Git repository containing this reference.")))

    repository_url = Attribute(
        "The repository URL, if this is a reference in a remote repository.")

    path = exported(TextLine(
        title=_("Path"), required=True, readonly=True,
        description=_(
            "The full path of this reference, e.g. refs/heads/master.")))

    name = Attribute(
        "A shortened version of the full path to this reference, with any "
        "leading refs/heads/ removed.")

    url_quoted_name = Attribute("The reference name, quoted for use in URLs.")

    commit_sha1 = exported(TextLine(
        title=_("Commit SHA-1"), required=True, readonly=True,
        description=_(
            "The full SHA-1 object name of the commit object referenced by "
            "this reference.")))

    object_type = Choice(
        title=_("Object type"), required=True, readonly=True,
        vocabulary=GitObjectType)

    author = Attribute(
        "The author of the commit pointed to by this reference.")
    author_date = Datetime(
        title=_("The author date of the commit pointed to by this reference."),
        required=False, readonly=True)

    committer = Attribute(
        "The committer of the commit pointed to by this reference.")
    committer_date = Datetime(
        title=_(
            "The committer date of the commit pointed to by this reference."),
        required=False, readonly=True)

    commit_message = Text(
        title=_(
            "The commit message of the commit pointed to by this reference."),
        required=False, readonly=True)

    display_name = TextLine(
        title=_("Display name"), required=True, readonly=True,
        description=_("Display name of the reference."))

    displayname = Attribute(
        "Copy of display_name for IHasMergeProposals views.")

    commit_message_first_line = TextLine(
        title=_("The first line of the commit message."),
        required=False, readonly=True)

    identity = Attribute(
        "The identity of this reference.  This will be the shortened path to "
        "the containing repository, plus a colon, plus the reference path "
        "with any leading refs/heads/ removed; for example, launchpad:master.")

    unique_name = Attribute(
        "The unique name of this reference.  This will be the unique name of "
        "the containing repository, plus a colon, plus the reference path "
        "with any leading refs/heads/ removed; for example, "
        "~launchpad-pqm/launchpad:master.")

    repository_type = Attribute(
        "The type of the repository containing this reference.")

    owner = Attribute("The owner of the repository containing this reference.")

    target = Attribute(
        "The target of the repository containing this reference.")

    namespace = Attribute(
        "The namespace of the repository containing this reference, as an "
        "`IGitNamespace`.")

    def getCodebrowseUrl():
        """Construct a browsing URL for this Git reference."""

    def getCodebrowseUrlForRevision(commit):
        """Construct a browsing URL for this Git at the given commit"""

    information_type = Attribute(
        "The type of information contained in the repository containing this "
        "reference.")

    private = Bool(
        title=_("Private"), required=False, readonly=True,
        description=_(
            "The repository containing this reference is visible only to its "
            "subscribers."))

    def visibleByUser(user):
        """Can the specified user see the repository containing this
        reference?"""

    def transitionToInformationType(information_type, user,
                                    verify_policy=True):
        """Set the information type for this reference's repository.

        :param information_type: The `InformationType` to transition to.
        :param user: The `IPerson` who is making the change.
        :param verify_policy: Check if the new information type complies
            with the `IGitNamespacePolicy`.
        """

    reviewer = Attribute(
        "The person or exclusive team that is responsible for reviewing "
        "proposals and merging into this reference.")

    code_reviewer = Attribute(
        "The reviewer if set, otherwise the owner of the repository "
        "containing this reference.")

    def isPersonTrustedReviewer(reviewer):
        """Return true if the `reviewer` is a trusted reviewer.

        The reviewer is trusted if they either own the repository containing
        this reference, or are in the team that owns the repository, or they
        are in the review team for the repository.
        """

    subscriptions = Attribute(
        "GitSubscriptions associated with the repository containing this "
        "reference.")

    subscribers = Attribute(
        "Persons subscribed to the repository containing this reference.")

    def subscribe(person, notification_level, max_diff_lines,
                  code_review_level, subscribed_by):
        """Subscribe this person to the repository containing this reference.

        :param person: The `Person` to subscribe.
        :param notification_level: The kinds of repository changes that
            cause notification.
        :param max_diff_lines: The maximum number of lines of diff that may
            appear in a notification.
        :param code_review_level: The kinds of code review activity that
            cause notification.
        :param subscribed_by: The person who is subscribing the subscriber.
            Most often the subscriber themselves.
        :return: A new or existing `GitSubscription`.
        """

    def getSubscription(person):
        """Return the `GitSubscription` for this person."""

    def unsubscribe(person, unsubscribed_by):
        """Remove the person's subscription to this reference's repository.

        :param person: The person or team to unsubscribe from the repository.
        :param unsubscribed_by: The person doing the unsubscribing.
        """

    def getNotificationRecipients():
        """Return a complete INotificationRecipientSet instance.

        The INotificationRecipientSet instance contains the subscribers
        and their subscriptions.
        """

    landing_targets = Attribute(
        "A collection of the merge proposals where this reference is "
        "the source.")
    _api_landing_targets = exported(
        CollectionField(
            title=_("Landing targets"),
            description=_(
                "A collection of the merge proposals where this reference is "
                "the source."),
            readonly=True,
            # Really IBranchMergeProposal, patched in
            # _schema_circular_imports.py.
            value_type=Reference(Interface)),
        exported_as="landing_targets")
    landing_candidates = Attribute(
        "A collection of the merge proposals where this reference is "
        "the target.")
    _api_landing_candidates = exported(
        CollectionField(
            title=_("Landing candidates"),
            description=_(
                "A collection of the merge proposals where this reference is "
                "the target."),
            readonly=True,
            # Really IBranchMergeProposal, patched in
            # _schema_circular_imports.py.
            value_type=Reference(Interface)),
        exported_as="landing_candidates")
    dependent_landings = exported(CollectionField(
        title=_("Dependent landings"),
        description=_(
            "A collection of the merge proposals that are dependent on this "
            "reference."),
        readonly=True,
        # Really IBranchMergeProposal, patched in _schema_circular_imports.py.
        value_type=Reference(Interface)))

    def getPrecachedLandingTargets(user):
        """Return precached landing targets.

        Target and prerequisite repositories are preloaded.
        """

    def getPrecachedLandingCandidates(user):
        """Return precached landing candidates.

        Source and prerequisite repositories are preloaded.
        """

    # XXX cjwatson 2015-04-16: Rename in line with landing_targets above
    # once we have a better name.
    def addLandingTarget(registrant, merge_target, merge_prerequisite=None,
                         date_created=None, needs_review=None,
                         description=None, review_requests=None,
                         commit_message=None):
        """Create a new BranchMergeProposal with this reference as the source.

        Both the target and the prerequisite, if it is there, must be
        references whose repositories have the same target as the source.

        References in personal repositories cannot specify merge proposals.

        :param registrant: The person who is adding the landing target.
        :param merge_target: Must be another reference, and different to
            self.
        :param merge_prerequisite: Optional, but if it is not None it must
            be another reference.
        :param date_created: Used to specify the date_created value of the
            merge request.
        :param needs_review: Used to specify the proposal is ready for
            review right now.
        :param description: A description of the bugs fixed, features added,
            or refactorings.
        :param review_requests: An optional list of (`Person`, review_type).
        """

    @operation_parameters(
        # merge_target and merge_prerequisite are actually IGitRef, patched
        # in _schema_circular_imports.
        merge_target=Reference(schema=Interface),
        merge_prerequisite=Reference(schema=Interface),
        needs_review=Bool(
            title=_("Needs review"),
            description=_(
                "If True, the proposal needs review.  Otherwise, it will be "
                "work in progress.")),
        initial_comment=Text(
            title=_("Initial comment"),
            description=_("Registrant's initial description of proposal.")),
        commit_message=Text(
            title=_("Commit message"),
            description=_("Message to use when committing this merge.")),
        reviewers=List(value_type=Reference(schema=IPerson)),
        review_types=List(value_type=TextLine()))
    @call_with(registrant=REQUEST_USER)
    # Really IBranchMergeProposal, patched in _schema_circular_imports.py.
    @export_factory_operation(Interface, [])
    @operation_for_version("devel")
    def createMergeProposal(registrant, merge_target, merge_prerequisite=None,
                            needs_review=None, initial_comment=None,
                            commit_message=None, reviewers=None,
                            review_types=None):
        """Create a new BranchMergeProposal with this reference as the source.

        Both the merge_target and the merge_prerequisite, if it is there,
        must be references whose repositories have the same target as the
        source.

        References in personal repositories cannot specify merge proposals.
        """

    @operation_parameters(
        status=List(
            title=_("A list of merge proposal statuses to filter by."),
            value_type=Choice(vocabulary=BranchMergeProposalStatus)),
        merged_revision_ids=List(TextLine(
            title=_('The target revision ID of the merge.'))))
    @call_with(visible_by_user=REQUEST_USER)
    # Really IBranchMergeProposal, patched in _schema_circular_imports.py.
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    @operation_for_version("devel")
    def getMergeProposals(status=None, visible_by_user=None,
                          merged_revision_ids=None, eager_load=False):
        """Return matching BranchMergeProposals."""

    def getDependentMergeProposals(status=None, visible_by_user=None,
                                   eager_load=False):
        """Return BranchMergeProposals dependent on merging this reference."""

    pending_updates = Attribute(
        "Whether there are recent changes in this repository that have not "
        "yet been scanned.")

    def getCommits(start, limit=None, stop=None, union_repository=None,
                   start_date=None, end_date=None, handle_timeout=False,
                   logger=None):
        """Get commit information from this reference.

        :param start: The commit to start listing from.
        :param limit: If not None, return no more than this many commits.
        :param stop: If not None, ignore this commit and its ancestors.
        :param union_repository: If not None, resolve commit identifiers in
            this repository as well (particularly useful with `stop`).
        :param start_date: If not None, ignore commits before this date.
        :param end_date: If not None, ignore commits after this date.
        :param handle_timeout: If True and the backend request times out,
            synthesise commit information from what we have in the database.
        :param logger: An optional logger.
        :return: An iterable of commit information dicts.
        """

    def getLatestCommits(quantity=10, extended_details=False, user=None,
                         handle_timeout=False, logger=None):
        """Return a specific number of the latest commits in this ref."""

    has_commits = Attribute("Whether this reference has any commits.")

    def getBlob(filename):
        """Get a blob by file name from this reference.

        :param filename: Relative path of a file in the repository.
        :return: A binary string with the blob content.
        """

    def getLatestScanJob():
        """Return the last IGitRefScanJobSource for the repository"""

    def rescan():
        """Force a rescan of the repository"""


class IGitRefEdit(Interface):
    """IGitRef methods that require launchpad.Edit permission."""

    @export_read_operation()
    @operation_for_version("devel")
    def getGrants():
        """Get the access grants specific to this reference.

        Other grants may apply via wildcard rules.
        """

    @operation_parameters(
        grants=List(
            title=_("Grants"),
            # Really IGitNascentRuleGrant, patched in
            # _schema_circular_imports.py.
            value_type=InlineObject(schema=Interface),
            description=_(dedent("""\
                The new list of grants for this reference.

                For example::

                    [
                        {
                            "grantee_type": "Repository owner",
                            "can_create": true,
                            "can_push": true,
                            "can_force_push": true
                        },
                        {
                            "grantee_type": "Person",
                            "grantee_link": "/~example-person",
                            "can_push": true
                        }
                    ]"""))))
    @call_with(user=REQUEST_USER)
    @export_write_operation()
    @operation_for_version("devel")
    def setGrants(grants, user):
        """Set the access grants specific to this reference.

        Other grants may apply via wildcard rules.
        """

    @operation_parameters(
        person=Reference(title=_("Person to check"), schema=IPerson))
    @export_read_operation()
    @operation_for_version("devel")
    def checkPermissions(person):
        """Check a person's permissions on this reference.

        :param person: An `IPerson` to check.
        :return: A list of zero or more of "create", "push", and
            "force-push", indicating the requested person's effective
            permissions on this reference.
        """


# XXX cjwatson 2015-01-19 bug=760849: "beta" is a lie to get WADL
# generation working.  Individual attributes must set their version to
# "devel".
@exported_as_webservice_entry(as_of="beta")
class IGitRef(IGitRefView, IGitRefEdit):
    """A reference in a Git repository."""


class IGitRefRemote(Interface):
    """Marker interface for a reference in a remote Git repository."""
    # XXX cjwatson 2020-12-16: Implementers of this don't implement IGitRef
    # correctly: several required properties will raise NotImplementedError.
    # We may need to split out the parts of IGitRef that don't apply to
    # remote references, and make this a full (non-marker) interface.


class IGitRefSet(Interface):
    def findByReposAndPaths(repos_and_paths):
        """Returns the collection of GitRefs for the given list of tuples
        (GitRepository, path).

        The "path" part of the tuple can be the shortcut version (e.g
        "master") or the full path (e.g "refs/heads/master"). If it's the
        short version, we also search for "refs/head/$path".

        :param repos_and_paths: A list of tuples with git repos and paths
        :return: A dict where the keys are the tuples provided, and the
                 values are the GitRef objects. If a given tuple is not
                 found, the key will be missing in the dictionary.
        """


class IGitRefBatchNavigator(ITableBatchNavigator):
    pass


class IGitRefRemoteSet(Interface):
    """Interface allowing creation of `GitRefRemote`s."""

    def new(repository_url, path):
        """Create a new remote reference."""
