Poll views
----------

The polls portlet shows the state of current polls, and links to past
polls.

    >>> from lp.testing.pages import extract_text
    >>> from datetime import timedelta

    >>> user = factory.makePerson()
    >>> team = factory.makeTeam(name='team')
    >>> owner = team.teamowner

    >>> def create_team_view(team, name=None, principal=None):
    ...     # XRDS inheritance requires a lot of setup.
    ...     path_info = '/~%s' % team.name
    ...     server_url = 'http://launchpad.test'
    ...     view = create_view(
    ...         team, name=name, principal=principal,
    ...         server_url=server_url, path_info=path_info)
    ...     view.initialize()
    ...     return view

The portlet does not render any markup when there are no polls...

    >>> ignored = login_person(user)
    >>> view = create_team_view(team, name='+portlet-polls', principal=user)
    >>> view.has_current_polls
    False

    >>> view.should_show_polls_portlet
    False

    >>> print(extract_text(view.render()))
    <BLANKLINE>

Unless the user is a team owner.

    >>> ignored = login_person(owner)
    >>> view = create_team_view(team, name='+portlet-polls', principal=owner)
    >>> view.has_current_polls
    False

    >>> view.should_show_polls_portlet
    True

    >>> print(extract_text(view.render()))
    Polls
    No current polls.
    Show polls
    Create a poll

The portlet shows a link to polls to all users when there is a poll, but it
has not opened.

    >>> from lp.registry.interfaces.poll import IPollSubset, PollSecrecy
    >>> from lp.services.utils import utc_now

    >>> open_date = utc_now() + timedelta(hours=6)
    >>> close_date = open_date + timedelta(weeks=1)
    >>> poll_subset = IPollSubset(team)
    >>> poll = poll_subset.new(
    ...     u'name', u'title', u'proposition', open_date, close_date,
    ...     PollSecrecy.OPEN, False)

    >>> ignored = login_person(user)
    >>> view = create_team_view(team, name='+portlet-polls', principal=user)
    >>> view.has_current_polls
    True

    >>> view.should_show_polls_portlet
    True

    >>> print(extract_text(view.render()))
    Polls
    Show polls

The portlet shows more details to the poll owner.

    >>> ignored = login_person(owner)
    >>> view = create_team_view(team, name='+portlet-polls', principal=owner)
    >>> view.has_current_polls
    True

    >>> view.should_show_polls_portlet
    True

    >>> print(extract_text(view.render()))
    Polls
    title - opens in 5 hours
    Show polls
    Create a poll

Current polls are listed in the portlet, the only difference between a user
and an owner is the owner has a link to create more polls.

    >>> poll.dateopens = open_date - timedelta(weeks=2)

    >>> ignored = login_person(user)
    >>> view = create_team_view(team, name='+portlet-polls', principal=user)
    >>> print(extract_text(view.render()))
    Polls
    title - closes on ...
    You have 7 days left to vote in this poll.
    Show polls

    >>> ignored = login_person(owner)
    >>> view = create_team_view(team, name='+portlet-polls', principal=owner)
    >>> print(extract_text(view.render()))
    Polls
    title - closes on ...
    You have 7 days left to vote in this poll.
    Show polls
    Create a poll

When all the polls are closed, the portlet states the case and has a link to
see the polls.

    >>> poll.datecloses = close_date - timedelta(weeks=2)

    >>> ignored = login_person(user)
    >>> view = create_team_view(team, name='+portlet-polls', principal=user)
    >>> print(extract_text(view.render()))
    Polls
    No current polls.
    Show polls

    >>> ignored = login_person(owner)
    >>> view = create_team_view(team, name='+portlet-polls', principal=owner)
    >>> print(extract_text(view.render()))
    Polls
    No current polls.
    Show polls
    Create a poll
