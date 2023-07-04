# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import logging
import os
import unittest
from doctest import DocTestSuite
from email.header import Header, decode_header, make_header
from email.mime.multipart import MIMEMultipart
from email.utils import parseaddr
from textwrap import dedent

import transaction
from testtools.matchers import Equals, Is
from zope.interface import implementer
from zope.security.management import setSecurityPolicy

from lp.services.compat import message_as_bytes
from lp.services.config import config
from lp.services.gpg.interfaces import (
    GPGKeyExpired,
    GPGKeyNotFoundError,
    IGPGHandler,
)
from lp.services.log.logger import BufferLogger
from lp.services.mail import helpers
from lp.services.mail.handlers import mail_handlers
from lp.services.mail.incoming import (
    ORIGINAL_TO_HEADER,
    authenticateEmail,
    extract_addresses,
    handleMail,
)
from lp.services.mail.interfaces import IMailHandler
from lp.services.mail.sendmail import MailController
from lp.services.mail.stub import TestMailer
from lp.services.mail.tests.helpers import testmails_path
from lp.services.webapp.authorization import LaunchpadSecurityPolicy
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import switch_dbuser
from lp.testing.factory import GPGSigningContext
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.gpgkeys import import_secret_test_key
from lp.testing.layers import LaunchpadZopelessLayer
from lp.testing.mail_helpers import pop_notifications
from lp.testing.systemdocs import LayeredDocFileSuite, setGlobs


@implementer(IMailHandler)
class FakeHandler:
    def __init__(self, allow_unknown_users=True):
        self.allow_unknown_users = allow_unknown_users
        self.handledMails = []

    def process(self, mail, to_addr, filealias):
        self.handledMails.append(mail)
        return True


class FakePymeKey:
    def __init__(self, fingerprint):
        self.fingerprint = fingerprint


class FakeGPGHandlerExpired:
    def __init__(self, key):
        self.key = key

    def getVerifiedSignature(self, content, signature=None):
        raise GPGKeyExpired(self.key)


class FakeGPGHandlerNotFound:
    def __init__(self, fingerprint):
        self.fingerprint = fingerprint

    def getVerifiedSignature(self, content, signature=None):
        raise GPGKeyNotFoundError(self.fingerprint)


