ExternalBugTracker: Issuezilla and other Freaks
===============================================

Bugzilla has a few variants out there in the wild, and we work hard to
support them all.

Issuezilla
----------

We support Issuezilla-style trackers. These trackers are essentially
modified (ancient) versions of Bugzilla; their XML elements have
slightly different names, and they lack the severity field. We pretend
Mozilla's Bugzilla is an Issuezilla instance here:

    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerSet

    >>> from lp.testing.layers import LaunchpadZopelessLayer
    >>> from lp.bugs.scripts.checkwatches import CheckwatchesMaster
    >>> from lp.bugs.tests.externalbugtracker import TestIssuezilla
    >>> from lp.services.log.logger import FakeLogger
    >>> txn = LaunchpadZopelessLayer.txn
    >>> mozilla_bugzilla = getUtility(IBugTrackerSet).getByName('mozilla.org')
    >>> issuezilla = TestIssuezilla(mozilla_bugzilla.baseurl)
    >>> transaction.commit()
    >>> with issuezilla.responses(post=False):
    ...     issuezilla._probe_version()
    (2, 11)
    >>> for bug_watch in mozilla_bugzilla.watches:
    ...     print("%s: %s %s" % (bug_watch.remotebug,
    ...         bug_watch.remotestatus, bug_watch.remote_importance))
    2000:
    123543:
    42: FUBAR BAZBAZ
    42: FUBAR BAZBAZ
    >>> transaction.commit()
    >>> bug_watch_updater = CheckwatchesMaster(txn, logger=FakeLogger())
    >>> with issuezilla.responses():
    ...     bug_watch_updater.updateBugWatches(
    ...         issuezilla, mozilla_bugzilla.watches)
    INFO Updating 4 watches for 3 bugs on https://bugzilla.mozilla.org
    INFO Didn't find bug '42' on https://bugzilla.mozilla.org
    (local bugs: 1, 2).

    >>> for bug_watch in mozilla_bugzilla.watches:
    ...     print("%s: %s %s" % (bug_watch.remotebug,
    ...         bug_watch.remotestatus, bug_watch.remote_importance))
    2000: RESOLVED FIXED LOW
    123543: ASSIGNED HIGH
    42: FUBAR BAZBAZ
    42: FUBAR BAZBAZ


Bugzilla prior to 2.11
----------------------

Old-style Bugzillas are quite similar to Issuezilla. Again we pretend
Mozilla.org's using this old version. Here's the scoop:

    >>> from lp.bugs.tests.externalbugtracker import TestOldBugzilla
    >>> old_bugzilla = TestOldBugzilla(mozilla_bugzilla.baseurl)

  a) The version is way old:

    >>> transaction.commit()
    >>> with old_bugzilla.responses(post=False):
    ...     old_bugzilla._probe_version()
    (2, 10)

  b) The tags are not prefixed with the bz: namespace:

    >>> bug_item_file = old_bugzilla._readBugItemFile()
    >>> "<bug_status>" in bug_item_file
    True
    >>> "<bug_id>" in bug_item_file
    True

We support them just fine:

    >>> remote_bugs = ['42', '123543']
    >>> with old_bugzilla.responses():
    ...     old_bugzilla.initializeRemoteBugDB(remote_bugs)
    >>> for remote_bug in remote_bugs:
    ...     print("%s: %s %s" % (
    ...         remote_bug,
    ...         old_bugzilla.getRemoteStatus(remote_bug),
    ...         old_bugzilla.getRemoteImportance(remote_bug)))
    42: RESOLVED FIXED LOW BLOCKER
    123543: ASSIGNED HIGH BLOCKER


Bugzilla oddities
-----------------

Some Bugzillas have some weird properties that we need to cater for:

    >>> from lp.bugs.tests.externalbugtracker import (
    ...     TestWeirdBugzilla)
    >>> weird_bugzilla = TestWeirdBugzilla(mozilla_bugzilla.baseurl)
    >>> transaction.commit()
    >>> with weird_bugzilla.responses(post=False):
    ...     weird_bugzilla._probe_version()
    (2, 20)

  a) The bug status tag is <bz:status> and not <bz:bug_status>

    >>> bug_item_file = weird_bugzilla._readBugItemFile()
    >>> print(bug_item_file)
    <li>...<bz:status>...

  b) The content is non-ascii:

    >>> six.ensure_text(bug_item_file).encode("ascii")
    Traceback (most recent call last):
    ...
    UnicodeEncodeError: 'ascii' codec can't encode character...

Yet everything still works as expected:

    >>> remote_bugs = ['2000', '123543']
    >>> with weird_bugzilla.responses():
    ...     weird_bugzilla.initializeRemoteBugDB(remote_bugs)
    >>> for remote_bug in remote_bugs:
    ...     print("%s: %s %s" % (
    ...         remote_bug,
    ...         weird_bugzilla.getRemoteStatus(remote_bug),
    ...         weird_bugzilla.getRemoteImportance(remote_bug)))
    2000: ASSIGNED HIGH BLOCKER
    123543: RESOLVED FIXED HIGH BLOCKER


Broken Bugzillas
----------------

What does /not/ work as expected is parsing Bugzillas which produce
invalid XML:

    >>> from lp.bugs.tests.externalbugtracker import (
    ...     TestBrokenBugzilla)
    >>> broken_bugzilla = TestBrokenBugzilla(mozilla_bugzilla.baseurl)
    >>> transaction.commit()
    >>> with broken_bugzilla.responses(post=False):
    ...     broken_bugzilla._probe_version()
    (2, 20)
    >>> "</foobar>" in broken_bugzilla._readBugItemFile()
    True

    >>> remote_bugs = ['42', '2000']
    >>> with broken_bugzilla.responses():
    ...     broken_bugzilla.initializeRemoteBugDB(remote_bugs)
    Traceback (most recent call last):
    ...
    lp.bugs.externalbugtracker.base.UnparsableBugData:
    Failed to parse XML description...

However, embedded control characters do not generate errors.

    >>> from lp.bugs.tests.externalbugtracker import (
    ...     AnotherBrokenBugzilla)
    >>> broken_bugzilla = AnotherBrokenBugzilla(mozilla_bugzilla.baseurl)
    >>> r"NOT\x01USED" in repr(broken_bugzilla._readBugItemFile())
    True

    >>> remote_bugs = ['42', '2000']
    >>> transaction.commit()
    >>> with broken_bugzilla.responses():
    ...     broken_bugzilla.initializeRemoteBugDB(remote_bugs) # no exception
