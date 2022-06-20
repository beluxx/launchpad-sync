Upload processing queue
=======================

The upload processing queue (PackageUpload and friends) is where
uploads go after they have been checked by process-upload.py and
before they get published by publish-distro.py.

Upload system stores syntactically corrects (see
nascentupload.rst) uploads driven by a submitted changesfile.

One PackageUpload ~ One upload ~ One changesfile.

An upload can contain a combination of content types, organized by:

 * Source (PackageUploadSource):
   a SourcePackageRelease ([tar.gz +] diff)

 * Build (PackageUploadBuild):
   a Build result, one or more BinaryPackageReleases resulted from a
   successfully build (deb).

 * Custom (PackageUploadCustom):
   a special file which will be processed in a specific way to publish
   its contents in the archive  (tar.gz). Currently we support
   translations, installer and  upgrader (see
   distroseriesqueue-{translation, dist-upgrader}).

Each of those instances points back to a PackageUpload entry
(parent) and to its type target:

 * PackageUploadSource -> SourcePackageRelease (SPR),
 * PackageUploadBuild -> Build,
 * PackageUploadCustom -> LibraryFileAlias (LFA).

The combination is assured by the upload policy used (see
nascentupload.rst), some of them allow source + binaries, other only
binaries + custom, other only source.

First up, we need to actually process an upload to get it into the
queue. To do this we prepare an OpenPGP key, and then run the upload handler.

    >>> from lp.testing.gpgkeys import import_public_test_keys
    >>> import_public_test_keys()

We need some setup for the upload handler.

    >>> from lp.archiveuploader.nascentupload import NascentUpload
    >>> from lp.archiveuploader.tests import datadir, getPolicy
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> from lp.soyuz.model.component import ComponentSelection
    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> hoary = ubuntu['hoary']
    >>> universe = getUtility(IComponentSet)['universe']
    >>> trash = ComponentSelection(distroseries=hoary, component=universe)

Construct an upload.

    >>> anything_policy = getPolicy(
    ...     name='absolutely-anything', distro='ubuntu', distroseries='hoary')

    >>> from lp.services.log.logger import DevNullLogger
    >>> ed_upload = NascentUpload.from_changesfile_path(
    ...     datadir("ed_0.2-20_i386.changes.source-only-unsigned"),
    ...     anything_policy, DevNullLogger())

    >>> ed_upload.process()
    >>> success = ed_upload.do_accept()
    >>> success
    True

Now the upload is in the queue, it'll likely be there as NEW because that's
what we expect the ed upload to produce. Let's find the queue item and
convert it to an ACCEPTED item.

    >>> from lp.soyuz.enums import PackageUploadStatus
    >>> from lp.soyuz.interfaces.queue import QueueInconsistentStateError

    >>> new_queue = hoary.getPackageUploads(PackageUploadStatus.NEW)

Use state-machine method provided by PackageUpload to ACCEPT an
upload. If some designed check according to the request state do not
pass, the state-machine methods will raise an exception indicating the
upload can not have that state.

XXX cprov 20051209: need to build a broken upload to test it properly

    >>> from lp.services.database.interfaces import IStore
    >>> for item in new_queue:
    ...     try:
    ...         item.setAccepted()
    ...         IStore(item).flush()
    ...     except QueueInconsistentStateError as info:
    ...         print(info)

    >>> accepted_queue = hoary.getPackageUploads(PackageUploadStatus.ACCEPTED)

    >>> from lp.services.log.logger import FakeLogger
    >>> for item in accepted_queue:
    ...     for source in item.sources:
    ...         print(source.sourcepackagerelease.name)
    ...     pub_records = item.realiseUpload(FakeLogger())
    ed
    DEBUG Publishing source ed/0.2-20 to ubuntu/hoary in ubuntu


Confirm we can now find ed published in hoary.

    >>> from lp.soyuz.enums import PackagePublishingStatus
    >>> from lp.soyuz.model.publishing import SourcePackagePublishingHistory
    >>> for release in IStore(SourcePackagePublishingHistory).find(
    ...         SourcePackagePublishingHistory,
    ...         distroseries=hoary, status=PackagePublishingStatus.PENDING):
    ...     if release.sourcepackagerelease.sourcepackagename.name == "ed":
    ...         print(release.sourcepackagerelease.version)
    0.2-20


