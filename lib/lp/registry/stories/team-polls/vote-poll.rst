Voting on polls
===============

Foo Bar (a member of the ubuntu-team) wants to vote on the 'never-closes'
poll, which is a poll with secret votes, which means they'll get a token
that they must use to see/change their vote afterwards.

    >>> browser = setupBrowser(auth='Basic foo.bar@canonical.com:test')
    >>> browser.open('http://launchpad.test/~ubuntu-team/+polls')
    >>> browser.getLink('A random poll that never closes').click()
    >>> browser.url
    'http://launchpad.test/~ubuntu-team/+poll/never-closes/+vote'

    >>> print(find_tag_by_id(browser.contents, 'your-vote').decode_contents())
    <BLANKLINE>
    ...
    <h2>Your current vote</h2>
    ...You have not yet voted in this poll...
    <h2>Vote now</h2>
    ...

    >>> browser.getControl('None of these options').selected = True
    >>> browser.getControl('Continue').click()

    >>> browser.url
    'http://launchpad.test/~ubuntu-team/+poll/never-closes/+vote'

    >>> tags = find_tags_by_class(browser.contents, "informational message")
    >>> for tag in tags:
    ...     print(tag.decode_contents())
    Your vote has been recorded. If you want to view or change it later you
    must write down this key: ...

    >>> print(find_tag_by_id(browser.contents, 'your-vote').decode_contents())
    <BLANKLINE>
    ...
    <h2>Your current vote</h2>
    ...Your current vote is for <b> none of the options. </b>...
    ...

Foo Bar will now vote on a poll with public votes.

    >>> browser.open('http://launchpad.test/~ubuntu-team/+polls')
    >>> browser.getLink('A public poll that never closes').click()
    >>> browser.url
    'http://launchpad.test/~ubuntu-team/+poll/never-closes4/+vote'

    >>> print(find_tag_by_id(browser.contents, 'your-vote').decode_contents())
    <BLANKLINE>
    ...
    <h2>Your current vote</h2>
    ...You have not yet voted in this poll...
    <h2>Vote now</h2>
    ...

    >>> browser.getControl('OptionB').selected = True
    >>> browser.getControl('Continue').click()

    >>> browser.url
    'http://launchpad.test/~ubuntu-team/+poll/never-closes4/+vote'

    >>> tags = find_tags_by_class(browser.contents, "informational message")
    >>> for tag in tags:
    ...     print(tag.decode_contents())
    Your vote was stored successfully. You can come back to this page at any
    time before this poll closes to view or change your vote, if you want.

    >>> print(find_tag_by_id(browser.contents, 'your-vote').decode_contents())
    <BLANKLINE>
    ...
    <h2>Your current vote</h2>
    ...Your current vote is for <b>OptionB</b>...
    ...


For convenience we provide an option for when the user doesn't want to vote
yet.

    >>> team_admin_browser = setupBrowser(
    ...     auth='Basic jeff.waugh@ubuntulinux.com:test')
    >>> team_admin_browser.open(
    ...   'http://launchpad.test/~ubuntu-team/+poll/never-closes/+vote')
    >>> 'You have not yet voted in this poll.' in team_admin_browser.contents
    True

    >>> team_admin_browser.getControl(name='newoption').value = ["donotvote"]
    >>> team_admin_browser.getControl(name='continue').click()

    >>> contents = team_admin_browser.contents
    >>> for tag in find_tags_by_class(contents, "informational message"):
    ...     print(tag.decode_contents())
    You chose not to vote yet.

    >>> print(find_tag_by_id(contents, 'your-vote').decode_contents())
    <BLANKLINE>
    ...
    <h2>Your current vote</h2>
    ...You have not yet voted in this poll...
    ...


No permission to vote
---------------------

Only members of a given team can vote on that team's polls. Other users can't,
even if they guess the URL for the voting page.

    >>> non_member_browser = setupBrowser(
    ...     auth='Basic test@canonical.com:test')
    >>> non_member_browser.open(
    ...     'http://launchpad.test/~ubuntu-team/+poll/never-closes/+vote')
    >>> for tag in find_tags_by_class(
    ...     non_member_browser.contents, "informational message"):
    ...     print(tag.decode_contents())
    You can’t vote in this poll because you’re not a member of Ubuntu Team.


Closed polls
------------

It's not possible to vote on closed polls, even if we manually craft the URL.

    >>> team_admin_browser.open(
    ...     'http://launchpad.test/~ubuntu-team/+poll/leader-2004')
    >>> print(find_tag_by_id(
    ...     team_admin_browser.contents, 'maincontent').decode_contents())
    <BLANKLINE>
    ...
    <h2>Voting has closed</h2>
    ...

    >>> team_admin_browser.open(
    ...     'http://launchpad.test/~ubuntu-team/+poll/leader-2004/+vote')
    >>> print(find_tag_by_id(
    ...     team_admin_browser.contents, 'maincontent').decode_contents())
    <BLANKLINE>
    ...
    <p class="informational message">
          This poll is already closed.
        </p>
    ...

    >>> team_admin_browser.getControl(name='continue')
    Traceback (most recent call last):
    ...
    LookupError: name ...'continue'
    ...

The same is true for condorcet polls too.

    >>> team_admin_browser.open(
    ...     'http://launchpad.test/~ubuntu-team/+poll/director-2004')
    >>> print(find_tag_by_id(
    ...     team_admin_browser.contents, 'maincontent').decode_contents())
    <BLANKLINE>
    ...
    <h2>Voting has closed</h2>
    ...

    >>> team_admin_browser.getControl(name='continue')
    Traceback (most recent call last):
    ...
    LookupError: name ...'continue'
    ...

    >>> team_admin_browser.open(
    ...     'http://launchpad.test/~ubuntu-team/+poll/director-2004/+vote')
    >>> print_feedback_messages(team_admin_browser.contents)
    This poll is already closed.
