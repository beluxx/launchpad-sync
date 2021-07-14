# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Charm recipe views."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "CharmRecipeAddView",
    "CharmRecipeAdminView",
    "CharmRecipeContextMenu",
    "CharmRecipeDeleteView",
    "CharmRecipeEditView",
    "CharmRecipeNavigation",
    "CharmRecipeNavigationMenu",
    "CharmRecipeRequestBuildsView",
    "CharmRecipeURL",
    "CharmRecipeView",
    ]

from lazr.restful.interface import (
    copy_field,
    use_template,
    )
from zope.component import getUtility
from zope.interface import (
    implementer,
    Interface,
    )
from zope.schema import (
    Dict,
    TextLine,
    )
from zope.security.interfaces import Unauthorized

from lp import _
from lp.app.browser.launchpadform import (
    action,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.app.browser.lazrjs import InlinePersonEditPickerWidget
from lp.app.browser.tales import format_link
from lp.charms.browser.widgets.charmrecipebuildchannels import (
    CharmRecipeBuildChannelsWidget,
    )
from lp.charms.interfaces.charmrecipe import (
    ICharmRecipe,
    ICharmRecipeSet,
    NoSuchCharmRecipe,
    )
from lp.charms.interfaces.charmrecipebuild import ICharmRecipeBuildSet
from lp.code.browser.widgets.gitref import GitRefWidget
from lp.code.interfaces.gitref import IGitRef
from lp.registry.interfaces.personproduct import IPersonProductFactory
from lp.registry.interfaces.product import IProduct
from lp.services.propertycache import cachedproperty
from lp.services.utils import seconds_since_epoch
from lp.services.webapp import (
    canonical_url,
    ContextMenu,
    enabled_with_permission,
    LaunchpadView,
    Link,
    Navigation,
    NavigationMenu,
    stepthrough,
    )
from lp.services.webapp.breadcrumb import (
    Breadcrumb,
    NameBreadcrumb,
    )
from lp.services.webapp.interfaces import ICanonicalUrlData
from lp.snappy.browser.widgets.storechannels import StoreChannelsWidget
from lp.soyuz.browser.build import get_build_by_id_str


@implementer(ICanonicalUrlData)
class CharmRecipeURL:
    """Charm recipe URL creation rules."""
    rootsite = "mainsite"

    def __init__(self, recipe):
        self.recipe = recipe

    @property
    def inside(self):
        owner = self.recipe.owner
        project = self.recipe.project
        return getUtility(IPersonProductFactory).create(owner, project)

    @property
    def path(self):
        return "+charm/%s" % self.recipe.name


class CharmRecipeNavigation(Navigation):
    usedfor = ICharmRecipe

    @stepthrough("+build-request")
    def traverse_build_request(self, name):
        try:
            job_id = int(name)
        except ValueError:
            return None
        return self.context.getBuildRequest(job_id)

    @stepthrough("+build")
    def traverse_build(self, name):
        build = get_build_by_id_str(ICharmRecipeBuildSet, name)
        if build is None or build.recipe != self.context:
            return None
        return build


class CharmRecipeBreadcrumb(NameBreadcrumb):

    @property
    def inside(self):
        # XXX cjwatson 2021-06-04: This should probably link to an
        # appropriate listing view, but we don't have one of those yet.
        return Breadcrumb(
            self.context.project, text=self.context.project.display_name,
            inside=self.context.project)


class CharmRecipeNavigationMenu(NavigationMenu):
    """Navigation menu for charm recipes."""

    usedfor = ICharmRecipe

    facet = "overview"

    links = ("admin", "edit", "delete")

    @enabled_with_permission("launchpad.Admin")
    def admin(self):
        return Link("+admin", "Administer charm recipe", icon="edit")

    @enabled_with_permission("launchpad.Edit")
    def edit(self):
        return Link("+edit", "Edit charm recipe", icon="edit")

    @enabled_with_permission("launchpad.Edit")
    def delete(self):
        return Link("+delete", "Delete charm recipe", icon="trash-icon")


class CharmRecipeContextMenu(ContextMenu):
    """Context menu for charm recipes."""

    usedfor = ICharmRecipe

    facet = "overview"

    links = ("request_builds",)

    @enabled_with_permission("launchpad.Edit")
    def request_builds(self):
        return Link("+request-builds", "Request builds", icon="add")


class CharmRecipeView(LaunchpadView):
    """Default view of a charm recipe."""

    @cachedproperty
    def builds_and_requests(self):
        return builds_and_requests_for_recipe(self.context)

    @property
    def person_picker(self):
        field = copy_field(
            ICharmRecipe["owner"],
            vocabularyName="AllUserTeamsParticipationPlusSelfSimpleDisplay")
        return InlinePersonEditPickerWidget(
            self.context, field, format_link(self.context.owner),
            header="Change owner", step_title="Select a new owner")

    @property
    def build_frequency(self):
        if self.context.auto_build:
            return "Built automatically"
        else:
            return "Built on request"

    @property
    def sorted_auto_build_channels_items(self):
        if self.context.auto_build_channels is None:
            return []
        return sorted(self.context.auto_build_channels.items())

    @property
    def store_channels(self):
        return ", ".join(self.context.store_channels)

    @property
    def user_can_see_source(self):
        try:
            return self.context.source.visibleByUser(self.user)
        except Unauthorized:
            return False


def builds_and_requests_for_recipe(recipe):
    """A list of interesting builds and build requests.

    All pending builds and pending build requests are shown, as well as up
    to 10 recent builds and recent failed build requests.  Pending items are
    ordered by the date they were created; recent items are ordered by the
    date they finished (if available) or the date they started (if the date
    they finished is not set due to an error).  This allows started but
    unfinished builds to show up in the view but be discarded as more recent
    builds become available.

    Builds that the user does not have permission to see are excluded (by
    the model code).
    """
    # We need to interleave items of different types, so SQL can't do all
    # the sorting for us.
    def make_sort_key(*date_attrs):
        def _sort_key(item):
            for date_attr in date_attrs:
                if getattr(item, date_attr, None) is not None:
                    return -seconds_since_epoch(getattr(item, date_attr))
            return 0

        return _sort_key

    items = sorted(
        list(recipe.pending_builds) + list(recipe.pending_build_requests),
        key=make_sort_key("date_created", "date_requested"))
    if len(items) < 10:
        # We need to interleave two unbounded result sets, but we only need
        # enough items from them to make the total count up to 10.  It's
        # simplest to just fetch the upper bound from each set and do our
        # own sorting.
        recent_items = sorted(
            list(recipe.completed_builds[:10 - len(items)]) +
            list(recipe.failed_build_requests[:10 - len(items)]),
            key=make_sort_key(
                "date_finished", "date_started",
                "date_created", "date_requested"))
        items.extend(recent_items[:10 - len(items)])
    return items


class ICharmRecipeEditSchema(Interface):
    """Schema for adding or editing a charm recipe."""

    use_template(ICharmRecipe, include=[
        "owner",
        "name",
        "project",
        "require_virtualized",
        "auto_build",
        "auto_build_channels",
        "store_upload",
        ])

    git_ref = copy_field(ICharmRecipe["git_ref"], required=True)

    # This is only required if store_upload is True.  Later validation takes
    # care of adjusting the required attribute.
    store_name = copy_field(ICharmRecipe["store_name"], required=True)
    store_channels = copy_field(ICharmRecipe["store_channels"], required=True)


class CharmRecipeAddView(LaunchpadFormView):
    """View for creating charm recipes."""

    page_title = label = "Create a new charm recipe"

    schema = ICharmRecipeEditSchema

    custom_widget_git_ref = GitRefWidget
    custom_widget_auto_build_channels = CharmRecipeBuildChannelsWidget
    custom_widget_store_channels = StoreChannelsWidget

    @property
    def field_names(self):
        fields = ["owner", "name"]
        if self.is_project_context:
            fields += ["git_ref"]
        else:
            fields += ["project"]
        return fields + [
            "auto_build",
            "auto_build_channels",
            "store_upload",
            "store_name",
            "store_channels",
            ]

    @property
    def is_project_context(self):
        return IProduct.providedBy(self.context)

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def initial_values(self):
        initial_values = {"owner": self.user}
        if (IGitRef.providedBy(self.context) and
                IProduct.providedBy(self.context.target)):
            initial_values["project"] = self.context.target
        return initial_values

    def validate_widgets(self, data, names=None):
        """See `LaunchpadFormView`."""
        if self.widgets.get("store_upload") is not None:
            # Set widgets as required or optional depending on the
            # store_upload field.
            super(CharmRecipeAddView, self).validate_widgets(
                data, ["store_upload"])
            store_upload = data.get("store_upload", False)
            self.widgets["store_name"].context.required = store_upload
            self.widgets["store_channels"].context.required = store_upload
        super(CharmRecipeAddView, self).validate_widgets(data, names=names)

    @action("Create charm recipe", name="create")
    def create_action(self, action, data):
        if IGitRef.providedBy(self.context):
            project = data["project"]
            git_ref = self.context
        elif self.is_project_context:
            project = self.context
            git_ref = data["git_ref"]
        else:
            raise NotImplementedError(
                "Unknown context for charm recipe creation.")
        recipe = getUtility(ICharmRecipeSet).new(
            self.user, data["owner"], project, data["name"], git_ref=git_ref,
            auto_build=data["auto_build"],
            auto_build_channels=data["auto_build_channels"],
            store_upload=data["store_upload"],
            store_name=data["store_name"],
            store_channels=data.get("store_channels"))
        self.next_url = canonical_url(recipe)

    def validate(self, data):
        super(CharmRecipeAddView, self).validate(data)
        owner = data.get("owner", None)
        if self.is_project_context:
            project = self.context
        else:
            project = data.get("project", None)
        name = data.get("name", None)
        if owner and project and name:
            if getUtility(ICharmRecipeSet).exists(owner, project, name):
                self.setFieldError(
                    "name",
                    "There is already a charm recipe owned by %s in %s with "
                    "this name." % (owner.display_name, project.display_name))


class BaseCharmRecipeEditView(LaunchpadEditFormView):

    schema = ICharmRecipeEditSchema

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    def validate_widgets(self, data, names=None):
        """See `LaunchpadFormView`."""
        if self.widgets.get("store_upload") is not None:
            # Set widgets as required or optional depending on the
            # store_upload field.
            super(BaseCharmRecipeEditView, self).validate_widgets(
                data, ["store_upload"])
            store_upload = data.get("store_upload", False)
            self.widgets["store_name"].context.required = store_upload
            self.widgets["store_channels"].context.required = store_upload
        super(BaseCharmRecipeEditView, self).validate_widgets(
            data, names=names)

    def validate(self, data):
        super(BaseCharmRecipeEditView, self).validate(data)
        # These are the requirements for public snaps.
        if "owner" in data:
            owner = data.get("owner", self.context.owner)
            if owner is not None and owner.private:
                self.setFieldError(
                    "owner",
                    "A public charm recipe cannot have a private owner.")
        if "git_ref" in data:
            ref = data.get("git_ref", self.context.git_ref)
            if ref is not None and ref.private:
                self.setFieldError(
                    "git_ref",
                    "A public charm recipe cannot have a private repository.")

    @action("Update charm recipe", name="update")
    def request_action(self, action, data):
        if not data.get("auto_build", False):
            if "auto_build_channels" in data:
                del data["auto_build_channels"]
        store_upload = data.get("store_upload", False)
        if not store_upload:
            if "store_name" in data:
                del data["store_name"]
            if "store_channels" in data:
                del data["store_channels"]
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)

    @property
    def adapters(self):
        """See `LaunchpadFormView`."""
        return {ICharmRecipeEditSchema: self.context}