Check IPackageUploadSet behaviour:

    >>> from lp.testing import verifyObject
    >>> from lp.soyuz.interfaces.queue import IPackageUploadSet

Grab an utility:

    >>> qset = getUtility(IPackageUploadSet)

Check if it implements its interface completely:

    >>> verifyObject(IPackageUploadSet, qset)
    True

Iterating over IPackageUploads via iPackageUploadSet:

    >>> len([item for item in qset])
    16

Retrieving an IPackageUpload by its id:

    >>> qset[1].id
    1

    >>> qset.get(1).id
    1

Counter, optionally by status (informally named "queue") and or distroseries:

    >>> qset.count()
    16

    >>> qset.count(PackageUploadStatus.DONE)
    5

    >>> qset.count(PackageUploadStatus.REJECTED)
    0

Retrieve some data from DB to play more with counter.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> distro = getUtility(IDistributionSet).getByName('ubuntu')
    >>> breezy_autotest = distro['breezy-autotest']

    >>> qset.count(distroseries=breezy_autotest)
    13

    >>> qset.count(status=PackageUploadStatus.ACCEPTED,
    ...            distroseries=breezy_autotest)
    0

    >>> qset.count(status=PackageUploadStatus.DONE,
    ...            distroseries=hoary)
    1


Check the behaviour of @cachedproperty  attributes:

    >>> qitem = qset.get(1)

    >>> qitem.date_created
    datetime.datetime(...)

    >>> print(qitem.changesfile.filename)
    mozilla-firefox_0.9_i386.changes

    >>> print(qitem.sourcepackagerelease.name)
    mozilla-firefox

    >>> print(qitem.displayname)
    mozilla-firefox

    >>> print(qitem.displayversion)
    0.9

    >>> print(qitem.displayarchs)
    i386

    >>> qitem.sourcepackagerelease
    <SourcePackageRelease mozilla-firefox ...>


Let's check the behaviour of @cachedproperty attributes in a custom upload:

    >>> custom_item = qset.get(5)

    >>> custom_item.date_created
    datetime.datetime(...)

    >>> print(custom_item.changesfile.filename)
    netapplet-1.0.0.tar.gz

    >>> print(custom_item.displayname)
    netapplet-1.0.0.tar.gz

    >>> print(custom_item.displayversion)
    -

    >>> print(custom_item.displayarchs)
    raw-translations

    >>> print(custom_item.sourcepackagerelease)
    None

The method getBuildByBuildIDs() will return all the PackageUploadBuild
records that match the supplied build IDs.

    >>> ids = (18,19)
    >>> for package_upload_build in qset.getBuildByBuildIDs(ids):
    ...     print(package_upload_build.packageupload.displayname)
    mozilla-firefox
    pmount

If the supplied IDs is empty or None, an empty list is returned:

    >>> qset.getBuildByBuildIDs([])
    []

    >>> qset.getBuildByBuildIDs(None)
    []


Upload Signing Key
------------------

IPackageUpload.signing_key should store the IGPGKey reference to
the key used to sign the changesfile when it applies (insecure policy
uploads).

It's mainly used to identify sponsored uploads, when someone with
rights to upload to ubuntu (mostly MOTU) signed over package changes
done by someone else.

Let's process a new upload:

    >>> insecure_policy = getPolicy(
    ...     name='insecure', distro='ubuntu', distroseries='hoary')

    >>> bar_ok = NascentUpload.from_changesfile_path(
    ...     datadir('suite/bar_1.0-1/bar_1.0-1_source.changes'),
    ...     insecure_policy, DevNullLogger())
    >>> bar_ok.process()
    >>> success = bar_ok.do_accept()
    >>> success
    True

    >>> signed_queue = bar_ok.queue_root

    >>> from lp.registry.interfaces.gpg import IGPGKey
    >>> from lp.soyuz.interfaces.queue import IPackageUpload

    >>> verifyObject(IPackageUpload, signed_queue)
    True

    >>> verifyObject(IGPGKey, signed_queue.signing_key)
    True

Let's check the IPerson entities related to this source upload:

    >>> signed_src = signed_queue.sources[0].sourcepackagerelease

    >>> print(signed_src.creator.displayname)
    Daniel Silverstone

    >>> print(signed_src.maintainer.displayname)
    Launchpad team

    >>> print(signed_queue.signing_key.owner.displayname)
    Foo Bar

