# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SourcePackageRecipe views."""

__all__ = [
    "SourcePackageRecipeAddView",
    "SourcePackageRecipeContextMenu",
    "SourcePackageRecipeEditView",
    "SourcePackageRecipeNavigationMenu",
    "SourcePackageRecipeRequestBuildsView",
    "SourcePackageRecipeRequestDailyBuildView",
    "SourcePackageRecipeView",
]

import itertools
import json

from brzbuildrecipe.recipe import ForbiddenInstructionError, RecipeParseError
from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from lazr.restful.interface import copy_field, use_template
from lazr.restful.interfaces import (
    IFieldHTMLRenderer,
    IWebServiceClientRequest,
)
from storm.locals import Store
from zope import component
from zope.browserpage import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.formlib.widget import Widget
from zope.interface import Interface, implementer, providedBy
from zope.publisher.interfaces import IView
from zope.schema import Choice, Field, List, Text, TextLine
from zope.schema.interfaces import ICollection
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from lp import _
from lp.app.browser.launchpadform import (
    LaunchpadEditFormView,
    LaunchpadFormView,
    action,
    has_structured_doc,
    render_radio_widget_part,
)
from lp.app.browser.lazrjs import (
    BooleanChoiceWidget,
    InlineEditPickerWidget,
    InlinePersonEditPickerWidget,
    TextAreaEditorWidget,
    TextLineEditorWidget,
)
from lp.app.browser.tales import format_link
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.validators.name import name_validator
from lp.app.widgets.itemswidgets import (
    LabeledMultiCheckBoxWidget,
    LaunchpadRadioWidget,
)
from lp.app.widgets.suggestion import RecipeOwnerWidget
from lp.code.errors import (
    BuildAlreadyPending,
    NoSuchBranch,
    NoSuchGitRepository,
    PrivateBranchRecipe,
    PrivateGitRepositoryRecipe,
    TooNewRecipeFormat,
)
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.code.interfaces.gitref import IGitRef
from lp.code.interfaces.gitrepository import IGitRepository
from lp.code.interfaces.sourcepackagerecipe import (
    MINIMAL_RECIPE_TEXT_BZR,
    MINIMAL_RECIPE_TEXT_GIT,
    IRecipeBranchSource,
    ISourcePackageRecipe,
    ISourcePackageRecipeSource,
)
from lp.code.vocabularies.sourcepackagerecipe import BuildableDistroSeries
from lp.registry.interfaces.series import SeriesStatus
from lp.services.fields import PersonChoice
from lp.services.propertycache import cachedproperty
from lp.services.webapp import (
    ContextMenu,
    LaunchpadView,
    Link,
    NavigationMenu,
    canonical_url,
    enabled_with_permission,
    structured,
)
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.breadcrumb import Breadcrumb, NameBreadcrumb
from lp.soyuz.interfaces.archive import ArchiveDisabled
from lp.soyuz.model.archive import validate_ppa


class SourcePackageRecipeBreadcrumb(NameBreadcrumb):
    @property
    def inside(self):
        return Breadcrumb(
            self.context.owner,
            url=canonical_url(
                self.context.owner, view_name="+recipes", rootsite="code"
            ),
            text="Recipes",
            inside=self.context.owner,
        )


class SourcePackageRecipeNavigationMenu(NavigationMenu):
    """Navigation menu for sourcepackage recipes."""

    usedfor = ISourcePackageRecipe

    facet = "branches"

    links = ("edit", "delete")

    @enabled_with_permission("launchpad.Edit")
    def edit(self):
        return Link("+edit", "Edit recipe", icon="edit")

    @enabled_with_permission("launchpad.Delete")
    def delete(self):
        return Link("+delete", "Delete recipe", icon="trash-icon")


class SourcePackageRecipeContextMenu(ContextMenu):
    """Context menu for sourcepackage recipes."""

    usedfor = ISourcePackageRecipe

    facet = "branches"

    links = (
        "request_builds",
        "request_daily_build",
    )

    def request_builds(self):
        """Provide a link for requesting builds of a recipe."""
        return Link("+request-builds", "Request build(s)", icon="add")

    def request_daily_build(self):
        """Provide a link for requesting a daily build of a recipe."""
        recipe = self.context
        ppa = recipe.daily_build_archive
        if (
            ppa is None
            or not ppa.enabled
            or not recipe.build_daily
            or not recipe.is_stale
            or not recipe.distroseries
        ):
            show_request_build = False
        else:
            has_upload = ppa.checkArchivePermission(recipe.owner)
            show_request_build = has_upload

        show_request_build = show_request_build and check_permission(
            "launchpad.Edit", recipe
        )
        return Link(
            "+request-daily-build", "Build now", enabled=show_request_build
        )


