#!/bin/sh
#
# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This script performs nightly chores. It should be run from
# cron as the launchpad user once a day. Typically the output
# will be sent to an email address for inspection.


LOGDIR=$1
LOGFILE=$LOGDIR/nightly.log

LOCK=/var/lock/launchpad_nightly.lock
if ! lockfile -r0 -l 259200 $LOCK; then
    echo "$(date): Unable to grab $LOCK lock - aborting" | tee -a "$LOGFILE"
    ps fuxwww
    exit 1
fi

if ! cd "$(dirname "$0")"; then
    echo "$(date): Unable to change directory to $(dirname "$0") - aborting" | tee -a "$LOGFILE"
    exit 1
fi

echo "$(date): Grabbed lock" >> "$LOGFILE"

echo "$(date): Expiring memberships" >> "$LOGFILE"
./flag-expired-memberships.py -q --log-file=DEBUG:"$LOGDIR/flag-expired-memberships.log"

echo "$(date): Allocating revision karma" >> "$LOGFILE"
./allocate-revision-karma.py -q --log-file=DEBUG:"$LOGDIR/allocate-revision-karma.log"

echo "$(date): Recalculating karma" >> "$LOGFILE"
./foaf-update-karma-cache.py -q --log-file=INFO:"$LOGDIR/foaf-update-karma-cache.log"

echo "$(date): Updating cached statistics" >> "$LOGFILE"
./update-stats.py -q --log-file=DEBUG:"$LOGDIR/update-stats.log"

echo "$(date): Expiring questions" >> "$LOGFILE"
./expire-questions.py -q --log-file=DEBUG:"$LOGDIR/expire-questions.log"

echo "$(date): Updating bugtask target name caches" >> "$LOGFILE"
./update-bugtask-targetnamecaches.py -q --log-file=DEBUG:"$LOGDIR/update-bugtask-targetnamecaches.log"

echo "$(date): Updating personal standings" >> "$LOGFILE"
./update-standing.py -q --log-file=DEBUG:"$LOGDIR/update-standing.log"

echo "$(date): Updating CVE database" >> "$LOGFILE"
./update-cve.py -q --log-file=DEBUG:"$LOGDIR/update-cve.log"

echo "$(date): Removing lock" >> "$LOGFILE"
rm -f $LOCK
