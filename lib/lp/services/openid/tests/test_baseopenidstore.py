# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `BaseStormOpenIDStore`."""

__all__ = [
    "BaseStormOpenIDStoreTestsMixin",
]

import time
import unittest

from openid.association import Association
from openid.store import nonce

from lp.services.database.interfaces import IMasterStore
from lp.services.openid.model.baseopenidstore import BaseStormOpenIDStore


class BaseStormOpenIDStoreTestsMixin:
    """Tests for `BaseStormOpenIDStore`."""

    def test_Class(self):
        self.assertIsInstance(self.store, BaseStormOpenIDStore)

    def test_storeAssociation(self):
        self.store.storeAssociation(
            "server-url\xA9",
            Association(b"handle", b"secret", 42, 600, "HMAC-SHA1"),
        )
        db_assoc = IMasterStore(self.store.Association).get(
            self.store.Association, ("server-url\xA9", "handle")
        )
        self.assertEqual(db_assoc.server_url, "server-url\xA9")
        self.assertEqual(db_assoc.handle, "handle")
        self.assertEqual(db_assoc.secret, b"secret")
        self.assertEqual(db_assoc.issued, 42)
        self.assertEqual(db_assoc.lifetime, 600)
        self.assertEqual(db_assoc.assoc_type, "HMAC-SHA1")

    def test_storeAssociation_update_existing(self):
        self.store.storeAssociation(
            "server-url",
            Association(b"handle", b"secret", 42, 600, "HMAC-SHA1"),
        )
        db_assoc = IMasterStore(self.store.Association).get(
            self.store.Association, ("server-url", "handle")
        )
        self.assertNotEqual(db_assoc, None)

        # Now update the association with new information.
        self.store.storeAssociation(
            "server-url",
            Association(b"handle", b"secret2", 420, 900, "HMAC-SHA256"),
        )
        self.assertEqual(db_assoc.secret, b"secret2")
        self.assertEqual(db_assoc.issued, 420)
        self.assertEqual(db_assoc.lifetime, 900)
        self.assertEqual(db_assoc.assoc_type, "HMAC-SHA256")

    def test_getAssociation(self):
        timestamp = int(time.time())
        self.store.storeAssociation(
            "server-url",
            Association(b"handle", b"secret", timestamp, 600, "HMAC-SHA1"),
        )

        assoc = self.store.getAssociation("server-url", "handle")
        self.assertIsInstance(assoc, Association)
        self.assertEqual(assoc.handle, "handle")
        self.assertEqual(assoc.secret, b"secret")
        self.assertEqual(assoc.issued, timestamp)
        self.assertEqual(assoc.lifetime, 600)
        self.assertEqual(assoc.assoc_type, "HMAC-SHA1")

    def test_getAssociation_unknown(self):
        assoc = self.store.getAssociation("server-url", "unknown")
        self.assertEqual(assoc, None)

    def test_getAssociation_expired(self):
        lifetime = 600
        timestamp = int(time.time()) - 2 * lifetime
        self.store.storeAssociation(
            "server-url",
            Association(
                b"handle", b"secret", timestamp, lifetime, "HMAC-SHA1"
            ),
        )
        # The association is not returned because it is out of date.
        # Further more, it is removed from the database.
        assoc = self.store.getAssociation("server-url", "handle")
        self.assertEqual(assoc, None)

        store = IMasterStore(self.store.Association)
        db_assoc = store.get(self.store.Association, ("server-url", "handle"))
        self.assertEqual(db_assoc, None)

    def test_getAssociation_no_handle(self):
        timestamp = int(time.time())
        self.store.storeAssociation(
            "server-url",
            Association(b"handle1", b"secret", timestamp, 600, "HMAC-SHA1"),
        )
        self.store.storeAssociation(
            "server-url",
            Association(
                b"handle2", b"secret", timestamp + 1, 600, "HMAC-SHA1"
            ),
        )

        # The most recent handle is returned.
        assoc = self.store.getAssociation("server-url", None)
        self.assertNotEqual(assoc, None)
        self.assertEqual(assoc.handle, "handle2")

    def test_removeAssociation(self):
        timestamp = int(time.time())
        self.store.storeAssociation(
            "server-url",
            Association(b"handle", b"secret", timestamp, 600, "HMAC-SHA1"),
        )
        self.assertEqual(
            self.store.removeAssociation("server-url", "handle"), True
        )
        self.assertEqual(
            self.store.getAssociation("server-url", "handle"), None
        )

    def test_removeAssociation_unknown(self):
        self.assertEqual(
            self.store.removeAssociation("server-url", "unknown"), False
        )

    def test_useNonce(self):
        timestamp = time.time()
        # The nonce can only be used once.
        self.assertEqual(
            self.store.useNonce("server-url", timestamp, "salt"), True
        )
        storm_store = IMasterStore(self.store.Nonce)
        new_nonce = storm_store.get(
            self.store.Nonce, ("server-url", timestamp, "salt")
        )
        self.assertIsNot(None, new_nonce)

        self.assertEqual(
            self.store.useNonce("server-url", timestamp, "salt"), False
        )
        self.assertEqual(
            self.store.useNonce("server-url", timestamp, "salt"), False
        )

    def test_useNonce_expired(self):
        timestamp = time.time() - 2 * nonce.SKEW
        self.assertEqual(
            self.store.useNonce("server-url", timestamp, "salt"), False
        )

    def test_useNonce_future(self):
        timestamp = time.time() + 2 * nonce.SKEW
        self.assertEqual(
            self.store.useNonce("server-url", timestamp, "salt"), False
        )

    def test_cleanupAssociations(self):
        timestamp = int(time.time()) - 100
        self.store.storeAssociation(
            "server-url",
            Association(b"handle1", b"secret", timestamp, 50, "HMAC-SHA1"),
        )
        self.store.storeAssociation(
            "server-url",
            Association(b"handle2", b"secret", timestamp, 200, "HMAC-SHA1"),
        )

        self.assertEqual(self.store.cleanupAssociations(), 1)

        # The second (non-expired) association is left behind.
        self.assertNotEqual(
            self.store.getAssociation("server-url", "handle2"), None
        )


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
