# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Private XMLRPC tests.
"""

import xmlrpc.client

from zope.component import getUtility

from lp.services.verification.interfaces.logintoken import ILoginTokenSet
from lp.testing import TestCase, anonymous_logged_in
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.xmlrpc import XMLRPCTestTransport


class TestPrivateXMLRPC(TestCase):
    """Several internal services require access to Launchpad data, typically
    over XML-RPC.  Because these services are internal and the data they expose
    is not needed by the outside world -- nor should it be -- Launchpad exposes
    an internal port for these private XML-RPC end points.  These internal-only
    end points are not available on the public XML-RPC port.
    """

    layer = LaunchpadFunctionalLayer

    public_root = "http://test@canonical.com:test@xmlrpc.launchpad.test/"
    private_root = "http://xmlrpc-private.launchpad.test:8087/"

    def get_public_proxy(self, path):
        """Get an xmlrpc.client.ServerProxy pointing at the public URL"""
        return xmlrpc.client.ServerProxy(
            self.public_root + path, transport=XMLRPCTestTransport()
        )

    def get_private_proxy(self, path):
        """Get an xmlrpc.client.ServerProxy pointing at the private URL"""
        return xmlrpc.client.ServerProxy(
            self.private_root + path, transport=XMLRPCTestTransport()
        )

    def test_mailing_lists_not_public(self):
        """For example, the team mailing list feature requires a connection
        between an internal Mailman server and Launchpad.  This end point is
        not available on the external XML-RPC port.
        """
        external_api = self.get_public_proxy("mailinglists/")
        e = self.assertRaises(
            xmlrpc.client.ProtocolError, external_api.getPendingActions
        )
        self.assertEqual(404, e.errcode)

    def test_mailing_lists_internally_available(self):
        """However, the end point is available on the internal port and does
        not require authentication.
        """
        internal_api = self.get_private_proxy("mailinglists/")
        self.assertEqual({}, internal_api.getPendingActions())

    def test_external_bugs_api(self):
        """The bugs API on the other hand is an external service so it is
        available on the external port.
        """
        with anonymous_logged_in():
            external_api = self.get_public_proxy("bugs/")
            bug_dict = dict(
                product="firefox", summary="the summary", comment="the comment"
            )
            result = external_api.filebug(bug_dict)
            self.assertStartsWith(result, "http://bugs.launchpad.test/bugs/")

    def test_internal_bugs_api(self):
        """There is an interal bugs api, too, but that doesn't share the same
        methods as those exposed publicly.
        """
        internal_api = self.get_private_proxy("bugs/")
        bug_dict = dict(
            product="firefox", summary="the summary", comment="the comment"
        )
        e = self.assertRaises(
            xmlrpc.client.ProtocolError, internal_api.filebug, bug_dict
        )
        self.assertEqual(404, e.errcode)

    def test_get_utility(self):
        with anonymous_logged_in():
            internal_api = self.get_private_proxy("bugs/")
            token_string = internal_api.newBugTrackerToken()
            token = getUtility(ILoginTokenSet)[token_string]
            self.assertEqual("LoginToken", token.__class__.__name__)