class SourcePackageRecipeView(LaunchpadView):
    """Default view of a SourcePackageRecipe."""

    def initialize(self):
        super().initialize()
        recipe = self.context
        if recipe.build_daily and recipe.daily_build_archive is None:
            self.request.response.addWarningNotification(
                structured(
                    "Daily builds for this recipe will <strong>not</strong> "
                    "occur.<br/><br/>There is no PPA."
                )
            )
        elif self.dailyBuildWithoutUploadPermission():
            self.request.response.addWarningNotification(
                structured(
                    "Daily builds for this recipe will <strong>not</strong> "
                    "occur.<br/><br/>The owner of the recipe (%s) does not "
                    "have permission to upload packages into the daily "
                    "build PPA (%s)"
                    % (
                        format_link(recipe.owner),
                        format_link(recipe.daily_build_archive),
                    )
                )
            )

    @property
    def page_title(self):
        return "%(name)s's %(recipe_name)s recipe" % {
            "name": self.context.owner.displayname,
            "recipe_name": self.context.name,
        }

    label = page_title

    @property
    def builds(self):
        return builds_for_recipe(self.context)

    def dailyBuildWithoutUploadPermission(self):
        """Returns true if there are upload permissions to the daily archive.

        If the recipe isn't built daily, we don't consider this a problem.
        """
        recipe = self.context
        ppa = recipe.daily_build_archive
        if recipe.build_daily:
            has_upload = ppa.checkArchivePermission(recipe.owner)
            return not has_upload
        return False

    @property
    def person_picker(self):
        field = copy_field(
            ISourcePackageRecipe["owner"],
            vocabularyName="UserTeamsParticipationPlusSelfSimpleDisplay",
        )
        return InlinePersonEditPickerWidget(
            self.context,
            field,
            format_link(self.context.owner),
            header="Change owner",
            step_title="Select a new owner",
        )

    @property
    def archive_picker(self):
        field = ISourcePackageEditSchema["daily_build_archive"]
        return InlineEditPickerWidget(
            self.context,
            field,
            format_link(self.context.daily_build_archive),
            header="Change daily build archive",
            step_title="Select a PPA",
        )

    @property
    def recipe_text_widget(self):
        """The recipe text as widget HTML."""
        recipe_text = ISourcePackageRecipe["recipe_text"]
        return TextAreaEditorWidget(self.context, recipe_text, title="")

    @property
    def daily_build_widget(self):
        return BooleanChoiceWidget(
            self.context,
            ISourcePackageRecipe["build_daily"],
            tag="span",
            false_text="Built on request",
            true_text="Built daily",
            header="Change build schedule",
        )

    @property
    def description_widget(self):
        """The description as a widget."""
        description = ISourcePackageRecipe["description"]
        return TextAreaEditorWidget(self.context, description, title="")

    @property
    def name_widget(self):
        name = ISourcePackageRecipe["name"]
        title = "Edit the recipe name"
        return TextLineEditorWidget(
            self.context, name, title, "h1", max_width="95%", truncate_lines=1
        )

    @property
    def distroseries_widget(self):
        from lp.app.browser.lazrjs import InlineMultiCheckboxWidget

        field = ISourcePackageEditSchema["distroseries"]
        return InlineMultiCheckboxWidget(
            self.context,
            field,
            attribute_type="reference",
            vocabulary="BuildableDistroSeries",
            label="Distribution series:",
            label_tag="dt",
            header="Change default distribution series:",
            empty_display_value="None",
            selected_items=sorted(
                self.context.distroseries, key=lambda ds: ds.displayname
            ),
            items_tag="dd",
        )


@component.adapter(ISourcePackageRecipe, ICollection, IWebServiceClientRequest)
@implementer(IFieldHTMLRenderer)
def distroseries_renderer(context, field, request):
    """Render a distroseries collection as a set of links."""

    def render(value):
        distroseries = sorted(
            context.distroseries, key=lambda ds: ds.displayname
        )
        if not distroseries:
            return "None"
        html = "<ul>"
        html += "".join(
            ["<li>%s</li>" % format_link(series) for series in distroseries]
        )
        html += "</ul>"
        return html

    return render


