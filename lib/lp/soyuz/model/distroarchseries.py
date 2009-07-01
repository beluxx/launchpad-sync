# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['DistroArchSeries',
           'DistroArchSeriesSet',
           'PocketChroot'
           ]

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    BoolCol, IntCol, StringCol, ForeignKey, SQLRelatedJoin, SQLObjectNotFound)
from storm.locals import SQL, Join
from storm.store import EmptyResultSet

from canonical.database.sqlbase import SQLBase, sqlvalues, quote_like, quote
from canonical.database.constants import DEFAULT
from canonical.database.enumcol import EnumCol

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet)
from canonical.launchpad.interfaces._schema_circular_imports import (
    IHasBuildRecords)
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageName
from lp.soyuz.interfaces.binarypackagerelease import IBinaryPackageReleaseSet
from lp.soyuz.interfaces.build import IBuildSet
from lp.soyuz.interfaces.distroarchseries import (
    IDistroArchSeries, IDistroArchSeriesSet, IPocketChroot)
from lp.soyuz.interfaces.publishing import (
    ICanPublishPackages, PackagePublishingPocket, PackagePublishingStatus)
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.distroarchseriesbinarypackage import (
    DistroArchSeriesBinaryPackage)
from lp.registry.interfaces.person import validate_public_person
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory)
from lp.soyuz.model.processor import Processor
from lp.soyuz.model.binarypackagerelease import (
    BinaryPackageRelease)
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, SLAVE_FLAVOR)

