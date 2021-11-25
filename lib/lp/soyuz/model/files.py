# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'BinaryPackageFile',
    'SourceFileMixin',
    'SourcePackageReleaseFile',
    ]

from zope.interface import implementer

from lp.registry.interfaces.sourcepackage import SourcePackageFileType
from lp.services.database.enumcol import DBEnum
from lp.services.database.sqlbase import SQLBase
from lp.services.database.sqlobject import ForeignKey
from lp.soyuz.enums import BinaryPackageFileType
from lp.soyuz.interfaces.files import (
    IBinaryPackageFile,
    ISourcePackageReleaseFile,
    )


@implementer(IBinaryPackageFile)
class BinaryPackageFile(SQLBase):
    """See IBinaryPackageFile """
    _table = 'BinaryPackageFile'

    binarypackagerelease = ForeignKey(dbName='binarypackagerelease',
                                      foreignKey='BinaryPackageRelease',
                                      notNull=True)
    libraryfile = ForeignKey(dbName='libraryfile',
                             foreignKey='LibraryFileAlias', notNull=True)
    filetype = DBEnum(name='filetype', enum=BinaryPackageFileType)


class SourceFileMixin:
    """Mix-in class for common functionality between source file classes."""

    @property
    def is_orig(self):
        return self.filetype in (
            SourcePackageFileType.ORIG_TARBALL,
            SourcePackageFileType.COMPONENT_ORIG_TARBALL,
            SourcePackageFileType.ORIG_TARBALL_SIGNATURE,
            SourcePackageFileType.COMPONENT_ORIG_TARBALL_SIGNATURE,
            )


@implementer(ISourcePackageReleaseFile)
class SourcePackageReleaseFile(SourceFileMixin, SQLBase):
    """See ISourcePackageFile"""

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
                                      dbName='sourcepackagerelease')
    libraryfile = ForeignKey(foreignKey='LibraryFileAlias',
                             dbName='libraryfile')
    filetype = DBEnum(enum=SourcePackageFileType)
