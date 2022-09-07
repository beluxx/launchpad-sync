GPGHandler
==========

`IGPGHandler` is a utility designed to handle OpenPGP (GPG) operations.

The following operations are supported:

 * Importing public and secret keys;
 * Generating a new key;
 * Finding local keys;
 * Retrieving public keys from the keyserver;
 * Verifying signatures (see gpg-signatures.rst);
 * Encrypting contents (see gpg-encrypt.rst);
 * Importing keyring files;
 * Obtaining keyserver URLs for public keys;
 * Sanitizing fingerprints.


Importing public OpenPGP keys
-----------------------------

The importPublicKey method is exposed by IGPGHandler but it's only used
internally by the retrieveKey method.  Ideally, we shouldn't need to
check for all error conditions that we do, but we can't assume the
keyserver is a trusted data source, so we have to do that.

    >>> from zope.component import getUtility
    >>> from lp.testing import verifyObject

    >>> from lp.services.gpg.interfaces import (
    ...     IGPGHandler,
    ...     IPymeKey,
    ...     )
    >>> gpghandler = getUtility(IGPGHandler)

-------------------------------------------------------------------------
XXX: All these checks for error conditions should probably be moved to a
unit tests somewhere else at some point. -- Guilherme Salgado, 2006-08-23
-------------------------------------------------------------------------

A GPGKeyNotFoundError is raised if we try to import an empty content.

    >>> key = gpghandler.importPublicKey(b'')
    Traceback (most recent call last):
    ...
    lp.services.gpg.interfaces.GPGKeyNotFoundError: ...

The same happens for bogus content.

    >>> key = gpghandler.importPublicKey(b'XXXXXXXXX')
    Traceback (most recent call last):
    ...
    lp.services.gpg.interfaces.GPGKeyNotFoundError: ...

Let's recover some coherent data and verify if it works as expected:

    >>> import os
    >>> from lp.testing.gpgkeys import gpgkeysdir
    >>> filepath = os.path.join(gpgkeysdir, 'test@canonical.com.pub')
    >>> with open(filepath, 'rb') as f:
    ...     pubkey = f.read()
    >>> key = gpghandler.importPublicKey(pubkey)

    >>> verifyObject(IPymeKey, key)
    True

    >>> print(key.fingerprint)
    A419AE861E88BC9E04B9C26FBA2B9389DFD20543

    >>> print(key.secret)
    False

    >>> print(key.can_encrypt)
    True

    >>> print(key.can_sign)
    True

    >>> print(key.can_certify)
    True

    >>> print(key.can_authenticate)
    False

Public keys can be exported in ASCII-armored format.

    >>> print(six.ensure_text(key.export()))
    -----BEGIN PGP PUBLIC KEY BLOCK-----
    ...
    -----END PGP PUBLIC KEY BLOCK-----
    <BLANKLINE>

Now, try to import a secret key, which will cause a
SecretGPGKeyImportDetected exception to be raised.

    >>> filepath = os.path.join(gpgkeysdir, 'test@canonical.com.sec')
    >>> with open(filepath, 'rb') as f:
    ...     seckey = f.read()
    >>> key = gpghandler.importPublicKey(seckey)
    Traceback (most recent call last):
    ...
    lp.services.gpg.interfaces.SecretGPGKeyImportDetected: ...

Now, try to import two public keys, causing a MoreThanOneGPGKeyFound
exception to be raised.

    >>> filepath = os.path.join(gpgkeysdir, 'foo.bar@canonical.com.pub')
    >>> with open(filepath, 'rb') as f:
    ...     pubkey2 = f.read()
    >>> key = gpghandler.importPublicKey(b'\n'.join([pubkey, pubkey2]))
    Traceback (most recent call last):
    ...
    lp.services.gpg.interfaces.MoreThanOneGPGKeyFound: ...

Raise a GPGKeyNotFoundError if we try to import a public key with damaged
preamble.

    >>> key = gpghandler.importPublicKey(pubkey[1:])
    Traceback (most recent call last):
    ...
    lp.services.gpg.interfaces.GPGKeyNotFoundError: ...

