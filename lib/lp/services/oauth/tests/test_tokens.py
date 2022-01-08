# Copyright 2010-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OAuth is a mechanism for allowing a user's desktop or a third-party
website to access Launchpad on a user's behalf.  These applications
are identified by a unique key and are stored as OAuthConsumers.  The
OAuth specification is defined in <http://oauth.net/core/1.0/>.
"""

from datetime import (
    datetime,
    timedelta,
    )
import hashlib

import pytz
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.services.oauth.interfaces import (
    IOAuthAccessToken,
    IOAuthConsumer,
    IOAuthConsumerSet,
    IOAuthRequestToken,
    IOAuthRequestTokenSet,
    )
from lp.services.oauth.model import OAuthValidationError
from lp.services.webapp.interfaces import (
    AccessLevel,
    OAuthPermission,
    )
from lp.testing import (
    login_person,
    oauth_access_token_for,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.mail_helpers import pop_notifications


class TestOAuth(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Set up some convenient data objects and timestamps."""
        super().setUp()

        self.person = self.factory.makePerson()
        self.consumer = self.factory.makeOAuthConsumer()

        now = datetime.now(pytz.timezone('UTC'))
        self.in_a_while = now + timedelta(hours=1)
        self.a_long_time_ago = now - timedelta(hours=1000)


class TestConsumerSet(TestOAuth):
    """Tests of the utility that manages OAuth consumers."""

    def setUp(self):
        super().setUp()
        self.consumers = getUtility(IOAuthConsumerSet)

    def test_interface(self):
        verifyObject(IOAuthConsumerSet, self.consumers)

    def test_new(self):
        consumer = self.consumers.new(
            self.factory.getUniqueUnicode("oauthconsumerkey"))
        verifyObject(IOAuthConsumer, consumer)

    def test_new_wont_create_duplicate_consumer(self):
        self.assertRaises(
            AssertionError, self.consumers.new, key=self.consumer.key)

    def test_getByKey(self):
        self.assertEqual(
            self.consumers.getByKey(self.consumer.key), self.consumer)

    def test_getByKey_returns_none_for_nonexistent_consumer(self):
        # There is no consumer called "oauthconsumerkey-nonexistent".
        nonexistent_key = self.factory.getUniqueUnicode(
            "oauthconsumerkey-nonexistent")
        self.assertEqual(self.consumers.getByKey(nonexistent_key), None)


class TestRequestTokenSet(TestOAuth):
    """Test the set of request tokens."""

    def setUp(self):
        """Set up a reference to the token list."""
        super().setUp()
        self.tokens = getUtility(IOAuthRequestTokenSet)

    def test_getByKey(self):
        token, _ = self.consumer.newRequestToken()
        self.assertEqual(token, self.tokens.getByKey(token.key))

    def test_getByKey_returns_none_for_unused_key(self):
        self.assertIsNone(self.tokens.getByKey("no-such-token"))