class DistroArchSeries(SQLBase):
    implements(IDistroArchSeries, IHasBuildRecords, ICanPublishPackages)
    _table = 'DistroArchSeries'
    _defaultOrder = 'id'

    distroseries = ForeignKey(dbName='distroseries',
        foreignKey='DistroSeries', notNull=True)
    processorfamily = ForeignKey(dbName='processorfamily',
        foreignKey='ProcessorFamily', notNull=True)
    architecturetag = StringCol(notNull=True)
    official = BoolCol(notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    package_count = IntCol(notNull=True, default=DEFAULT)
    supports_virtualized = BoolCol(notNull=False, default=False)

    packages = SQLRelatedJoin('BinaryPackageRelease',
        joinColumn='distroarchseries',
        intermediateTable='BinaryPackagePublishing',
        otherColumn='binarypackagerelease')

    def __getitem__(self, name):
        return self.getBinaryPackage(name)

    @property
    def default_processor(self):
        """See `IDistroArchSeries`."""
        # XXX cprov 2005-08-31:
        # This could possibly be better designed; let's think about it in
        # the future. Pick the first processor we found for this
        # distroarchseries.processorfamily. The data model should
        # change to have a default processor for a processorfamily
        return self.processors[0]

    @property
    def processors(self):
        """See `IDistroArchSeries`."""
        return Processor.selectBy(family=self.processorfamily, orderBy='id')

    @property
    def title(self):
        """See `IDistroArchSeries`."""
        return '%s for %s (%s)' % (
            self.distroseries.title, self.architecturetag,
            self.processorfamily.name
            )

    @property
    def displayname(self):
        """See `IDistroArchSeries`."""
        return '%s %s %s' % (
            self.distroseries.distribution.displayname,
            self.distroseries.displayname, self.architecturetag)

    def updatePackageCount(self):
        """See `IDistroArchSeries`."""
        query = """
            BinaryPackagePublishingHistory.distroarchseries = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.status = %s AND
            BinaryPackagePublishingHistory.pocket = %s
            """ % sqlvalues(
                    self,
                    self.distroseries.distribution.all_distro_archive_ids,
                    PackagePublishingStatus.PUBLISHED,
                    PackagePublishingPocket.RELEASE
                 )
        self.package_count = BinaryPackagePublishingHistory.select(
            query).count()

    @property
    def isNominatedArchIndep(self):
        """See `IDistroArchSeries`."""
        return (self.distroseries.nominatedarchindep and
                self.id == self.distroseries.nominatedarchindep.id)

    def getPocketChroot(self):
        """See `IDistroArchSeries`."""
        pchroot = PocketChroot.selectOneBy(distroarchseries=self)
        return pchroot

    def getChroot(self, default=None):
        """See `IDistroArchSeries`."""
        pocket_chroot = self.getPocketChroot()

        if pocket_chroot is None:
            return default

        return pocket_chroot.chroot

    def addOrUpdateChroot(self, chroot):
        """See `IDistroArchSeries`."""
        pocket_chroot = self.getPocketChroot()

        if pocket_chroot is None:
            return PocketChroot(distroarchseries=self, chroot=chroot)
        else:
            pocket_chroot.chroot = chroot

        return pocket_chroot

    def findPackagesByName(self, pattern, fti=False):
        """Search BinaryPackages matching pattern and archtag"""
        binset = getUtility(IBinaryPackageReleaseSet)
        return binset.findByNameInDistroSeries(
            self.distroseries, pattern, self.architecturetag, fti)

    def searchBinaryPackages(self, text):
        """See `IDistroArchSeries`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)
        origin = [
            BinaryPackageRelease,
            Join(
                BinaryPackagePublishingHistory,
                BinaryPackagePublishingHistory.binarypackagerelease ==
                    BinaryPackageRelease.id
                ),
            Join(
                BinaryPackageName,
                BinaryPackageRelease.binarypackagename ==
                    BinaryPackageName.id
                )
            ]
        find_spec = (
            BinaryPackageRelease,
            BinaryPackageName,
            SQL("rank(BinaryPackageRelease.fti, ftq(%s)) AS rank" %
                sqlvalues(text))
            )
        archives = self.distroseries.distribution.getArchiveIDList()

        # Note: When attempting to convert the query below into straight
        # Storm expressions, a 'tuple index out-of-range' error was always
        # raised.
        result = store.using(*origin).find(
            find_spec,
            """
            BinaryPackagePublishingHistory.distroarchseries = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.dateremoved is NULL AND
            (BinaryPackageRelease.fti @@ ftq(%s) OR
             BinaryPackageName.name ILIKE '%%' || %s || '%%')
            """ % (quote(self), quote(archives),
                   quote(text), quote_like(text))
            ).config(distinct=True)

        result = result.order_by("rank DESC, BinaryPackageName.name")

        # import here to avoid circular import problems
        from canonical.launchpad.database import (
            DistroArchSeriesBinaryPackageRelease)

        # Create a function that will decorate the results, converting
        # them from the find_spec above into DASBPRs:
        def result_to_dasbpr(
            (binary_package_release, binary_package_name, rank)):
            return DistroArchSeriesBinaryPackageRelease(
                distroarchseries=self,
                binarypackagerelease=binary_package_release)

        # Return the decorated result set so the consumer of these
        # results will only see DSPs
        return DecoratedResultSet(result, result_to_dasbpr)

    def getBinaryPackage(self, name):
        """See `IDistroArchSeries`."""
        if not IBinaryPackageName.providedBy(name):
            try:
                name = BinaryPackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return DistroArchSeriesBinaryPackage(
            self, name)

    def getBuildRecords(self, build_state=None, name=None, pocket=None,
                        arch_tag=None, user=None):
        """See IHasBuildRecords"""
        # Ignore "user", since it would not make any difference to the
        # records returned here (private builds are only in PPA right
        # now).

        # For consistency we return an empty resultset if arch_tag
        # is provided but doesn't match our architecture.
        if arch_tag is not None and arch_tag != self.architecturetag:
            return EmptyResultSet()

        # Use the facility provided by IBuildSet to retrieve the records.
        return getUtility(IBuildSet).getBuildsByArchIds(
            [self.id], build_state, name, pocket)

    def getReleasedPackages(self, binary_name, pocket=None,
                            include_pending=False, exclude_pocket=None,
                            archive=None):
        """See IDistroArchSeries."""
        queries = []

        if not IBinaryPackageName.providedBy(binary_name):
            binary_name = BinaryPackageName.byName(binary_name)

        queries.append("""
        binarypackagerelease=binarypackagerelease.id AND
        binarypackagerelease.binarypackagename=%s AND
        distroarchseries = %s
        """ % sqlvalues(binary_name, self))

        if pocket is not None:
            queries.append("pocket=%s" % sqlvalues(pocket.value))

        if exclude_pocket is not None:
            queries.append("pocket!=%s" % sqlvalues(exclude_pocket.value))

        if include_pending:
            queries.append("status in (%s, %s)" % sqlvalues(
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingStatus.PENDING))
        else:
            queries.append("status=%s" % sqlvalues(
                PackagePublishingStatus.PUBLISHED))

        archives = self.distroseries.distribution.getArchiveIDList(archive)
        queries.append("archive IN %s" % sqlvalues(archives))

        published = BinaryPackagePublishingHistory.select(
            " AND ".join(queries),
            clauseTables = ['BinaryPackageRelease'],
            orderBy=['-id'])

        return shortlist(published)

    def getPendingPublications(self, archive, pocket, is_careful):
        """See `ICanPublishPackages`."""
        queries = [
            "distroarchseries = %s AND archive = %s"
            % sqlvalues(self, archive)
            ]

        target_status = [PackagePublishingStatus.PENDING]
        if is_careful:
            target_status.append(PackagePublishingStatus.PUBLISHED)
        queries.append("status IN %s" % sqlvalues(target_status))

        # restrict to a specific pocket.
        queries.append('pocket = %s' % sqlvalues(pocket))

        # Exclude RELEASE pocket if the distroseries was already released,
        # since it should not change, unless the archive allows it.
        if (not self.distroseries.isUnstable() and
            not archive.allowUpdatesToReleasePocket()):
            queries.append(
            'pocket != %s' % sqlvalues(PackagePublishingPocket.RELEASE))

        publications = BinaryPackagePublishingHistory.select(
                    " AND ".join(queries), orderBy=["-id"])

        return publications

    def publish(self, diskpool, log, archive, pocket, is_careful=False):
        """See `ICanPublishPackages`."""
        log.debug("Attempting to publish pending binaries for %s"
              % self.architecturetag)

        dirty_pockets = set()

        for bpph in self.getPendingPublications(archive, pocket, is_careful):
            if not self.distroseries.checkLegalPocket(
                bpph, is_careful, log):
                continue
            bpph.publish(diskpool, log)
            dirty_pockets.add((self.distroseries.name, bpph.pocket))

        return dirty_pockets

    @property
    def main_archive(self):
        return self.distroseries.distribution.main_archive


class DistroArchSeriesSet:
    """This class is to deal with DistroArchSeries related stuff"""

    implements(IDistroArchSeriesSet)

    def __iter__(self):
        return iter(DistroArchSeries.select())

    def get(self, dar_id):
        """See `canonical.launchpad.interfaces.IDistributionSet`."""
        return DistroArchSeries.get(dar_id)

    def count(self):
        return DistroArchSeries.select().count()


class PocketChroot(SQLBase):
    implements(IPocketChroot)
    _table = "PocketChroot"

    distroarchseries = ForeignKey(dbName='distroarchseries',
                                   foreignKey='DistroArchSeries',
                                   notNull=True)

    pocket = EnumCol(schema=PackagePublishingPocket,
                     default=PackagePublishingPocket.RELEASE,
                     notNull=True)

    chroot = ForeignKey(dbName='chroot', foreignKey='LibraryFileAlias')

