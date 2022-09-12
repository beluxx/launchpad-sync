Editing a poll
==============

All attributes of a poll can be changed as long as the poll has not opened
yet.

First we create a new poll to use throughout this test.

    >>> login("jeff.waugh@ubuntulinux.com")
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> factory.makePoll(
    ...     getUtility(IPersonSet).getByName("ubuntu-team"),
    ...     "dpl-2080",
    ...     "dpl-2080",
    ...     "dpl-2080",
    ... )
    <lp.registry.model.poll.Poll...
    >>> logout()

Now we'll try to change its name to something that is already in use.

    >>> team_admin_browser = setupBrowser(
    ...     auth="Basic jeff.waugh@ubuntulinux.com:test"
    ... )
    >>> team_admin_browser.open(
    ...     "http://launchpad.test/~ubuntu-team/+poll/dpl-2080"
    ... )
    >>> team_admin_browser.getLink("Change details").click()

    >>> team_admin_browser.url
    'http://launchpad.test/~ubuntu-team/+poll/dpl-2080/+edit'

    >>> team_admin_browser.getControl(
    ...     "The unique name of this poll"
    ... ).value = "never-closes"
    >>> team_admin_browser.getControl("Save").click()

    >>> print_feedback_messages(team_admin_browser.contents)
    There is 1 error.
    ...never-closes is already in use by another poll in this team.

Entering an end date that precedes the start date returns a nice error
message.

    >>> team_admin_browser.getControl(
    ...     "The unique name of this poll"
    ... ).value = "dpl-2080"
    >>> team_admin_browser.getControl(
    ...     name="field.dateopens"
    ... ).value = "3000-11-01 00:00:00+00:00"
    >>> team_admin_browser.getControl(
    ...     name="field.datecloses"
    ... ).value = "3000-01-01 00:00:00+00:00"
    >>> team_admin_browser.getControl("Save").click()

    >>> print_feedback_messages(team_admin_browser.contents)
    There is 1 error.
    A poll cannot close at the time (or before) it opens.

We successfully change the polls name

    >>> team_admin_browser.getControl(
    ...     "The unique name of this poll"
    ... ).value = "election-3000"
    >>> team_admin_browser.getControl(
    ...     name="field.dateopens"
    ... ).value = "3000-01-01 00:00:00+00:00"
    >>> team_admin_browser.getControl(
    ...     name="field.datecloses"
    ... ).value = "3000-11-01 00:00:00+00:00"
    >>> team_admin_browser.getControl("Save").click()

    >>> team_admin_browser.url
    'http://launchpad.test/~ubuntu-team/+poll/election-3000'

Trying to edit a poll that's already open isn't possible.

    >>> team_admin_browser.open("http://launchpad.test/~ubuntu-team/")
    >>> team_admin_browser.getLink("Show polls").click()
    >>> team_admin_browser.url
    'http://launchpad.test/~ubuntu-team/+polls'

    >>> team_admin_browser.getLink("A random poll that never closes").click()
    >>> team_admin_browser.url
    'http://launchpad.test/~ubuntu-team/+poll/never-closes/+vote'

    >>> team_admin_browser.open(
    ...     "http://launchpad.test/~ubuntu-team/+poll/never-closes/+edit"
    ... )
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(team_admin_browser.contents, "not-editable")
    ...     )
    ... )
    This poll can't be edited...

It's also not possible to edit a poll that's already closed.

    >>> team_admin_browser.open("http://launchpad.test/~ubuntu-team/")
    >>> team_admin_browser.getLink("Show polls").click()
    >>> team_admin_browser.url
    'http://launchpad.test/~ubuntu-team/+polls'

    >>> team_admin_browser.getLink("2004 Director's Elections").click()
    >>> team_admin_browser.url
    'http://launchpad.test/~ubuntu-team/+poll/director-2004'

    >>> "Voting has closed" in team_admin_browser.contents
    True

    >>> team_admin_browser.getLink("Change details").click()
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(team_admin_browser.contents, "not-editable")
    ...     )
    ... )
    This poll can't be edited...
