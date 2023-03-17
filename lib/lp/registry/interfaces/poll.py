# Copyright 2009-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "CannotCreatePoll",
    "IPoll",
    "IPollSet",
    "IPollSubset",
    "IPollOption",
    "IPollOptionSet",
    "IVote",
    "IVoteCast",
    "PollAlgorithm",
    "PollSecrecy",
    "PollStatus",
    "IVoteSet",
    "IVoteCastSet",
    "OptionIsNotFromSimplePoll",
]

import http.client
from datetime import datetime, timedelta, timezone

from lazr.enum import DBEnumeratedType, DBItem
from lazr.restful.declarations import (
    collection_default_content,
    error_status,
    export_read_operation,
    exported,
    exported_as_webservice_collection,
    exported_as_webservice_entry,
    operation_for_version,
    operation_parameters,
    operation_returns_collection_of,
)
from lazr.restful.fields import Reference
from zope.component import getUtility
from zope.interface import Attribute, Interface, invariant
from zope.interface.exceptions import Invalid
from zope.schema import Bool, Choice, Datetime, Int, List, Text, TextLine

from lp import _
from lp.app.validators.name import name_validator
from lp.registry.enums import PollSort
from lp.registry.interfaces.person import ITeam
from lp.services.fields import ContentNameField


class PollNameField(ContentNameField):

    errormessage = _("%s is already in use by another poll in this team.")

    @property
    def _content_iface(self):
        return IPoll

    def _getByName(self, name):
        team = ITeam(self.context, None)
        if team is None:
            team = self.context.team
        return getUtility(IPollSet).getByTeamAndName(team, name)


class PollAlgorithm(DBEnumeratedType):
    """The algorithm used to accept and calculate the results."""

    SIMPLE = DBItem(
        1,
        """
        Simple Voting

        The most simple method for voting; you just choose a single option.
        """,
    )

    CONDORCET = DBItem(
        2,
        """
        Condorcet Voting

        One of various methods used for calculating preferential votes. See
        http://www.electionmethods.org/CondorcetEx.htm for more information.
        """,
    )


class PollSecrecy(DBEnumeratedType):
    """The secrecy of a given Poll."""

    OPEN = DBItem(
        1,
        """
        Public Votes (Anyone can see a person's vote)

        Everyone who wants will be able to see a person's vote.
        """,
    )

    ADMIN = DBItem(
        2,
        """
        Semi-secret Votes (Only team administrators can see a person's vote)

        All team owners and administrators will be able to see a person's vote.
        """,
    )

    SECRET = DBItem(
        3,
        """
        Secret Votes (It's impossible to track a person's vote)

        We don't store the option a person voted in our database,
        """,
    )


class PollStatus:
    """This class stores the constants used when searching for polls."""

    OPEN = "open"
    CLOSED = "closed"
    NOT_YET_OPENED = "not-yet-opened"
    ALL = frozenset([OPEN, CLOSED, NOT_YET_OPENED])


@error_status(http.client.FORBIDDEN)
class CannotCreatePoll(Exception):
    pass


