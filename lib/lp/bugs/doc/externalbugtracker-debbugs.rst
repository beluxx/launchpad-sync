===========================
ExternalBugTracker: DebBugs
===========================

Differently from Bugzilla, debbugs watch syncing is done by reading from
a local database, so we can use a real class for testing: we just need
to point it to our test debbugs db. Let's set up the db location for our
test:

    >>> import os.path
    >>> from lp.services.config import config
    >>> from lp.bugs.tests import __file__
    >>> test_db_location = os.path.join(
    ...     os.path.dirname(__file__), "data/debbugs_db"
    ... )

You can specify the db_location explicitly:

    >>> from lp.bugs.externalbugtracker import BATCH_SIZE_UNLIMITED, DebBugs
    >>> from lp.testing.layers import LaunchpadZopelessLayer
    >>> txn = LaunchpadZopelessLayer.txn
    >>> external_debbugs = DebBugs(
    ...     "http://example.com/", db_location=test_db_location
    ... )
    >>> external_debbugs.db_location == test_db_location
    True

Or, if we create a DebBugs instance without specifying a db location, it
will use the config value:

    >>> external_debbugs = DebBugs("http://example.com/")
    >>> external_debbugs.db_location == config.malone.debbugs_db_location
    True

DebBugs, of course, implements IExternalBugTracker.

    >>> from lp.bugs.interfaces.externalbugtracker import IExternalBugTracker
    >>> from lp.testing import verifyObject

    >>> verifyObject(IExternalBugTracker, external_debbugs)
    True

Because we keep a local copy of the DebBugs database we don't need to
worry about batching bug watch updates for performance reasons, so
DebBugs instances don't have a batch_size limit.

    >>> external_debbugs.batch_size == BATCH_SIZE_UNLIMITED
    True


Retrieving bug status from the debbugs database
===============================================

The retrieval of the remote status is done through the
getRemoteStatus() method. If we pass a bug number that doesn't exist in
the debbugs db, BugNotFound is raised.

    >>> external_debbugs.getRemoteStatus("42")
    Traceback (most recent call last):
    ...
    lp.bugs.externalbugtracker.base.BugNotFound: 42

If we pass a non-integer bug id, InvalidBugId is raised.

    >>> external_debbugs.getRemoteStatus("foo")
    Traceback (most recent call last):
    ...
    lp.bugs.externalbugtracker.base.InvalidBugId:
    Debbugs bug number not an integer: foo

The debbugs database has two subdirectories in it. The db-h directory
contains current bugs, while the archive contains older bugs that have
been moved there manually. The DebBugs wrapper fetches bugs from them
transparently. Bug 237001 lives in db-h:

    >>> external_debbugs.getRemoteStatus("237001")
    'open normal'

Bug 563 resides in the archive. It is also fetchable:

    >>> external_debbugs.getRemoteStatus("563")
    'done normal'


Getting the time
================

We don't have access to the Debian server's exact time, but we trust it
being correct.

    >>> external_debbugs.getCurrentDBTime()
    datetime.datetime(...)


Checking debbugs bug watches
============================

    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerSet
    >>> debbugs = getUtility(IBugTrackerSet).getByName("debbugs")
    >>> bug_watches = list(debbugs.watches_needing_update)
    >>> len(bug_watches)
    0

It looks as though there are no bug watches needing to be updated.
That's because the check for whether a bug watch needs to be updated
looks at its next_check field, which is None by default. Updating the
bug watches should solve that problem.

    >>> from datetime import datetime, timezone
    >>> for watch in debbugs.watches:
    ...     watch.next_check = datetime.now(timezone.utc)
    ...

    >>> bug_watches = list(debbugs.watches_needing_update)
    >>> len(bug_watches)
    5

Now there are some watches to update we can run the update against them.
The importing of comments, which is controlled by a configuration
option, is disabled here and will be tested later.

    >>> transaction.commit()

    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.bugs.scripts.checkwatches import CheckwatchesMaster
    >>> bug_watch_updater = CheckwatchesMaster(txn, logger=FakeLogger())
    >>> external_debbugs.sync_comments = False
    >>> bug_watch_ids = sorted([bug_watch.id for bug_watch in bug_watches])
    >>> bug_watch_updater.updateBugWatches(external_debbugs, bug_watches)
    INFO Updating 5 watches for 5 bugs on http://...

    >>> from lp.bugs.interfaces.bugwatch import IBugWatchSet
    >>> for bug_watch_id in bug_watch_ids:
    ...     bug_watch = getUtility(IBugWatchSet).get(bug_watch_id)
    ...     print("%s: %s" % (bug_watch.remotebug, bug_watch.remotestatus))
    ...
    280883: done grave woody security
    304014: open important
    327452: done critical patch security
    327549: open important security
    308994: open important

