# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for the checkwatches.py cronscript."""

__metaclass__ = type


from logging import getLogger
import socket

from zope.component import getUtility

from canonical.database.constants import UTC_NOW
from canonical.launchpad.components import externalbugtracker
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IBugTrackerSet)
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import (
    setupInteraction, endInteraction)


class BugWatchUpdater(object):
    """Takes responsibility for updating remote bug watches."""

    def __init__(self, txn, log=None):
        if log is None:
            self.log = getLogger()
        else:
            self.log = log
        self.txn = txn

    def _login(self):
        """Set up an interaction as the Bug Watch Updater"""
        auth_utility = getUtility(IPlacelessAuthUtility)
        setupInteraction(
            auth_utility.getPrincipalByLogin('bugwatch@bugs.launchpad.net'),
            login='bugwatch@bugs.launchpad.net')

    def _logout(self):
        """Tear down the Bug Watch Updater Interaction."""
        endInteraction()

    def updateBugTrackers(self):
        """Update all the bug trackers that have watches pending."""
        ubuntu_bugzilla = getUtility(ILaunchpadCelebrities).ubuntu_bugzilla

        # Set up an interaction as the Bug Watch Updater since the
        # notification code expects a logged in user.
        self._login()

        for bug_tracker in getUtility(IBugTrackerSet):
            self.txn.begin()
            # Save the url for later, since we might need it to report an
            # error after a transaction has been aborted.
            bug_tracker_url = bug_tracker.baseurl
            try:
                if bug_tracker == ubuntu_bugzilla:
                    # XXX: 2007-09-11 Graham Binns
                    #      We automatically ignore the Ubuntu Bugzilla
                    #      here as all its bugs have been imported into
                    #      Launchpad. Ideally we would have some means
                    #      to identify all bug trackers like this so
                    #      that hard-coding like this can be genericised
                    #      (Bug 138949).
                    self.log.info(
                        "Skipping updating Ubuntu Bugzilla watches.")
                else:
                    self.updateBugTracker(bug_tracker)
                self.txn.commit()
            except (KeyboardInterrupt, SystemExit):
                # We should never catch KeyboardInterrupt or SystemExit.
                raise
            except:
                # If something unexpected goes wrong, we log it and
                # continue: a failure shouldn't break the updating of
                # the other bug trackers.
                self.log.error(
                    "An exception was raised when updating %s" %
                    bug_tracker_url,
                    exc_info=True)
                self.txn.abort()
        self._logout()

    def _getExternalBugTracker(self, bug_tracker):
        """Return an `ExternalBugTracker` instance for `bug_tracker`."""
        return externalbugtracker.get_external_bugtracker(
            self.txn, bug_tracker)

    def updateBugTracker(self, bug_tracker):
        """Updates the given bug trackers's bug watches."""
        # We only want to update each bugwatch once per day, so we limit
        # the watches that we need to update to those which haven't been
        # updated for 24 hours.
        bug_watches_to_update = (
            bug_tracker.getBugWatchesNeedingUpdate(24))

        try:
            remotesystem = self._getExternalBugTracker(bug_tracker)
        except externalbugtracker.UnknownBugTrackerTypeError, error:
            # We update all the bug watches to reflect the fact that
            # this error occurred. We also update their last checked
            # date to ensure that they don't get checked for another
            # 24 hours (see above).
            error_type = (
                externalbugtracker.get_bugwatcherrortype_for_error(error))
            for bug_watch in bug_watches_to_update:
                bug_watch.last_error_type = error_type
                bug_watch.lastchecked = UTC_NOW

            self.log.info(
                "ExternalBugtracker for BugTrackerType '%s' is not "
                "known." % (error.bugtrackertypename))
        else:
            if bug_watches_to_update.count() > 0:
                try:
                    remotesystem.updateBugWatches(bug_watches_to_update)
                except externalbugtracker.BugWatchUpdateError, error:
                    self.log.error(str(error))
                except socket.timeout:
                    # We don't want to die on a timeout, since most likely
                    # it's just a problem for this iteration. Nevertheless
                    # we log the problem.
                    self.log.error(
                        "Connection timed out when updating %s" %
                        bug_tracker.baseurl)
                    self.txn.abort()
            else:
                self.log.info(
                    "No watches to update on %s" % bug_tracker.baseurl)

