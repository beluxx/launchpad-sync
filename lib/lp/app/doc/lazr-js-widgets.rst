LAZR JS Wrappers
================

The lp.app.browser.lazrjs module contains several classes that simplify the
use of widgets defined in Lazr-JS.

When rendering these widgets in page templates, all you need to do is 'call'
them.  TAL will do this for you.

  <tal:widget replace="structure view/nifty_widget"/>


TextLineEditorWidget
--------------------

We have a convenient wrapper for the inlineedit/editor JS widget in
TextLineEditorWidget.

    >>> from lp.app.browser.lazrjs import TextLineEditorWidget

The bare minimum that you need to provide the widget is the object that you
are editing, and the exported field that is being edited, and a title for the
edit link that is rendered as the itle of the anchor so it shows on mouse
over, and the tag that surrounds the text.

    >>> from lp.registry.interfaces.product import IProduct
    >>> product = factory.makeProduct(
    ...     name='widget', displayname='Widgets > important')
    >>> title_field = IProduct['display_name']
    >>> title = 'Edit the title'
    >>> widget = TextLineEditorWidget(
    ...     product, title_field, title, 'h1', max_width='90%',
    ...     truncate_lines=2)

The widget is rendered by executing it, it prints out the attribute
content.

    >>> print(widget())
    <h1 id="edit-display_name">
    <span class="yui3-editable_text-text ellipsis"
          style="max-width: 90%;">
        Widgets &gt; important
    </span>
    </h1>

In addition, when the logged in user can edit the value, there is a link to
the edit view that appears as well as a <script> tag that will change that
link into an AJAX control when JS is available:

    >>> ignored = login_person(product.owner)
    >>> print(widget())
    <h1 id="edit-display_name">
    <span class="yui3-editable_text-text ellipsis"
          style="max-width: 90%;">
        Widgets &gt; important
    </span>
        <a class="yui3-editable_text-trigger sprite edit action-icon"
           href="http://launchpad.test/widget/+edit"
           title="">Edit</a>
    </h1>
    <script>
    ...
    </script>


Changing the tag
****************

The id of the surrounding tag defaults to "edit-" followed by the name of the
attribute being edited.  This can be overridden if needed using the
"content_box_id" constructor argument.

    >>> span_widget = TextLineEditorWidget(
    ...     product, title_field, title, 'span', content_box_id="overridden")
    >>> login(ANONYMOUS) # To not get the script tag rendered
    >>> print(span_widget())
    <span id="overridden">...</span>


Changing the edit link
**********************

When there is a logged in user that has edit rights on the field being edited,
the edit button is shown, and has a link that takes to the user to a normal
edit page if javascript is disabled.  This link defaults to the '+edit' view
of the object being edited.  This can be overridden in two ways:
  * change the 'edit_view' parameter to be a different view
  * provide an 'edit_url' to use instead
  * provide an 'edit_title' to set the title attribute of the anchor

    >>> print(widget.edit_url)
    http://launchpad.test/widget/+edit

    >>> diff_view = TextLineEditorWidget(
    ...     product, title_field, title, 'h1', edit_view='+edit-people',
    ...     edit_title='Change the product title')
    >>> print(diff_view.edit_url)
    http://launchpad.test/widget/+edit-people
    >>> print(diff_view.edit_title)
    Change the product title
    >>> ignored = login_person(product.owner)
    >>> print(diff_view())
    <h1...
    <a class="yui3-editable_text-trigger sprite edit action-icon"
       href="http://launchpad.test/widget/+edit-people"
       title="Change the product title">...

    >>> diff_url = TextLineEditorWidget(
    ...     product, title_field, title, 'h1', edit_url='http://example.com/')
    >>> print(diff_url.edit_url)
    http://example.com/


Other nifty bits
****************

You are also able to set the default text to show if the attribute has no
value using the 'default_text' parameter.  The 'initial_value_override' is
used by the javascript widget to provide that text instead of the objects
value (of the default_text).  The width of the field can also be specified
using the 'width' parameter (please use 'em's).

For an example of these parameters, see the editor for a products programming
languages.


TextAreaEditorWidget
--------------------

This widget renders a multi-line editor.  Example uses of this widget are:
  * editing a bug's description
  * editing a merge proposal's commit message or description
  * editing a PPA's description

    >>> from lp.app.browser.lazrjs import TextAreaEditorWidget

The bare minimum that you need to provide the widget is the object that you
are editing, and the exported field that is being edited, and a title for the
edit link that is rendered as the itle of the anchor so it shows on mouse
over.

    >>> eric = factory.makePerson(name='eric')
    >>> archive = factory.makeArchive(
    ...     owner=eric, name='ppa', description='short description')
    >>> from lp.soyuz.interfaces.archive import IArchive
    >>> description = IArchive['description']
    >>> widget = TextAreaEditorWidget(archive, description, 'A title')

