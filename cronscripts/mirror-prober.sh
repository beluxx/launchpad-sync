#!/bin/sh
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This script runs the mirror prober scripts as the
# launchpad user every two hours. Typically the output
# will be sent to an email address for inspection.

# Only run this script on loganberry
THISHOST=`uname -n`
if [ "loganberry" != "$THISHOST" ]
then
        echo "This script must be run on loganberry."
        exit 1
fi

# Only run this as the launchpad user
USER=`whoami`
if [ "launchpad" != "$USER" ]
then
        echo "Must be launchpad user to run this script."
        exit 1
fi


export LPCONFIG=production
export http_proxy=http://squid.internal:3128/
export ftp_proxy=http://squid.internal:3128/

LOCK=/var/lock/launchpad_mirror_prober.lock
lockfile -r0 -l 259200 $LOCK
if [ $? -ne 0 ]; then
    echo Unable to grab $LOCK lock - aborting
    ps fuxwww
    exit 1
fi

cd /srv/launchpad.net/production/launchpad/cronscripts

echo '== Distribution mirror prober (archive)' `date` ==
python2.5 -S distributionmirror-prober.py --content-type=archive --max-mirrors=20

echo '== Distribution mirror prober (cdimage)' `date` ==
python2.5 -S distributionmirror-prober.py --content-type=cdimage --max-mirrors=30

rm -f $LOCK