The next_check value for all the watches got set to null when they
were updated, so there are no watches left needing an update.

    >>> flush_database_updates()
    >>> watches = debbugs.watches_needing_update
    >>> watches.count()
    0

And the linked bugtasks got updated:

    >>> import operator
    >>> bugtasks = []
    >>> for bug_watch in bug_watches:
    ...     bugtasks += list(bug_watch.bugtasks)
    ...
    >>> for bugtask in sorted(bugtasks, key=operator.attrgetter("id")):
    ...     print(
    ...         bugtask.bug.id,
    ...         bugtask.bugtargetname,
    ...         bugtask.status.title,
    ...         end=" ",
    ...     )
    ...     print(bugtask.importance.title)
    ...
    1 mozilla-firefox (Debian) New Unknown
    3 mozilla-firefox (Debian Sarge) New Unknown
    7 evolution (Debian) Fix Released Unknown
    15 thunderbird New Unknown

Sometimes the severity field is missing in the bug summary. That will
cause importance to be set to medium, equivalent to the default normal
severity in debbugs.

    >>> import email
    >>> with open(
    ...     os.path.join(test_db_location, "db-h", "01", "237001.summary")
    ... ) as summary_file:
    ...     summary = email.message_from_file(summary_file)
    >>> "Severity" not in summary
    True

    >>> external_debbugs.getRemoteStatus("237001")
    'open normal'


Debbugs status conversions
==========================

Let's take closer look at the status conversion. Debbugs has basically
only two statuses, 'open' and 'done', so in order to get a more fine
grained mapping to Malone statuses, we need to look at the tags as
well. The most simple mapping is from 'done', in debbugs it means that
the bug has been fixed and a new package with the fix has been
uploaded, so it maps to 'Fix Released.

    >>> print(external_debbugs.convertRemoteStatus("done normal").title)
    Fix Released

If the status is simply 'open', we map it to 'New', since
there's no way of knowing if the bug is confirmed or not.

    >>> print(external_debbugs.convertRemoteStatus("open normal").title)
    New

If the 'wontfix' tag is present we map it to "Won't Fix". The 'wontfix'
tag takes precedence over the confirmed tags (help, confirmed, upstream,
fixed-upstream) since 'wontfix' is the state after confirmed. The 'wontfix'
tag also takes precedence over the fix-committed tags (pending, fixed,
fixed-in-experimental) since the malone status will correctly change to
fix-released when the debbugs status changes to 'done', so a nonsensical
combination of 'fixed' & 'wontfix' tags will only affect the malone status
temporarily.

    >>> print(
    ...     external_debbugs.convertRemoteStatus(
    ...         "open normal pending fixed fixed-in-experimental"
    ...         " wontfix help confirmed upstream fixed-upstream"
    ...     ).title
    ... )
    Won't Fix

If the 'moreinfo' tag is present, we map the status to 'Needs Info'.

    >>> print(
    ...     external_debbugs.convertRemoteStatus("open normal moreinfo").title
    ... )
    Incomplete

Of course, if the 'moreinfo' tag is present and the status is 'done',
we still map to 'Fix Released'.

    >>> print(
    ...     external_debbugs.convertRemoteStatus("done normal moreinfo").title
    ... )
    Fix Released

If the 'help' tag is present, it means that the maintainer is
requesting help with the bug, so it's most likely a confirmed bug.

    >>> print(external_debbugs.convertRemoteStatus("open normal help").title)
    Confirmed

The 'pending' tag means that a fix is about to be uploaded, so it maps
to 'Fix Committed'.

    >>> print(
    ...     external_debbugs.convertRemoteStatus("open normal pending").title
    ... )
    Fix Committed

The 'fixed' tag means that the bug has been either fixed or work around
somehow, but there's still an issue to be solved. We map it to 'Fix
Committed', so that people can see that a fix is available.

    >>> print(external_debbugs.convertRemoteStatus("open normal fixed").title)
    Fix Committed

If the bug is forwarded upstream, it should mean that it's a confirmed
bug.

    >>> print(
    ...     external_debbugs.convertRemoteStatus("open normal upstream").title
    ... )
    Confirmed

