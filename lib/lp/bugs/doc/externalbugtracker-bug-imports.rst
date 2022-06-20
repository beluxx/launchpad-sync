ExternalBugTracker bug imports
==============================

Some ExternalBugTracker implementations support importing bugs from the
remote bug tracker into Launchpad. They indicate that they support doing
this by implementing ISupportsBugImport, and implement all the specified
methods.

    >>> from zope.interface import implementer
    >>> from lp.bugs.interfaces.externalbugtracker import ISupportsBugImport
    >>> from lp.bugs.externalbugtracker import (
    ...     ExternalBugTracker)
    >>> @implementer(ISupportsBugImport)
    ... class BugImportingExternalBugTracker(ExternalBugTracker):
    ...
    ...     _bugs = {}
    ...
    ...     def getBugReporter(self, remote_bug):
    ...         display_name, email = self._bugs[remote_bug]['reporter']
    ...         return display_name, email
    ...     def getBugSummaryAndDescription(self, remote_bug):
    ...         return (
    ...             "Sample summary %s" % remote_bug,
    ...             "Sample description %s." % remote_bug)
    ...     def getBugTargetName(self, remote_bug):
    ...         return self._bugs[remote_bug]['package']

    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.bugs.tests.externalbugtracker import (
    ...     new_bugtracker)
    >>> bugtracker = new_bugtracker(BugTrackerType.BUGZILLA)
    >>> external_bugtracker = BugImportingExternalBugTracker(
    ...     'http://example.com/')

When importing bugs, the reporter is automatically created in Launchpad,
if they don't exist.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> print(getUtility(IPersonSet).getByEmail('joe.bloggs@example.com'))
    None

The method that imports a bug is importBug(). In addition to the
ISupportBugImports external bug tracker, it requires the corresponding
IBugTracker in Launchpad, and the bug target, in which the bug should be
imported into, and the remote bug number. At the moment only
distributions are supported as the bug target.

    # Make sane data to play this test.
    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.testing.dbuser import lp_dbuser
    >>> from lp.testing.layers import LaunchpadZopelessLayer

    >>> with lp_dbuser():
    ...     debian = getUtility(IDistributionSet).getByName('debian')
    ...     evolution_dsp = debian.getSourcePackage('evolution')
    ...     ignore = factory.makeSourcePackagePublishingHistory(
    ...         distroseries=debian.currentseries,
    ...         sourcepackagename=evolution_dsp.sourcepackagename)

    >>> from lp.bugs.scripts.checkwatches import CheckwatchesMaster
    >>> debian = getUtility(IDistributionSet).getByName('debian')
    >>> external_bugtracker._bugs['3'] =  {
    ...     'package': 'evolution',
    ...     'reporter': ("Joe Bloggs", "joe.bloggs@example.com")}
    >>> transaction.commit()
    >>> bug_watch_updater = CheckwatchesMaster(
    ...     LaunchpadZopelessLayer.txn, logger=FakeLogger())
    >>> bug = bug_watch_updater.importBug(
    ...     external_bugtracker, bugtracker, debian, '3')

The summary and descriptions of the imported bugs are what was returned
by getBugSummaryAndDescription().

    >>> print(bug.title)
    Sample summary 3
    >>> print(bug.description)
    Sample description 3.

The bug reporter, as returned by getBugReporter(), got automatically created.

    >>> getUtility(IPersonSet).getByEmail(
    ...     'joe.bloggs@example.com', filter_status=False) is not None
    True
    >>> print(bug.owner.displayname)
    Joe Bloggs

Since they didn't have a Launchpad account before, they don't have a
preferred email address, and the one that is associated with their
account is marked as NEW, since we don't know whether it's valid.

    >>> from lp.services.identity.interfaces.emailaddress import (
    ...     IEmailAddressSet)
    >>> reporter_email_addresses = getUtility(IEmailAddressSet).getByPerson(
    ...     bug.owner)
    >>> for email_address in reporter_email_addresses:
    ...     print("%s: %s" % (email_address.email, email_address.status.name))
    joe.bloggs@example.com: NEW
    >>> print(bug.owner.preferredemail)
    None

    >>> bug.owner.creation_rationale.name
    'BUGIMPORT'
    >>> print(bug.owner.creation_comment)
    when importing bug #3 from http://...

No one got subscribed to the created bug, since the relevant people
already get email notifications via the external bug tracker.

    >>> [person.name for person in bug.getDirectSubscribers()]
    []

The bug got filed against the evolution package in Debian, and it has a
bug watch pointing to the original remote bug, so that the bug report is
kept in sync.

    >>> [added_task] = bug.bugtasks
    >>> print(added_task.bugtargetname)
    evolution (Debian)

    >>> print(added_task.bugwatch.bugtracker.name)
    bugzilla-checkwatches-1
    >>> print(added_task.bugwatch.remotebug)
    3


Non-existent source package
---------------------------

If a package doesn't exist in Launchpad already, it will be filed on the
distribution itself, with no source package specified. The package is
always included in the description of Debian bugs, so that information
isn't normally lost. A warning is also logged, so that the one running
the script gets notified about it.

    >>> external_bugtracker._bugs['5'] = {
    ...     'package': 'no-such-package',
    ...     'reporter': ("Joe Bloggs", "joe.bloggs@example.com")}
    >>> print(debian.getSourcePackage('no-such-package'))
    None
    >>> bug = bug_watch_updater.importBug(
    ...     external_bugtracker, bugtracker, debian, '5')
    WARNING Unknown debian package (#5 at http://...): no-such-package
    (OOPS-...)

    >>> [added_task] = bug.bugtasks
    >>> print(added_task.distribution.name)
    debian
    >>> print(added_task.sourcepackagename)
    None


Syncing status
--------------

After the bug watch has been created for the imported bug, the status is
not synced immediately. The status will be updated the next time all the
bug watches for this bug tracker gets updated. This is to avoid making
one request per imported bug.

    >>> added_task.status.name
    'NEW'
    >>> print(added_task.bugwatch.lastchecked)
    None


Reporter already registered in Launchpad
----------------------------------------

Even if the reporter of the bug has an account in Launchpad (and thus a
valid email address), they still won't be subscribed to the imported bug.

    >>> no_priv = getUtility(IPersonSet).getByName('no-priv')
    >>> no_priv.preferredemail is not None
    True
    >>> external_bugtracker._bugs['7'] = {
    ...     'package': 'evolution',
    ...     'reporter': ('Not Used', no_priv.preferredemail.email)}
    >>> bug = bug_watch_updater.importBug(
    ...     external_bugtracker, bugtracker, debian, '7')

    >>> print(bug.owner.name)
    no-priv
    >>> print(bug.owner.displayname)
    No Privileges Person

    >>> [person.name for person in bug.getDirectSubscribers()]
    []
