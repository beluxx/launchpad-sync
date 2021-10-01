# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test harness for running the new-login.txt tests."""

__all__ = [
    'FakeOpenIDConsumer',
    'FakeOpenIDResponse',
    'IAccountSet_getByOpenIDIdentifier_monkey_patched',
    'SRegResponse_fromSuccessResponse_stubbed',
    'fill_login_form_and_submit',
    ]

from contextlib import contextmanager
from datetime import (
    datetime,
    timedelta,
    )
import unittest

from openid.consumer.consumer import (
    FAILURE,
    SUCCESS,
    )
from openid.extensions import (
    pape,
    sreg,
    )
from openid.yadis.discover import DiscoveryFailure
from six.moves import http_client
from six.moves.urllib.error import HTTPError
from six.moves.urllib.parse import (
    parse_qsl,
    quote,
    urlsplit,
    )
from testtools.matchers import (
    Contains,
    ContainsDict,
    Equals,
    MatchesListwise,
    )
from zope.component import getUtility
from zope.security.management import newInteraction
from zope.security.proxy import removeSecurityProxy
from zope.session.interfaces import ISession
from zope.testbrowser.wsgi import Browser as TestBrowser

from lp.registry.interfaces.person import IPerson
from lp.services.database.interfaces import (
    IStore,
    IStoreSelector,
    )
from lp.services.database.policy import MasterDatabasePolicy
from lp.services.identity.interfaces.account import (
    AccountStatus,
    IAccountSet,
    )
from lp.services.identity.interfaces.emailaddress import EmailAddressStatus
from lp.services.openid.extensions.macaroon import (
    MacaroonRequest,
    MacaroonResponse,
    )
from lp.services.openid.model.openididentifier import OpenIdIdentifier
from lp.services.timeline.requesttimeline import get_request_timeline
from lp.services.webapp.interfaces import ILaunchpadApplication
from lp.services.webapp.login import (
    OpenIDCallbackView,
    OpenIDLogin,
    )
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    logout,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.browser import (
    Browser,
    setUp,
    )
from lp.testing.fixture import ZopeViewReplacementFixture
from lp.testing.layers import (
    AppServerLayer,
    DatabaseFunctionalLayer,
    FunctionalLayer,
    )
from lp.testing.pages import (
    extract_text,
    find_main_content,
    find_tag_by_id,
    find_tags_by_class,
    )
from lp.testing.systemdocs import LayeredDocFileSuite
from lp.testopenid.interfaces.server import ITestOpenIDPersistentIdentity


class FakeOpenIDResponse:

    def __init__(self, identity_url, status=SUCCESS, message='', email=None,
                 full_name=None, discharge_macaroon_raw=None):
        self.message = message
        self.status = status
        self.identity_url = identity_url
        self.sreg_email = email
        self.sreg_fullname = full_name
        self.discharge_macaroon_raw = discharge_macaroon_raw


class StubbedOpenIDCallbackView(OpenIDCallbackView):
    login_called = False

    def login(self, account):
        super(StubbedOpenIDCallbackView, self).login(account)
        self.login_called = True
        current_policy = getUtility(IStoreSelector).get_current()
        if not isinstance(current_policy, MasterDatabasePolicy):
            raise AssertionError(
                "Not using the master store: %s" % current_policy)


class FakeConsumer:
    """An OpenID consumer that stashes away arguments for test inspection."""

    def complete(self, params, requested_url):
        self.params = params
        self.requested_url = requested_url


class FakeConsumerOpenIDCallbackView(OpenIDCallbackView):
    """An OpenID handler with fake consumer so arguments can be inspected."""

    def _getConsumer(self):
        self.fake_consumer = FakeConsumer()
        return self.fake_consumer


@contextmanager
def SRegResponse_fromSuccessResponse_stubbed():

    def sregFromFakeSuccessResponse(cls, success_response, signed_only=True):
        return {'email': success_response.sreg_email,
                'fullname': success_response.sreg_fullname}

    orig_method = sreg.SRegResponse.fromSuccessResponse
    # Use a stub SRegResponse.fromSuccessResponse that works with
    # FakeOpenIDResponses instead of real ones.
    sreg.SRegResponse.fromSuccessResponse = classmethod(
        sregFromFakeSuccessResponse)
    try:
        yield
    finally:
        sreg.SRegResponse.fromSuccessResponse = orig_method