@exported_as_webservice_entry(as_of="beta")
class IPoll(Interface):
    """A poll for a given proposition in a team."""

    id = Int(title=_("The unique ID"), required=True, readonly=True)

    team = exported(
        Reference(
            ITeam,
            title=_("The team that this poll refers to."),
            required=True,
            readonly=True,
        )
    )

    name = exported(
        PollNameField(
            title=_("The unique name of this poll"),
            description=_(
                "A short unique name, beginning with a lower-case "
                "letter or number, and containing only letters, "
                "numbers, dots, hyphens, or plus signs."
            ),
            required=True,
            readonly=False,
            constraint=name_validator,
        )
    )

    title = exported(
        TextLine(
            title=_("The title of this poll"), required=True, readonly=False
        )
    )

    dateopens = exported(
        Datetime(
            title=_("The date and time when this poll opens"),
            required=True,
            readonly=False,
        )
    )

    datecloses = exported(
        Datetime(
            title=_("The date and time when this poll closes"),
            required=True,
            readonly=False,
        )
    )

    proposition = exported(
        Text(
            title=_("The proposition that is going to be voted"),
            required=True,
            readonly=False,
        )
    )

    type = exported(
        Choice(
            title=_("The type of this poll"),
            required=True,
            readonly=False,
            vocabulary=PollAlgorithm,
            default=PollAlgorithm.CONDORCET,
        )
    )

    allowspoilt = exported(
        Bool(
            title=_("Users can spoil their votes?"),
            description=_(
                "Allow users to leave the ballot blank (i.e. cast a vote for "
                '"None of the above")'
            ),
            required=True,
            readonly=False,
            default=True,
        )
    )

    secrecy = exported(
        Choice(
            title=_("The secrecy of the Poll"),
            required=True,
            readonly=False,
            vocabulary=PollSecrecy,
            default=PollSecrecy.SECRET,
        )
    )

    @invariant
    def saneDates(poll):
        """Ensure the poll's dates are sane.

        A poll's end date must be after its start date and its start date must
        be at least 12h from now.
        """
        if poll.dateopens >= poll.datecloses:
            raise Invalid(
                "A poll cannot close at the time (or before) it opens."
            )
        now = datetime.now(timezone.utc)
        # Allow a bit of slack to account for time between form creation and
        # validation.
        twelve_hours_ahead = now + timedelta(hours=12) - timedelta(seconds=60)
        start_date = poll.dateopens.astimezone(timezone.utc)
        if start_date < twelve_hours_ahead:
            raise Invalid(
                "A poll cannot open less than 12 hours after it's created."
            )

    def isOpen(when=None):
        """Return True if this Poll is still open.

        The optional :when argument is used only by our tests, to test if the
        poll is/was/will be open at a specific date.
        """

    def isClosed(when=None):
        """Return True if this Poll is already closed.

        The optional :when argument is used only by our tests, to test if the
        poll is/was/will be closed at a specific date.
        """

    def isNotYetOpened(when=None):
        """Return True if this Poll is not yet opened.

        The optional :when argument is used only by our tests, to test if the
        poll is/was/will be not-yet-opened at a specific date.
        """

    def closesIn():
        """Return a timedelta object of the interval between now and the date
        when this poll closes."""

    def opensIn():
        """Return a timedelta object of the interval between now and the date
        when this poll opens."""

    def newOption(name, title, active=True):
        """Create a new PollOption for this poll."""

    def getActiveOptions():
        """Return all PollOptions of this poll that are active."""

    def getAllOptions():
        """Return all Options of this poll."""

    def personVoted(person):
        """Return True if :person has already voted in this poll."""

    def getVotesByPerson(person):
        """Return the votes of the given person in this poll.

        The return value will always be a list of Vote objects. That's for
        consistency because on simple polls there'll be always a single vote,
        but for condorcet poll, there'll always be a list.
        """

    def getTotalVotes():
        """Return the total number of votes this poll had.

        This must be used only on closed polls.
        """

    def getWinners():
        """Return the options which won this poll.

        This should be used only on closed polls.
        """

    def removeOption(option, when=None):
        """Remove the given option from this poll.

        A ValueError is raised if the given option doesn't belong to this poll.
        This method can be used only on polls that are not yet opened.
        The optional :when argument is used only by our tests, to test if the
        poll is/was/will be not-yet-opened at a specific date.
        """

    def getOptionByName(name):
        """Return the PollOption by the given name."""

    def storeSimpleVote(person, option, when=None):
        """Store and return the vote of a given person in a this poll.

        This method can be used only if this poll is still open and if this is
        a Simple-style poll.

        :option: The chosen option.

        :when: Optional argument used only by our tests, to test if the poll
               is/was/will be open at a specific date.
        """

    def storeCondorcetVote(person, options, when=None):
        """Store and return the votes of a given person in this poll.

        This method can be used only if this poll is still open and if this is
        a Condorcet-style poll.

        :options: A dictionary, where the options are the keys and the
                  preferences of each option are the values.

        :when: Optional argument used only by our tests, to test if the poll
               is/was/will be open at a specific date.
        """

    def getPairwiseMatrix():
        """Return the pairwise matrix for this poll.

        This method is only available for condorcet-style polls.
        See http://www.electionmethods.org/CondorcetEx.htm for an example of a
        pairwise matrix.
        """


@exported_as_webservice_collection(IPoll)
class IPollSet(Interface):
    """The set of Poll objects."""

    def new(
        team,
        name,
        title,
        proposition,
        dateopens,
        datecloses,
        secrecy,
        allowspoilt,
        poll_type=PollAlgorithm.SIMPLE,
    ):
        """Create a new Poll for the given team."""

    @operation_parameters(
        team=Reference(ITeam, title=_("Team"), required=False),
        status=List(
            title=_("Poll statuses"),
            description=_(
                "A list of one or more of 'open', 'closed', or "
                "'not-yet-opened'.  Defaults to all statuses."
            ),
            value_type=Choice(values=PollStatus.ALL),
            min_length=1,
            required=False,
        ),
        order_by=Choice(
            title=_("Sort order"), vocabulary=PollSort, required=False
        ),
    )
    @operation_returns_collection_of(IPoll)
    @export_read_operation()
    @operation_for_version("devel")
    def find(
        team=None, status=None, order_by=PollSort.NEWEST_FIRST, when=None
    ):
        """Search for polls.

        :param team: An optional `ITeam` to filter by.
        :param status: A collection containing as many values as you want
            from PollStatus.  Defaults to `PollStatus.ALL`.
        :param order_by: An optional `PollSort` item indicating how to sort
            the results.  Defaults to `PollSort.NEWEST_FIRST`.
        :param when: Used only by tests, to filter for polls open at a
            specific date.
        """

    def findByTeam(
        team, status=None, order_by=PollSort.NEWEST_FIRST, when=None
    ):
        """Return all Polls for the given team, filtered by status.

        :param team: A `ITeam` to filter by.
        :param status: A collection containing as many values as you want
            from PollStatus.  Defaults to `PollStatus.ALL`.
        :param order_by: An optional `PollSort` item indicating how to sort
            the results.  Defaults to `PollSort.NEWEST_FIRST`.
        :param when: Used only by tests, to filter for polls open at a
            specific date.
        """

    def getByTeamAndName(team, name, default=None):
        """Return the Poll for the given team with the given name.

        Return :default if there's no Poll with this name for that team.
        """

    @collection_default_content()
    def emptyList():
        """Return an empty collection of polls.

        This only exists to keep lazr.restful happy.
        """


