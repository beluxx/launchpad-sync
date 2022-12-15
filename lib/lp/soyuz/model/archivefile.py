# Copyright 2016-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A file in an archive."""

__all__ = [
    "ArchiveFile",
    "ArchiveFileSet",
]

import os.path
import re

import pytz
from storm.databases.postgres import Returning
from storm.locals import And, DateTime, Int, Reference, Storm, Unicode
from zope.component import getUtility
from zope.interface import implementer

from lp.services.database.bulk import load_related
from lp.services.database.constants import UTC_NOW
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.interfaces import IPrimaryStore, IStore
from lp.services.database.sqlbase import convert_storm_clause_to_string
from lp.services.database.stormexpr import BulkUpdate, RegexpMatch
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.services.librarian.model import LibraryFileAlias, LibraryFileContent
from lp.soyuz.interfaces.archivefile import IArchiveFile, IArchiveFileSet


@implementer(IArchiveFile)
class ArchiveFile(Storm):
    """See `IArchiveFile`."""

    __storm_table__ = "ArchiveFile"

    id = Int(primary=True)

    archive_id = Int(name="archive", allow_none=False)
    archive = Reference(archive_id, "Archive.id")

    container = Unicode(name="container", allow_none=False)

    path = Unicode(name="path", allow_none=False)

    library_file_id = Int(name="library_file", allow_none=False)
    library_file = Reference(library_file_id, "LibraryFileAlias.id")

    scheduled_deletion_date = DateTime(
        name="scheduled_deletion_date", tzinfo=pytz.UTC, allow_none=True
    )

    def __init__(self, archive, container, path, library_file):
        """Construct an `ArchiveFile`."""
        super().__init__()
        self.archive = archive
        self.container = container
        self.path = path
        self.library_file = library_file
        self.scheduled_deletion_date = None


def _now():
    """Get the current transaction timestamp.

    Tests can override this with a Storm expression or a `datetime` to
    simulate time changes.
    """
    return UTC_NOW


@implementer(IArchiveFileSet)
class ArchiveFileSet:
    """See `IArchiveFileSet`."""

    @staticmethod
    def new(archive, container, path, library_file):
        """See `IArchiveFileSet`."""
        archive_file = ArchiveFile(archive, container, path, library_file)
        IPrimaryStore(ArchiveFile).add(archive_file)
        return archive_file

    @classmethod
    def newFromFile(
        cls, archive, container, path, fileobj, size, content_type
    ):
        library_file = getUtility(ILibraryFileAliasSet).create(
            os.path.basename(path),
            size,
            fileobj,
            content_type,
            restricted=archive.private,
            allow_zero_length=True,
        )
        return cls.new(archive, container, path, library_file)

    @staticmethod
    def getByArchive(
        archive,
        container=None,
        path=None,
        path_parent=None,
        sha256=None,
        condemned=None,
        eager_load=False,
    ):
        """See `IArchiveFileSet`."""
        clauses = [ArchiveFile.archive == archive]
        # XXX cjwatson 2016-03-15: We'll need some more sophisticated way to
        # match containers once we're using them for custom uploads.
        if container is not None:
            clauses.append(ArchiveFile.container == container)
        if path is not None:
            clauses.append(ArchiveFile.path == path)
        if path_parent is not None:
            clauses.append(
                RegexpMatch(
                    ArchiveFile.path, "^%s/[^/]+$" % re.escape(path_parent)
                )
            )
        if sha256 is not None:
            clauses.extend(
                [
                    ArchiveFile.library_file == LibraryFileAlias.id,
                    LibraryFileAlias.contentID == LibraryFileContent.id,
                    LibraryFileContent.sha256 == sha256,
                ]
            )
        if condemned is not None:
            if condemned:
                clauses.append(ArchiveFile.scheduled_deletion_date != None)
            else:
                clauses.append(ArchiveFile.scheduled_deletion_date == None)
        archive_files = IStore(ArchiveFile).find(ArchiveFile, *clauses)

        def eager_load(rows):
            lfas = load_related(LibraryFileAlias, rows, ["library_file_id"])
            load_related(LibraryFileContent, lfas, ["contentID"])

        if eager_load:
            return DecoratedResultSet(archive_files, pre_iter_hook=eager_load)
        else:
            return archive_files

    @staticmethod
    def scheduleDeletion(archive_files, stay_of_execution):
        """See `IArchiveFileSet`."""
        clauses = [
            ArchiveFile.id.is_in(
                {archive_file.id for archive_file in archive_files}
            ),
            ArchiveFile.library_file == LibraryFileAlias.id,
            LibraryFileAlias.content == LibraryFileContent.id,
        ]
        new_date = _now() + stay_of_execution
        return_columns = [
            ArchiveFile.container,
            ArchiveFile.path,
            LibraryFileContent.sha256,
        ]
        return list(
            IPrimaryStore(ArchiveFile).execute(
                Returning(
                    BulkUpdate(
                        {ArchiveFile.scheduled_deletion_date: new_date},
                        table=ArchiveFile,
                        values=[LibraryFileAlias, LibraryFileContent],
                        where=And(*clauses),
                    ),
                    columns=return_columns,
                )
            )
        )

    @staticmethod
    def unscheduleDeletion(archive_files):
        """See `IArchiveFileSet`."""
        clauses = [
            ArchiveFile.id.is_in(
                {archive_file.id for archive_file in archive_files}
            ),
            ArchiveFile.library_file == LibraryFileAlias.id,
            LibraryFileAlias.content == LibraryFileContent.id,
        ]
        return_columns = [
            ArchiveFile.container,
            ArchiveFile.path,
            LibraryFileContent.sha256,
        ]
        return list(
            IPrimaryStore(ArchiveFile).execute(
                Returning(
                    BulkUpdate(
                        {ArchiveFile.scheduled_deletion_date: None},
                        table=ArchiveFile,
                        values=[LibraryFileAlias, LibraryFileContent],
                        where=And(*clauses),
                    ),
                    columns=return_columns,
                )
            )
        )

    @staticmethod
    def getContainersToReap(archive, container_prefix=None):
        clauses = [
            ArchiveFile.archive == archive,
            ArchiveFile.scheduled_deletion_date < _now(),
        ]
        if container_prefix is not None:
            clauses.append(ArchiveFile.container.startswith(container_prefix))
        return (
            IStore(ArchiveFile)
            .find(ArchiveFile.container, *clauses)
            .group_by(ArchiveFile.container)
        )

    @staticmethod
    def delete(archive_files):
        """See `IArchiveFileSet`."""
        # XXX cjwatson 2016-03-30 bug=322972: Requires manual SQL due to
        # lack of support for DELETE FROM ... USING ... in Storm.
        clauses = [
            ArchiveFile.id.is_in(
                {archive_file.id for archive_file in archive_files}
            ),
            ArchiveFile.library_file_id == LibraryFileAlias.id,
            LibraryFileAlias.contentID == LibraryFileContent.id,
        ]
        where = convert_storm_clause_to_string(And(*clauses))
        return list(
            IPrimaryStore(ArchiveFile).execute(
                """
            DELETE FROM ArchiveFile
            USING LibraryFileAlias, LibraryFileContent
            WHERE """
                + where
                + """
            RETURNING
                ArchiveFile.container,
                ArchiveFile.path,
                LibraryFileContent.sha256
            """
            )
        )