@contextmanager
def MacaroonResponse_fromSuccessResponse_stubbed():

    def macaroonFromFakeSuccessResponse(cls, success_response,
                                        signed_only=True):
        return MacaroonResponse(
            discharge_macaroon_raw=success_response.discharge_macaroon_raw)

    orig_method = MacaroonResponse.fromSuccessResponse
    # Use a stub MacaroonResponse.fromSuccessResponse that works with
    # FakeOpenIDResponses instead of real ones.
    MacaroonResponse.fromSuccessResponse = classmethod(
        macaroonFromFakeSuccessResponse)
    try:
        yield
    finally:
        MacaroonResponse.fromSuccessResponse = orig_method


@contextmanager
def IAccountSet_getByOpenIDIdentifier_monkey_patched():
    # Monkey patch getUtility(IAccountSet).getByOpenIDIdentifier() with a
    # method that will raise an AssertionError when it's called and the
    # installed DB policy is not MasterDatabasePolicy.  This is to ensure that
    # the code we're testing forces the use of the master DB by installing the
    # MasterDatabasePolicy.
    account_set = removeSecurityProxy(getUtility(IAccountSet))
    orig_getByOpenIDIdentifier = account_set.getByOpenIDIdentifier

    def fake_getByOpenIDIdentifier(identifier):
        current_policy = getUtility(IStoreSelector).get_current()
        if not isinstance(current_policy, MasterDatabasePolicy):
            raise AssertionError(
                "Not using the master store: %s" % current_policy)
        return orig_getByOpenIDIdentifier(identifier)

    try:
        account_set.getByOpenIDIdentifier = fake_getByOpenIDIdentifier
        yield
    finally:
        account_set.getByOpenIDIdentifier = orig_getByOpenIDIdentifier


