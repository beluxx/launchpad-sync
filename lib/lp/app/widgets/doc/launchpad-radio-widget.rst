LaunchpadRadioWidget
====================

There are two Launchpad radio widgets, one that shows descriptions,
and one that doesn't.

    >>> from lp.app.widgets.itemswidgets import (
    ...     LaunchpadRadioWidget, LaunchpadRadioWidgetWithDescription)

The LaunchpadRadioWidget is mostly used to display items from
an enumerated type.

    >>> from lp.services.beautifulsoup import BeautifulSoup
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.code.interfaces.branch import IBranch
    >>> branch = factory.makeAnyBranch()
    >>> branch_type_field = IBranch['branch_type'].bind(branch)
    >>> request = LaunchpadTestRequest()
    >>> radio_widget = LaunchpadRadioWidget(
    ...     branch_type_field, branch_type_field.vocabulary, request)
    >>> radio_widget.setRenderedValue(branch_type_field.vocabulary.HOSTED)

The widget is rendered as a collection of labels with the radio
buttons inside.

    >>> html = BeautifulSoup(radio_widget())
    >>> for label in html.find_all('label'):
    ...     print(label.decode_contents(formatter='html'))
    <input checked="checked" class="radioType" id="field.branch_type.0"
           name="field.branch_type" type="radio" value="HOSTED"/>&nbsp;Hosted
    <input class="radioType" id="field.branch_type.1" name="field.branch_type"
           type="radio" value="MIRRORED"/>&nbsp;Mirrored
    <input class="radioType" id="field.branch_type.2" name="field.branch_type"
           type="radio" value="IMPORTED"/>&nbsp;Imported
    <input class="radioType" id="field.branch_type.3" name="field.branch_type"
           type="radio" value="REMOTE"/>&nbsp;Remote


LaunchpadRadioWidgetWithDescription
-----------------------------------

The LaunchpadRadioWidgetWithDescription widget renders the descriptions
along with the titles from the enumerated type vocabulary.

    >>> radio_widget = LaunchpadRadioWidgetWithDescription(
    ...     branch_type_field, branch_type_field.vocabulary, request)
    >>> radio_widget.setRenderedValue(branch_type_field.vocabulary.HOSTED)

The widget is rendered in a table with the descriptions lined up
under the labels.  The labels are rendered next to the radio buttons,
in a different table cell, and use the 'for' attribute of the label
to associate the label with the radio button input.

    >>> print(radio_widget())
    <table class="radio-button-widget"><tr>
      <td rowspan="2"><input class="radioType" checked="checked"
          id="field.branch_type.0" name="field.branch_type" type="radio"
          value="HOSTED" /></td>
      <td><label for="field.branch_type.0">Hosted</label></td>
    </tr>
    <tr>
      <td class="formHelp">Launchpad is the primary location of this branch.
      </td>
    </tr>
    <tr>
      <td rowspan="2"><input class="radioType" id="field.branch_type.1"
          name="field.branch_type" type="radio" value="MIRRORED" /></td>
      <td><label for="field.branch_type.1">Mirrored</label></td>
    </tr>
    <tr>
      <td class="formHelp">Primarily hosted elsewhere and is periodically
      mirrored from the external location into Launchpad.  </td>
    </tr>
    <tr>
      <td rowspan="2"><input class="radioType" id="field.branch_type.2"
          name="field.branch_type" type="radio" value="IMPORTED" /></td>
      <td><label for="field.branch_type.2">Imported</label></td>
    </tr>
    <tr>
      <td class="formHelp">This branch has been imported from an
      externally-hosted branch in bzr or another VCS and is made available
      through Launchpad. </td>
    </tr>
    <tr>
      <td rowspan="2"><input class="radioType" id="field.branch_type.3"
          name="field.branch_type" type="radio" value="REMOTE" /></td>
      <td><label for="field.branch_type.3">Remote</label></td>
    </tr>
    <tr>
      <td class="formHelp">Registered in Launchpad with an external location,
      but is not to be mirrored, nor available through Launchpad. </td>
    </tr>
    </table>
    <input name="field.branch_type-empty-marker" type="hidden" value="1" />

