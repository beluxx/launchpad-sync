Widgets for Displaying a Bug Task
=================================

There are some widgets which helps displaying certain attributes of a
bug task. Using these move out some logic for the page template, and it
helps creating pages where some attributes are editable only under
certain conditions.

AssigneeDisplayWidget
---------------------

This widget is used to display the assignee of a bug task. It displays
the assignee's browser name, with a link to their person page, and with a
person icon in front of the name.

    >>> from lp.bugs.browser.widgets.bugtask import AssigneeDisplayWidget
    >>> from lp.bugs.interfaces.bug import IBugSet, IBugTask
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> firefox_bugtask = bug_one.bugtasks[0]
    >>> print(firefox_bugtask.assignee.displayname)
    Mark Shuttleworth

    >>> assignee_field = IBugTask['assignee'].bind(firefox_bugtask)
    >>> assignee_widget = AssigneeDisplayWidget(assignee_field, None, None)
    >>> print(assignee_widget())
    <a href="http://.../~mark"><img
        style="padding-bottom: 2px" alt="" src="/@@/person" />
      Mark Shuttleworth</a>

If we would want to display a different value than the real assignee,
we can use setRenderedValue()

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> foo_bar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
    >>> assignee_widget.setRenderedValue(foo_bar)
    >>> print(assignee_widget())
    <a href="http://.../~name16"><img
        style="padding-bottom: 2px" alt="" src="/@@/person" />
      Foo Bar</a>

If the assignee is None, 'not assigned' will be displayed:

    >>> firefox_ubuntu_bugtask = bug_one.bugtasks[1]
    >>> assignee_field = IBugTask['assignee'].bind(firefox_ubuntu_bugtask)
    >>> assignee_widget = AssigneeDisplayWidget(assignee_field, None, None)
    >>> print(assignee_widget())
    <i>not assigned</i>

If it's a remote bug task, where the information is pulled from a bug
watch, 'unknown' is displayed, since we don't support pulling the
assignee yet:

    >>> bug_nine = getUtility(IBugSet).get(9)
    >>> thunderbird_bugtask = bug_nine.bugtasks[0]
    >>> thunderbird_bugtask.pillar.official_malone
    False
    >>> assignee_field = IBugTask['assignee'].bind(thunderbird_bugtask)
    >>> assignee_widget = AssigneeDisplayWidget(assignee_field, None, None)
    >>> print(assignee_widget())
    <i>unknown</i>

DBItemDisplayWidget
-------------------

This widget is used for displaying DBItem attributes of the bug task,
like status and importance. It displays the title of the item
in a span with the appropriate css class:

    >>> from lp.bugs.browser.widgets.bugtask import DBItemDisplayWidget
    >>> firefox_bugtask.status.title
    'New'
    >>> status_field = IBugTask['status'].bind(firefox_bugtask)
    >>> status_widget = DBItemDisplayWidget(status_field, None, None)
    >>> print(status_widget())
    <span class="statusNEW">New</span>

If the value is None, a dash is displayed:

    >>> test_task = bug_nine.bugtasks[1]
    >>> test_task.assignee is None
    True
    >>> assignee_field = IBugTask['assignee'].bind(test_task)
    >>> assignee_widget = DBItemDisplayWidget(assignee_field, None, None)
    >>> print(assignee_widget())
    <span>&mdash;</span>

We can set a specific value to be displayed using setRenderedValue():

    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> status_widget.setRenderedValue(BugTaskStatus.CONFIRMED)
    >>> print(status_widget())
    <span class="statusCONFIRMED">Confirmed</span>