class TestOpenIDCallbackView(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def _createViewWithResponse(
            self, account, response_status=SUCCESS, response_msg='',
            view_class=StubbedOpenIDCallbackView,
            email='non-existent@example.com', identifier=None):
        if identifier is None:
            identifier = ITestOpenIDPersistentIdentity(
                account).openid_identity_url
        openid_response = FakeOpenIDResponse(
            identifier, status=response_status, message=response_msg,
            email=email, full_name='Foo User')
        return self._createAndRenderView(
            openid_response, view_class=view_class)

    def _createAndRenderView(self, response,
                             view_class=StubbedOpenIDCallbackView, form=None):
        if form is None:
            form = {'starting_url': 'http://launchpad.test/after-login'}
        request = LaunchpadTestRequest(form=form, environ={'PATH_INFO': '/'})
        # The layer we use sets up an interaction (by calling login()), but we
        # want to use our own request in the interaction, so we logout() and
        # setup a newInteraction() using our request.
        logout()
        newInteraction(request)
        view = view_class(object(), request)
        view.initialize()
        view.openid_response = response
        # Monkey-patch getByOpenIDIdentifier() to make sure the view uses the
        # master DB. This mimics the problem we're trying to avoid, where
        # getByOpenIDIdentifier() doesn't find a newly created account because
        # it looks in the slave database.
        with IAccountSet_getByOpenIDIdentifier_monkey_patched():
            html = view.render()
        return view, html

    def test_full_fledged_account(self):
        # In the common case we just login and redirect to the URL specified
        # in the 'starting_url' query arg.
        test_email = 'test-example@example.com'
        person = self.factory.makePerson(email=test_email)
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createViewWithResponse(
                person.account, email=test_email)
        self.assertTrue(view.login_called)
        response = view.request.response
        self.assertEqual(http_client.TEMPORARY_REDIRECT, response.getStatus())
        self.assertEqual(view.request.form['starting_url'],
                         response.getHeader('Location'))
        # The 'last_write' flag was not updated (unlike in the other test
        # methods) because in this case we didn't have to create a
        # Person/Account entry, so it's ok for further requests to hit the
        # slave DBs.
        self.assertNotIn('last_write', ISession(view.request)['lp.dbpolicy'])

    def test_gather_params(self):
        # If the currently requested URL includes a query string, the
        # parameters in the query string must be included when constructing
        # the params mapping (which is then used to complete the open ID
        # response).  OpenIDCallbackView._gather_params does that gathering.
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=bar',
            form={'starting_url': 'http://launchpad.test/after-login'},
            environ={'PATH_INFO': '/'})
        view = OpenIDCallbackView(context=None, request=None)
        params = view._gather_params(request)
        expected_params = {
            'starting_url': 'http://launchpad.test/after-login',
            'foo': 'bar',
        }
        self.assertEqual(params, expected_params)

    def test_gather_params_with_unicode_data(self):
        # If the currently requested URL includes a query string, the
        # parameters in the query string will be included when constructing
        # the params mapping (which is then used to complete the open ID
        # response) and if there are non-ASCII characters in the query string,
        # they are properly decoded.
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=%E1%9B%9D',
            environ={'PATH_INFO': '/'})
        view = OpenIDCallbackView(context=None, request=None)
        params = view._gather_params(request)
        self.assertEqual(params['foo'], u'\u16dd')

    def test_unexpected_multivalue_fields(self):
        # The parameter gatering doesn't expect to find multi-valued form
        # field and it reports an error if it finds any.
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=1&foo=2',
            environ={'PATH_INFO': '/'})
        view = OpenIDCallbackView(context=None, request=None)
        self.assertRaises(ValueError, view._gather_params, request)

    def test_get_requested_url(self):
        # The OpenIDCallbackView needs to pass the currently-being-requested
        # URL to the OpenID library.  OpenIDCallbackView._get_requested_url
        # returns the URL.
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=bar',
            form={'starting_url': 'http://launchpad.test/after-login'})
        view = OpenIDCallbackView(context=None, request=None)
        url = view._get_requested_url(request)
        self.assertEqual(url, 'http://example.com?foo=bar')

    def test_open_id_callback_handles_query_string(self):
        # If the currently requested URL includes a query string, the
        # parameters in the query string must be included when constructing
        # the params mapping (which is then used to complete the open ID
        # response).
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=bar',
            form={'starting_url': 'http://launchpad.test/after-login'},
            environ={'PATH_INFO': '/'})
        view = FakeConsumerOpenIDCallbackView(object(), request)
        view.initialize()
        self.assertEqual(
            view.fake_consumer.params,
            {
                'starting_url': 'http://launchpad.test/after-login',
                'foo': 'bar',
            })
        self.assertEqual(
            view.fake_consumer.requested_url, 'http://example.com?foo=bar')

    def test_unseen_identity(self):
        # When we get a positive assertion about an identity URL we've never
        # seen, we automatically register an account with that identity
        # because someone who registered on login.lp.net or login.u.c should
        # be able to login here without any further steps.
        identifier = u'4w7kmzU'
        account_set = getUtility(IAccountSet)
        self.assertRaises(
            LookupError, account_set.getByOpenIDIdentifier, identifier)
        openid_response = FakeOpenIDResponse(
            'http://testopenid.test/+id/%s' % identifier, status=SUCCESS,
            email='non-existent@example.com', full_name='Foo User')
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createAndRenderView(openid_response)
        self.assertTrue(view.login_called)
        account = account_set.getByOpenIDIdentifier(identifier)
        self.assertIsNot(None, account)
        self.assertEqual(AccountStatus.ACTIVE, account.status)
        person = IPerson(account, None)
        self.assertIsNot(None, person)
        self.assertEqual('Foo User', person.displayname)
        self.assertEqual('non-existent@example.com',
                         removeSecurityProxy(person.preferredemail).email)

        # We also update the last_write flag in the session, to make sure
        # further requests use the master DB and thus see the newly created
        # stuff.
        self.assertLastWriteIsSet(view.request)

    def test_unseen_identity_with_registered_email(self):
        # When we get a positive assertion about an identity URL we've never
        # seen but whose email address is already registered, we just change
        # the identity URL that's associated with the existing email address.
        identifier = u'4w7kmzU'
        email = 'test@example.com'
        person = self.factory.makePerson(
            displayname='Test account', email=email,
            account_status=AccountStatus.DEACTIVATED,
            email_address_status=EmailAddressStatus.NEW)
        account = person.account
        account_set = getUtility(IAccountSet)
        self.assertRaises(
            LookupError, account_set.getByOpenIDIdentifier, identifier)
        openid_response = FakeOpenIDResponse(
            'http://testopenid.test/+id/%s' % identifier, status=SUCCESS,
            email=email, full_name='Foo User')
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createAndRenderView(openid_response)
        self.assertTrue(view.login_called)

        # The existing accounts had a new openid_identifier added, the
        # account was reactivated and its preferred email was set, but
        # its display name was not changed.
        identifiers = [i.identifier for i in account.openid_identifiers]
        self.assertIn(identifier, identifiers)

        self.assertEqual(AccountStatus.ACTIVE, account.status)
        self.assertEqual(
            email, removeSecurityProxy(person.preferredemail).email)
        person = IPerson(account, None)
        self.assertIsNot(None, person)
        self.assertEqual('Test account', person.displayname)

        # We also update the last_write flag in the session, to make sure
        # further requests use the master DB and thus see the newly created
        # stuff.
        self.assertLastWriteIsSet(view.request)

    def test_deactivated_account(self):
        # The user has the account's password and is trying to login, so we'll
        # just re-activate their account.
        email = 'foo@example.com'
        person = self.factory.makePerson(
            displayname='Test account', email=email,
            account_status=AccountStatus.DEACTIVATED,
            email_address_status=EmailAddressStatus.NEW)
        openid_identifier = removeSecurityProxy(
            person.account).openid_identifiers.any().identifier
        openid_response = FakeOpenIDResponse(
            'http://testopenid.test/+id/%s' % openid_identifier,
            status=SUCCESS, email=email, full_name=person.displayname)
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createAndRenderView(openid_response)
        self.assertTrue(view.login_called)
        response = view.request.response
        self.assertEqual(http_client.TEMPORARY_REDIRECT, response.getStatus())
        self.assertEqual(view.request.form['starting_url'],
                         response.getHeader('Location'))
        self.assertEqual(AccountStatus.ACTIVE, person.account.status)
        self.assertEqual(email, person.preferredemail.email)
        # We also update the last_write flag in the session, to make sure
        # further requests use the master DB and thus see the newly created
        # stuff.
        self.assertLastWriteIsSet(view.request)

    def test_never_used_account(self):
        # The account was created by one of our scripts but was never
        # activated, so we just activate it.
        email = 'foo@example.com'
        person = self.factory.makePerson(
            displayname='Test account', email=email,
            account_status=AccountStatus.DEACTIVATED,
            email_address_status=EmailAddressStatus.NEW)
        openid_identifier = IStore(OpenIdIdentifier).find(
            OpenIdIdentifier.identifier,
            OpenIdIdentifier.account_id == person.account.id).order_by(
                OpenIdIdentifier.account_id).order_by(
                    OpenIdIdentifier.account_id).first()
        openid_response = FakeOpenIDResponse(
            'http://testopenid.test/+id/%s' % openid_identifier,
            status=SUCCESS, email=email, full_name=person.displayname)
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createAndRenderView(openid_response)
        self.assertTrue(view.login_called)
        self.assertEqual(AccountStatus.ACTIVE, person.account.status)
        self.assertEqual(email, person.preferredemail.email)
        # We also update the last_write flag in the session, to make sure
        # further requests use the master DB and thus see the newly created
        # stuff.
        self.assertLastWriteIsSet(view.request)

    def test_suspended_account(self):
        # There's a chance that our OpenID Provider lets a suspended account
        # login, but we must not allow that.
        person = self.factory.makePerson(
            account_status=AccountStatus.SUSPENDED)
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createViewWithResponse(person.account)
        self.assertFalse(view.login_called)
        main_content = extract_text(find_main_content(html))
        self.assertIn('This account has been suspended', main_content)

    def test_deceased_account(self):
        # There's a chance that our OpenID Provider lets a deceased account
        # login, but we must not allow that.
        person = self.factory.makePerson(
            account_status=AccountStatus.DECEASED)
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createViewWithResponse(person.account)
        self.assertFalse(view.login_called)
        main_content = extract_text(find_main_content(html))
        self.assertIn('This account belongs to a deceased user', main_content)

    def test_account_with_team_email_address(self):
        # If the email address from the OpenID provider is owned by a
        # team, there's not much we can do. See bug #556680 for
        # discussions about a proper solution.
        self.factory.makeTeam(email="foo@bar.com")

        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createViewWithResponse(
                None, email="foo@bar.com",
                identifier=self.factory.getUniqueString())
        self.assertFalse(view.login_called)
        main_content = extract_text(find_main_content(html))
        self.assertIn('Team email address conflict', main_content)

    def test_missing_fields(self):
        # If the OpenID provider response does not include required fields
        # (full name or email missing), the login error page is shown.
        person = self.factory.makePerson()
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createViewWithResponse(
                person.account, email=None)
        self.assertFalse(view.login_called)
        main_content = extract_text(find_main_content(html))
        self.assertIn(
            'No email address or full name found in sreg response',
            main_content)

    def test_discharge_macaroon(self):
        # If a discharge macaroon was requested and received, the view
        # returns a form that submits it to the starting URL.
        test_email = 'test-example@example.com'
        person = self.factory.makePerson(email=test_email)
        identifier = ITestOpenIDPersistentIdentity(
            person.account).openid_identity_url
        openid_response = FakeOpenIDResponse(
            identifier, status=SUCCESS, message='', email=test_email,
            full_name='Foo User', discharge_macaroon_raw='dummy discharge')
        form = {
            'starting_url': 'http://launchpad.test/after-login',
            'discharge_macaroon_action': 'field.actions.complete',
            'discharge_macaroon_field': 'field.discharge_macaroon',
            }
        with SRegResponse_fromSuccessResponse_stubbed():
            with MacaroonResponse_fromSuccessResponse_stubbed():
                view, html = self._createAndRenderView(
                    openid_response, form=form)
        self.assertTrue(view.login_called)
        self.assertEqual('dummy discharge', view.discharge_macaroon_raw)
        discharge_form = find_tag_by_id(html, 'discharge-form')
        self.assertEqual(form['starting_url'], discharge_form['action'])
        self.assertThat(
            [dict(tag.attrs) for tag in discharge_form.find_all('input')],
            MatchesListwise([
                ContainsDict({
                    'type': Equals('hidden'),
                    'name': Equals('field.actions.complete'),
                    'value': Equals('1'),
                    }),
                ContainsDict({
                    'type': Equals('hidden'),
                    'name': Equals('field.discharge_macaroon'),
                    'value': Equals('dummy discharge'),
                    }),
                ContainsDict({
                    'type': Equals('submit'),
                    'value': Equals('Continue'),
                    }),
                ]))

    def test_discharge_macaroon_missing(self):
        # If a discharge macaroon was requested but not received, the login
        # error page is shown.
        test_email = 'test-example@example.com'
        person = self.factory.makePerson(email=test_email)
        identifier = ITestOpenIDPersistentIdentity(
            person.account).openid_identity_url
        openid_response = FakeOpenIDResponse(
            identifier, status=SUCCESS, message='', email=test_email,
            full_name='Foo User')
        form = {
            'starting_url': 'http://launchpad.test/after-login',
            'discharge_macaroon_action': 'field.actions.complete',
            'discharge_macaroon_field': 'field.discharge_macaroon',
            }
        with SRegResponse_fromSuccessResponse_stubbed():
            with MacaroonResponse_fromSuccessResponse_stubbed():
                view, html = self._createAndRenderView(
                    openid_response, form=form)
        self.assertFalse(view.login_called)
        main_content = extract_text(find_main_content(html))
        self.assertIn(
            "OP didn't include a macaroon extension in the response.",
            main_content)

    def test_negative_openid_assertion(self):
        # The OpenID provider responded with a negative assertion, so the
        # login error page is shown.
        person = self.factory.makePerson()
        view, html = self._createViewWithResponse(
            person.account, response_status=FAILURE,
            response_msg='Server denied check_authentication')
        self.assertFalse(view.login_called)
        main_content = extract_text(find_main_content(html))
        self.assertIn('Your login was unsuccessful', main_content)

    def test_negative_openid_assertion_when_user_already_logged_in(self):
        # The OpenID provider responded with a negative assertion, but the
        # user already has a valid cookie, so we add a notification message to
        # the response and redirect to the starting_url specified in the
        # OpenID response.
        test_person = self.factory.makePerson()

        class StubbedOpenIDCallbackViewLoggedIn(StubbedOpenIDCallbackView):
            account = test_person.account

        view, html = self._createViewWithResponse(
            test_person.account, response_status=FAILURE,
            response_msg='Server denied check_authentication',
            view_class=StubbedOpenIDCallbackViewLoggedIn)
        self.assertFalse(view.login_called)
        response = view.request.response
        self.assertEqual(http_client.TEMPORARY_REDIRECT, response.getStatus())
        self.assertEqual(view.request.form['starting_url'],
                         response.getHeader('Location'))
        notification_msg = view.request.response.notifications[0].message
        expected_msg = ('Your authentication failed but you were already '
                        'logged into Launchpad')
        self.assertIn(expected_msg, notification_msg)

    def test_IAccountSet_getByOpenIDIdentifier_monkey_patched(self):
        with IAccountSet_getByOpenIDIdentifier_monkey_patched():
            self.assertRaises(
                AssertionError,
                getUtility(IAccountSet).getByOpenIDIdentifier, u'foo')

    def test_logs_to_timeline(self):
        # Completing an OpenID association *can* make an HTTP request to the
        # OP, so it's a potentially long action. It is logged to the
        # request timeline.
        person = self.factory.makePerson()
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createViewWithResponse(person.account)
        start, stop = get_request_timeline(view.request).actions[-2:]
        self.assertEqual(start.category, 'openid-association-complete-start')
        self.assertEqual(start.detail, '')
        self.assertEqual(stop.category, 'openid-association-complete-stop')
        self.assertEqual(stop.detail, '')

    def assertLastWriteIsSet(self, request):
        last_write = ISession(request)['lp.dbpolicy']['last_write']
        self.assertTrue(datetime.utcnow() - last_write < timedelta(minutes=1))


