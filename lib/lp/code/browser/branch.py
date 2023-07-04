# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Branch views."""

__all__ = [
    "BranchBreadcrumb",
    "BranchContextMenu",
    "BranchDeletionView",
    "BranchEditStatusView",
    "BranchEditView",
    "BranchEditWhiteboardView",
    "BranchReviewerEditView",
    "BranchMirrorStatusView",
    "BranchMirrorMixin",
    "BranchNavigation",
    "BranchEditMenu",
    "BranchUpgradeView",
    "BranchURL",
    "BranchView",
    "CodeEditOwnerMixin",
    "RegisterBranchMergeProposalView",
]

import json
from datetime import datetime, timezone

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from lazr.restful.fields import Reference
from lazr.restful.interface import copy_field, use_template
from lazr.uri import URI
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.formlib.widget import CustomWidgetFactory
from zope.formlib.widgets import TextAreaWidget
from zope.interface import Interface, implementer, providedBy
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.schema import Bool, Choice, Text
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from lp import _
from lp.app.browser.informationtype import InformationTypePortletMixin
from lp.app.browser.launchpadform import (
    LaunchpadEditFormView,
    LaunchpadFormView,
    action,
)
from lp.app.browser.lazrjs import EnumChoiceWidget
from lp.app.enums import InformationType
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.vocabularies import InformationTypeVocabulary
from lp.app.widgets.itemswidgets import LaunchpadRadioWidgetWithDescription
from lp.app.widgets.suggestion import TargetBranchWidget
from lp.blueprints.interfaces.specificationbranch import ISpecificationBranch
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.interfaces.bugbranch import IBugBranch
from lp.bugs.interfaces.bugtask import UNRESOLVED_BUGTASK_STATUSES, IBugTaskSet
from lp.bugs.interfaces.bugtasksearch import BugTaskSearchParams
from lp.code.browser.branchmergeproposal import (
    latest_proposals_for_each_branch,
)
from lp.code.browser.branchref import BranchRef
from lp.code.browser.codeimport import CodeImportTargetMixin
from lp.code.browser.decorations import DecoratedBranch
from lp.code.browser.sourcepackagerecipelisting import HasRecipesMenuMixin
from lp.code.browser.widgets.branchtarget import BranchTargetWidget
from lp.code.enums import BranchType
from lp.code.errors import (
    BranchCreationForbidden,
    BranchExists,
    BranchTargetError,
    CannotUpgradeBranch,
    InvalidBranchMergeProposal,
)
from lp.code.interfaces.branch import IBranch, IBranchSet
from lp.code.interfaces.branchcollection import IAllBranches
from lp.code.interfaces.branchmergeproposal import IBranchMergeProposal
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.code.interfaces.codereviewvote import ICodeReviewVoteReference
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.vocabularies import UserTeamsParticipationPlusSelfVocabulary
from lp.services import searchbuilder
from lp.services.config import config
from lp.services.database.constants import UTC_NOW
from lp.services.features import getFeatureFlag
from lp.services.feeds.browser import BranchFeedLink, FeedsMixin
from lp.services.helpers import english_list, truncate_text
from lp.services.job.interfaces.job import JobStatus
from lp.services.propertycache import cachedproperty
from lp.services.webapp import (
    ContextMenu,
    LaunchpadView,
    Link,
    Navigation,
    NavigationMenu,
    canonical_url,
    enabled_with_permission,
    stepthrough,
    stepto,
)
from lp.services.webapp.authorization import (
    check_permission,
    precache_permission_for_objects,
)
from lp.services.webapp.breadcrumb import NameBreadcrumb
from lp.services.webapp.escaping import structured
from lp.services.webapp.interfaces import ICanonicalUrlData
from lp.services.webapp.publisher import DataDownloadView
from lp.services.webhooks.browser import WebhookTargetNavigationMixin
from lp.snappy.browser.hassnaps import HasSnapsMenuMixin, HasSnapsViewMixin
from lp.translations.interfaces.translationtemplatesbuild import (
    ITranslationTemplatesBuildSource,
)


@implementer(ICanonicalUrlData)
class BranchURL:
    """Branch URL creation rules."""

    rootsite = "code"
    inside = None

    def __init__(self, branch):
        self.branch = branch

    @property
    def path(self):
        return self.branch.unique_name


class BranchBreadcrumb(NameBreadcrumb):
    @property
    def inside(self):
        return self.context.target.components[-1]


