==================
Upload Queue Pages
==================


Upload queue pages are designed to offer the ability to perform
control and visualisation over the current uploads queue.

Currently the queue page is only available for DistroSeries context.


The upload-admin role
=====================

In our sample data, Ubuntu's upload manager is "name12", who has the
rights to administer the queue for the four main components.  This
permissioning data has no web UI to administer it yet, so we'll create
a Zope interaction to show it:

    >>> login('foo.bar@canonical.com')
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.interfaces.archivepermission import (
    ...     IArchivePermissionSet,
    ...     )
    >>> permission_set = getUtility(IArchivePermissionSet)
    >>> main_archive = getUtility(IDistributionSet)['ubuntu'].main_archive
    >>> name12 = getUtility(IPersonSet).getByName('name12')
    >>> permissions = permission_set.componentsForQueueAdmin(
    ...     main_archive, name12)
    >>> from operator import attrgetter
    >>> for permission in sorted(permissions, key=attrgetter("id")):
    ...     print(permission.component.name)
    main
    restricted
    universe
    multiverse

    >>> logout()

Let's setup a browser with the defined upload-admin for future use.
(name12 is test@canonical.com)

    >>> upload_manager_browser = setupBrowser(
    ...       auth="Basic test@canonical.com:test")


Accessing the queues
====================

The link "View Uploads" is presented in Distrorelease page.

Viewing the current queue, by default the NEW queue.

    >>> anon_browser.open(
    ...     "http://launchpad.test/ubuntu/breezy-autotest/")
    >>> anon_browser.getLink("All uploads").click()

    >>> anon_browser.getControl(
    ...     name="queue_state", index=0).displayValue
    ['New']

    >>> def print_queue(contents):
    ...     queue_rows = find_tags_by_class(contents, "queue-row")
    ...     for row in queue_rows:
    ...         print(extract_text(row))

    >>> print_queue(anon_browser.contents)  # noqa
    Package             Version     Component Section Priority Sets Pocket  When
    netapplet...ddtp... -                                           Release 2006-...
    netapplet...dist... -                                           Release 2006-...
    alsa-utils (source) 1.0.9a-4... main      base    low           Release 2006-...
    netapplet (source)  0.99.6-1    main      web     low           Release 2006-...
    pmount (i386)       0.1-1                                       Release 2006-...
    moz...irefox (i386) 0.9                                         Release 2006-...

The package name in the results list is a clickable link to the changes
file for that upload.

    >>> print(anon_browser.getLink("netapplet-1.0.0.tar.gz"))
    <Link text='netapplet-1.0.0.tar.gz'
	  url='http://.../+upload/7/+files/netapplet-1.0.0.tar.gz'>

    >>> print(anon_browser.getLink("alsa-utils"))
    <Link text='alsa-utils'
	  url='http://.../+upload/4/+files/netapplet-1.0.0.tar.gz'>

(This link for alsa-utils is pointing at the librarian URL for
netapplet, because we have used its changes file for all the
PackageUpload records for the purposes of this doctest.)

We grant public access to all available queues, including the
UNAPPROVED one.

    >>> anon_browser.getControl(
    ...     name="queue_state", index=0).displayValue = ['Unapproved']
    >>> anon_browser.getControl("Update").click()
    >>> print_queue(anon_browser.contents)  # noqa
    Package             Version   Component Section  Priority Sets Pocket   When
    lang...-de (source) 1.0       main      trans... low           Proposed 2007-...
    netapplet...ddtp... -                                          Backp... 2006-...
    cnews (source)      1.0       main      base     low           Release  2006-...
    cnews (source)      1.0       main      base     low           Release  2006-...
    netapplet...(raw-translations) -                               Updates  2006-...