If the enumerated type doesn't have any descriptions, then the extra
rows are not rendered.

    >>> from lazr.enum import EnumeratedType, Item
    >>> class SomeFruit(EnumeratedType):
    ...     "A choice of fruit."
    ...     APPLE = Item('Apple')
    ...     PEAR = Item('Pear')
    ...     ORANGE = Item('Orange')

    >>> radio_widget = LaunchpadRadioWidgetWithDescription(
    ...     branch_type_field, SomeFruit, request)
    >>> print(radio_widget())
    <table class="radio-button-widget"><tr>
      <td><input class="radioType" id="field.branch_type.0"
                 name="field.branch_type" type="radio" value="APPLE" /></td>
      <td><label for="field.branch_type.0">Apple</label></td>
    </tr>
    <tr>
      <td><input class="radioType" id="field.branch_type.1"
                 name="field.branch_type" type="radio" value="PEAR" /></td>
      <td><label for="field.branch_type.1">Pear</label></td>
    </tr>
    <tr>
      <td><input class="radioType" id="field.branch_type.2"
                 name="field.branch_type" type="radio" value="ORANGE" /></td>
      <td><label for="field.branch_type.2">Orange</label></td>
    </tr>
    </table>
    <input name="field.branch_type-empty-marker" type="hidden" value="1" />

Sometimes, it is desirable to display to the user additional, context specific
information to explain the choices available for selection. This can be done
by setting the optional extra_hint and extra_hint_class attributes on the
widget.
    >>> radio_widget.extra_hint = 'Some additional information'
    >>> radio_widget.extra_hint_class = 'inline-informational'
    >>> print(radio_widget())
    <div class="inline-informational">Some additional information</div>
    <table class="radio-button-widget"><tr>
    ...
    </table>
    <input name="field.branch_type-empty-marker" type="hidden" value="1" />


LaunchpadBooleanRadioWidget
---------------------------

The LaunchpadBooleanRadioWidget renders a boolean field as radio buttons.
This widget is uses the LaunchpadRadioWidget to render the items. The values
are rendered as 'yes' and 'no'; a missing value radio item is not rendered.

    >>> from zope.schema import Bool
    >>> from lp.app.widgets.itemswidgets import LaunchpadBooleanRadioWidget

    >>> field = Bool(
    ...     __name__='sentient',
    ...     title=u"Are you sentient?",
    ...     description=u"Are you human or a bot?",
    ...     required=False, readonly=False, default=True)

    >>> class Agent:
    ...     def __init__(self, sentient):
    ...         self.sentient = sentient

    >>> agent = Agent(True)
    >>> bound_field = field.bind(agent)
    >>> radio_widget = LaunchpadBooleanRadioWidget(bound_field, request)
    >>> print(radio_widget())
    <label style="font-weight: normal"><input
        class="radioType" checked="checked" id="field.sentient.0"
        name="field.sentient" type="radio" value="yes"
    />&nbsp;yes</label><br
    /><label style="font-weight: normal"><input
        class="radioType" id="field.sentient.1" name="field.sentient"
        type="radio" value="no" />&nbsp;no</label>
    <input name="field.sentient-empty-marker" type="hidden" value="1" />

The labels for True and False values can be set using the true_label and
false_label attributes.

    >>> radio_widget.true_label = 'I think therefore I am'
    >>> radio_widget.false_label = 'I am a turing test'
    >>> print(radio_widget())
    <label style="font-weight: normal"><input
        class="radioType" checked="checked" id="field.sentient.0"
        name="field.sentient" type="radio" value="yes"
    />&nbsp;I think therefore I am</label><br
    /><label style="font-weight: normal"><input
        class="radioType" id="field.sentient.1" name="field.sentient"
        type="radio" value="no" />&nbsp;I am a turing test</label>
    <input name="field.sentient-empty-marker" type="hidden" value="1" />
