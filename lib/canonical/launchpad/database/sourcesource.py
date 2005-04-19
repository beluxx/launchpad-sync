"""Launchpad SourceSource Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

# Zope
from zope.interface import implements
from zope.component import getUtility

# SQL object
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote
from canonical.database.datetimecol import UtcDateTimeCol

# Launchpad interfaces
from canonical.launchpad.interfaces import ISourceSource, \
    ISourceSourceAdmin, ISourceSourceSet, IProductSet

from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import ImportTestStatus
from canonical.lp.dbschema import ImportStatus
from canonical.lp.dbschema import RevisionControlSystems
# tools
import datetime
from sets import Set
import logging

class XXXXSourceSource(SQLBase): 
    """SourceSource table"""

    implements (ISourceSource,
                ISourceSourceAdmin)
    
    _table = 'SourceSource'

    # canonical.lp.dbschema.ImportStatus
    importstatus = EnumCol(dbName='importstatus', notNull=True,
                         schema=ImportStatus, default=ImportStatus.TESTING)
    name = StringCol(default=None)
    title = StringCol(default=None)
    description = StringCol(default=None)
    cvsroot = StringCol(default=None)
    cvsmodule = StringCol(default=None)
    cvstarfile = ForeignKey(foreignKey='LibraryFileAlias',
                   dbName='cvstarfile', default=None)
    cvstarfileurl = StringCol(default=None)
    cvsbranch = StringCol(default=None)
    svnrepository = StringCol(default=None)
    # where are the tarballs released from this branch placed?
    releaseroot = StringCol(default=None)
    releaseverstyle = StringCol(default=None)
    releasefileglob = StringCol(default=None)
    releaseparentbranch = ForeignKey(foreignKey='Branch',
                   dbName='releaseparentbranch', default=None)
    branch = ForeignKey(foreignKey='Branch', dbName='branch', default=None)
    lastsynced = UtcDateTimeCol(default=None)
    syncinterval = DateTimeCol(default=None)
    rcstype = EnumCol(dbName='rcstype',
                      default=RevisionControlSystems.CVS,
                      schema=RevisionControlSystems,
                      notNull=True)
    hosted = StringCol(default=None)
    upstreamname = StringCol(default=None)
    processingapproved = UtcDateTimeCol(default=None)
    syncingapproved = UtcDateTimeCol(default=None)
    # For when Rob approves it
    newarchive = StringCol(default=None)
    newbranchcategory = StringCol(default=None)
    newbranchbranch = StringCol(default=None)
    newbranchversion = StringCol(default=None)
    # Temporary HORRIBLE HACK keybuk stuff
    packagedistro = StringCol(default=None)
    packagefiles_collapsed = StringCol(default=None)
    owner = ForeignKey(foreignKey='Person', dbName='owner',
                   notNull=True)
    currentgpgkey = StringCol(default=None)
    fileidreference = StringCol(default=None)
    dateautotested = UtcDateTimeCol(default=None)
    datestarted = UtcDateTimeCol(default=None)
    datefinished = UtcDateTimeCol(default=None)
    productseries = ForeignKey(dbName='productseries',
                               foreignKey='ProductSeries',
                               notNull=True)

    # properties
    def product(self):
        return self.productseries.product
    product = property(product)

    def namesReviewed(self):
        if not (self.product.reviewed and self.product.active):
            return False
        if self.product.project is None:
            return True
        if self.product.project.reviewed and self.product.project.active:
            return True
        return False

    def certifyForSync(self):
        """enable the sync for processing"""
        self.processingapproved = 'NOW'
        self.syncinterval = datetime.timedelta(1)
        self.importstatus = ImportStatus.PROCESSING

    def syncCertified(self):
        """is the sync enabled"""
        return self.processingapproved is not None

    def autoSyncEnabled(self):
        """is the sync automatically scheduling"""
        return self.importstatus == ImportStatus.SYNCING

    def enableAutoSync(self):
        """enable autosyncing"""
        self.syncingapproved = 'NOW'
        self.importstatus = ImportStatus.SYNCING

    def canChangeProductSeries(self):
        """is this sync allowed to have its product series changed?"""
        return self.product.name == "unassigned"

    def changeProductSeries(self, series):
        """change the productseries this sync belongs to"""
        assert (self.canChangeProductSeries())
        self.productseries = series

    def needsReview(self):
        if not self.syncapproved and self.dateautotested:
            return True
        return False

    def _get_repository(self):
        # XXX: Is that used anywhere but in buildJob? If not, that should
        # probably be moved to buildbot as well. -- David Allouche 2005-03-25
        if self.rcstype == RevisionControlSystems.CVS:
            return self.cvsroot
        elif self.rcstype == RevisionControlSystems.SVN:
            return self.svnrepository
        else:
            logging.critical ("unhandled source rcs type: %s", self.rcstype)
            # FIXME!
            return None

    def _get_package_files(self):
        # XXX: Not used anywhere but in buildJob. Should that be moved to
        # buildbot? -- David Allouche 2005-03-25
        if self.package_files_collapsed is None:
            return None
        return self.package_files_collapsed.split()


class XXXXSourceSourceSet(object):
    """The set of SourceSource's."""
    implements(ISourceSourceSet)

    def __init__(self):
        self.title = 'Bazaar Upstream Imports'

    def __getitem__(self, sourcesourcename):
        ss = SourceSource.selectBy(name=sourcesourcename)
        return ss[0]

    def _querystr(self, ready=None, text=None, state=None):
        """Return a querystring and clauseTables for use in a search or a
        get or a query."""
        query = '1=1'
        clauseTables = Set()
        clauseTables.add('SourceSource')
        # deal with the cases which require project and product
        if ( ready is not None ) or text:
            if len(query) > 0:
                query = query + ' AND\n'
            query += "SourceSource.product = Product.id"
            if text:
                query += ' AND Product.fti @@ ftq(%s)' % quote(text)
            if ready is not None:
                query += ' AND '
                query += 'Product.active IS TRUE AND '
                query += 'Product.reviewed IS TRUE '
            query += ' AND '
            query += '( Product.project IS NULL OR '
            query += '( Product.project = Project.id '
            if text:
                query += ' AND Project.fti @@ ftq(%s) ' % quote(text)
            if ready is not None:
                query += ' AND '
                query += 'Project.active IS TRUE AND '
                query += 'Project.reviewed IS TRUE'
            query += ') )'
            clauseTables.add('Project')
            clauseTables.add('Product')
        # now just add filters on sourcesource
        if state:
            if len(query) > 0:
                query += ' AND '
            query += 'SourceSource.importstatus = %d' % state
        return query, clauseTables

    def search(self, ready=None, 
                     text=None,
                     state=None,
                     start=None,
                     length=None):
        query, clauseTables = self._querystr(ready, text, state)
        return SourceSource.select(query, distinct=True,
                                   clauseTables=clauseTables)[start:length]
        

    # this is pedantic, to get every item individually, but it does allow
    # for making sure nothing gets passed in accidentally.
    def newSourceSource(self,
            owner=None,
            productseries=None,
            rcstype=None,
            cvsroot=None,
            cvsmodule=None,
            cvsbranch=None,
            cvstarfileurl=None,
            svnrepository=None,
            releaseroot=None,
            releaseverstyle=None,
            releasefileglob=None):
        return SourceSource(
            owner=owner,
            productseries=productseries,
            rcstype=rcstype,
            cvsroot=cvsroot,
            cvsmodule=cvsmodule,
            cvsbranch=cvsbranch,
            cvstarfileurl=cvstarfileurl,
            svnrepository=svnrepository,
            releaseroot=releaseroot,
            releaseverstyle=releaseverstyle,
            releasefileglob=releasefileglob)

