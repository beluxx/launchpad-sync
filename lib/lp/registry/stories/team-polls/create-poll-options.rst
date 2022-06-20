Poll options
============

A poll can have any number of options, but these must be created
before the poll has opened.

First we create a new poll to use throughout this test.

    >>> login('jeff.waugh@ubuntulinux.com')
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> factory.makePoll(getUtility(IPersonSet).getByName('ubuntu-team'),
    ...                  u'dpl-2080', u'dpl-2080', u'dpl-2080')
    <lp.registry.model.poll.Poll...
    >>> logout()

Our poll is not yet open, so new options can be added to it.

    >>> team_admin_browser = setupBrowser(
    ...     auth='Basic jeff.waugh@ubuntulinux.com:test')
    >>> team_admin_browser.open(
    ...     'http://launchpad.test/~ubuntu-team/+poll/dpl-2080')
    >>> team_admin_browser.getLink('Add new option').click()
    >>> team_admin_browser.url
    'http://launchpad.test/~ubuntu-team/+poll/dpl-2080/+newoption'

    >>> bill_name = (
    ...     'bill-amazingly-huge-middle-name-almost-impossible-to-read-'
    ...     'graham')
    >>> team_admin_browser.getControl('Name').value = bill_name
    >>> team_admin_browser.getControl('Title').value = 'Bill Graham'
    >>> team_admin_browser.getControl('Create').click()

After adding an options we're taken back to the poll's home page.

    >>> team_admin_browser.url
    'http://launchpad.test/~ubuntu-team/+poll/dpl-2080'

And here we see the option listed as one of the active options for this
poll.

    >>> print(extract_text(
    ...     find_tag_by_id(team_admin_browser.contents, 'options')))
    Name        Title           Active
    bill...     Bill Graham     Yes

If we try to add a new option without providing a title, we'll get an error
message because the title is required.

    >>> team_admin_browser.getLink('Add new option').click()
    >>> team_admin_browser.url
    'http://launchpad.test/~ubuntu-team/+poll/dpl-2080/+newoption'

    >>> will_name = (
    ...     'will-amazingly-huge-middle-name-almost-impossible-to-read-'
    ...     'graham')
    >>> team_admin_browser.getControl('Name').value = will_name
    >>> team_admin_browser.getControl('Title').value = ''
    >>> team_admin_browser.getControl('Create').click()

    >>> print_feedback_messages(team_admin_browser.contents)
    There is 1 error.
    Required input is missing.

If we try to add a new option with the same name of a existing option, we
should get a nice error message

    >>> team_admin_browser.getControl('Name').value = bill_name
    >>> team_admin_browser.getControl('Title').value = 'Bill Again'
    >>> team_admin_browser.getControl('Create').click()

    >>> print_feedback_messages(team_admin_browser.contents)
    There is 1 error.
    ...is already in use by another option in this poll.

It's not possible to add/edit a poll option after a poll is open or closed.
That's only possible when the poll is not yet open.

    >>> team_admin_browser.open(
    ...     'http://launchpad.test/~ubuntu-team/+poll/director-2004/'
    ...     '+newoption')

    >>> print_feedback_messages(team_admin_browser.contents)
    You can’t add new options because the poll is already closed.

    >>> team_admin_browser.open(
    ...     'http://launchpad.test/~ubuntu-team/+poll/never-closes/'
    ...     '+newoption')
    >>> print_feedback_messages(team_admin_browser.contents)
    You can’t add new options because the poll is already open.
