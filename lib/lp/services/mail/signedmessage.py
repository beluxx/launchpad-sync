# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for simpler handling of PGP signed email messages."""

__all__ = [
    "SignedMessage",
    "signed_message_from_bytes",
    "strip_pgp_signature",
]

import email
import re
from email.message import Message

from zope.interface import implementer

from lp.services.mail.interfaces import ISignedMessage

clearsigned_re = re.compile(
    rb"-----BEGIN PGP SIGNED MESSAGE-----"
    rb".*?(?:\r\n|\n)(?:\r\n|\n)(.*)(?:\r\n|\n)"
    rb"(-----BEGIN PGP SIGNATURE-----"
    rb".*"
    rb"-----END PGP SIGNATURE-----)",
    re.DOTALL,
)

# Regexp for matching the signed content in multipart messages.
multipart_signed_content = (
    r"%(boundary)s\n(?P<signed_content>.*?)\n%(boundary)s\n.*?\n%(boundary)s"
)

# Lines that start with '-' are escaped with '- '.
dash_escaped = re.compile(b"^- ", re.MULTILINE)


def signed_message_from_bytes(buf):
    """Parse the byte string and return a SignedMessage.

    It makes sure that the SignedMessage instance has access to the
    parsed bytes.
    """
    msg = email.message_from_bytes(buf, _class=SignedMessage)
    msg.parsed_bytes = buf
    return msg


@implementer(ISignedMessage)
class SignedMessage(Message):
    """Provides easy access to signed content and the signature"""

    parsed_bytes = None

    def _getSignatureAndSignedContent(self):
        """Returns the PGP signature and the content that's signed.

        The signature is returned as a byte string, and the content is
        returned as a byte string.

        If the message isn't signed, both signature and the content is
        None.
        """
        assert (
            self.parsed_bytes is not None
        ), "Use signed_message_from_bytes() to create the message."
        signed_content = signature = None
        # Check for MIME/PGP signed message first.
        # See: RFC3156 - MIME Security with OpenPGP
        # RFC3156 says that in order to be a complient signed message, there
        # must be two and only two parts and that the second part must have
        # content_type 'application/pgp-signature'.
        if self.is_multipart():
            payload = self.get_payload()
            if len(payload) == 2:
                content_part, signature_part = payload
                sig_content_type = signature_part.get_content_type()
                if sig_content_type == "application/pgp-signature":
                    # We need to extract the signed content from the parsed
                    # bytes, since content_part.as_bytes() isn't guaranteed
                    # to return the exact byte string it was created from.
                    boundary = "--" + self.get_boundary()
                    match = re.search(
                        (
                            multipart_signed_content
                            % {"boundary": re.escape(boundary)}
                        ).encode("ASCII"),
                        self.parsed_bytes,
                        re.DOTALL,
                    )
                    signed_content = match.group("signed_content")
                    signature = signature_part.get_payload(decode=True)
                    return signature, signed_content
        # If we still have no signature, then we have one of several cases:
        #  1) We do not have a multipart message
        #  2) We have a multipart message with two parts, but the second part
        #     isn't a signature. E.g.
        #        multipart/mixed
        #          text/plain <- clear signed review comment
        #          text/x-diff <- patch
        #  3) We have a multipart message with more than two parts.
        #        multipart/mixed
        #          text/plain <- clear signed body text
        #          text/x-diff <- patch or merge directoive
        #          application/pgp-signature <- detached signature
        # Now we can handle one and two by walking the content and stopping at
        # the first part that isn't multipart, and getting a signature out of
        # that.  We can partly handle number three by at least checking the
        # clear text signed message, but we don't check the detached signature
        # for the attachment.
        for part in self.walk():
            if part.is_multipart():
                continue
            match = clearsigned_re.search(part.get_payload(decode=True))
            if match is not None:
                signed_content_unescaped = match.group(1)
                signed_content = dash_escaped.sub(
                    b"", signed_content_unescaped
                )
                signature = match.group(2)
                return signature, signed_content
            # Stop processing after the first non-multipart part.
            break
        return signature, signed_content

    @property
    def signedMessage(self):
        """Returns the PGP signed content as a message.

        Returns None if the message wasn't signed.
        """
        signature, signed_content = self._getSignatureAndSignedContent()
        if signed_content is None:
            return None
        else:
            if not self.is_multipart() and clearsigned_re.search(
                self.get_payload(decode=True)
            ):
                # Add a new line so that a message with no headers will
                # be created.
                signed_content = b"\n" + signed_content
            return signed_message_from_bytes(signed_content)

    @property
    def signedContent(self):
        """Returns the PGP signed content as a byte string.

        Returns None if the message wasn't signed.
        """
        signature, signed_content = self._getSignatureAndSignedContent()
        return signed_content

    @property
    def signature(self):
        """Returns the PGP signature used to sign the message.

        Returns None if the message wasn't signed.
        """
        signature, signed_content = self._getSignatureAndSignedContent()
        return signature

    @property
    def raw_length(self):
        """Return the length in bytes of the underlying raw form."""
        return len(self.parsed_bytes)


def strip_pgp_signature(buf):
    """Strip any PGP signature from the supplied byte string."""
    signed_message = signed_message_from_bytes(buf)
    # For unsigned text the signedContent will be None.
    if signed_message.signedContent is not None:
        return signed_message.signedContent
    else:
        return buf