def builds_for_recipe(recipe):
    """A list of interesting builds.

    All pending builds are shown, as well as 1-5 recent builds.
    Recent builds are ordered by date finished (if completed) or
    date_started (if date finished is not set due to an error building or
    other circumstance which resulted in the build not being completed).
    This allows started but unfinished builds to show up in the view but
    be discarded as more recent builds become available.

    Builds that the user does not have permission to see are excluded.
    """
    builds = [
        build
        for build in recipe.pending_builds
        if check_permission("launchpad.View", build)
    ]
    for build in recipe.completed_builds:
        if not check_permission("launchpad.View", build):
            continue
        builds.append(build)
        if len(builds) >= 5:
            break
    return builds


def new_builds_notification_text(
    builds, already_pending=None, contains_unbuildable=False
):
    nr_builds = len(builds)
    if not nr_builds:
        builds_text = "All requested recipe builds are already queued."
    elif nr_builds == 1:
        builds_text = "1 new recipe build has been queued."
    else:
        builds_text = "%d new recipe builds have been queued." % nr_builds
    if nr_builds > 0 and already_pending:
        builds_text = "<p>%s</p>%s" % (builds_text, already_pending)
    if contains_unbuildable:
        builds_text = (
            "%s<p>The recipe contains an obsolete distroseries, "
            "which has been skipped.</p>" % builds_text
        )
    return structured(builds_text)


class SourcePackageRecipeRequestBuildsView(LaunchpadFormView):
    """A view for requesting builds of a SourcePackageRecipe."""

    @property
    def initial_values(self):
        """Set initial values for the widgets.

        The distroseries function as defaults for requesting a build.
        """
        initial_values = {"distroseries": self.context.distroseries}
        if self.context.daily_build_archive and check_permission(
            "launchpad.Append", self.context.daily_build_archive
        ):
            initial_values["archive"] = self.context.daily_build_archive
        return initial_values

    class schema(Interface):
        """Schema for requesting a build."""

        archive = Choice(
            vocabulary="TargetPPAs", title="Archive", required=False
        )
        distroseries = List(
            Choice(vocabulary="BuildableDistroSeries"),
            title="Distribution series",
        )

    custom_widget_distroseries = LabeledMultiCheckBoxWidget

    def validate(self, data):
        if not data["archive"]:
            self.setFieldError(
                "archive", "You must specify the archive to build into."
            )
            return
        distros = data.get("distroseries", [])
        if not len(distros):
            self.setFieldError(
                "distroseries",
                "You need to specify at least one distro series for which "
                "to build.",
            )
            return

    def requestBuild(self, data):
        """User action for requesting a number of builds.

        We raise exceptions for most errors but if there's already a pending
        build for a particular distroseries, we simply record that so that
        other builds can ne queued and a message be displayed to the caller.
        """
        informational = {}
        builds = []
        for distroseries in data["distroseries"]:
            try:
                build = self.context.requestBuild(
                    data["archive"], self.user, distroseries, manual=True
                )
                builds.append(build)
            except BuildAlreadyPending as e:
                existing_message = informational.get("already_pending")
                if existing_message:
                    new_message = existing_message[:-1] + (
                        ", and %s." % e.distroseries
                    )
                else:
                    new_message = (
                        "An identical build is "
                        "already pending for %s." % e.distroseries
                    )
                informational["already_pending"] = new_message

        return builds, informational


class SourcePackageRecipeRequestBuildsHtmlView(
    SourcePackageRecipeRequestBuildsView
):
    """Supports HTML form recipe build requests."""

    next_url = None

    @property
    def title(self):
        return "Request builds for %s" % self.context.name

    label = title

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action("Request builds", name="request")
    def request_action(self, action, data):
        builds, informational = self.requestBuild(data)
        self.next_url = self.cancel_url
        already_pending = informational.get("already_pending")
        notification_text = new_builds_notification_text(
            builds, already_pending
        )
        self.request.response.addNotification(notification_text)


