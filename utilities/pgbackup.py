#!/usr/bin/env python
"""
Backup one or more PostgreSQL databases.
Suitable for use in crontab for daily backups.
"""

import sys
import os
import os.path
import stat
import subprocess
import logging
from datetime import datetime
from optparse import OptionParser

MB = float(1024*1024)

return_code = 0 # Return code of this script. Set to the most recent failed
                # system call's return code

def call(cmd, **kw):
    log.debug(' '.join(cmd))
    rv = subprocess.call(cmd, **kw)
    if rv != 0:
        global return_code
        return_code = rv
    return rv

def main(options, databases):
    #Need longer file names if this is used more than daily
    #today = datetime.now().strftime('%Y%m%d_%H:%M:%S')
    today = datetime.now().strftime('%Y%m%d')

    backup_dir = options.backup_dir
 
    for database in databases:
        dest =  os.path.join(backup_dir, '%s.%s.dump' % (database, today))
        cmd = [
            "/usr/bin/pg_dump",
            "-U", "postgres",
            "--format=c",
            "--compress=0",
            "--blobs",
            "--file=%s" % dest,
            database,
            ]
        # If the file already exists, it was from a dump that didn't
        # complete (because completed dumps are renamed during compression).
        # Remove it.
        if os.path.exists(dest):
            log.warn("%s already exists. Removing." % dest)
            os.unlink(dest)
        rv = call(cmd, stdin=subprocess.PIPE)
        if rv != 0:
            log.critical("Failed to backup %s (%d)" % (database, rv))
            continue
        size = os.stat(dest)[stat.ST_SIZE]

        bzdest = "%s.bz2" % dest
        # If the file already exists, it is from an older dump today.
        # We know we have a full, current dump so kill the old compressed one.
        if os.path.exists(bzdest):
            log.warn("%s already exists. Removing." % bzdest)
            os.unlink(bzdest)
        cmd = ["/usr/bin/bzip2", "-9", dest]
        rv = call(cmd, stdin=subprocess.PIPE)
        if rv != 0:
            log.critical("Failed to compress %s (%d)" % (database, rv))
            continue
        csize = os.stat(bzdest)[stat.ST_SIZE]

        log.info("Backed up %s (%0.2fMB/%0.2fMB)" % (
            database, size/MB, csize/MB,
            ))

if __name__ == '__main__':
    parser = OptionParser(
            usage="usage: %prog [options] database [database ..]"
            )
    parser.add_option("-v", "--verbose", dest="verbose", default=0,
            action="count")
    parser.add_option("-q", "--quiet", dest="quiet", default=0,
            action="count")
    parser.add_option("-d", "--dir", dest="backup_dir",
            default="/var/lib/postgres/backups")
    (options, databases) = parser.parse_args()
    if len(databases) == 0:
        parser.error("must specify at least one database")
    if not os.path.isdir(options.backup_dir):
        parser.error(
                "Incorrect --dir. %s does not exist or is not a directory" % (
                    options.backup_dir
                    )
                )

    # Setup our log
    log = logging.getLogger('pgbackup')
    hdlr = logging.StreamHandler(strm=sys.stderr)
    hdlr.setFormatter(logging.Formatter(
            fmt='%(asctime)s %(levelname)s %(message)s'
            ))
    log.addHandler(hdlr)
    verbosity = options.verbose - options.quiet
    if verbosity > 0:
        log.setLevel(logging.DEBUG)
    elif verbosity == 0: # Default
        log.setLevel(logging.INFO)
    elif verbosity == -1:
        log.setLevel(logging.WARN)
    elif verbosity < -1:
        log.setLevel(logging.ERROR)

    main(options, databases)
    sys.exit(return_code)
