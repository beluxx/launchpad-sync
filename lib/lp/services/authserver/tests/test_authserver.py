# Copyright 2009-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the internal codehosting API."""

import xmlrpc.client

from pymacaroons import Macaroon
from storm.sqlobject import SQLObjectNotFound
from testtools.matchers import (
    Equals,
    Is,
    MatchesListwise,
    MatchesStructure,
    )
from zope.component import getUtility
from zope.interface import implementer
from zope.publisher.xmlrpc import TestRequest

from lp.services.authserver.interfaces import (
    IAuthServer,
    IAuthServerApplication,
    )
from lp.services.authserver.xmlrpc import AuthServerAPIView
from lp.services.config import config
from lp.services.identity.interfaces.account import AccountStatus
from lp.services.librarian.interfaces import (
    ILibraryFileAlias,
    ILibraryFileAliasSet,
    )
from lp.services.macaroons.interfaces import (
    BadMacaroonContext,
    IMacaroonIssuer,
    NO_USER,
    )
from lp.services.macaroons.model import MacaroonIssuerBase
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.xmlrpc import XMLRPCTestTransport
from lp.xmlrpc import faults
from lp.xmlrpc.interfaces import IPrivateApplication


class TestAuthServerInterfaces(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_application_interface(self):
        # The AuthServer interface is available on the authserver attribute
        # of our private XML-RPC instance.
        private_root = getUtility(IPrivateApplication)
        self.assertTrue(
            verifyObject(IAuthServerApplication, private_root.authserver))

    def test_api_interface(self):
        # The AuthServerAPIView provides the IAuthServer XML-RPC API.
        private_root = getUtility(IPrivateApplication)
        authserver_api = AuthServerAPIView(
            private_root.authserver, TestRequest())
        self.assertTrue(verifyObject(IAuthServer, authserver_api))


class GetUserAndSSHKeysTests(TestCaseWithFactory):
    """Tests for the implementation of `IAuthServer.getUserAndSSHKeys`.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        private_root = getUtility(IPrivateApplication)
        self.authserver = AuthServerAPIView(
            private_root.authserver, TestRequest())

    def test_user_not_found(self):
        # getUserAndSSHKeys returns the NoSuchPersonWithName fault if there is
        # no Person of the given name.
        self.assertEqual(
            faults.NoSuchPersonWithName('no-one'),
            self.authserver.getUserAndSSHKeys('no-one'))

    def test_user_no_keys(self):
        # getUserAndSSHKeys returns a dict with keys ['id', 'name', 'keys'].
        # 'keys' refers to a list of SSH public keys in LP, which is empty for
        # a freshly created user.
        new_person = self.factory.makePerson()
        self.assertEqual(
            dict(id=new_person.id, name=new_person.name, keys=[]),
            self.authserver.getUserAndSSHKeys(new_person.name))

    def test_user_with_keys(self):
        # For a user with registered SSH keys, getUserAndSSHKeys returns the
        # name of the key type (RSA or DSA) and the text of the keys under
        # 'keys' in the dict.
        new_person = self.factory.makePerson()
        with person_logged_in(new_person):
            key = self.factory.makeSSHKey(person=new_person)
            self.assertEqual(
                dict(id=new_person.id, name=new_person.name,
                     keys=[(key.keytype.title, key.keytext)]),
                self.authserver.getUserAndSSHKeys(new_person.name))

    def test_inactive_user_with_keys(self):
        # getUserAndSSHKeys returns the InactiveAccount fault if the given
        # name refers to an inactive account.
        new_person = self.factory.makePerson(
            account_status=AccountStatus.SUSPENDED)
        with person_logged_in(new_person):
            self.factory.makeSSHKey(person=new_person)
            self.assertEqual(
                faults.InactiveAccount(new_person.name),
                self.authserver.getUserAndSSHKeys(new_person.name))

    def test_via_xmlrpc(self):
        new_person = self.factory.makePerson()
        with person_logged_in(new_person):
            key = self.factory.makeSSHKey(person=new_person)
        authserver = xmlrpc.client.ServerProxy(
            'http://xmlrpc-private.launchpad.test:8087/authserver',
            transport=XMLRPCTestTransport())
        self.assertEqual(
            {'id': new_person.id, 'name': new_person.name,
             'keys': [[key.keytype.title, key.keytext]]},
            authserver.getUserAndSSHKeys(new_person.name))


@implementer(IMacaroonIssuer)
class DummyMacaroonIssuer(MacaroonIssuerBase):

    identifier = 'test'
    issuable_via_authserver = True
    _root_secret = 'test'
    _verified_user = NO_USER

    def checkIssuingContext(self, context, **kwargs):
        """See `MacaroonIssuerBase`."""
        if not ILibraryFileAlias.providedBy(context):
            raise BadMacaroonContext(context)
        return context.id

    def checkVerificationContext(self, context, **kwargs):
        """See `IMacaroonIssuerBase`."""
        if not ILibraryFileAlias.providedBy(context):
            raise BadMacaroonContext(context)
        return context

    def verifyPrimaryCaveat(self, verified, caveat_value, context, **kwargs):
        """See `MacaroonIssuerBase`."""
        ok = caveat_value == str(context.id)
        if ok:
            verified.user = self._verified_user
        return ok


class MacaroonTests(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super().setUp()
        self.issuer = DummyMacaroonIssuer()
        self.useFixture(ZopeUtilityFixture(
            self.issuer, IMacaroonIssuer, name='test'))
        private_root = getUtility(IPrivateApplication)
        self.authserver = AuthServerAPIView(
            private_root.authserver, TestRequest())

    def test_issue_unknown_issuer(self):
        self.assertEqual(
            faults.PermissionDenied(),
            self.authserver.issueMacaroon(
                'unknown-issuer', 'LibraryFileAlias', 1))

    def test_issue_wrong_context_type(self):
        self.assertEqual(
            faults.PermissionDenied(),
            self.authserver.issueMacaroon(
                'unknown-issuer', 'nonsense', 1))

    def test_issue_not_issuable_via_authserver(self):
        self.issuer.issuable_via_authserver = False
        self.assertEqual(
            faults.PermissionDenied(),
            self.authserver.issueMacaroon('test', 'LibraryFileAlias', 1))

    def test_issue_bad_context(self):
        build = self.factory.makeSnapBuild()
        self.assertEqual(
            faults.PermissionDenied(),
            self.authserver.issueMacaroon('test', 'SnapBuild', build.id))

    def test_issue_success(self):
        macaroon = Macaroon.deserialize(
            self.authserver.issueMacaroon('test', 'LibraryFileAlias', 1))
        self.assertThat(macaroon, MatchesStructure(
            location=Equals(config.vhost.mainsite.hostname),
            identifier=Equals('test'),
            caveats=MatchesListwise([
                MatchesStructure.byEquality(caveat_id='lp.test 1'),
                ])))

    def test_verify_nonsense_macaroon(self):
        self.assertEqual(
            faults.Unauthorized(),
            self.authserver.verifyMacaroon('nonsense', 'LibraryFileAlias', 1))

    def test_verify_unknown_issuer(self):
        macaroon = Macaroon(
            location=config.vhost.mainsite.hostname,
            identifier='unknown-issuer', key='test')
        self.assertEqual(
            faults.Unauthorized(),
            self.authserver.verifyMacaroon(
                macaroon.serialize(), 'LibraryFileAlias', 1))

    def test_verify_wrong_context_type(self):
        lfa = getUtility(ILibraryFileAliasSet)[1]
        macaroon = self.issuer.issueMacaroon(lfa)
        self.assertEqual(
            faults.Unauthorized(),
            self.authserver.verifyMacaroon(
                macaroon.serialize(), 'nonsense', lfa.id))

    def test_verify_wrong_context(self):
        lfa = getUtility(ILibraryFileAliasSet)[1]
        macaroon = self.issuer.issueMacaroon(lfa)
        self.assertEqual(
            faults.Unauthorized(),
            self.authserver.verifyMacaroon(
                macaroon.serialize(), 'LibraryFileAlias', 2))

    def test_verify_nonexistent_lfa(self):
        macaroon = self.issuer.issueMacaroon(
            getUtility(ILibraryFileAliasSet)[1])
        # Pick a large ID that doesn't exist in sampledata.
        lfa_id = 1000000
        self.assertRaises(
            SQLObjectNotFound, getUtility(ILibraryFileAliasSet).__getitem__,
            lfa_id)
        self.assertEqual(
            faults.Unauthorized(),
            self.authserver.verifyMacaroon(
                macaroon.serialize(), 'LibraryFileAlias', lfa_id))

    def test_verify_unverified_user(self):
        # The authserver refuses macaroons whose issuer doesn't explicitly
        # indicate whether they were issued on behalf of a particular user.
        self.issuer._verified_user = None
        lfa = getUtility(ILibraryFileAliasSet)[1]
        macaroon = self.issuer.issueMacaroon(lfa)
        self.assertEqual(
            faults.Unauthorized(),
            self.authserver.verifyMacaroon(
                macaroon.serialize(), 'LibraryFileAlias', lfa.id))

    def test_verify_specific_user(self):
        # The authserver refuses macaroons that were issued on behalf of a
        # particular user, rather than being standalone.
        self.issuer._verified_user = self.factory.makePerson()
        lfa = getUtility(ILibraryFileAliasSet)[1]
        macaroon = self.issuer.issueMacaroon(lfa)
        self.assertEqual(
            faults.Unauthorized(),
            self.authserver.verifyMacaroon(
                macaroon.serialize(), 'LibraryFileAlias', lfa.id))

    def test_verify_success(self):
        lfa = getUtility(ILibraryFileAliasSet)[1]
        macaroon = self.issuer.issueMacaroon(lfa)
        self.assertThat(
            self.authserver.verifyMacaroon(
                macaroon.serialize(), 'LibraryFileAlias', lfa.id),
            Is(True))