The results can be filtered matching source name, binary name or
custom-upload filename.

    >>> anon_browser.getControl(name="queue_text").value = 'language'
    >>> anon_browser.getControl("Update").click()
    >>> print_queue(anon_browser.contents)  # noqa
    Package             Version   Component Section  Priority Sets Pocket   When
    lang...-de (source) 1.0       main      trans... low           Proposed 2007-...

    >>> anon_browser.getControl(name="queue_text").value = 'netapplet'
    >>> anon_browser.getControl("Update").click()
    >>> print_queue(anon_browser.contents)  # noqa
    Package             Version   Component Section  Priority Sets Pocket   When
    netapplet...ddtp... -                                          Backp... 2006-...
    netapplet...(raw-translations) -                               Updates  2006-...

    >>> anon_browser.getControl(
    ...     name="queue_state", index=0).displayValue = ['New']
    >>> anon_browser.getControl(name="queue_text").value = 'pmount'
    >>> anon_browser.getControl("Update").click()
    >>> print_queue(anon_browser.contents)  # noqa
    Package             Version   Component Section  Priority Sets Pocket   When
    pmount (i386)       0.1-1                                      Release  2006-...

A source's package sets are listed in the queue. Since there are none in
the sample data, we'll first add some.

    >>> login('foo.bar@canonical.com')
    >>> from lp.soyuz.interfaces.packageset import IPackagesetSet
    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> hoary = ubuntu['hoary']
    >>> breezy_autotest = ubuntu['breezy-autotest']
    >>> pss = getUtility(IPackagesetSet)
    >>> desktop = pss.new(
    ...     u'desktop', u'Ubuntu Desktop', name12, breezy_autotest)
    >>> server = pss.new(u'server', u'Ubuntu Server', name12, breezy_autotest)
    >>> core = pss.new(u'core', u'Ubuntu Core', name12, breezy_autotest)
    >>> desktop.add([core])
    >>> desktop.addSources(['alsa-utils'])
    >>> server.addSources(['alsa-utils'])
    >>> core.addSources(['netapplet'])

Package sets from other series are not shown.

    >>> kubuntu = pss.new(u'kubuntu', u'Kubuntu', name12, hoary)
    >>> kubuntu.addSources(['alsa-utils'])
    >>> logout()

    >>> anon_browser.getControl(
    ...     name="queue_state", index=0).displayValue = ['New']
    >>> anon_browser.getControl(name="queue_text").value = ''
    >>> anon_browser.getControl("Update").click()
    >>> print_queue(anon_browser.contents)  # noqa
    Package             Version   Component Section  Priority Sets           Pocket  When
    netapplet...ddtp... -                                                    Release 2006-...
    netapplet...dist... -                                                    Release 2006-...
    alsa-utils (source) 1.0.9a-4... main      base    low     desktop server Release 2006-...
    netapplet (source)  0.99.6-1    main      web     low     core           Release 2006-...
    pmount (i386)       0.1-1                                                Release 2006-...
    moz...irefox (i386) 0.9                                                  Release 2006-...

    >>> login('foo.bar@canonical.com')
    >>> desktop.removeSources(['alsa-utils'])
    >>> server.removeSources(['alsa-utils'])
    >>> core.removeSources(['netapplet'])
    >>> logout()

Queue item filelist
===================

First set up some additional data to show in the listing: a package diff
and an extra, expired, source file.

    >>> import io
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.services.database.constants import UTC_NOW
    >>> from lp.services.librarian.interfaces.client import ILibrarianClient
    >>> from lp.soyuz.enums import PackageDiffStatus
    >>> login(ANONYMOUS)
    >>> old = main_archive.getPublishedSources(
    ...     name=u'alsa-utils', version='1.0.9a-4')[0].sourcepackagerelease
    >>> new = main_archive.getPublishedSources(
    ...     name=u'alsa-utils',
    ...     version='1.0.9a-4ubuntu1')[0].sourcepackagerelease
    >>> diff = removeSecurityProxy(old.requestDiffTo(
    ...     requester=name12, to_sourcepackagerelease=new))
    >>> diff.date_fulfilled = UTC_NOW
    >>> diff.status = PackageDiffStatus.COMPLETED
    >>> diff.diff_content = getUtility(ILibrarianClient).addFile(
    ...     'alsa-utils.diff.gz', 11, io.BytesIO(b'i am a diff'),
    ...     'application/gzipped-patch')
    >>> sprf = new.addFile(factory.makeLibraryFileAlias(
    ...     filename='alsa-utils_1.0.9a-4ubuntu1.diff.gz'))
    >>> removeSecurityProxy(sprf.libraryfile).content = None
    >>> logout()

