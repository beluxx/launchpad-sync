Propose/add your teams as member of another one
===============================================

Any team administrator is allowed to propose/add (depending on the
membership policy) their teams as members of another team.

This is done from the +add-my-teams page, which is linked from a team's
home page.

    >>> browser = setupBrowser(auth="Basic colin.watson@ubuntulinux.com:test")
    >>> browser.open("http://launchpad.test/~name21")
    >>> browser.getLink("Add one of my teams").click()
    >>> browser.title
    'Propose/add one of your teams to another one...

For moderated teams, it's only possible to propose another team as a member.
The proposal will have to be reviewed by a team administrator.

    >>> print(extract_text(find_tag_by_id(browser.contents, "candidates")))
    This is a moderated team, so one of its administrators will have
    to review any memberships you propose.
    GuadaMen
    Ubuntu Security Team
    Ubuntu Team
    or Cancel

We'll now propose Ubuntu Team as a member of the Hoary Gnome Team (name21).

    >>> browser.open("http://launchpad.test/~name21")
    >>> link = browser.getLink("Add one of my teams")
    >>> link.click()
    >>> browser.getControl(name="field.teams").value = ["ubuntu-team"]
    >>> browser.getControl("Continue").click()
    >>> browser.title
    'Hoary Gnome Team in Launchpad'
    >>> print_feedback_messages(browser.contents)
    Ubuntu Team has been proposed to this team.
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "recently-proposed")
    ...     )
    ... )
    Pending approval
    Ubuntu Team...

If the team is already invited, the invitation will be accepted instead
of trying to propose the membership, which is an invalid status change.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from storm.store import Store
    >>> login("no-priv@canonical.com")
    >>> inviting_owner = factory.makePerson(email="inviter@example.com")
    >>> login("inviter@example.com")
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> super_team = factory.makeTeam(name="super-team", owner=inviting_owner)
    >>> sub_team = factory.makeTeam(name="sub-team", owner=no_priv)
    >>> print(super_team.addMember(sub_team, inviting_owner))
    (True, <DBItem TeamMembershipStatus.INVITED...)
    >>> Store.of(sub_team).flush()
    >>> logout()
    >>> user_browser.open("http://launchpad.test/~super-team/+add-my-teams")
    >>> user_browser.getControl(name="field.teams").value = ["sub-team"]
    >>> user_browser.getControl("Continue").click()
    >>> print(user_browser.title)
    Super Team in Launchpad
    >>> print_feedback_messages(user_browser.contents)
    Sub Team has been added to this team because of an existing invite.
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(user_browser.contents, "recently-approved")
    ...     )
    ... )
    Latest members
    Sub Team

If it were an OPEN team, we'd be able to directly add any of our teams as
members.

    >>> admin_browser.open("http://launchpad.test/~name21/+edit")
    >>> admin_browser.getControl(
    ...     name="field.membership_policy"
    ... ).displayValue = ["Open Team"]
    >>> admin_browser.getControl("Save").click()
    >>> admin_browser.title
    'Hoary Gnome Team in Launchpad'

    >>> browser.open("http://launchpad.test/~name21/+add-my-teams")
    >>> browser.getControl(name="field.teams").value = ["ubuntu-team"]
    >>> browser.getControl("Continue").click()
    >>> browser.title
    'Hoary Gnome Team in Launchpad'
    >>> print_feedback_messages(browser.contents)
    Ubuntu Team has been added to this team.
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "recently-approved")
    ...     )
    ... )
    Latest members
    Ubuntu Team...

In the case of restricted teams, though, there is no way to propose any of
your teams as members.

    >>> admin_browser.open("http://launchpad.test/~ubuntu-team/+edit")
    >>> admin_browser.getControl(
    ...     name="field.membership_policy"
    ... ).displayValue = ["Restricted Team"]
    >>> admin_browser.getControl("Save").click()
    >>> admin_browser.title
    'Ubuntu Team in Launchpad'

    >>> browser.open("http://launchpad.test/~ubuntu-team")
    >>> browser.getLink("Add one of my teams")
    Traceback (most recent call last):
     ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> browser.open("http://launchpad.test/~ubuntu-team/+add-my-teams")
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "candidates"),
    ...         formatter="html",
    ...     )
    ... )
    This is a restricted team
    New members can not be proposed&mdash;they can only be added by one
    of the team's administrators.

The page is restricted to logged in users.

    >>> anon_browser.open("http://launchpad.test/~ubuntu-team/+add-my-teams")
    Traceback (most recent call last):
    zope.security.interfaces.Unauthorized: ...

You also can't propose a team to itself. Here although Colin Watson is
usually allowed to propose Guadamen in other team, it doesn't appear in
the list when proposing a team for the Guadamen team. Likewise Mailing
List Experts isn't shown because the Launchpad Administrators are a
member of Mailing List Experts.  Adding Mailing List Experts would
create a cycle.

    >>> browser.open("http://launchpad.test/~guadamen/+add-my-teams")
    >>> browser.getControl(name="field.teams").options
    ['ubuntu-security']

Teams that are already member of the team can't be proposed or added.
For example, Ubuntu Team is not in the list of choices
anymore of the Hoary Gnome Team:

    >>> admin_browser.open("http://launchpad.test/~name21/+edit")
    >>> admin_browser.getControl(
    ...     name="field.membership_policy"
    ... ).displayValue = ["Open"]
    >>> admin_browser.getControl("Save").click()

    >>> browser.open("http://launchpad.test/~name21/+members")
    >>> browser.open("http://launchpad.test/~name21/+add-my-teams")
    >>> browser.getControl(name="field.teams").options
    ['guadamen', 'ubuntu-security']
    >>> browser.getControl(name="field.teams").value = [
    ...     "guadamen",
    ...     "ubuntu-security",
    ... ]
    >>> browser.getControl("Continue").click()
    >>> print_feedback_messages(browser.contents)
    GuadaMen and Ubuntu Security Team have been added to this team.

And when no teams can be added, a message is displayed:

    >>> browser.open("http://launchpad.test/~name21/+add-my-teams")
    >>> print(extract_text(find_tag_by_id(browser.contents, "no-candidates")))
    None of the teams you administer can be added to this team.
