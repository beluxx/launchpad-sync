# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Watch a log file and wait until it has grown in size."""

__metaclass__ = type
__all__ = [
    'LogWatcher',
    ]


import os
import time
import errno
import datetime

from Mailman.mm_cfg import LOG_DIR

try:
    # Python 2.5
    SEEK_END = os.SEEK_END
except AttributeError:
    # Python 2.4
    SEEK_END = 2


LOG_GROWTH_WAIT_INTERVAL = datetime.timedelta(seconds=5)
SECONDS_TO_SNOOZE = 0.1


class LogWatcher:
    """Watch logs/xmlrpc and wait until a pattern has been seen.

    You MUST open the LogWatcher before any data you're interested in could
    get written to the log.
    """
    def __init__(self, filename='xmlrpc'):
        # Import this here since sys.path isn't set up properly when this
        # module is imported.
        # pylint: disable-msg=F0401
        self._log_path = os.path.join(LOG_DIR, filename)

    def _line_feeder(self):
        """Iterate over all the lines of the file."""
        while True:
            try:
                log_file = open(self._log_path)
            except IOError, error:
                if error.errno == errno.ENOENT:
                    # If the file does not yet exist, act just like EOF.
                    yield ''
                raise
            else:
                # Ignore anything that's already in the file.
                log_file.seek(0, SEEK_END)
                break
        while True:
            yield log_file.readline()

    def _wait(self, landmark):
        """Wait until the landmark string has been seen.

        'landmark' must appear on a single line.  Comparison is done with 'in'
        on each line of the file.
        """
        until = datetime.datetime.now() + LOG_GROWTH_WAIT_INTERVAL
        line_feeder = self._line_feeder()
        while True:
            line = line_feeder.next()
            if landmark in line:
                # Return None on success for doctest convenience.
                return None
            if datetime.datetime.now() > until:
                return 'Timed out'
            time.sleep(SECONDS_TO_SNOOZE)

    def wait_for_create(self, team_name):
        """Wait for the list creation message."""
        return self._wait('[%s] create/reactivate: success' % team_name)

    def wait_for_resynchronization(self, team_name):
        return self._wait('[%s] resynchronize: success' % team_name)

    def wait_for_deactivation(self, team_name):
        return self._wait('[%s] deactivate: success' % team_name)

    def wait_for_reactivation(self, team_name):
        return self._wait('[%s] reactivate: success' % team_name)

    def wait_for_modification(self, team_name):
        return self._wait('[%s] modify: success' % team_name)

    def wait_for_membership_changes(self, team_name):
        return self._wait('Membership changes for: %s' % team_name)

    def wait_for_membership_updates(self, team_name):
        return self._wait('Membership updates for: %s' % team_name)

    def wait_for_discard(self, message_id):
        return self._wait('Message discarded, msgid: <%s>' % message_id)

    def wait_for_hold(self, message_id):
        return self._wait('Holding message for LP approval: <%s>'
                              % message_id)

    def wait_for_mbox_delivery(self, message_id):
        return self._wait('msgid: <%s>')

    def wait(self):
        # XXX REMOVE ME
        return self._wait('')