class TestOpenIDCallbackRedirects(TestCaseWithFactory):
    layer = FunctionalLayer

    APPLICATION_URL = 'http://example.com'
    STARTING_URL = APPLICATION_URL + '/start'

    def test_open_id_callback_redirect_from_get(self):
        # If OpenID callback request was a GET, the starting_url is extracted
        # correctly.
        view = OpenIDCallbackView(context=None, request=None)
        view.request = LaunchpadTestRequest(
            SERVER_URL=self.APPLICATION_URL,
            form={'starting_url': self.STARTING_URL})
        view.initialize()
        view._redirect()
        self.assertEqual(
            http_client.TEMPORARY_REDIRECT, view.request.response.getStatus())
        self.assertEqual(
            view.request.response.getHeader('Location'), self.STARTING_URL)

    def test_open_id_callback_redirect_from_post(self):
        # If OpenID callback request was a POST, the starting_url is extracted
        # correctly.
        view = OpenIDCallbackView(context=None, request=None)
        view.request = LaunchpadTestRequest(
            SERVER_URL=self.APPLICATION_URL, form={'fake': 'value'},
            QUERY_STRING='starting_url=' + self.STARTING_URL)
        view.initialize()
        view._redirect()
        self.assertEqual(
            http_client.TEMPORARY_REDIRECT, view.request.response.getStatus())
        self.assertEqual(
            view.request.response.getHeader('Location'), self.STARTING_URL)

    def test_openid_callback_redirect_fallback(self):
        # If OpenID callback request was a POST or GET with no form or query
        # string values at all, then the application URL is used.
        view = OpenIDCallbackView(context=None, request=None)
        view.request = LaunchpadTestRequest(SERVER_URL=self.APPLICATION_URL)
        view.initialize()
        view._redirect()
        self.assertEqual(
            http_client.TEMPORARY_REDIRECT, view.request.response.getStatus())
        self.assertEqual(
            view.request.response.getHeader('Location'), self.APPLICATION_URL)