And of course, if the maintainer marked the bug as 'confirmed'.

    >>> print(
    ...     external_debbugs.convertRemoteStatus(
    ...         "open normal confirmed"
    ...     ).title
    ... )
    Confirmed


If it has been fixed upstream, it's definitely a confirmed bug.

    >>> print(
    ...     external_debbugs.convertRemoteStatus(
    ...         "open normal fixed-upstream"
    ...     ).title
    ... )
    Confirmed

If it has been fixed in experimental, we mark it 'Fix Committed' until
the fix has reached the unstable distribution.

    >>> print(
    ...     external_debbugs.convertRemoteStatus(
    ...         "open normal fixed-in-experimental"
    ...     ).title
    ... )
    Fix Committed

All other tags we map to 'New'.

    >>> print(
    ...     external_debbugs.convertRemoteStatus(
    ...         "open normal unreproducible lfs woody"
    ...     ).title
    ... )
    New

If we pass in a malformed status string an UnknownRemoteStatusError will
be raised.

    >>> print(external_debbugs.convertRemoteStatus("open"))
    Traceback (most recent call last):
      ...
    lp.bugs.externalbugtracker.base.UnknownRemoteStatusError: open


Importing bugs
==============

The Debbugs ExternalBugTracker can import a Debian bug into Launchpad.

    >>> from lp.testing import verifyObject
    >>> from lp.bugs.interfaces.externalbugtracker import ISupportsBugImport
    >>> verifyObject(ISupportsBugImport, external_debbugs)
    True

The bug reporter gets taken from the From field in the debbugs bug
report.

    >>> with open(
    ...     os.path.join(test_db_location, "db-h", "35", "322535.report")
    ... ) as report_file:
    ...     report = email.message_from_file(report_file)
    >>> print(report["From"])
    Moritz Muehlenhoff <jmm@inutil.org>

    >>> name, address = external_debbugs.getBugReporter("322535")
    >>> print(name)
    Moritz Muehlenhoff
    >>> print(address)
    jmm@inutil.org

The getBugSummaryAndDescription method reads the bug report from the
debbugs db, and returns the debbugs subject as the summary, and the
description as the description.

    >>> print(report["Subject"])
    evolution: Multiple format string vulnerabilities in Evolution

    >>> print(report.get_payload(decode=True).decode())
    Package: evolution
    Severity: grave
    Tags: security
    <BLANKLINE>
    Multiple exploitable format string vulnerabilities have been found in
    Evolution. Please see
    http://www.securityfocus.com/archive/1/407789/30/0/threaded
    for details. 2.3.7 fixes all these issues.
    ...

    >>> summary, description = external_debbugs.getBugSummaryAndDescription(
    ...     "322535"
    ... )
    >>> print(summary)
    evolution: Multiple format string vulnerabilities in Evolution

    >>> print(description)
    Package: evolution
    Severity: grave
    Tags: security
    <BLANKLINE>
    Multiple exploitable format string vulnerabilities have been found in
    Evolution. Please see
    http://www.securityfocus.com/archive/1/407789/30/0/threaded
    for details. 2.3.7 fixes all these issues.
    ...

Which package to file the bug against is determined by the
getBugTargetName() method.

    >>> print(external_debbugs.getBugTargetName("322535"))
    evolution


Importing Comments
==================

Along with importing debian bug reports, comments on those bug reports
can also be imported. The DebBugs class implements the
ISupportsCommentImport interface.

    >>> from lp.bugs.externalbugtracker import get_external_bugtracker
    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> from lp.bugs.interfaces.externalbugtracker import (
    ...     ISupportsCommentImport,
    ... )
    >>> from lp.bugs.tests.externalbugtracker import new_bugtracker
    >>> external_debbugs = get_external_bugtracker(
    ...     new_bugtracker(BugTrackerType.DEBBUGS)
    ... )

    >>> ISupportsCommentImport.providedBy(external_debbugs)
    True

ISupportsCommentImport defines four methods: getCommentIds(),
fetchComments(), getPosterForComment() and getMessageForComment().
DebBugs implements all of these.

    >>> from lp.bugs.tests.externalbugtracker import (
    ...     TestDebBugs,
    ...     TestDebianBug,
    ... )
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> bug = getUtility(IBugSet).get(4)
    >>> bug_watch = bug.addWatch(
    ...     debbugs, "1234", getUtility(ILaunchpadCelebrities).janitor
    ... )
    >>> external_debbugs = TestDebBugs(
    ...     "http://example.com/",
    ...     {"1234": TestDebianBug(package="evolution", id=1234)},
    ... )

