# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""OAuth interfaces."""

__metaclass__ = type

__all__ = [
    'IOAuthAccessToken',
    'IOAuthConsumer',
    'IOAuthConsumerSet',
    'IOAuthNonce',
    'IOAuthRequestToken',
    'OAuthPermission']

from zope.schema import Bool, Choice, Datetime, Object, TextLine
from zope.interface import Interface

from canonical.lazr import DBEnumeratedType, DBItem

from canonical.launchpad import _
from canonical.launchpad.interfaces.person import IPerson


class OAuthPermission(DBEnumeratedType):
    """The permission granted by the user to the OAuth consumer."""

    UNAUTHORIZED = DBItem(10, """
        Not authorized

        The user didn't authorize the consumer to act on his behalf.
        """)

    READ_PUBLIC = DBItem(20, """
        Read public data

        The consumer can act on the user's behalf but only for reading public
        data.
        """)

    WRITE_PUBLIC = DBItem(30, """
        Read and write public data

        The consumer can act on the user's behalf but only for reading and
        writing public data.
        """)

    READ_PRIVATE = DBItem(40, """
        Read public and private data

        The consumer can act on the user's behalf but only for reading
        public and private data.
        """)

    WRITE_PRIVATE = DBItem(50, """
        Read and write public and private data

        The consumer can act on the user's behalf for reading and writing
        public and private data.
        """)


class IOAuthConsumer(Interface):
    """An application which acts on behalf of a Launchpad user."""

    date_created = Datetime(
        title=_('Date created'), required=True, readonly=True)
    disabled = Bool(
        title=_('Disabled?'), required=False, readonly=False,
        description=_('Disabled consumers are not allowed to access any '
                      'protected resources.'))
    key = TextLine(
        title=_('Key'), required=True, readonly=True,
        description=_('The unique key which identifies a consumer. It is '
                      'included by the consumer in each request made.'))
    secret = TextLine(
        title=_('Secret'), required=False, readonly=False,
        description=_('The secret which, if not empty, should be used by the '
                      'consumer to sign its requests.'))

    def newRequestToken():
        """Return a new `IOAuthRequestToken` with a random key and secret.

        Also sets the token's date_expires to `REQUEST_TOKEN_VALIDITY` hours
        from the creation date (now).

        The other attributes of the token are supposed to be set whenever the
        user logs into Launchpad and grants (or not) access to this consumer.
        """

    def getRequestToken(key):
        """Return the `IOAuthRequestToken` with the given key.

        If the token with the given key does not exist or is associated with
        another consumer, return None.
        """


class IOAuthConsumerSet(Interface):
    """The set of OAuth consumers."""

    def new(key, secret=''):
        """Return the newly created consumer.

        You must make sure the given `key` is not already in use by another
        consumer before trying to create a new one.

        The `secret` defaults to an empty string because most consumers will
        be open source desktop applications for which it wouldn't be actually
        secret.

        :param key: The unique key which will be associated with the new
            consumer.
        :param secret: A secret which should be used by the consumer to sign
            its requests.
        """

    def getByKey(key):
        """Return the consumer with the given key.

        If there's no consumer with the given key, return None.

        :param key: The unique key associated with a consumer.
        """


class IOAuthToken(Interface):
    """Base class for `IOAuthRequestToken` and `IOAuthAccessToken`.

    This class contains the commonalities of the two token classes we actually
    care about and shall not be used on its own.
    """

    consumer = Object(
        schema=IOAuthConsumer, title=_('The consumer.'),
        description=_("The consumer which will access Launchpad on the "
                      "user's behalf."))
    person = Object(
        schema=IPerson, title=_('Person'), required=False, readonly=False,
        description=_('The user on whose behalf the consumer is accessing.'))
    permission = Choice(
        title=_('Permission'), required=False, readonly=False,
        vocabulary=OAuthPermission,
        description=_('The permission granted by the user to this consumer.'))
    date_created = Datetime(
        title=_('Date created'), required=True, readonly=True)
    date_expires = Datetime(
        title=_('Date expires'), required=False, readonly=False,
        description=_('From this date onwards this token can not be used '
                      'by the consumer to access protected resources.'))
    key = TextLine(
        title=_('Key'), required=True, readonly=True,
        description=_('The key used to identify this token.  It is included '
                      'by the consumer in each request.'))
    secret = TextLine(
        title=_('Secret'), required=True, readonly=True,
        description=_('The secret associated with this token.  It is used '
                      'by the consumer to sign its requests.'))


class IOAuthAccessToken(IOAuthToken):
    """A token used by a consumer to access protected resources in LP.

    It's created automatically once a user logs in and grants access to a
    consumer.  The consumer then exchanges an `IOAuthRequestToken` for it.
    """


class IOAuthRequestToken(IOAuthToken):
    """A token used by a consumer to ask the user to authenticate on LP.

    After the user has authenticated and granted access to that consumer, the
    request token is exchanged for an access token and is then destroyed.
    """

    date_reviewed = Datetime(
        title=_('Date reviewed'), required=True, readonly=True,
        description=_('The date in which the user authorized (or not) the '
                      'consumer to access his protected resources on '
                      'Launchpad.'))
    is_reviewed = Bool(
        title=_('Has this token been reviewed?'),
        required=False, readonly=True,
        description=_('A reviewed request token can only be exchanged for an '
                      'access token (in case the user granted access).'))

    def review(user, permission):
        """Grant `permission` as `user` to this token's consumer.

        Set this token's person, permission and date_reviewed.  This will also
        cause this token to be marked as used, meaning it can only be
        exchanged for an access token with the same permission, consumer and
        person.
        """

    def createAccessToken():
        """Create an `IOAuthAccessToken` identical to this request token.

        After the access token is created, this one is deleted as it can't be
        used anymore.

        You must not attempt to create an access token if the request token
        hasn't been reviewed or if its permission is UNAUTHORIZED.
        """


class IOAuthNonce(Interface):
    """The unique (nonce,timestamp) for requests from a given consumer.

    The nonce value (which is unique for all requests with that timestamp)
    is generated by the consumer and included, together with the timestamp,
    in each request made.  It's used to prevent replay attacks.
    """

    request_timestamp = Datetime(
        title=_('Date issued'), required=True, readonly=True)
    consumer = Object(schema=IOAuthConsumer, title=_('The consumer.'))
    nonce = TextLine(title=_('Nonce'), required=True, readonly=True)