Based on this information we can conclude that source 'bar' is
maintained by 'Launchpad Team', was modified by 'Daniel Silverstone'
and sponsored by 'Foo Bar'.


IHasQueueItems
--------------

Check State Machine over PackageUploadBuilds:

Performing full acceptance:

    >>> items = breezy_autotest.getPackageUploads(PackageUploadStatus.NEW)
    >>> for item in items:
    ...     item.setAccepted()
    ...     print(item.displayname, item.status.name)
    netapplet-1.0.0.tar.gz ACCEPTED
    netapplet-1.0.0.tar.gz ACCEPTED
    alsa-utils ACCEPTED
    netapplet ACCEPTED
    pmount ACCEPTED
    mozilla-firefox ACCEPTED

Move the ACCEPTED items back to NEW.

    >>> from lp.soyuz.model.queue import PassthroughStatusValue
    >>> items = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.ACCEPTED)
    >>> for item in items:
    ...     item.status = PassthroughStatusValue(PackageUploadStatus.NEW)
    ...     print(item.displayname, item.status.name)
    netapplet-1.0.0.tar.gz NEW
    netapplet-1.0.0.tar.gz NEW
    alsa-utils NEW
    netapplet NEW
    pmount NEW
    mozilla-firefox NEW

Check several available state machine methods on a NEW queue item
(except setAccepted, it's already covered by other tests, check if they
don't raise any exception):

    >>> test_qitem = getUtility(IPackageUploadSet)[1]
    >>> test_qitem.setUnapproved()
    >>> test_qitem.setRejected()
    >>> test_qitem.setDone()
    >>> test_qitem.status = PassthroughStatusValue(PackageUploadStatus.NEW)

Check forbidden approval of not selected Section:

    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> from lp.soyuz.interfaces.section import ISectionSet

Retrieve mozilla-firefox Upload:

    >>> item = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.NEW, name=u'mozilla')[0]

Override the mozilla-firefox component to fresh created 'hell' component.

XXX cprov 20060118: remove proxy magic is required for BPR instances.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> naked_bin = removeSecurityProxy(
    ...       item.builds[0].build.binarypackages[0])
    >>> naked_bin.component = getUtility(IComponentSet).new('hell')
    >>> try:
    ...     item.setAccepted()
    ... except QueueInconsistentStateError as e:
    ...     print(item.displayname, e)
    ... else:
    ...     print(item.displayname, 'ACCEPTED')
    mozilla-firefox Component "hell" is not allowed in breezy-autotest

Check how we treat source upload duplications in UNAPPROVED queue (NEW
has a similar behaviour):

    >>> dups = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.UNAPPROVED, name=u'cnews')
    >>> dups.count()
    2
    >>> dup_one, dup_two = list(dups)

    >>> print(dup_one.displayname)
    cnews
    >>> print(dup_one.displayversion)
    1.0
    >>> print(dup_two.displayname)
    cnews
    >>> print(dup_two.displayversion)
    1.0

The upload admin can not accept both since we check unique
(name, version) accross distribution:

    >>> dup_one.setAccepted()
    >>> dup_one.status == PackageUploadStatus.ACCEPTED
    True

The database modification needs to be realised in the DB, otherwise
the look up code won't be able to identify any duplications:

    >>> IStore(dup_one).flush()

As expected the second item acceptance will fail and the item will
remain in the original queue

    >>> dup_two.setAccepted()
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.queue.QueueInconsistentStateError: The source cnews -
    1.0 is already accepted in ubuntu/breezy-autotest and you cannot upload
    the same version within the same distribution. You have to modify the
    source version and re-upload.
    >>> dup_two.status.name
    'UNAPPROVED'

The only available action will be rejection:

    >>> dup_two.setRejected()
    >>> IStore(dup_one).flush()
    >>> dup_two.status.name
    'REJECTED'

Move the second item back to its original queue to perform the same
test after the former accepted item was published (DONE queue)

    >>> dup_two.status = PassthroughStatusValue(
    ...     PackageUploadStatus.UNAPPROVED)
    >>> IStore(dup_two).flush()
    >>> dup_two.status.name
    'UNAPPROVED'

    >>> dup_one.setDone()
    >>> dup_one.status == PackageUploadStatus.DONE
    True
    >>> IStore(dup_one).flush()

