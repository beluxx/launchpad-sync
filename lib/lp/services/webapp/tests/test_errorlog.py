# Copyright 2009-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for error logging & OOPS reporting."""

import http.client
import sys
import traceback
from textwrap import dedent

import oops_amqp
import testtools
from fixtures import TempDir
from lazr.batchnavigator.interfaces import InvalidBatchSizeError
from lazr.restful.declarations import error_status
from talisker.logs import logging_context
from timeline.timeline import Timeline
from zope.interface import directlyProvides
from zope.principalregistry.principalregistry import UnauthenticatedPrincipal
from zope.publisher.browser import TestRequest
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.xmlrpc import IXMLRPCRequest
from zope.security.interfaces import Unauthorized

from lp.app.errors import GoneError, TranslationUnavailable
from lp.layers import WebServiceLayer
from lp.services.config import config
from lp.services.database.sqlbase import flush_database_caches
from lp.services.webapp.authentication import LaunchpadPrincipal
from lp.services.webapp.errorlog import (
    ErrorReportingUtility,
    ScriptRequest,
    _filter_session_statement,
    _is_sensitive,
    attach_http_request,
    notify_publisher,
)
from lp.services.webapp.interfaces import IUnloggedException, NoReferrerError
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer


class ArbitraryException(Exception):
    """Used to test handling of exceptions in OOPS reports."""


