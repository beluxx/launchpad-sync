# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Session Storm database classes"""

__all__ = ["SessionData", "SessionPkgData"]

from storm.locals import Pickle, Storm, Unicode
from zope.interface import implementer, provider

from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.session.interfaces import IUseSessionStore


@implementer(IUseSessionStore)
@provider(IUseSessionStore)
class SessionData(Storm):
    """A user's Session."""

    __storm_table__ = "SessionData"
    client_id = Unicode(primary=True)
    created = UtcDateTimeCol()
    last_accessed = UtcDateTimeCol()


@implementer(IUseSessionStore)
@provider(IUseSessionStore)
class SessionPkgData(Storm):
    """Data storage for a Session."""

    __storm_table__ = "SessionPkgData"
    __storm_primary__ = "client_id", "product_id", "key"

    client_id = Unicode()
    product_id = Unicode()
    key = Unicode()
    pickle = Pickle()