class TestRequestTokens(TestOAuth):
    """Tests for OAuth request token objects."""

    def test_newRequestToken(self):
        request_token, secret = self.consumer.newRequestToken()
        verifyObject(IOAuthRequestToken, request_token)
        self.assertIsInstance(secret, str)
        self.assertEqual(
            removeSecurityProxy(request_token)._secret,
            hashlib.sha256(secret.encode('ASCII')).hexdigest())

    def test_key_and_secret_automatically_generated(self):
        request_token, secret = self.consumer.newRequestToken()
        self.assertEqual(len(request_token.key), 20)
        self.assertEqual(len(removeSecurityProxy(request_token)._secret), 64)

    def test_date_created(self):
        request_token, _ = self.consumer.newRequestToken()
        now = datetime.now(pytz.timezone('UTC'))
        self.assertTrue(request_token.date_created <= now)

    def test_new_token_is_not_reviewed(self):
        request_token, _ = self.consumer.newRequestToken()
        self.assertFalse(request_token.is_reviewed)
        self.assertEqual(None, request_token.person)
        self.assertEqual(None, request_token.date_reviewed)

        # An unreviewed token has no associated permission, expiration
        # date, or context.
        self.assertEqual(None, request_token.permission)
        self.assertEqual(None, request_token.date_expires)
        self.assertEqual(None, request_token.context)

    def test_getRequestToken(self):
        token_1, _ = self.consumer.newRequestToken()
        token_2 = self.consumer.getRequestToken(token_1.key)
        self.assertEqual(token_1, token_2)

    def test_getRequestToken_for_wrong_consumer_returns_none(self):
        token_1, _ = self.consumer.newRequestToken()
        consumer_2 = self.factory.makeOAuthConsumer()
        self.assertIsNone(consumer_2.getRequestToken(token_1.key))

    def test_getRequestToken_for_nonexistent_key_returns_none(self):
        self.assertIsNone(self.consumer.getRequestToken("no-such-token"))

    def test_isSecretValid(self):
        token, secret = self.consumer.newRequestToken()
        self.assertTrue(token.isSecretValid(secret))
        self.assertFalse(token.isSecretValid(secret + 'a'))

    def test_token_review(self):
        request_token, _ = self.consumer.newRequestToken()

        request_token.review(self.person, OAuthPermission.WRITE_PUBLIC)
        now = datetime.now(pytz.timezone('UTC'))

        self.assertTrue(request_token.is_reviewed)
        self.assertEqual(request_token.person, self.person)
        self.assertEqual(request_token.permission,
                         OAuthPermission.WRITE_PUBLIC)

        self.assertTrue(request_token.date_created <= now)

        # By default, reviewing a token does not set a context or
        # expiration date.
        self.assertIsNone(request_token.context)
        self.assertIsNone(request_token.date_expires)

    def test_token_review_as_unauthorized(self):
        request_token, _ = self.consumer.newRequestToken()
        request_token.review(self.person, OAuthPermission.UNAUTHORIZED)

        # This token has been reviewed, but it may not be used for any
        # purpose.
        self.assertTrue(request_token.is_reviewed)
        self.assertEqual(request_token.permission,
                         OAuthPermission.UNAUTHORIZED)

    def test_review_with_expiration_date(self):
        # A request token may be associated with an expiration date
        # upon review.
        request_token, _ = self.consumer.newRequestToken()
        request_token.review(
            self.person, OAuthPermission.WRITE_PUBLIC,
            date_expires=self.in_a_while)
        self.assertEqual(request_token.date_expires, self.in_a_while)

    def test_review_with_expiration_date_in_the_past(self):
        # The expiration date, like the permission and context, is
        # associated with the eventual access token. It has nothing to
        # do with how long the *request* token will remain
        # valid.
        #
        # Setting a request token's date_expires to a date in the past
        # is not a good idea, but it won't expire the request token.
        request_token, _ = self.consumer.newRequestToken()
        request_token.review(
            self.person, OAuthPermission.WRITE_PUBLIC,
            date_expires=self.a_long_time_ago)
        self.assertEqual(request_token.date_expires, self.a_long_time_ago)
        self.assertFalse(request_token.is_expired)

    def _reviewed_token_for_context(self, context_factory):
        """Create and review a request token with a given context."""
        token, _ = self.consumer.newRequestToken()
        name = self.factory.getUniqueString('context')
        context = context_factory(name)
        token.review(
            self.person, OAuthPermission.WRITE_PRIVATE, context=context)
        return token, name

    def test_review_with_product_context(self):
        # When reviewing a request token, the context may be set to a
        # product.
        token, name = self._reviewed_token_for_context(
            self.factory.makeProduct)
        self.assertEqual(token.context.name, name)

    def test_review_with_project_group_context(self):
        # When reviewing a request token, the context may be set to a
        # project group.
        token, name = self._reviewed_token_for_context(
            self.factory.makeProject)
        self.assertEqual(token.context.name, name)

    def test_review_with_distrosourcepackage_context(self):
        # When reviewing a request token, the context may be set to a
        # distribution source package.
        token, name = self._reviewed_token_for_context(
            self.factory.makeDistributionSourcePackage)
        self.assertEqual(token.context.name, name)

    def test_expired_request_token_cant_be_reviewed(self):
        """An expired request token can't be reviewed."""
        token = self.factory.makeOAuthRequestToken(
            date_created=self.a_long_time_ago)
        self.assertRaises(
            OAuthValidationError, token.review, self.person,
            OAuthPermission.WRITE_PUBLIC)

    def test_get_request_tokens_for_person(self):
        """It's possible to get a person's request tokens."""
        person = self.factory.makePerson()
        self.assertEqual(person.oauth_request_tokens.count(), 0)
        for i in range(0, 3):
            self.factory.makeOAuthRequestToken(reviewed_by=person)
        self.assertEqual(person.oauth_request_tokens.count(), 3)

    def test_expired_request_token_disappears_from_list(self):
        person = self.factory.makePerson()
        self.assertEqual(person.oauth_request_tokens.count(), 0)
        request_token = self.factory.makeOAuthRequestToken(reviewed_by=person)
        self.assertEqual(person.oauth_request_tokens.count(), 1)

        login_person(person)
        request_token.date_expires = self.a_long_time_ago

        self.assertEqual(person.oauth_request_tokens.count(), 0)