class BranchNavigation(WebhookTargetNavigationMixin, Navigation):
    usedfor = IBranch

    @stepthrough("+bug")
    def traverse_bug_branch(self, bugid):
        """Traverses to an `IBugBranch`."""
        bug = getUtility(IBugSet).get(bugid)

        for bug_branch in bug.linked_bugbranches:
            if bug_branch.branch == self.context:
                return bug_branch

    @stepto(".bzr")
    def dotbzr(self):
        return BranchRef(self.context)

    @stepthrough("+subscription")
    def traverse_subscription(self, name):
        """Traverses to an `IBranchSubscription`."""
        person = getUtility(IPersonSet).getByName(name)

        if person is not None:
            return self.context.getSubscription(person)

    @stepthrough("+merge")
    def traverse_merge_proposal(self, id):
        """Traverse to an `IBranchMergeProposal`."""
        try:
            id = int(id)
        except ValueError:
            # Not a number.
            return None
        return self.context.getMergeProposalByID(id)

    @stepto("+diff")
    def traverse_diff(self):
        segments = list(self.request.getTraversalStack())
        if len(segments) == 1:
            new = segments.pop()
            old = None
            self.request.stepstogo.consume()
        elif len(segments) == 2:
            new = segments.pop()
            old = segments.pop()
            self.request.stepstogo.consume()
            self.request.stepstogo.consume()
        else:
            return None
        return BranchDiffView(self.context, self.request, new, old=old)

    @stepto("+code-import")
    def traverse_code_import(self):
        """Traverses to the `ICodeImport` for the branch."""
        return self.context.code_import

    @stepthrough("+translation-templates-build")
    def traverse_translation_templates_build(self, id_string):
        """Traverses to a `TranslationTemplatesBuild`."""
        from lp.soyuz.browser.build import get_build_by_id_str

        ttb = get_build_by_id_str(ITranslationTemplatesBuildSource, id_string)
        if ttb is None or ttb.branch != self.context:
            return None
        return ttb


class BranchEditMenu(NavigationMenu):
    """Edit menu for IBranch."""

    usedfor = IBranch
    facet = "branches"
    title = "Edit branch"
    links = ("edit", "reviewer", "edit_whiteboard", "webhooks", "delete")

    @enabled_with_permission("launchpad.Edit")
    def edit(self):
        text = "Change branch details"
        return Link("+edit", text, icon="edit")

    @enabled_with_permission("launchpad.Moderate")
    def delete(self):
        text = "Delete branch"
        return Link("+delete", text, icon="trash-icon")

    @enabled_with_permission("launchpad.AnyPerson")
    def edit_whiteboard(self):
        text = "Edit whiteboard"
        enabled = self.context.branch_type == BranchType.IMPORTED
        return Link("+whiteboard", text, icon="edit", enabled=enabled)

    @enabled_with_permission("launchpad.Edit")
    def reviewer(self):
        text = "Set branch reviewer"
        return Link("+reviewer", text, icon="edit")

    @enabled_with_permission("launchpad.Edit")
    def webhooks(self):
        text = "Manage webhooks"
        return Link("+webhooks", text, icon="edit")


class BranchContextMenu(ContextMenu, HasRecipesMenuMixin, HasSnapsMenuMixin):
    """Context menu for branches."""

    usedfor = IBranch
    facet = "branches"
    links = [
        "add_subscriber",
        "browse_revisions",
        "create_recipe",
        "create_snap",
        "link_bug",
        "link_blueprint",
        "register_merge",
        "source",
        "subscription",
        "edit_status",
        "edit_import",
        "upgrade_branch",
        "view_recipes",
        "view_snaps",
        "visibility",
    ]

    @enabled_with_permission("launchpad.Edit")
    def edit_status(self):
        text = "Change branch status"
        return Link("+edit-status", text, icon="edit")

    @enabled_with_permission("launchpad.Moderate")
    def visibility(self):
        """Return the 'Set information type' Link."""
        text = "Change information type"
        return Link("+edit-information-type", text)

    def browse_revisions(self):
        """Return a link to the branch's revisions on codebrowse."""
        text = "All revisions"
        enabled = self.context.code_is_browsable
        url = self.context.getCodebrowseUrl("changes")
        return Link(url, text, enabled=enabled)

    @enabled_with_permission("launchpad.AnyPerson")
    def subscription(self):
        if self.context.hasSubscription(self.user):
            url = "+edit-subscription"
            text = "Edit your subscription"
            icon = "edit"
        else:
            url = "+subscribe"
            text = "Subscribe yourself"
            icon = "add"
        return Link(url, text, icon=icon)

    @enabled_with_permission("launchpad.AnyPerson")
    def add_subscriber(self):
        text = "Subscribe someone else"
        return Link("+addsubscriber", text, icon="add")

    def register_merge(self):
        text = "Propose for merging"
        enabled = (
            self.context.target.supports_merge_proposals
            and not self.context.branch_type == BranchType.IMPORTED
        )
        return Link("+register-merge", text, icon="add", enabled=enabled)

    def link_bug(self):
        text = "Link a bug report"
        return Link("+linkbug", text, icon="add")

    def link_blueprint(self):
        if list(self.context.getSpecificationLinks(self.user)):
            text = "Link to another blueprint"
        else:
            text = "Link to a blueprint"
        # XXX: JonathanLange 2009-05-13 spec=package-branches: Actually,
        # distroseries can also have blueprints, so it makes sense to
        # associate package-branches with them.
        #
        # Since the blueprints are only related to products, there is no
        # point showing this link if the branch is junk.
        enabled = self.context.product is not None
        return Link("+linkblueprint", text, icon="add", enabled=enabled)

    def source(self):
        """Return a link to the branch's file listing on codebrowse."""
        text = "Browse the code"
        enabled = self.context.code_is_browsable
        url = self.context.getCodebrowseUrl("files")
        return Link(url, text, icon="info", enabled=enabled)

    def edit_import(self):
        text = "Edit import source or review import"
        enabled = (
            self.context.branch_type == BranchType.IMPORTED
            and check_permission("launchpad.Edit", self.context.code_import)
        )
        return Link("+edit-import", text, icon="edit", enabled=enabled)

    @enabled_with_permission("launchpad.Edit")
    def upgrade_branch(self):
        enabled = self.context.needs_upgrading
        return Link(
            "+upgrade", "Upgrade this branch", icon="edit", enabled=enabled
        )

    def create_recipe(self):
        # You can't create a recipe for a private branch.
        enabled = not self.context.private
        text = "Create packaging recipe"
        return Link("+new-recipe", text, enabled=enabled, icon="add")


