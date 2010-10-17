# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Launchpad functional test helpers.

This file needs to be refactored, moving its functionality into
canonical.testing
"""

__metaclass__ = type


from zope.app.testing.functional import FunctionalTestSetup

from canonical.database.sqlbase import ZopelessTransactionManager
from canonical.ftests.pgsql import PgTestSetup
from canonical.lp import initZopeless
from canonical.testing.layers import (
    FunctionalLayer,
    ZopelessLayer,
    )
from canonical.testing.layers import (
    disconnect_stores,
    reconnect_stores,
    )


__all__ = [
    'LaunchpadTestSetup', 'LaunchpadZopelessTestSetup',
    'LaunchpadFunctionalTestSetup',
    ]


class LaunchpadTestSetup(PgTestSetup):
    template = 'launchpad_ftest_template'
    dbname = 'launchpad_ftest' # Needs to match ftesting.zcml
    dbuser = 'launchpad'


class LaunchpadFunctionalTestSetup(LaunchpadTestSetup):
    def _checkLayerInvariants(self):
        assert FunctionalLayer.isSetUp or ZopelessLayer.isSetUp, """
                FunctionalTestSetup invoked at an inappropriate time.
                May only be invoked in the FunctionalLayer or ZopelessLayer
                """

    def setUp(self, dbuser=None):
        self._checkLayerInvariants()
        if dbuser is not None:
            self.dbuser = dbuser
        assert self.dbuser == 'launchpad', (
            "Non-default user names should probably be using "
            "script layer or zopeless layer.")
        disconnect_stores()
        super(LaunchpadFunctionalTestSetup, self).setUp()
        FunctionalTestSetup().setUp()
        reconnect_stores()

    def tearDown(self):
        self._checkLayerInvariants()
        FunctionalTestSetup().tearDown()
        disconnect_stores()
        super(LaunchpadFunctionalTestSetup, self).tearDown()