class CharmRecipeAdminView(BaseCharmRecipeEditView):
    """View for administering charm recipes."""

    @property
    def label(self):
        return "Administer %s charm recipe" % self.context.name

    page_title = "Administer"

    field_names = ["require_virtualized"]


class CharmRecipeEditView(BaseCharmRecipeEditView):
    """View for editing charm recipes."""

    @property
    def label(self):
        return "Edit %s charm recipe" % self.context.name

    page_title = "Edit"

    field_names = [
        "owner",
        "name",
        "project",
        "git_ref",
        "auto_build",
        "auto_build_channels",
        "store_upload",
        "store_name",
        "store_channels",
        ]
    custom_widget_git_ref = GitRefWidget
    custom_widget_auto_build_channels = CharmRecipeBuildChannelsWidget
    custom_widget_store_channels = StoreChannelsWidget

    def validate(self, data):
        super(CharmRecipeEditView, self).validate(data)
        owner = data.get("owner", None)
        project = data.get("project", None)
        name = data.get("name", None)
        if owner and project and name:
            try:
                recipe = getUtility(ICharmRecipeSet).getByName(
                    owner, project, name)
                if recipe != self.context:
                    self.setFieldError(
                        "name",
                        "There is already a charm recipe owned by %s in %s "
                        "with this name." %
                        (owner.display_name, project.display_name))
            except NoSuchCharmRecipe:
                pass