The protection code should also identify dups with items in DONE queue

    >>> dup_two.setAccepted()
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.queue.QueueInconsistentStateError: The source cnews -
    1.0 is already accepted in ubuntu/breezy-autotest and you cannot upload
    the same version within the same distribution. You have to modify the
    source version and re-upload.

The ubuntu policy allows unofficial sections to live sometime in the
repository, until someone find time to override them. It's better than
dropping binary packages that might have consumed a lot of resources
for such a unimportant issue.

Retrieve the 'pmount' NEW queue entry and override it with a
just-created, thus unofficial, section named 'boing'.

    >>> item = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.NEW, name=u'pmount')[0]

    >>> pmount_binary = item.builds[0].build.binarypackages[0]
    >>> removeSecurityProxy(
    ...     pmount_binary).section = getUtility(ISectionSet).new('boing')

The 'pmount' entry for the unofficial section 'boing', can be
normally accepted.

    >>> item.setAccepted()
    >>> print(item.status.name)
    ACCEPTED

Roll back modified data:

    >>> transaction.abort()

Clear existing mail stack:

    >>> from lp.testing.mail_helpers import pop_notifications
    >>> rubbish = pop_notifications()

As mentioned above, values returned by getPackageUploads matching a given
'name' and 'version' may contain different types of uploads.

Sampledata contains only a i386 binary exactly matching 'pmount 0.1-1'.

    >>> from operator import attrgetter
    >>> def print_queue_items(queue_items):
    ...     for queue_item in queue_items:
    ...         print("%s  %s  %s" % (
    ...             queue_item.displayname, queue_item.displayversion,
    ...             queue_item.displayarchs))

    >>> queue_items = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.NEW, name=u'pmount', version=u'0.1-1',
    ...     exact_match=True)
    >>> print_queue_items(queue_items)
    pmount  0.1-1  i386

We will set up a very peculiar environment to test this aspect of
`getPackageUploads`. First we will include another a non-matching source
version of pmount (0.1-2) into the binary pmount upload we already
have in the sampledata.

    >>> [binary_queue] = queue_items
    >>> pmount = ubuntu.getSourcePackage('pmount')
    >>> non_matching_pmount = pmount.getVersion('0.1-2')
    >>> unused = binary_queue.addSource(
    ...    non_matching_pmount.sourcepackagerelease)

'pmount 0.1-1' binary upload continues to be returned when we query
the queue for 'pmount 0.1-1', via the existing binary path.

    >>> queue_items = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.NEW, name=u'pmount', version=u'0.1-1',
    ...     exact_match=True)
    >>> print_queue_items(queue_items)
    pmount  0.1-1  i386

Also, when we can create a source 'pmount 0.1-1' upload in the
breezy-autotest context. It also becomes part of the lookup results.

    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> candidate_queue = breezy_autotest.createQueueEntry(
    ...     PackagePublishingPocket.RELEASE,
    ...     breezy_autotest.main_archive,
    ...     'pmount_0.1-1_source.changes', b'some content')
    >>> matching_pmount = pmount.getVersion('0.1-1')
    >>> unused = candidate_queue.addSource(
    ...     matching_pmount.sourcepackagerelease)

    >>> queue_items = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.NEW, name=u'pmount', version=u'0.1-1',
    ...     exact_match=True)
    >>> print_queue_items(queue_items)
    pmount  0.1-1  source
    pmount  0.1-1  i386

It means that call sites querying the upload queue should be aware of
this aspect and filter the results appropriately.

One special call site is `PackageUploadSource.verifyBeforeAccepted`.

It should allow the acceptance of 'pmount 0.1-1' source, even if there
is a 'pmount 0.1-1' binary upload already accepted in its context.
(see bug #280700 for more information about this policy decision)

# XXX StuartBishop 20100311 bug=537335: Need to order results here.
    >>> queue_items = sorted(list(queue_items),
    ...     key=attrgetter('displayarchs'))
    >>> [binary_item, source_item] = queue_items
    >>> binary_item.setAccepted()

    >>> queue_items = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.ACCEPTED, name=u'pmount',
    ...     version=u'0.1-1', exact_match=True)
    >>> print_queue_items(queue_items)
    pmount  0.1-1  i386