def fill_login_form_and_submit(browser, email_address):
    assert browser.getControl(name='field.email') is not None, (
        "We don't seem to be looking at a login form.")
    browser.getControl(name='field.email').value = email_address
    browser.getControl('Continue').click()


class TestOpenIDReplayAttack(TestCaseWithFactory):
    layer = AppServerLayer

    def test_replay_attacks_do_not_succeed(self):
        browser = Browser()
        browser.followRedirects = False
        browser.open('%s/+login' % self.layer.appserver_root_url())
        # On a JS-enabled browser this page would've been auto-submitted
        # (thanks to the onload handler), but here we have to do it manually.
        self.assertIn('body onload', browser.contents)
        browser.getControl('Continue').click()

        self.assertEqual('Login', browser.title)
        fill_login_form_and_submit(browser, 'test@canonical.com')
        self.assertEqual(
            http_client.FOUND, int(browser.headers['Status'].split(' ', 1)[0]))
        callback_url = browser.headers['Location']
        self.assertIn('+openid-callback', callback_url)
        browser.open(callback_url)
        self.assertEqual(
            http_client.TEMPORARY_REDIRECT,
            int(browser.headers['Status'].split(' ', 1)[0]))
        browser.open(browser.headers['Location'])
        login_status = extract_text(
            find_tag_by_id(browser.contents, 'logincontrol'))
        self.assertIn('Sample Person (name12)', login_status)

        # Now we open the +openid-callback URL that was used to complete the
        # authentication on a different browser with a fresh set of cookies.
        replay_browser = Browser()
        replay_browser.open(callback_url)
        login_status = extract_text(
            find_tag_by_id(replay_browser.contents, 'logincontrol'))
        self.assertEqual('Log in / Register', login_status)
        error_msg = find_tags_by_class(replay_browser.contents, 'error')[0]
        self.assertEqual('Nonce already used or out of range',
                         extract_text(error_msg))


