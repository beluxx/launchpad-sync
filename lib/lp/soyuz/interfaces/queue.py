# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Queue interfaces."""

__metaclass__ = type

__all__ = [
    'IHasQueueItems',
    'IPackageUploadQueue',
    'IPackageUpload',
    'IPackageUploadBuild',
    'IPackageUploadSource',
    'IPackageUploadCustom',
    'IPackageUploadSet',
    'NonBuildableSourceUploadError',
    'QueueBuildAcceptError',
    'QueueInconsistentStateError',
    'QueueSourceAcceptError',
    'QueueStateWriteProtectedError',
    ]

from lazr.enum import (
    DBEnumeratedType,
    )

from lazr.restful.declarations import (
    export_as_webservice_entry,
    exported,
    )
from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Datetime,
    Int,
    List,
    TextLine,
    )

from canonical.launchpad import _

from lp.soyuz.enums import PackageUploadStatus


class QueueStateWriteProtectedError(Exception):
    """This exception prevent directly set operation in queue state.

    The queue state machine is controlled by its specific provided methods,
    like: setNew, setAccepted and so on.
    """


class QueueInconsistentStateError(Exception):
    """Queue state machine error.

    It's generated when the solicited state makes the record
    inconsistent against the current system constraints.
    """


class NonBuildableSourceUploadError(QueueInconsistentStateError):
    """Source upload will not result in any build record.

    This error is raised when trying to accept a source upload that is
    consistent but will not build in any of the architectures supported
    in its targeted distroseries.
    """


class QueueSourceAcceptError(Exception):
    """It prevents a PackageUploadSource from being ACCEPTED.

    It is generated by Component and/or Section mismatching in a DistroSeries.
    """


class QueueBuildAcceptError(Exception):
    """It prevents a PackageUploadBuild from being ACCEPTED.

    It is generated by Component and/or Section mismatching in a DistroSeries.
    """


class IPackageUploadQueue(Interface):
    """Used to establish permission to a group of package uploads.

    Recieves an IDistroSeries and a PackageUploadStatus dbschema
    on initialisation.
    No attributes exposed via interface, only used to check permissions.
    """