class BranchMirrorMixin:
    """Provide mirror_location property.

    Requires self.branch to be set by the class using this mixin.
    """

    @property
    def mirror_location(self):
        """Check the mirror location to see if it is a private one."""
        branch = self.branch

        # If the user has edit permissions, then show the actual location.
        if branch.url is None or check_permission("launchpad.Edit", branch):
            return branch.url

        # XXX: Tim Penhey, 2008-05-30, bug 235916
        # Instead of a configuration hack we should support the users
        # specifying whether or not they want the mirror location
        # hidden or not.  Given that this is a database patch,
        # it isn't going to happen today.
        hosts = config.codehosting.private_mirror_hosts.split(",")
        private_mirror_hosts = [name.strip() for name in hosts]

        uri = URI(branch.url)
        for private_host in private_mirror_hosts:
            if uri.underDomain(private_host):
                return "<private server>"

        return branch.url


class BranchView(
    InformationTypePortletMixin,
    FeedsMixin,
    BranchMirrorMixin,
    LaunchpadView,
    HasSnapsViewMixin,
    CodeImportTargetMixin,
):
    feed_types = (BranchFeedLink,)

    @property
    def page_title(self):
        return self.context.bzr_identity

    label = page_title

    def initialize(self):
        super().initialize()
        self.branch = self.context
        self.notices = []
        # Cache permission so private team owner can be rendered.
        # The security adaptor will do the job also but we don't want or need
        # the expense of running several complex SQL queries.
        authorised_people = [self.branch.owner]
        if self.user is not None:
            precache_permission_for_objects(
                self.request, "launchpad.LimitedView", authorised_people
            )
        # Replace our context with a decorated branch, if it is not already
        # decorated.
        if not isinstance(self.context, DecoratedBranch):
            self.context = DecoratedBranch(self.context)

    def user_is_subscribed(self):
        """Is the current user subscribed to this branch?"""
        if self.user is None:
            return False
        return self.context.hasSubscription(self.user)

    def owner_is_reviewer(self):
        """Is the branch owner the default reviewer?"""
        if self.context.reviewer == None:
            return True
        return self.context.owner == self.context.reviewer

    def show_whiteboard(self):
        """Return whether or not the whiteboard should be shown.

        The whiteboard is only shown for import branches.
        """
        if self.is_imported and self.context.whiteboard:
            return True
        else:
            return False

    def has_metadata(self):
        """Return whether there is branch metadata to display."""
        return (
            self.context.branch_format
            or self.context.repository_format
            or self.context.control_format
            or self.context.stacked_on
        )

    @property
    def is_empty_directory(self):
        """True if the branch is an empty directory without even a '.bzr'."""
        return self.context.control_format is None

    @property
    def pending_updates(self):
        """Whether or not there are pending updates for this branch."""
        return self.context.pending_updates

    def bzr_download_url(self):
        """Return the generic URL for downloading the branch."""
        if self.user_can_download():
            return self.context.bzr_identity
        else:
            return None

    def bzr_upload_url(self):
        """Return the generic URL for uploading the branch."""
        if self.user_can_upload():
            return self.context.bzr_identity
        else:
            return None

    @property
    def user_can_upload(self):
        """Whether the user can upload to this branch."""
        branch = self.context
        if branch.branch_type != BranchType.HOSTED:
            return False
        return check_permission("launchpad.Edit", branch)

    def user_can_download(self):
        """Whether the user can download this branch."""
        return (
            self.context.branch_type != BranchType.REMOTE
            and self.context.revision_count > 0
        )

    @cachedproperty
    def landing_targets(self):
        """Return a filtered list of landing targets."""
        targets = self.context.getPrecachedLandingTargets(self.user)
        return latest_proposals_for_each_branch(targets)

    @property
    def latest_landing_candidates(self):
        """Return a decorated filtered list of landing candidates."""
        # Only show the most recent 5 landing_candidates
        return self.landing_candidates[:5]

    @cachedproperty
    def landing_candidates(self):
        """Return a decorated list of landing candidates."""
        candidates = self.context.getPrecachedLandingCandidates(self.user)
        return [
            proposal
            for proposal in candidates
            if check_permission("launchpad.View", proposal)
        ]

    @property
    def recipes_link(self):
        """A link to recipes for this branch."""
        count = self.context.recipes.count()
        if count == 0:
            # Nothing to link to.
            return "No recipes using this branch."
        elif count == 1:
            # Link to the single recipe.
            return structured(
                '<a href="%s">1 recipe</a> using this branch.',
                canonical_url(self.context.recipes.one()),
            ).escapedtext
        else:
            # Link to a recipe listing.
            return structured(
                '<a href="+recipes">%s recipes</a> using this branch.', count
            ).escapedtext

    @property
    def is_imported(self):
        """Is this an imported branch?"""
        return self.context.branch_type == BranchType.IMPORTED

    @property
    def is_import_branch_with_no_landing_candidates(self):
        """Is the branch an import branch with no landing candidates?"""
        if self.landing_candidates:
            return False
        if not self.is_imported:
            return False
        return True

    def _getBranchCountText(self, count):
        """Help to show user friendly text."""
        if count == 0:
            return "No branches"
        elif count == 1:
            return "1 branch"
        else:
            return "%s branches" % count

    @cachedproperty
    def dependent_branch_count_text(self):
        branch_count = len(self.dependent_branches)
        return self._getBranchCountText(branch_count)

    @cachedproperty
    def landing_candidate_count_text(self):
        branch_count = len(self.landing_candidates)
        return self._getBranchCountText(branch_count)

    @cachedproperty
    def dependent_branches(self):
        return [
            branch
            for branch in self.context.dependent_branches
            if check_permission("launchpad.View", branch)
        ]

    @cachedproperty
    def no_merges(self):
        """Return true if there are no pending merges"""
        return (
            len(self.landing_targets)
            + len(self.landing_candidates)
            + len(self.dependent_branches)
            == 0
        )

    @property
    def show_rescan_link(self):
        """Only show the rescan button if the latest scan has failed"""
        scan_job = self.context.getLatestScanJob()
        # Having no jobs is a valid situation as there is a prune job.
        # We don't need to allow a rescan
        if not scan_job:
            return False
        return scan_job.job.status == JobStatus.FAILED

    @cachedproperty
    def linked_bugtasks(self):
        """Return a list of bugtasks linked to the branch."""
        if self.context.is_series_branch:
            status_filter = searchbuilder.any(*UNRESOLVED_BUGTASK_STATUSES)
        else:
            status_filter = None
        return list(self.context.getLinkedBugTasks(self.user, status_filter))

    @cachedproperty
    def revision_info(self):
        collection = getUtility(IAllBranches).visibleByUser(self.user)
        return collection.getExtendedRevisionDetails(
            self.user, self.context.latest_revisions
        )

    @property
    def show_merge_links(self):
        """Return whether or not merge proposal links should be shown.

        Merge proposal links should not be shown if there is only one branch
        in a non-final state.
        """
        if not self.context.target.supports_merge_proposals:
            return False
        return self.context.target.collection.getBranches().count() > 1

    def translations_sources(self):
        """Anything that automatically exports its translations here.

        Produces a list, so that the template can easily check whether
        there are any translations sources.
        """
        # Actually only ProductSeries currently do that.
        return list(self.context.getProductSeriesPushingTranslations())

    @property
    def status_widget(self):
        """The config to configure the ChoiceSource JS widget."""
        return EnumChoiceWidget(
            self.context.branch,
            IBranch["lifecycle_status"],
            header="Change status to",
            css_class_prefix="branchstatus",
        )

    @property
    def spec_links(self):
        return self.context.getSpecificationLinks(self.user)