class IPollSubset(Interface):
    """The set of Poll objects for a given team."""

    team = Attribute(_("The team of these polls."))

    title = Attribute("Polls Page Title")

    def new(
        name,
        title,
        proposition,
        dateopens,
        datecloses,
        secrecy,
        allowspoilt,
        poll_type=PollAlgorithm.SIMPLE,
    ):
        """Create a new Poll for this team."""

    def getAll():
        """Return all Polls of this team."""

    def getOpenPolls(when=None):
        """Return all Open Polls for this team ordered by the date they'll
        close.

        The optional :when argument is used only by our tests, to test if the
        poll is/was/will be open at a specific date.
        """

    def getNotYetOpenedPolls(when=None):
        """Return all Not-Yet-Opened Polls for this team ordered by the date
        they'll open.

        The optional :when argument is used only by our tests, to test if the
        poll is/was/will be open at a specific date.
        """

    def getClosedPolls(when=None):
        """Return all Closed Polls for this team ordered by the date they
        closed.

        The optional :when argument is used only by our tests, to test if the
        poll is/was/will be open at a specific date.
        """


class PollOptionNameField(ContentNameField):

    errormessage = _("%s is already in use by another option in this poll.")

    @property
    def _content_iface(self):
        return IPollOption

    def _getByName(self, name):
        if IPollOption.providedBy(self.context):
            poll = self.context.poll
        else:
            poll = self.context
        return poll.getOptionByName(name)


class IPollOption(Interface):
    """An option to be voted in a given Poll."""

    id = Int(title=_("The unique ID"), required=True, readonly=True)

    poll = Int(
        title=_("The Poll to which this option refers to."),
        required=True,
        readonly=True,
    )

    name = PollOptionNameField(title=_("Name"), required=True, readonly=False)

    title = TextLine(
        title=_("Title"),
        description=_(
            "The title of this option. A single brief sentence that "
            "summarises the outcome for which people are voting if "
            "they select this option."
        ),
        required=True,
        readonly=False,
    )

    active = Bool(
        title=_("Is this option active?"),
        required=True,
        readonly=False,
        default=True,
    )

    def destroySelf():
        """Remove this option from the database."""


class IPollOptionSet(Interface):
    """The set of PollOption objects."""

    def new(poll, name, title, active=True):
        """Create a new PollOption."""

    def findByPoll(poll, only_active=False):
        """Return all PollOptions of the given poll.

        If :only_active is True, then return only the active polls.
        """

    def getByPollAndId(poll, id, default=None):
        """Return the PollOption with the given id.

        Return :default if there's no PollOption with the given id or if that
        PollOption is not in the given poll.
        """


class IVoteCast(Interface):
    """Here we store who voted in a Poll, but not their votes."""

    id = Int(title=_("The unique ID"), required=True, readonly=True)

    person = Int(
        title=_("The Person that voted."), required=False, readonly=True
    )

    poll = Int(
        title=_("The Poll in which the person voted."),
        required=True,
        readonly=True,
    )


class IVoteCastSet(Interface):
    """The set of all VoteCast objects."""

    def new(poll, person):
        """Create a new VoteCast."""


class IVote(Interface):
    """Here we store the vote itself, linked to a special token.

    This token is given to the user when they vote, so they can change their
    vote later.
    """

    id = Int(title=_("The unique ID"), required=True, readonly=True)

    person = Int(
        title=_("The Person that voted."), required=False, readonly=True
    )

    poll = Int(
        title=_("The Poll in which the person voted."),
        required=True,
        readonly=True,
    )

    option = Int(
        title=_("The PollOption chosen."), required=True, readonly=False
    )

    preference = Int(
        title=_("The preference of the chosen PollOption"),
        required=True,
        readonly=False,
    )

    token = Text(
        title=_("The token we give to the user."), required=True, readonly=True
    )


class OptionIsNotFromSimplePoll(Exception):
    """Someone tried use an option from a non-SIMPLE poll as if it was from a
    SIMPLE one."""


class IVoteSet(Interface):
    """The set of all Vote objects."""

    def new(poll, option, preference, token, person):
        """Create a new Vote."""

    def getByToken(token):
        """Return the list of votes with the given token.

        For polls whose type is SIMPLE, this list will contain a single vote,
        because in SIMPLE poll only one option can be chosen.
        """

    def getVotesByOption(option):
        """Return the number of votes the given option received.

        Raises a TypeError if the given option doesn't belong to a
        simple-style poll.
        """