class SourcePackageRecipeRequestBuildsAjaxView(
    SourcePackageRecipeRequestBuildsView
):
    """Supports AJAX form recipe build requests."""

    def _process_error(
        self,
        data=None,
        builds=None,
        informational=None,
        errors=None,
        reason="Validation",
    ):
        """Set up the response and json data to return to the caller."""
        self.request.response.setStatus(200, reason)
        self.request.response.setHeader("Content-type", "application/json")
        return_data = dict(builds=builds, errors=errors)
        if informational:
            return_data.update(informational)
        return json.dumps(return_data)

    def failure(self, action, data, errors):
        """Called by the form if validate() finds any errors.

        We simply convert the errors to json and return that data to the
        caller for display to the user.
        """
        return self._process_error(data=data, errors=self.widget_errors)

    @action("Request builds", name="request", failure=failure)
    def request_action(self, action, data):
        """User action for requesting a number of builds.

        The failure handler will handle any validation errors. We still need
        to handle errors which may occur when invoking the business logic.
        These "expected" errors are ones which result in a predefined message
        being displayed to the user. If the business method raises an
        unexpected exception, that will be handled using the form's standard
        exception processing mechanism (using response code 500).
        """
        builds, informational = self.requestBuild(data)
        # If there are errors we return a json data snippet containing the
        # errors as well as the form content. These errors are processed
        # by the caller's response handler and displayed to the user. The
        # form content may be rendered as well if required.
        if informational:
            builds_html = None
            if len(builds):
                builds_html = self.render()
            return self._process_error(
                data=data,
                builds=builds_html,
                informational=informational,
                reason="Request Build",
            )

    @property
    def builds(self):
        return builds_for_recipe(self.context)


class SourcePackageRecipeRequestDailyBuildView(LaunchpadFormView):
    """Supports requests to perform a daily build for a recipe.

    Renders the recipe builds table so that the recipe index page can be
    updated with the new build records.

    This view works for both ajax and html form requests.
    """

    next_url = None

    # Attributes for the html version
    page_title = "Build now"

    def initialize(self):
        super().initialize()
        if self.request.method == "GET":
            self.request.response.redirect(canonical_url(self.context))

    class schema(Interface):
        """Schema for requesting a build."""

    @action("Build now", name="build")
    def build_action(self, action, data):
        recipe = self.context
        try:
            builds = recipe.performDailyBuild()
        except ArchiveDisabled as e:
            self.request.response.addErrorNotification(str(e))
            self.next_url = canonical_url(recipe)
            return

        if self.request.is_ajax:
            template = ViewPageTemplateFile(
                "../templates/sourcepackagerecipe-builds.pt"
            )
            return template(self)
        else:
            contains_unbuildable = recipe.containsUnbuildableSeries(
                recipe.daily_build_archive
            )
            self.next_url = canonical_url(recipe)
            self.request.response.addNotification(
                new_builds_notification_text(
                    builds, contains_unbuildable=contains_unbuildable
                )
            )

    @property
    def builds(self):
        return builds_for_recipe(self.context)


class ISourcePackageEditSchema(Interface):
    """Schema for adding or editing a recipe."""

    use_template(
        ISourcePackageRecipe,
        include=[
            "name",
            "description",
            "owner",
            "build_daily",
            "distroseries",
        ],
    )
    daily_build_archive = Choice(
        vocabulary="TargetPPAs",
        title="Daily build archive",
        description=(
            "If built daily, this is the archive where the package "
            "will be uploaded."
        ),
    )
    recipe_text = has_structured_doc(
        Text(
            title="Recipe text",
            required=True,
            description="""The text of the recipe.
                <a href="/+help-code/recipe-syntax.html" target="help"
                  >Syntax help&nbsp;
                  <span class="sprite maybe action-icon">
                    Help
                  </span></a>
               """,
        )
    )


EXISTING_PPA = "existing-ppa"
CREATE_NEW = "create-new"


USE_ARCHIVE_VOCABULARY = SimpleVocabulary(
    (
        SimpleTerm(EXISTING_PPA, EXISTING_PPA, _("Use an existing PPA")),
        SimpleTerm(
            CREATE_NEW, CREATE_NEW, _("Create a new PPA for this recipe")
        ),
    )
)


