# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Package copying utilities."""

__metaclass__ = type

__all__ = [
    'CopyChecker',
    'check_copy_permissions',
    'do_copy',
    '_do_direct_copy',
    'update_files_privacy',
    ]

import apt_pkg
from lazr.delegates import delegate_to
from zope.component import (
    getAdapter,
    getUtility,
    )
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.security import IAuthorization
from lp.registry.interfaces.role import IPersonRoles
from lp.registry.model.person import Person
from lp.services.database.bulk import load_related
from lp.soyuz.adapters.overrides import SourceOverride
from lp.soyuz.enums import SourcePackageFormat
from lp.soyuz.interfaces.archive import CannotCopy
from lp.soyuz.interfaces.binarypackagebuild import BuildSetStatus
from lp.soyuz.interfaces.publishing import (
    active_publishing_status,
    IBinaryPackagePublishingHistory,
    IPublishingSet,
    ISourcePackagePublishingHistory,
    )
from lp.soyuz.interfaces.queue import IPackageUploadCustom
from lp.soyuz.mail.packageupload import PackageUploadMailer
from lp.soyuz.model.processacceptedbugsjob import (
    close_bugs_for_sourcepublication,
    )
from lp.soyuz.scripts.custom_uploads_copier import CustomUploadsCopier


# XXX cprov 2009-06-12: this function should be incorporated in
# IPublishing.
def update_files_privacy(pub_record):
    """Update file privacy according to the publishing destination

    :param pub_record: One of a SourcePackagePublishingHistory or
        BinaryPackagePublishingHistory record.

    :return: a list of changed `LibraryFileAlias` objects.
    """
    package_files = []
    archive = None
    if ISourcePackagePublishingHistory.providedBy(pub_record):
        archive = pub_record.archive
        # Unrestrict the package files files if necessary.
        sourcepackagerelease = pub_record.sourcepackagerelease
        package_files.extend(
            [(source_file, 'libraryfile')
             for source_file in sourcepackagerelease.files])
        # Unrestrict the package diff files if necessary.
        package_files.extend(
            [(diff, 'diff_content')
             for diff in sourcepackagerelease.package_diffs])
        # Unrestrict the source upload changesfile if necessary.
        package_upload = sourcepackagerelease.package_upload
        package_files.append((package_upload, 'changesfile'))
        package_files.append((sourcepackagerelease, 'changelog'))
    elif IBinaryPackagePublishingHistory.providedBy(pub_record):
        archive = pub_record.archive
        # Unrestrict the binary files if necessary.
        binarypackagerelease = pub_record.binarypackagerelease
        package_files.extend(
            [(binary_file, 'libraryfile')
             for binary_file in binarypackagerelease.files])
        # Unrestrict the upload changesfile file as necessary.
        build = binarypackagerelease.build
        package_upload = build.package_upload
        package_files.append((package_upload, 'changesfile'))
        # Unrestrict the buildlog file as necessary.
        package_files.append((build, 'log'))
    elif IPackageUploadCustom.providedBy(pub_record):
        # Unrestrict the custom files included
        package_files.append((pub_record, 'libraryfilealias'))
        # And set archive to the right attribute for PUCs
        archive = pub_record.packageupload.archive
    else:
        raise AssertionError(
            "pub_record is not one of SourcePackagePublishingHistory, "
            "BinaryPackagePublishingHistory or PackageUploadCustom.")

    changed_files = []
    for obj, attr_name in package_files:
        lfa = getattr(obj, attr_name, None)
        # Only unrestrict restricted files published in public archives,
        # not the opposite. We don't have a use-case for privatizing
        # files yet.
        if (lfa is None or
            lfa.restricted == archive.private or
            lfa.restricted == False):
            continue
        # LibraryFileAlias.restricted is normally read-only, but we have a
        # good excuse here.
        removeSecurityProxy(lfa).restricted = archive.private
        changed_files.append(lfa)

    return changed_files