Each queue item has a hidden 'filelist' section which is
toggled via javascript by clicking in the 'expand' arrow
image:

    >>> anon_browser.getControl(
    ...     name="queue_state", index=0).displayValue = ['New']
    >>> anon_browser.getControl(name="queue_text").value = ''
    >>> anon_browser.getControl("Update").click()

    >>> print(find_tag_by_id(anon_browser.contents, 'queue-4-icon').decode(
    ...     formatter='html'))
    <span class="expander-link" id="queue-4-icon">&nbsp;</span>

The 'filelist' is expanded as one or more table rows, right below the
clicked item:

    >>> filelist_body = first_tag_by_class(anon_browser.contents, 'queue-4')
    >>> filelist = filelist_body.find_all('tr')

It contains a list of files related to the queue item clicked, followed
by its size, one file per line. Expired files have no size.

    >>> for row in filelist:
    ...     print(extract_text(row))
    alsa-utils_1.0.9a-4ubuntu1.dsc (3 bytes)
    alsa-utils_1.0.9a-4ubuntu1.diff.gz
    diff from 1.0.9a-4 to 1.0.9a-4ubuntu1 (11 bytes)

Each unexpired filename links to its respective proxied librarian URL.
Expired files have no link, so we just get None.

    >>> for row in filelist:
    ...     print(row.find('a'))
    <a href="http://.../+upload/4/+files/alsa-utils_1.0.9a-4ubuntu1.dsc">
      alsa-utils_1.0.9a-4ubuntu1.dsc
    </a>
    None
    <a href="http://.../alsa-utils.diff.gz">diff from 1.0.9a-4 to
    1.0.9a-4ubuntu1</a>

On binary queue items we also present the stamp 'NEW' for files never
published in the archive (it helps archive admins when reviewing
candidates).  The binary items will also individually show their
version, component, section and priority.

    >>> [filelist] = find_tags_by_class(anon_browser.contents, 'queue-2')
    >>> print(extract_text(filelist))
    pmount_1.0-1_all.deb (18 bytes) NEW 0.1-1 main base important

XXX cprov 20070726: we should extend the test when we are able to
probe javascripts events.


Accepting items
===============

Inspect the ACCEPTED queue:

    >>> anon_browser.getControl(
    ...     name="queue_state", index=0).displayValue = ['Accepted']
    >>> anon_browser.getControl("Update").click()
    >>> print_feedback_messages(anon_browser.contents)
    The Accepted queue is empty.

Now we act on the queue, which requires admin or upload_manager permission.
First, we need to add fake librarian files so that email notifications work:

    >>> from lp.archiveuploader.tests import (
    ...     insertFakeChangesFileForAllPackageUploads)
    >>> insertFakeChangesFileForAllPackageUploads()

And store a chroot for ubuntu breezy-autotest/i386 architectures, so
the builds can be created.

    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher

    >>> login('foo.bar@canonical.com')

    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

    >>> breezy_autotest = ubuntu.getSeries('breezy-autotest')
    >>> test_publisher = SoyuzTestPublisher()
    >>> ignore = test_publisher.setUpDefaultDistroSeries(breezy_autotest)
    >>> test_publisher.addFakeChroots(distroseries=breezy_autotest)

Upload a new "bar" source so we can accept it later.

    >>> from lp.archiveuploader.tests import datadir
    >>> changes_file = open(
    ...     datadir('suite/bar_1.0-1/bar_1.0-1_source.changes'), 'rb')
    >>> changes_file_content = changes_file.read()
    >>> changes_file.close()

    >>> bar_src = test_publisher.getPubSource(
    ...     sourcename='bar', distroseries=breezy_autotest, spr_only=True,
    ...     version='1.0-1', component='universe', section='devel',
    ...     changes_file_content=changes_file_content)

    >>> from lp.soyuz.enums import PackageUploadStatus
    >>> from lp.soyuz.model.queue import PassthroughStatusValue
    >>> removeSecurityProxy(bar_src.package_upload).status = (
    ...     PassthroughStatusValue(PackageUploadStatus.NEW))
    >>> bar_queue_id = bar_src.package_upload.id