class BranchRescanView(LaunchpadEditFormView):
    schema = Interface
    field_names = []
    next_url = None

    @action("Rescan", name="rescan")
    def rescan(self, action, data):
        self.context.unscan(rescan=True)
        self.request.response.addNotification("Branch scan scheduled")
        self.next_url = canonical_url(self.context)


class BranchEditFormView(LaunchpadEditFormView):
    """Base class for forms that edit a branch."""

    field_names = None

    def getInformationTypesToShow(self):
        """Get the information types to display on the edit form.

        We display a highly customised set of information types:
        anything allowed by the namespace, plus the current type,
        except some of the obscure types unless there's a linked
        bug with an obscure type.
        """
        allowed_types = self.context.getAllowedInformationTypes(self.user)

        # If we're stacked on a private branch, only show that
        # information type.
        if self.context.stacked_on and self.context.stacked_on.private:
            shown_types = {self.context.stacked_on.information_type}
        else:
            shown_types = (
                InformationType.PUBLIC,
                InformationType.PUBLICSECURITY,
                InformationType.PRIVATESECURITY,
                InformationType.USERDATA,
                InformationType.PROPRIETARY,
                InformationType.EMBARGOED,
            )

            # XXX Once Branch Visibility Policies are removed, we only want to
            # show Private (USERDATA) if the branch is linked to such a bug.
            hidden_types = (
                # InformationType.USERDATA,
            )
            if set(allowed_types).intersection(hidden_types):
                params = BugTaskSearchParams(
                    user=self.user,
                    linked_branches=self.context.id,
                    information_type=hidden_types,
                )
                if not getUtility(IBugTaskSet).searchBugIds(params).is_empty():
                    shown_types += hidden_types

        # Now take the intersection of the allowed and shown types.
        combined_types = set(allowed_types).intersection(shown_types)
        combined_types.add(self.context.information_type)
        return combined_types

    @cachedproperty
    def schema(self):
        info_types = self.getInformationTypesToShow()

        class BranchEditSchema(Interface):
            """Defines the fields for the edit form.

            This is necessary so as to make an editable field for the
            branch privacy.  Normally the field is not editable through
            the interface in order to stop direct setting of the private
            attribute, but in this case we actually want the user to be
            able to edit it.
            """

            use_template(
                IBranch,
                include=[
                    "name",
                    "url",
                    "description",
                    "lifecycle_status",
                    "whiteboard",
                ],
            )
            information_type = copy_field(
                IBranch["information_type"],
                readonly=False,
                vocabulary=InformationTypeVocabulary(types=info_types),
            )
            reviewer = copy_field(IBranch["reviewer"], required=True)
            owner = copy_field(IBranch["owner"], readonly=False)
            target = Reference(
                title=_("Branch target"),
                required=True,
                schema=IBranchTarget,
                description=_(
                    "The project (if any) this branch pertains to. "
                    "If no project is specified, then it is a personal "
                    "branch"
                ),
            )

        return BranchEditSchema

    @property
    def page_title(self):
        return "Edit %s" % self.context.displayname

    @property
    def label(self):
        return self.page_title

    @property
    def adapters(self):
        """See `LaunchpadFormView`"""
        return {self.schema: self.context}

    @action(
        "Change Branch",
        name="change",
        failure=LaunchpadFormView.ajax_failure_handler,
    )
    def change_action(self, action, data):
        # If the owner or product has changed, add an explicit notification.
        # We take our own snapshot here to make sure that the snapshot records
        # changes to the owner and private, and we notify the listeners
        # explicitly below rather than the notification that would normally be
        # sent in updateContextFromData.
        changed = False
        branch_before_modification = Snapshot(
            self.context, providing=providedBy(self.context)
        )
        if "owner" in data:
            new_owner = data.pop("owner")
            if new_owner != self.context.owner:
                self.context.setOwner(new_owner, self.user)
                changed = True
                self.request.response.addNotification(
                    "The branch owner has been changed to %s (%s)"
                    % (new_owner.displayname, new_owner.name)
                )
        if "private" in data:
            # Read only for display.
            data.pop("private")
        # We must process information type before target so that the any new
        # information type is valid for the target.
        if "information_type" in data:
            information_type = data.pop("information_type")
            self.context.transitionToInformationType(
                information_type, self.user
            )
        if "target" in data:
            target = data.pop("target")
            existing_junk = self.context.target.name == "+junk"
            same_junk_status = target == "+junk" and existing_junk
            if target == "+junk":
                target = None
            if not same_junk_status or (
                target is not None and target != self.context.target
            ):
                try:
                    self.context.setTarget(self.user, project=target)
                except BranchTargetError as e:
                    self.setFieldError("target", e.args[0])
                    return

                changed = True
                if target:
                    self.request.response.addNotification(
                        "The branch target has been changed to %s (%s)"
                        % (target.displayname, target.name)
                    )
                else:
                    self.request.response.addNotification(
                        "This branch is now a personal branch for %s (%s)"
                        % (
                            self.context.owner.displayname,
                            self.context.owner.name,
                        )
                    )
        if "reviewer" in data:
            reviewer = data.pop("reviewer")
            if reviewer != self.context.code_reviewer:
                if reviewer == self.context.owner:
                    # Clear the reviewer if set to the same as the owner.
                    self.context.reviewer = None
                else:
                    self.context.reviewer = reviewer
                changed = True

        if self.updateContextFromData(data, notify_modified=False):
            changed = True

        if changed:
            # Notify the object has changed with the snapshot that was taken
            # earlier.
            field_names = [
                form_field.__name__ for form_field in self.form_fields
            ]
            notify(
                ObjectModifiedEvent(
                    self.context, branch_before_modification, field_names
                )
            )
            # Only specify that the context was modified if there
            # was in fact a change.
            self.context.date_last_modified = UTC_NOW

        if self.request.is_ajax:
            return ""

    @property
    def next_url(self):
        """Return the next URL to call when this call completes."""
        if not self.request.is_ajax and not self.errors:
            return self.cancel_url
        return None

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class BranchEditWhiteboardView(BranchEditFormView):
    """A view for editing the whiteboard only."""

    field_names = ["whiteboard"]