class TestErrorReportingUtility(TestCaseWithFactory):
    # want rabbit
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super().setUp()
        # ErrorReportingUtility reads the global config to get the
        # current error directory.
        tempdir = self.useFixture(TempDir()).path
        test_data = dedent(
            """
            [error_reports]
            error_dir: %s
            """
            % tempdir
        )
        config.push("test_data", test_data)
        self.addCleanup(config.pop, "test_data")

    def test_configure(self):
        """Test ErrorReportingUtility.setConfigSection()."""
        utility = ErrorReportingUtility()
        # The ErrorReportingUtility uses the config.error_reports section
        # by default.
        self.assertEqual(config.error_reports.oops_prefix, utility.oops_prefix)
        self.assertEqual(
            config.error_reports.error_dir, utility._oops_datedir_repo.root
        )
        # Some external processes may extend the reporter/prefix with
        # extra information.
        utility.configure(section_name="branchscanner")
        self.assertEqual("T-branchscanner", utility.oops_prefix)

        # The default error section can be restored.
        utility.configure()
        self.assertEqual(config.error_reports.oops_prefix, utility.oops_prefix)

        # We should have had two publishers set up:
        self.assertEqual(2, len(utility._all_publishers))
        # - a fallback publisher chaining a rabbit publisher and a datedir
        #   publisher
        self.assertIsInstance(utility._main_publishers[0], oops_amqp.Publisher)
        self.assertEqual(
            utility._main_publishers[1], utility._oops_datedir_repo.publish
        )
        # - a notify publisher
        self.assertEqual(utility._all_publishers[1], notify_publisher)

    def test_multiple_raises_in_request(self):
        """An OOPS links to the previous OOPS in the request, if any."""
        utility = ErrorReportingUtility()
        utility._main_publishers[0].__call__ = lambda report: []

        request = TestRequestWithPrincipal()
        try:
            raise ArbitraryException("foo")
        except ArbitraryException:
            report = utility.raising(sys.exc_info(), request)

        self.assertFalse("last_oops" in report)
        self.assertEqual(report["id"], logging_context.flat["oopsid"])
        last_oopsid = request.oopsid
        try:
            raise ArbitraryException("foo")
        except ArbitraryException:
            report = utility.raising(sys.exc_info(), request)

        self.assertTrue("last_oops" in report)
        self.assertEqual(report["last_oops"], last_oopsid)
        self.assertEqual(report["id"], logging_context.flat["oopsid"])

    def test_raising_with_request(self):
        """Test ErrorReportingUtility.raising() with a request"""
        utility = ErrorReportingUtility()
        utility._main_publishers[0].__call__ = lambda report: []

        request = TestRequestWithPrincipal(
            environ={
                "SERVER_URL": "http://localhost:9000/foo",
                "HTTP_COOKIE": "lp=cookies_hidden_for_security_reasons",
                "name1": "value1",
            },
            form={
                "name1": "value3 \xa7",
                "name2": "value2",
                "\N{BLACK SQUARE}": "value4",
            },
        )
        request.setInWSGIEnvironment("launchpad.pageid", "IFoo:+foo-template")

        try:
            raise ArbitraryException("xyz\nabc")
        except ArbitraryException:
            report = utility.raising(sys.exc_info(), request)

        # topic is obtained from the request
        self.assertEqual("IFoo:+foo-template", report["topic"])
        self.assertEqual(
            "account-name, 42, account-name, description |\u25a0|",
            report["username"],
        )
        self.assertEqual("http://localhost:9000/foo", report["url"])
        self.assertEqual(
            {
                "CONTENT_LENGTH": "0",
                "GATEWAY_INTERFACE": "TestFooInterface/1.0",
                "HTTP_COOKIE": "<hidden>",
                "HTTP_HOST": "127.0.0.1",
                "SERVER_URL": "http://localhost:9000/foo",
                "\u25a0": "value4",
                "lp": "<hidden>",
                "name1": "value3 \xa7",
                "name2": "value2",
            },
            report["req_vars"],
        )
        # verify that the oopsid was set on the request
        self.assertEqual(request.oopsid, report["id"])
        self.assertEqual(request.oops, report)
        self.assertEqual(report["id"], logging_context.flat["oopsid"])

    def test_raising_request_with_principal_person(self):
        utility = ErrorReportingUtility()
        utility._main_publishers[0].__call__ = lambda report: []

        # Attach a person to the request; the report uses their name.
        person = self.factory.makePerson(name="my-username")
        request = TestRequestWithPrincipal(account=person.account)

        # Make sure Storm would have to reload person.name if it were used.
        flush_database_caches()

        try:
            raise ArbitraryException("xyz\nabc")
        except ArbitraryException:
            report = self.assertStatementCount(
                0, utility.raising, sys.exc_info(), request
            )
        self.assertEqual(
            "my-username, 42, account-name, description |\u25a0|",
            report["username"],
        )
        self.assertEqual(report["id"], logging_context.flat["oopsid"])

    def test_raising_request_with_principal_person_set_to_none(self):
        """
        Tests oops report generated when request.principal is set to None
        @see webapp.authentication.PlacelessAuthUtility
             (_authenticateUsingCookieAuth method) for details
             about when the principal could be set to None
        """
        utility = ErrorReportingUtility()
        utility._main_publishers[0].__call__ = lambda report: []

        request = TestRequestWithPrincipal()

        # Explicitly sets principal.person to None; the report falls back to
        # the account's display name.
        request.principal.person = None

        try:
            raise ArbitraryException("xyz\nabc")
        except ArbitraryException:
            report = utility.raising(sys.exc_info(), request)
        self.assertEqual(
            "account-name, 42, account-name, description |\u25a0|",
            report["username"],
        )
        self.assertEqual(report["id"], logging_context.flat["oopsid"])

    def test_raising_with_xmlrpc_request(self):
        # Test ErrorReportingUtility.raising() with an XML-RPC request.
        request = TestRequest()
        directlyProvides(request, IXMLRPCRequest)
        request.getPositionalArguments = lambda: (1, 2)
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        try:
            raise ArbitraryException("xyz\nabc")
        except ArbitraryException:
            report = utility.raising(sys.exc_info(), request)
        self.assertEqual("(1, 2)", report["req_vars"]["xmlrpc args"])

    def test_raising_non_utf8_request_param_key_bug_896959(self):
        # When a form has a nonutf8 request param, the key in req_vars must
        # still be unicode (or utf8).
        request = TestRequest(form={"foo\x85": "bar"})
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        try:
            raise ArbitraryException("foo")
        except ArbitraryException:
            report = utility.raising(sys.exc_info(), request)
        for key in report["req_vars"].keys():
            if isinstance(key, bytes):
                key.decode("utf8")
            else:
                self.assertIsInstance(key, str)

    def test_raising_with_webservice_request(self):
        # Test ErrorReportingUtility.raising() with a WebServiceRequest
        # request. Only some exceptions result in OOPSes.
        request = TestRequest()
        directlyProvides(request, WebServiceLayer)
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None

        # Exceptions that don't use error_status result in OOPSes.
        try:
            raise ArbitraryException("xyz\nabc")
        except ArbitraryException:
            self.assertNotEqual(None, utility.raising(sys.exc_info(), request))

        # Exceptions with a error_status in the 500 range result
        # in OOPSes.
        @error_status(http.client.INTERNAL_SERVER_ERROR)
        class InternalServerError(Exception):
            pass

        try:
            raise InternalServerError("")
        except InternalServerError:
            self.assertNotEqual(None, utility.raising(sys.exc_info(), request))

        # Exceptions with any other error_status do not result
        # in OOPSes.
        @error_status(http.client.BAD_REQUEST)
        class BadDataError(Exception):
            pass

        try:
            raise BadDataError("")
        except BadDataError:
            self.assertEqual(None, utility.raising(sys.exc_info(), request))

    def test_raising_for_script(self):
        """Test ErrorReportingUtility.raising with a ScriptRequest."""
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None

        # A list because code using ScriptRequest expects that - ScriptRequest
        # translates it to a dict for now.
        req_vars = [
            ("name2", "value2"),
            ("name1", "value1"),
            ("name1", "value3"),
        ]
        url = "https://launchpad.net/example"
        try:
            raise ArbitraryException("xyz\nabc")
        except ArbitraryException:
            # Do not test escaping of request vars here, it is already tested
            # in test_raising_with_request.
            request = ScriptRequest(req_vars, URL=url)
            report = utility.raising(sys.exc_info(), request)

        self.assertEqual(url, report["url"])
        self.assertEqual(dict(req_vars), report["req_vars"])

    def test_raising_with_unprintable_exception(self):
        class UnprintableException(Exception):
            def __str__(self):
                raise RuntimeError("arrgh")

            __repr__ = __str__

        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        try:
            raise UnprintableException()
        except UnprintableException:
            report = utility.raising(sys.exc_info())

        unprintable = "<unprintable UnprintableException object>"
        self.assertEqual(unprintable, report["value"])
        self.assertIn(
            "UnprintableException: " + unprintable, report["tb_text"]
        )

    def test_raising_unauthorized_without_request(self):
        """Unauthorized exceptions are logged when there's no request."""
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        try:
            raise Unauthorized("xyz")
        except Unauthorized:
            oops = utility.raising(sys.exc_info())
        self.assertNotEqual(None, oops)

    def test_raising_unauthorized_without_principal(self):
        """Unauthorized exceptions are logged when the request has no
        principal."""
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        request = ScriptRequest([("name2", "value2")])
        try:
            raise Unauthorized("xyz")
        except Unauthorized:
            self.assertNotEqual(None, utility.raising(sys.exc_info(), request))

    def test_raising_unauthorized_with_unauthenticated_principal(self):
        """Unauthorized exceptions are not logged when the request has an
        unauthenticated principal."""
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        request = TestRequestWithUnauthenticatedPrincipal()
        try:
            raise Unauthorized("xyz")
        except Unauthorized:
            self.assertEqual(None, utility.raising(sys.exc_info(), request))

    def test_raising_unauthorized_with_authenticated_principal(self):
        """Unauthorized exceptions are logged when the request has an
        authenticated principal."""
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        request = TestRequestWithPrincipal()
        try:
            raise Unauthorized("xyz")
        except Unauthorized:
            self.assertNotEqual(None, utility.raising(sys.exc_info(), request))

    def test_raising_translation_unavailable(self):
        """Test ErrorReportingUtility.raising() with a TranslationUnavailable
        exception.

        An OOPS is not recorded when a TranslationUnavailable exception is
        raised.
        """
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        self.assertTrue(
            TranslationUnavailable.__name__ in utility._ignored_exceptions,
            "TranslationUnavailable is not in _ignored_exceptions.",
        )
        try:
            raise TranslationUnavailable("xyz")
        except TranslationUnavailable:
            self.assertEqual(None, utility.raising(sys.exc_info()))

    def test_ignored_exceptions_for_offsite_referer(self):
        # Exceptions caused by bad URLs that may not be an Lp code issue.
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        errors = {
            GoneError.__name__,
            InvalidBatchSizeError.__name__,
            NotFound.__name__,
        }
        self.assertEqual(
            errors, utility._ignored_exceptions_for_offsite_referer
        )

    def test_ignored_exceptions_for_offsite_referer_reported(self):
        # Oopses are reported when Launchpad is the referer for a URL
        # that caused an exception.
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        request = TestRequest(
            environ={
                "SERVER_URL": "http://launchpad.test/fnord",
                "HTTP_REFERER": "http://launchpad.test/snarf",
            }
        )
        try:
            raise GoneError("fnord")
        except GoneError:
            self.assertNotEqual(None, utility.raising(sys.exc_info(), request))

    def test_ignored_exceptions_for_cross_vhost_referer_reported(self):
        # Oopses are reported when a Launchpad  vhost is the referer for a URL
        # that caused an exception.
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        request = TestRequest(
            environ={
                "SERVER_URL": "http://launchpad.test/fnord",
                "HTTP_REFERER": "http://bazaar.launchpad.test/snarf",
            }
        )
        try:
            raise GoneError("fnord")
        except GoneError:
            self.assertNotEqual(None, utility.raising(sys.exc_info(), request))

    def test_ignored_exceptions_for_criss_cross_vhost_referer_reported(self):
        # Oopses are reported when a Launchpad referer for a bad URL on a
        # vhost that caused an exception.
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        request = TestRequest(
            environ={
                "SERVER_URL": "http://bazaar.launchpad.test/fnord",
                "HTTP_REFERER": "http://launchpad.test/snarf",
            }
        )
        try:
            raise GoneError("fnord")
        except GoneError:
            self.assertNotEqual(None, utility.raising(sys.exc_info(), request))

    def test_ignored_exceptions_for_offsite_referer_not_reported(self):
        # Oopses are not reported when Launchpad is not the referer.
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        # There is no HTTP_REFERER header in this request
        request = TestRequest(
            environ={"SERVER_URL": "http://launchpad.test/fnord"}
        )
        try:
            raise GoneError("fnord")
        except GoneError:
            self.assertEqual(None, utility.raising(sys.exc_info(), request))

    def test_raising_no_referrer_error(self):
        """Test ErrorReportingUtility.raising() with a NoReferrerError
        exception.

        An OOPS is not recorded when a NoReferrerError exception is
        raised.
        """
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        try:
            raise NoReferrerError("xyz")
        except NoReferrerError:
            self.assertEqual(None, utility.raising(sys.exc_info()))

    def test_raising_with_string_as_traceback(self):
        # ErrorReportingUtility.raising() can be called with a string in the
        # place of a traceback. This is useful when the original traceback
        # object is unavailable - e.g. when logging a failure reported by a
        # non-oops-enabled service.

        try:
            raise RuntimeError("hello")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            # Turn the traceback into a string. When the traceback itself
            # cannot be passed to ErrorReportingUtility.raising, a string like
            # one generated by format_exc is sometimes passed instead.
            exc_tb = traceback.format_exc()

        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        report = utility.raising((exc_type, exc_value, exc_tb))
        # traceback is what we supplied.
        self.assertEqual(exc_tb, report["tb_text"])

    def test_oopsMessage(self):
        """oopsMessage pushes and pops the messages."""
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        with utility.oopsMessage({"a": "b", "c": "d"}):
            self.assertEqual({0: {"a": "b", "c": "d"}}, utility._oops_messages)
            # An additional message doesn't supplant the original message.
            with utility.oopsMessage(dict(e="f", a="z", c="d")):
                self.assertEqual(
                    {
                        0: {"a": "b", "c": "d"},
                        1: {"a": "z", "e": "f", "c": "d"},
                    },
                    utility._oops_messages,
                )
            # Messages are removed when out of context.
            self.assertEqual({0: {"a": "b", "c": "d"}}, utility._oops_messages)

    def test__makeErrorReport_includes_oops_messages(self):
        """The error report should include the oops messages."""
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        message = {"a": "b", "c": "d"}
        with utility.oopsMessage(message):
            try:
                raise ArbitraryException("foo")
            except ArbitraryException:
                info = sys.exc_info()
                oops = utility._oops_config.create(dict(exc_info=info))
                self.assertEqual(
                    {"<oops-message-0>": str(message)}, oops["req_vars"]
                )

    def test__makeErrorReport_combines_request_and_error_vars(self):
        """The oops messages should be distinct from real request vars."""
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        request = ScriptRequest([("c", "d")])
        message = {"a": "b"}
        with utility.oopsMessage(message):
            try:
                raise ArbitraryException("foo")
            except ArbitraryException:
                info = sys.exc_info()
                oops = utility._oops_config.create(
                    dict(exc_info=info, http_request=request)
                )
                self.assertEqual(
                    {"<oops-message-0>": str(message), "c": "d"},
                    oops["req_vars"],
                )

    def test_filter_session_statement(self):
        """Removes quoted strings if database_id is SQL-session."""
        statement = "SELECT 'gone'"
        self.assertEqual(
            "SELECT '%s'", _filter_session_statement("SQL-session", statement)
        )

    def test_filter_session_statement_noop(self):
        """If database_id is not SQL-session, it's a no-op."""
        statement = "SELECT 'gone'"
        self.assertEqual(
            statement, _filter_session_statement("SQL-launchpad", statement)
        )

    def test_session_queries_filtered(self):
        """Test that session queries are filtered."""
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        timeline = Timeline()
        timeline.start("SQL-session", "SELECT 'gone'").finish()
        try:
            raise ArbitraryException("foo")
        except ArbitraryException:
            info = sys.exc_info()
            oops = utility._oops_config.create(
                dict(exc_info=info, timeline=timeline)
            )
        self.assertEqual("SELECT '%s'", oops["timeline"][0][3])


