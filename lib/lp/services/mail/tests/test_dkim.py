# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test DKIM-signed messages"""

import logging

import dkim
import dkim.dnsplug
import six

from lp.services.features.testing import FeatureFixture
from lp.services.identity.interfaces.account import AccountStatus
from lp.services.identity.interfaces.emailaddress import EmailAddressStatus
from lp.services.mail import incoming
from lp.services.mail.incoming import (
    authenticateEmail,
    InactiveAccount,
    )
from lp.services.mail.interfaces import IWeaklyAuthenticatedPrincipal
from lp.services.mail.signedmessage import signed_message_from_bytes
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


# sample private key made with 'openssl genrsa' and public key using 'openssl
# rsa -pubout'.  Not really the key for canonical.com ;-)
sample_privkey = b"""\
-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgQC7ozYozzZuLYQi2DXSMtI3wWzWd7tAJfg+zwbOcNS4Aib6lo3R
y6ansi+fOhHSwgeOrkBGKzgHi2T8iDPzpUFhAZuOFsQaVY6yHzhXwPFi/nKYtFxU
X0DE4/GxkmNDgBOPqIpyEUQJvf5+byvb5mI85AS09em90EQGpf/a/O1Y0QIDAQAB
AoGABTPEN6NvFeTrKfAmpdpE28jgFJ4jMecbl9ozjRuxuhxNKltsOSnVSAb3rQl2
HwrEHN+V5pwiJItn1FyOXC3zvwmeKfX1J290+dleI4kNfXf97eYtJyOVVdRcreNA
7qUROmFgN8sLOWsPgvYq3IRf+QxBXD/BPVEhuHBbCJBFq8UCQQDcJ6oDk2D2+8W2
5f+3nrTBIrFtQBlApJF6q26zTOmwvOM6wrx+9wa4gAcVD8dbH2eklekTfLE3k7cU
r1WHzN5HAkEA2jAuctbruPfmTP2KctjgeEokaOq7ym5aVwcbSlTHtJZLIOjvlPmu
BhFFqZj0Yy3H1LhpYpGHrvG+uGp07h6kJwJAcIqeMKHAacGe+rZsmJM615hClxSz
VAZMkCbeui3RMJX+muU9srHY76wS8sNUJ9LQCqTPtzSA62ZJqvtOf9NMtQJAZgVp
cqE0D4U61n0nI5RtQVHJvJUlwf3fmBnmlNcXmkU8U+MXQ52L1aJ15Ft0yns5mSmx
fTl3LEI1X53HlyAUuQJALHmpSB2Qq0DqmgcAGXkDsh3GRfMv91a7u99VDT/fe+J0
2KXtp+K0MdWdAe/83icQ/WlYKIDz0Asm5FZcsTNapw==
-----END RSA PRIVATE KEY-----
"""

sample_pubkey = b"""\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC7ozYozzZuLYQi2DXSMtI3wWzW
d7tAJfg+zwbOcNS4Aib6lo3Ry6ansi+fOhHSwgeOrkBGKzgHi2T8iDPzpUFhAZuO
FsQaVY6yHzhXwPFi/nKYtFxUX0DE4/GxkmNDgBOPqIpyEUQJvf5+byvb5mI85AS0
9em90EQGpf/a/O1Y0QIDAQAB
-----END PUBLIC KEY-----
"""

sample_dns = b"""\
k=rsa; \
p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC7ozYozzZuLYQi2DXSMtI3wWzW\
d7tAJfg+zwbOcNS4Aib6lo3Ry6ansi+fOhHSwgeOrkBGKzgHi2T8iDPzpUFhAZuO\
FsQaVY6yHzhXwPFi/nKYtFxUX0DE4/GxkmNDgBOPqIpyEUQJvf5+byvb5mI85AS0\
9em90EQGpf/a/O1Y0QIDAQAB"""