@delegate_to(ISourcePackagePublishingHistory)
class CheckedCopy:
    """Representation of a copy that was checked and approved.

    Decorates `ISourcePackagePublishingHistory`, tweaking
    `getStatusSummaryForBuilds` to return `BuildSetStatus.NEEDSBUILD`
    for source-only copies.
    """

    def __init__(self, context, include_binaries):
        self.context = context
        self.include_binaries = include_binaries

    def getStatusSummaryForBuilds(self):
        """Always `BuildSetStatus.NEEDSBUILD` for source-only copies."""
        if self.include_binaries:
            return self.context.getStatusSummaryForBuilds()
        else:
            return {'status': BuildSetStatus.NEEDSBUILD}


def check_copy_permissions(person, archive, series, pocket, sources,
                           move=False):
    """Check that `person` has permission to copy a package.

    :param person: User attempting the upload.
    :param archive: Destination `Archive`.
    :param series: Destination `DistroSeries`.
    :param pocket: Destination `Pocket`.
    :param sources: Sequence of `SourcePackagePublishingHistory`s for the
        packages to be copied.
    :param move: If True, also check whether `person` has permission to
        delete the sources.
    :raises CannotCopy: If the copy is not allowed.
    """
    # Circular import.
    from lp.soyuz.model.archive import Archive
    from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease

    if person is None:
        raise CannotCopy("Cannot check copy permissions (no requester).")

    if len(sources) > 1:
        # Bulk-load the data we'll need from each source publication.
        load_related(SourcePackageRelease, sources, ["sourcepackagereleaseID"])
        if move:
            # Bulk-load at least some of the data we'll need for permission
            # checks on each source archive.  Not all of this is currently
            # preloadable.
            archives = load_related(Archive, sources, ["archiveID"])
            load_related(Person, archives, ["ownerID"])

    # If there is a requester, check that they have upload permission into
    # the destination (archive, component, pocket). This check is done
    # here rather than in the security adapter because it requires more
    # info than is available in the security adapter.
    for source in sources:
        dest_series = series or source.distroseries
        spn = source.sourcepackagerelease.sourcepackagename
        policy = archive.getOverridePolicy(dest_series, pocket)
        override = policy.calculateSourceOverrides(
            {spn: SourceOverride(component=source.component)})[spn]

        # Is the destination pocket open at all?
        reason = archive.checkUploadToPocket(
            dest_series, pocket, person=person)
        if reason is not None:
            raise CannotCopy(reason)

        # If the package exists in the target, make sure the person has
        # upload permission for its component. Otherwise, any upload
        # permission on this archive will do.
        reason = archive.verifyUpload(
            person, spn, override.component, dest_series,
            strict_component=(override.new == False), pocket=pocket)
        if reason is not None:
            # Queue admins are allowed to copy even if they can't upload.
            if not archive.canAdministerQueue(
                person, override.component, pocket, dest_series):
                raise CannotCopy(reason)

    if move:
        roles = IPersonRoles(person)
        for source_archive in set(source.archive for source in sources):
            # XXX cjwatson 2019-10-09: Checking the archive rather than the
            # SPPH duplicates security adapter logic, which is unfortunate;
            # but too much of the logic required to use
            # DelegatedAuthorization-based adapters such as the one used for
            # launchpad.Edit on SPPH lives in
            # lp.services.webapp.authorization and is hard to use without a
            # full Zope interaction.
            source_archive_authz = getAdapter(
                source_archive, IAuthorization, "launchpad.Append")
            if not source_archive_authz.checkAuthenticated(roles):
                raise CannotCopy(
                    "%s is not permitted to delete publications from %s." %
                    (person.display_name, source_archive.displayname))
        for source in sources:
            if not source.archive.canModifySuite(
                    source.distroseries, source.pocket):
                raise CannotCopy(
                    "Cannot delete publications from suite '%s'" %
                    source.distroseries.getSuite(source.pocket))