class ISourcePackageAddSchema(ISourcePackageEditSchema):
    daily_build_archive = Choice(
        vocabulary="TargetPPAs",
        title="Daily build archive",
        required=False,
        description=(
            "If built daily, this is the archive where the package "
            "will be uploaded."
        ),
    )

    use_ppa = Choice(
        title=_("Which PPA"),
        vocabulary=USE_ARCHIVE_VOCABULARY,
        description=_("Which PPA to use..."),
        required=True,
    )

    ppa_name = TextLine(
        title=_("New PPA name"),
        required=False,
        constraint=name_validator,
        description=_(
            "A new PPA with this name will be created for "
            "the owner of the recipe ."
        ),
    )


class ErrorHandled(Exception):
    """A field error occurred and was handled."""


class RecipeTextValidatorMixin:
    """Class to validate that the Source Package Recipe text is valid."""

    def validate(self, data):
        if data["build_daily"]:
            if len(data["distroseries"]) == 0:
                self.setFieldError(
                    "distroseries",
                    "You must specify at least one series for daily builds.",
                )
        try:
            self.error_handler(
                getUtility(IRecipeBranchSource).getParsedRecipe,
                data["recipe_text"],
            )
        except ErrorHandled:
            pass

    def error_handler(self, callable, *args, **kwargs):
        try:
            return callable(*args)
        except TooNewRecipeFormat:
            self.setFieldError(
                "recipe_text",
                "The recipe format version specified is not available.",
            )
        except ForbiddenInstructionError as e:
            self.setFieldError(
                "recipe_text",
                'The recipe instruction "%s" is not permitted here.'
                % e.instruction_name,
            )
        except NoSuchBranch as e:
            self.setFieldError(
                "recipe_text", "%s is not a branch on Launchpad." % e.name
            )
        except NoSuchGitRepository as e:
            self.setFieldError(
                "recipe_text",
                "%s is not a Git repository on Launchpad." % e.name,
            )
        except (
            RecipeParseError,
            PrivateBranchRecipe,
            PrivateGitRepositoryRecipe,
        ) as e:
            self.setFieldError("recipe_text", str(e))
        raise ErrorHandled()


@implementer(IView)
class RelatedBranchesWidget(Widget):
    """A widget to render the related branches for a recipe."""

    __call__ = ViewPageTemplateFile(
        "../templates/sourcepackagerecipe-related-branches.pt"
    )

    related_package_branch_info = []
    related_series_branch_info = []

    def hasInput(self):
        return True

    def setRenderedValue(self, value):
        self.related_package_branch_info = value["related_package_branch_info"]
        self.related_series_branch_info = value["related_series_branch_info"]


class RecipeRelatedBranchesMixin(LaunchpadFormView):
    """A class to find related branches for a recipe's base branch."""

    custom_widget_related_branches = RelatedBranchesWidget

    def extendFields(self):
        """See `LaunchpadFormView`.

        Adds a related branches field to the form.
        """
        self.form_fields += form.Fields(Field(__name__="related_branches"))
        self.widget_errors["related_branches"] = ""

    def setUpWidgets(self, context=None):
        # Adds a new related branches widget.
        super().setUpWidgets(context)
        self.widgets["related_branches"].display_label = False
        self.widgets["related_branches"].setRenderedValue(
            dict(
                related_package_branch_info=self.related_package_branch_info,
                related_series_branch_info=self.related_series_branch_info,
            )
        )

    @cachedproperty
    def related_series_branch_info(self):
        branch_to_check = self.getBranch()
        if IBranch.providedBy(branch_to_check):
            branch_target = IBranchTarget(branch_to_check.target)
            return branch_target.getRelatedSeriesBranchInfo(
                branch_to_check, limit_results=5
            )

    @cachedproperty
    def related_package_branch_info(self):
        branch_to_check = self.getBranch()
        if IBranch.providedBy(branch_to_check):
            branch_target = IBranchTarget(branch_to_check.target)
            return branch_target.getRelatedPackageBranchInfo(
                branch_to_check, limit_results=5
            )


