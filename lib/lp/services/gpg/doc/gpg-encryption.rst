   OpenPGP Encrypt/Decrypt Operation
   =================================

This document describes the current procedure to encrypt and
decrypt contents in Launchpad, and demonstrates that the methods
can support Unicode contents.

    >>> import six
    >>> from lp.testing.gpgkeys import (
    ...     import_public_test_keys,
    ...     import_secret_test_key,
    ...     decrypt_content,
    ... )
    >>> import transaction
    >>> import_public_test_keys()
    >>> key = import_secret_test_key()

    >>> transaction.commit()

Sample Person has public and secret keys set.

    >>> from zope.component import getUtility
    >>> from lp.testing import login
    >>> from lp.services.webapp.interfaces import ILaunchBag

    >>> bag = getUtility(ILaunchBag)

    >>> bag.user is None
    True

    >>> login("test@canonical.com")
    >>> print(bag.user.name)
    name12

    >>> from lp.services.gpg.interfaces import IGPGHandler
    >>> gpghandler = getUtility(IGPGHandler)

Let's use a unicode content, it can't be directly typed as
unicode, because doctest system seems to be reencoding the test
content, let's use cryptic form.

    >>> content = "\ufcber"

Note, gpg_keys is ordered (by GPGKey.id), we can slice it without
generating warnings: (its is also valid for Person.inactive_gpg_keys
property, since both are generating using GPGKeyset.getGPGKeys)

    >>> fingerprint = bag.user.gpg_keys[0].fingerprint

Note fingerprint is also unicode.

    >>> print(fingerprint)
    A419AE861E88BC9E04B9C26FBA2B9389DFD20543

    >>> key = gpghandler.retrieveKey(fingerprint)
    >>> cipher = gpghandler.encryptContent(content.encode("utf-8"), key)

cipher contains the encrypted content.

Storing the raw password may compromise the security, but is the
only way we can decrypt the cipher content.

    >>> password = "test"
    >>> plain = decrypt_content(cipher, password)

voilá, the same content shows up again.

    >>> print(backslashreplace(plain.decode("utf-8")))
    \ufcber

The encryption process supports passing another charset string.

    >>> content = "a\xe7ucar"
    >>> cipher = gpghandler.encryptContent(content.encode("iso-8859-1"), key)
    >>> plain = decrypt_content(cipher, "test")
    >>> print(backslashreplace(plain.decode("iso-8859-1")))
    a\xe7ucar

Let's try to pass unicode and see if it fails

    >>> cipher = gpghandler.encryptContent(content, key)
    Traceback (most recent call last):
    ...
    TypeError: Content must be bytes.

Decrypt a unicode content:

    >>> content = "a\xe7ucar"
    >>> cipher = gpghandler.encryptContent(content.encode("iso-8859-1"), key)
    >>> cipher = six.ensure_text(cipher)
    >>> plain = decrypt_content(cipher, "test")
    Traceback (most recent call last):
    ...
    TypeError: Content must be bytes.

What about a message encrypted for an unknown key.

    >>> cipher = b"""-----BEGIN PGP MESSAGE-----
    ... Version: GnuPG v1.2.5 (GNU/Linux)
    ...
    ... hQEOAxkWbKKY/feTEAP+NoZRhb+/2OOd4f0FGRe7XP1HMvsRZ7X0uk/EjCv1CVnn
    ... TUS3UjPTWOsO27ehN6SeS0jXoD7o6LBOQ2b/P/mXor+nUAm9cb6OpE/FfYKINldp
    ... Hle2x6Zvp+/2Lc24wQ3TPnJYi+kEMTgOF0HUYNS32bOcmArZe7A6q2FKjamSHBkD
    ... /iLF0GRbkp8v9/NqGQ6JQBMn8YLJi8mXRCs4VsiqEV/sOpYkil6d7tRFN6vE3vOZ
    ... NUDiwbycPeArbrHZIQzmnYtwb/RHqpSJe1s9yiOc/OlA+IcRL/7nnNQMQx0mkiwL
    ... sDYPkggh2n4Q2Ekz1RuLenu7pMmDsc8rEqAmI1LeqnMF0sDVAU5NhqLp5ObBea2b
    ... G/b2jrAvKOIS0HkPITSuM6nGt5hyBpgfW0qgCYAuqy41g3VwveInaazsNDlEgFAI
    ... 5OEmM2uvEKnTTfbwOqL/pPfKykemKvghUnyQRyig0zyMWr5WfvFbM/UTF6bw8utE
    ... AffSyBndPoGzJx7g7FHrRsgw17bvgSlSqA5XmwHq7qe0zc+FWN3S9ieb3aQR6/w0
    ... yIgU3hOHG469l8nV/35QH9xQRkQ7VPwIUMXDQCvTuSIg9uYbz8+TwJTwV5mLK/Nl
    ... FRowszYIbgELNtN+QsSpmZYvMl93p5wxmrIgmf8AlXpUwY5X1L8q+8a94zYCUhQS
    ... RQ1x4ejjULKx5HfX4dufIohCllAfMVFOkO7ywD7qDCOAIxyoC8oPWsXtTYqSwl5P
    ... nu/xOm3FroyjpMCe691BiMXxY7MsefyLt0kwIbCtzgp6btsg+96xz/S9LSqjPugA
    ... 1rTfWQYZj/bmWcNaR5DSsQZAYalEGK+TI9hDA2ECruhYzMb8Ykl2c9FcdV3sOu9R
    ... UB+Czv0mWAmb
    ... =LQK5
    ... -----END PGP MESSAGE-----
    ... """
    >>> plain = decrypt_content(cipher, "test")
    >>> plain is None
    True

    >>> gpghandler.resetLocalState()
