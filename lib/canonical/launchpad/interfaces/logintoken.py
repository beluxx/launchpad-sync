# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class ILoginToken(Interface):
    """The object that stores one time tokens used for validating email
    addresses and other tasks that require verifying if an email address is
    valid such as password recovery and account merging."""
    id = Int(
        title=_('ID'), required=True, readonly=True,
        )
    email = Text(
        title=_('The email address that this request was sent to.'),
                required=True,
        )
    requester = Int(
        title=_('The Person that made this request.'), required=True,
        )
    requesteremail = Text(
        title=_('The email address that was used to login when making this request.'),
                required=True,
        )
    created = Datetime(
        title=_('The timestamp that this request was made.'), required=True,
        )
    tokentype = Text(
        title=_('The type of request, as per dbschema.TokenType.'),
                required=True,
        )
    token = Text(
        title=_('The token (not the URL) emailed used to uniquely identify this request.'),
                required=True,
        )


class ILoginTokenSet(Interface):
    """The set of LoginTokens."""

    def __getitem__(id):
        """Returns the LoginToken with the given id.

        Raises KeyError if there is no such LoginToken.
        """

    def get(id, default=None):
        """Returns the LoginToken with the given id.

        Returns the default value if there is no such LoginToken.
        """