class TestSensitiveRequestVariables(testtools.TestCase):
    """Test request variables that should not end up in the stored OOPS.

    The _is_sensitive() method will return True for any variable name that
    should not be included in the OOPS.
    """

    def test_oauth_signature_is_sensitive(self):
        """The OAuth signature can be in the body of a POST request, but if
        that happens we don't want it to be included in the OOPS, so we need
        to mark it as sensitive.
        """
        request = TestRequest(
            environ={"SERVER_URL": "http://api.launchpad.test"},
            form={"oauth_signature": "&BTXPJ6pQTvh49r9p"},
        )
        self.assertTrue(_is_sensitive(request, "oauth_signature"))


class TestRequestWithUnauthenticatedPrincipal(TestRequest):
    principal = UnauthenticatedPrincipal(
        "Anonymous", "Anonymous", "Anonymous User"
    )


class TestRequestWithPrincipal(TestRequest):
    def __init__(self, account=None, *args, **kw):
        super().__init__(*args, **kw)
        self.setPrincipal(
            LaunchpadPrincipal(
                42,
                "account-name",
                # non-ASCII description
                "description |\N{BLACK SQUARE}|",
                account,
            )
        )

    def setInWSGIEnvironment(self, key, value):
        self._orig_env[key] = value


class TestOopsIgnoring(testtools.TestCase):
    def test_offsite_404_ignored(self):
        # A request originating from another site that generates a NotFound
        # (404) is ignored (i.e., no OOPS is logged).
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        report = {
            "type": "NotFound",
            "url": "http://example.com",
            "req_vars": {"HTTP_REFERER": "example.com"},
        }
        self.assertEqual(None, utility._oops_config.publish(report))

    def test_onsite_404_not_ignored(self):
        # A request originating from a local site that generates a NotFound
        # (404) produces an OOPS.
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        report = {
            "type": "NotFound",
            "url": "http://example.com",
            "req_vars": {"HTTP_REFERER": "http://launchpad.test/"},
        }
        self.assertNotEqual(None, utility._oops_config.publish(report))

    def test_404_without_referer_is_ignored(self):
        # If a 404 is generated and there is no HTTP referer, we don't produce
        # an OOPS.
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        report = {
            "type": "NotFound",
            "url": "http://example.com",
            "req_vars": {},
        }
        self.assertEqual(None, utility._oops_config.publish(report))

    def test_ignored_report_filtered(self):
        utility = ErrorReportingUtility()
        utility._oops_config.publisher = None
        report = {"ignore": True}
        self.assertEqual(None, utility._oops_config.publish(report))

    def test_marked_exception_is_ignored(self):
        # If an exception has been marked as ignorable, then it is ignored in
        # the report.
        utility = ErrorReportingUtility()
        try:
            raise ArbitraryException("xyz\nabc")
        except ArbitraryException:
            exc_info = sys.exc_info()
            directlyProvides(exc_info[1], IUnloggedException)
        report = utility._oops_config.create(dict(exc_info=exc_info))
        self.assertTrue(report["ignore"])


class TestHooks(testtools.TestCase):
    def test_attach_http_nonbasicvalue(self):
        report = {"req_vars": {}}
        complexthing = object()
        context = {
            "http_request": {"SIMPLE": "string", "COMPLEX": complexthing}
        }
        attach_http_request(report, context)
        self.assertEqual(
            {"SIMPLE": "string", "COMPLEX": str(complexthing)},
            report["req_vars"],
        )
