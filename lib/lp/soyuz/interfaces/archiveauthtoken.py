# Copyright 2009-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ArchiveAuthToken interface."""

__all__ = [
    'IArchiveAuthToken',
    'IArchiveAuthTokenSet',
    ]

from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Datetime,
    Int,
    TextLine,
    )

from lp import _
from lp.registry.interfaces.person import IPerson
from lp.soyuz.interfaces.archive import IArchive


class IArchiveAuthTokenView(Interface):
    """Interface for Archive Authorization Tokens requiring launchpad.View."""
    id = Int(title=_('ID'), required=True, readonly=True)

    archive = Reference(
        IArchive, title=_("Archive"), required=True, readonly=True,
        description=_("The archive for this authorization token."))

    person = Reference(
        IPerson, title=_("Person"), required=False, readonly=True,
        description=_("The person for this authorization token."))
    person_id = Attribute('db person value')

    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True,
        description=_("The timestamp when the token was created."))

    date_deactivated = Datetime(
        title=_("Date De-activated"), required=False,
        description=_("The timestamp when the token was de-activated."))

    token = TextLine(
        title=_("Token"), required=True, readonly=True,
        description=_("The access token to the archive for this person."))

    archive_url = TextLine(
        title=_("Archive url"), readonly=True,
        description=_(
            "External archive URL including basic auth for this person"))

    name = TextLine(
        title=_("Name"), required=False, readonly=True,
        description=_(
            "The name in the case of a named authorization token, or None."))

    def deactivate():
        """Deactivate the token by setting date_deactivated to UTC_NOW."""

    def asDict():
        """Returns a dictionary where the value of `token` is the secret and
        the value of `archive_url` is the externally-usable archive URL
        including basic auth.
        """


class IArchiveAuthTokenEdit(Interface):
    """Interface for Archive Auth Tokens requiring launchpad.Edit."""


class IArchiveAuthToken(IArchiveAuthTokenView, IArchiveAuthTokenEdit):
    """An interface for Archive Auth Tokens."""


class IArchiveAuthTokenSet(Interface):
    """An interface for `ArchiveAuthTokenSet`."""

    def get(token_id):
        """Retrieve a token by its database ID.

        :param token_id: The database ID.
        :return: An object conforming to `IArchiveAuthToken`.
        """

    def getByToken(token):
        """Retrieve a token by its token text.

        :param token: The token text for the token.
        :return: An object conforming to `IArchiveAuthToken`.
        """

    def getByArchive(archive, with_current_subscription=False):
        """Retrieve all the tokens for an archive.

        :param archive: The context archive.
        :param with_current_subscription: If True, only return tokens
            associated with a current subscription.
        :return: A result set containing `IArchiveAuthToken`s.
        """

    def getActiveTokenForArchiveAndPerson(archive, person):
        """Retrieve a valid active token for the given archive and person.

        :param archive: The archive to which the token corresponds.
        :param person: The person to which the token corresponds.
        :return: An `IArchiveAuthToken` or None.
        """

    def getActiveTokenForArchiveAndPersonName(archive, person_name):
        """Retrieve a valid active token for the given archive and person name.

        :param archive: The archive to which the token corresponds.
        :param person_name: The name of the person to which the token
            corresponds.
        :return: An `IArchiveAuthToken` or None.
        """

    def getActiveNamedTokenForArchive(archive, name):
        """Retrieve a valid active named token for the given archive and name.

        :param archive: The archive to which the token corresponds.
        :param name: The name of a named authorization token.
        :return An object conforming to `IArchiveAuthToken` or None.
        """

    def getActiveNamedTokensForArchive(archive, names=None):
        """Retrieve a subset of valid active named tokens for the given
        archive if `names` is specified, or all valid active named tokens
        for the archive if `names` is null.

        :param archive: The archive to which the tokens correspond.
        :param names: An optional list of token names.
        :return: A result set containing `IArchiveAuthToken`s.
        """

    def deactivateNamedTokensForArchive(archive, names):
        """Deactivate named tokens for the given archive.

        :param archive: The archive to which the tokens correspond.
        :param names: A list of token names.
        """
