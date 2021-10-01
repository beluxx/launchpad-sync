# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Script run from test_isolation.py to confirm transaction isolation
settings work. Note we need to use a non-default isolation level to
confirm that the changes are actually being made by the API calls."""

__all__ = []

import transaction

from lp.services.config import dbconfig
from lp.services.database.sqlbase import (
    cursor,
    disconnect_stores,
    )
from lp.services.scripts import execute_zcml_for_scripts


execute_zcml_for_scripts()


def check():
    cur = cursor()
    cur.execute("UPDATE Person SET homepage_content='foo' WHERE name='mark'")
    cur.execute("SHOW transaction_isolation")
    print(cur.fetchone()[0])

    transaction.abort()
    transaction.begin()

    cur = cursor()
    cur.execute("UPDATE Person SET homepage_content='bar' WHERE name='mark'")
    cur.execute("SHOW transaction_isolation")
    print(cur.fetchone()[0])

dbconfig.override(dbuser='launchpad_main', isolation_level='read_committed')
disconnect_stores()
check()

dbconfig.override(isolation_level='repeatable_read')
disconnect_stores()
check()