getCommentIds() will return a list of the comment IDs for a given remote
bug. DebBugs comment IDs are RFC822 message IDs.

    >>> comment_ids = external_debbugs.getCommentIds(bug_watch.remotebug)
    >>> print(comment_ids)
    ['<20040309081430.98BF411EE67@tux>']

However, it will only return IDs for comments which can actually be
imported. Comments which have no usable date will not be imported.

    >>> external_debbugs.debbugs_db._data_file = (
    ...     "debbugs-comment-with-no-date.txt"
    ... )

    >>> comment_ids = external_debbugs.getCommentIds(bug_watch.remotebug)
    >>> print(comment_ids)
    []

getCommentIds() will only return a given comment ID once, even if that
comment ID exists several times in the DebBugs comment log. To
demonstrate this we'll use a data file that contains two copies of the
same comment.

    >>> external_debbugs.debbugs_db._data_file = (
    ...     "debbugs-duplicate-comment-ids.txt"
    ... )

If we query the DebBugs database directly we'll see that there are two
copies of the same comment.

    >>> debian_bug = external_debbugs._findBug(bug_watch.remotebug)
    >>> for comment in debian_bug.comments:
    ...     comment_email = email.message_from_bytes(comment)
    ...     print(comment_email["message-id"])
    ...
    <20040309081430.98BF411EE67@tux>
    <20040309081430.98BF411EE67@tux>

However, getCommentIds() will only return the comment ID once.

    >>> comment_ids = external_debbugs.getCommentIds(bug_watch.remotebug)
    >>> print(comment_ids)
    ['<20040309081430.98BF411EE67@tux>']

The debbugs implementation of fetchComments() doesn't actually do
anything, since DebBugs comments are stored locally and there is no need
to pre-fetch them. It exists, nevertheless, so that
CheckwatchesMaster.importBugComments() can call it.

    >>> external_debbugs.fetchComments(bug_watch, comment_ids)

getPosterForComment() will return a tuple of displayname, email for a
given comment ID.

    >>> comment_id = comment_ids[0]
    >>> poster_name, poster_email = external_debbugs.getPosterForComment(
    ...     bug_watch.remotebug, comment_id
    ... )
    >>> print("%s <%s>" % (poster_name, poster_email))
    Teun Vink <teun@tux.office.luna.net>

getMessageForComment() will return an imported comment as a Launchpad
Message. It requires a Person instance to be used as the Message's
owner, so we'll turn Teun Vink into a Person.

    >>> from lp.registry.interfaces.person import (
    ...     IPersonSet,
    ...     PersonCreationRationale,
    ... )
    >>> poster = getUtility(IPersonSet).ensurePerson(
    ...     poster_email,
    ...     poster_name,
    ...     PersonCreationRationale.BUGIMPORT,
    ...     comment="when importing comments for %s." % bug_watch.title,
    ... )

    >>> message = external_debbugs.getMessageForComment(
    ...     bug_watch.remotebug, comment_id, poster
    ... )

    >>> print(message.owner.displayname)
    Teun Vink

    >>> print(message.text_contents)
    Things happen.

Where the DebBugs comment specifies a date in its Received header,
getMessageForComment will use that date as the date for the message it
returns rather than the one listed in the email's Date header. This is
because the Date header is set by the client and can't, therefore, be
trusted to be correct. The Received header is set by the server and is
therefore more likely to be accurate.

    >>> external_debbugs.debbugs_db._data_file = (
    ...     "debbugs-comment-with-received-date.txt"
    ... )

    >>> comment_ids = external_debbugs.getCommentIds(bug_watch.remotebug)
    >>> print(comment_ids)
    ['<yetanothermessageid@launchpad>']

    >>> external_debbugs.fetchComments(bug_watch, comment_ids)
    >>> message = external_debbugs.getMessageForComment(
    ...     bug_watch.remotebug, comment_ids[0], poster
    ... )

    >>> print(message.datecreated)
    2008-05-30 21:18:12+00:00

If we parse the comment manually we'll see that the message's
datecreated comes not from the Date header but from the Received header.

    >>> from lp.bugs.tests.externalbugtracker import read_test_file
    >>> parsed_message = email.message_from_bytes(
    ...     read_test_file("debbugs-comment-with-received-date.txt").encode(
    ...         "UTF-8"
    ...     )
    ... )

    >>> print(parsed_message["date"])
    Fri, 14 Dec 2007 18:54:30 +0000

    >>> print(parsed_message["received"])
    (at 220301) by example.com; 30 May 2008 21:18:12 +0000