Swallow any email generated at the upload:

    >>> from lp.services.config import config
    >>> from lp.services.job.runner import JobRunner
    >>> from lp.services.mail import stub
    >>> from lp.soyuz.interfaces.archivejob import (
    ...     IPackageUploadNotificationJobSource,
    ...     )
    >>> from lp.testing.mail_helpers import pop_notifications

    >>> def run_package_upload_notification_jobs():
    ...     with permissive_security_policy(
    ...             config.IPackageUploadNotificationJobSource.dbuser):
    ...         job_source = getUtility(IPackageUploadNotificationJobSource)
    ...         JobRunner.fromReady(job_source).runAll()

    >>> run_package_upload_notification_jobs()
    >>> swallow = pop_notifications()

Set up a second browser on the same page to simulate accidentally posting to
the form twice.

    >>> logout()
    >>> duplicate_submission_browser = setupBrowser(
    ...       auth="Basic test@canonical.com:test")
    >>> duplicate_submission_browser.open(
    ...    "http://localhost/ubuntu/breezy-autotest/+queue")

Go back to the "new" queue and accept "bar":

    >>> upload_manager_browser.open(
    ...    "http://localhost/ubuntu/breezy-autotest/+queue")
    >>> print_queue(upload_manager_browser.contents)  # noqa
    Package             Version     Component Section Priority Sets Pocket  When
    bar (source)        1.0-1       universe  devel   low           Release ...
    netapplet...ddtp... -                                           Release 2006-...
    netapplet...dist... -                                           Release 2006-...
    alsa-utils (source) 1.0.9a-4... main      base    low           Release 2006-...
    netapplet (source)  0.99.6-1    main      web     low           Release 2006-...
    pmount (i386)       0.1-1                                       Release 2006-...
    moz...irefox (i386) 0.9                                         Release 2006-...

    >>> upload_manager_browser.getControl(
    ...     name="QUEUE_ID").value = [str(bar_queue_id)]
    >>> upload_manager_browser.getControl(name="Accept").click()
    >>> print_queue(upload_manager_browser.contents)  # noqa
    Package             Version     Component Section Priority Sets Pocket  When
    netapplet...ddtp... -                                           Release 2006-...
    netapplet...dist... -                                           Release 2006-...
    alsa-utils (source) 1.0.9a-4... main      base    low           Release 2006-...
    netapplet (source)  0.99.6-1    main      web     low           Release 2006-...
    pmount (i386)       0.1-1                                       Release 2006-...
    moz...irefox (i386) 0.9                                         Release 2006-...

Accepting queue items results in an email to the uploader (and the changer
if it is someone other than the uploader) and (usually) an email to the
distroseries' announcement list (see nascentupload-announcements.rst).

    >>> run_package_upload_notification_jobs()
    >>> [changer_notification, signer_notification,
    ...  announcement] = pop_notifications()
    >>> print(changer_notification['To'])
    Daniel Silverstone <daniel.silverstone@canonical.com>
    >>> print(signer_notification['To'])
    Foo Bar <foo.bar@canonical.com>
    >>> print(announcement['To'])
    autotest_changes@ubuntu.com

Forcing a duplicated submission on a queue item is recognised.  Here we
submit the same form again via a different browser instance, which simulates
a double post.

    >>> duplicate_submission_browser.getControl(
    ...     name="QUEUE_ID").value = [str(bar_queue_id)]
    >>> duplicate_submission_browser.getControl(name="Accept").click()
    >>> print_feedback_messages(duplicate_submission_browser.contents)
    FAILED: bar (Unable to accept queue item due to status.)

No emails are sent in this case:

    >>> run_package_upload_notification_jobs()
    >>> len(stub.test_emails)
    0

Because it's a single source upload, accepting bar will not put it in the
accepted queue since it skips that state and goes straight to being published.
Let's accept mozilla-firefox so we can see it in the accepted queue:

    >>> upload_manager_browser.open(
    ...    "http://localhost/ubuntu/breezy-autotest/+queue")
    >>> upload_manager_browser.getControl(name="QUEUE_ID").value = ['1']
    >>> upload_manager_browser.getControl(name="Accept").click()
    >>> print_feedback_messages(upload_manager_browser.contents)
    OK: mozilla-firefox