class TestDKIM(TestCaseWithFactory):
    """Messages can be strongly authenticated by DKIM."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Login with admin roles as we aren't testing access here.
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        self._log_output = six.StringIO()
        handler = logging.StreamHandler(self._log_output)
        self.logger = logging.getLogger('mail-authenticate-dkim')
        self.logger.addHandler(handler)
        self.addCleanup(lambda: self.logger.removeHandler(handler))
        self.monkeypatch_dns()

    def fake_signing(self, plain_message, canonicalize=None):
        if canonicalize is None:
            canonicalize = (dkim.Relaxed, dkim.Relaxed)
        dkim_line = dkim.sign(plain_message,
            selector=b'example',
            domain=b'canonical.com',
            privkey=sample_privkey,
            logger=self.logger,
            canonicalize=canonicalize)
        assert dkim_line[-1:] == b'\n'
        return dkim_line + plain_message

    def monkeypatch_dns(self):
        self._dns_responses = {}

        def my_lookup(name, timeout=None):
            try:
                return self._dns_responses[name]
            except KeyError:
                return None

        orig_get_txt = dkim.dnsplug._get_txt
        dkim.dnsplug._get_txt = my_lookup

        def restore():
            dkim.dnsplug._get_txt = orig_get_txt

        self.addCleanup(restore)

    def preload_dns_response(self, response_type='valid'):
        """Configure a fake DNS key response.

        :param response_type: Describes what response to give back as the
        key.  The default, 'valid', is to give the valid test signing key.
        'broken' gives a key that's almost but not quite valid, 'garbage'
        gives one that doesn't look valid at all.
        """
        if response_type == 'valid':
            key = sample_dns
        elif response_type == 'broken':
            key = sample_dns.replace(b';', b'')
        elif response_type == 'garbage':
            key = b'abcdefg'
        else:
            raise ValueError(response_type)
        self._dns_responses[u'example._domainkey.canonical.com.'] = key

    def get_dkim_log(self):
        return self._log_output.getvalue()

    def assertStronglyAuthenticated(self, principal, signed_message):
        if IWeaklyAuthenticatedPrincipal.providedBy(principal):
            self.fail('expected strong authentication; got weak:\n'
                + self.get_dkim_log() + '\n\n'
                + six.ensure_text(signed_message, errors='replace'))

    def assertWeaklyAuthenticated(self, principal, signed_message):
        if not IWeaklyAuthenticatedPrincipal.providedBy(principal):
            self.fail('expected weak authentication; got strong:\n'
                + self.get_dkim_log() + '\n\n'
                + six.ensure_text(signed_message, errors='replace'))

    def assertDkimLogContains(self, substring):
        log = self.get_dkim_log()
        if log.find(substring) == -1:
            self.fail("didn't find %r in log: %s" % (substring, log))

    def makeMessageBytes(self, sender=None, from_address=None):
        if from_address is None:
            from_address = "Foo Bar <foo.bar@canonical.com>"
        buf = (b"From: " + six.ensure_binary(from_address) + b"\n" + b"""\
Date: Fri, 1 Apr 2010 00:00:00 +1000
Subject: yet another comment
To: 1@bugs.staging.launchpad.net

  importance critical

