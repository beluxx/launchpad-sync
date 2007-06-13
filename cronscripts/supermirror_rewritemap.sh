#!/bin/sh

RSYNC_FILE=/srv/launchpad.net/etc/supermirror_rewritemap.conf

if [ -f "$RSYNC_FILE" ]
then
    # This simply exports for us the RSYNC_PASSWORD
    # variable. We don't want it here because we don't
    # want that password exposed within RF
    . $RSYNC_FILE
else
    echo `date` "Supermirror config file not found, exiting"
    exit 1
fi

# We want to override any value that's been set so that
# when this script is run it always uses LPCONFIG=lpnet1
export LPCONFIG=lpnet1

cd  /srv/launchpad.net/production/launchpad/cronscripts

LOCK=/var/lock/smrewrite.lock
MAP=/tmp/new-sm-map

lockfile -l 600 ${LOCK}

python supermirror_rewritemap.py -q ${MAP} && rsync ${MAP} \
        launchpad@bazaar.launchpad.net::config/launchpad-lookup.txt

rm -f ${LOCK}
