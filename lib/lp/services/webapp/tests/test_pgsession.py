# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test pgsession.py."""

import hashlib
from datetime import datetime

from zope.publisher.browser import TestRequest
from zope.security.management import endInteraction, newInteraction

from lp.services.webapp.interfaces import ISessionData, ISessionDataContainer
from lp.services.webapp.pgsession import PGSessionData, PGSessionDataContainer
from lp.testing import TestCase
from lp.testing.layers import LaunchpadFunctionalLayer, LaunchpadLayer


class PicklingTest:
    """This class is used to ensure we can store arbitrary pickles"""

    def __init__(self, value):
        self.value = value

    def __eq__(self, obj):
        return self.value == obj.value


class TestPgSession(TestCase):
    dbuser = "session"
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super().setUp()
        self.sdc = PGSessionDataContainer()
        self.addCleanup(delattr, self, "sdc")
        LaunchpadLayer.resetSessionDb()
        self.request = TestRequest()
        self.addCleanup(delattr, self, "request")
        newInteraction(self.request)
        self.addCleanup(endInteraction)

    def test_sdc_basics(self):
        # Make sure we have the correct class and it provides the required
        # interface.
        self.assertTrue(isinstance(self.sdc, PGSessionDataContainer))
        self.assertTrue(ISessionDataContainer.providedBy(self.sdc))

        client_id = "Client Id"

        # __getitem__ does not raise a keyerror for an unknown client id.
        # This is not correct, but needed to work around a design flaw in
        # the session machinery.
        self.assertNotEqual(None, self.sdc["Unknown client id"])

        # __setitem__ calls are ignored.
        self.sdc[client_id] = "ignored"

        # Once __setitem__ is called, we can access the SessionData
        session_data = self.sdc[client_id]
        self.assertTrue(isinstance(session_data, PGSessionData))
        self.assertTrue(ISessionData.providedBy(session_data))

    def test_storage(self):
        client_id1 = "Client Id #1"
        client_id2 = "Client Id #2"
        product_id1 = "Product Id #1"
        product_id2 = "Product Id #2"

        # Create some SessionPkgData storages
        self.sdc[client_id1] = "whatever"
        self.sdc[client_id2] = "whatever"
        session1a = self.sdc[client_id1][product_id1]

        # Set some values in the session
        session1a["key1"] = "value1"
        session1a["key2"] = PicklingTest("value2")
        self.assertEqual(session1a["key1"], "value1")
        self.assertEqual(session1a["key2"].value, "value2")

        # Make sure no leakage between sessions
        session1b = self.sdc[client_id1][product_id2]
        session2a = self.sdc[client_id2][product_id1]
        self.assertRaises(KeyError, session1b.__getitem__, "key")
        self.assertRaises(KeyError, session2a.__getitem__, "key")

        # Make sure data can be retrieved from the db
        session1a_dupe = self.sdc[client_id1][product_id1]

        # This new session should not be the same object
        self.assertIsNot(session1a, session1a_dupe)

        # But it should contain copies of the same data, unpickled from the
        # database
        self.assertEqual(session1a["key1"], session1a_dupe["key1"])
        self.assertEqual(session1a["key2"], session1a_dupe["key2"])

        # They must be copies - not the same object
        self.assertIsNot(session1a["key2"], session1a_dupe["key2"])

        # Ensure the keys method works as it is suppsed to
        self.assertContentEqual(session1a.keys(), ["key1", "key2"])
        self.assertContentEqual(session2a.keys(), [])

        # Ensure we can delete and alter things from the session
        del session1a["key1"]
        session1a["key2"] = "new value2"
        self.assertRaises(KeyError, session1a.__getitem__, "key1")
        self.assertEqual(session1a["key2"], "new value2")
        self.assertContentEqual(session1a.keys(), ["key2"])

        # Note that deleting will not raise a KeyError
        del session1a["key1"]
        del session1a["key1"]
        del session1a["whatever"]

        # And ensure that these changes are persistent
        session1a_dupe = self.sdc[client_id1][product_id1]
        self.assertRaises(KeyError, session1a_dupe.__getitem__, "key1")
        self.assertEqual(session1a_dupe["key2"], "new value2")
        self.assertContentEqual(session1a_dupe.keys(), ["key2"])

    def test_session_only_stored_when_changed(self):
        # A record of the session is only stored in the database when
        # some data is stored against the session.
        client_id = "Client Id #1"
        product_id = "Product Id"

        session = self.sdc[client_id]
        pkgdata = session[product_id]
        self.assertRaises(KeyError, pkgdata.__getitem__, "key")

        # Test results depend on the session being empty. This is
        # taken care of by setUp().
        store = self.sdc.store
        result = store.execute("SELECT COUNT(*) FROM SessionData")
        self.assertEqual(result.get_one()[0], 0)

        # The session cookie is also not yet set in the response.
        self.assertEqual(
            self.request.response.getCookie("launchpad_tests"), None
        )

        # Now try storing some data in the session, which will result
        # in it being stored in the database.
        pkgdata["key"] = "value"
        result = store.execute(
            "SELECT client_id FROM SessionData ORDER BY client_id"
        )
        client_ids = [row[0] for row in result]
        self.assertEqual(
            client_ids, [hashlib.sha256(client_id.encode("ASCII")).hexdigest()]
        )

        # The session cookie also is now set, via the same "trigger".
        self.assertNotEqual(
            self.request.response.getCookie("launchpad_tests"), None
        )

        # also see the page test xx-no-anonymous-session-cookies for tests of
        # the cookie behaviour.

    def test_datetime_compatibility(self):
        # datetime objects serialized by either Python 2 or 3 can be
        # unserialized as part of the session.
        client_id = "Client Id #1"
        product_id = "Product Id"
        expected_datetime = datetime(2021, 3, 4, 0, 50, 1, 300000)

        session = self.sdc[client_id]
        session._ensureClientId()

        # These are returned by the following code in Python 2.7 and 3.5
        # respectively:
        #
        #     pickle.dumps(expected_datetime, protocol=2)
        python_2_pickle = (
            b"\x80\x02cdatetime\ndatetime\nq\x00"
            b"U\n\x07\xe5\x03\x04\x002\x01\x04\x93\xe0q\x01\x85q\x02Rq\x03."
        )
        python_3_pickle = (
            b"\x80\x02cdatetime\ndatetime\nq\x00"
            b"c_codecs\nencode\nq\x01"
            b"X\r\x00\x00\x00\x07\xc3\xa5\x03\x04\x002\x01\x04\xc2\x93\xc3\xa0"
            b"q\x02X\x06\x00\x00\x00latin1q\x03\x86q\x04Rq\x05\x85q\x06R"
            b"q\x07."
        )

        store = self.sdc.store
        store.execute(
            "SELECT set_session_pkg_data(?, ?, ?, ?)",
            (
                session.hashed_client_id,
                product_id,
                "logintime",
                python_2_pickle,
            ),
            noresult=True,
        )
        store.execute(
            "SELECT set_session_pkg_data(?, ?, ?, ?)",
            (
                session.hashed_client_id,
                product_id,
                "last_write",
                python_3_pickle,
            ),
            noresult=True,
        )

        pkgdata = session[product_id]
        self.assertEqual(expected_datetime, pkgdata["logintime"])
        self.assertEqual(expected_datetime, pkgdata["last_write"])
