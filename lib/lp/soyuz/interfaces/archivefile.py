# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for a file in an archive."""

__metaclass__ = type
__all__ = [
    'IArchiveFile',
    'IArchiveFileSet',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Datetime,
    Int,
    TextLine,
    )

from lp import _
from lp.services.librarian.interfaces import ILibraryFileAlias
from lp.soyuz.interfaces.archive import IArchive


class IArchiveFile(Interface):
    """A file in an archive.

    This covers files that are not published in the archive's package pool,
    such as the Packages and Sources index files.
    """

    id = Int(title=_("ID"), required=True, readonly=True)

    archive = Reference(
        title=_("The archive containing the index file."),
        schema=IArchive, required=True, readonly=True)

    container = TextLine(
        title=_("An identifier for the component that manages this file."),
        required=True, readonly=True)

    path = TextLine(
        title=_("The path to the index file within the published archive."),
        required=True, readonly=True)

    library_file = Reference(
        title=_("The index file in the librarian."),
        schema=ILibraryFileAlias, required=True, readonly=True)

    scheduled_deletion_date = Datetime(
        title=_("The date when this file should stop being published."),
        required=False, readonly=False)


class IArchiveFileSet(Interface):
    """Bulk operations on files in an archive."""

    def new(archive, container, path, library_file):
        """Create a new `IArchiveFile`.

        :param archive: The `IArchive` containing the new file.
        :param container: An identifier for the component that manages this
            file.
        :param path: The path to the new file within its archive.
        :param library_file: The `ILibraryFileAlias` embodying the new file.
        """

    def newFromFile(archive, container, path, fileobj, size, content_type):
        """Create a new `IArchiveFile` from a file on the file system.

        :param archive: The `IArchive` containing the new file.
        :param container: An identifier for the component that manages this
            file.
        :param path: The path to the new file within its archive.
        :param fileobj: A file-like object to read the data from.
        :param size: The size of the file in bytes.
        :param content_type: The MIME type of the file.
        """

    def getByArchive(archive, container=None, path=None, only_condemned=False,
                     eager_load=False):
        """Get files in an archive.

        :param archive: Return files in this `IArchive`.
        :param container: Return only files with this container.
        :param path: Return only files with this path.
        :param only_condemned: If True, return only files with a
            scheduled_deletion_date set.
        :param eager_load: If True, preload related `LibraryFileAlias` and
            `LibraryFileContent` rows.
        :return: An iterable of matched files.
        """

    def scheduleDeletion(archive_files, stay_of_execution):
        """Schedule these archive files for future deletion.

        :param archive_files: The `IArchiveFile`s to schedule for deletion.
        :param stay_of_execution: A `timedelta`; schedule files for deletion
            this amount of time in the future.
        :return: An iterable of (container, path, sha256) for files that
            were scheduled for deletion.
        """

    def unscheduleDeletion(archive_files):
        """Unschedule these archive files for deletion.

        This is useful in the case when the new content of a file is
        identical to a version that was previously condemned.

        :param archive_files: The `IArchiveFile`s to unschedule for deletion.
        :return: An iterable of (container, path, sha256) for files that
            were unscheduled for deletion.
        """

    def getContainersToReap(archive, container_prefix=None):
        """Return containers in this archive with files that should be reaped.

        :param archive: Return containers in this `IArchive`.
        :param container_prefix: Return only containers that start with this
            prefix.
        :return: An iterable of matched container names.
        """

    def reap(archive, container=None):
        """Delete archive files that are past their scheduled deletion date.

        :param archive: Delete files from this `IArchive`.
        :param container: Delete only files with this container.
        :return: An iterable of (container, path, sha256) for files that
            were deleted.
        """