The item is moved to the ACCEPTED queue:

    >>> upload_manager_browser.getControl(
    ...    name="queue_state", index=0).displayValue = ['Accepted']
    >>> upload_manager_browser.getControl("Update").click()
    >>> print_queue(upload_manager_browser.contents)  # noqa
    Package             Version     Component Section Priority Sets Pocket  When
    moz...irefox (i386) 0.9                                         Release 2006-...

Going back to the "new" queue, we can see our item has gone:

    >>> upload_manager_browser.getControl(
    ...    name="queue_state", index=0).displayValue = ['New']
    >>> upload_manager_browser.getControl("Update").click()
    >>> print_queue(upload_manager_browser.contents)  # noqa
    Package             Version     Component Section Priority Sets Pocket  When
    netapplet...ddtp... -                                           Release 2006-...
    netapplet...dist... -                                      Release 2006-...
    alsa-utils (source) 1.0.9a-4... main      base    low      Release 2006-...
    netapplet (source)  0.99.6-1    main      web     low      Release 2006-...
    pmount (i386)       0.1-1                                  Release 2006-...

When accepting items from the unapproved queue, the page will remain on the
unapproved list after the items are accepted, to allow piecemeal
selection and acceptance.

    >>> upload_manager_browser.getControl(
    ...    name="queue_state", index=0).displayValue = ['Unapproved']
    >>> upload_manager_browser.getControl("Update").click()

Accept "cnews" source:

    >>> upload_manager_browser.getControl(name="QUEUE_ID").value = ['9']
    >>> upload_manager_browser.getControl(name="Accept").click()
    >>> print_feedback_messages(upload_manager_browser.contents)
    OK: cnews

And the page is still on the Unapproved list:

    >>> upload_manager_browser.getControl(
    ...     name="queue_state", index=0).displayValue
    ['Unapproved']

Move back to the New queue:

    >>> upload_manager_browser.getControl(
    ...     name="queue_state", index=0).displayValue = ['New']
    >>> upload_manager_browser.getControl("Update").click()


Overriding items
================

At acceptance time, the component, section and priority (for binaries)
may be overridden to new values by changing the value in any or all of
the drop-down (select) boxes to the left of the "accept" button.  Source
uploads can only have their component and section overridden.  Binary
uploads can have all three properties overrdden but can be overridden
only at their file level.  Currently, this UI only permits overriding
all of the binary files in an upload at once, or not at all.

Thus, the items that are checked for acceptance will also be overridden
depending on the selected values.  This allows many items to be
all overridden at once with the same value(s).

The upload manager selects netapplet(source) and pmount(i386) for acceptance:

    >>> upload_manager_browser.getControl(name="QUEUE_ID").value=['2', '3']

And changes some override values:

    >>> upload_manager_browser.getControl(
    ...     name="component_override").displayValue = ['restricted']
    >>> upload_manager_browser.getControl(
    ...     name="section_override").displayValue = ['admin']
    >>> upload_manager_browser.getControl(
    ...     name="priority_override").displayValue = ['extra']

And now accepts the checked items:

    >>> upload_manager_browser.getControl(name="Accept").click()

They see the informational message that confirms the details of what was
overridden:

    >>> print_feedback_messages(upload_manager_browser.contents)
    OK: netapplet(restricted/admin)
    OK: pmount(restricted/admin/extra)

    >>> print_queue(upload_manager_browser.contents)  # noqa
    Package             Version     Component Section Priority Sets Pocket  When
    netapplet...ddtp... -                                           Release 2006-...
    netapplet...dist... -                                           Release 2006-...
    alsa-utils (source) 1.0.9a-4... main      base    low           Release 2006-...

Any user can now see the 'accepted' queue contains pmount with its
overridden values.

    >>> anon_browser.getControl(
    ...     name="queue_state", index=0).displayValue=['Accepted']
    >>> anon_browser.getControl("Update").click()
    >>> print_queue(anon_browser.contents)  # noqa
    Package             Version     Component Section Priority Sets Pocket  When
    pmount (i386)       0.1-1                                       Release 2006-...
    ...

The user can drill down into the file list to see the overridden binary
values:

    >>> filelist = find_tags_by_class(anon_browser.contents, 'queue-2')
    >>> for row in filelist:
    ...     print(extract_text(row))
    pmount_1.0-1_all.deb (18 bytes) NEW 0.1-1 restricted admin extra
    Accepted a moment ago by Sample Person

