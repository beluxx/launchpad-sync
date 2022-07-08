NascentUpload Epoch Handling
============================

NascentUpload class supports 'epoch' on versions as specified by:

http://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version

Note that for this tests we already have getUploadFor{Source, Binary}
helper functions added in the globals by test_nascentupload_documentation.py.

Ubuntu/hoary in sampledata is ready to receive uploads in RELEASE
pocket.

    >>> from lp.registry.interfaces.distribution import (
    ...     IDistributionSet)

    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> hoary = ubuntu.getSeries('hoary')

    >>> print(hoary.status.name)
    DEVELOPMENT


Epoch Version Conflicts
-----------------------

Debian-like archives don't include epochs in the version specified in
the filename of pool files.

This makes it possible for packages with different versions to include
the same filename, for instance:

 * source 'bar' version '1.0-1' uses 'bar_1.0-1.diff.gz'
 * source 'bar' version 1:1.0-1' also uses 'bar_1.0-1.diff.gz'

Because of this, we need to be careful when publishing to the archive
to ensure that published files don't get overwritten.

In Soyuz we try to catch such situations by performing a file lookup in the
archive against the proposed source files before 'accepting' it.


Collision in Upload-Time
........................

When the 'non-epoched' version is already published before uploading
the candidate, we need to detect collisions at upload-time, returning
a rejection email to the user.

Upload and publish 'non-epoched' version:

    >>> bar_src_upload = getUploadForSource(
    ...     'suite/bar_1.0-1/bar_1.0-1_source.changes')
    >>> bar_src_upload.process()
    >>> result = bar_src_upload.do_accept()
    >>> bar_src_queue_noepoch = bar_src_upload.queue_root
    >>> print(bar_src_queue_noepoch.displayversion)
    1.0-1
    >>> bar_src_queue_noepoch.status.name
    'NEW'
    >>> bar_src_queue_noepoch.setAccepted()
    >>> pub_records = bar_src_queue_noepoch.realiseUpload()
    >>> bar_src_queue_noepoch.status.name
    'DONE'

Upload 'epoched' bar version:

    >>> bar_src_upload = getUploadForSource(
    ...     'suite/bar_1.0-1_epoched/bar_1.0-1_source.changes')
    >>> bar_src_upload.process()
    >>> print(bar_src_upload.rejection_message)
    File bar_1.0-1.diff.gz already exists in Primary Archive for Ubuntu
        Linux, but uploaded version has different contents. See more
        information about this error in
        https://help.launchpad.net/Packaging/UploadErrors.
    Files specified in DSC are broken or missing, skipping package
        unpack verification.

We rely on uploadprocessor to abort the transaction at this point not
storing the respective SourcePackageRelease.

Clean up this change and carry on:

    >>> import transaction
    >>> transaction.abort()


Collision in queue DONE
.......................

When the 'non-epoched' version is still in queue, we need to identify
collisions when publishing the new candidate:

Upload 'non-epoched' bar source:

    >>> bar_src_upload = getUploadForSource(
    ...     'suite/bar_1.0-1/bar_1.0-1_source.changes')
    >>> bar_src_upload.process()
    >>> result = bar_src_upload.do_accept()
    >>> bar_src_queue_noepoch = bar_src_upload.queue_root
    >>> bar_src_queue_noepoch.status.name
    'NEW'

Upload 'epoched' bar source :

    >>> bar_src_upload = getUploadForSource(
    ...     'suite/bar_1.0-1_epoched/bar_1.0-1_source.changes')
    >>> bar_src_upload.process()
    >>> result = bar_src_upload.do_accept()
    >>> bar_src_queue_epoch = bar_src_upload.queue_root
    >>> bar_src_queue_epoch.status.name
    'NEW'

Upload a newer'epoched' bar source :

    >>> bar_src_upload = getUploadForSource(
    ...     'suite/bar_1.0-2_epoched/bar_1.0-2_source.changes')
    >>> bar_src_upload.process()
    >>> result = bar_src_upload.do_accept()
    >>> bar_src_queue_epoch2 = bar_src_upload.queue_root
    >>> bar_src_queue_epoch2.status.name
    'NEW'

Accept all bar sources:

    >>> print(bar_src_queue_noepoch.displayversion)
    1.0-1
    >>> bar_src_queue_noepoch.setAccepted()
    >>> bar_src_queue_noepoch.status.name
    'ACCEPTED'

    >>> print(bar_src_queue_epoch.displayversion)
    1:1.0-1
    >>> bar_src_queue_epoch.setAccepted()
    >>> bar_src_queue_epoch.status.name
    'ACCEPTED'

    >>> print(bar_src_queue_epoch2.displayversion)
    1:1.0-2
    >>> bar_src_queue_epoch2.setAccepted()
    >>> bar_src_queue_epoch2.status.name
    'ACCEPTED'