class BranchEditStatusView(BranchEditFormView):
    """A view for editing the lifecycle status only."""

    field_names = ["lifecycle_status"]


class BranchEditInformationTypeView(BranchEditFormView):
    """A view for editing the information type only."""

    field_names = ["information_type"]


class BranchMirrorStatusView(LaunchpadFormView):
    """This view displays the mirror status of a branch.

    This includes the next mirror time and any failures that may have
    occurred.
    """

    MAXIMUM_STATUS_MESSAGE_LENGTH = 128

    schema = Interface

    field_names = []

    @property
    def show_detailed_error_message(self):
        """Show detailed error message for branch owner and experts."""
        if self.user is None:
            return False
        else:
            celebs = getUtility(ILaunchpadCelebrities)
            return self.user.inTeam(self.context.owner) or self.user.inTeam(
                celebs.admin
            )

    @property
    def mirror_of_ssh(self):
        """True if this a mirror branch with an sftp or bzr+ssh URL."""
        if not self.context.url:
            return False  # not a mirror branch
        uri = URI(self.context.url)
        return uri.scheme in ("sftp", "bzr+ssh")

    @property
    def in_mirror_queue(self):
        """Is it likely that the branch is being mirrored in the next run of
        the puller?
        """
        return self.context.next_mirror_time < datetime.now(timezone.utc)

    @property
    def mirror_disabled(self):
        """Has mirroring this branch been disabled?"""
        return self.context.next_mirror_time is None

    @property
    def mirror_failed_once(self):
        """Has there been exactly one failed attempt to mirror this branch?"""
        return self.context.mirror_failures == 1

    @property
    def mirror_status_message(self):
        """A message from a bad scan or pull, truncated for display."""
        message = self.context.mirror_status_message
        if len(message) <= self.MAXIMUM_STATUS_MESSAGE_LENGTH:
            return message
        return (
            truncate_text(message, self.MAXIMUM_STATUS_MESSAGE_LENGTH) + " ..."
        )

    @property
    def show_mirror_failure(self):
        """True if mirror_of_ssh is false and branch mirroring failed."""
        return not self.mirror_of_ssh and self.context.mirror_failures

    @property
    def action_url(self):
        return "%s/+mirror-status" % canonical_url(self.context)

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action("Try again", name="try-again")
    def retry(self, action, data):
        self.context.requestMirror()


