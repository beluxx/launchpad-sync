Poll preconditions
==================

There's some preconditions that we need to meet to vote in polls and remove
options from them.  Not meeting these preconditions is a programming error and
should be treated as such.

    >>> from zope.component import getUtility
    >>> from datetime import timedelta
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.poll import IPollSet

    >>> ubuntu_team = getUtility(IPersonSet).get(17)
    >>> ubuntu_team_member = getUtility(IPersonSet).get(1)
    >>> ubuntu_team_nonmember = getUtility(IPersonSet).get(12)

    >>> pollset = getUtility(IPollSet)
    >>> director_election = pollset.getByTeamAndName(
    ...     ubuntu_team, "director-2004"
    ... )
    >>> director_options = director_election.getActiveOptions()
    >>> leader_election = pollset.getByTeamAndName(ubuntu_team, "leader-2004")
    >>> leader_options = leader_election.getActiveOptions()
    >>> opendate = leader_election.dateopens
    >>> onesec = timedelta(seconds=1)


If the poll is already opened, it's impossible to remove an option.

    >>> leader_election.removeOption(leader_options[0], when=opendate)
    Traceback (most recent call last):
    ...
    AssertionError


Trying to vote two times is a programming error.

    >>> votes = leader_election.storeSimpleVote(
    ...     ubuntu_team_member, leader_options[0], when=opendate
    ... )

    >>> votes = leader_election.storeSimpleVote(
    ...     ubuntu_team_member, leader_options[0], when=opendate
    ... )
    Traceback (most recent call last):
    ...
    AssertionError: Can't vote twice in one poll


It's not possible for a non-member to vote, neither to vote when the poll is
not open.

    >>> votes = leader_election.storeSimpleVote(
    ...     ubuntu_team_nonmember, leader_options[0], when=opendate
    ... )
    Traceback (most recent call last):
    ...
    AssertionError: Person ... is not a member of this poll's team.

    >>> votes = leader_election.storeSimpleVote(
    ...     ubuntu_team_member, leader_options[0], when=opendate - onesec
    ... )
    Traceback (most recent call last):
    ...
    AssertionError: This poll is not open


It's not possible to vote on an option that doesn't belong to the poll you're
voting in.

    >>> options = {leader_options[0]: 1}
    >>> votes = director_election.storeCondorcetVote(
    ...     ubuntu_team_member, options, when=opendate
    ... )
    Traceback (most recent call last):
    ...
    AssertionError: The option ... doesn't belong to this poll

