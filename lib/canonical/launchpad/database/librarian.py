from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from sqlobject import StringCol, ForeignKey, IntCol, RelatedJoin

class LibraryFileContent(SQLBase):
    """A pointer to file content in the librarian."""

    _table = 'LibraryFileContent'

    _columns = [
        # FIXME: make sqlobject let us use the default in the DB
        UtcDateTimeCol('dateCreated', dbName='dateCreated', notNull=True,
                       default=UTC_NOW),
        UtcDateTimeCol('dateMirrored', dbName='dateMirrored', default=None),
        IntCol('filesize', dbName='filesize', notNull=True),
        StringCol('sha1', dbName='sha1', notNull=True),
    ]


class LibraryFileAlias(SQLBase):
    """A filename and mimetype that we can serve some given content with."""
    
    _table = 'LibraryFileAlias'

    content = ForeignKey(
            foreignKey='LibraryFileContent', dbName='content', notNull=True,
            )
    filename = StringCol(notNull=True)
    mimetype = StringCol(notNull=True)

    def url(self):
        raise NotImplementedError, 'Implement me'
    url = property(url)

    products = RelatedJoin('ProductRelease', joinColumn='libraryfile',
                           otherColumn='productrelease',
                           intermediateTable='ProductReleaseFile');

    sourcepackages = RelatedJoin('SourcePackageRelease',
                                 joinColumn='libraryfile',
                                 otherColumn='sourcepackagerelease',
                                 intermediateTable='SourcePackageReleaseFile');

