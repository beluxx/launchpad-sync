# Copyright 2010-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the codehosting SSH server glue."""

__metaclass__ = type

from lazr.sshserver.auth import (
    NoSuchPersonWithName,
    SSHUserAuthServer,
    )
from lazr.sshserver.service import Factory
from twisted.conch.ssh.common import NS
from twisted.conch.ssh.keys import Key
from twisted.internet.testing import StringTransport

from lp.codehosting.sshserver.daemon import (
    get_key_path,
    get_portal,
    PRIVATE_KEY_FILE,
    PUBLIC_KEY_FILE,
    )
from lp.testing import TestCase
from lp.xmlrpc import faults


class StringTransportWith_setTcpKeepAlive(StringTransport):
    def __init__(self, hostAddress=None, peerAddress=None):
        StringTransport.__init__(self, hostAddress, peerAddress)
        self._keepAlive = False

    def setTcpKeepAlive(self, flag):
        self._keepAlive = flag


class TestFactory(TestCase):
    """Tests for our SSH factory."""

    def makeFactory(self):
        """Create and start the factory that our SSH server uses."""
        factory = Factory(
            get_portal(None, None),
            private_key=Key.fromFile(
                get_key_path(PRIVATE_KEY_FILE)),
            public_key=Key.fromFile(
                get_key_path(PUBLIC_KEY_FILE)))
        factory.startFactory()
        return factory

    def startConnecting(self, factory):
        """Connect to the `factory`."""
        server_transport = factory.buildProtocol(None)
        server_transport.makeConnection(StringTransportWith_setTcpKeepAlive())
        return server_transport

    def test_set_keepalive_on_connection(self):
        # The server transport sets TCP keep alives on the underlying
        # transport.
        factory = self.makeFactory()
        server_transport = self.startConnecting(factory)
        self.assertTrue(server_transport.transport._keepAlive)

    def beginAuthentication(self, factory):
        """Connect to `factory` and begin authentication on this connection.

        :return: The `SSHServerTransport` after the process of authentication
            has begun.
        """
        server_transport = self.startConnecting(factory)
        server_transport.ssh_SERVICE_REQUEST(NS('ssh-userauth'))
        self.addCleanup(server_transport.service.serviceStopped)
        return server_transport

    def test_authentication_uses_our_userauth_service(self):
        # The service of an SSHServerTransport after authentication has
        # started is an instance of our SSHUserAuthServer class.
        factory = self.makeFactory()
        transport = self.beginAuthentication(factory)
        self.assertIsInstance(transport.service, SSHUserAuthServer)

    def test_two_connections_two_minds(self):
        # Two attempts to authenticate do not share the user-details cache.
        factory = self.makeFactory()

        server_transport1 = self.beginAuthentication(factory)
        server_transport2 = self.beginAuthentication(factory)

        mind1 = server_transport1.service.getMind()
        mind2 = server_transport2.service.getMind()

        self.assertIsNot(mind1.cache, mind2.cache)


class TestXMLRPC(TestCase):
    """Test XML-RPC protocol integrity."""

    def test_NoSuchPersonWithName_error_code(self):
        # The error code for NoSuchPersonWithName in lazr.sshserver matches
        # that in lp.xmlrpc.faults.
        self.assertEqual(
            faults.NoSuchPersonWithName.error_code,
            NoSuchPersonWithName.error_code)
