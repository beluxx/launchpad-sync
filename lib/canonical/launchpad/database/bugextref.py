from datetime import datetime

# Zope
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBugExternalRef, IBugExternalRefSet

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database.bugset import BugSetBase



class BugExternalRef(SQLBase):
    """An external reference for a bug, not supported remote bug systems."""

    implements(IBugExternalRef)

    _table = 'BugExternalRef'
    bug = ForeignKey(foreignKey='Bug', dbName='bug', notNull=True)
    url = StringCol(notNull=True)
    title = StringCol(notNull=True)
    datecreated = DateTimeCol(notNull=True, default=datetime.utcnow())
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)

class BugExternalRefSet(BugSetBase):
    """A set for BugExternalRef."""

    implements(IBugExternalRefSet)
    table = BugExternalRef

    def __init__(self, bug=None):
        super(BugExternalRefSet, self).__init__(bug)
        self.title = 'Web References'
        if bug:
            self.title += ' for Malone Bug #' + str(bug)

    def createBugExternalRef(self, bug, url, title, owner):
        """See canonical.launchpad.interfaces.IBugExternalRefSet."""
        return BugExternalRef(
            bug = bug, url = url, title = title, owner = owner)

def BugExternalRefFactory(context, **kw):
    bug = context.context.bug
    datecreated = datetime.utcnow()
    return BugExternalRef(
        bug=bug,
        owner=context.request.principal.id,
        **kw)

