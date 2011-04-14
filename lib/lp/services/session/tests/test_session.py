# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Session tests."""

__metaclass__ = type

from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    ISlaveStore,
    IStore,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.session.model import (
    SessionData,
    SessionPkgData,
    )
from lp.testing import TestCase


class TestSessionModelAdapters(TestCase):
    layer = DatabaseFunctionalLayer

    def test_adapters(self):
        for adapter in [IMasterStore, ISlaveStore, IStore]:
            for cls in [SessionData, SessionPkgData]:
                for obj in [cls, cls()]:
                    store = adapter(obj)
                    self.assert_(
                        'session' in store.get_database()._dsn,
                        'Unknown store returned adapting %r to %r'
                        % (obj, adapter))