'netapplet' has gone straight to the 'done' queue because it's a single
source upload, and we can see its overridden values there:

    >>> anon_browser.getControl(
    ...     name="queue_state", index=0).displayValue=['Done']
    >>> anon_browser.getControl("Update").click()
    >>> print_queue(anon_browser.contents)  # noqa
    Package             Version     Component  Section Priority Sets Pocket  When
    ...
    netapplet (source)  0.99.6-1    restricted admin   low ...


Rejecting items
===============

Rejecting 'alsa-utils' source:

    >>> run_package_upload_notification_jobs()
    >>> stub.test_emails = []

    >>> upload_manager_browser.getControl(name="QUEUE_ID").value = ['4']
    >>> upload_manager_browser.getControl(name="Reject").disabled
    False
    >>> upload_manager_browser.getControl(name='rejection_comment').value = (
    ...     'Foo')
    >>> upload_manager_browser.getControl(name="Reject").click()
    >>> print_feedback_messages(upload_manager_browser.contents)
    OK: alsa-utils

    >>> print_queue(upload_manager_browser.contents)  # noqa
    Package             Version     Component Section Priority Sets Pocket  When
    netapplet...ddtp... -                                           Release 2006-...
    netapplet...dist... -                                           Release 2006-...

    >>> upload_manager_browser.getControl(
    ...     name="queue_state", index=0).displayValue=['Rejected']
    >>> upload_manager_browser.getControl("Update").click()
    >>> logs = find_tags_by_class(
    ...     upload_manager_browser.contents, "log-content")
    >>> for log in logs:
    ...     print(extract_text(log))
    Rejected...a moment ago...by Sample Person...Foo

One rejection email is generated:

    >>> run_package_upload_notification_jobs()
    >>> [rejection] = pop_notifications()
    >>> rejection['Subject']
    '[ubuntu/breezy-autotest] alsa-utils 1.0.9a-4ubuntu1 (Rejected)'

Please note that in this case the rejection reason is not available
and how that's stated in the notification email body.

    >>> body = rejection.get_payload()[0]
    >>> print(body.as_string()) # doctest: -NORMALIZE_WHITESPACE
    Content-Type: text/plain; charset="utf-8"
    MIME-Version: 1.0
    Content-Transfer-Encoding: quoted-printable
    <BLANKLINE>
    Rejected:
    Rejected by Sample Person: Foo
    ...
    You are receiving this email because you are the most recent person
    listed in this package's changelog.
    <BLANKLINE>

The override controls are now available for rejected packages.

Navigate to the rejected items queue.

    >>> upload_manager_browser.getControl(
    ...    name="queue_state", index=0).displayValue = ['Rejected']
    >>> upload_manager_browser.getControl("Update").click()

    >>> upload_manager_browser.getControl(
    ...     name="queue_state", index=0).displayValue
    ['Rejected']

The various override controls are present now.

    >>> upload_manager_browser.getControl(
    ...     name="component_override").displayValue
    ['(no change)']
    >>> upload_manager_browser.getControl(
    ...     name="section_override").displayValue
    ['(no change)']
    >>> upload_manager_browser.getControl(
    ...     name="priority_override").displayValue
    ['(no change)']

Since the user looks at packages in the rejected queue the "Reject"
button will be disabled.

    >>> upload_manager_browser.getControl(name="Reject").disabled
    True

Accepting alsa again, and check that the package upload log has more rows

    >>> upload_manager_browser.getControl(name="QUEUE_ID").value = ['4']
    >>> upload_manager_browser.getControl(name="Accept").click()
    >>> upload_manager_browser.getControl(
    ...     name="queue_state", index=0).displayValue=['Accepted']
    >>> upload_manager_browser.getControl("Update").click()
    >>> pkg_content = first_tag_by_class(upload_manager_browser.contents,
    ...                                  "queue-4")
    >>> logs = find_tags_by_class(str(pkg_content), "log-content")
    >>> for log in logs:
    ...     print(extract_text(log))
    Accepted...a moment ago...by Sample Person...
    Rejected...a moment ago...by Sample Person...Foo


Clean up
========

    >>> from lp.testing.layers import LibrarianLayer
    >>> LibrarianLayer.librarian_fixture.clear()
