# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ['ParsedApacheLog']

import six
from storm.locals import (
    Int,
    Storm,
    Unicode,
    )
from zope.interface import implementer

from lp.services.apachelogparser.interfaces.parsedapachelog import (
    IParsedApacheLog,
    )
from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.interfaces import IStore


@implementer(IParsedApacheLog)
class ParsedApacheLog(Storm):
    """See `IParsedApacheLog`"""
    __storm_table__ = 'ParsedApacheLog'

    id = Int(primary=True)
    first_line = Unicode(allow_none=False)
    bytes_read = Int(allow_none=False)
    date_last_parsed = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    def __init__(self, first_line, bytes_read):
        super(ParsedApacheLog, self).__init__()
        self.first_line = six.ensure_text(first_line)
        self.bytes_read = bytes_read
        IStore(self.__class__).add(self)
