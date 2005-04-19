from datetime import datetime

# Zope
from zope.interface import implements
from zope.exceptions import NotFoundError

# SQL imports
from sqlobject import ForeignKey, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR
from sqlobject import SQLObjectNotFound

from canonical.launchpad.interfaces import IBugWatch, \
        IBugWatchSet
from canonical.launchpad.database.bug import BugSetBase
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol


class BugWatch(SQLBase):
    implements(IBugWatch)
    _table = 'BugWatch'
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    bugtracker = ForeignKey(dbName='bugtracker',
                foreignKey='BugTracker', notNull=True)
    remotebug = StringCol(notNull=True)
    remotestatus = StringCol(notNull=False, default=None)
    lastchanged = UtcDateTimeCol(notNull=False, default=None)
    lastchecked = UtcDateTimeCol(notNull=False, default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    owner = ForeignKey(dbName='owner', foreignKey='Person',
                notNull=True)

    def _title(self):
        title = 'Malone Bug #' + str(self.bug.id)
        title += ' maps to bug #' + str(self.remotebug)
        title += ' in ' + self.bugtracker.title
        return title
    title = property(_title)

class BugWatchSet(BugSetBase):
    """A set for BugWatch"""

    implements(IBugWatchSet)
    table = BugWatch

    def __init__(self, bug=None):
        super(BugWatchSet, self).__init__(bug)
        self.title = 'A Set of Bug Watches'

    def get(self, id):
        """See canonical.launchpad.interfaces.IBugWatchSet."""
        try:
            return BugWatch.get(id)
        except SQLObjectNotFound:
            raise NotFoundError("BugWatch with ID %d does not exist" % id)

def BugWatchFactory(context, **kw):
    bug = context.context.bug
    return BugWatch(
        bug=bug, owner=context.request.principal.id, datecreated=UTC_NOW,
        lastchanged=UTC_NOW, lastchecked=UTC_NOW, **kw)
