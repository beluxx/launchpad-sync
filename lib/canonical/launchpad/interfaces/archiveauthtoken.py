# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""ArchiveAuthToken interface."""

__metaclass__ = type

__all__ = [
    'IArchiveAuthToken',
    'IArchiveAuthTokenSet',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Int, TextLine

from canonical.launchpad import _
from canonical.launchpad.interfaces.archive import IArchive
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr.fields import Reference


class IArchiveAuthTokenView(Interface):
    """Interface for Archive Authorisation Tokens requiring launchpad.View."""
    id = Int(title=_('ID'), required=True, readonly=True)

    archive = Reference(
        IArchive, title=_("Archive"), required=True, readonly=True,
        description=_("The archive for this authorisation token."))

    person = Reference(
        IPerson, title=_("Person"), required=True, readonly=True,
        description=_("The person for this authorisation token."))

    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True,
        description=_("The timestamp when the token was created."))

    date_deactivated = Datetime(
        title=_("Date De-activated"), required=False,
        description=_("The timestamp when the token was de-activated."))

    token = TextLine(
        title=_("Token"), required=True, readonly=True,
        description=_("The access token to the archive for this person."))


class IArchiveAuthTokenEdit(Interface):
    """Interface for Archive Auth Tokens requiring launchpad.Edit."""
    def deactivate(self):
        """Deactivate the token by setting date_deactivated to UTC_NOW."""


class IArchiveAuthToken(IArchiveAuthTokenView, IArchiveAuthTokenEdit):
    """An interface for Archive Auth Tokens."""


class IArchiveAuthTokenSet(Interface):
    """An interface for `ArchiveAuthTokenSet`."""

    def get(token_id):
        """Retrieve a token by its database ID.

        :param token_id: The database ID
        :return: An object conforming to IArchiveAuthToken
        """

    def getByToken(token):
        """Retrieve a token by its token text.

        :param token: The token text for the token.
        :return An object conforming to IArchiveAuthToken
        """

    def getActiveTokenForArchiveAndPerson(archive, person):
        """Retrieve an active token for the given archive and person.

        :param archive: The archive to which the token corresponds.
        :param person: The person to which the token corresponds.
        :return An object conforming to IArchiveAuthToken or None.
        """
