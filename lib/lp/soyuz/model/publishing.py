# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'BinaryPackagePublishingHistory',
    'get_current_source_releases',
    'makePoolPath',
    'PublishingSet',
    'SourcePackagePublishingHistory',
    ]


from collections import defaultdict
from datetime import datetime
from operator import (
    attrgetter,
    itemgetter,
    )
import os
import sys

import pytz
import six
from sqlobject import (
    ForeignKey,
    IntCol,
    StringCol,
    )
from storm.expr import (
    And,
    Cast,
    Desc,
    Join,
    LeftJoin,
    Not,
    Or,
    Sum,
    )
from storm.info import ClassAlias
from storm.store import Store
from storm.zope import IResultSet
from storm.zope.interfaces import ISQLObjectResultSet
from zope.component import getUtility
from zope.interface import implementer
from zope.security.proxy import (
    isinstance as zope_isinstance,
    removeSecurityProxy,
    )

from lp.app.errors import NotFoundError
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.person import validate_public_person
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database import bulk
from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.sqlbase import SQLBase
from lp.services.database.stormexpr import IsDistinctFrom
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.librarian.model import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.services.webapp.errorlog import (
    ErrorReportingUtility,
    ScriptRequest,
    )
from lp.services.worlddata.model.country import Country
from lp.soyuz.adapters.proxiedsourcefiles import ProxiedSourceLibraryFileAlias
from lp.soyuz.enums import (
    BinaryPackageFormat,
    PackagePublishingPriority,
    PackagePublishingStatus,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.binarypackagebuild import (
    BuildSetStatus,
    IBinaryPackageBuildSet,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.distributionjob import (
    IDistroSeriesDifferenceJobSource,
    )
from lp.soyuz.interfaces.publishing import (
    active_publishing_status,
    DeletionError,
    IBinaryPackagePublishingHistory,
    IPublishingSet,
    ISourcePackagePublishingHistory,
    name_priority_map,
    OverrideError,
    PoolFileOverwriteError,
    )
from lp.soyuz.interfaces.section import ISectionSet
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import (
    BinaryPackageRelease,
    BinaryPackageReleaseDownloadCount,
    )
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.model.files import (
    BinaryPackageFile,
    SourcePackageReleaseFile,
    )
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


def makePoolPath(source_name, component_name):
    # XXX cprov 2006-08-18: move it away, perhaps archivepublisher/pool.py
    """Return the pool path for a given source name and component name."""
    from lp.archivepublisher.diskpool import poolify
    return os.path.join('pool', poolify(source_name, component_name))


def get_component(archive, distroseries, component):
    """Override the component to fit in the archive, if possible.

    If the archive has a default component, and it forbids use of the
    requested component in the requested series, use the default.

    If there is no default, just return the given component.
    """
    permitted_components = archive.getComponentsForSeries(distroseries)
    if (component not in permitted_components and
        archive.default_component is not None):
        return archive.default_component
    return component


def proxied_urls(files, parent):
    """Run the files passed through `ProxiedLibraryFileAlias`."""
    return [ProxiedLibraryFileAlias(file, parent).http_url for file in files]


def proxied_source_urls(files, parent):
    """Return the files passed through `ProxiedSourceLibraryFileAlias`."""
    return [
        ProxiedSourceLibraryFileAlias(file, parent).http_url for file in files]


class ArchivePublisherBase:
    """Base class for `IArchivePublisher`."""

    def setPublished(self):
        """see IArchiveSafePublisher."""
        # XXX cprov 2006-06-14:
        # Implement sanity checks before set it as published
        if (self.status in active_publishing_status and
                self.datepublished is None):
            # update the DB publishing record status if they
            # are pending, don't do anything for the ones
            # already published (usually when we use -C
            # publish-distro.py option)
            if self.status == PackagePublishingStatus.PENDING:
                self.status = PackagePublishingStatus.PUBLISHED
            self.datepublished = UTC_NOW

    def publish(self, diskpool, log):
        """See `IPublishing`"""
        try:
            for pub_file in self.files:
                source = self.source_package_name
                component = self.component.name
                filename = pub_file.libraryfile.filename
                filealias = pub_file.libraryfile
                sha1 = filealias.content.sha1
                path = diskpool.pathFor(component, source, filename)

                action = diskpool.addFile(
                    component, source, filename, sha1, filealias)
                if action == diskpool.results.FILE_ADDED:
                    log.debug("Added %s from library" % path)
                elif action == diskpool.results.SYMLINK_ADDED:
                    log.debug("%s created as a symlink." % path)
                elif action == diskpool.results.NONE:
                    log.debug(
                        "%s is already in pool with the same content." % path)
        except PoolFileOverwriteError as e:
            message = "PoolFileOverwriteError: %s, skipping." % e
            properties = [('error-explanation', message)]
            request = ScriptRequest(properties)
            error_utility = ErrorReportingUtility()
            error_utility.raising(sys.exc_info(), request)
            log.error('%s (%s)' % (message, request.oopsid))
        else:
            self.setPublished()

    def setSuperseded(self):
        """Set to SUPERSEDED status."""
        self.status = PackagePublishingStatus.SUPERSEDED
        self.datesuperseded = UTC_NOW

    def setDeleted(self, removed_by, removal_comment=None):
        """Set to DELETED status."""
        getUtility(IPublishingSet).setMultipleDeleted(
            self.__class__, [self.id], removed_by, removal_comment)

    def requestObsolescence(self):
        """See `IArchivePublisher`."""
        # The tactic here is to bypass the domination step when publishing,
        # and let it go straight to death row processing.  This is because
        # domination ignores stable distroseries, and that is exactly what
        # we're most likely to be obsoleting.
        #
        # Setting scheduleddeletiondate achieves that aim.
        self.status = PackagePublishingStatus.OBSOLETE
        self.scheduleddeletiondate = UTC_NOW
        return self

    @property
    def age(self):
        """See `IArchivePublisher`."""
        return datetime.now(pytz.UTC) - self.datecreated

    @property
    def component_name(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.component.name

    @property
    def section_name(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.section.name


@implementer(ISourcePackagePublishingHistory)
class SourcePackagePublishingHistory(SQLBase, ArchivePublisherBase):
    """A source package release publishing record."""

    sourcepackagename = ForeignKey(
        foreignKey='SourcePackageName', dbName='sourcepackagename')
    sourcepackagerelease = ForeignKey(
        foreignKey='SourcePackageRelease', dbName='sourcepackagerelease')
    distroseries = ForeignKey(foreignKey='DistroSeries', dbName='distroseries')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    status = EnumCol(schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=UTC_NOW)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(foreignKey='SourcePackageRelease',
                              dbName='supersededby', default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket,
                     default=PackagePublishingPocket.RELEASE,
                     notNull=True)
    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)
    copied_from_archive = ForeignKey(
        dbName="copied_from_archive", foreignKey="Archive", notNull=False)
    removed_by = ForeignKey(
        dbName="removed_by", foreignKey="Person",
        storm_validator=validate_public_person, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)
    ancestor = ForeignKey(
        dbName="ancestor", foreignKey="SourcePackagePublishingHistory",
        default=None)
    creator = ForeignKey(
        dbName='creator', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False, default=None)
    sponsor = ForeignKey(
        dbName='sponsor', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False, default=None)
    packageupload = ForeignKey(
        dbName='packageupload', foreignKey='PackageUpload', default=None)

    @property
    def package_creator(self):
        """See `ISourcePackagePublishingHistory`."""
        return self.sourcepackagerelease.creator

    @property
    def package_maintainer(self):
        """See `ISourcePackagePublishingHistory`."""
        return self.sourcepackagerelease.maintainer

    @property
    def package_signer(self):
        """See `ISourcePackagePublishingHistory`."""
        return self.sourcepackagerelease.signing_key_owner

    @cachedproperty
    def newer_distroseries_version(self):
        """See `ISourcePackagePublishingHistory`."""
        self.distroseries.setNewerDistroSeriesVersions([self])
        return get_property_cache(self).newer_distroseries_version

    def getPublishedBinaries(self):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        result_set = publishing_set.getBinaryPublicationsForSources(self)
        return DecoratedResultSet(result_set, result_decorator=itemgetter(1))

    def getBuiltBinaries(self, want_files=False):
        """See `ISourcePackagePublishingHistory`."""
        binary_publications = list(Store.of(self).find(
            BinaryPackagePublishingHistory,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.distroarchseriesID ==
                DistroArchSeries.id,
            BinaryPackagePublishingHistory.archiveID == self.archiveID,
            BinaryPackagePublishingHistory.pocket == self.pocket,
            BinaryPackageBuild.id == BinaryPackageRelease.buildID,
            BinaryPackageBuild.source_package_release_id ==
                self.sourcepackagereleaseID,
            DistroArchSeries.distroseriesID == self.distroseriesID).order_by(
                Desc(BinaryPackagePublishingHistory.id)))

        # Preload attached BinaryPackageReleases.
        bpr_ids = set(
            pub.binarypackagereleaseID for pub in binary_publications)
        list(Store.of(self).find(
            BinaryPackageRelease, BinaryPackageRelease.id.is_in(bpr_ids)))

        if want_files:
            # Preload BinaryPackageFiles.
            bpfs = list(Store.of(self).find(
                BinaryPackageFile,
                BinaryPackageFile.binarypackagereleaseID.is_in(bpr_ids)))
            bpfs_by_bpr = defaultdict(list)
            for bpf in bpfs:
                bpfs_by_bpr[bpf.binarypackagerelease].append(bpf)
            for bpr in bpfs_by_bpr:
                get_property_cache(bpr).files = bpfs_by_bpr[bpr]

            # Preload LibraryFileAliases.
            lfa_ids = set(bpf.libraryfileID for bpf in bpfs)
            list(Store.of(self).find(
                LibraryFileAlias, LibraryFileAlias.id.is_in(lfa_ids)))

        unique_binary_publications = []
        for pub in binary_publications:
            if pub.binarypackagerelease.id in bpr_ids:
                unique_binary_publications.append(pub)
                bpr_ids.remove(pub.binarypackagerelease.id)
                if len(bpr_ids) == 0:
                    break

        return unique_binary_publications

    @staticmethod
    def _convertBuilds(builds_for_sources):
        """Convert from IPublishingSet getBuilds to SPPH getBuilds."""
        return [build[1] for build in builds_for_sources]

    def getBuilds(self):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        result_set = publishing_set.getBuildsForSources([self])
        return SourcePackagePublishingHistory._convertBuilds(result_set)

    def getFileByName(self, name):
        """See `ISourcePackagePublishingHistory`."""
        changelog = self.sourcepackagerelease.changelog
        if changelog is not None and name == changelog.filename:
            return changelog
        raise NotFoundError(name)

    def changesFileUrl(self):
        """See `ISourcePackagePublishingHistory`."""
        # We use getChangesFileLFA() as opposed to getChangesFilesForSources()
        # because the latter is more geared towards the web UI and taxes the
        # db much more in terms of the join width and the pre-joined data.
        #
        # This method is accessed overwhelmingly via the LP API and calling
        # getChangesFileLFA() which is much lighter on the db has the
        # potential of performing significantly better.
        changes_lfa = getUtility(IPublishingSet).getChangesFileLFA(
            self.sourcepackagerelease)

        if changes_lfa is None:
            # This should not happen in practice, but the code should
            # not blow up because of bad data.
            return None

        # Return a webapp-proxied LibraryFileAlias so that restricted
        # librarian files are accessible.  Non-restricted files will get
        # a 302 so that webapp threads are not tied up.
        the_url = proxied_urls((changes_lfa,), self.archive)[0]
        return the_url

    def changelogUrl(self):
        """See `ISourcePackagePublishingHistory`."""
        lfa = self.sourcepackagerelease.changelog
        if lfa is not None:
            return proxied_urls((lfa,), self)[0]
        return None

    def createMissingBuilds(self, architectures_available=None, logger=None):
        """See `ISourcePackagePublishingHistory`."""
        return getUtility(IBinaryPackageBuildSet).createForSource(
            self.sourcepackagerelease, self.archive, self.distroseries,
            self.pocket, architectures_available, logger)

    @property
    def files(self):
        """See `IPublishing`."""
        files = self.sourcepackagerelease.files
        lfas = bulk.load_related(LibraryFileAlias, files, ['libraryfileID'])
        bulk.load_related(LibraryFileContent, lfas, ['contentID'])
        return files

    def getSourceAndBinaryLibraryFiles(self):
        """See `IPublishing`."""
        publishing_set = getUtility(IPublishingSet)
        result_set = publishing_set.getFilesForSources(self)
        libraryfiles = [file for source, file, content in result_set]

        # XXX cprov 20080710: UNIONs cannot be ordered appropriately.
        # See IPublishing.getFilesForSources().
        return sorted(libraryfiles, key=attrgetter('filename'))

    @property
    def meta_sourcepackage(self):
        """see `ISourcePackagePublishingHistory`."""
        return self.distroseries.getSourcePackage(
            self.sourcepackagerelease.sourcepackagename)

    @property
    def meta_distributionsourcepackagerelease(self):
        """see `ISourcePackagePublishingHistory`."""
        return self.distroseries.distribution.getSourcePackageRelease(
            self.sourcepackagerelease)

    # XXX: StevenK 2011-09-13 bug=848563: This can die when
    # self.sourcepackagename is populated.
    @property
    def source_package_name(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.sourcepackagerelease.name

    @property
    def source_package_version(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.sourcepackagerelease.version

    @property
    def displayname(self):
        """See `IPublishing`."""
        release = self.sourcepackagerelease
        name = release.sourcepackagename.name
        return "%s %s in %s" % (name, release.version, self.distroseries.name)

    def supersede(self, dominant=None, logger=None):
        """See `ISourcePackagePublishingHistory`."""
        assert self.status in active_publishing_status, (
            "Should not dominate unpublished source %s" %
            self.sourcepackagerelease.title)

        self.setSuperseded()

        if dominant is not None:
            if logger is not None:
                logger.debug(
                    "%s/%s has been judged as superseded by %s/%s" %
                    (self.sourcepackagerelease.sourcepackagename.name,
                     self.sourcepackagerelease.version,
                     dominant.sourcepackagerelease.sourcepackagename.name,
                     dominant.sourcepackagerelease.version))

            self.supersededby = dominant.sourcepackagerelease

    def changeOverride(self, new_component=None, new_section=None,
                       creator=None):
        """See `ISourcePackagePublishingHistory`."""
        # Check we have been asked to do something
        if (new_component is None and
            new_section is None):
            raise AssertionError("changeOverride must be passed either a"
                                 " new component or new section")

        # Check there is a change to make
        if new_component is None:
            new_component = self.component
        elif isinstance(new_component, six.string_types):
            new_component = getUtility(IComponentSet)[new_component]
        if new_section is None:
            new_section = self.section
        elif isinstance(new_section, six.string_types):
            new_section = getUtility(ISectionSet)[new_section]

        if new_component == self.component and new_section == self.section:
            return

        if new_component != self.component:
            # See if the archive has changed by virtue of the component
            # changing:
            distribution = self.distroseries.distribution
            new_archive = distribution.getArchiveByComponent(
                new_component.name)
            if new_archive != None and new_archive != self.archive:
                raise OverrideError(
                    "Overriding component to '%s' failed because it would "
                    "require a new archive." % new_component.name)

        # Refuse to create new publication records that will never be
        # published.
        if not self.archive.canModifySuite(self.distroseries, self.pocket):
            raise OverrideError(
                "Cannot change overrides in suite '%s'" %
                self.distroseries.getSuite(self.pocket))

        return getUtility(IPublishingSet).newSourcePublication(
            distroseries=self.distroseries,
            sourcepackagerelease=self.sourcepackagerelease,
            pocket=self.pocket,
            component=new_component,
            section=new_section,
            creator=creator,
            archive=self.archive)

    def copyTo(self, distroseries, pocket, archive, override=None,
               create_dsd_job=True, creator=None, sponsor=None,
               packageupload=None):
        """See `ISourcePackagePublishingHistory`."""
        component = self.component
        section = self.section
        if override is not None:
            if override.component is not None:
                component = override.component
            if override.section is not None:
                section = override.section

        return getUtility(IPublishingSet).newSourcePublication(
            archive,
            self.sourcepackagerelease,
            distroseries,
            component,
            section,
            pocket,
            ancestor=self,
            create_dsd_job=create_dsd_job,
            creator=creator,
            sponsor=sponsor,
            copied_from_archive=self.archive,
            packageupload=packageupload)

    def getStatusSummaryForBuilds(self):
        """See `ISourcePackagePublishingHistory`."""
        return getUtility(
            IPublishingSet).getBuildStatusSummaryForSourcePublication(self)

    def sourceFileUrls(self, include_meta=False):
        """See `ISourcePackagePublishingHistory`."""
        sources = Store.of(self).find(
            (LibraryFileAlias, LibraryFileContent),
            LibraryFileContent.id == LibraryFileAlias.contentID,
            LibraryFileAlias.id == SourcePackageReleaseFile.libraryfileID,
            SourcePackageReleaseFile.sourcepackagerelease ==
                SourcePackageRelease.id,
            SourcePackageRelease.id == self.sourcepackagereleaseID)
        source_urls = proxied_source_urls(
            [source for source, _ in sources], self)
        if include_meta:
            meta = [
                (content.filesize, content.sha256) for _, content in sources]
            return [
                dict(url=url, size=size, sha256=sha256)
                for url, (size, sha256) in zip(source_urls, meta)]
        return source_urls

    def binaryFileUrls(self):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        binaries = publishing_set.getBinaryFilesForSources(
            self).config(distinct=True)
        binary_urls = proxied_urls(
            [binary for _source, binary, _content in binaries], self.archive)
        return binary_urls

    def packageDiffUrl(self, to_version):
        """See `ISourcePackagePublishingHistory`."""
        # There will be only very few diffs for each package so
        # iterating is fine here, since the package_diffs property is a
        # multiple join and returns all the diffs quite quickly.
        for diff in self.sourcepackagerelease.package_diffs:
            if diff.to_source.version == to_version:
                return ProxiedLibraryFileAlias(
                    diff.diff_content, self.archive).http_url
        return None

    def requestDeletion(self, removed_by, removal_comment=None,
                        immutable_check=True):
        """See `IPublishing`."""
        # Fail if operation would modify an immutable suite (eg. the
        # RELEASE pocket of a CURRENT series).
        if (immutable_check and
            not self.archive.canModifySuite(self.distroseries, self.pocket)):
            raise DeletionError(
                "Cannot delete publications from suite '%s'" %
                self.distroseries.getSuite(self.pocket))

        self.setDeleted(removed_by, removal_comment)
        if self.archive.is_main:
            dsd_job_source = getUtility(IDistroSeriesDifferenceJobSource)
            dsd_job_source.createForPackagePublication(
                self.distroseries,
                self.sourcepackagerelease.sourcepackagename, self.pocket)

    def api_requestDeletion(self, removed_by, removal_comment=None):
        """See `IPublishingEdit`."""
        # Special deletion method for the api that makes sure binaries
        # get deleted too.
        getUtility(IPublishingSet).requestDeletion(
            [self], removed_by, removal_comment)

    def hasRestrictedFiles(self):
        """See ISourcePackagePublishingHistory."""
        for source_file in self.sourcepackagerelease.files:
            if source_file.libraryfile.restricted:
                return True

        for binary in self.getBuiltBinaries():
            for binary_file in binary.binarypackagerelease.files:
                if binary_file.libraryfile.restricted:
                    return True

        return False


@implementer(IBinaryPackagePublishingHistory)
class BinaryPackagePublishingHistory(SQLBase, ArchivePublisherBase):
    """A binary package publishing record."""

    binarypackagename = ForeignKey(
        foreignKey='BinaryPackageName', dbName='binarypackagename')
    binarypackagerelease = ForeignKey(
        foreignKey='BinaryPackageRelease', dbName='binarypackagerelease')
    distroarchseries = ForeignKey(
        foreignKey='DistroArchSeries', dbName='distroarchseries')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    priority = EnumCol(dbName='priority', schema=PackagePublishingPriority)
    status = EnumCol(dbName='status', schema=PackagePublishingStatus)
    phased_update_percentage = IntCol(
        dbName='phased_update_percentage', notNull=False, default=None)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    creator = ForeignKey(
        dbName='creator', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False, default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=UTC_NOW)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(
        foreignKey='BinaryPackageBuild', dbName='supersededby', default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket)
    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)
    copied_from_archive = ForeignKey(
        dbName="copied_from_archive", foreignKey="Archive", notNull=False)
    removed_by = ForeignKey(
        dbName="removed_by", foreignKey="Person",
        storm_validator=validate_public_person, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)

    @property
    def distroarchseriesbinarypackagerelease(self):
        """See `IBinaryPackagePublishingHistory`."""
        # Import here to avoid circular import.
        from lp.soyuz.model.distroarchseriesbinarypackagerelease import (
            DistroArchSeriesBinaryPackageRelease)

        return DistroArchSeriesBinaryPackageRelease(
            self.distroarchseries,
            self.binarypackagerelease)

    @property
    def files(self):
        """See `IPublishing`."""
        files = self.binarypackagerelease.files
        lfas = bulk.load_related(LibraryFileAlias, files, ['libraryfileID'])
        bulk.load_related(LibraryFileContent, lfas, ['contentID'])
        return files

    @property
    def distroseries(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.distroarchseries.distroseries

    # XXX: StevenK 2011-09-13 bug=848563: This can die when
    # self.binarypackagename is populated.
    @property
    def binary_package_name(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.binarypackagerelease.name

    @property
    def binary_package_version(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.binarypackagerelease.version

    @property
    def build(self):
        return self.binarypackagerelease.build

    @property
    def source_package_name(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.binarypackagerelease.sourcepackagename

    @property
    def source_package_version(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.binarypackagerelease.sourcepackageversion

    @property
    def architecture_specific(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.binarypackagerelease.architecturespecific

    @property
    def is_debug(self):
        """See `IBinaryPackagePublishingHistory`."""
        return (
            self.binarypackagerelease.binpackageformat
            == BinaryPackageFormat.DDEB)

    @property
    def priority_name(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.priority.name

    @property
    def displayname(self):
        """See `IPublishing`."""
        release = self.binarypackagerelease
        name = release.binarypackagename.name
        distroseries = self.distroarchseries.distroseries
        return "%s %s in %s %s" % (name, release.version,
                                   distroseries.name,
                                   self.distroarchseries.architecturetag)

    def getDownloadCount(self):
        """See `IBinaryPackagePublishingHistory`."""
        return self.archive.getPackageDownloadTotal(self.binarypackagerelease)

    def publish(self, diskpool, log):
        """See `IPublishing`."""
        if self.is_debug and not self.archive.publish_debug_symbols:
            self.setPublished()
        else:
            super(BinaryPackagePublishingHistory, self).publish(diskpool, log)

    def getOtherPublications(self):
        """See `IBinaryPackagePublishingHistory`."""
        available_architectures = [
            das.id for das in
                self.distroarchseries.distroseries.architectures]
        return IMasterStore(BinaryPackagePublishingHistory).find(
                BinaryPackagePublishingHistory,
                BinaryPackagePublishingHistory.status.is_in(
                    active_publishing_status),
                BinaryPackagePublishingHistory.distroarchseriesID.is_in(
                    available_architectures),
                binarypackagerelease=self.binarypackagerelease,
                archive=self.archive,
                pocket=self.pocket,
                component=self.component,
                section=self.section,
                priority=self.priority,
                phased_update_percentage=self.phased_update_percentage)

    def supersede(self, dominant=None, logger=None):
        """See `IBinaryPackagePublishingHistory`."""
        # At this point only PUBLISHED (ancient versions) or PENDING (
        # multiple overrides/copies) publications should be given. We
        # tolerate SUPERSEDED architecture-independent binaries, because
        # they are dominated automatically once the first publication is
        # processed.
        if self.status not in active_publishing_status:
            assert not self.binarypackagerelease.architecturespecific, (
                "Should not dominate unpublished architecture specific "
                "binary %s (%s)" % (
                self.binarypackagerelease.title,
                self.distroarchseries.architecturetag))
            return

        self.setSuperseded()

        if dominant is not None:
            # DDEBs cannot themselves be dominant; they are always dominated
            # by their corresponding DEB. Any attempt to dominate with a
            # dominant DDEB is a bug.
            assert not dominant.is_debug, (
                "Should not dominate with %s (%s); DDEBs cannot dominate" % (
                    dominant.binarypackagerelease.title,
                    dominant.distroarchseries.architecturetag))

            dominant_build = dominant.binarypackagerelease.build
            distroarchseries = dominant_build.distro_arch_series
            if logger is not None:
                logger.debug(
                    "The %s build of %s has been judged as superseded by the "
                    "build of %s.  Arch-specific == %s" % (
                    distroarchseries.architecturetag,
                    self.binarypackagerelease.title,
                    dominant_build.source_package_release.title,
                    self.binarypackagerelease.architecturespecific))
            # Binary package releases are superseded by the new build,
            # not the new binary package release. This is because
            # there may not *be* a new matching binary package -
            # source packages can change the binaries they build
            # between releases.
            self.supersededby = dominant_build

        debug = getUtility(IPublishingSet).findCorrespondingDDEBPublications(
            [self])
        for dominated in debug:
            dominated.supersede(dominant, logger)

    def changeOverride(self, new_component=None, new_section=None,
                       new_priority=None, new_phased_update_percentage=None,
                       creator=None):
        """See `IBinaryPackagePublishingHistory`."""

        # Check we have been asked to do something
        if (new_component is None and new_section is None
            and new_priority is None and new_phased_update_percentage is None):
            raise AssertionError("changeOverride must be passed a new "
                                 "component, section, priority and/or "
                                 "phased_update_percentage.")

        if self.is_debug:
            raise OverrideError(
                "Cannot override ddeb publications directly; override "
                "the corresponding deb instead.")

        # Check there is a change to make
        if new_component is None:
            new_component = self.component
        elif isinstance(new_component, six.string_types):
            new_component = getUtility(IComponentSet)[new_component]
        if new_section is None:
            new_section = self.section
        elif isinstance(new_section, six.string_types):
            new_section = getUtility(ISectionSet)[new_section]
        if new_priority is None:
            new_priority = self.priority
        elif isinstance(new_priority, six.string_types):
            new_priority = name_priority_map[new_priority]
        if new_phased_update_percentage is None:
            new_phased_update_percentage = self.phased_update_percentage
        elif (new_phased_update_percentage < 0 or
              new_phased_update_percentage > 100):
            raise ValueError(
                "new_phased_update_percentage must be between 0 and 100 "
                "(inclusive).")
        elif new_phased_update_percentage == 100:
            new_phased_update_percentage = None

        if (new_component == self.component and
            new_section == self.section and
            new_priority == self.priority and
            new_phased_update_percentage == self.phased_update_percentage):
            return

        bpr = self.binarypackagerelease

        if new_component != self.component:
            # See if the archive has changed by virtue of the component
            # changing:
            distribution = self.distroarchseries.distroseries.distribution
            new_archive = distribution.getArchiveByComponent(
                new_component.name)
            if new_archive is not None and new_archive != self.archive:
                raise OverrideError(
                    "Overriding component to '%s' failed because it would "
                    "require a new archive." % new_component.name)

        # Refuse to create new publication records that will never be
        # published.
        if not self.archive.canModifySuite(self.distroseries, self.pocket):
            raise OverrideError(
                "Cannot change overrides in suite '%s'" %
                self.distroseries.getSuite(self.pocket))

        # Search for related debug publications, and override them too.
        debugs = getUtility(IPublishingSet).findCorrespondingDDEBPublications(
            [self])
        # We expect only one, but we will override all of them.
        for debug in debugs:
            BinaryPackagePublishingHistory(
                binarypackagename=debug.binarypackagename,
                binarypackagerelease=debug.binarypackagerelease,
                distroarchseries=debug.distroarchseries,
                status=PackagePublishingStatus.PENDING,
                datecreated=UTC_NOW,
                pocket=debug.pocket,
                component=new_component,
                section=new_section,
                priority=new_priority,
                creator=creator,
                archive=debug.archive,
                phased_update_percentage=new_phased_update_percentage)

        # Append the modified package publishing entry
        return BinaryPackagePublishingHistory(
            binarypackagename=bpr.binarypackagename,
            binarypackagerelease=bpr,
            distroarchseries=self.distroarchseries,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=self.pocket,
            component=new_component,
            section=new_section,
            priority=new_priority,
            archive=self.archive,
            creator=creator,
            phased_update_percentage=new_phased_update_percentage)

    def copyTo(self, distroseries, pocket, archive):
        """See `BinaryPackagePublishingHistory`."""
        return getUtility(IPublishingSet).copyBinaries(
            archive, distroseries, pocket, [self])

    def _getDownloadCountClauses(self, start_date=None, end_date=None):
        clauses = [
            BinaryPackageReleaseDownloadCount.archive == self.archive,
            BinaryPackageReleaseDownloadCount.binary_package_release ==
                self.binarypackagerelease,
            ]

        if start_date is not None:
            clauses.append(BinaryPackageReleaseDownloadCount.day >= start_date)
        if end_date is not None:
            clauses.append(BinaryPackageReleaseDownloadCount.day <= end_date)

        return clauses

    def getDownloadCounts(self, start_date=None, end_date=None):
        """See `IBinaryPackagePublishingHistory`."""
        clauses = self._getDownloadCountClauses(start_date, end_date)

        return Store.of(self).using(
            BinaryPackageReleaseDownloadCount,
            LeftJoin(
                Country,
                BinaryPackageReleaseDownloadCount.country_id ==
                    Country.id)).find(
            BinaryPackageReleaseDownloadCount, *clauses).order_by(
                Desc(BinaryPackageReleaseDownloadCount.day), Country.name)

    def getDailyDownloadTotals(self, start_date=None, end_date=None):
        """See `IBinaryPackagePublishingHistory`."""
        clauses = self._getDownloadCountClauses(start_date, end_date)

        results = Store.of(self).find(
            (BinaryPackageReleaseDownloadCount.day,
             Sum(BinaryPackageReleaseDownloadCount.count)),
            *clauses).group_by(
                BinaryPackageReleaseDownloadCount.day)

        def date_to_string(result):
            return (result[0].strftime('%Y-%m-%d'), result[1])

        return dict(date_to_string(result) for result in results)

    def api_requestDeletion(self, removed_by, removal_comment=None):
        """See `IPublishingEdit`."""
        # Special deletion method for the api.  We don't do anything
        # different here (yet).
        self.requestDeletion(removed_by, removal_comment)

    def requestDeletion(self, removed_by, removal_comment=None):
        """See `IPublishing`."""
        if not self.archive.canModifySuite(self.distroseries, self.pocket):
            raise DeletionError(
                "Cannot delete publications from suite '%s'" %
                self.distroseries.getSuite(self.pocket))

        if self.is_debug:
            raise DeletionError(
                "Cannot delete ddeb publications directly; delete the "
                "corresponding deb instead.")

        self.setDeleted(removed_by, removal_comment)

    def binaryFileUrls(self, include_meta=False):
        """See `IBinaryPackagePublishingHistory`."""
        binaries = Store.of(self).find(
            (LibraryFileAlias, LibraryFileContent),
            LibraryFileContent.id == LibraryFileAlias.contentID,
            LibraryFileAlias.id == BinaryPackageFile.libraryfileID,
            BinaryPackageFile.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackageRelease.id == self.binarypackagereleaseID)
        binary_urls = proxied_urls(
            [binary for binary, _ in binaries], self.archive)
        if include_meta:
            meta = [
                (content.filesize, content.sha1, content.sha256)
                for _, content in binaries]
            return [dict(url=url, size=size, sha1=sha1, sha256=sha256)
                for url, (size, sha1, sha256) in zip(binary_urls, meta)]
        return binary_urls


def expand_binary_requests(distroseries, binaries):
    """Architecture-expand a dict of binary publication requests.

    For architecture-independent binaries, a tuple will be returned for each
    enabled architecture in the series.
    For architecture-dependent binaries, a tuple will be returned only for the
    architecture corresponding to the build architecture, if it exists and is
    enabled.

    :param binaries: A dict mapping `BinaryPackageReleases` to tuples of their
        desired overrides.

    :return: The binaries and the architectures in which they should be
        published, as a sequence of (`DistroArchSeries`,
        `BinaryPackageRelease`, (overrides)) tuples.
    """

    archs = list(distroseries.enabled_architectures)
    arch_map = dict((arch.architecturetag, arch) for arch in archs)

    expanded = []
    for bpr, overrides in six.iteritems(binaries):
        if bpr.architecturespecific:
            # Find the DAS in this series corresponding to the original
            # build arch tag. If it does not exist or is disabled, we should
            # not publish.
            target_arch = arch_map.get(bpr.build.arch_tag)
            target_archs = [target_arch] if target_arch is not None else []
        else:
            target_archs = archs
        for target_arch in target_archs:
            expanded.append((target_arch, bpr, overrides))
    return expanded


@implementer(IPublishingSet)
class PublishingSet:
    """Utilities for manipulating publications in batches."""

    def publishBinaries(self, archive, distroseries, pocket, binaries,
                        copied_from_archives=None):
        """See `IPublishingSet`."""
        if copied_from_archives is None:
            copied_from_archives = {}
        # Expand the dict of binaries into a list of tuples including the
        # architecture.
        if distroseries.distribution != archive.distribution:
            raise AssertionError(
                "Series distribution %s doesn't match archive distribution %s."
                % (distroseries.distribution.name, archive.distribution.name))

        expanded = expand_binary_requests(distroseries, binaries)
        if len(expanded) == 0:
            # The binaries are for a disabled DistroArchSeries or for
            # an unsupported architecture.
            return []

        # Find existing publications.
        # We should really be able to just compare BPR.id, but
        # CopyChecker doesn't seem to ensure that there are no
        # conflicting binaries from other sources.
        def make_package_condition(archive, das, bpr):
            return And(
                BinaryPackagePublishingHistory.archiveID == archive.id,
                BinaryPackagePublishingHistory.distroarchseriesID == das.id,
                BinaryPackagePublishingHistory.binarypackagenameID ==
                    bpr.binarypackagenameID,
                Cast(BinaryPackageRelease.version, "text") == bpr.version,
                )

        candidates = (
            make_package_condition(archive, das, bpr)
            for das, bpr, overrides in expanded)
        already_published = IMasterStore(BinaryPackagePublishingHistory).find(
            (BinaryPackagePublishingHistory.distroarchseriesID,
             BinaryPackageRelease.binarypackagenameID,
             BinaryPackageRelease.version),
            BinaryPackagePublishingHistory.pocket == pocket,
            BinaryPackagePublishingHistory.status.is_in(
                active_publishing_status),
            BinaryPackageRelease.id ==
                BinaryPackagePublishingHistory.binarypackagereleaseID,
            Or(*candidates)).config(distinct=True)
        already_published = frozenset(already_published)

        needed = [
            (das, bpr, overrides) for (das, bpr, overrides) in
            expanded if (das.id, bpr.binarypackagenameID, bpr.version)
            not in already_published]
        if not needed:
            return []

        BPPH = BinaryPackagePublishingHistory
        return bulk.create(
            (BPPH.archive, BPPH.copied_from_archive,
             BPPH.distroarchseries, BPPH.pocket,
             BPPH.binarypackagerelease, BPPH.binarypackagename,
             BPPH.component, BPPH.section, BPPH.priority,
             BPPH.phased_update_percentage, BPPH.status, BPPH.datecreated),
            [(archive, copied_from_archives.get(bpr), das, pocket, bpr,
              bpr.binarypackagename,
              get_component(archive, das.distroseries, component),
              section, priority, phased_update_percentage,
              PackagePublishingStatus.PENDING, UTC_NOW)
              for (das, bpr,
                   (component, section, priority,
                    phased_update_percentage)) in needed],
            get_objects=True)

    def copyBinaries(self, archive, distroseries, pocket, bpphs, policy=None,
                     source_override=None):
        """See `IPublishingSet`."""
        from lp.soyuz.adapters.overrides import BinaryOverride
        if distroseries.distribution != archive.distribution:
            raise AssertionError(
                "Series distribution %s doesn't match archive distribution %s."
                % (distroseries.distribution.name, archive.distribution.name))

        if bpphs is None:
            return

        if zope_isinstance(bpphs, list):
            if len(bpphs) == 0:
                return
        else:
            if ISQLObjectResultSet.providedBy(bpphs):
                bpphs = IResultSet(bpphs)
            if bpphs.is_empty():
                return

        if policy is not None:
            bpn_archtag = {}
            ddebs = set()
            for bpph in bpphs:
                # DDEBs just inherit their corresponding DEB's
                # overrides, so don't ask for specific ones.
                if bpph.is_debug:
                    ddebs.add(bpph.binarypackagerelease)
                    continue

                bpn_archtag[(
                    bpph.binarypackagerelease.binarypackagename,
                    bpph.distroarchseries.architecturetag)] = bpph
            with_overrides = {}
            overrides = policy.calculateBinaryOverrides(
                dict(
                    ((bpn, archtag), BinaryOverride(
                        source_override=source_override))
                    for bpn, archtag in bpn_archtag.keys()))
            for (bpn, archtag), override in overrides.items():
                bpph = bpn_archtag[(bpn, archtag)]
                new_component = override.component or bpph.component
                new_section = override.section or bpph.section
                new_priority = override.priority or bpph.priority
                # No "or bpph.phased_update_percentage" here; if the
                # override doesn't specify one then we leave it at None
                # (a.k.a. 100% of users).
                new_phased_update_percentage = (
                    override.phased_update_percentage)
                calculated = (
                    new_component, new_section, new_priority,
                    new_phased_update_percentage)
                with_overrides[bpph.binarypackagerelease] = calculated

                # If there is a corresponding DDEB then give it our
                # overrides too. It should always be part of the copy
                # already.
                maybe_ddeb = bpph.binarypackagerelease.debug_package
                if maybe_ddeb is not None:
                    assert maybe_ddeb in ddebs
                    ddebs.remove(maybe_ddeb)
                    with_overrides[maybe_ddeb] = calculated
        else:
            with_overrides = dict(
                (bpph.binarypackagerelease, (bpph.component, bpph.section,
                 bpph.priority, None)) for bpph in bpphs)
        if not with_overrides:
            return list()
        copied_from_archives = {
            bpph.binarypackagerelease: bpph.archive for bpph in bpphs}
        return self.publishBinaries(
            archive, distroseries, pocket, with_overrides,
            copied_from_archives)

    def newSourcePublication(self, archive, sourcepackagerelease,
                             distroseries, component, section, pocket,
                             ancestor=None, create_dsd_job=True,
                             copied_from_archive=None,
                             creator=None, sponsor=None, packageupload=None):
        """See `IPublishingSet`."""
        # Circular import.
        from lp.registry.model.distributionsourcepackage import (
            DistributionSourcePackage,
            )

        if distroseries.distribution != archive.distribution:
            raise AssertionError(
                "Series distribution %s doesn't match archive distribution %s."
                % (distroseries.distribution.name, archive.distribution.name))

        pub = SourcePackagePublishingHistory(
            distroseries=distroseries,
            pocket=pocket,
            copied_from_archive=copied_from_archive,
            archive=archive,
            sourcepackagename=sourcepackagerelease.sourcepackagename,
            sourcepackagerelease=sourcepackagerelease,
            component=get_component(archive, distroseries, component),
            section=section,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            ancestor=ancestor,
            creator=creator,
            sponsor=sponsor,
            packageupload=packageupload)
        DistributionSourcePackage.ensure(pub)

        if create_dsd_job and archive == distroseries.main_archive:
            dsd_job_source = getUtility(IDistroSeriesDifferenceJobSource)
            dsd_job_source.createForPackagePublication(
                distroseries, sourcepackagerelease.sourcepackagename, pocket)
        Store.of(sourcepackagerelease).flush()
        del get_property_cache(sourcepackagerelease).published_archives

        return pub

    def getBuildsForSourceIds(self, source_publication_ids, archive=None,
                              build_states=None):
        """See `IPublishingSet`."""
        # If an archive was passed in as a parameter, add an extra expression
        # to filter by archive:
        extra_exprs = []
        if archive is not None:
            extra_exprs.append(
                SourcePackagePublishingHistory.archive == archive)

        # If an optional list of build states was passed in as a parameter,
        # ensure that the result is limited to builds in those states.
        if build_states is not None:
            extra_exprs.append(BinaryPackageBuild.status.is_in(build_states))

        store = IStore(SourcePackagePublishingHistory)

        # We'll be looking for builds in the same distroseries as the
        # SPPH for the same release.
        builds_for_distroseries_expr = (
            SourcePackagePublishingHistory.distroseriesID ==
                BinaryPackageBuild.distro_series_id,
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                BinaryPackageBuild.source_package_release_id,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids),
            DistroArchSeries.id == BinaryPackageBuild.distro_arch_series_id,
            )

        # First, we'll find the builds that were built in the same
        # archive context as the published sources.
        builds_in_same_archive = store.find(
            BinaryPackageBuild,
            builds_for_distroseries_expr,
            (SourcePackagePublishingHistory.archiveID ==
                BinaryPackageBuild.archive_id),
            *extra_exprs)

        # Next get all the builds that have a binary published in the
        # same archive... even though the build was not built in
        # the same context archive.
        builds_copied_into_archive = store.find(
            BinaryPackageBuild,
            builds_for_distroseries_expr,
            (SourcePackagePublishingHistory.archiveID !=
                BinaryPackageBuild.archive_id),
            BinaryPackagePublishingHistory.archive ==
                SourcePackagePublishingHistory.archiveID,
            BinaryPackagePublishingHistory.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackageRelease.build == BinaryPackageBuild.id,
            *extra_exprs)

        builds_union = builds_copied_into_archive.union(
            builds_in_same_archive).config(distinct=True)

        # Now that we have a result_set of all the builds, we'll use it
        # as a subquery to get the required publishing and arch to do
        # the ordering. We do this in this round-about way because we
        # can't sort on SourcePackagePublishingHistory.id after the
        # union. See bug 443353 for details.
        find_spec = (
            SourcePackagePublishingHistory,
            BinaryPackageBuild,
            DistroArchSeries,
            )

        # Storm doesn't let us do builds_union.values('id') -
        # ('Union' object has no attribute 'columns'). So instead
        # we have to instantiate the objects just to get the id.
        build_ids = [build.id for build in builds_union]

        result_set = store.find(
            find_spec, builds_for_distroseries_expr,
            BinaryPackageBuild.id.is_in(build_ids))

        return result_set.order_by(
            SourcePackagePublishingHistory.id,
            DistroArchSeries.architecturetag)

    def getByIdAndArchive(self, id, archive, source=True):
        """See `IPublishingSet`."""
        if source:
            baseclass = SourcePackagePublishingHistory
        else:
            baseclass = BinaryPackagePublishingHistory
        return Store.of(archive).find(
            baseclass,
            baseclass.id == id,
            baseclass.archive == archive.id).one()

    def _extractIDs(self, one_or_more_source_publications):
        """Return a list of database IDs for the given list or single object.

        :param one_or_more_source_publications: an single object or a list of
            `ISourcePackagePublishingHistory` objects.

        :return: a list of database IDs corresponding to the give set of
            objects.
        """
        try:
            source_publications = tuple(one_or_more_source_publications)
        except TypeError:
            source_publications = (one_or_more_source_publications,)

        return [source_publication.id
                for source_publication in source_publications]

    def getBuildsForSources(self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        return self.getBuildsForSourceIds(source_publication_ids)

    def _getSourceBinaryJoinForSources(self, source_publication_ids,
        active_binaries_only=True):
        """Return the join linking sources with binaries."""
        join = [
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                BinaryPackageBuild.source_package_release_id,
            BinaryPackageRelease.build == BinaryPackageBuild.id,
            BinaryPackageRelease.binarypackagenameID ==
                BinaryPackageName.id,
            SourcePackagePublishingHistory.distroseriesID ==
                DistroArchSeries.distroseriesID,
            BinaryPackagePublishingHistory.distroarchseriesID ==
                DistroArchSeries.id,
            BinaryPackagePublishingHistory.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.pocket ==
               SourcePackagePublishingHistory.pocket,
            BinaryPackagePublishingHistory.archiveID ==
               SourcePackagePublishingHistory.archiveID,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids)]

        # If the call-site requested to join only on binaries published
        # with an active publishing status then we need to further restrict
        # the join.
        if active_binaries_only:
            join.append(BinaryPackagePublishingHistory.status.is_in(
                active_publishing_status))

        return join

    def getUnpublishedBuildsForSources(self,
                                       one_or_more_source_publications,
                                       build_states=None):
        """See `IPublishingSet`."""
        # The default build state that we'll search for is FULLYBUILT
        if build_states is None:
            build_states = [BuildStatus.FULLYBUILT]

        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        store = IStore(SourcePackagePublishingHistory)
        published_builds = store.find(
            (SourcePackagePublishingHistory, BinaryPackageBuild,
                DistroArchSeries),
            self._getSourceBinaryJoinForSources(
                source_publication_ids, active_binaries_only=False),
            BinaryPackagePublishingHistory.datepublished != None,
            BinaryPackageBuild.status.is_in(build_states))

        published_builds.order_by(
            SourcePackagePublishingHistory.id,
            DistroArchSeries.architecturetag)

        # Now to return all the unpublished builds, we use the difference
        # of all builds minus the published ones.
        unpublished_builds = self.getBuildsForSourceIds(
            source_publication_ids,
            build_states=build_states).difference(published_builds)

        return unpublished_builds

    def getBinaryFilesForSources(self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        store = IStore(SourcePackagePublishingHistory)
        binary_result = store.find(
            (SourcePackagePublishingHistory, LibraryFileAlias,
             LibraryFileContent),
            LibraryFileContent.id == LibraryFileAlias.contentID,
            LibraryFileAlias.id == BinaryPackageFile.libraryfileID,
            BinaryPackageFile.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackageRelease.buildID == BinaryPackageBuild.id,
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                BinaryPackageBuild.source_package_release_id,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.archiveID ==
                SourcePackagePublishingHistory.archiveID,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids))

        return binary_result.order_by(LibraryFileAlias.id)

    def getFilesForSources(self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        store = IStore(SourcePackagePublishingHistory)
        source_result = store.find(
            (SourcePackagePublishingHistory, LibraryFileAlias,
             LibraryFileContent),
            LibraryFileContent.id == LibraryFileAlias.contentID,
            LibraryFileAlias.id == SourcePackageReleaseFile.libraryfileID,
            SourcePackageReleaseFile.sourcepackagerelease ==
                SourcePackagePublishingHistory.sourcepackagereleaseID,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids))

        binary_result = self.getBinaryFilesForSources(
            one_or_more_source_publications)

        result_set = source_result.union(
            binary_result.config(distinct=True))

        return result_set

    def getBinaryPublicationsForSources(self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        result_set = IStore(SourcePackagePublishingHistory).find(
            (SourcePackagePublishingHistory, BinaryPackagePublishingHistory,
             BinaryPackageRelease, BinaryPackageName, DistroArchSeries),
            self._getSourceBinaryJoinForSources(source_publication_ids))

        result_set.order_by(
            SourcePackagePublishingHistory.id,
            BinaryPackageName.name,
            DistroArchSeries.architecturetag,
            Desc(BinaryPackagePublishingHistory.id))

        return result_set

    def getBuiltPackagesSummaryForSourcePublication(self, source_publication):
        """See `IPublishingSet`."""
        result_set = IStore(BinaryPackageName).find(
            (BinaryPackageName.name, BinaryPackageRelease.summary,
             DistroArchSeries.architecturetag,
             BinaryPackagePublishingHistory.id),
            self._getSourceBinaryJoinForSources([source_publication.id]))
        result_set.config(distinct=(BinaryPackageName.name,))
        result_set.order_by(
            BinaryPackageName.name,
            DistroArchSeries.architecturetag,
            Desc(BinaryPackagePublishingHistory.id))
        return [
            {"binarypackagename": name, "summary": summary}
            for name, summary, _, _ in result_set]

    def getActiveArchSpecificPublications(self, sourcepackagerelease, archive,
                                          distroseries, pocket):
        """See `IPublishingSet`."""
        return IStore(BinaryPackagePublishingHistory).find(
            BinaryPackagePublishingHistory,
            BinaryPackageBuild.source_package_release_id ==
                sourcepackagerelease.id,
            BinaryPackageRelease.build == BinaryPackageBuild.id,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.archiveID == archive.id,
            BinaryPackagePublishingHistory.distroarchseriesID ==
                DistroArchSeries.id,
            DistroArchSeries.distroseriesID == distroseries.id,
            BinaryPackagePublishingHistory.pocket == pocket,
            BinaryPackagePublishingHistory.status.is_in(
                active_publishing_status),
            BinaryPackageRelease.architecturespecific == True)

    def getChangesFilesForSources(self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        # Avoid circular imports.
        from lp.soyuz.model.queue import PackageUpload, PackageUploadSource

        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        result_set = IStore(SourcePackagePublishingHistory).find(
            (SourcePackagePublishingHistory, PackageUpload,
             SourcePackageRelease, LibraryFileAlias, LibraryFileContent),
            LibraryFileContent.id == LibraryFileAlias.contentID,
            LibraryFileAlias.id == PackageUpload.changes_file_id,
            PackageUpload.id == PackageUploadSource.packageuploadID,
            PackageUpload.status == PackageUploadStatus.DONE,
            PackageUpload.distroseriesID ==
                SourcePackageRelease.upload_distroseriesID,
            PackageUpload.archiveID ==
                SourcePackageRelease.upload_archiveID,
            PackageUploadSource.sourcepackagereleaseID ==
                SourcePackageRelease.id,
            SourcePackageRelease.id ==
                SourcePackagePublishingHistory.sourcepackagereleaseID,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids))

        result_set.order_by(SourcePackagePublishingHistory.id)
        return result_set

    def getChangesFileLFA(self, spr):
        """See `IPublishingSet`."""
        # Avoid circular imports.
        from lp.soyuz.model.queue import PackageUpload, PackageUploadSource

        return IStore(SourcePackagePublishingHistory).find(
            LibraryFileAlias,
            LibraryFileAlias.id == PackageUpload.changes_file_id,
            PackageUpload.status == PackageUploadStatus.DONE,
            PackageUpload.distroseriesID == spr.upload_distroseries.id,
            PackageUpload.archiveID == spr.upload_archive.id,
            PackageUpload.id == PackageUploadSource.packageuploadID,
            PackageUploadSource.sourcepackagereleaseID == spr.id).one()

    def getBuildStatusSummariesForSourceIdsAndArchive(self, source_ids,
        archive):
        """See `IPublishingSet`."""
        # source_ids can be None or an empty sequence.
        if not source_ids:
            return {}

        store = IStore(SourcePackagePublishingHistory)
        # Find relevant builds while also getting PackageBuilds and
        # BuildFarmJobs into the cache. They're used later.
        build_info = list(
            self.getBuildsForSourceIds(source_ids, archive=archive))
        source_pubs = set()
        found_source_ids = set()
        for row in build_info:
            source_pubs.add(row[0])
            found_source_ids.add(row[0].id)
        pubs_without_builds = set(source_ids) - found_source_ids
        if pubs_without_builds:
            # Add in source pubs for which no builds were found: we may in
            # future want to make this a LEFT OUTER JOIN in
            # getBuildsForSourceIds but to avoid destabilising other code
            # paths while we fix performance, it is just done as a single
            # separate query for now.
            source_pubs.update(store.find(
                SourcePackagePublishingHistory,
                SourcePackagePublishingHistory.id.is_in(pubs_without_builds),
                SourcePackagePublishingHistory.archive == archive))
        # For each source_pub found, provide an aggregate summary of its
        # builds.
        binarypackages = getUtility(IBinaryPackageBuildSet)
        source_build_statuses = {}
        need_unpublished = set()
        for source_pub in source_pubs:
            source_builds = [
                build for build in build_info if build[0].id == source_pub.id]
            builds = SourcePackagePublishingHistory._convertBuilds(
                source_builds)
            summary = binarypackages.getStatusSummaryForBuilds(builds)
            # Thank you, Zope, for security wrapping an abstract data
            # structure.
            summary = removeSecurityProxy(summary)
            summary['date_published'] = source_pub.datepublished
            summary['source_package_name'] = source_pub.source_package_name
            source_build_statuses[source_pub.id] = summary

            # If:
            #   1. the SPPH is in an active publishing state, and
            #   2. all the builds are fully-built, and
            #   3. the SPPH is not being published in a rebuild/copy
            #      archive (in which case the binaries are not published)
            #   4. There are unpublished builds
            # Then we augment the result with FULLYBUILT_PENDING and
            # attach the unpublished builds.
            if (source_pub.status in active_publishing_status and
                    summary['status'] == BuildSetStatus.FULLYBUILT and
                    not source_pub.archive.is_copy):
                need_unpublished.add(source_pub)

        if need_unpublished:
            unpublished = list(self.getUnpublishedBuildsForSources(
                need_unpublished))
            unpublished_per_source = defaultdict(list)
            for source_pub, build, _ in unpublished:
                unpublished_per_source[source_pub].append(build)
            for source_pub, builds in unpublished_per_source.items():
                summary = {
                    'status': BuildSetStatus.FULLYBUILT_PENDING,
                    'builds': builds,
                    'date_published': source_pub.datepublished,
                    'source_package_name': source_pub.source_package_name,
                }
                source_build_statuses[source_pub.id] = summary

        return source_build_statuses

    def getBuildStatusSummaryForSourcePublication(self, source_publication):
        """See `ISourcePackagePublishingHistory`.getStatusSummaryForBuilds.

        This is provided here so it can be used by both the SPPH as well
        as our delegate class ArchiveSourcePublication, which implements
        the same interface but uses cached results for builds and binaries
        used in the calculation.
        """
        source_id = source_publication.id
        return self.getBuildStatusSummariesForSourceIdsAndArchive([source_id],
            source_publication.archive)[source_id]

    def setMultipleDeleted(self, publication_class, ids, removed_by,
                           removal_comment=None):
        """Mark multiple publication records as deleted."""
        ids = list(ids)
        if len(ids) == 0:
            return

        permitted_classes = [
            BinaryPackagePublishingHistory,
            SourcePackagePublishingHistory,
            ]
        assert publication_class in permitted_classes, "Deleting wrong type."

        if removed_by is None:
            removed_by_id = None
        else:
            removed_by_id = removed_by.id

        affected_pubs = IMasterStore(publication_class).find(
            publication_class, publication_class.id.is_in(ids))
        affected_pubs.set(
            status=PackagePublishingStatus.DELETED,
            datesuperseded=UTC_NOW,
            removed_byID=removed_by_id,
            removal_comment=removal_comment)

        # Find and mark any related debug packages.
        if publication_class == BinaryPackagePublishingHistory:
            debug_ids = [
                pub.id for pub in self.findCorrespondingDDEBPublications(
                    affected_pubs)]
            IMasterStore(publication_class).find(
                BinaryPackagePublishingHistory,
                BinaryPackagePublishingHistory.id.is_in(debug_ids)).set(
                    status=PackagePublishingStatus.DELETED,
                    datesuperseded=UTC_NOW,
                    removed_byID=removed_by_id,
                    removal_comment=removal_comment)

    def findCorrespondingDDEBPublications(self, pubs):
        """See `IPublishingSet`."""
        ids = [pub.id for pub in pubs]
        deb_bpph = ClassAlias(BinaryPackagePublishingHistory)
        debug_bpph = BinaryPackagePublishingHistory
        origin = [
            deb_bpph,
            Join(
                BinaryPackageRelease,
                deb_bpph.binarypackagereleaseID ==
                    BinaryPackageRelease.id),
            Join(
                debug_bpph,
                debug_bpph.binarypackagereleaseID ==
                    BinaryPackageRelease.debug_packageID)]
        return IMasterStore(debug_bpph).using(*origin).find(
            debug_bpph,
            deb_bpph.id.is_in(ids),
            debug_bpph.status.is_in(active_publishing_status),
            deb_bpph.archiveID == debug_bpph.archiveID,
            deb_bpph.distroarchseriesID == debug_bpph.distroarchseriesID,
            deb_bpph.pocket == debug_bpph.pocket,
            deb_bpph.componentID == debug_bpph.componentID,
            deb_bpph.sectionID == debug_bpph.sectionID,
            deb_bpph.priority == debug_bpph.priority,
            Not(IsDistinctFrom(
                deb_bpph.phased_update_percentage,
                debug_bpph.phased_update_percentage)))

    def requestDeletion(self, pubs, removed_by, removal_comment=None):
        """See `IPublishingSet`."""
        pubs = list(pubs)
        sources = [
            pub for pub in pubs
            if ISourcePackagePublishingHistory.providedBy(pub)]
        binaries = [
            pub for pub in pubs
            if IBinaryPackagePublishingHistory.providedBy(pub)]
        if not sources and not binaries:
            return
        assert len(sources) + len(binaries) == len(pubs)

        locations = set(
            (pub.archive, pub.distroseries, pub.pocket) for pub in pubs)
        for archive, distroseries, pocket in locations:
            if not archive.canModifySuite(distroseries, pocket):
                raise DeletionError(
                    "Cannot delete publications from suite '%s'" %
                    distroseries.getSuite(pocket))

        spph_ids = [spph.id for spph in sources]
        self.setMultipleDeleted(
            SourcePackagePublishingHistory, spph_ids, removed_by,
            removal_comment=removal_comment)

        getUtility(IDistroSeriesDifferenceJobSource).createForSPPHs(sources)

        # Append the sources' related binaries to our condemned list,
        # and mark them all deleted.
        bpph_ids = [bpph.id for bpph in binaries]
        bpph_ids.extend(self.getBinaryPublicationsForSources(sources).values(
            BinaryPackagePublishingHistory.id))
        if len(bpph_ids) > 0:
            self.setMultipleDeleted(
                BinaryPackagePublishingHistory, bpph_ids, removed_by,
                removal_comment=removal_comment)


def get_current_source_releases(context_sourcepackagenames, archive_ids_func,
                                package_clause_func, extra_clauses, key_col):
    """Get the current source package releases in a context.

    You probably don't want to use this directly; try
    (Distribution|DistroSeries)(Set)?.getCurrentSourceReleases instead.
    """
    # Builds one query for all the distro_source_packagenames.
    # This may need tuning: its possible that grouping by the common
    # archives may yield better efficiency: the current code is
    # just a direct push-down of the previous in-python lookup to SQL.
    series_clauses = []
    for context, package_names in context_sourcepackagenames.items():
        clause = And(
            SourcePackagePublishingHistory.sourcepackagenameID.is_in(
                map(attrgetter('id'), package_names)),
            SourcePackagePublishingHistory.archiveID.is_in(
                archive_ids_func(context)),
            package_clause_func(context),
            )
        series_clauses.append(clause)
    if not len(series_clauses):
        return {}

    releases = IStore(SourcePackageRelease).find(
        (SourcePackageRelease, key_col),
        SourcePackagePublishingHistory.sourcepackagereleaseID
            == SourcePackageRelease.id,
        SourcePackagePublishingHistory.status.is_in(
            active_publishing_status),
        Or(*series_clauses),
        *extra_clauses).config(
            distinct=(
                SourcePackageRelease.sourcepackagenameID,
                key_col)
        ).order_by(
            SourcePackageRelease.sourcepackagenameID,
            key_col,
            Desc(SourcePackagePublishingHistory.id))
    return releases