class SourcePackageRecipeAddView(
    RecipeRelatedBranchesMixin, RecipeTextValidatorMixin, LaunchpadFormView
):
    """View for creating Source Package Recipes."""

    title = label = "Create a new source package recipe"

    schema = ISourcePackageAddSchema
    next_url = None
    custom_widget_distroseries = LabeledMultiCheckBoxWidget
    custom_widget_owner = RecipeOwnerWidget
    custom_widget_use_ppa = LaunchpadRadioWidget

    def initialize(self):
        super().initialize()
        widget = self.widgets["use_ppa"]
        current_value = widget._getFormValue()
        self.use_ppa_existing = render_radio_widget_part(
            widget, EXISTING_PPA, current_value
        )
        self.use_ppa_new = render_radio_widget_part(
            widget, CREATE_NEW, current_value
        )
        archive_widget = self.widgets["daily_build_archive"]
        self.show_ppa_chooser = len(archive_widget.vocabulary) > 0
        if not self.show_ppa_chooser:
            self.widgets["ppa_name"].setRenderedValue("ppa")
        # Force there to be no '(nothing selected)' item in the select.
        # We do this as the input isn't listed as 'required' otherwise
        # the validator gets all confused when we want to create a new
        # PPA.
        archive_widget._displayItemForMissingValue = False

    def setUpFields(self):
        super().setUpFields()
        # Ensure distro series widget allows input
        self.form_fields["distroseries"].for_input = True

    def getBranch(self):
        """The branch or repository on which the recipe is built."""
        return self.context

    def _recipe_names(self):
        """A generator of recipe names."""
        # +junk-daily doesn't make a very good recipe name, so use the
        # branch name in that case; similarly for personal Git repositories.
        if (
            IBranch.providedBy(self.context)
            and self.context.target.allow_recipe_name_from_target
        ) or (
            (
                IGitRepository.providedBy(self.context)
                or IGitRef.providedBy(self.context)
            )
            and self.context.namespace.allow_recipe_name_from_target
        ):
            branch_target_name = self.context.target.name.split("/")[-1]
        else:
            branch_target_name = self.context.name
        yield "%s-daily" % branch_target_name
        counter = itertools.count(1)
        while True:
            yield "%s-daily-%s" % (branch_target_name, next(counter))

    def _find_unused_name(self, owner):
        # Grab the last path element of the branch target path.
        source = getUtility(ISourcePackageRecipeSource)
        for recipe_name in self._recipe_names():
            if not source.exists(owner, recipe_name):
                return recipe_name

    @property
    def initial_values(self):
        distroseries = BuildableDistroSeries.findSeries(self.user)
        series = [
            series
            for series in distroseries
            if series.status
            in (SeriesStatus.CURRENT, SeriesStatus.DEVELOPMENT)
        ]
        if IBranch.providedBy(self.context):
            recipe_text = MINIMAL_RECIPE_TEXT_BZR % self.context.identity
        elif IGitRepository.providedBy(self.context):
            default_ref = None
            if self.context.default_branch is not None:
                default_ref = self.context.getRefByPath(
                    self.context.default_branch
                )
            if default_ref is not None:
                branch_name = default_ref.name
            else:
                branch_name = "ENTER-BRANCH-NAME"
            recipe_text = MINIMAL_RECIPE_TEXT_GIT % (
                self.context.identity,
                branch_name,
            )
        elif IGitRef.providedBy(self.context):
            recipe_text = MINIMAL_RECIPE_TEXT_GIT % (
                self.context.repository.identity,
                self.context.name,
            )
        else:
            raise AssertionError("Unsupported context: %r" % (self.context,))
        return {
            "name": self._find_unused_name(self.user),
            "recipe_text": recipe_text,
            "owner": self.user,
            "distroseries": series,
            "build_daily": True,
            "use_ppa": EXISTING_PPA,
        }

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action("Create Recipe", name="create")
    def request_action(self, action, data):
        owner = data["owner"]
        if data["use_ppa"] == CREATE_NEW:
            ppa_name = data.get("ppa_name", None)
            ppa = owner.createPPA(
                getUtility(ILaunchpadCelebrities).ubuntu, ppa_name
            )
        else:
            ppa = data["daily_build_archive"]
        try:
            source_package_recipe = self.error_handler(
                getUtility(ISourcePackageRecipeSource).new,
                self.user,
                owner,
                data["name"],
                data["recipe_text"],
                data["description"],
                data["distroseries"],
                ppa,
                data["build_daily"],
            )
            Store.of(source_package_recipe).flush()
        except ErrorHandled:
            return

        self.next_url = canonical_url(source_package_recipe)

    def validate(self, data):
        super().validate(data)
        name = data.get("name", None)
        owner = data.get("owner", None)
        if name and owner:
            SourcePackageRecipeSource = getUtility(ISourcePackageRecipeSource)
            if SourcePackageRecipeSource.exists(owner, name):
                self.setFieldError(
                    "name",
                    "There is already a recipe owned by %s with this name."
                    % owner.displayname,
                )
        if data["use_ppa"] == CREATE_NEW:
            ppa_name = data.get("ppa_name", None)
            if ppa_name is None:
                self.setFieldError(
                    "ppa_name", "You need to specify a name for the PPA."
                )
            else:
                error = validate_ppa(
                    owner, getUtility(ILaunchpadCelebrities).ubuntu, ppa_name
                )
                if error is not None:
                    self.setFieldError("ppa_name", error)


