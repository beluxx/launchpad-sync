# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TemporaryBlobStorage',
    'TemporaryStorageManager',
    ]

from cStringIO import StringIO
from datetime import timedelta, datetime
import random
import sha
import time
import thread

from pytz import UTC
from sqlobject import StringCol, ForeignKey
from zope.component import getUtility
from zope.interface import implements

from canonical import uuid
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces import (
    ITemporaryBlobStorage,
    ITemporaryStorageManager,
    ILibraryFileAliasSet,
    )


class TemporaryBlobStorage(SQLBase):
    """A temporary BLOB stored in Launchpad."""

    implements(ITemporaryBlobStorage)

    _table='TemporaryBlobStorage'

    uuid = StringCol(notNull=True, alternateID=True)
    file_alias = ForeignKey(
            dbName='file_alias', foreignKey='LibraryFileAlias', notNull=True,
            alternateID=True
            )
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)

    @property
    def blob(self):
        self.file_alias.open()
        try:
            return self.file_alias.read()
        finally:
            self.file_alias.close()


class TemporaryStorageManager:
    """A tool to create temporary BLOB's in Launchpad."""

    implements(ITemporaryStorageManager)

    def new(self, blob, expires=None):
        """See ITemporaryStorageManager."""
        if expires is None:
            expires = datetime.utcnow().replace(tzinfo=UTC)

        # At this stage we could do some sort of throttling if we were
        # concerned about abuse of the temporary storage facility. For
        # example, we could check the number of rows in temporary storage,
        # or the total amount of space dedicated to temporary storage, and
        # return an error code if that volume was unacceptably high. But for
        # the moment we will just ensure the BLOB is not that LARGE.
        #
        # YAGNI - there are plenty of other ways to upload large chunks
        # of data to Launchpad that will hang around permanently. Size
        # limitations on uploads needs to be done in Zope3 to avoid DOS
        # attacks in general.
        # if len(blob) > 320000:
        #     return None
        # create the BLOB and return the UUID

        new_uuid = str(uuid.generate_uuid())

        # We use a random filename, so only things that can look up the
        # secret can retrieve the original data.
        secret = sha.new("%s%s%s%s%s" % (
            time.time(), random.random(), thread.get_ident(),
            new_uuid, expires
            )).hexdigest()

        file_alias = getUtility(ILibraryFileAliasSet).create(
                secret, len(blob), StringIO(blob),
                'application/octet-stream', expires
                )
        TemporaryBlobStorage(uuid=new_uuid, file_alias=file_alias)
        return new_uuid

    def fetch(self, uuid):
        """See ITemporaryStorageManager."""
        return TemporaryBlobStorage.selectOneBy(uuid=uuid)

    def delete(self, uuid):
        """See ITemporaryStorageManager."""
        blob = TemporaryBlobStorage.selectOneBy(uuid=uuid)
        if blob is not None:
            TemporaryBlobStorage.delete(blob.id)