class CopyChecker:
    """Check copy candiates.

    Allows the checker function to identify conflicting copy candidates
    within the copying batch.
    """
    def __init__(self, archive, include_binaries, strict_binaries=True,
                 unembargo=False):
        """Initialize a copy checker.

        :param archive: the target `IArchive`.
        :param include_binaries: controls whether or not the published
            binaries for each given source should be also copied along
            with the source.
        :param strict_binaries: If 'include_binaries' is True then setting
            this to True will make the copy fail if binaries cannot be also
            copied.
        :param unembargo: If True, allow copying from a private archive to a
            public archive.
        """
        self.archive = archive
        self.include_binaries = include_binaries
        self.strict_binaries = strict_binaries
        self.unembargo = unembargo
        self._inventory = {}

    def _getInventoryKey(self, candidate):
        """Return a key representing the copy candidate in the inventory.

        :param candidate: a `ISourcePackagePublishingHistory` copy candidate.
        :return: a tuple with the source (name, version) strings.
        """
        return (
            candidate.source_package_name, candidate.source_package_version)

    def addCopy(self, source):
        """Store a copy in the inventory as a `CheckedCopy` instance."""
        inventory_key = self._getInventoryKey(source)
        checked_copy = CheckedCopy(source, self.include_binaries)
        candidates = self._inventory.setdefault(inventory_key, [])
        candidates.append(checked_copy)

    def getCheckedCopies(self):
        """Return a list of copies allowed to be performed."""
        for copies in self._inventory.values():
            for copy in copies:
                yield copy

    def getConflicts(self, candidate):
        """Conflicting `CheckedCopy` objects in the inventory.

        :param candidate: a `ISourcePackagePublishingHistory` copy candidate.
        :return: a list of conflicting copies in the inventory, in case
            of non-conflicting candidates an empty list is returned.
        """
        inventory_key = self._getInventoryKey(candidate)
        return self._inventory.get(inventory_key, [])

    def _checkArchiveConflicts(self, source, series):
        """Check for possible conflicts in the destination archive.

        Check if there is a source with the same name and version published
        in the destination archive or in the inventory of copies already
        approved. If it exists (regardless of the series and pocket) and
        it has built or will build binaries, do not allow the copy without
        binaries.

        This is because the copied source will rebuild binaries that
        conflict with existing ones.

        Even when the binaries are included, they are checked for conflict.

        :param source: copy candidate, `ISourcePackagePublishingHistory`.
        :param series: destination `IDistroSeries`.

        :raise CannotCopy: when a copy is not allowed to be performed
            containing the reason of the error.
        """
        destination_archive_conflicts = self.archive.getPublishedSources(
            name=source.sourcepackagerelease.name,
            version=source.sourcepackagerelease.version,
            exact_match=True)

        inventory_conflicts = self.getConflicts(source)

        # If there are no conflicts with the same version, we can skip the
        # rest of the checks, but we still want to check conflicting files
        if (destination_archive_conflicts.is_empty() and
            len(inventory_conflicts) == 0):
            self._checkConflictingFiles(source)
            return

        # Cache the conflicting publications because they will be iterated
        # more than once.
        destination_archive_conflicts = list(destination_archive_conflicts)
        destination_archive_conflicts.extend(inventory_conflicts)

        # Identify published binaries and incomplete builds or unpublished
        # binaries from archive conflicts. Either will deny source-only
        # copies, since a rebuild will result in binaries that cannot be
        # published in the archive because they will conflict with the
        # existent ones.
        published_binaries = set()
        for candidate in destination_archive_conflicts:
            # If the candidate refers to a different sourcepackagerelease
            # with the same name and version there is a high chance that
            # they have conflicting files that cannot be published in the
            # repository pool. So, we deny the copy until the existing
            # source gets deleted (and removed from the archive).
            if (source.sourcepackagerelease.id !=
                candidate.sourcepackagerelease.id):
                raise CannotCopy(
                    'a different source with the same version is published '
                    'in the destination archive')

            # If the conflicting candidate (which we already know refer to
            # the same sourcepackagerelease) was found in the copy
            # destination series we don't have to check its building status
            # if binaries are included. It's not going to change in terms of
            # new builds and the resulting binaries will match. See more
            # details in `ISourcePackageRelease.getBuildsByArch`.
            if (candidate.distroseries.id == series.id and
                self.archive.id == source.archive.id and
                self.include_binaries):
                continue

            # Conflicting candidates pending build or building in a different
            # series are a blocker for the copy. The copied source will
            # certainly produce conflicting binaries.
            build_summary = candidate.getStatusSummaryForBuilds()
            building_states = (
                BuildSetStatus.NEEDSBUILD,
                BuildSetStatus.BUILDING,
                )
            if build_summary['status'] in building_states:
                raise CannotCopy(
                    "same version already building in the destination "
                    "archive for %s" % candidate.distroseries.displayname)

            # If the set of built binaries does not match the set of published
            # ones the copy should be denied and the user should wait for the
            # next publishing cycle to happen before copying the package.
            # The copy is only allowed when all built binaries are published,
            # this way there is no chance of a conflict.
            if build_summary['status'] == BuildSetStatus.FULLYBUILT_PENDING:
                raise CannotCopy(
                    "same version has unpublished binaries in the "
                    "destination archive for %s, please wait for them to be "
                    "published before copying" %
                    candidate.distroseries.displayname)

            # Update published binaries inventory for the conflicting
            # candidates.
            archive_binaries = set(
                pub_binary.binarypackagerelease.id
                for pub_binary in candidate.getBuiltBinaries())
            published_binaries.update(archive_binaries)

        if not self.include_binaries:
            if len(published_binaries) > 0:
                raise CannotCopy(
                    "same version already has published binaries in the "
                    "destination archive")
        else:
            # Since DEB files are compressed with 'ar' (encoding the creation
            # timestamp) and serially built by our infrastructure, it's
            # correct to assume that the set of BinaryPackageReleases being
            # copied can only be a superset of the set of
            # BinaryPackageReleases published in the destination archive.
            copied_binaries = set(
                pub.binarypackagerelease.id
                for pub in source.getBuiltBinaries())
            if not copied_binaries.issuperset(published_binaries):
                raise CannotCopy(
                    "binaries conflicting with the existing ones")
        self._checkConflictingFiles(source)

    def _checkConflictingFiles(self, source):
        # If both the source and destination archive are the same, we don't
        # need to perform this test, since that guarantees the filenames
        # do not conflict.
        if source.archive.id == self.archive.id:
            return None
        source_files = [
            sprf.libraryfile.filename for sprf in
            source.sourcepackagerelease.files]
        destination_sha1s = self.archive.getFilesAndSha1s(source_files)
        for lf in source.sourcepackagerelease.files:
            if lf.libraryfile.filename in destination_sha1s:
                sha1 = lf.libraryfile.content.sha1
                if sha1 != destination_sha1s[lf.libraryfile.filename]:
                    raise CannotCopy(
                        "%s already exists in destination archive with "
                        "different contents." % lf.libraryfile.filename)

    def checkCopy(self, source, series, pocket, person=None,
                  check_permissions=True, move=False):
        """Check if the source can be copied to the given location.

        Check possible conflicting publications in the destination archive.
        See `_checkArchiveConflicts()`.

        Also checks if the version of the source being copied is equal or
        higher than any version of the same source present in the
        destination suite (series + pocket).

        If person is not None, check that this person has upload rights to
        the destination (archive, component, pocket).

        :param source: copy candidate, `ISourcePackagePublishingHistory`.
        :param series: destination `IDistroSeries`.
        :param pocket: destination `PackagePublishingPocket`.
        :param person: requester `IPerson`.
        :param check_permissions: boolean indicating whether or not the
            requester's permissions to copy should be checked.
        :param move: if True, also check whether `person` has permission to
            delete the source.

        :raise CannotCopy when a copy is not allowed to be performed
            containing the reason of the error.
        """
        if check_permissions:
            check_copy_permissions(
                person, self.archive, series, pocket, [source], move=move)

        if series.distribution != self.archive.distribution:
            raise CannotCopy(
                "Series %s %s not supported in archive for %s." %
                (series.distribution.name, series.name,
                 self.archive.distribution.name))

        format = SourcePackageFormat.getTermByToken(
            source.sourcepackagerelease.dsc_format).value

        if not series.isSourcePackageFormatPermitted(format):
            raise CannotCopy(
                "Source format '%s' not supported by target series %s." %
                (source.sourcepackagerelease.dsc_format, series.name))

        # Deny copies of source publications containing files with an
        # expiration date set.
        for source_file in source.sourcepackagerelease.files:
            if source_file.libraryfile.expires is not None:
                raise CannotCopy('source contains expired files')

        if self.include_binaries and self.strict_binaries:
            built_binaries = source.getBuiltBinaries(want_files=True)
            if len(built_binaries) == 0:
                raise CannotCopy("source has no binaries to be copied")
            # Deny copies of binary publications containing files with
            # expiration date set. We only set such value for immediate
            # expiration of old superseded binaries, so no point in
            # checking its content, the fact it is set is already enough
            # for denying the copy.
            for binary_pub in built_binaries:
                for binary_file in binary_pub.binarypackagerelease.files:
                    if binary_file.libraryfile.expires is not None:
                        raise CannotCopy('source has expired binaries')

        # Check if there is already a source with the same name and version
        # published in the destination archive.
        self._checkArchiveConflicts(source, series)

        ancestry = self.archive.getPublishedSources(
            name=source.source_package_name, exact_match=True,
            distroseries=series, pocket=pocket,
            status=active_publishing_status).first()
        if ancestry is not None:
            ancestry_version = ancestry.sourcepackagerelease.version
            copy_version = source.sourcepackagerelease.version
            apt_pkg.init_system()
            if apt_pkg.version_compare(copy_version, ancestry_version) < 0:
                raise CannotCopy(
                    "version older than the %s published in %s" %
                    (ancestry.displayname, ancestry.distroseries.name))

        requires_unembargo = (
            not self.archive.private and source.hasRestrictedFiles())

        if requires_unembargo and not self.unembargo:
            raise CannotCopy(
                "Cannot copy restricted files to a public archive without "
                "explicit unembargo option.")

        # Copy is approved, update the copy inventory.
        self.addCopy(source)