class IPackageUpload(Interface):
    """A Queue item for the archive uploader."""

    export_as_webservice_entry(publish_web_link=False)

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )

    status = exported(
        Choice(
            vocabulary=PackageUploadStatus,
            description=_("The status of this upload."),
            title=_("Queue status"), required=False, readonly=True,
            ))

    distroseries = exported(
        Reference(
            # Really IDistroSeries, patched in
            # _schema_circular_imports.py
            schema=Interface,
            description=_("The distroseries targeted by this upload."),
            title=_("Series"), required=True, readonly=False,
            ))

    pocket = exported(
        Choice(
            # Really PackagePublishingPocket, patched in
            # _schema_circular_imports.py
            vocabulary=DBEnumeratedType,
            description=_("The pocket targeted by this upload."),
            title=_("The pocket"), required=True, readonly=False,
            ))

    date_created = exported(
        Datetime(
            title=_('Date created'),
            description=_("The date this package upload was done.")))

    changesfile = Attribute("The librarian alias for the changes file "
                            "associated with this upload")

    signing_key = Attribute("Changesfile Signing Key.")
    archive = exported(
        Reference(
            # Really IArchive, patched in _schema_circular_imports.py
            schema=Interface,
            description=_("The archive for this upload."),
            title=_("Archive"), required=True, readonly=True))
    sources = Attribute("The queue sources associated with this queue item")
    builds = Attribute("The queue builds associated with the queue item")
    customfiles = Attribute("Custom upload files associated with this "
                            "queue item")

    custom_file_urls = exported(
        List(
            title=_("Custom File URLs"),
            description=_("Librarian URLs for all the custom files attached "
                          "to this upload."),
            value_type=TextLine(),
            required=False,
            readonly=True))

    displayname = exported(
        TextLine(
            title=_("Generic displayname for a queue item"), readonly=True),
        exported_as="display_name")
    displayversion = exported(
        TextLine(
            title=_("The source package version for this item"),
            readonly=True),
        exported_as="display_version")
    displayarchs = exported(
        TextLine(
            title=_("Architectures related to this item"), readonly=True),
        exported_as="display_arches")

    sourcepackagerelease = Attribute(
        "The source package release for this item")

    contains_source = Attribute("whether or not this upload contains sources")
    contains_build = Attribute("whether or not this upload contains binaries")
    contains_installer = Attribute(
        "whether or not this upload contains installers images")
    contains_translation = Attribute(
        "whether or not this upload contains translations")
    contains_upgrader = Attribute(
        "wheter or not this upload contains upgrader images")
    contains_ddtp = Attribute(
        "wheter or not this upload contains DDTP images")
    isPPA = Attribute(
        "Return True if this PackageUpload is a PPA upload.")
    is_delayed_copy = Attribute(
        "Whether or not this PackageUpload record is a delayed-copy.")

    components = Attribute(
        """The set of components used in this upload.

        For sources, this is the component on the associated
        sourcepackagerelease.  For binaries, this is all the components
        on all the binarypackagerelease records arising from the build.
        """)

    def setNew():
        """Set queue state to NEW."""

    def setUnapproved():
        """Set queue state to UNAPPROVED."""

    def setAccepted():
        """Set queue state to ACCEPTED.

        Perform the required checks on its content, so we guarantee data
        integrity by code.
        """

    def setDone():
        """Set queue state to DONE."""

    def setRejected():
        """Set queue state to REJECTED."""

    def acceptFromUploader(changesfile_path, logger=None):
        """Perform upload acceptance during upload-time.

         * Move the upload to accepted queue in all cases.
         * Publish and close bugs for 'single-source' uploads.
         * Skip bug-closing for PPA uploads.
         * Grant karma to people involved with the upload.

        :raises: AssertionError if the context is a delayed-copy.
        """

    def acceptFromCopy():
        """Perform upload acceptance for a delayed-copy record.

         * Move the upload to accepted queue in all cases.

        :raises: AssertionError if the context is not a delayed-copy or
            has no sources associated to it.
        """

    def acceptFromQueue(announce_list, logger=None, dry_run=False):
        """Call setAccepted, do a syncUpdate, and send notification email.

         * Grant karma to people involved with the upload.

        :raises: AssertionError if the context is a delayed-copy.
        """

    def rejectFromQueue(logger=None, dry_run=False):
        """Call setRejected, do a syncUpdate, and send notification email."""

    def realiseUpload(logger=None):
        """Take this ACCEPTED upload and create the publishing records for it
        as appropriate.

        When derivation is taken into account, this may result in queue items
        being created for derived distributions.

        If a logger is provided, messages will be written to it as the upload
        is entered into the publishing records.

        Return a list containing the publishing records created.
        """

    def addSource(spr):
        """Add the provided source package release to this queue entry."""

    def addBuild(build):
        """Add the provided build to this queue entry."""

    def addCustom(library_file, custom_type):
        """Add the provided library file alias as a custom queue entry of
        the given custom type.
        """

    def syncUpdate():
        """Write updates made on this object to the database.

        This should be used when you can't wait until the transaction is
        committed to have some updates actually written to the database.
        """

    def notify(announce_list=None, summary_text=None,
        changes_file_object=None, logger=None):
        """Notify by email when there is a new distroseriesqueue entry.

        This will send new, accept, announce and rejection messages as
        appropriate.

        :param announce_list: The email address of the distro announcements

        :param summary_text: Any additional text to append to the auto-
            generated summary.  This is also the only text used if there is
            a rejection message generated.

        :param changes_file_object: An open file object pointing at the
            changes file.  Current, only nascentupload need supply this
            as the transaction is not committed to the DB at that point so
            data needs to be obtained from the changes file.

        :param logger: Specify a logger object if required.  Mainly for tests.
        """

    def overrideSource(new_component, new_section, allowed_components):
        """Override the source package contained in this queue item.

        :param new_component: An IComponent to replace the existing one
            in the upload's source.
        :param new_section: An ISection to replace the existing one
            in the upload's source.
        :param allowed_components: A sequence of components that the
            callsite is allowed to override from and to.

        :raises QueueInconsistentStateError: if either the existing
            or the new_component are not in the allowed_components
            sequence.

        The override values may be None, in which case they are not
        changed.

        :return: True if the source was overridden.
        """

    def overrideBinaries(new_component, new_section, new_priority,
                         allowed_components):
        """Override all the binaries in a binary queue item.

        :param new_component: An IComponent to replace the existing one
            in the upload's source.
        :param new_section: An ISection to replace the existing one
            in the upload's source.
        :param new_priority: A valid PackagePublishingPriority to replace
            the existing one in the upload's binaries.
        :param allowed_components: A sequence of components that the
            callsite is allowed to override from and to.

        :raises QueueInconsistentStateError: if either the existing
            or the new_component are not in the allowed_components
            sequence.

        The override values may be None, in which case they are not
        changed.

        :return: True if the binaries were overridden.
        """