However, if none of the Received headers don't match the hostname that
we have for the remote debbugs instance, getMessageForComment() will
default to using the Date header again.

    >>> external_debbugs.debbugs_db._data_file = (
    ...     "debbugs-comment-with-no-useful-received-date.txt"
    ... )

    >>> comment_ids = external_debbugs.getCommentIds(bug_watch.remotebug)

    >>> external_debbugs.fetchComments(bug_watch, comment_ids)
    >>> message = external_debbugs.getMessageForComment(
    ...     bug_watch.remotebug, comment_ids[0], poster
    ... )

    >>> print(message.datecreated)
    2007-12-14 18:54:30+00:00

    >>> parsed_message = email.message_from_bytes(
    ...     read_test_file("debbugs-comment-with-received-date.txt").encode(
    ...         "UTF-8"
    ...     )
    ... )

    >>> print(parsed_message["date"])
    Fri, 14 Dec 2007 18:54:30 +0000

    >>> print(parsed_message["received"])
    (at 220301) by example.com; 30 May 2008 21:18:12 +0000

DebBugs has a method, _getDateForComment(), which returns the correct
date for a given email.message.Message instance. This can be
demonstrated by instantiating Message with some test data and passing
the instance to _getDateForComment()

    >>> test_message = email.message.Message()

If the message has no Date or useful Received headers,
_getDateForComment() will return None.

    >>> print(external_debbugs._getDateForComment(test_message))
    None

If the message has only a Date header, that will be returned as the
correct date.

    >>> test_message["date"] = "Mon, 14 Jul 2008 21:10:10 +0100"
    >>> external_debbugs._getDateForComment(test_message)
    datetime.datetime(2008, 7, 14, 20, 10, 10, tzinfo=datetime.timezone.utc)

If we add a Received header that isn't related to the domain of the
current instance, the Date header will still have precedence.

    >>> test_message[
    ...     "received"
    ... ] = "by thiswontwork.com; Tue, 15 Jul 2008 09:12:11 +0100"
    >>> external_debbugs._getDateForComment(test_message)
    datetime.datetime(2008, 7, 14, 20, 10, 10, tzinfo=datetime.timezone.utc)

If there's a Received header that references the correct domain, the
date in that header will take precedence.

    >>> test_message[
    ...     "received"
    ... ] = "by example.com; Tue, 15 Jul 2008 10:20:11 +0100"
    >>> external_debbugs._getDateForComment(test_message)
    datetime.datetime(2008, 7, 15, 9, 20, 11, tzinfo=datetime.timezone.utc)


Pushing comments to DebBugs
---------------------------

The DebBugs ExternalBugTracker implements the ISupportsCommentPushing
interface, which allows checkwatches to use it to push Launchpad
comments back to the remote DebBugs instance.

    >>> from lp.bugs.interfaces.externalbugtracker import (
    ...     ISupportsCommentPushing,
    ... )
    >>> ISupportsCommentPushing.providedBy(external_debbugs)
    True

Since DebBugs manages bugs through email interchanges, pushing a comment
to a remote DebBugs instance is merely a case of sending an email to the
correct bug thread.

    >>> test_debian_bug = TestDebianBug(
    ...     summary="Example bug 1234",
    ...     package="evolution",
    ...     id=1234,
    ... )
    >>> external_debbugs = TestDebBugs(
    ...     "http://example.com/", {"1234": test_debian_bug}
    ... )

The addRemoteCommentMethod() takes three parameters: The remote bug to
which we want to push the comment, the body of the comment that we wish
to push and the rfc822msgid of the comment that we're pushing. It
returns the ID of the comment on the remote bugtracker, which in this
case will be the rfc822msgid that gets passed as a parameter.

    >>> transaction.commit()

    >>> print(
    ...     external_debbugs.addRemoteComment(
    ...         "1234",
    ...         "A little fermented curd will do the trick!",
    ...         "<123456@launchpad.net>",
    ...     )
    ... )
    <123456@launchpad.net>