We also get an error if we try to import an incomplete public key
(which probably happened in bug #2547):

    >>> key = gpghandler.importPublicKey(pubkey[:-300])
    Traceback (most recent call last):
    ...
    lp.services.gpg.interfaces.GPGKeyNotFoundError: ...


Importing secret OpenPGP keys
-----------------------------

Secret keys can be imported using IGPGHandler.importSecretKey() which
does exactly the same job performed by importPublicKey() but
supporting only ASCII-armored secret keys.

    >>> filepath = os.path.join(gpgkeysdir, 'test@canonical.com.sec')
    >>> with open(filepath, 'rb') as f:
    ...     seckey = f.read()
    >>> key = gpghandler.importSecretKey(seckey)

    >>> verifyObject(IPymeKey, key)
    True

    >>> print(key.fingerprint)
    A419AE861E88BC9E04B9C26FBA2B9389DFD20543

    >>> print(key.secret)
    True

    >>> print(key.can_encrypt)
    True

    >>> print(key.can_sign)
    True

    >>> print(key.can_certify)
    True

    >>> print(key.can_authenticate)
    False

Secret keys can be exported in ASCII-armored format.

    >>> print(six.ensure_text(key.export()))
    -----BEGIN PGP PRIVATE KEY BLOCK-----
    ...
    -----END PGP PRIVATE KEY BLOCK-----
    <BLANKLINE>


Keyserver uploads
-----------------

IGPGHandler also allow callsites to upload the public part of a local
key to the configuration keyserver.

We will set up and use the test-keyserver.

    >>> from lp.testing.keyserver import KeyServerTac
    >>> tac = KeyServerTac()
    >>> tac.setUp()

Import a test key.

    >>> filepath = os.path.join(gpgkeysdir, 'ppa-sample@canonical.com.sec')
    >>> with open(filepath, 'rb') as f:
    ...     seckey = f.read()
    >>> new_key = gpghandler.importSecretKey(seckey)

Upload the just-generated key to the keyserver so that we can reset
the local keyring.

    >>> gpghandler.uploadPublicKey(new_key.fingerprint)

    >>> gpghandler.resetLocalState()
    >>> len(list(gpghandler.localKeys()))
    0

When we need the public key again we use retrieveKey(), which will
hit the keyserver and import it automatically.

    >>> retrieved_key = gpghandler.retrieveKey(new_key.fingerprint)
    >>> retrieved_key.fingerprint == new_key.fingerprint
    True

An attempt to upload an unknown key will fail.

    >>> gpghandler.uploadPublicKey('F' * 40)
    Traceback (most recent call last):
    ...
    lp.services.gpg.interfaces.GPGKeyDoesNotExistOnServer: GPG key
    FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF does not exist on the keyserver.

Uploading the same key more than once is fine, it is handled on the
keyserver side.

    >>> gpghandler.uploadPublicKey(new_key.fingerprint)

An attempt to upload a key when the keyserver is unreachable results
in a error.

    >>> tac.tearDown()
    >>> gpghandler.uploadPublicKey(new_key.fingerprint)
    Traceback (most recent call last):
    ...
    lp.services.gpg.interfaces.GPGUploadFailure: Could not reach keyserver at
    http://localhost:11371...Connection refused...


Fingerprint sanitizing
----------------------

The GPG handler offers a convenience method to sanitize key
fingerprints:

    >>> print(gpghandler.sanitizeFingerprint("XXXXX"))
    None

    >>> fingerprint = 'C858 2652 1A6E F6A6 037B  B3F7 9FF2 583E 681B 6469'
    >>> print(gpghandler.sanitizeFingerprint(fingerprint))
    C85826521A6EF6A6037BB3F79FF2583E681B6469

    >>> fingerprint = 'c858 2652 1a6e f6a6 037b  b3f7 9ff2 583e 681b 6469'
    >>> print(gpghandler.sanitizeFingerprint(fingerprint))
    C85826521A6EF6A6037BB3F79FF2583E681B6469

    >>> print(gpghandler.sanitizeFingerprint('681B 6469'))
    None

    >>> print(gpghandler.sanitizeFingerprint('abnckjdiue'))
    None

    >>> non_ascii_chars = u'\xe9\xe1\xed'
    >>> fingerprint = ('c858 2652 1a6e f6a6 037b  b3f7 9ff2 583e 681b 6469 %s'
    ...                % non_ascii_chars)
    >>> print(gpghandler.sanitizeFingerprint(fingerprint))
    C85826521A6EF6A6037BB3F79FF2583E681B6469

    >>> fingerprint = (
    ...     '%s c858 2652 1a6e f6a6 037b  b3f7 9ff2 583e 681b 6469 %s'
    ...     % (non_ascii_chars, non_ascii_chars))
    >>> print(gpghandler.sanitizeFingerprint(fingerprint))
    None
