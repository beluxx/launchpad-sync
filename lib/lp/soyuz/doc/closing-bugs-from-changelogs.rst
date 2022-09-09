Closing bugs from changelogs
============================

When a package is uploaded to a distribution, a bug number can be
specified in the Launchpad-bugs-fixed header of the changes file.

The bug is closed at package acceptance time.  After processing queue items,
process-accepted.py attempts to close any open, valid bugs named in the
aforementioned header.  It will not close bugs for uploads to PPAs or to the
main distribution's "proposed" pocket.

All this is done by the function close_bugs_for_queue_item.  This document
describes the function in detail and demonstrates that process-accepted.py
calls it.

    >>> changes_template = """
    ... Format: 1.7
    ... Launchpad-bugs-fixed: %s
    ... """

The package uploads are associated with specific releases of the
package, but the bugs they reference may be filed on the generic
distribution package.

    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.testing.dbuser import switch_dbuser

    >>> login("no-priv@canonical.com")

    >>> switch_dbuser("launchpad")

    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> ubuntu_hoary = ubuntu.getSeries("hoary")

    >>> bug_params = CreateBugParams(
    ...     getUtility(ILaunchBag).user, "Test bug", "Test bug."
    ... )

The package source uploads are represented as PackageUpload items
that are associated with PackageUploadSource items and a changes
file. The only thing in the changes file that is used to close the bug
is the Launchpad-bugs-fixed header.

The PackageUploadSource items are linked to SourcePackageRelease
items, but for closing bugs the only thing that mattters is who uploaded
it, what package name is it, and to what distribution series it was
uploaded to.

First, let's define a helper function that adds a PackageUpload record
using the changes file template (changes_template) above with the
Launchpad-bugs-fixed header.  This is required so that we have some data
for close_bugs_for_queue_item to operate on.

    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> def add_package_upload(
    ...     source_release,
    ...     fixing_text,
    ...     pocket=PackagePublishingPocket.RELEASE,
    ...     archive=None,
    ...     distroseries=None,
    ... ):
    ...     """Create a PackageUpload record."""
    ...     changes = (changes_template % fixing_text).encode("UTF-8")
    ...     if distroseries is None:
    ...         distroseries = ubuntu_hoary
    ...     if archive is None:
    ...         archive = distroseries.main_archive
    ...     queue_item = distroseries.createQueueEntry(
    ...         archive=archive,
    ...         pocket=pocket,
    ...         changesfilename="%s.changes" % source_release.name,
    ...         changesfilecontent=changes,
    ...     )
    ...     queue_item.addSource(source_release)
    ...     return queue_item

Throughout this document we'll now create PackageUpload records for various
packages in the sample data (e.g. pmount, cdrkit) using this helper function.

Now we can make a bug and a package upload for pmount.

    >>> pmount_ubuntu = ubuntu.getSourcePackage("pmount")
    >>> pmount_release = pmount_ubuntu.getVersion(
    ...     "0.1-1"
    ... ).sourcepackagerelease

    >>> pmount_bug_id = pmount_ubuntu.createBug(bug_params).id

    >>> queue_item = add_package_upload(pmount_release, pmount_bug_id)

    # Need to commit the transaction so that the changes file can be
    # downloaded from the Librarian.  switch_dbuser takes care of this.
    >>> switch_dbuser(test_dbuser)

Right after the queue items have been processed by the publishing
scripts, close_bugs_for_queue_item() is called with the id of each queue item
that has been published. Passing a queue item with a Launchpad-bugs-fixed
header will close the specified bug.

    >>> from lp.bugs.interfaces.bug import IBugSet

    >>> def print_single_task_status(bug_id):
    ...     bug = getUtility(IBugSet).get(bug_id)
    ...     [task] = bug.bugtasks
    ...     return task.status.name
    ...

    >>> print_single_task_status(pmount_bug_id)
    'NEW'

    >>> from lp.soyuz.model.processacceptedbugsjob import (
    ...     close_bugs_for_queue_item,
    ... )
    >>> close_bugs_for_queue_item(queue_item)

    >>> print_single_task_status(pmount_bug_id)
    'FIXRELEASED'