We can look for the mail that would have been sent.

    >>> from lp.testing.mail_helpers import pop_notifications
    >>> [msg] = pop_notifications()
    >>> print(msg["X-Envelope-To"])
    1234@example.com

    >>> print(msg["Message-Id"])
    <123456@launchpad.net>
    >>> print(msg["To"])
    1234@example.com
    >>> print(msg["From"])
    debbugs@bugs.launchpad.net
    >>> print(msg["Subject"])
    Re: Example bug 1234
    >>> print(msg.get_payload(decode=True).decode("UTF-8"))
    A little fermented curd will do the trick!


Script for importing Debian bugs, linking them to Ubuntu
--------------------------------------------------------

There's a script called `import-debian-bugs.py`, which accepts a list of
bug numbers to be imported. It will link the bugs to the debbugs bug
tracker.

    >>> debbugs = getUtility(ILaunchpadCelebrities).debbugs
    >>> [bug.title for bug in debbugs.getBugsWatching("237001")]
    []
    >>> [bug.title for bug in debbugs.getBugsWatching("322535")]
    []
    >>> transaction.commit()

    # Make sane data to play this test.
    >>> from lp.testing.dbuser import lp_dbuser
    >>> from lp.registry.interfaces.distribution import IDistributionSet

    >>> with lp_dbuser():
    ...     debian = getUtility(IDistributionSet).getByName("debian")
    ...     evolution_dsp = debian.getSourcePackage("evolution")
    ...     ignore = factory.makeSourcePackagePublishingHistory(
    ...         distroseries=debian.currentseries,
    ...         sourcepackagename=evolution_dsp.sourcepackagename,
    ...     )
    ...

    >>> import subprocess
    >>> process = subprocess.Popen(
    ...     "scripts/import-debian-bugs.py 237001 322535",
    ...     shell=True,
    ...     stdin=subprocess.PIPE,
    ...     stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE,
    ...     universal_newlines=True,
    ... )
    >>> (out, err) = process.communicate()
    >>> process.returncode
    0
    >>> print(err)
    INFO    Updating 1 watches for 1 bugs on http://bugs.debian.org
    INFO    Imported 4 comments for remote bug 237001...
    INFO    Imported debbugs #237001 as Launchpad bug #...
    INFO    Imported debbugs #322535 as Launchpad bug #...
    INFO    Committing the transaction.
    <BLANKLINE>

    >>> transaction.commit()
    >>> debbugs = getUtility(ILaunchpadCelebrities).debbugs
    >>> for bug in debbugs.getBugsWatching("237001"):
    ...     print(bug.title)
    ...
    evolution mail crashes on opening an email with a TIFF attachment
    >>> for bug in debbugs.getBugsWatching("322535"):
    ...     print(bug.title)
    ...
    evolution: Multiple format string vulnerabilities in Evolution

In addition to simply importing the bugs and linking it to the debbugs
bug, it will also create an Ubuntu task for the imported bugs. This will
allow Ubuntu triagers to go through all the imported bugs and decide
whether they affects Ubuntu.

    >>> [imported_bug] = debbugs.getBugsWatching("237001")
    >>> for bugtask in imported_bug.bugtasks:
    ...     print("%s: %s" % (bugtask.bugtargetname, bugtask.status.name))
    ...
    evolution (Ubuntu): NEW
    evolution (Debian): NEW


Importing bugs twice
....................

If a Debian bug already exists in Launchpad (i.e it has a bug watch), it
won't be imported again. A warning is logged so that the person running
the script gets notified about it.

    >>> from lp.bugs.scripts.importdebianbugs import import_debian_bugs
    >>> from lp.services.log.logger import FakeLogger
    >>> [bug.id for bug in debbugs.getBugsWatching("304014")]
    [1]
    >>> import_debian_bugs(["304014"], logger=FakeLogger())
    WARNING Not importing debbugs #304014, since it's already
            linked from LP bug(s) #1.
    >>> [bug.id for bug in debbugs.getBugsWatching("304014")]
    [1]


Getting the remote product for a bug
====================================

We can get the remote product for a bug by calling getRemoteProduct() on
a DebBugs instance. In actual fact this is a wrapper around
getBugTargetName(), since the package in DebBugs is a "remote product"
in Launchpad.

    >>> external_debbugs = DebBugs(
    ...     "http://example.com/", db_location=test_db_location
    ... )

    >>> print(external_debbugs.getRemoteProduct("237001"))
    evolution

Trying to call getRemoteProduct() on a bug that doesn't exist will raise
a BugNotFound error.

    >>> print(external_debbugs.getRemoteProduct("42"))
    Traceback (most recent call last):
      ...
    lp.bugs.externalbugtracker.base.BugNotFound: 42