class CharmRecipeDeleteView(BaseCharmRecipeEditView):
    """View for deleting charm recipes."""

    @property
    def label(self):
        return "Delete %s charm recipe" % self.context.name

    page_title = "Delete"

    field_names = []

    @action("Delete charm recipe", name="delete")
    def delete_action(self, action, data):
        owner = self.context.owner
        self.context.destroySelf()
        self.next_url = canonical_url(owner, view_name="+charm-recipes")


class CharmRecipeRequestBuildsView(LaunchpadFormView):
    """A view for requesting builds of a charm recipe."""

    @property
    def label(self):
        return "Request builds for %s" % self.context.name

    page_title = "Request builds"

    class schema(Interface):
        """Schema for requesting a build."""

        channels = Dict(
            title="Source snap channels", key_type=TextLine(), required=True,
            description=ICharmRecipe["auto_build_channels"].description)

    custom_widget_channels = CharmRecipeBuildChannelsWidget

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def initial_values(self):
        """See `LaunchpadFormView`."""
        return {
            "channels": self.context.auto_build_channels,
            }

    @action("Request builds", name="request")
    def request_action(self, action, data):
        self.context.requestBuilds(self.user, channels=data["channels"])
        self.request.response.addNotification(
            _("Builds will be dispatched soon."))
        self.next_url = self.cancel_url
