# Copyright 2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for signing keys stored at the signing service."""

__metaclass__ = type

__all__ = [
    'ISigningServiceClient',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )

from lp import _


class ISigningServiceClient(Interface):
    service_public_key = Attribute(_("The public key of signing service."))
    private_key = Attribute(_("This client's private key."))

    def getNonce():
        """Get nonce, to be used when sending messages.
        """

    def generate(key_type, description):
        """Generate a key to be used when signing.

        :param key_type: One of available key types at SigningKeyType
        :param description: String description of the generated key
        :return: A dict with 'fingerprint' (str) and 'public-key' (bytes)
        """

    def sign(key_type, fingerprint, message_name, message, mode):
        """Sign the given message using the specified key_type and a
        pre-generated fingerprint (see `generate` method).

        :param key_type: One of the key types from SigningKeyType enum
        :param fingerprint: The fingerprint of the signing key, generated by
                            the `generate` method
        :param message_name: A description of the message being signed
        :param message: The message to be signed
        :param mode: SigningMode.ATTACHED or SigningMode.DETACHED
        :return: A dict with 'public-key' and 'signed-message'
        """
