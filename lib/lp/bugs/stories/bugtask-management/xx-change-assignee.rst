Changing bug assignment
=======================

A bug is unassigned by choosing the "Assigned to" -> "Nobody" option.

    >>> admin_browser.open("http://launchpad.test/firefox/+bug/1")

Bug 1 is currently assigned to someone.

    >>> assignee_control = admin_browser.getControl(
    ...     name="firefox.assignee.option", index=0)
    >>> assignee_control.value == ["firefox.assignee.assigned_to"]
    True

But we can change it to be assigned to nobody.

    >>> assignee_control.value = ["firefox.assignee.assign_to_nobody"]

    >>> admin_browser.getControl("Save Changes", index=0).click()

    >>> admin_browser.getControl(
    ...     name="firefox.assignee.option", index=0).value
    ['firefox.assignee.assign_to_nobody']


Bug assignment to non-contributors
==================================

When attempting to assign a bug to a user who isn't an established bug
contributor (they have no bugs currently assigned to them) the user is
warned immediately after the assignment, so that they can change their
choice if it was mistaken.

    >>> admin_browser.open("http://launchpad.test/firefox/+bug/1")
    >>> assignee_control = admin_browser.getControl(
    ...     name="firefox.assignee.option", index=0)
    >>> assignee_control.value = ["firefox.assignee.assign_to"]
    >>> assign_to_control = admin_browser.getControl(
    ...     name="firefox.assignee", index=0)
    >>> assign_to_control.value = "cprov"
    >>> admin_browser.getControl("Save Changes", index=0).click()
    >>> print(extract_text(
    ...     first_tag_by_class(admin_browser.contents, 'warning message')))
    Celso Providelo
    did not previously have any assigned bugs in
    Mozilla Firefox.
    If this bug was assigned by mistake,
    you may change the assignment.

If the new assignee does have bugs assigned, but not in the relevant pillar,
the user will be warned too.

    >>> admin_browser.open("http://bugs.launchpad.test/jokosher/+bug/11")
    >>> assignee_control = admin_browser.getControl(
    ...     name="jokosher.assignee.option", index=0)
    >>> assignee_control.value = ["jokosher.assignee.assign_to"]
    >>> assign_to_control = admin_browser.getControl(
    ...     name="jokosher.assignee", index=0)
    >>> assign_to_control.value = "cprov"
    >>> admin_browser.getControl("Save Changes", index=0).click()
    >>> print(extract_text(
    ...     first_tag_by_class(admin_browser.contents, 'warning message')))
    Celso Providelo
    did not previously have any assigned bugs in Jokosher.
    If this bug was assigned by mistake, you may change the assignment.

When assigning a bug to oneself, though, the warning message is suppreseed.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.testing import login, logout

    >>> login('no-priv@canonical.com')
    >>> no_priv = getUtility(IPersonSet).getByName('no-priv')
    >>> no_priv.isBugContributor(user=no_priv)
    False

    >>> logout()

    >>> user_browser.open("http://bugs.launchpad.test/jokosher/+bug/11")
    >>> assignee_control = user_browser.getControl(
    ...     name="jokosher.assignee.option", index=0)
    >>> assignee_control.value = ["jokosher.assignee.assign_to_me"]
    >>> user_browser.getControl("Save Changes", index=0).click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/jokosher/+bug/11
    >>> print(first_tag_by_class(
    ...     user_browser.contents, 'warning message'))
    None


Bug task assignment by regular users
====================================

Regular users can only set themselves and their teams as assignees if
there is a bug supervisor established for a project.

To demonstrate, let's first set a bug supervisor for the jokosher
project used in these tests.

    >>> login('foo.bar@canonical.com')
    >>> from lp.registry.interfaces.product import IProductSet
    >>> jokosher = getUtility(IProductSet).getByName('jokosher')
    >>> foobar = getUtility(IPersonSet).getByName('name16')
    >>> jokosher.bug_supervisor = foobar

To avoid any confusion, the option to assign somebody else is only
shown if the user has sufficient privileges to assign anybody or if
the user is a member of at least one team. no-priv is no a member of
any team and hence does no see the option to asign somebody else.

    >>> no_priv.teams_participated_in.count()
    0

    >>> logout()
    >>> user_browser.open("http://bugs.launchpad.test/jokosher/+bug/11")
    >>> assignee_control = user_browser.getControl(
    ...     name="jokosher.assignee.option", index=0)
    >>> assignee_control.value = ["jokosher.assignee.assign_to"]
    Traceback (most recent call last):
    ...
    ValueError: Option ...'jokosher.assignee.assign_to' not found ...
    >>> user_browser.getControl(name="jokosher.assignee", index=0)
    Traceback (most recent call last):
    ...
    LookupError: name ...'jokosher.assignee'
    ...

Once no_priv is a member of a team, the option is shown.

    >>> login('no-priv@canonical.com')
    >>> no_privs_team_name = factory.makeTeam(owner=no_priv).name
    >>> logout()
    >>> user_browser.open("http://bugs.launchpad.test/jokosher/+bug/11")
    >>> assignee_control = user_browser.getControl(
    ...     name="jokosher.assignee.option", index=0)
    >>> assignee_control.value = ["jokosher.assignee.assign_to"]
    >>> assign_to_control = user_browser.getControl(
    ...     name="jokosher.assignee", index=0)
    >>> assign_to_control.value = no_privs_team_name
    >>> user_browser.getControl("Save Changes", index=0).click()
    >>> print_errors(user_browser.contents)

But if they try to set other persons or teams, they get an error message.

    >>> user_browser.open("http://bugs.launchpad.test/jokosher/+bug/11")
    >>> assignee_control = user_browser.getControl(
    ...     name="jokosher.assignee.option", index=0)
    >>> assignee_control.value = ["jokosher.assignee.assign_to"]
    >>> assign_to_control = user_browser.getControl(
    ...     name="jokosher.assignee", index=0)
    >>> assign_to_control.value = "name12"
    >>> user_browser.getControl("Save Changes", index=0).click()
    >>> print_errors(user_browser.contents)
    There is 1 error in the data you entered. Please fix it and try again.
    (Find…)
    Constraint not satisfied