class FakeHTTPResponse:
    status = 500


class OpenIDConsumerThatFailsDiscovery:

    def begin(self, url):
        raise DiscoveryFailure(
            'HTTP Response status from identity URL host is not 200. '
            'Got status 500', FakeHTTPResponse)


class TestMissingServerShowsNiceErrorPage(TestCase):
    layer = DatabaseFunctionalLayer

    def test_missing_openid_server_shows_nice_error_page(self):
        fixture = ZopeViewReplacementFixture('+login', ILaunchpadApplication)

        class OpenIDLoginThatFailsDiscovery(fixture.original):
            def _getConsumer(self):
                return OpenIDConsumerThatFailsDiscovery()

        fixture.replacement = OpenIDLoginThatFailsDiscovery
        self.useFixture(fixture)
        browser = TestBrowser()
        self.assertRaises(HTTPError,
                          browser.open, 'http://launchpad.test/+login')
        self.assertEqual('503 Service Unavailable',
                         browser.headers.get('status'))
        self.assertTrue(
            'OpenID Provider Is Unavailable at This Time' in browser.contents)


class FakeOpenIDRequest:
    extensions = None
    return_to = None

    def addExtension(self, extension):
        if self.extensions is None:
            self.extensions = [extension]
        else:
            self.extensions.append(extension)

    def shouldSendRedirect(self):
        return False

    def htmlMarkup(self, trust_root, return_to):
        self.return_to = return_to
        return None