class BranchDeletionView(LaunchpadFormView):
    """Used to delete a branch."""

    schema = IBranch
    field_names = []
    next_url = None

    @property
    def page_title(self):
        return "Delete branch %s" % self.context.displayname

    label = page_title

    @cachedproperty
    def display_deletion_requirements(self):
        """Normal deletion requirements, indication of permissions.

        :return: A list of tuples of (item, operation, reason, allowed)
        """
        reqs = []
        for item, (operation, reason) in self.context.deletionRequirements(
            eager_load=True
        ).items():
            allowed = check_permission("launchpad.Edit", item)
            reqs.append((item, operation, reason, allowed))
        return reqs

    @cachedproperty
    def stacked_branches_count(self):
        """Cache a count of the branches stacked on this."""
        return self.context.getStackedBranches().count()

    def stacked_branches_text(self):
        """Cache a count of the branches stacked on this."""
        if self.stacked_branches_count == 1:
            return _("branch")
        else:
            return _("branches")

    def all_permitted(self):
        """Return True if all deletion requirements are permitted, else False.

        Uses display_deletion_requirements as its source data.
        """
        # Not permitted if there are any branches stacked on this.
        if self.stacked_branches_count > 0:
            return False
        return (
            len(
                [
                    item
                    for item, action, reason, allowed in (
                        self.display_deletion_requirements
                    )
                    if not allowed
                ]
            )
            == 0
        )

    @action(
        "Delete",
        name="delete_branch",
        condition=lambda x, y: x.all_permitted(),
    )
    def delete_branch_action(self, action, data):
        branch = self.context
        if self.all_permitted():
            # Since the user is going to delete the branch, we need to have
            # somewhere valid to send them next.
            self.next_url = canonical_url(branch.target)
            message = "Branch %s deleted." % branch.unique_name
            self.context.destroySelf(break_references=True)
            self.request.response.addNotification(message)
        else:
            self.request.response.addNotification(
                "This branch cannot be deleted."
            )
            self.next_url = canonical_url(branch)

    @property
    def branch_deletion_actions(self):
        """Return the branch deletion actions as a zpt-friendly dict.

        The keys are 'delete' and 'alter'; the values are dicts of
        'item', 'reason' and 'allowed'.
        """
        row_dict = {"delete": [], "alter": [], "break_link": []}
        for (
            item,
            operation,
            reason,
            allowed,
        ) in self.display_deletion_requirements:
            if IBugBranch.providedBy(item):
                operation = "break_link"
            elif ISpecificationBranch.providedBy(item):
                operation = "break_link"
            elif IProductSeries.providedBy(item):
                operation = "break_link"
            row = {
                "item": item,
                "reason": reason,
                "allowed": allowed,
            }
            row_dict[operation].append(row)
        return row_dict

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class BranchUpgradeView(LaunchpadFormView):
    """Used to upgrade a branch."""

    schema = IBranch
    field_names = []

    @property
    def page_title(self):
        return "Upgrade branch %s" % self.context.displayname

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url

    @action("Upgrade", name="upgrade_branch")
    def upgrade_branch_action(self, action, data):
        try:
            self.context.requestUpgrade(self.user)
        except CannotUpgradeBranch as e:
            self.request.response.addErrorNotification(e)