class TestAccessTokens(TestOAuth):
    """Tests for OAuth access tokens."""

    def _exchange_request_token_for_access_token(self):
        # Use this method instead of factory.makeOAuthAccessToken() to
        # a) to show how a request token is exchanged for an access
        # token, b) acquire a reference to the request token that was
        # used to create the access token.
        request_token, _ = self.consumer.newRequestToken()
        request_token.review(self.person, OAuthPermission.WRITE_PRIVATE)
        access_token, access_secret = request_token.createAccessToken()
        return request_token, access_token, access_secret

    def test_exchange_request_token_for_access_token(self):
        # Make sure the basic exchange of request token for access
        # token works.
        request_token, access_token, access_secret = (
            self._exchange_request_token_for_access_token())
        verifyObject(IOAuthAccessToken, access_token)
        self.assertIsInstance(access_secret, str)
        self.assertEqual(
            removeSecurityProxy(access_token)._secret,
            hashlib.sha256(access_secret.encode('ASCII')).hexdigest())

    def test_access_token_inherits_data_fields_from_request_token(self):
        request_token, access_token, _ = (
            self._exchange_request_token_for_access_token())

        self.assertEqual(request_token.consumer, access_token.consumer)

        # An access token inherits its permission from the request
        # token that created it. But an access token's .permission is
        # an AccessLevel object, not an OAuthPermission. The only real
        # difference is that there's no AccessLevel corresponding to
        # OAuthPermission.UNAUTHORIZED.
        self.assertEqual(access_token.permission, AccessLevel.WRITE_PRIVATE)

        self.assertIsNone(access_token.context)
        self.assertIsNone(access_token.date_expires)

    def test_access_token_field_inheritance(self):
        # Make sure that specific fields like context and expiration
        # date are passed down from request token to access token.
        context = self.factory.makeProduct()
        request_token, _ = self.consumer.newRequestToken()
        request_token.review(
            self.person, OAuthPermission.WRITE_PRIVATE,
            context=context, date_expires=self.in_a_while)
        access_token, _ = request_token.createAccessToken()
        self.assertEqual(request_token.context, access_token.context)
        self.assertEqual(request_token.date_expires, access_token.date_expires)

    def test_request_token_disappears_when_exchanged(self):
        request_token, access_token, _ = (
            self._exchange_request_token_for_access_token())
        self.assertIsNone(self.consumer.getRequestToken(request_token.key))

    def test_cant_exchange_unreviewed_request_token(self):
        # An unreviewed request token cannot be exchanged for an access token.
        token, _ = self.consumer.newRequestToken()
        self.assertRaises(OAuthValidationError, token.createAccessToken)

    def test_cant_exchange_unauthorized_request_token(self):
        # A request token associated with the UNAUTHORIZED
        # OAuthPermission cannot be exchanged for an access token.
        token, _ = self.consumer.newRequestToken()
        token.review(self.person, OAuthPermission.UNAUTHORIZED)
        self.assertRaises(OAuthValidationError, token.createAccessToken)

    def test_expired_request_token_cant_be_exchanged(self):
        """An expired request token can't be exchanged for an access token.

        This can only happen if the token was reviewed before it expired.
        """
        token = self.factory.makeOAuthRequestToken(
            date_created=self.a_long_time_ago, reviewed_by=self.person)
        self.assertRaises(OAuthValidationError, token.createAccessToken)

    def test_write_permission(self):
        """An access token can only be modified by its creator."""
        access_token, _ = self.factory.makeOAuthAccessToken()

        def try_to_set():
            access_token.permission = AccessLevel.WRITE_PUBLIC

        self.assertRaises(Unauthorized, try_to_set)

        login_person(access_token.person)
        try_to_set()

    def test_isSecretValid(self):
        request_token, _ = self.consumer.newRequestToken()
        request_token.review(self.person, OAuthPermission.WRITE_PRIVATE)
        token, secret = request_token.createAccessToken()
        self.assertTrue(token.isSecretValid(secret))
        self.assertFalse(token.isSecretValid(secret + 'a'))

    def test_get_access_tokens_for_person(self):
        """It's possible to get a person's access tokens."""
        person = self.factory.makePerson()
        self.assertEqual(person.oauth_access_tokens.count(), 0)
        for i in range(0, 3):
            self.factory.makeOAuthAccessToken(self.consumer, person)
        self.assertEqual(person.oauth_access_tokens.count(), 3)

    def test_expired_access_token_disappears_from_list(self):
        person = self.factory.makePerson()
        self.assertEqual(person.oauth_access_tokens.count(), 0)
        access_token, _ = self.factory.makeOAuthAccessToken(
            self.consumer, person)
        self.assertEqual(person.oauth_access_tokens.count(), 1)

        login_person(access_token.person)
        access_token.date_expires = self.a_long_time_ago
        self.assertEqual(person.oauth_access_tokens.count(), 0)

    def test_email_notification_message_for_generated_tokens(self):
        token = self.factory.makeOAuthRequestToken(
            reviewed_by=self.person,
        )
        token.createAccessToken()
        notifications = pop_notifications()

        expected = (
            'OAuth token generated for %s in Launchpad' % self.person.name
        )
        self.assertEqual(expected, notifications[0]['subject'])


class TestHelperFunctions(TestOAuth):

    def setUp(self):
        super().setUp()
        self.context = self.factory.makeProduct()

    def test_oauth_access_token_for_creates_nonexistent_token(self):
        # If there's no token for user/consumer key/permission/context,
        # one is created.
        person = self.factory.makePerson()
        self.assertEqual(person.oauth_access_tokens.count(), 0)
        oauth_access_token_for(
            self.consumer.key, person, OAuthPermission.WRITE_PUBLIC,
            self.context)
        self.assertEqual(person.oauth_access_tokens.count(), 1)

    def test_oauth_access_token_string_permission(self):
        """You can pass in a string instead of an OAuthPermission."""
        access_token, _ = oauth_access_token_for(
            self.consumer.key, self.person, 'WRITE_PUBLIC')
        self.assertEqual(access_token.permission, AccessLevel.WRITE_PUBLIC)

    def test_oauth_access_token_string_with_nonexistent_permission(self):
        # NO_SUCH_PERMISSION doesn't correspond to any OAuthPermission
        # object.
        self.assertRaises(
            KeyError, oauth_access_token_for, self.consumer.key,
            self.person, 'NO_SUCH_PERMISSION')