Why isn't this fixed yet?""")
        if sender is not None:
            buf = b"Sender: " + six.ensure_binary(sender) + b"\n" + buf
        return buf

    def test_dkim_broken_pubkey(self):
        """Handle a subtly-broken pubkey like qq.com, see bug 881237.

        The message is not trusted but inbound message processing does not
        abort either.
        """
        signed_message = self.fake_signing(self.makeMessageBytes())
        self.preload_dns_response('broken')
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')
        self.assertDkimLogContains(
            "ERROR unknown algorithm in k= tag")

    def test_dkim_garbage_pubkey(self):
        signed_message = self.fake_signing(self.makeMessageBytes())
        self.preload_dns_response('garbage')
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')
        # We seem to just get the public key as the error message, which
        # isn't the most informative of errors, but this is buried inside
        # dkimpy and there isn't much we can do about it.
        self.assertDkimLogContains("ERROR %s" % b"abcdefg")

    def test_dkim_disabled(self):
        """With disabling flag set, mail isn't trusted."""
        self.useFixture(FeatureFixture({
            'mail.dkim_authentication.disabled': 'true'}))
        # A test that would normally pass will now fail
        self.assertRaises(self.failureException,
            self.test_dkim_valid_strict)

    def test_dkim_valid_strict(self):
        signed_message = self.fake_signing(self.makeMessageBytes(),
            canonicalize=(dkim.Simple, dkim.Simple))
        self.preload_dns_response()
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertStronglyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_valid(self):
        signed_message = self.fake_signing(self.makeMessageBytes())
        self.preload_dns_response()
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertStronglyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_untrusted_signer(self):
        # Valid signature from an untrusted domain -> untrusted
        signed_message = self.fake_signing(self.makeMessageBytes())
        self.preload_dns_response()
        saved_domains = incoming._trusted_dkim_domains[:]

        def restore():
            incoming._trusted_dkim_domains = saved_domains

        self.addCleanup(restore)
        incoming._trusted_dkim_domains = []
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_signing_irrelevant(self):
        # It's totally valid for a message to be signed by a domain other than
        # that of the From-sender, if that domain is relaying the message.
        # However, we shouldn't then trust the purported sender, because they
        # might have just made it up rather than relayed it.
        tweaked_message = self.makeMessageBytes(
            from_address='steve.alexander@ubuntulinux.com')
        signed_message = self.fake_signing(tweaked_message)
        self.preload_dns_response()
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        # should come from From, not the dkim signature
        self.assertEqual(principal.person.preferredemail.email,
            'steve.alexander@ubuntulinux.com')

    def test_dkim_changed_from_address(self):
        # If the address part of the message has changed, it's detected.
        #  We still treat this as weakly authenticated by the purported
        # From-header sender, though perhaps in future we would prefer
        # to reject these messages.
        signed_message = self.fake_signing(self.makeMessageBytes())
        self.preload_dns_response()
        fiddled_message = signed_message.replace(
            b'From: Foo Bar <foo.bar@canonical.com>',
            b'From: Carlos <carlos@canonical.com>')
        principal = authenticateEmail(
            signed_message_from_bytes(fiddled_message))
        self.assertWeaklyAuthenticated(principal, fiddled_message)
        # should come from From, not the dkim signature
        self.assertEqual(principal.person.preferredemail.email,
            'carlos@canonical.com')

    def test_dkim_changed_from_realname(self):
        # If the real name part of the message has changed, it's detected.
        signed_message = self.fake_signing(self.makeMessageBytes())
        self.preload_dns_response()
        fiddled_message = signed_message.replace(
            b'From: Foo Bar <foo.bar@canonical.com>',
            b'From: Evil Foo <foo.bar@canonical.com>')
        principal = authenticateEmail(
            signed_message_from_bytes(fiddled_message))
        # We don't care about the real name for determining the principal.
        self.assertWeaklyAuthenticated(principal, fiddled_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_nxdomain(self):
        # If there's no DNS entry for the pubkey it should be handled
        # decently.
        signed_message = self.fake_signing(self.makeMessageBytes())
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_message_unsigned(self):
        # This is a degenerate case: a message with no signature is
        # treated as weakly authenticated.
        # The library doesn't log anything if there's no header at all.
        principal = authenticateEmail(
            signed_message_from_bytes(self.makeMessageBytes()))
        self.assertWeaklyAuthenticated(principal, self.makeMessageBytes())
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_body_mismatch(self):
        # The message has a syntactically valid DKIM signature that
        # doesn't actually correspond to what was signed.  We log
        # something about this but we don't want to drop the message.
        signed_message = self.fake_signing(self.makeMessageBytes())
        signed_message += b'blah blah'
        self.preload_dns_response()
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')
        self.assertDkimLogContains('body hash mismatch')

    def test_dkim_signed_by_other_address(self):
        # If the message is From one of a person's addresses, and the Sender
        # corresponds to another, and there is a DKIM signature for the Sender
        # domain, this is valid - see bug 643223.  For this to be a worthwhile
        # test  we need the two addresses to be in different domains.   It
        # will be signed by canonical.com, so make that the sender.
        person = self.factory.makePerson(
            email='dkimtest@canonical.com',
            name='dkimtest',
            displayname='DKIM Test')
        self.factory.makeEmail(
            person=person,
            address='dkimtest@example.com')
        self.preload_dns_response()
        tweaked_message = self.makeMessageBytes(
            sender="dkimtest@canonical.com",
            from_address="DKIM Test <dkimtest@example.com>")
        signed_message = self.fake_signing(tweaked_message)
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertStronglyAuthenticated(principal, signed_message)

    def test_dkim_signed_but_from_unknown_address(self):
        """Sent from trusted dkim address, but only the From address is known.

        See https://bugs.launchpad.net/launchpad/+bug/925597
        """
        self.factory.makePerson(
            email='dkimtest@example.com',
            name='dkimtest',
            displayname='DKIM Test')
        self.preload_dns_response()
        tweaked_message = self.makeMessageBytes(
            sender="dkimtest@canonical.com",
            from_address="DKIM Test <dkimtest@example.com>")
        signed_message = self.fake_signing(tweaked_message)
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertEqual(principal.person.preferredemail.email,
            'dkimtest@example.com')
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertDkimLogContains(
            'valid dkim signature, but not from a known email address')

    def test_dkim_signed_but_from_unverified_address(self):
        """Sent from trusted dkim address, but only the From address is known.

        The sender is a known, but unverified address.

        See https://bugs.launchpad.net/launchpad/+bug/925597
        """
        from_address = "dkimtest@example.com"
        sender_address = "dkimtest@canonical.com"
        person = self.factory.makePerson(
            email=from_address,
            name='dkimtest',
            displayname='DKIM Test')
        self.factory.makeEmail(sender_address, person, EmailAddressStatus.NEW)
        self.preload_dns_response()
        tweaked_message = self.makeMessageBytes(
            sender=sender_address,
            from_address="DKIM Test <dkimtest@example.com>")
        signed_message = self.fake_signing(tweaked_message)
        principal = authenticateEmail(
            signed_message_from_bytes(signed_message))
        self.assertEqual(principal.person.preferredemail.email,
            from_address)
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertDkimLogContains(
            'valid dkim signature, but not from an active email address')

    def test_dkim_signed_from_person_without_account(self):
        """You can have a person with no account.

        We don't accept mail from them.

        See https://bugs.launchpad.net/launchpad/+bug/925597
        """
        from_address = "dkimtest@example.com"
        # This is not quite the same as having account=None, but it seems as
        # close as the factory lets us get? -- mbp 2012-04-13
        self.factory.makePerson(
            email=from_address,
            name='dkimtest',
            displayname='DKIM Test',
            account_status=AccountStatus.NOACCOUNT)
        self.preload_dns_response()
        message_text = self.makeMessageBytes(
            sender=from_address,
            from_address=from_address)
        signed_message = self.fake_signing(message_text)
        self.assertRaises(
            InactiveAccount,
            authenticateEmail,
            signed_message_from_bytes(signed_message))
