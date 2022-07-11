# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

from doctest import DocTestSuite
import unittest

from zope.component import provideAdapter
from zope.interface import implementer
from zope.publisher.browser import TestRequest
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.http import IHTTPApplicationResponse
from zope.session.interfaces import (
    ISession,
    ISessionData,
    )

from lp.services.webapp.escaping import structured
from lp.services.webapp.interfaces import (
    INotificationRequest,
    INotificationResponse,
    )
from lp.services.webapp.notifications import NotificationResponse
from lp.testing.layers import FunctionalLayer


@implementer(ISession)
class MockSession(dict):

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            self[key] = MockSessionData()
            return super().__getitem__(key)


@implementer(ISessionData)
class MockSessionData(dict):

    lastAccessTime = 0

    def __call__(self, whatever):
        return self


@implementer(IHTTPApplicationResponse)
class MockHTTPApplicationResponse:

    def redirect(self, location, status=None, trusted=False):
        """Just report the redirection to the doctest"""
        if status is None:
            status = 302
        print('%d: %s' % (status, location))


def adaptNotificationRequestToResponse(request):
    try:
        return request.response
    except AttributeError:
        response = NotificationResponse()
        request.response = response
        response._request = request
        return response


def setUp(test):
    mock_session = MockSession()
    provideAdapter(lambda x: mock_session, (INotificationRequest,), ISession)
    provideAdapter(lambda x: mock_session, (INotificationResponse,), ISession)
    provideAdapter(
        adaptNotificationRequestToResponse,
        (INotificationRequest,), INotificationResponse)

    mock_browser_request = TestRequest()
    provideAdapter(
        lambda x: mock_browser_request, (INotificationRequest,),
        IBrowserRequest)

    test.globs['MockResponse'] = MockHTTPApplicationResponse
    test.globs['structured'] = structured


def test_suite():
    suite = unittest.TestSuite()
    doctest_suite = DocTestSuite(
        'lp.services.webapp.notifications',
        setUp=setUp,
        )
    doctest_suite.layer = FunctionalLayer
    suite.addTest(doctest_suite)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