class IPackageUploadBuild(Interface):
    """A Queue item's related builds."""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )


    packageupload = Int(
            title=_("PackageUpload"), required=True,
            readonly=False,
            )

    build = Int(
            title=_("The related build"), required=True, readonly=False,
            )

    def publish(logger=None):
        """Publish this queued source in the distroseries referred to by
        the parent queue item.

        We determine the distroarchseries by matching architecturetags against
        the distroarchseries the build was compiled for.

        This method can raise NotFoundError if the architecturetag can't be
        matched up in the queue item's distroseries.

        Returns a list of the secure binary package publishing history
        objects in case it is of use to the caller. This may include records
        published into other distroarchseriess if this build contained arch
        independant packages.

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """


class IPackageUploadSource(Interface):
    """A Queue item's related sourcepackagereleases."""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )


    packageupload = Int(
            title=_("PackageUpload"), required=True,
            readonly=False,
            )

    sourcepackagerelease = Int(
            title=_("The related source package release"), required=True,
            readonly=False,
            )

    def getSourceAncestry():
        """Return a suitable ancestry publication for this context.

        The possible ancestries locations for a give source upload, assuming
        that only PRIMARY archive allows post-RELEASE pockets are:

         1. original archive, original distroseries and pocket (old
            DEVELOPMENT/SRU/PPA uploads).
         2. primary archive, original distroseries and release pocket (NEW
            SRU/PPA uploads fallback).
         3. primary_archive, any distroseries and release pocket (BACKPORTS)

        We lookup a source publication with the same name in those location
        and in that order. If an ancestry is found it is returned, otherwise
        it returns None.

        :return: `ISourcePackagePublishingHistory` for the corresponding
             ancestry or None if it wasn't found.
        """

    def verifyBeforeAccept():
        """Perform overall checks before promoting source to ACCEPTED queue.

        If two queue items have the same (name, version) pair there is
        an inconsistency. To identify this situation we check the accepted
        & done queue items for each distroseries for such duplicates and
        raise an exception if any are found.
        See bug #31038 & #62976 for details.
        """

    def verifyBeforePublish():
        """Perform overall checks before publishing a source queue record.

        Check if the source package files do not collide with the
        ones already published in the archive. We need this to catch
        inaccurate  *epoched* versions, which would pass the upload version
        check but would collide with diff(s) or dsc(s) previously published
        on disk. This inconsistency is well known in debian-like archives
        and happens because filenames do not contain epoch. For further
        information see bug #119753.
        """

    def checkComponentAndSection():
        """Verify the current Component and Section via Selection table.

        Check if the current sourcepackagerelease component and section
        matches with those included in the target distribution series,
        if not raise QueueSourceAcceptError exception.
        """

    def publish(logger=None):
        """Publish this queued source in the distroseries referred to by
        the parent queue item.

        Returns the secure source package publishing history object in case
        it is of use to the caller.

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """


class IPackageUploadCustom(Interface):
    """Stores anything else than source and binaries that needs publication.

    It is essentially a map between DistroSeries/Pocket/LibrarianFileAlias.

    The LibrarianFileAlias usually is a TGZ containing an specific format.
    Currently we support:
     [Debian-Installer, Rosetta-Translation, Dist-Upgrader, DDTP-Tarball]

    Each one has an processor which is invoked by the publish method.
    """

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )

    packageupload = Int(
            title=_("PackageUpload"), required=True,
            readonly=False,
            )

    customformat = Int(
            title=_("The custom format for the file"), required=True,
            readonly=False,
            )

    libraryfilealias = Int(
            title=_("The file"), required=True, readonly=False,
            )

    def temp_filename():
        """Return a filename containing the libraryfile for this upload.

        This filename will be in a temporary directory and can be the
        ensure dir can be deleted once whatever needed the file is finished
        with it.
        """

    def publish(logger=None):
        """Publish this custom item directly into the filesystem.

        This can only be run by a process which has filesystem access to
        the archive (or wherever else the content will go).

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """

    def publishDebianInstaller(logger=None):
        """Publish this custom item as a raw installer tarball.

        This will write the installer tarball out to the right part of
        the archive.

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """

    def publishDistUpgrader(logger=None):
        """Publish this custom item as a raw dist-upgrader tarball.

        This will write the dist-upgrader tarball out to the right part of
        the archive.

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """

    def publishDdtpTarball(logger=None):
        """Publish this custom item as a raw ddtp-tarball.

        This will write the ddtp-tarball out to the right part of
        the archive.

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """

    def publishRosettaTranslations(logger=None):
        """Publish this custom item as a rosetta tarball.

        Essentially this imports the tarball into rosetta.

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """

    def publishStaticTranslations(logger):
        """Publish this custom item as a static translations tarball.

        This is currently a no-op as we don't publish these files, they only
        reside in the librarian for later retrieval using the webservice.
        """

    def publishMetaData(logger):
        """Publish this custom item as a meta-data file.

        This method writes the meta-data custom file to the archive in
        the location matching this schema:
        /<person>/meta/<ppa_name>/<filename>

        It's not written to the main archive location because that could be
        protected by htaccess in the case of private archives.
        """


class IPackageUploadSet(Interface):
    """Represents a set of IPackageUploads"""

    def __iter__():
        """IPackageUpload iterator"""

    def __getitem__(queue_id):
        """Retrieve an IPackageUpload by a given id"""

    def get(queue_id):
        """Retrieve an IPackageUpload by a given id"""

    def count(status=None, distroseries=None, pocket=None):
        """Number of IPackageUpload present in a given status.

        If status is ommitted return the number of all entries.
        'distroseries' is optional and restrict the results in given
        distroseries, same for pocket.
        """

    def createDelayedCopy(archive, distroseries, pocket, signing_key):
        """Return a `PackageUpload` record for a delayed-copy operation.

        :param archive: target `IArchive`,
        :param distroseries: target `IDistroSeries`,
        :param pocket: target `PackagePublishingPocket`,
        :param signing_key: `IGPGKey` of the user requesting this copy.

        :return: an `IPackageUpload` record in NEW state.
        """

    def getAll(distroseries, created_since_date=None, status=None,
               archive=None, pocket=None, custom_type=None):
        """Get package upload records for a series with optional filtering.

        :param created_since_date: If specified, only returns items uploaded
            since the timestamp supplied.
        :param status: Filter results by this `PackageUploadStatus`
        :param archive: Filter results for this `IArchive`
        :param pocket: Filter results by this `PackagePublishingPocket`
        :param custom_type: Filter results by this `PackageUploadCustomFormat`
        :return: A result set containing `IPackageUpload`s
        """

    def findSourceUpload(name, version, archive, distribution):
        """Return a `PackageUpload` for a matching source.

        :param name: a string with the exact source name.
        :param version: a string with the exact source version.
        :param archive: source upload target `IArchive`.
        :param distribution: source upload target `IDistribution`.

        :return: a matching `IPackageUpload` object.
        """

    def getBuildByBuildIDs(build_ids):
        """Return `PackageUploadBuilds`s for the supplied build IDs."""

    def getSourceBySourcePackageReleaseIDs(spr_ids):
        """Return `PackageUploadSource`s for the sourcepackagerelease IDs."""


class IHasQueueItems(Interface):
    """An Object that has queue items"""

    def getPackageUploadQueue(state):
        """Return an IPackageUploadeQueue occording the given state."""

    def getQueueItems(status=None, name=None, version=None,
                      exact_match=False, pocket=None, archive=None):
        """Get the union of builds, sources and custom queue items.

        Returns builds, sources and custom queue items in a given state,
        matching a give name and version terms.

        If 'status' is not supplied, return all items in the queues,
        it supports multiple statuses as a list.

        If 'name' and 'version' are supplied only items which match (SQL LIKE)
        the sourcepackage name, binarypackage name or the filename will be
        returned.  'name' can be supplied without supplying 'version'.
        'version' has no effect on custom queue items.

        If 'pocket' is specified return only queue items inside it, otherwise
        return all pockets.  It supports multiple pockets as a list.

        If 'archive' is specified return only queue items targeted to this
        archive, if not restrict the results to the
        IDistribution.main_archive.

        Use 'exact_match' argument for precise results.
        """
