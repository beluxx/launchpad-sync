# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for CodeImports."""

__all__ = [
    "CodeImportEditView",
    "CodeImportMachineView",
    "CodeImportNameValidationMixin",
    "CodeImportNewView",
    "CodeImportSetBreadcrumb",
    "CodeImportSetNavigation",
    "CodeImportSetView",
    "CodeImportTargetMixin",
    "RequestImportView",
    "TryImportAgainView",
    "validate_import_url",
]

from textwrap import dedent
from urllib.parse import urlparse

from lazr.restful.interface import copy_field, use_template
from zope.component import getUtility, queryAdapter
from zope.formlib import form
from zope.formlib.interfaces import IInputWidget
from zope.formlib.utility import setUpWidget
from zope.formlib.widget import CustomWidgetFactory
from zope.interface import Interface
from zope.schema import Choice
from zope.security.interfaces import Unauthorized
from zope.traversing.interfaces import IPathAdapter

from lp import _
from lp.app.browser.launchpadform import LaunchpadFormView, action
from lp.app.errors import NotFoundError
from lp.app.widgets.itemswidgets import (
    LaunchpadDropdownWidget,
    LaunchpadRadioWidget,
)
from lp.app.widgets.textwidgets import StrippedTextWidget, URIWidget
from lp.code.enums import (
    NON_CVS_RCS_TYPES,
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeImportResultStatus,
    CodeImportReviewStatus,
    CodeReviewNotificationLevel,
    RevisionControlSystems,
    TargetRevisionControlSystems,
)
from lp.code.errors import (
    BranchExists,
    CodeImportAlreadyRequested,
    CodeImportAlreadyRunning,
    CodeImportNotInReviewedState,
    GitRepositoryExists,
)
from lp.code.interfaces.branch import IBranch, user_has_special_branch_access
from lp.code.interfaces.branchnamespace import (
    IBranchNamespacePolicy,
    get_branch_namespace,
)
from lp.code.interfaces.codeimport import ICodeImport, ICodeImportSet
from lp.code.interfaces.codeimportmachine import ICodeImportMachineSet
from lp.code.interfaces.gitnamespace import (
    IGitNamespacePolicy,
    get_git_namespace,
)
from lp.registry.interfaces.product import IProduct
from lp.services.beautifulsoup import BeautifulSoup
from lp.services.fields import URIField
from lp.services.propertycache import cachedproperty
from lp.services.webapp import LaunchpadView, Navigation, canonical_url, stepto
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.batching import BatchNavigator
from lp.services.webapp.breadcrumb import Breadcrumb
from lp.services.webapp.escaping import structured


class CodeImportSetNavigation(Navigation):
    """Navigation methods for IBuilder."""

    usedfor = ICodeImportSet

    @stepto("+machines")
    def bugs(self):
        return getUtility(ICodeImportMachineSet)


class CodeImportSetBreadcrumb(Breadcrumb):
    """Builds a breadcrumb for an `ICodeImportSet`."""

    text = "Code Import System"


class DropdownWidgetWithAny(LaunchpadDropdownWidget):
    """A <select> widget with a more appropriate 'nothing selected' message.

    By default `LaunchpadDropdownWidget` displays 'nothing selected' when the
    associated value is None or not supplied, which is not what we want on
    this page.
    """

    _messageNoValue = _("Any")


class CodeImportSetView(LaunchpadView):
    """The default view for `ICodeImportSet`.

    We present the CodeImportSet as a list of all imports.
    """

    page_title = "Code Imports"

    def initialize(self):
        """See `LaunchpadView.initialize`."""
        review_status_field = copy_field(
            ICodeImport["review_status"], required=False, default=None
        )
        self.review_status_widget = CustomWidgetFactory(DropdownWidgetWithAny)
        setUpWidget(self, "review_status", review_status_field, IInputWidget)

        rcs_type_field = copy_field(
            ICodeImport["rcs_type"], required=False, default=None
        )
        self.rcs_type_widget = CustomWidgetFactory(DropdownWidgetWithAny)
        setUpWidget(self, "rcs_type", rcs_type_field, IInputWidget)

        target_rcs_type_field = copy_field(
            ICodeImport["target_rcs_type"], required=False, default=None
        )
        self.target_rcs_type_widget = CustomWidgetFactory(
            DropdownWidgetWithAny
        )
        setUpWidget(
            self, "target_rcs_type", target_rcs_type_field, IInputWidget
        )

        # status should be None if either (a) there were no query arguments
        # supplied, i.e. the user browsed directly to this page (this is when
        # hasValidInput returns False) or (b) the user chose 'Any' in the
        # status widget (this is when hasValidInput returns True but
        # getInputValue returns None).
        review_status = None
        if self.review_status_widget.hasValidInput():
            review_status = self.review_status_widget.getInputValue()
        # Similar for 'rcs_type' and 'target_rcs_type'.
        rcs_type = None
        if self.rcs_type_widget.hasValidInput():
            rcs_type = self.rcs_type_widget.getInputValue()
        target_rcs_type = None
        if self.target_rcs_type_widget.hasValidInput():
            target_rcs_type = self.target_rcs_type_widget.getInputValue()

        imports = self.context.search(
            review_status=review_status,
            rcs_type=rcs_type,
            target_rcs_type=target_rcs_type,
        )

        self.batchnav = BatchNavigator(imports, self.request)