class CodeEditOwnerMixin:
    """A mixin to adjust owner vocabularies for admins."""

    def setUpFields(self):
        super().setUpFields()
        # If the user can administer the relevant object type, then they
        # should be able to assign the ownership of the object to any valid
        # person or team.
        if check_permission("launchpad.Admin", self.context):
            owner_field = self.schema["owner"]
            any_owner_choice = Choice(
                __name__="owner",
                title=owner_field.title,
                description=self.any_owner_description,
                required=True,
                vocabulary="ValidPersonOrTeam",
            )
            any_owner_field = form.Fields(
                any_owner_choice, render_context=self.render_context
            )
            # Replace the normal owner field with a more permissive vocab.
            self.form_fields = self.form_fields.omit("owner")
            self.form_fields = any_owner_field + self.form_fields
        else:
            # For normal users, there is an edge case with package branches
            # where the editor may not be in the team of the branch owner.  In
            # these cases we need to extend the vocabulary connected to the
            # owner field.
            if not self.user.inTeam(self.context.owner):
                vocab = UserTeamsParticipationPlusSelfVocabulary()
                owner = self.context.owner
                terms = [
                    SimpleTerm(owner, owner.name, owner.unique_displayname)
                ]
                terms.extend([term for term in vocab])
                owner_field = self.schema["owner"]
                owner_choice = Choice(
                    __name__="owner",
                    title=owner_field.title,
                    description=owner_field.description,
                    required=True,
                    vocabulary=SimpleVocabulary(terms),
                )
                new_owner_field = form.Fields(
                    owner_choice, render_context=self.render_context
                )
                # Replace the normal owner field with a more permissive vocab.
                self.form_fields = self.form_fields.omit("owner")
                self.form_fields = new_owner_field + self.form_fields


class BranchEditView(CodeEditOwnerMixin, BranchEditFormView):
    """The main branch for editing the branch attributes."""

    @property
    def field_names(self):
        field_names = ["owner", "name"]
        if not self.context.sourcepackagename:
            field_names.append("target")
        field_names.extend(
            ["information_type", "url", "description", "lifecycle_status"]
        )
        return field_names

    custom_widget_target = BranchTargetWidget
    custom_widget_lifecycle_status = LaunchpadRadioWidgetWithDescription
    custom_widget_information_type = LaunchpadRadioWidgetWithDescription

    any_owner_description = _(
        "As an administrator you are able to assign this branch to any "
        "person or team."
    )

    def setUpFields(self):
        super().setUpFields()
        branch = self.context
        if branch.branch_type in (BranchType.HOSTED, BranchType.IMPORTED):
            self.form_fields = self.form_fields.omit("url")

    def _setBranchExists(self, existing_branch, field_name="name"):
        owner = existing_branch.owner
        if owner == self.user:
            prefix = "You already have"
        else:
            prefix = "%s already has" % owner.displayname
        message = structured(
            "%s a branch for <em>%s</em> called <em>%s</em>.",
            prefix,
            existing_branch.target.displayname,
            existing_branch.name,
        )
        self.setFieldError(field_name, message)

    def validate(self, data):
        # Check that we're not moving a team branch to the +junk
        # pseudo project.
        if "name" in data:
            # Only validate if the name has changed or the owner has changed.
            owner = data["owner"]
            if (data["name"] != self.context.name) or (
                owner != self.context.owner
            ):
                # We only allow moving within the same branch target for now.
                namespace = self.context.target.getNamespace(owner)
                try:
                    namespace.validateMove(
                        self.context, self.user, name=data["name"]
                    )
                except BranchCreationForbidden:
                    self.addError(
                        "%s is not allowed to own branches in %s."
                        % (owner.displayname, self.context.target.displayname)
                    )
                except BranchExists as e:
                    self._setBranchExists(e.existing_branch)

        # If the branch is a MIRRORED branch, then the url
        # must be supplied, and if HOSTED the url must *not*
        # be supplied.
        url = data.get("url")
        if self.context.branch_type == BranchType.MIRRORED:
            if url is None:
                # If the url is not set due to url validation errors,
                # there will be an error set for it.
                error = self.getFieldError("url")
                if not error:
                    self.setFieldError(
                        "url",
                        "Branch URLs are required for Mirrored branches.",
                    )
        else:
            # We don't care about whether the URL is set for REMOTE branches,
            # and the URL field is not shown for IMPORT or HOSTED branches.
            pass


class BranchReviewerEditView(BranchEditFormView):
    """The view to set the review team."""

    field_names = ["reviewer"]

    @property
    def initial_values(self):
        return {"reviewer": self.context.code_reviewer}


