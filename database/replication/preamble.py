#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Generate a preamble for slonik(1) scripts based on the current LPCONFIG.
"""

__metaclass__ = type
__all__ = []

import _pythonpath

import time
from optparse import OptionParser

from canonical.config import config
from canonical.database.sqlbase import connect
from canonical.launchpad import scripts

import replication.helpers

if __name__ == '__main__':
    parser = OptionParser()
    scripts.db_options(parser)
    (options, args) = parser.parse_args()
    if args:
        parser.error("Too many arguments")
    scripts.execute_zcml_for_scripts(use_web_security=False)

    con = connect(options.dbuser)
    print '# slonik(1) preamble generated %s' % time.ctime()
    print '# LPCONFIG=%s' % config.instance_name
    print
    print replication.helpers.preamble(con)