def do_copy(sources, archive, series, pocket, include_binaries=False,
            person=None, check_permissions=True, overrides=None,
            send_email=False, strict_binaries=True, close_bugs=True,
            create_dsd_job=True, announce_from_person=None, sponsored=None,
            packageupload=None, unembargo=False, phased_update_percentage=None,
            move=False, logger=None):
    """Perform the complete copy of the given sources incrementally.

    Verifies if each copy can be performed using `CopyChecker` and
    raises `CannotCopy` if one or more copies could not be performed.

    When `CannotCopy` is raised, call sites are responsible for rolling
    back the transaction.  Otherwise, performed copies will be commited.

    Wrapper for `do_direct_copy`.

    :param sources: a list of `ISourcePackagePublishingHistory`.
    :param archive: the target `IArchive`.
    :param series: the target `IDistroSeries`, if None is given the same
        current source distroseries will be used as destination.
    :param pocket: the target `PackagePublishingPocket`.
    :param include_binaries: optional boolean, controls whether or
        not the published binaries for each given source should be also
        copied along with the source.
    :param person: the requester `IPerson`.
    :param check_permissions: boolean indicating whether or not the
        requester's permissions to copy should be checked.
    :param overrides: A list of `IOverride` as returned from one of the copy
        policies which will be used as a manual override insyead of using the
        default override returned by IArchive.getOverridePolicy().  There
        must be the same number of overrides as there are sources and each
        override must be for the corresponding source in the sources list.
    :param send_email: Should we notify for the copy performed?
        NOTE: If running in zopeless mode, the email is sent even if the
        transaction is later aborted. (See bug 29744)
    :param announce_from_person: If send_email is True,
        then send announcement emails with this person as the From:
    :param strict_binaries: If 'include_binaries' is True then setting this
        to True will make the copy fail if binaries cannot be also copied.
    :param close_bugs: A boolean indicating whether or not bugs on the
        copied publications should be closed.
    :param create_dsd_job: A boolean indicating whether or not a dsd job
         should be created for the new source publication.
    :param sponsored: An `IPerson` representing the person who is
        being sponsored for this copy. May be None, but if present will
        affect the "From:" address on notifications and the creator of the
        publishing record will be set to this person.
    :param packageupload: The `IPackageUpload` that caused this publication
        to be created.
    :param unembargo: If True, allow copying restricted files from a private
        archive to a public archive, and unrestrict their library files when
        doing so.
    :param phased_update_percentage: The phased update percentage to apply
        to the copied publication.
    :param move: If True, delete the source publication after copying to the
        destination.
    :param logger: An optional logger.

    :raise CannotCopy when one or more copies were not allowed. The error
        will contain the reason why each copy was denied.

    :return: a list of `ISourcePackagePublishingHistory` and
        `BinaryPackagePublishingHistory` corresponding to the copied
        publications.
    """
    copies = []
    errors = []
    copy_checker = CopyChecker(
        archive, include_binaries, strict_binaries=strict_binaries,
        unembargo=unembargo)

    for source in sources:
        if series is None:
            destination_series = source.distroseries
        else:
            destination_series = series
        try:
            copy_checker.checkCopy(
                source, destination_series, pocket, person, check_permissions,
                move=move)
        except CannotCopy as reason:
            errors.append("%s (%s)" % (source.displayname, reason))
            continue

    if len(errors) != 0:
        error_text = "\n".join(errors)
        if send_email:
            source = sources[0]
            # Although the interface allows multiple sources to be copied
            # at once, we can only send rejection email if a single source
            # is specified for now.  This is only relied on by packagecopyjob
            # which will only process one package at a time.  We need to
            # make the notification code handle atomic rejections such that
            # it notifies about multiple packages.
            if series is None:
                series = source.distroseries
            # In zopeless mode this email will be sent immediately.
            mailer = PackageUploadMailer.forAction(
                'rejected', person, source.sourcepackagerelease, [], [],
                archive, series, pocket, summary_text=error_text,
                logger=logger)
            mailer.sendAll()
        raise CannotCopy(error_text)

    overrides_index = 0
    for source in copy_checker.getCheckedCopies():
        if series is None:
            destination_series = source.distroseries
        else:
            destination_series = series
        override = None
        if overrides:
            override = overrides[overrides_index]
        # Make a note of the destination source's version for use in sending
        # the email notification and closing bugs.
        existing = archive.getPublishedSources(
            name=source.sourcepackagerelease.name, exact_match=True,
            status=active_publishing_status, distroseries=series,
            pocket=pocket).first()
        if existing:
            old_version = existing.sourcepackagerelease.version
        else:
            old_version = None
        if sponsored is not None:
            announce_from_person = sponsored
            creator = sponsored
            sponsor = person
        else:
            creator = person
            sponsor = None
        sub_copies = _do_direct_copy(
            source, archive, destination_series, pocket, include_binaries,
            override, close_bugs=close_bugs, create_dsd_job=create_dsd_job,
            close_bugs_since_version=old_version, creator=creator,
            sponsor=sponsor, packageupload=packageupload,
            phased_update_percentage=phased_update_percentage, move=move,
            logger=logger)
        if send_email and sub_copies:
            mailer = PackageUploadMailer.forAction(
                'accepted', person, source.sourcepackagerelease, [], [],
                archive, destination_series, pocket,
                announce_from_person=announce_from_person,
                previous_version=old_version, logger=logger)
            mailer.sendAll()
        if not archive.private and source.hasRestrictedFiles():
            # Fix copies by unrestricting files with privacy mismatch.
            # We must do this *after* calling mailer.sendAll (which only
            # actually sends mail on commit), because otherwise the new
            # changelog LFA won't be visible without a commit, which may
            # not be safe here.
            for pub_record in sub_copies:
                for changed_file in update_files_privacy(pub_record):
                    if logger is not None:
                        logger.info("Made %s public" % changed_file.filename)

        overrides_index += 1
        copies.extend(sub_copies)

    return copies