class CodeImportBaseView(LaunchpadFormView):
    """A base view for both new and edit code import views."""

    schema = ICodeImport

    custom_widget_cvs_root = CustomWidgetFactory(
        StrippedTextWidget, displayWidth=50
    )
    custom_widget_cvs_module = CustomWidgetFactory(
        StrippedTextWidget, displayWidth=20
    )
    custom_widget_url = CustomWidgetFactory(URIWidget, displayWidth=50)

    @cachedproperty
    def _is_edit_user(self):
        """Can this user edit specific fields?"""
        return check_permission("launchpad.Edit", self.code_import)

    @cachedproperty
    def _is_moderator_user(self):
        """Is a moderator of code imports?"""
        return check_permission("launchpad.Moderate", self.code_import)

    def showOptionalMarker(self, field_name):
        """Don't show the optional marker for rcs locations."""
        # No field in either the new or edit view needs an optional marker,
        # so we can be simple here.
        return False

    def setSecondaryFieldError(self, field, error):
        """Set the field error only if there isn't an error already."""
        if not self.getFieldError(field):
            self.setFieldError(field, error)

    def _validateCVS(self, cvs_root, cvs_module, existing_import=None):
        """If the user has specified cvs, then we need to make
        sure that there isn't already an import with those values."""
        if cvs_root is None:
            self.setSecondaryFieldError("cvs_root", "Enter a CVS root.")
        if cvs_module is None:
            self.setSecondaryFieldError("cvs_module", "Enter a CVS module.")

        if cvs_root and cvs_module:
            code_import = getUtility(ICodeImportSet).getByCVSDetails(
                cvs_root, cvs_module
            )
            if code_import is not None and code_import != existing_import:
                self.addError(
                    structured(
                        """
                    Those CVS details are already specified for
                    the imported branch <a href="%s">%s</a>.""",
                        canonical_url(code_import.target),
                        code_import.target.unique_name,
                    )
                )

    def _validateURL(
        self,
        url,
        rcs_type,
        target_rcs_type,
        existing_import=None,
        field_name="url",
    ):
        """If the user has specified a url, we need to make sure that there
        isn't already an import with that url."""
        if url is None:
            self.setSecondaryFieldError(
                field_name, "Enter the URL of a foreign VCS branch."
            )
        else:
            reason = validate_import_url(
                url, rcs_type, target_rcs_type, existing_import
            )
            if reason:
                self.setFieldError(field_name, reason)


class CodeImportNameValidationMixin:
    """Provide branch/repository name validation logic for code imports."""

    def _setBranchExists(self, existing_branch, field_name):
        self.setFieldError(
            field_name,
            structured(
                dedent(
                    """
            There is already an existing import for
            <a href="%(product_url)s">%(product_name)s</a>
            with the name of
            <a href="%(branch_url)s">%(branch_name)s</a>."""
                ),
                product_url=canonical_url(existing_branch.target),
                product_name=existing_branch.target.name,
                branch_url=canonical_url(existing_branch),
                branch_name=existing_branch.name,
            ),
        )