With no-one logged in, there are no edit buttons.

    >>> login(ANONYMOUS)
    >>> print(widget())
    <div>
      <div class="lazr-multiline-edit" id="edit-description">
        <div class="clearfix">
          <h3>A title</h3>
        </div>
        <div class="yui3-editable_text-text"><p>short description</p></div>
      </div>
    </div>

The initial text defaults to the value of the attribute, which is then passed
through two string formatter methods to obfuscate the email and then return
the text as HTML.

When the logged in user has edit permission, the edit button is shown, and
javascript is written to the page to hook up the links to show the multiline
editor.

    >>> ignored = login_person(eric)
    >>> print(widget())
    <div>
      <div class="lazr-multiline-edit" id="edit-description">
        <div class="clearfix">
          <div class="edit-controls">
            <a class="yui3-editable_text-trigger sprite edit action-icon"
               href="http://launchpad.test/~eric/+archive/ubuntu/ppa/+edit"
               title="">Edit</a>
          </div>
          <h3>A title</h3>
        </div>
        <div class="yui3-editable_text-text"><p>short description</p></div>
      </div>
      <script>...</script>
    </div>


Changing the edit link
**********************

The edit link can be changed in exactly the same way as for the
TextLineEditorWidget above.


Hiding the widget for empty fields
**********************************

Sometimes you don't want to show the widget if there is no content.  An
example of this can be found in the branch merge proposal view for editing the
description or the commit message.  This uses links when there is no content.
Ideally the interaction with the links would be encoded as part of the widget
itself, but that is an exercise left for another yak shaver.

Hiding the widget is done by appending the "hidden" CSS class to the outer
tag.

    >>> archive.description = None
    >>> from lp.services.propertycache import clear_property_cache
    >>> clear_property_cache(widget)
    >>> print(widget())
    <div>
    <div class="lazr-multiline-edit hidden" id="edit-description">
    ...

This behaviour can be overridden by setting the "hide_empty" parameter to
False.

    >>> widget = TextAreaEditorWidget(
    ...     archive, description, 'A title', hide_empty=False)
    >>> print(widget())
    <div>
    <div class="lazr-multiline-edit" id="edit-description">
    ...


Not linkifying the text
***********************

A part of the standard HTML rendering is to "linkify" links.  That is, turn
words that look like hyperlinks into anchors.  This is not always considered a
good idea as some spammers can create PPAs and link to other sites in the
descriptions.  since the barrier to create a PPA is relatively low, we
restrict the linkability of some fields.  The constructor provides a
"linkify_text" parameter that defaults to True.  Set this to False to avoid
the linkification of text.  See the IArchive['description'] editor for an
example.


InlineEditPickerWidget
----------------------

The InlineEditPickerWidget provides a simple way to create a popup selector
widget to choose items from a vocabulary.

    >>> from lp.app.browser.lazrjs import InlineEditPickerWidget

The bare minimum that you need to provide the widget is the object that you
are editing, and the exported field that is being edited, and the default
HTML representation of the field you are editing.

Since most of the things that are being chosen are entities in Launchpad, and
most of those entities have URLs, a common approach is to have the default
HTML be a link to that entity.  There is a utility function called format_link
that does the equivalent of the TALES expression 'obj/fmt:link'.

    >>> from lp.app.browser.tales import format_link
    >>> default_text = format_link(archive.owner)

The vocabulary is determined from the field passed in.  If the vocabulary is a
huge vocabulary (one that provides a search), then the picker is shown with an
entry field to allow the user to search for an item.  If the vocabulary is not
huge, the different items are shown in the normal paginated way for the user
to select.

    >>> ignore = login_person(product.owner)
    >>> owner = IProduct['owner']
    >>> widget = InlineEditPickerWidget(product, owner, default_text)
    >>> print(widget())
    <span id="edit-owner">
      <span class="yui3-activator-data-box">
        <a href="/~eric" class="sprite person">Eric</a>
      </span>
      <span>
        <a class="sprite edit action-icon lazr-btn yui3-activator-act"
          href="http://launchpad.test/widget/+edit"
          title="">Edit</a>
        <div class="yui3-activator-message-box yui3-activator-hidden"></div>
    </span> ...


Picker headings
***************

The picker has two headings that are almost always desirable to customize.
  * "header" - Shown at the top of the picker
  * "step_title" - Shown just below the green progress bar

To customize these, pass the named parameters into the constructor of the
widget.


Other nifty links
*****************

If the logged in user is in the defined vocabulary (only occurs with people
type vocabularies), a link is shown "Assign to me'.