class FakeOpenIDConsumer:

    def begin(self, url):
        return FakeOpenIDRequest()


class StubbedOpenIDLogin(OpenIDLogin):

    def _getConsumer(self):
        return FakeOpenIDConsumer()


class ForwardsCorrectly:
    """Match query_strings which get forwarded correctly.

    Correctly is defined as the form parameters ending up simply urllib quoted
    wrapped in the return_to url.
    """

    def match(self, query_string):
        args = dict(parse_qsl(query_string))
        request = LaunchpadTestRequest(form=args)
        request.processInputs()
        # This is a hack to make the request.getURL(1) call issued by the view
        # not raise an IndexError.
        request._app_names = ['foo']
        view = StubbedOpenIDLogin(object(), request)
        view()
        escaped_args = tuple(map(quote, list(args.items())[0]))
        expected_fragment = quote('%s=%s' % escaped_args)
        return Contains(
            expected_fragment).match(view.openid_request.return_to)

    def __str__(self):
        return 'ForwardsCorrectly()'


class TestOpenIDLogin(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_return_to_with_non_ascii_value_bug_61171(self):
        # Sometimes the +login link will have non-ascii characters in the
        # query param values, and we need to include those in the return_to
        # URL that we pass to the OpenID provider. The params may not be
        # legimate utf8 even.
        self.assertThat('key=value\x85', ForwardsCorrectly())

    def test_return_to_with_non_ascii_key_bug_897039(self):
        # Sometimes the +login link will have non-ascii characters in the
        # query param keys, and we need to include those in the return_to URL
        # that we pass to the OpenID provider. The params may not be legimate
        # utf8 even.
        self.assertThat('key\x85=value', ForwardsCorrectly())

    def test_unicode_form_params_bug_898638(self):
        # Sometimes the form params are unicode because a decode('utf8')
        # worked in the form machinery... and if so they cannot be trivially
        # quoted but must be encoded first.
        key = quote(u'key\xf3'.encode('utf8'))
        value = quote(u'value\xf3'.encode('utf8'))
        query_string = "%s=%s" % (key, value)
        self.assertThat(query_string, ForwardsCorrectly())

    def test_sreg_fields(self):
        # We request the user's email address and Full Name (through the SREG
        # extension) to the OpenID provider so that we can automatically
        # register unseen OpenID identities.
        request = LaunchpadTestRequest()
        request.processInputs()
        # This is a hack to make the request.getURL(1) call issued by the view
        # not raise an IndexError.
        request._app_names = ['foo']
        view = StubbedOpenIDLogin(object(), request)
        view()
        extensions = view.openid_request.extensions
        self.assertIsNot(None, extensions)
        sreg_extension = extensions[0]
        self.assertIsInstance(sreg_extension, sreg.SRegRequest)
        self.assertEqual(['email', 'fullname'],
                         sorted(sreg_extension.allRequestedFields()))
        self.assertEqual(sorted(sreg_extension.required),
                         sorted(sreg_extension.allRequestedFields()))

    def test_pape_extension_added_with_reauth_query(self):
        # We can signal that a request should be reauthenticated via
        # a reauth URL parameter, which should add PAPE extension's
        # max_auth_age paramter.
        request = LaunchpadTestRequest(QUERY_STRING='reauth=1')
        request.processInputs()
        # This is a hack to make the request.getURL(1) call issued by the view
        # not raise an IndexError.
        request._app_names = ['foo']
        view = StubbedOpenIDLogin(object(), request)
        view()
        extensions = view.openid_request.extensions
        self.assertIsNot(None, extensions)
        pape_extension = extensions[1]
        self.assertIsInstance(pape_extension, pape.Request)
        self.assertEqual(0, pape_extension.max_auth_age)

    def test_macaroon_extension_added_with_macaroon_query(self):
        # We can signal that we need to acquire a discharge macaroon via a
        # macaroon_caveat_id form parameter, which should add the macaroon
        # extension.
        caveat_id = 'ask SSO'
        form = {
            'macaroon_caveat_id': caveat_id,
            'discharge_macaroon_action': 'field.actions.complete',
            'discharge_macaroon_field': 'field.discharge_macaroon',
            }
        request = LaunchpadTestRequest(form=form, method='POST')
        request.processInputs()
        # This is a hack to make the request.getURL(1) call issued by the view
        # not raise an IndexError.
        request._app_names = ['foo']
        view = StubbedOpenIDLogin(object(), request)
        view()
        extensions = view.openid_request.extensions
        self.assertIsNot(None, extensions)
        macaroon_extension = extensions[1]
        self.assertIsInstance(macaroon_extension, MacaroonRequest)
        self.assertEqual(caveat_id, macaroon_extension.caveat_id)
        return_to_args = dict(parse_qsl(
            urlsplit(view.openid_request.return_to).query))
        self.assertEqual(
            'field.actions.complete',
            return_to_args['discharge_macaroon_action'])
        self.assertEqual(
            'field.discharge_macaroon',
            return_to_args['discharge_macaroon_field'])

    def test_logs_to_timeline(self):
        # Beginning an OpenID association makes an HTTP request to the
        # OP, so it's a potentially long action. It is logged to the
        # request timeline.
        request = LaunchpadTestRequest()
        request.processInputs()
        # This is a hack to make the request.getURL(1) call issued by the view
        # not raise an IndexError.
        request._app_names = ['foo']
        view = StubbedOpenIDLogin(object(), request)
        view()
        start, stop = get_request_timeline(request).actions[-2:]
        self.assertEqual(start.category, 'openid-association-begin-start')
        self.assertEqual(start.detail, 'http://testopenid.test/')
        self.assertEqual(stop.category, 'openid-association-begin-stop')
        self.assertEqual(stop.detail, 'http://testopenid.test/')


class TestOpenIDRealm(TestCaseWithFactory):
    # The realm (aka trust_root) specified by the RP is "designed to give the
    # end user an indication of the scope of the authentication request", so
    # for us the realm will always be the root URL of the mainsite.
    layer = AppServerLayer

    def test_realm_for_mainsite(self):
        browser = Browser()
        browser.open('%s/+login' % self.layer.appserver_root_url())
        # At this point browser.contents contains a hidden form which would've
        # been auto-submitted if we had in-browser JS support, but since we
        # don't we can easily inspect what's in the form.
        self.assertEqual('%s/' % browser.rooturl,
                         browser.getControl(name='openid.realm').value)

    def test_realm_for_vhosts(self):
        browser = Browser()
        browser.open('%s/+login' % self.layer.appserver_root_url('bugs'))
        # At this point browser.contents contains a hidden form which would've
        # been auto-submitted if we had in-browser JS support, but since we
        # don't we can easily inspect what's in the form.
        self.assertEqual('%s'
                         % self.layer.appserver_root_url(ensureSlash=True),
                         browser.getControl(name='openid.realm').value)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(LayeredDocFileSuite(
        'login.txt', setUp=setUp, layer=AppServerLayer))
    return suite