class NewCodeImportForm(Interface):
    """The fields presented on the form for editing a code import."""

    use_template(IBranch, ["owner"])
    use_template(ICodeImport, ["rcs_type", "cvs_root", "cvs_module"])

    svn_branch_url = URIField(
        title=_("Branch URL"),
        required=False,
        description=_(
            "The URL of a Subversion branch, starting with svn:// or "
            "http(s)://.   You can include a username and password as part "
            "of the url, but this will be displayed on the branch page."
        ),
        allowed_schemes=["http", "https", "svn"],
        allow_userinfo=True,
        allow_port=True,
        allow_query=False,
        allow_fragment=False,
        trailing_slash=False,
    )

    git_repo_url = URIField(
        title=_("Repo URL"),
        required=False,
        description=_(
            "The URL of the Git repository.  For imports to Bazaar, the "
            "HEAD branch will be imported by default, but you can import "
            "different branches by appending ',branch=$name' to the URL.  "
            "For imports to Git, the entire repository will be imported."
        ),
        allowed_schemes=["git", "http", "https"],
        allow_userinfo=True,
        allow_port=True,
        allow_query=False,
        allow_fragment=False,
        trailing_slash=False,
    )

    git_target_rcs_type = Choice(
        title=_("Target version control system"),
        description=_(
            "The version control system that the source code should be "
            "imported into on the Launchpad side."
        ),
        required=False,
        vocabulary=TargetRevisionControlSystems,
    )

    bzr_branch_url = URIField(
        title=_("Branch URL"),
        required=False,
        description=_("The URL of the Bazaar branch."),
        allowed_schemes=["http", "https", "bzr", "ftp"],
        allow_userinfo=True,
        allow_port=True,
        allow_query=False,  # Query makes no sense in Bazaar
        allow_fragment=False,  # Fragment makes no sense in Bazaar
        trailing_slash=False,
    )

    branch_name = copy_field(
        IBranch["name"],
        __name__="branch_name",
        title=_("Name"),
        description=_(
            "This will be used in the branch or repository URL to identify "
            "the import.  Examples: main, trunk."
        ),
    )

    product = Choice(
        title=_("Project"),
        description=_("The Project to associate the code import with."),
        vocabulary="Product",
    )