def _do_direct_copy(source, archive, series, pocket, include_binaries,
                    override=None, close_bugs=True, create_dsd_job=True,
                    close_bugs_since_version=None, creator=None,
                    sponsor=None, packageupload=None,
                    phased_update_percentage=None, move=False, logger=None):
    """Copy publishing records to another location.

    Copy each item of the given list of `SourcePackagePublishingHistory`
    to the given destination if they are not yet available (previously
    copied).

    Also copy published binaries for each source if requested to. Again,
    only copy binaries that were not yet copied before.

    :param source: an `ISourcePackagePublishingHistory`.
    :param archive: the target `IArchive`.
    :param series: the target `IDistroSeries`, if None is given the same
        current source distroseries will be used as destination.
    :param pocket: the target `PackagePublishingPocket`.
    :param include_binaries: optional boolean, controls whether or
        not the published binaries for each given source should be also
        copied along with the source.
    :param override: An `IOverride` as per do_copy().
    :param close_bugs: A boolean indicating whether or not bugs on the
        copied publication should be closed.
    :param create_dsd_job: A boolean indicating whether or not a dsd job
         should be created for the new source publication.
    :param close_bugs_since_version: If close_bugs is True,
        then this parameter says which changelog entries to parse looking
        for bugs to close.  See `close_bugs_for_sourcepackagerelease`.
    :param creator: the requester `IPerson`.
    :param sponsor: the sponsor `IPerson`, if this copy is being sponsored.
    :param packageupload: The `IPackageUpload` that caused this publication
        to be created.
    :param phased_update_percentage: The phased update percentage to apply
        to the copied publication.
    :param move: If True, delete the source publication after copying to the
        destination.
    :param logger: An optional logger.

    :return: a list of `ISourcePackagePublishingHistory` and
        `BinaryPackagePublishingHistory` corresponding to the copied
        publications.
    """
    copies = []
    custom_files = []

    # Copy source if it's not yet copied.
    source_in_destination = archive.getPublishedSources(
        name=source.sourcepackagerelease.name, exact_match=True,
        version=source.sourcepackagerelease.version,
        status=active_publishing_status,
        distroseries=series, pocket=pocket)
    policy = archive.getOverridePolicy(
        series, pocket, phased_update_percentage=phased_update_percentage)
    if override is None and policy is not None:
        # Only one override can be returned so take the first
        # element of the returned list.
        override = policy.calculateSourceOverrides(
            {source.sourcepackagerelease.sourcepackagename: SourceOverride()}
            )[source.sourcepackagerelease.sourcepackagename]
    if source_in_destination.is_empty():
        # If no manual overrides were specified and the archive has an
        # override policy then use that policy to get overrides.
        source_copy = source.copyTo(
            series, pocket, archive, override, create_dsd_job=create_dsd_job,
            creator=creator, sponsor=sponsor, packageupload=packageupload)
        if close_bugs:
            close_bugs_for_sourcepublication(
                source_copy, close_bugs_since_version)
        copies.append(source_copy)
    else:
        source_copy = source_in_destination.first()
    if source_copy.packageupload is not None:
        custom_files.extend(source_copy.packageupload.customfiles)

    if include_binaries:
        # Copy missing binaries for the matching architectures in the
        # destination series. ISPPH.getBuiltBinaries() return only unique
        # publication per binary package releases (i.e. excludes irrelevant
        # arch-indep publications) and IBPPH.copy is prepared to expand
        # arch-indep publications.
        binary_copies = getUtility(IPublishingSet).copyBinaries(
            archive, series, pocket, source.getBuiltBinaries(), policy=policy,
            source_override=override)

        if binary_copies is not None:
            copies.extend(binary_copies)
            binary_uploads = set(
                bpph.binarypackagerelease.build.package_upload
                for bpph in binary_copies)
            for binary_upload in binary_uploads:
                if binary_upload is not None:
                    custom_files.extend(binary_upload.customfiles)

    if custom_files:
        # Custom uploads aren't modelled as publication history records, so
        # we have to send these through the upload queue.
        custom_copier = CustomUploadsCopier(
            series, target_pocket=pocket, target_archive=archive)
        for custom in custom_files:
            if custom_copier.isCopyable(custom):
                custom_copier.copyUpload(custom)

    # Always ensure the needed builds exist in the copy destination
    # after copying the binaries.
    # XXX cjwatson 2012-06-22 bug=869308: Fails to honour P-a-s.
    source_copy.createMissingBuilds(logger=logger)

    if move:
        removal_comment = "Moved to %s" % series.getSuite(pocket)
        if archive != source.archive:
            removal_comment += " in %s" % archive.reference
        getUtility(IPublishingSet).requestDeletion(
            [source], creator, removal_comment=removal_comment)

    return copies