class IncomingTestCase(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    def test_invalid_signature(self):
        """Invalid signature should not be handled as an OOPs.

        It should produce a message explaining to the user what went wrong.
        """
        person = self.factory.makePerson()
        transaction.commit()
        email_address = person.preferredemail.email
        invalid_body = (
            "-----BEGIN PGP SIGNED MESSAGE-----\n"
            "Hash: SHA1\n\n"
            "Body\n"
            "-----BEGIN PGP SIGNATURE-----\n"
            "Not a signature.\n"
            "-----END PGP SIGNATURE-----\n"
        )
        ctrl = MailController(
            email_address,
            "to@example.com",
            "subject",
            invalid_body,
            bulk=False,
        )
        ctrl.send()
        handleMail()
        self.assertEqual([], self.oopses)
        [notification] = pop_notifications()
        body = notification.get_payload()[0].get_payload(decode=True).decode()
        self.assertIn(
            "An error occurred while processing a mail you sent to "
            "Launchpad's email\ninterface.\n\n\n"
            "Error message:\n\nSignature couldn't be verified: "
            "(7, 58, %r)" % "No data",
            body,
        )

    def test_expired_key(self):
        """An expired key should not be handled as an OOPS.

        It should produce a message explaining to the user what went wrong.
        """
        person = self.factory.makePerson()
        key = FakePymeKey("0" * 40)
        self.useFixture(
            ZopeUtilityFixture(FakeGPGHandlerExpired(key), IGPGHandler)
        )
        transaction.commit()
        email_address = person.preferredemail.email
        invalid_body = (
            "-----BEGIN PGP SIGNED MESSAGE-----\n"
            "Hash: SHA1\n\n"
            "Body\n"
            "-----BEGIN PGP SIGNATURE-----\n"
            "Not a signature.\n"
            "-----END PGP SIGNATURE-----\n"
        )
        ctrl = MailController(
            email_address,
            "to@example.com",
            "subject",
            invalid_body,
            bulk=False,
        )
        ctrl.send()
        handleMail()
        self.assertEqual([], self.oopses)
        [notification] = pop_notifications()
        body = notification.get_payload()[0].get_payload(decode=True).decode()
        self.assertIn(
            "An error occurred while processing a mail you sent to "
            "Launchpad's email\ninterface.\n\n\n"
            "Error message:\n\nSignature couldn't be verified: "
            "%s\nhas expired" % key.fingerprint,
            body,
        )

    def test_key_not_found(self):
        """A key not found on the keyserver should not be handled as an OOPS.

        It should produce a message explaining to the user what went wrong.
        """
        person = self.factory.makePerson()
        fingerprint = "0" * 40
        self.useFixture(
            ZopeUtilityFixture(
                FakeGPGHandlerNotFound(fingerprint), IGPGHandler
            )
        )
        transaction.commit()
        email_address = person.preferredemail.email
        invalid_body = (
            "-----BEGIN PGP SIGNED MESSAGE-----\n"
            "Hash: SHA1\n\n"
            "Body\n"
            "-----BEGIN PGP SIGNATURE-----\n"
            "Not a signature.\n"
            "-----END PGP SIGNATURE-----\n"
        )
        ctrl = MailController(
            email_address,
            "to@example.com",
            "subject",
            invalid_body,
            bulk=False,
        )
        ctrl.send()
        handleMail()
        self.assertEqual([], self.oopses)
        [notification] = pop_notifications()
        body = notification.get_payload()[0].get_payload(decode=True).decode()
        self.assertIn(
            "An error occurred while processing a mail you sent to "
            "Launchpad's email\ninterface.\n\n\n"
            "Error message:\n\nSignature couldn't be verified: "
            "No GPG key found with the given content:\n%s" % fingerprint,
            body,
        )

    def test_mail_too_big(self):
        """Much-too-big mail should generate a bounce, not an OOPS.

        See <https://bugs.launchpad.net/launchpad/+bug/893612>.
        """
        person = self.factory.makePerson()
        transaction.commit()
        email_address = person.preferredemail.email
        fat_body = "\n".join(
            ["some big mail with this line repeated many many times\n"]
            * 1000000
        )
        ctrl = MailController(
            email_address, "to@example.com", "subject", fat_body, bulk=False
        )
        ctrl.send()
        handleMail()
        self.assertEqual([], self.oopses)
        [notification] = pop_notifications()
        body = notification.get_payload()[0].get_payload(decode=True).decode()
        self.assertIn("The mail you sent to Launchpad is too long.", body)
        self.assertIn("was 55 MB and the limit is 10 MB.", body)

    def test_invalid_to_addresses(self):
        # Invalid To: header should not be handled as an OOPS.
        with open(
            os.path.join(testmails_path, "invalid-to-header.txt"), "rb"
        ) as f:
            raw_mail = f.read()
        # Due to the way handleMail works, even if we pass a valid To header
        # to the TestMailer, as we're doing here, it falls back to parse all
        # To and CC headers from the raw_mail. Also, TestMailer is used here
        # because MailController won't send an email with a broken To: header.
        TestMailer().send("from@example.com", "to@example.com", raw_mail)
        handleMail()
        self.assertEqual([], self.oopses)

    def makeSentMessage(
        self,
        sender,
        to,
        subject="subject",
        body="body",
        cc=None,
        handler_domain=None,
    ):
        if handler_domain is None:
            extra, handler_domain = to.split("@")
        test_handler = FakeHandler()
        mail_handlers.add(handler_domain, test_handler)
        message = MIMEMultipart()
        message["Message-Id"] = "<message-id>"
        message["To"] = Header(to)
        message["From"] = Header(sender)
        message["Subject"] = Header(subject)
        if cc is not None:
            message["Cc"] = cc
        message.set_payload(body)
        TestMailer().send(sender, to, message_as_bytes(message))
        return message, test_handler

    def test_invalid_from_address_no_at(self):
        # Invalid From: header such as no "@" is handled.
        message, test_handler = self.makeSentMessage(
            "me_at_eg.dom", "test@lp.dev"
        )
        handleMail()
        self.assertEqual([], self.oopses)
        self.assertEqual(1, len(test_handler.handledMails))
        self.assertEqual("me_at_eg.dom", test_handler.handledMails[0]["From"])

    def test_invalid_cc_address_no_at(self):
        # Invalid From: header such as no "@" is handled.
        message, test_handler = self.makeSentMessage(
            "me@eg.dom", "test@lp.dev", cc="me_at_eg.dom"
        )
        handleMail()
        self.assertEqual([], self.oopses)
        self.assertEqual(1, len(test_handler.handledMails))
        self.assertEqual("me_at_eg.dom", test_handler.handledMails[0]["Cc"])

    def test_invalid_from_address_unicode(self):
        # Invalid From: header such as no "@" is handled.
        message, test_handler = self.makeSentMessage(
            "m\xeda@eg.dom", "test@lp.dev"
        )
        handleMail()
        self.assertEqual([], self.oopses)
        self.assertEqual(1, len(test_handler.handledMails))
        self.assertEqual(
            "m\xeda@eg.dom",
            str(
                make_header(
                    decode_header(test_handler.handledMails[0]["From"])
                )
            ),
        )

    def test_invalid_from_address_no_mime_encoding(self):
        # An invalid From: header with non-MIME-encoded non-ASCII characters
        # is handled.
        test_handler = FakeHandler()
        mail_handlers.add("lp.dev", test_handler)
        raw_message = dedent(
            """\
            Content-Type: text/plain; charset="UTF-8"
            MIME-Version: 1.0
            Message-Id: <message-id>
            To: test@lp.dev
            From: \u05D0 <alef@eg.dom>
            Subject: subject

            body
            """
        ).encode("UTF-8")
        TestMailer().send(
            "\u05D0 <alef@eg.dom>".encode(), "test@lp.dev", raw_message
        )
        handleMail()
        self.assertEqual([], self.oopses)
        self.assertEqual(1, len(test_handler.handledMails))
        self.assertEqual(
            "alef@eg.dom",
            parseaddr(str(test_handler.handledMails[0]["From"]))[1],
        )

    def test_invalid_cc_address_unicode(self):
        # Invalid Cc: header such as no "@" is handled.
        message, test_handler = self.makeSentMessage(
            "me@eg.dom", "test@lp.dev", cc="m\xeda@eg.dom"
        )
        handleMail()
        self.assertEqual([], self.oopses)
        self.assertEqual(1, len(test_handler.handledMails))
        self.assertEqual(
            "m\xeda@eg.dom",
            str(
                make_header(decode_header(test_handler.handledMails[0]["Cc"]))
            ),
        )


class AuthenticateEmailTestCase(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    def test_bad_signature_timestamp(self):
        """If the signature is nontrivial future-dated, it's not trusted."""

        signing_context = GPGSigningContext(
            import_secret_test_key(), password="test"
        )
        msg = self.factory.makeSignedMessage(signing_context=signing_context)
        # It's not trivial to make a gpg signature with a bogus timestamp, so
        # let's just treat everything as invalid, and trust that the regular
        # implementation of extraction and checking of timestamps is correct,
        # or at least tested.

        def fail_all_timestamps(timestamp, context):
            raise helpers.IncomingEmailError("fail!")

        self.assertRaises(
            helpers.IncomingEmailError,
            authenticateEmail,
            msg,
            fail_all_timestamps,
        )

    def test_unknown_email(self):
        # An unknown email address returns no principal.
        unknown = "random-unknown@example.com"
        mail = self.factory.makeSignedMessage(email_address=unknown)
        self.assertThat(authenticateEmail(mail), Is(None))

    def test_badly_formed_email(self):
        # A badly formed email address returns no principal.
        bad = "\xed@example.com"
        mail = self.factory.makeSignedMessage(email_address=bad)
        self.assertThat(authenticateEmail(mail), Is(None))


class TestExtractAddresses(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    def test_original_to(self):
        mail = self.factory.makeSignedMessage()
        original_to = "eric@vikings.example.com"
        mail[ORIGINAL_TO_HEADER] = original_to
        self.assertThat(
            extract_addresses(mail, None, None), Equals([original_to])
        )

    def test_original_to_in_body(self):
        header_to = "eric@vikings-r-us.example.com"
        original_to = "eric@vikings.example.com"
        alias = "librarian-somewhere"
        body = "%s: %s\n\nsome body stuff" % (ORIGINAL_TO_HEADER, original_to)
        log = BufferLogger()
        mail = self.factory.makeSignedMessage(body=body, to_address=header_to)
        addresses = extract_addresses(mail, alias, log)
        self.assertThat(addresses, Equals([header_to]))
        self.assertThat(
            log.getLogBuffer(),
            Equals("INFO Suspected spam: librarian-somewhere\n"),
        )

    def test_original_to_missing(self):
        header_to = "eric@vikings-r-us.example.com"
        alias = "librarian-somewhere"
        log = BufferLogger()
        mail = self.factory.makeSignedMessage(to_address=header_to)
        addresses = extract_addresses(mail, alias, log)
        self.assertThat(addresses, Equals([header_to]))
        self.assertThat(
            log.getLogBuffer(),
            Equals(
                "WARNING No X-Launchpad-Original-To header was present "
                "in email: librarian-somewhere\n"
            ),
        )


def setUp(test):
    setGlobs(test)
    test._old_policy = setSecurityPolicy(LaunchpadSecurityPolicy)
    switch_dbuser(config.processmail.dbuser)


def tearDown(test):
    setSecurityPolicy(test._old_policy)


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    suite.addTest(DocTestSuite("lp.services.mail.incoming"))
    suite.addTest(
        LayeredDocFileSuite(
            "incomingmail.rst",
            setUp=setUp,
            tearDown=tearDown,
            layer=LaunchpadZopelessLayer,
            stdout_logging_level=logging.WARNING,
        )
    )
    return suite