The changelog associated with the SourcePackageRelease is automatically
added as a comment from the janitor.

    >>> switch_dbuser("launchpad")
    >>> pmount_bug = getUtility(IBugSet).get(pmount_bug_id)
    >>> last_comment = pmount_bug.messages[-1]
    >>> print(pmount_release.creator.displayname)
    Mark Shuttleworth
    >>> print(last_comment.owner.displayname)
    Launchpad Janitor

    >>> print(pmount_release.changelog_entry)
    pmount (0.1-1) hoary; urgency=low
    <BLANKLINE>
     * Fix description (Malone #1)
     * Fix debian (Debian #2000)
     * Fix warty (Warty Ubuntu #1)
    <BLANKLINE>
     -- Sample Person <test@canonical.com> Tue, 7 Feb 2006 12:10:08 +0300

    >>> print(last_comment.text_contents)
    This bug was fixed in the package pmount - 0.1-1
    <BLANKLINE>
    ---------------
    pmount (0.1-1) hoary; urgency=low
    <BLANKLINE>
     * Fix description (Malone #1)
     * Fix debian (Debian #2000)
     * Fix warty (Warty Ubuntu #1)
    <BLANKLINE>
     -- Sample Person <test@canonical.com> Tue, 7 Feb 2006 12:10:08 +0300

A bug notification is created for both the status change, and for the
comment addition. The both notifications will be batched together into a
single email later.

    >>> from lp.bugs.model.bugnotification import BugNotification
    >>> from lp.services.database.interfaces import IStore
    >>> notifications = (
    ...     IStore(BugNotification)
    ...     .find(BugNotification)
    ...     .order_by(BugNotification.id)
    ... )
    >>> for notification in list(notifications)[-2:]:
    ...     print(
    ...         "From %s:\n%s\n"
    ...         % (
    ...             notification.message.owner.displayname,
    ...             notification.message.text_contents,
    ...         )
    ...     )
    From Launchpad Janitor:
    ** Changed in: pmount (Ubuntu)
           Status: New => Fix Released
    <BLANKLINE>
    From Launchpad Janitor:
    This bug was fixed in the package pmount - 0.1-1
    <BLANKLINE>
    ---------------
    pmount (0.1-1) hoary; urgency=low
    <BLANKLINE>
     * Fix description (Malone #1)
     * Fix debian (Debian #2000)
     * Fix warty (Warty Ubuntu #1)
    <BLANKLINE>
     -- Sample Person <test@canonical.com> Tue, 7 Feb 2006 12:10:08 +0300
    <BLANKLINE>

If another upload claims to close the same bug (which is already
closed), no additional comment is added. This situation may occur when
packages are synced from Debian.

    >>> print_single_task_status(pmount_bug_id)
    'FIXRELEASED'
    >>> number_of_old_notifications = notifications.count()

    >>> close_bugs_for_queue_item(queue_item)

    >>> notifications = (
    ...     IStore(BugNotification)
    ...     .find(BugNotification)
    ...     .order_by(BugNotification.id)
    ... )
    >>> new_notifications = notifications[number_of_old_notifications:]
    >>> [
    ...     notification.message.text_contents
    ...     for notification in new_notifications
    ... ]
    []


Let's define another helper function that will compare a bug status,
call close_bugs_for_queue_item() and then check the status again.

    >>> def close_bugs_and_check_status(bug_id_list, queue_item):
    ...     """Close bugs, reporting status before and after."""
    ...     print("Before:")
    ...     for bug_id in bug_id_list:
    ...         print(print_single_task_status(bug_id))
    ...     switch_dbuser(test_dbuser)
    ...     close_bugs_for_queue_item(queue_item)
    ...     switch_dbuser("launchpad")
    ...     print("After:")
    ...     for bug_id in bug_id_list:
    ...         print(print_single_task_status(bug_id))
    ...


Uploads to pocket PROPOSED should not close bugs, see bug #125279 for
further information.  Here we upload a package, cdrkit, to the proposed pocket
for the ubuntu distro.  The bug status before and after calling
close_bugs_for_queue_item is "NEW".

    >>> cdrkit_ubuntu = ubuntu.getSourcePackage("cdrkit")
    >>> cdrkit_release = cdrkit_ubuntu.currentrelease.sourcepackagerelease

    >>> cdrkit_bug_id = cdrkit_ubuntu.createBug(bug_params).id

    >>> queue_item = add_package_upload(
    ...     cdrkit_release,
    ...     cdrkit_bug_id,
    ...     pocket=PackagePublishingPocket.PROPOSED,
    ... )

    >>> close_bugs_and_check_status([cdrkit_bug_id], queue_item)
    Before: NEW
    After: NEW

Similarly, uploads to the backports pocket will not close bugs. (See bug
#295621).

    >>> queue_item = add_package_upload(
    ...     cdrkit_release,
    ...     cdrkit_bug_id,
    ...     pocket=PackagePublishingPocket.BACKPORTS,
    ... )

    >>> close_bugs_and_check_status([cdrkit_bug_id], queue_item)
    Before: NEW
    After: NEW

Uploads to PPAs will not close bugs (see bug #137767).  Here we upload a
package, cdrkit, to cprov's PPA.  The bug status before and after calling
close_bugs_for_queue_item is "NEW".

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> arbitrary_ppa = getUtility(IPersonSet).getByName("cprov").archive
    >>> queue_item = add_package_upload(
    ...     cdrkit_release, cdrkit_bug_id, archive=arbitrary_ppa
    ... )

    >>> close_bugs_and_check_status([cdrkit_bug_id], queue_item)
    Before: NEW
    After: NEW

It's possible to specify more than one bug in the Launchpad-bugs-fixed
header, each will be marked as Fix Released. If a nonexistent bug,
'666', is specified, it's ignored.

    >>> pmount_bug_id = pmount_ubuntu.createBug(bug_params).id
    >>> another_pmount_bug_id = pmount_ubuntu.createBug(bug_params).id

    >>> fixing_text = "%d 666 %d" % (pmount_bug_id, another_pmount_bug_id)

    >>> queue_item = add_package_upload(pmount_release, fixing_text)
    >>> bug_list = [pmount_bug_id, another_pmount_bug_id]
    >>> close_bugs_and_check_status(bug_list, queue_item)
    Before: NEW NEW
    After: FIXRELEASED FIXRELEASED


process-accepted.py
-------------------

The closing of bugs are done in process-accepted.py, right after the
queue items have been processed.

    >>> switch_dbuser("launchpad")

    >>> queue_item = add_package_upload(pmount_release, fixing_text)
    >>> queue_item.setAccepted()

    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus

    >>> pmount_bug = getUtility(IBugSet).get(pmount_bug_id)
    >>> [pmount_task] = pmount_bug.bugtasks
    >>> pmount_task.transitionToStatus(
    ...     BugTaskStatus.CONFIRMED, pmount_task.distribution.owner
    ... )

    >>> another_pmount_bug = getUtility(IBugSet).get(another_pmount_bug_id)
    >>> [another_pmount_task] = another_pmount_bug.bugtasks
    >>> another_pmount_task.transitionToStatus(
    ...     BugTaskStatus.CONFIRMED, another_pmount_task.distribution.owner
    ... )


    >>> print_single_task_status(pmount_bug_id)
    'CONFIRMED'

    >>> print_single_task_status(another_pmount_bug_id)
    'CONFIRMED'

    >>> switch_dbuser(test_dbuser)

    >>> import os.path
    >>> import subprocess
    >>> from lp.services.config import config
    >>> script = os.path.join(config.root, "scripts/process-accepted.py")
    >>> process = subprocess.Popen(
    ...     [script, "ubuntu"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ... )
    >>> stdout, stderr = process.communicate()
    >>> process.returncode
    0

    >>> print_single_task_status(pmount_bug_id)
    'FIXRELEASED'

    >>> print_single_task_status(another_pmount_bug_id)
    'FIXRELEASED'