Published the 'non-epoched' bar source version as the base package:

    >>> pub_records = bar_src_queue_noepoch.realiseUpload()
    >>> bar_src_queue_noepoch.status.name
    'DONE'

When publishing the 'epoched' bar source the collision is detected:

    >>> bar_src_queue_epoch.realiseUpload()
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.queue.QueueInconsistentStateError: bar_1.0-1.diff.gz
    is already published in archive for hoary
    >>> bar_src_queue_epoch.status.name
    'ACCEPTED'

At this point the archive-admins can 'reject' the record manually or
it will be ignored (with the error message below) every cron.daily cycle.

    >>> bar_src_queue_epoch.setRejected()
    >>> bar_src_queue_epoch.status.name
    'REJECTED'

We also detect a collision when publishing the newer 'epoched' version
containing a orig file with diferent contents than the one already
published in 'non-epoched' version:

    >>> bar_src_queue_epoch2.realiseUpload()
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.queue.QueueInconsistentStateError: bar_1.0.orig.tar.gz
    is already published in archive for hoary with a different SHA1 hash
    (e918d6f5ec2184ae1d795a130da36c9a82c4beaf !=
    73a04163fee97fd2257ab266bd48f1d3d528e012)

    >>> bar_src_queue_epoch2.status.name
    'ACCEPTED'

Similar to what happens to the 'epoched' version, the ignored queue
item should be rejected:

    >>> bar_src_queue_epoch2.setRejected()
    >>> bar_src_queue_epoch2.status.name
    'REJECTED'


Clean up this change and carry on:

    >>> transaction.abort()


Dealing with Epochs and diverging binary versions
-------------------------------------------------

Let's process an source upload and ensure that the resulting
SourcePackageRelease record store a proper 'version':

    >>> bar_src_upload = getUploadForSource(
    ...     'suite/bar_1.0-9/bar_1.0-9_source.changes')
    >>> bar_src_upload.process()
    >>> result = bar_src_upload.do_accept()

For source uploads, Changes.version == DSC.version == SPR.version:

    >>> print(bar_src_upload.changes.version)
    1:1.0-9

    >>> print(bar_src_upload.changes.dsc.dsc_version)
    1:1.0-9

    >>> bar_src_queue = bar_src_upload.queue_root
    >>> bar_spr = bar_src_queue.sources[0].sourcepackagerelease
    >>> print(bar_spr.version)
    1:1.0-9

    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> from lp.soyuz.interfaces.publishing import IPublishingSet
    >>> getUtility(IPublishingSet).newSourcePublication(
    ...     bar_src_upload.policy.distro.main_archive, bar_spr,
    ...     bar_src_upload.policy.distroseries,
    ...     PackagePublishingPocket.RELEASE,
    ...     component=bar_spr.component, section=bar_spr.section)
    <SourcePackagePublishingHistory at ...>

Let's accept the source and claim 'build from accepted' to process the
respective binary:

    >>> bar_src_queue.status.name
    'NEW'
    >>> bar_src_queue.setAccepted()
    >>> bar_src_queue.status.name
    'ACCEPTED'

For a binary upload we expect the same, a BinaryPackageRelease
'version' that includes 'epoch':

    >>> bar_bin_upload = getUploadForBinary(
    ...     'suite/bar_1.0-9_binary/bar_1.0-9_i386.changes')
    >>> bar_bin_upload.process()
    >>> result = bar_bin_upload.do_accept()
    >>> bar_bin_queue = bar_bin_upload.queue_root
    >>> bar_bin_queue.status.name
    'NEW'

The Changesfile version always refers to the source version and the
binary versions included in the upload can diverge between themselves
and from the source version.

    >>> print(bar_bin_upload.changes.version)
    1:1.0-9

    >>> deb_file = bar_bin_upload.changes.files[0]
    >>> print(deb_file.filename)
    bar_6.6.6_i386.deb

    >>> print(deb_file.version)
    1:1.0-9

    >>> print(deb_file.source_version)
    1:1.0-9

    >>> print(deb_file.control_version)
    1:6.6.6

Anyway, the proper value for BinaryPackageRelease.version is the
version stored in the binary control file:

    >>> bar_bpr = bar_bin_queue.builds[0].build.binarypackages[0]
    >>> print(bar_bpr.version)
    1:6.6.6