class SourcePackageRecipeEditView(
    RecipeRelatedBranchesMixin, RecipeTextValidatorMixin, LaunchpadEditFormView
):
    """View for editing Source Package Recipes."""

    def getBranch(self):
        """The branch or repository on which the recipe is built."""
        return self.context.base

    @property
    def title(self):
        return "Edit %s source package recipe" % self.context.name

    label = title

    schema = ISourcePackageEditSchema
    next_url = None
    custom_widget_distroseries = LabeledMultiCheckBoxWidget

    def setUpFields(self):
        super().setUpFields()

        # Ensure distro series widget allows input
        self.form_fields["distroseries"].for_input = True

        if check_permission("launchpad.Admin", self.context):
            # Exclude the PPA archive dropdown.
            self.form_fields = self.form_fields.omit("daily_build_archive")

            owner_field = self.schema["owner"]
            any_owner_choice = PersonChoice(
                __name__="owner",
                title=owner_field.title,
                description=(
                    "As an administrator you are able to assign"
                    " this recipe to any person or team."
                ),
                required=True,
                vocabulary="ValidPersonOrTeam",
            )
            any_owner_field = form.Fields(
                any_owner_choice, render_context=self.render_context
            )
            # Replace the normal owner field with a more permissive vocab.
            self.form_fields = self.form_fields.omit("owner")
            self.form_fields = any_owner_field + self.form_fields

    @property
    def initial_values(self):
        return {
            "distroseries": self.context.distroseries,
            "recipe_text": self.context.recipe_text,
        }

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action("Update Recipe", name="update")
    def request_action(self, action, data):
        changed = False
        recipe_before_modification = Snapshot(
            self.context, providing=providedBy(self.context)
        )

        recipe_text = data.pop("recipe_text")
        try:
            recipe = self.error_handler(
                getUtility(IRecipeBranchSource).getParsedRecipe, recipe_text
            )
            if self.context.builder_recipe != recipe:
                self.error_handler(self.context.setRecipeText, recipe_text)
                changed = True
        except ErrorHandled:
            return

        distros = data.pop("distroseries")
        if distros != self.context.distroseries:
            self.context.distroseries.clear()
            for distroseries_item in distros:
                self.context.distroseries.add(distroseries_item)
            changed = True

        if self.updateContextFromData(data, notify_modified=False):
            changed = True

        if changed:
            field_names = [
                form_field.__name__ for form_field in self.form_fields
            ]
            notify(
                ObjectModifiedEvent(
                    self.context, recipe_before_modification, field_names
                )
            )

        self.next_url = canonical_url(self.context)

    @property
    def adapters(self):
        """See `LaunchpadEditFormView`"""
        return {ISourcePackageEditSchema: self.context}

    def validate(self, data):
        super().validate(data)
        name = data.get("name", None)
        owner = data.get("owner", None)
        if name and owner:
            SourcePackageRecipeSource = getUtility(ISourcePackageRecipeSource)
            if SourcePackageRecipeSource.exists(owner, name):
                recipe = owner.getRecipe(name)
                if recipe != self.context:
                    self.setFieldError(
                        "name",
                        "There is already a recipe owned by %s with this "
                        "name." % owner.displayname,
                    )


class SourcePackageRecipeDeleteView(LaunchpadFormView):
    @property
    def title(self):
        return "Delete %s source package recipe" % self.context.name

    label = title

    class schema(Interface):
        """Schema for deleting a recipe."""

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def next_url(self):
        return canonical_url(self.context.owner)

    @action("Delete recipe", name="delete")
    def request_action(self, action, data):
        self.context.destroySelf()