Binary accepted, let's accept the source.

    >>> source_item.setAccepted()

Both uploads are waiting to be published.

    >>> queue_items = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.ACCEPTED, name=u'pmount',
    ...     version=u'0.1-1', exact_match=True)
    >>> print_queue_items(queue_items)
    pmount  0.1-1  source
    pmount  0.1-1  i386

Let's publish them.

    >>> binary_item.setDone()
    >>> source_item.setDone()

Roll back modified data:

    >>> transaction.abort()


Overriding uploads
------------------

Sources and binaries for the upload may be overridden via the methods
overrideSource() and overrideBinaries().  The former allows overriding
of component and section and the latter both those plus the section.
In addition to these parameters, you must also supply
"allowed_components", which is a sequence of IComponent.  Any overrides
must have the existing and new component in this sequence otherwise
QueueAdminUnauthorizedError is raised.

The alsa-utils source is already in the queue with component "main"
and section "base".

    >>> [item] = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.NEW, name=u'alsa-utils')
    >>> [source] = item.sources
    >>> print("%s/%s" % (
    ...     source.sourcepackagerelease.component.name,
    ...     source.sourcepackagerelease.section.name))
    main/base

Overriding to a component not in the allowed_components list results in
an error:

    >>> restricted = getUtility(IComponentSet)['restricted']
    >>> universe = getUtility(IComponentSet)['universe']
    >>> main = getUtility(IComponentSet)['main']
    >>> web = getUtility(ISectionSet)['web']
    >>> print(item.overrideSource(
    ...     new_component=restricted, new_section=web,
    ...     allowed_components=(universe,)))
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.queue.QueueAdminUnauthorizedError:
    No rights to override to restricted

Allowing "restricted" still won't work because the original component
is "main":

    >>> print(item.overrideSource(
    ...     new_component=restricted, new_section=web,
    ...     allowed_components=(restricted,)))
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.queue.QueueAdminUnauthorizedError:
    No rights to override from main

Specifying both main and restricted allows the override to restricted/web.
overrideSource() returns True if it completed the task.

    >>> print(item.overrideSource(
    ...     new_component=restricted, new_section=web,
    ...     allowed_components=(main,restricted)))
    True
    >>> print("%s/%s" % (
    ...     source.sourcepackagerelease.component.name,
    ...     source.sourcepackagerelease.section.name))
    restricted/web

Similarly for binaries:

    >>> [item] = breezy_autotest.getPackageUploads(
    ...     PackageUploadStatus.NEW, name=u'pmount')
    >>> [build] = item.builds
    >>> [binary_package] = build.build.binarypackages
    >>> print("%s/%s/%s" % (
    ...     binary_package.component.name,
    ...     binary_package.section.name,
    ...     binary_package.priority.title))
    main/base/Important

    >>> from lp.soyuz.enums import PackagePublishingPriority
    >>> binary_changes = [{
    ...     "component": restricted,
    ...     "section": web,
    ...     "priority": PackagePublishingPriority.EXTRA,
    ...     }]
    >>> print(item.overrideBinaries(
    ...     binary_changes, allowed_components=(universe,)))
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.queue.QueueAdminUnauthorizedError:
    No rights to override to restricted

    >>> print(item.overrideBinaries(
    ...     binary_changes, allowed_components=(restricted,)))
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.queue.QueueAdminUnauthorizedError:
    No rights to override from main

    >>> print(item.overrideBinaries(
    ...     binary_changes, allowed_components=(main, restricted)))
    True
    >>> print("%s/%s/%s" % (
    ...     binary_package.component.name,
    ...     binary_package.section.name,
    ...     binary_package.priority.title))
    restricted/web/Extra


Queue items retrieval
---------------------

IPackageUploadSet.getPackageUploads() returns an optionally filtered list of
PackageUpload records for the supplied distroseries.

    >>> warty = distro['warty']
    >>> warty.getPackageUploads().count()
    1

Filtering by status:

    >>> warty.getPackageUploads(
    ...     status=PackageUploadStatus.DONE).count()
    1

Filtering by archive:

    >>> from lp.soyuz.enums import ArchivePurpose
    >>> from lp.soyuz.interfaces.archive import IArchiveSet
    >>> partner_archive = getUtility(IArchiveSet).getByDistroPurpose(
    ...     warty.distribution, ArchivePurpose.PARTNER)
    >>> warty.getPackageUploads(archive=partner_archive).count()
    0