class CodeImportNewView(CodeImportBaseView, CodeImportNameValidationMixin):
    """The view to request a new code import."""

    schema = NewCodeImportForm
    next_url = None
    for_input = True

    custom_widget_rcs_type = LaunchpadRadioWidget
    custom_widget_git_target_rcs_type = LaunchpadRadioWidget

    @property
    def initial_values(self):
        return {
            "owner": self.user,
            "rcs_type": RevisionControlSystems.BZR,
            "branch_name": "trunk",
            "git_target_rcs_type": TargetRevisionControlSystems.BZR,
        }

    @property
    def context_is_product(self):
        return IProduct.providedBy(self.context)

    @property
    def label(self):
        label = "Request a code import"
        if self.context_is_product:
            label += " for %s" % self.context.displayname
        return label

    @property
    def cancel_url(self):
        """Cancel should take the user back to the root site."""
        return "/"

    def setUpFields(self):
        CodeImportBaseView.setUpFields(self)
        if self.context_is_product:
            self.form_fields = self.form_fields.omit("product")

        # If the user can administer branches, then they should be able to
        # assign the ownership of the branch to any valid person or team.
        if user_has_special_branch_access(self.user):
            owner_field = self.schema["owner"]
            any_owner_choice = Choice(
                __name__="owner",
                title=owner_field.title,
                description=_(
                    "As an administrator you are able to reassign this "
                    "branch to any person or team."
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

    def setUpWidgets(self):
        super().setUpWidgets()

        # Extract the radio buttons from the rcs_type widget, so we can
        # display them separately in the form.
        soup = BeautifulSoup(self.widgets["rcs_type"]())
        fields = soup.find_all("input")
        [cvs_button, svn_button, git_button, bzr_button, empty_marker] = [
            field
            for field in fields
            if field.get("value") in ["CVS", "BZR_SVN", "GIT", "BZR", "1"]
        ]
        bzr_button["onclick"] = "updateWidgets()"
        cvs_button["onclick"] = "updateWidgets()"
        svn_button["onclick"] = "updateWidgets()"
        git_button["onclick"] = "updateWidgets()"
        # The following attributes are used only in the page template.
        self.rcs_type_cvs = str(cvs_button)
        self.rcs_type_svn = str(svn_button)
        self.rcs_type_git = str(git_button)
        self.rcs_type_bzr = str(bzr_button)
        self.rcs_type_emptymarker = str(empty_marker)
        # This widget is only conditionally required in the rcs_type == GIT
        # case, but we still don't want a "(nothing selected)" item.
        self.widgets["git_target_rcs_type"]._displayItemForMissingValue = False

    def _getImportLocation(self, data):
        """Return the import location based on type."""
        rcs_type = data["rcs_type"]
        if rcs_type == RevisionControlSystems.CVS:
            return data.get("cvs_root"), data.get("cvs_module"), None
        elif rcs_type == RevisionControlSystems.BZR_SVN:
            return None, None, data.get("svn_branch_url")
        elif rcs_type == RevisionControlSystems.GIT:
            return None, None, data.get("git_repo_url")
        elif rcs_type == RevisionControlSystems.BZR:
            return None, None, data.get("bzr_branch_url")
        else:
            raise AssertionError(
                "Unexpected revision control type %r." % rcs_type
            )

    def _create_import(self, data, status):
        """Create the code import."""
        product = self.getProduct(data)
        cvs_root, cvs_module, url = self._getImportLocation(data)
        if data["rcs_type"] == RevisionControlSystems.GIT:
            target_rcs_type = data.get(
                "git_target_rcs_type", TargetRevisionControlSystems.BZR
            )
        else:
            target_rcs_type = TargetRevisionControlSystems.BZR
        return getUtility(ICodeImportSet).new(
            registrant=self.user,
            owner=data["owner"],
            context=product,
            branch_name=data["branch_name"],
            rcs_type=data["rcs_type"],
            target_rcs_type=target_rcs_type,
            url=url,
            cvs_root=cvs_root,
            cvs_module=cvs_module,
            review_status=status,
        )

    @action(_("Request Import"), name="request_import")
    def request_import_action(self, action, data):
        """Create the code_import, and subscribe the user to the branch."""
        try:
            code_import = self._create_import(data, None)
        except BranchExists as e:
            self._setBranchExists(e.existing_branch, "branch_name")
            return
        except GitRepositoryExists as e:
            self._setBranchExists(e.existing_repository, "branch_name")
            return

        # Subscribe the user.
        code_import.target.subscribe(
            self.user,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.NOEMAIL,
            self.user,
        )

        self.next_url = canonical_url(code_import.target)

        self.request.response.addNotification(
            """
            New code import created. The code import will start shortly."""
        )

    def getProduct(self, data):
        """If the context is a product, use that, otherwise get from data."""
        if self.context_is_product:
            return self.context
        else:
            return data.get("product")

    def validate_widgets(self, data, names=None):
        """See `LaunchpadFormView`."""
        self.widgets["git_target_rcs_type"].context.required = (
            data.get("rcs_type") == RevisionControlSystems.GIT
        )
        super().validate_widgets(data, names=names)

    def validate(self, data):
        """See `LaunchpadFormView`."""
        rcs_type = data["rcs_type"]
        if rcs_type == RevisionControlSystems.GIT:
            target_rcs_type = data.get(
                "git_target_rcs_type", TargetRevisionControlSystems.BZR
            )
        else:
            target_rcs_type = TargetRevisionControlSystems.BZR

        # Make sure that the user is able to create branches/repositories
        # for the specified namespace.
        product = self.getProduct(data)
        # 'owner' in data may be None if it failed validation.
        owner = data.get("owner")
        if product is not None and owner is not None:
            if target_rcs_type == TargetRevisionControlSystems.BZR:
                namespace = get_branch_namespace(owner, product)
                policy = IBranchNamespacePolicy(namespace)
                can_create = policy.canCreateBranches(self.user)
            else:
                namespace = get_git_namespace(product, owner)
                policy = IGitNamespacePolicy(namespace)
                can_create = policy.canCreateRepositories(self.user)
            if not can_create:
                self.setFieldError(
                    "product",
                    "You are not allowed to register imports for %s."
                    % product.displayname,
                )

        # Make sure fields for unselected revision control systems
        # are blanked out:
        if rcs_type == RevisionControlSystems.CVS:
            self._validateCVS(data.get("cvs_root"), data.get("cvs_module"))
        elif rcs_type == RevisionControlSystems.BZR_SVN:
            self._validateURL(
                data.get("svn_branch_url"),
                rcs_type,
                target_rcs_type,
                field_name="svn_branch_url",
            )
        elif rcs_type == RevisionControlSystems.GIT:
            self._validateURL(
                data.get("git_repo_url"),
                rcs_type,
                target_rcs_type,
                field_name="git_repo_url",
            )
        elif rcs_type == RevisionControlSystems.BZR:
            self._validateURL(
                data.get("bzr_branch_url"),
                rcs_type,
                target_rcs_type,
                field_name="bzr_branch_url",
            )
        else:
            raise AssertionError(
                "Unexpected revision control type %r." % rcs_type
            )


class EditCodeImportForm(Interface):
    """The fields presented on the form for editing a code import."""

    url = copy_field(ICodeImport["url"], readonly=False)
    cvs_root = copy_field(ICodeImport["cvs_root"], readonly=False)
    cvs_module = copy_field(ICodeImport["cvs_module"], readonly=False)
    whiteboard = copy_field(IBranch["whiteboard"])


def _makeEditAction(label, status, text):
    """Make an Action to call a particular code import method.

    :param label: The label for the action, which will end up as the
         button title.
    :param status: If the code import has this as its review_status, don't
        show the button (always show the button if it is None).
    :param text: The text to go after 'The code import has been' in a
        notifcation, if a change was made.
    """
    if status is not None:

        def condition(self, ignored):
            return self._showButtonForStatus(status)

    else:
        condition = None

    def success(self, action, data):
        """Make the requested status change."""
        if self._is_moderator_user:
            # Moderators can change everything in code import, including its
            # status.
            if status is not None:
                data["review_status"] = status
            event = self.code_import.updateFromData(data, self.user)
            if event is not None:
                self.request.response.addNotification(
                    "The code import has been " + text + "."
                )
        elif self._is_edit_user and "url" in data:
            # Edit users can only change URL
            event = self.code_import.updateURL(data["url"], self.user)
            if event is not None:
                self.request.response.addNotification(
                    "The code import URL has been updated."
                )
        else:
            self.request.response.addNotification("No changes made.")

    name = label.lower().replace(" ", "_")
    return form.Action(label, name=name, success=success, condition=condition)


class CodeImportEditView(CodeImportBaseView):
    """View for editing code imports.

    This view is registered against the target, but mostly edits the code
    import for that target -- the exception being that it also allows the
    editing of the branch whiteboard in the case of Bazaar branches.  If the
    target has no associated code import, then the result is a 404.  If the
    target does have a code import, then the adapters property allows the
    form internals to do the associated mappings.
    """

    schema = EditCodeImportForm
    next_url = None
    cancel_url = None

    # Need this to render the context to prepopulate the form fields.
    # Added here as the base class isn't LaunchpadEditFormView.
    render_context = True
    page_title = "Edit import details"
    label = page_title

    @property
    def initial_values(self):
        if (
            self.code_import.target_rcs_type
            == TargetRevisionControlSystems.BZR
        ):
            return {"whiteboard": self.context.whiteboard}
        else:
            return {}

    def initialize(self):
        """Show a 404 if the target has no code import."""
        self.code_import = self.context.code_import
        if self.code_import is None:
            raise NotFoundError
        if not self._is_edit_user and not self._is_moderator_user:
            raise Unauthorized
        # The next and cancel location is the target details page.
        self.cancel_url = self.next_url = canonical_url(self.context)
        super().initialize()

    @property
    def adapters(self):
        """See `LaunchpadFormView`."""
        return {EditCodeImportForm: self.code_import}

    def setUpFields(self):
        CodeImportBaseView.setUpFields(self)

        # If the import is a Subversion import, then omit the CVS
        # fields, and vice versa.
        if self.code_import.rcs_type == RevisionControlSystems.CVS:
            self.form_fields = self.form_fields.omit("url")
        elif self.code_import.rcs_type in NON_CVS_RCS_TYPES:
            self.form_fields = self.form_fields.omit("cvs_root", "cvs_module")
        else:
            raise AssertionError("Unknown rcs_type for code import.")

        if (
            self.code_import.target_rcs_type
            != TargetRevisionControlSystems.BZR
        ):
            self.form_fields = self.form_fields.omit("whiteboard")

    def _showButtonForStatus(self, status):
        """If the status is different, and the user is super, show button."""
        return (
            self._is_moderator_user
            and self.code_import.review_status != status
        )

    actions = form.Actions(
        _makeEditAction(_("Update"), None, "updated"),
        _makeEditAction(
            _("Approve"), CodeImportReviewStatus.REVIEWED, "approved"
        ),
        _makeEditAction(
            _("Mark Invalid"), CodeImportReviewStatus.INVALID, "set as invalid"
        ),
        _makeEditAction(
            _("Suspend"), CodeImportReviewStatus.SUSPENDED, "suspended"
        ),
        _makeEditAction(
            _("Mark Failing"),
            CodeImportReviewStatus.FAILING,
            "marked as failing",
        ),
    )

    def validate(self, data):
        """See `LaunchpadFormView`."""
        if self.code_import.rcs_type == RevisionControlSystems.CVS:
            self._validateCVS(
                data.get("cvs_root"), data.get("cvs_module"), self.code_import
            )
        elif self.code_import.rcs_type in NON_CVS_RCS_TYPES:
            self._validateURL(
                data.get("url"),
                self.code_import.rcs_type,
                self.code_import.target_rcs_type,
                self.code_import,
            )
        else:
            raise AssertionError("Unknown rcs_type for code import.")


class CodeImportMachineView(LaunchpadView):
    """The view for the page that shows all the import machines."""

    label = "Import machines for Launchpad"

    @property
    def machines(self):
        """Get the machines, sorted alphabetically by hostname."""
        return getUtility(ICodeImportMachineSet).getAll()


def validate_import_url(url, rcs_type, target_rcs_type, existing_import=None):
    """Validate the given import URL."""
    if rcs_type.name == target_rcs_type.name and urlparse(url).netloc.endswith(
        "launchpad.net"
    ):
        return (
            "You cannot create same-VCS imports for branches or repositories "
            "that are hosted by Launchpad."
        )
    code_import = getUtility(ICodeImportSet).getByURL(url, target_rcs_type)
    if code_import is not None:
        if existing_import and code_import == existing_import:
            return None
        if code_import.target_rcs_type == TargetRevisionControlSystems.BZR:
            target_type = "branch"
        else:
            target_type = "repository"
        return structured(
            "This foreign branch URL is already specified for the imported "
            "%s <a href='%s'>%s</a>.",
            target_type,
            canonical_url(code_import.target),
            code_import.target.unique_name,
        )


class CodeImportTargetMixin:
    """Common code import methods for Branch and GitRepository views."""

    @cachedproperty
    def latest_code_import_results(self):
        """Return the last 10 CodeImportResults."""
        return list(self.context.code_import.results[:10])

    def iconForCodeImportResultStatus(self, status):
        """The icon to represent the `CodeImportResultStatus` `status`."""
        if status == CodeImportResultStatus.SUCCESS_PARTIAL:
            return "/@@/yes-gray"
        elif status in CodeImportResultStatus.successes:
            return "/@@/yes"
        else:
            return "/@@/no"

    @property
    def url_is_web(self):
        """True if an imported branch's URL is HTTP or HTTPS."""
        # You should only be calling this if it's an SVN, BZR or GIT code
        # import
        assert self.context.code_import
        url = self.context.code_import.url
        assert url
        # https starts with http too!
        return url.startswith("http")


class RequestImportView(LaunchpadFormView):
    """Provide an 'Import now' button on the branch/repository index page.

    This only appears on the page of a branch/repository with an associated
    code import that is being actively imported and where there is a import
    scheduled at some point in the future.
    """

    schema = Interface
    field_names = []

    form_style = "display: inline"

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action("Import Now", name="request")
    def request_import_action(self, action, data):
        try:
            self.context.code_import.requestImport(
                self.user, error_if_already_requested=True
            )
            self.request.response.addNotification(
                "Import will run as soon as possible."
            )
        except CodeImportNotInReviewedState:
            self.request.response.addNotification(
                "This import is no longer being updated automatically."
            )
        except CodeImportAlreadyRunning:
            self.request.response.addNotification(
                "The import is already running."
            )
        except CodeImportAlreadyRequested as e:
            user = e.requesting_user
            adapter = queryAdapter(user, IPathAdapter, "fmt")
            self.request.response.addNotification(
                structured(
                    "The import has already been requested by %s."
                    % adapter.link(None)
                )
            )

    @property
    def prefix(self):
        return "request%s" % self.context.id

    @property
    def action_url(self):
        return "%s/@@+request-import" % canonical_url(self.context)


class TryImportAgainView(LaunchpadFormView):
    """Provide an 'Try again' button on the branch/repository index page.

    This only appears on the page of a branch/repository with an associated
    code import that is marked as failing.
    """

    schema = Interface
    field_names = []

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action("Try Again", name="tryagain")
    def request_try_again(self, action, data):
        if (
            self.context.code_import.review_status
            != CodeImportReviewStatus.FAILING
        ):
            self.request.response.addNotification(
                "The import is now %s."
                % self.context.code_import.review_status.name
            )
        else:
            self.context.code_import.tryFailingImportAgain(self.user)
            self.request.response.addNotification(
                "Import will be tried again as soon as possible."
            )

    @property
    def prefix(self):
        return "tryagain"