If the field is optional, a "Remove" link is shown.  The "Remove" text is
customizable thought the "remove_button_text" parameter.


BooleanChoiceWidget
-------------------

This widget provides a simple popup with two options for the user to choose
from.

    >>> from lp.app.browser.lazrjs import BooleanChoiceWidget

As with the other widgets, this one requires a context object and a Bool type
field.  The rendering of the widget hooks up to the lazr ChoiceSource with the
standard patch plugin.

The surrounding tag is customisable, and a prefix may be given.  The prefix is
passed through to the ChoiceSource and is rendered as part of the widget, but
isn't updated when the value changes.

If the user does not have edit rights, the widget just renders the text based
on the current value of the field on the object:

    >>> login(ANONYMOUS)
    >>> from lp.registry.interfaces.person import IPerson
    >>> hide_email = IPerson['hide_email_addresses']
    >>> widget = BooleanChoiceWidget(
    ...     eric, hide_email, 'span',
    ...     false_text="Don't hide it",
    ...     true_text="Keep it secret",
    ...     prefix="My email: ")
    >>> print(widget())
    <span id="edit-hide_email_addresses">
    My email: <span class="value">Don't hide it</span>
    </span>

If the user has edit rights, an edit icon is rendered and some javascript is
rendered to hook up the widget.

    >>> ignored = login_person(eric)
    >>> print(widget())
    <span id="edit-hide_email_addresses">
    My email: <span class="value">Don't hide it</span>
      <span>
        <a class="editicon sprite edit action-icon"
           href="http://launchpad.test/~eric/+edit" title="">Edit</a>
      </span>
    </span>
    <script>
    LPJS.use('lp.app.choice', function(Y) {
    ...
    </script>


Changing the edit link
**********************

The edit link can be changed in exactly the same way as for the
TextLineEditorWidget above.


InlineMultiCheckboxWidget
-------------------

This widget is used to edit fields which are Lists or Sets. It displays the
current items in the collection when the page is rendered and provides the
ability to edit the selected items via a popup overlay. The popup has a set of
checkboxes for selecting one or more items from a vocabulary. The vocabulary
defaults to that associated with the field being edited but can be user
defined.

    >>> from lp.app.browser.lazrjs import InlineMultiCheckboxWidget

The bare minimum that you need to provide the widget is the object that you
are editing, and the exported field that is being edited, and the label to
display for the set of checkboxes.

The surrounding tag for the label and set of checkboxes are both customisable,
and a prefix may be given.  The prefix is rendered as part of the widget, but
isn't updated when the value changes.

Other customisable parameters include the popup header text (defaults to the
field title suffixed by ":"), the string to render when the field contains no
selected items (defaults to "None"), and a CSS style to add to each checkbox
node (defaults to '').

If the user does not have edit rights, the widget just renders the text based
on the current value of the field on the object:

    >>> login(ANONYMOUS)
    >>> from lp.code.interfaces.sourcepackagerecipe import (
    ...     ISourcePackageRecipe,
    ...     )
    >>> distroseries = ISourcePackageRecipe['distroseries']
    >>> recipe = factory.makeSourcePackageRecipe(
    ...     owner=eric, name=u'cake_recipe', description=u'Yummy.')
    >>> widget = InlineMultiCheckboxWidget(
    ...     recipe, distroseries, 'Recipe distro series',
    ...     header='Select distroseries:', vocabulary='BuildableDistroSeries',
    ...     label_tag='dt', items_tag='dl',
    ...     selected_items=recipe.distroseries)
    >>> print(widget())
    <span id="edit-distroseries">
      <dt>
        Recipe distro series
      </dt>
      <span class="yui3-activator-data-box">
        <dl id='edit-distroseries-items'>
    ...
      </span>
      <div class="yui3-activator-message-box yui3-activator-hidden" />
    </span>

If the user has edit rights, an edit icon is rendered and some javascript is
rendered to hook up the widget.

    >>> ignored = login_person(eric)
    >>> print(widget())
    <span id="edit-distroseries">
      <dt>
        Recipe distro series
          <a class="sprite edit action-icon lazr-btn yui3-activator-act"
             href="http://code.launchpad.test/~eric/+recipe/cake_recipe/+edit"
             id="edit-distroseries-btn"
             title="">Edit</a>
      </dt>
      <span class="yui3-activator-data-box">
        <dl id='edit-distroseries-items'>
    ...
      <div class="yui3-activator-message-box yui3-activator-hidden" />
      </span>
      <script>
      LPJS.use('lp.app.multicheckbox', function(Y) {
      ...
      </script>


Changing the edit link
**********************

The edit link can be changed in exactly the same way as for the
TextLineEditorWidget above.