Filtering by pocket:

    >>> warty.getPackageUploads(
    ...     pocket=PackagePublishingPocket.RELEASE).count()
    1

Filtering by custom_type.  We need to add some custom uploads to show this.

    >>> from lp.soyuz.enums import PackageUploadCustomFormat
    >>> static_xlat = PackageUploadCustomFormat.STATIC_TRANSLATIONS
    >>> def add_static_xlat_upload():
    ...     upload = warty.createQueueEntry(
    ...         pocket=PackagePublishingPocket.RELEASE,
    ...         changesfilename="test", changesfilecontent=b"test",
    ...         archive=warty.main_archive)
    ...     arbitrary_file = factory.makeLibraryFileAlias()
    ...     upload.addCustom(arbitrary_file, static_xlat)

    >>> add_static_xlat_upload()

    >>> print(warty.getPackageUploads(
    ...     custom_type=static_xlat).count())
    1

There is also a created_since_date filter that will only return packages
uploaded since the timestamp specified.  This is most useful when retrieving
static translation files.  Static translation files are Gnome help files that
are stripped from built packages and uploaded with the binary as a custom
file.

Providing the timestamp of the last one returned in the previous call is a
convenient way to continue from where the caller left off.

Add another custom upload.

    >>> add_static_xlat_upload()
    >>> uploads = warty.getPackageUploads(custom_type=static_xlat)
    >>> print(uploads.count())
    2

Commit a transaction to ensure new DB objects get a later timestamp.

    >>> import transaction
    >>> transaction.commit()

    >>> last_custom_time = uploads[1].date_created
    >>> add_static_xlat_upload()
    >>> uploads = warty.getPackageUploads(
    ...     created_since_date=last_custom_time, custom_type=static_xlat)

Only the just-created file is returned:

    >>> uploads.count()
    1

    >>> uploads[0].date_created > last_custom_time
    True


Queue Manipulation
------------------

Two convenience methods exist, acceptFromQueue and rejectFromQueue that will
accept or reject the item and send an email respectively.

Let's accept something in the queue.  (We need to populate the librarian
with fake changes files first so that emails can be generated.)

    >>> from lp.archiveuploader.tests import insertFakeChangesFile
    >>> items = breezy_autotest.getPackageUploads(PackageUploadStatus.NEW)
    >>> insertFakeChangesFile(items[1].changesfile.content.id)
    >>> insertFakeChangesFile(items[3].changesfile.content.id)
    >>> items[1].acceptFromQueue()

Two emails are generated.  We won't look what is inside them here, that is
well shown in nascentupload-announcements.rst.

    >>> from lp.services.config import config
    >>> from lp.services.job.runner import JobRunner
    >>> from lp.soyuz.interfaces.archivejob import (
    ...     IPackageUploadNotificationJobSource,
    ...     )
    >>> from lp.testing.dbuser import dbuser

    >>> def run_package_upload_notification_jobs():
    ...     job_source = getUtility(IPackageUploadNotificationJobSource)
    ...     logger = DevNullLogger()
    ...     with dbuser(config.IPackageUploadNotificationJobSource.dbuser):
    ...         JobRunner.fromReady(job_source, logger).runAll()

    >>> run_package_upload_notification_jobs()
    >>> [notification, announcement] = pop_notifications()

When accepting single sources we also immediately create its
corresponding build records. It means that the source will be ready to
build once it was accepted, using 'queue-tool' or via the Web UI.

    >>> queue_source = items[1].sources[0]
    >>> [build] = queue_source.sourcepackagerelease.builds

    >>> print(build.title)
    i386 build of alsa-utils 1.0.9a-4ubuntu1 in ubuntu hoary RELEASE

    >>> print(build.status.name)
    NEEDSBUILD

    >>> print(build.buildqueue_record.lastscore)
    10

Let's reject something in the queue:

    >>> items[3].rejectFromQueue(factory.makePerson())

One email is generated (see nascentupload-announcements.rst)

    >>> run_package_upload_notification_jobs()
    >>> [notification] = pop_notifications()

Clean up the librarian files:

    >>> from lp.testing.layers import LibrarianLayer
    >>> LibrarianLayer.librarian_fixture.clear()