class RegisterProposalSchema(Interface):
    """The schema to define the form for registering a new merge proposal."""

    target_branch = Choice(
        title=_("Target branch"),
        vocabulary="Branch",
        required=True,
        readonly=True,
        description=_(
            "The branch that the source branch will be merged into."
        ),
    )

    prerequisite_branch = Choice(
        title=_("Prerequisite branch"),
        vocabulary="Branch",
        required=False,
        readonly=False,
        description=_(
            "A branch that should be merged before this one.  (Its changes"
            " will not be shown in the diff.)"
        ),
    )

    comment = Text(
        title=_("Description of the change"),
        required=False,
        description=_(
            "Describe what changes your branch introduces, "
            "what bugs it fixes, or what features it implements. "
            "Ideally include rationale and how to test. "
            "You do not need to repeat information from the commit "
            "message here."
        ),
    )

    reviewer = copy_field(ICodeReviewVoteReference["reviewer"], required=False)

    review_type = copy_field(
        ICodeReviewVoteReference["review_type"],
        description="Lowercase keywords describing the type of review you "
        "would like to be performed.",
    )

    commit_message = IBranchMergeProposal["commit_message"]

    needs_review = Bool(
        title=_("Needs review"),
        required=True,
        default=True,
        description=_("Is the proposal ready for review now?"),
    )


class RegisterBranchMergeProposalView(LaunchpadFormView):
    """The view to register new branch merge proposals."""

    schema = RegisterProposalSchema
    next_url = None
    for_input = True

    custom_widget_target_branch = TargetBranchWidget
    custom_widget_commit_message = CustomWidgetFactory(
        TextAreaWidget, cssClass="comment-text"
    )
    custom_widget_comment = CustomWidgetFactory(
        TextAreaWidget, cssClass="comment-text"
    )

    page_title = label = "Propose branch for merging"

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    def initialize(self):
        """Show a 404 if the branch target doesn't support proposals."""
        if not self.context.target.supports_merge_proposals:
            raise NotFound(self.context, "+register-merge")
        LaunchpadFormView.initialize(self)

    @action(
        "Propose Merge",
        name="register",
        failure=LaunchpadFormView.ajax_failure_handler,
    )
    def register_action(self, action, data):
        """Register the new branch merge proposal."""

        registrant = self.user
        source_branch = self.context
        target_branch = data["target_branch"]
        prerequisite_branch = data.get("prerequisite_branch")

        review_requests = []
        reviewer = data.get("reviewer")
        review_type = data.get("review_type")
        if reviewer is None:
            reviewer = target_branch.code_reviewer
        if reviewer is not None:
            review_requests.append((reviewer, review_type))

        branch_names = [
            branch.unique_name for branch in [source_branch, target_branch]
        ]
        visibility_info = getUtility(IBranchSet).getBranchVisibilityInfo(
            self.user, reviewer, branch_names
        )
        visible_branches = list(visibility_info["visible_branches"])
        if self.request.is_ajax and len(visible_branches) < 2:
            self.request.response.setStatus(400, "Branch Visibility")
            self.request.response.setHeader("Content-Type", "application/json")
            return json.dumps(
                {
                    "person_name": visibility_info["person_name"],
                    "branches_to_check": branch_names,
                    "visible_branches": visible_branches,
                }
            )

        try:
            proposal = source_branch.addLandingTarget(
                registrant=registrant,
                merge_target=target_branch,
                merge_prerequisite=prerequisite_branch,
                needs_review=data["needs_review"],
                description=data.get("comment"),
                review_requests=review_requests,
                commit_message=data.get("commit_message"),
            )
            if len(visible_branches) < 2:
                invisible_branches = [
                    branch.unique_name
                    for branch in [source_branch, target_branch]
                    if branch.unique_name not in visible_branches
                ]
                self.request.response.addNotification(
                    "To ensure visibility, %s is now subscribed to: %s"
                    % (
                        visibility_info["person_name"],
                        english_list(invisible_branches),
                    )
                )
            # Success so we do a client redirect to the new mp page.
            if self.request.is_ajax:
                self.request.response.setStatus(201)
                self.request.response.setHeader(
                    "Location", canonical_url(proposal)
                )
                return None
            else:
                self.next_url = canonical_url(proposal)
        except InvalidBranchMergeProposal as error:
            self.addError(str(error))

    def validate(self, data):
        source_branch = self.context
        target_branch = data.get("target_branch")

        # Make sure that the target branch is different from the context.
        if target_branch is None:
            # Skip the following tests.
            # The existence of the target_branch is handled by the form
            # machinery.
            pass
        elif source_branch == target_branch:
            self.setFieldError(
                "target_branch",
                "The target branch cannot be the same as the source branch.",
            )
        else:
            # Make sure that the target_branch is in the same project.
            if not target_branch.isBranchMergeable(source_branch):
                self.setFieldError(
                    "target_branch",
                    "This branch is not mergeable into %s."
                    % target_branch.bzr_identity,
                )


@implementer(IBrowserPublisher)
class BranchDiffView(DataDownloadView):
    content_type = "text/x-patch"

    def __init__(self, context, request, new, old=None):
        super().__init__(context, request)
        self.new = new
        self.old = old

    def __call__(self):
        if getFeatureFlag("code.bzr.diff.disable_proxy"):
            self.request.response.setStatus(401)
            return "Proxying of branch diffs is disabled.\n"
        return super().__call__()

    @property
    def filename(self):
        if self.old is None:
            return "%s_%s.diff" % (self.context.name, self.new)
        else:
            return "%s_%s_%s.diff" % (self.context.name, self.old, self.new)

    def getBody(self):
        return self.context.getDiff(self.new, old=self.old)

    def browserDefault(self, request):
        return self, ()
