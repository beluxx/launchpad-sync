# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "GitGranteeDisplayWidget",
    "GitGranteeField",
    "GitGranteeWidget",
]

from lazr.enum import DBItem
from lazr.restful.fields import Reference
from zope.browserpage import ViewPageTemplateFile
from zope.formlib.interfaces import (
    ConversionError,
    IDisplayWidget,
    IInputWidget,
    InputErrors,
    MissingInputError,
    WidgetInputError,
)
from zope.formlib.utility import setUpWidget
from zope.formlib.widget import (
    BrowserWidget,
    CustomWidgetFactory,
    DisplayWidget,
    InputWidget,
    renderElement,
)
from zope.interface import implementer
from zope.schema import Choice, Field
from zope.schema.interfaces import IField
from zope.schema.vocabulary import getVocabularyRegistry
from zope.security.proxy import isinstance as zope_isinstance

from lp import _
from lp.app.browser.tales import PersonFormatterAPI
from lp.app.errors import UnexpectedFormData
from lp.app.validators import LaunchpadValidationError
from lp.app.widgets.popup import PersonPickerWidget
from lp.code.enums import GitGranteeType
from lp.code.interfaces.gitrule import IGitRule
from lp.registry.interfaces.person import IPerson
from lp.services.webapp.interfaces import (
    IAlwaysSubmittedWidget,
    IMultiLineWidgetLayout,
)


class IGitGranteeField(IField):
    """An interface for a Git access grantee field."""

    rule = Reference(
        title=_("Rule"),
        required=True,
        readonly=True,
        schema=IGitRule,
        description=_("The rule that this grantee is for."),
    )


@implementer(IGitGranteeField)
class GitGranteeField(Field):
    """A field that holds a Git access grantee."""

    def __init__(self, rule, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rule = rule

    def constraint(self, value):
        """See `IField`."""
        if zope_isinstance(value, DBItem) and value.enum == GitGranteeType:
            return value != GitGranteeType.PERSON
        else:
            return value in getVocabularyRegistry().get(
                None, "ValidPersonOrTeam"
            )


@implementer(IDisplayWidget)
class GitGranteePersonDisplayWidget(BrowserWidget):
    def __init__(self, context, vocabulary, request):
        super().__init__(context, request)

    def __call__(self):
        if self._renderedValueSet():
            return PersonFormatterAPI(self._data).link(None)
        else:
            return ""


@implementer(IMultiLineWidgetLayout)
class GitGranteeWidgetBase(BrowserWidget):
    template = ViewPageTemplateFile("templates/gitgrantee.pt")
    default_option = "person"
    _widgets_set_up = False

    def setUpSubWidgets(self):
        if self._widgets_set_up:
            return
        fields = [
            Choice(
                __name__="person",
                title="Person",
                required=False,
                vocabulary="ValidPersonOrTeam",
            ),
        ]
        if self._read_only:
            self.person_widget = CustomWidgetFactory(
                GitGranteePersonDisplayWidget
            )
        else:
            self.person_widget = CustomWidgetFactory(
                PersonPickerWidget,
                # XXX cjwatson 2018-10-18: This is a little unfortunate, but
                # otherwise there's no spacing at all between the
                # (deliberately unlabelled) radio button and the text box.
                style="margin-left: 4px;",
            )
        for field in fields:
            setUpWidget(
                self,
                field.__name__,
                field,
                self._sub_widget_interface,
                prefix=self.name,
            )
        self._widgets_set_up = True

    def setUpOptions(self):
        """Set up options to be rendered."""
        self.options = {}
        for option in ("repository_owner", "person"):
            attributes = {
                "type": "radio",
                "name": self.name,
                "value": option,
                "id": "%s.option.%s" % (self.name, option),
                # XXX cjwatson 2018-10-18: Ugly, but it's worse without
                # this, especially in a permissions table where this widget
                # is normally used.
                "style": "margin-left: 0;",
            }
            if (
                self.request.form_ng.getOne(self.name, self.default_option)
                == option
            ):
                attributes["checked"] = "checked"
            if self._read_only:
                attributes["disabled"] = "disabled"
            self.options[option] = renderElement("input", **attributes)

    @property
    def show_options(self):
        return {
            option: not self._read_only or self.default_option == option
            for option in ("repository_owner", "person")
        }

    def setRenderedValue(self, value):
        """See `IWidget`."""
        self.setUpSubWidgets()
        if value == GitGranteeType.REPOSITORY_OWNER:
            self.default_option = "repository_owner"
            return
        elif value is None or IPerson.providedBy(value):
            self.default_option = "person"
            self.person_widget.setRenderedValue(value)
            return
        else:
            raise AssertionError("Not a valid value: %r" % value)

    def __call__(self):
        """See `zope.formlib.interfaces.IBrowserWidget`."""
        self.setUpSubWidgets()
        self.setUpOptions()
        return self.template()


@implementer(IDisplayWidget)
class GitGranteeDisplayWidget(GitGranteeWidgetBase, DisplayWidget):
    """Widget for displaying a Git access grantee."""

    _sub_widget_interface = IDisplayWidget
    _read_only = True


@implementer(IAlwaysSubmittedWidget, IInputWidget)
class GitGranteeWidget(GitGranteeWidgetBase, InputWidget):
    """Widget for selecting a Git access grantee."""

    _sub_widget_interface = IInputWidget
    _read_only = False
    _widgets_set_up = False

    @property
    def show_options(self):
        show_options = super().show_options
        # Hide options that indicate unique grantee_types (e.g.
        # repository_owner) if they already exist for the context rule.
        if (
            show_options["repository_owner"]
            and not self.context.rule.repository.findRuleGrantsByGrantee(
                GitGranteeType.REPOSITORY_OWNER,
                ref_pattern=self.context.rule.ref_pattern,
                include_transitive=False,
            ).is_empty()
        ):
            show_options["repository_owner"] = False
        return show_options

    def hasInput(self):
        self.setUpSubWidgets()
        form_value = self.request.form_ng.getOne(self.name)
        if form_value is None:
            return False
        return form_value != "person" or self.person_widget.hasInput()

    def hasValidInput(self):
        """See `zope.formlib.interfaces.IInputWidget`."""
        try:
            self.getInputValue()
            return True
        except InputErrors:
            return False
        except UnexpectedFormData:
            return False

    def getInputValue(self):
        """See `zope.formlib.interfaces.IInputWidget`."""
        self.setUpSubWidgets()
        form_value = self.request.form_ng.getOne(self.name)
        if form_value == "repository_owner":
            return GitGranteeType.REPOSITORY_OWNER
        elif form_value == "person":
            try:
                return self.person_widget.getInputValue()
            except MissingInputError:
                raise WidgetInputError(
                    self.name,
                    self.label,
                    LaunchpadValidationError(
                        "Please enter a person or team name"
                    ),
                )
            except ConversionError:
                entered_name = self.request.form_ng.getOne(
                    "%s.person" % self.name
                )
                raise WidgetInputError(
                    self.name,
                    self.label,
                    LaunchpadValidationError(
                        "There is no person or team named '%s' registered in "
                        "Launchpad" % entered_name
                    ),
                )
        else:
            raise UnexpectedFormData("No valid option was selected.")

    def error(self):
        """See `zope.formlib.interfaces.IBrowserWidget`."""
        try:
            if self.hasInput():
                self.getInputValue()
        except InputErrors as error:
            self._error = error
        return super().error()
