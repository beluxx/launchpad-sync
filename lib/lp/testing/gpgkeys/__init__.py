# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OpenPGP keys used for testing.

There are two GPG keys located in the 'gpgkeys' sub directory, one for
Sample Person and for Foo Bar. The passwords for the secret keys are
'test'.

Before they are used in tests they need to be imported, so that
GpgHandler knows about them.  import_public_test_keys() imports all
public keys available, while import_public_key(email_addr) only imports
the key associated with that specific email address.

Secret keys are also imported into the local key ring, they are used for
decrypt data in pagetests.
"""

import os
from io import BytesIO

import gpgme
import six
from zope.component import getUtility

from lp.registry.interfaces.gpg import IGPGKeySet
from lp.registry.interfaces.person import IPersonSet
from lp.services.gpg.interfaces import IGPGHandler, get_gpgme_context

gpgkeysdir = os.path.join(os.path.dirname(__file__), "data")


def import_public_key(email_addr):
    """Imports the public key related to the given email address."""
    gpghandler = getUtility(IGPGHandler)
    personset = getUtility(IPersonSet)

    pubkey = test_pubkey_from_email(email_addr)
    key = gpghandler.importPublicKey(pubkey)

    # Strip out any '-passwordless' annotation from the email addresses.
    email_addr = email_addr.replace("-passwordless", "")

    # Some of the keys shouldn't be inserted into the db.
    if email_addr.endswith("do-not-insert-into-db"):
        return

    person = personset.getByEmail(email_addr)

    # Some of the sample keys do not have corresponding Launchpad
    # users, so ignore them.
    if not person:
        return

    for gpgkey in person.gpg_keys:
        if gpgkey.fingerprint == key.fingerprint:
            # If the key's already added to the database, do nothing.
            return

    # Insert the key into the database.
    keyset = getUtility(IGPGKeySet)
    key = keyset.new(
        ownerID=person.id,
        keyid=key.keyid,
        fingerprint=key.fingerprint,
        keysize=key.keysize,
        algorithm=key.algorithm,
        active=(not key.revoked),
    )


def iter_test_key_emails():
    """Iterates over the email addresses for the keys in the gpgkeysdir."""
    for name in sorted(os.listdir(gpgkeysdir), reverse=True):
        if name.endswith(".pub"):
            yield name[:-4]


def import_public_test_keys():
    """Imports all the public keys located in gpgkeysdir into the db."""
    for email in iter_test_key_emails():
        import_public_key(email)


def import_secret_test_key(keyfile="test@canonical.com.sec"):
    """Imports the secret key located in gpgkeysdir into local keyring.

    :param keyfile: The name of the file to be imported.
    """
    gpghandler = getUtility(IGPGHandler)
    with open(os.path.join(gpgkeysdir, keyfile), "rb") as f:
        seckey = f.read()
    return gpghandler.importSecretKey(seckey)


def test_pubkey_file_from_email(email_addr):
    """Get the file name for a test pubkey by email address."""
    return os.path.join(gpgkeysdir, email_addr + ".pub")


def test_pubkey_from_email(email_addr):
    """Get the on disk content for a test pubkey by email address."""
    with open(test_pubkey_file_from_email(email_addr), "rb") as f:
        return f.read()


def test_keyrings():
    """Iterate over the filenames for test keyrings."""
    for entry in os.scandir(gpgkeysdir):
        if entry.name.endswith(".gpg"):
            yield entry.path


def decrypt_content(content, password):
    """Return the decrypted content or None if failed

    content must be a byte string, and password must be a native string.
    It's up to the caller to encode or decode properly.

    :content: encrypted data content
    :password: password to unlock the secret key in question
    """
    if not isinstance(password, str):
        raise TypeError("Password must be a str.")

    if not isinstance(content, bytes):
        raise TypeError("Content must be bytes.")

    ctx = get_gpgme_context()

    # setup containers
    cipher = BytesIO(content)
    plain = BytesIO()

    def passphrase_cb(uid_hint, passphrase_info, prev_was_bad, fd):
        os.write(fd, six.ensure_binary("%s\n" % password))

    ctx.passphrase_cb = passphrase_cb

    # Do the decryption.
    try:
        ctx.decrypt(cipher, plain)
    except gpgme.GpgmeError:
        return None

    return plain.getvalue()
