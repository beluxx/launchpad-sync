The BugTask Assignee Widget
===========================

A custom widget is used to collect the assignee for a bug task.

    >>> from lp.bugs.browser.widgets.bugtask import BugTaskAssigneeWidget

This widget was created to address a common user complaint, that it's
unnecessarily difficult to "take" a bug.

Of course, a widget is just a view on a field, so it takes a request
argument:

    >>> from lp.services.webapp.servers import LaunchpadTestRequest

and a context, which is an IBugTask.assignee field:

    >>> from lp.bugs.interfaces.bugtask import IBugTask
    >>> field = IBugTask['assignee']

Let's borrow a bugtask to use in this example:

    >>> from zope.component import getUtility
    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> bugtask = getUtility(IBugTaskSet).get(2)

    >>> ORIGINAL_ASSIGNEE = bugtask.assignee

    >>> context = field.bind(bugtask)

IInputWidget instead of ISimpleInputWidget
------------------------------------------

This widget implements IInputWidget, instead of ISimpleInputWidget,
because ISimpleInputWidget is messy and complex. Each section below
that demonstrates the kind of assignments that can be done with this
widget will test each method of the IInputWidget.

Taking a bug
------------

To take a bug, you can choose the "me" radio button. First, let's
pretend to be logged in as Foo Bar:

    >>> from lp.testing import login
    >>> login("foo.bar@canonical.com")

Then, let's simulate selecting the "me" radio button, to assign the
bug to the currently logged-in user:

    >>> request = LaunchpadTestRequest(form={
    ...     'field.assignee.option': 'field.assignee.assign_to_me'})
    >>> widget = BugTaskAssigneeWidget(context, None, request)

Currently, the bugtask is not assigned to the current user:

    >>> widget.assignedToCurrentUser()
    False

But it is assigned to another user:

    >>> widget.assignedToAnotherUser()
    True

    >>> widget.selectedRadioButton() == widget.assign_to_me
    True

    >>> print(widget.getAssigneeDisplayValue())
    Mark Shuttleworth (mark)

The widget has input:

    >>> widget.hasInput()
    True

The widget has valid input:

    >>> widget.validate()
    >>> widget.hasValidInput()
    True

The input value is the current user:

    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> widget.getInputValue() == getUtility(ILaunchBag).user
    True

Let's apply the changes:

    >>> print(bugtask.assignee.displayname)
    Mark Shuttleworth
    >>> widget.applyChanges(bugtask)
    True
    >>> print(bugtask.assignee.displayname)
    Foo Bar

Finally, let's rebind the widget's context to the updated context, as
its current context will be out of sync with the new value:

    >>> context = field.bind(bugtask)
    >>> widget.context = context

Assigning the bug to someone else
---------------------------------

To assign the bug to someone else, select the "assign_to" radio
option.

This time we use a different prefix than the standard 'field'.

    >>> request.form = {'foo.assignee.option': 'foo.assignee.assign_to'}

In order to tell the widget about the new prefix, we need to call
setPrefix.

    >>> widget.name
    'field.assignee'
    >>> widget.setPrefix('foo')
    >>> print(widget.name)
    foo.assignee

The chooser widget got its name updated as well.

    >>> print(widget.assignee_chooser_widget.name)
    foo.assignee
    >>> print(widget.assignee_chooser_widget.onKeyPress)
    selectWidget('foo.assignee.assign_to', event)

If this option is selected, but no value is entered in
"field.assignee", validation will fail:

    >>> widget.validate()
    Traceback (most recent call last):
    ...
    zope.formlib.interfaces.WidgetInputError: ...

Likewise, if a non-existent field.assignee is provided, the validation
will fail:

    >>> request.form['foo.assignee'] = 'name'
    >>> widget.validate()
    Traceback (most recent call last):
    ...
    zope.formlib.interfaces.WidgetInputError: ...

Note, in this case, that the widget will properly select the
"assign_to" radio button:

    >>> widget.selectedRadioButton() == widget.assign_to
    True

Let's supply a field.assignee so that the widget validation succeeds:

    >>> request.form['foo.assignee'] = 'name12'
    >>> widget.validate()

Now, the bugtask is assigned to the current user:

    >>> widget.assignedToCurrentUser()
    True

Which means it's not assigned to another user:

    >>> widget.assignedToAnotherUser()
    False

    >>> print(widget.getAssigneeDisplayValue())
    Foo Bar (name16)

The widget has input:

    >>> widget.hasInput()
    True

The widget has valid input:

    >>> widget.hasValidInput()
    True

The input value is the user with .name == 'name12':

    >>> widget.getInputValue().name == 'name12'
    True

Let's apply the changes:

    >>> bugtask.assignee.id == 16
    True
    >>> widget.applyChanges(bugtask)
    True
    >>> bugtask.assignee.id == 12
    True

Again, let's rebind the widget's context to the updated context:

    >>> context = field.bind(bugtask)
    >>> widget.context = context

The "assigned_to" button will now be selected:

    >>> request.form = {}
    >>> widget.selectedRadioButton() == widget.assigned_to
    True

If we were to resubmit the form, without making any changes, the
assignee would remain unchanged, so the input value is effectively the
value of the current assignee:

    >>> request.form = {'foo.assignee.option' : 'foo.assignee.assigned_to'}
    >>> widget.getInputValue().name == 'name12'
    True

Assigning the bug to no-one
---------------------------

Lastly, a bug can be put "up for grabs" again by selecting the
"assign_to_nobody" option.

    >>> widget.setPrefix('field')
    >>> request.form = {
    ...     'field.assignee.option': 'field.assignee.assign_to_nobody'}

    >>> widget.validate()

The widget has input:

    >>> widget.hasInput()
    True

The widget has valid input:

    >>> widget.hasValidInput()
    True

The input value is None:

    >>> widget.getInputValue() is None
    True

Let's apply the changes:

    >>> bugtask.assignee.id == 12
    True
    >>> widget.applyChanges(bugtask)
    True
    >>> bugtask.assignee is None
    True

Again, rebind to make sure the widget's context is using the
updated context:

    >>> context = field.bind(bugtask)
    >>> widget.context = context

Now, the bugtask is neither assigned to the current user:

    >>> widget.assignedToCurrentUser()
    False

Nor to another:

    >>> widget.assignedToAnotherUser()
    False

    >>> widget.selectedRadioButton() == widget.assign_to_nobody
    True

    >>> widget.getAssigneeDisplayValue() is None
    True

All that's left now is a bit of cleanup:

    >>> bugtask.transitionToAssignee(ORIGINAL_ASSIGNEE)
