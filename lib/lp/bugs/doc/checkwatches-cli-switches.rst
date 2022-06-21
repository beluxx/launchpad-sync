Updating selected bug trackers
==============================

The CheckwatchesMaster class can be instructed to update only a subset of
bugtrackers. This is acheived by passing a list of bug tracker names to
the updateBugTrackers() method.

    >>> import transaction
    >>> from lp.services.database.sqlbase import cursor, sqlvalues
    >>> from lp.services.database.constants import UTC_NOW
    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.bugs.scripts.checkwatches import CheckwatchesMaster

We'll update all bugtrackers so that the test doesn't try to make any
external connections.

    >>> cur = cursor()
    >>> cur.execute("UPDATE BugWatch SET lastchecked=%s" %
    ...     sqlvalues(UTC_NOW))
    >>> transaction.commit()

    >>> updater = CheckwatchesMaster(transaction, logger=FakeLogger())

    >>> updater.updateBugTrackers(['debbugs', 'gnome-bugzilla'])
    DEBUG...No watches to update on http://bugs.debian.org
    DEBUG...No watches to update on http://bugzilla.gnome.org/bugs

If a bug tracker is disabled checkwatches won't try to update it.

    >>> from lp.testing.dbuser import lp_dbuser

    >>> with lp_dbuser():
    ...     login('foo.bar@canonical.com')
    ...     bug_tracker = factory.makeBugTracker('http://example.com')
    ...     bug_tracker.active = False
    ...     bug_tracker_name = bug_tracker.name

    >>> updater.updateBugTrackers([bug_tracker_name])
    DEBUG...Updates are disabled for bug tracker at http://example.com

This functionality can also be used with the checkwatches cronscript,
allowing a user to pass a list of bugtrackers to check at the command
line.

    >>> from lp.bugs.scripts.checkwatches import CheckWatchesCronScript
    >>> from lp.services.config import config

    >>> class TestCheckWatchesCronScript(CheckWatchesCronScript):
    ...
    ...     def __init__(self, name, dbuser=None, test_args=None):
    ...         super().__init__(name, dbuser, test_args)
    ...         self.txn = transaction
    ...
    ...     def handle_options(self):
    ...         self.logger = FakeLogger()

    >>> def run_cronscript_with_args(args):
    ...     # It may seem a bit weird to do ths rather than letting the
    ...     # LaunchpadScript code handle it, but doing that means that
    ...     # LayerIsolationErrors get raised as it leaves threads lying
    ...     # around.
    ...     login('bugwatch@bugs.launchpad.net')
    ...     transaction.commit()
    ...     checkwatches_cronscript = TestCheckWatchesCronScript(
    ...         "checkwatches", config.checkwatches.dbuser,
    ...         test_args=args)
    ...     checkwatches_cronscript.main()

    >>> run_cronscript_with_args([
    ...     '--bug-tracker=mozilla.org', '--bug-tracker=debbugs', '-v',
    ...     '--batch-size=10'])
    DEBUG Using a global batch size of 10
    DEBUG No watches to update on https://bugzilla.mozilla.org/
    DEBUG No watches to update on http://bugs.debian.org
    INFO  Time for this run: ... seconds.


Updating all watches from the command line
------------------------------------------

In order to update all bug watches from the checkwatches command line,
a user needs to pass the '--reset' option to the checkwatches cron script.

First, lets add some bug watches to the Savannah bug tracker to
demonstrate this.

    >>> import pytz
    >>> from datetime import datetime
    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerSet
    >>> from lp.testing.factory import LaunchpadObjectFactory

    >>> factory = LaunchpadObjectFactory()
    >>> with lp_dbuser():
    ...     login('foo.bar@canonical.com')
    ...     savannah = getUtility(IBugTrackerSet).getByName('savannah')
    ...     for i in range(5):
    ...         bug_watch = factory.makeBugWatch(bugtracker=savannah)
    ...         bug_watch.lastchecked = datetime.now(pytz.timezone('UTC'))

    >>> run_cronscript_with_args(['-vvt', 'savannah', '--reset'])
    INFO Resetting 5 bug watches for bug tracker 'savannah'
    INFO Updating 5 watches on bug tracker 'savannah'
    INFO 'Unsupported Bugtracker' error updating http://savannah.gnu.org/:
    SAVANE
    INFO 0 watches left to check on bug tracker 'savannah'
    INFO Time for this run...


Getting help
------------

The help for the checkwatches cronscript explains the usage of the bug
tracker option fully.

    >>> import subprocess
    >>> process = subprocess.Popen(
    ...     ['cronscripts/checkwatches.py', '-h'],
    ...     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE, universal_newlines=True)
    >>> (out, err) = process.communicate()
    >>> print(out)
    Usage: checkwatches.py [options]
    <BLANKLINE>
    Options:
      ...
      -t BUG_TRACKER, --bug-tracker=BUG_TRACKER
                            Only check a given bug tracker. Specifying
                            more than one bugtracker using this option
                            will check all the bugtrackers specified...
      -b BATCH_SIZE, --batch-size=BATCH_SIZE
                            Set the number of watches to be checked per
                            bug tracker in this run. If BATCH_SIZE is 0,
                            all watches on the bug tracker that are
                            eligible for checking will be checked.
      --reset               Update all the watches on the bug tracker,
                            regardless of whether or not they need
                            checking.
      --jobs=JOBS           The number of simulataneous jobs to run, 1
                            by default.
    <BLANKLINE>
