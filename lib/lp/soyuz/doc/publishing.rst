==============================
SourcePackagePublishingHistory
==============================

This class provides public access to publishing records via a SQL view.

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.model.publishing import (
    ...     BinaryPackagePublishingHistory,
    ...     SourcePackagePublishingHistory,
    ...     )

Select a publishing record from the sampledata (pmount is a
interesting one):

    >>> spph = IStore(SourcePackagePublishingHistory).get(
    ...     SourcePackagePublishingHistory, 8)
    >>> print(spph.sourcepackagerelease.name)
    pmount
    >>> print(spph.distroseries.name)
    hoary

None of the sources in the sample data are signed, so we can fake one here
to make sure verifyObject will work.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.model.gpgkey import GPGKey
    >>> name16 = getUtility(IPersonSet).getByName('name16')
    >>> fake_signer = GPGKey.selectOneBy(owner=name16)
    >>> spph.sourcepackagerelease.signing_key_owner = fake_signer.owner
    >>> spph.sourcepackagerelease.signing_key_fingerprint = (
    ...     fake_signer.fingerprint)

Verify if the object follows its interface contracts:

    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.distroseries import IDistroSeries
    >>> from lp.registry.interfaces.sourcepackage import ISourcePackage
    >>> from lp.soyuz.interfaces.publishing import (
    ...     IBinaryPackagePublishingHistory,
    ...     ISourcePackagePublishingHistory,
    ...     )
    >>> from lp.soyuz.interfaces.sourcepackagerelease import (
    ...     ISourcePackageRelease)

    >>> verifyObject(ISourcePackagePublishingHistory, spph)
    True

 XXX cprov 20060322: None of the attributes below pass verifyObject().
 So, they claim to implement some thing they don't really have. Most
 of the problems are related with bad interface inheritance.

    >>> IDistroSeries.providedBy(spph.distroseries)
    True

    >>> ISourcePackageRelease.providedBy(spph.sourcepackagerelease)
    True

    >>> ISourcePackageRelease.providedBy(spph.supersededby)
    True

    >>> ISourcePackage.providedBy(spph.meta_sourcepackage)
    True

ISourcePackagePublishingHistory has some handy shortcuts to get textual
representations of the source package name, version, component and section.
This is mostly as a convenience to API users so that we don't need to export
tiny 2-column content classes and force the users to retrieve those.

    >>> print(spph.source_package_name)
    pmount

    >>> print(spph.source_package_version)
    0.1-1

    >>> print(spph.component_name)
    main

    >>> print(spph.section_name)
    base

Other properties are shortcuts to the source package's properties:

    >>> print(spph.package_creator)
    <Person at ... mark (Mark Shuttleworth)>

    >>> print(spph.package_maintainer)
    <Person at ... mark (Mark Shuttleworth)>

    >>> print(spph.package_signer)
    <Person at ... name16 (Foo Bar)>

The signer can also be None for packages that were synced (e.g. from Debian):

    >>> from lp.services.propertycache import get_property_cache
    >>> spph.sourcepackagerelease.signing_key_owner = None
    >>> spph.sourcepackagerelease.signing_key_fingerprint = None
    >>> print(spph.package_signer)
    None

There is also a method that returns the .changes file URL. This is proxied
through the webapp rather than being a librarian URL because the changesfile
could be private and thus in the restricted librarian.

    >>> from lp.archiveuploader.tests import (
    ...     insertFakeChangesFileForAllPackageUploads)
    >>> insertFakeChangesFileForAllPackageUploads()

The pmount source has no packageupload in the sampledata:

    >>> print(spph.changesFileUrl())
    None

The iceweasel source has good data:

    >>> pub = spph.archive.getPublishedSources(name=u"iceweasel").first()
    >>> print(pub.changesFileUrl())
    http://.../ubuntu/+archive/primary/+files/mozilla-firefox_0.9_i386.changes

There is also a helper property to determine whether the current release for
this package in the distroseries is newer than this publishing. Nothing is
returned if there is no package in the distroseries primary archive with a
later version.

    >>> print(pub.newer_distroseries_version)
    None

If we publish iceweasel 1.1 in the same distroseries, then the distroseries
source package release will be returned.

    >>> from lp.soyuz.tests.test_publishing import (
    ...     SoyuzTestPublisher)
    >>> test_publisher = SoyuzTestPublisher()
    >>> test_publisher.prepareBreezyAutotest()
    >>> new_version = test_publisher.getPubSource(
    ...     distroseries=pub.distroseries, version="1.1",
    ...     sourcename='iceweasel')

    >>> del get_property_cache(pub).newer_distroseries_version
    >>> print(pub.newer_distroseries_version.title)
    iceweasel 1.1 source package in Ubuntu

We can calculate the newer_distroseries_version for many spph objects at once.

    >>> del get_property_cache(pub).newer_distroseries_version
    >>> pub.distroseries.setNewerDistroSeriesVersions([pub])
    >>> print(get_property_cache(pub).newer_distroseries_version.title)
    iceweasel 1.1 source package in Ubuntu

A helper is also included to create a summary of the build statuses for
the spph's related builds, getStatusSummaryForBuilds(), which just
augments the IBuildSet.getStatusSummaryForBuilds() method to include the
'pending' state when builds are fully built but not yet published.

    >>> from lp.buildmaster.enums import BuildStatus
    >>> spph = test_publisher.getPubSource(
    ...     sourcename='abc', architecturehintlist='any')
    >>> builds = spph.createMissingBuilds()
    >>> for build in builds:
    ...     build.updateStatus(BuildStatus.FULLYBUILT)

Create a helper for printing the build status summary:

    >>> import operator
    >>> def print_build_status_summary(summary):
    ...     print(summary['status'].title)
    ...     for build in sorted(
    ...         summary['builds'], key=operator.attrgetter('title')):
    ...         print(build.title)
    >>> build_status_summary = spph.getStatusSummaryForBuilds()
    >>> print_build_status_summary(build_status_summary)
    FULLYBUILT_PENDING
    hppa build of abc 666 in ubuntutest breezy-autotest RELEASE
    i386 build of abc 666 in ubuntutest breezy-autotest RELEASE

The underlying method being used here is getUnpublishedBuildsForSources():

    >>> from lp.soyuz.interfaces.publishing import (
    ...     IPublishingSet)
    >>> ps = getUtility(IPublishingSet)
    >>> unpublished_builds = ps.getUnpublishedBuildsForSources([spph])
    >>> for _, b, _ in sorted(unpublished_builds, key=lambda b:b[1].title):
    ...     print(b.title)
    hppa build of abc 666 in ubuntutest breezy-autotest RELEASE
    i386 build of abc 666 in ubuntutest breezy-autotest RELEASE

Note: if the related archive for this source package publishing is
a rebuild archive then the status summary will always display
FULLY_BUILT.

    >>> from lp.soyuz.enums import ArchivePurpose
    >>> spph.archive.purpose = ArchivePurpose.COPY
    >>> build_status_summary = spph.getStatusSummaryForBuilds()
    >>> print_build_status_summary(build_status_summary)
    FULLYBUILT
    hppa build of abc 666 in ubuntutest breezy-autotest RELEASE
    i386 build of abc 666 in ubuntutest breezy-autotest RELEASE

    # Just set the purpose back before continuing on.
    >>> spph.archive.purpose = ArchivePurpose.PRIMARY

If one of the builds becomes published, it will not appear in the summary:

    >>> from lp.soyuz.enums import (
    ...     PackagePublishingStatus)
    >>> bpr = test_publisher.uploadBinaryForBuild(builds[0], 'abc-bin')
    >>> bpph = test_publisher.publishBinaryInArchive(bpr, spph.archive,
    ...     status=PackagePublishingStatus.PUBLISHED)
    >>> print_build_status_summary(spph.getStatusSummaryForBuilds())
    FULLYBUILT_PENDING
    i386 build of abc 666 in ubuntutest breezy-autotest RELEASE

Nor will it be included in the unpublished builds:

    >>> for _, build, _ in ps.getUnpublishedBuildsForSources([spph]):
    ...     print(build.title)
    i386 build of abc 666 in ubuntutest breezy-autotest RELEASE

By default, only FULLYBUILT builds are included in the returned
unpublished builds:

    >>> builds[1].updateStatus(
    ...     BuildStatus.SUPERSEDED, force_invalid_transition=True)
    >>> for _, build, _ in ps.getUnpublishedBuildsForSources([spph]):
    ...     print(build.title)

But the returned build-states can be set explicitly:

    >>> for _, build, _ in ps.getUnpublishedBuildsForSources(
    ...     [spph],
    ...     build_states=[BuildStatus.FULLYBUILT, BuildStatus.SUPERSEDED]):
    ...     print(build.title)
    i386 build of abc 666 in ubuntutest breezy-autotest RELEASE

Just switch it back to FULLYBUILT before continuing:

    >>> builds[1].updateStatus(
    ...     BuildStatus.FULLYBUILT, force_invalid_transition=True)

After publishing the second binary, the status changes to FULLYBUILT as
per normal:

    >>> bpr = test_publisher.uploadBinaryForBuild(builds[1], 'abc-bin')
    >>> bpph = test_publisher.publishBinaryInArchive(
    ...     bpr, spph.archive,
    ...     status=PackagePublishingStatus.PUBLISHED)
    >>> print_build_status_summary(spph.getStatusSummaryForBuilds())
    FULLYBUILT
    hppa build of abc 666 in ubuntutest breezy-autotest RELEASE
    i386 build of abc 666 in ubuntutest breezy-autotest RELEASE

There are no longer any unpublished builds for the source package:

    >>> for _, build, _ in ps.getUnpublishedBuildsForSources([spph]):
    ...     print(build.title)

If a build is deleted, it does not cause the build status summary to change:

    >>> from lp.soyuz.interfaces.publishing import IPublishingSet
    >>> mark = getUtility(IPersonSet).getByName('mark')
    >>> ignored = getUtility(IPublishingSet).requestDeletion([spph], mark)
    >>> import transaction
    >>> transaction.commit()
    >>> print_build_status_summary(spph.getStatusSummaryForBuilds())
    FULLYBUILT
    hppa build of abc 666 in ubuntutest breezy-autotest RELEASE
    i386 build of abc 666 in ubuntutest breezy-autotest RELEASE

If a build of a SourcePackagePublishingHistory is manually set to
superseded (just to cancel the build) even though the SPPH is itself
not marked as superseded, the status summary will not include
that build:

    >>> spph = test_publisher.getPubSource(
    ...     sourcename='def', architecturehintlist='any')
    >>> builds = spph.createMissingBuilds()
    >>> builds[0].updateStatus(BuildStatus.SUPERSEDED)
    >>> builds[1].updateStatus(BuildStatus.FULLYBUILT)
    >>> build_status_summary = spph.getStatusSummaryForBuilds()
    >>> print_build_status_summary(build_status_summary)
    FULLYBUILT_PENDING
    i386 build of def 666 in ubuntutest breezy-autotest RELEASE

And after publishing the other build, the normal FULLY_BUILT status
is achieved (without the 'canceled' build):

    >>> bpr = test_publisher.uploadBinaryForBuild(builds[1], 'def-bin')
    >>> bpph = test_publisher.publishBinaryInArchive(bpr, spph.archive,
    ...     status=PackagePublishingStatus.PUBLISHED)
    >>> print_build_status_summary(spph.getStatusSummaryForBuilds())
    FULLYBUILT
    i386 build of def 666 in ubuntutest breezy-autotest RELEASE

IBinaryPackagePublishingHistory also contains similar API conveniences.

    >>> bpph = test_publisher.getPubBinaries(binaryname='def-bin')[0]
    >>> verifyObject(IBinaryPackagePublishingHistory, bpph)
    True

    >>> print(bpph.binary_package_name)
    def-bin

    >>> print(bpph.binary_package_version)
    666

    >>> print(bpph.component_name)
    main

    >>> print(bpph.section_name)
    base


Retrieve any SourcePackagePublishingHistory entry.

    >>> from lp.soyuz.interfaces.files import (
    ...     ISourcePackageReleaseFile)
    >>> from lp.soyuz.interfaces.publishing import (
    ...     IBinaryPackagePublishingHistory)
    >>> spph = IStore(SourcePackagePublishingHistory).get(
    ...     SourcePackagePublishingHistory, 10)

    >>> print(spph.displayname)
    alsa-utils 1.0.8-1ubuntu1 in warty


Files published are accessible via the files property:

    >>> any_pub_file = spph.files[0]
    >>> ISourcePackageReleaseFile.providedBy(any_pub_file)
    True

    >>> print(spph.files[0].libraryfile.filename)
    alsa-utils_1.0.8-1ubuntu1.dsc


Deletion and obsolescence
=========================

ArchivePublisherBase, which is common to SourcePackagePublishingHistory
and BinaryPackagePublishingHistory, contains the methods requestDeletion
and requestObsolescence.  These will change the publishing record to
the states DELETED and OBSOLETE respectively.

requestDeletion requires a removed_by (IPerson) and optionally a
removal_comment argument.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.series import SeriesStatus
    >>> mark = getUtility(IPersonSet).getByName('mark')
    >>> spph.distroseries.status = SeriesStatus.DEVELOPMENT
    >>> spph.requestDeletion(mark, "testing deletion")

Inspecting the modified record shows it's ready for domination:

    >>> from storm.store import Store
    >>> from lp.services.database.sqlbase import get_transaction_timestamp
    >>> transaction_timestamp = get_transaction_timestamp(Store.of(spph))

    >>> modified_spph = spph
    >>> modified_spph.status
    <DBItem PackagePublishingStatus.DELETED, (4) Deleted>

    >>> modified_spph.datesuperseded == transaction_timestamp
    True

    >>> print(modified_spph.removed_by.name)
    mark

    >>> print(modified_spph.removal_comment)
    testing deletion

requstObsolescence takes no additional arguments:

    >>> modified_spph = spph.requestObsolescence()

Inspecting the modified record shows it's ready for death row (obsoleted
publications skip domination because domination only works in post-release
pockets for stable distroseries):

    >>> modified_spph.status
    <DBItem PackagePublishingStatus.OBSOLETE, (5) Obsolete>

    >>> modified_spph.scheduleddeletiondate == transaction_timestamp
    True

    >>> spph.distroseries.status = SeriesStatus.CURRENT


Copying and published binarypackages lookup
===========================================

ISourcePackagePublishingHistory provides the getPublishedBinaries
which returns all published binaries build from a source in the pocket
it is published.

We will use SoyuzTestPublisher to generate coherent publications to
test this feature. We will create a publication for a source (foo) and
two architecture-specific binaries in ubuntu/breezy-autotest.

    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> source = test_publisher.getPubSource(
    ...     sourcename='ghi',
    ...     architecturehintlist='any',
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     pocket=PackagePublishingPocket.PROPOSED)

    >>> binaries = test_publisher.getPubBinaries(
    ...     binaryname='ghi-bin',
    ...     pub_source=source,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     pocket=PackagePublishingPocket.PROPOSED)

    >>> print(source.displayname)
    ghi 666 in breezy-autotest

    >>> for bin in binaries:
    ...     print(bin.displayname)
    ghi-bin 666 in breezy-autotest i386
    ghi-bin 666 in breezy-autotest hppa

Using the source publication, ISourcePackagePublishingHistory, we
can obtain the published binaries.

    >>> created_ids = [bin.id for bin in binaries]
    >>> retrieved_ids = [bin.id for bin in source.getPublishedBinaries()]
    >>> sorted(created_ids) == sorted(retrieved_ids)
    True

We can also inspect the builds created for a source publication
without retrieving its binaries.

    >>> for build in source.getBuilds():
    ...     print(build.title)
    hppa build of ghi 666 in ubuntutest breezy-autotest PROPOSED
    i386 build of ghi 666 in ubuntutest breezy-autotest PROPOSED

Now that we know how to retrieve generated binary publication related
to a source publication we can exercise the API provided to copy
publications across suites and/or archives.

One of the most common use-cases for copying a publication is when
archive-admins wants to release for public audience a Stable Release
Update (SRU) which was successfully tested in PROPOSED pocket. This
procedure will consist of a source copy from PROPOSED to UPDATES
including its binaries.

'distroseries' and 'archive' will be constant.

    >>> distroseries = source.distroseries
    >>> distroseries.status = SeriesStatus.CURRENT
    >>> archive = source.archive

'pocket' will be UPDATES.

    >>> pocket = PackagePublishingPocket.UPDATES

Let's perform the copy of the source and all its binaries.

    >>> copied_source = source.copyTo(distroseries, pocket, archive)

    >>> copied_binaries = []
    >>> for bin in binaries:
    ...     copied_binaries.extend(
    ...         bin.copyTo(distroseries, pocket, archive))

The 'copied' records are instances of
{Source,Binary}PackagePublishingHistory:

    >>> ISourcePackagePublishingHistory.providedBy(copied_source)
    True

    >>> [IBinaryPackagePublishingHistory.providedBy(bin)
    ...  for bin in copied_binaries]
    [True, True]

Copied publications are created as PENDING, so the publisher will have
a chance to verify it's contents and include it in the destination
archive index.

    >>> print(copied_source.status.name)
    PENDING

    >>> for bin in copied_binaries:
    ...     print(bin.status.name)
    PENDING
    PENDING

Let's retrieve the 'insecure' corresponding publishing records since
only they provide the API we are interested in.

    >>> copied_source = IStore(SourcePackagePublishingHistory).get(
    ...     SourcePackagePublishingHistory, copied_source.id)

    >>> copied_binaries = [
    ...     IStore(BinaryPackagePublishingHistory).get(
    ...         BinaryPackagePublishingHistory, bin.id)
    ...     for bin in copied_binaries]

When we call createMissingBuilds method on the copied sources it won't
create any builds since the binaries were copied over too.

    >>> copied_source.createMissingBuilds()
    []

Now we can observe that both, the original and the copied sources are
related only with their corresponding binaries, see bug #181834 for
previous broken implementation in this area.

    >>> for bin in source.getPublishedBinaries():
    ...     print(bin.displayname, bin.pocket.name, bin.status.name)
    ghi-bin 666 in breezy-autotest hppa PROPOSED PUBLISHED
    ghi-bin 666 in breezy-autotest i386 PROPOSED PUBLISHED

    >>> for bin in copied_source.getPublishedBinaries():
    ...     print(bin.displayname, bin.pocket.name, bin.status.name)
    ghi-bin 666 in breezy-autotest hppa UPDATES PENDING
    ghi-bin 666 in breezy-autotest i386 UPDATES PENDING

Note that even PENDING binary publications are returned by
getPublishedBinaries(), it considers both PENDING and PUBLISHED status
as active, SUPERSEDED, DELETED and OBSOLETE are excluded. Differently,
getBuiltBinaries() follows binaries in any state.

    >>> source.getPublishedBinaries().count()
    2

    >>> len(source.getBuiltBinaries())
    2

Note that getPublishedBinaries() returns a DecoratedResultSet and
getBuiltBinaries() returns a list.

When we supersede one of the original binary publications, it gets
excluded from the getPublishedBinaries() results, but not from the
getBuiltBinaries() result.

    >>> a_binary = source.getPublishedBinaries()[0]
    >>> a_binary.supersede()

    >>> source.getPublishedBinaries().count()
    1

    >>> len(source.getBuiltBinaries())
    2

The same happens when we delete the i386 binary, so no binaries are
published in the original location.

    >>> deletable = source.getPublishedBinaries()[0]
    >>> deletable.requestDeletion(mark, "go")
    >>> deleted = deletable

    >>> source.getPublishedBinaries().count()
    0

    >>> len(source.getBuiltBinaries())
    2

Finally we will mark both copied binary publication as obsolete and
verify that the getPublishedBinaries() result is also empty after that.

    >>> copied_source.getPublishedBinaries().count()
    2

    >>> for bin in copied_source.getPublishedBinaries():
    ...     obsoleted = bin.requestObsolescence()

    >>> copied_source.getPublishedBinaries().count()
    0

    >>> len(copied_source.getBuiltBinaries())
    2

Additionally to find all built binaries regardless of their states,
getBuiltBinaries() also excludes the duplications generated by
overrides.

Before performing an overriding we will move the all built binaries in
the copied location to PUBLISHED, so they can be visible again for
getPublishedBinaries().

    >>> for pub in copied_source.getBuiltBinaries():
    ...     pub.status = PackagePublishingStatus.PUBLISHED
    ...     pub.scheduleddeletiondate = None

Now we override the first binary publication, the hppa one, to
component 'universe'.

    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> universe = getUtility(IComponentSet)['universe']

    >>> first_binary = copied_source.getPublishedBinaries()[0]
    >>> override = first_binary.changeOverride(new_component=universe)

Not only do the two copied binaries show up in getPublishedBinaries(),
but also the override just done.

    >>> for pub in copied_source.getPublishedBinaries():
    ...     print(pub.displayname, pub.component.name)
    ghi-bin 666 in breezy-autotest hppa universe
    ghi-bin 666 in breezy-autotest hppa main
    ghi-bin 666 in breezy-autotest i386 main

The publication duplication is solved in the publishing pipeline,
specifically in the 'domination' state. See
`archivepublisher.tests.test_dominator` for more information.

On the other hand, getBuiltBinaries() will return only 2 binary
publications and the hppa one is the overridden one.

    >>> for pub in copied_source.getBuiltBinaries():
    ...     print(pub.displayname, pub.component.name)
    ghi-bin 666 in breezy-autotest hppa universe
    ghi-bin 666 in breezy-autotest i386 main

We have to re-publish the superseded and the deleted publications above
because it's used below.

    >>> a_binary.status = PackagePublishingStatus.PUBLISHED
    >>> deleted.status = PackagePublishingStatus.PUBLISHED


Copying and inspecting architecture independent binaries
========================================================

copyTo() behaves differently for architecture independent and
architecture specific binaries. We will create a
architecture-independent publication called 'pirulito' perform a copy
using it.

    >>> source_all = test_publisher.getPubSource(
    ...     sourcename='pirulito', architecturehintlist='all',
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     pocket=PackagePublishingPocket.PROPOSED)

    >>> binaries_all = test_publisher.getPubBinaries(
    ...     binaryname='pirulito', pub_source=source_all,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     pocket=PackagePublishingPocket.PROPOSED)

    >>> print(source_all.displayname)
    pirulito 666 in breezy-autotest

    >>> for bin in binaries_all:
    ...     print(bin.displayname)
    pirulito 666 in breezy-autotest i386
    pirulito 666 in breezy-autotest hppa

Sources are treated in the same way, one publication for each copy
request.

    >>> copied_source_all = source_all.copyTo(distroseries, pocket, archive)

    >>> print(copied_source_all.displayname)
    pirulito 666 in breezy-autotest

Architecture independent binaries, however, when copied results in
multiple publications, one for it supported architecture in the
destination distroseries. In other words, arch-indep copying is
atomic.

    >>> [bin_i386, bin_hppa] = binaries_all

    >>> bin_i386.binarypackagerelease == bin_hppa.binarypackagerelease
    True

    >>> bin_i386.binarypackagerelease.architecturespecific
    False

    >>> binary_copies = bin_i386.copyTo(distroseries, pocket, archive)

The same binary is published in both supported architecture.

    >>> for bin in binary_copies:
    ...     print(bin.displayname)
    pirulito 666 in breezy-autotest hppa
    pirulito 666 in breezy-autotest i386

getPublishedBinaries() on the copied sources returns both binary
publications, even if they refer to the same architecture independent
binary.

    >>> copied_binaries_all = copied_source_all.getPublishedBinaries()

    >>> for bin in copied_binaries_all:
    ...     print(bin.displayname)
    pirulito 666 in breezy-autotest hppa
    pirulito 666 in breezy-autotest i386

    >>> [copy_i386, copy_hppa] = copied_binaries_all

    >>> copy_i386.binarypackagerelease == copy_hppa.binarypackagerelease
    True

getBuiltBinaries(), on the other hand, returns only one publication
(the one for the 'nominatedarchindep' architecture in the destination
distroseries).

    >>> [built_binary] = copied_source_all.getBuiltBinaries()

    >>> print(built_binary.displayname)
    pirulito 666 in breezy-autotest i386


Copying to PPAs
===============

Another common copy use-case is rebuild the same source in another
suite. To simulate this we will create a publication in Celso's PPA.

    >>> cprov = getUtility(IPersonSet).getByName('cprov')

    >>> ppa_source = test_publisher.getPubSource(
    ...     sourcename='jkl',
    ...     archive=cprov.archive,
    ...     status=PackagePublishingStatus.PUBLISHED)
    >>> ppa_binaries = test_publisher.getPubBinaries(
    ...     binaryname='jkl-bin',
    ...     pub_source=ppa_source,
    ...     status=PackagePublishingStatus.PUBLISHED)

    >>> print(ppa_source.displayname, ppa_source.archive.displayname)
    jkl 666 in breezy-autotest PPA for Celso Providelo

    >>> for bin in ppa_binaries:
    ...     print(bin.displayname, bin.archive.displayname)
    jkl-bin 666 in breezy-autotest i386 PPA for Celso Providelo
    jkl-bin 666 in breezy-autotest hppa PPA for Celso Providelo

Now we will copy only the source from Celso's PPA breezy-autotest to
hoary-test.

We hack cprov's PPA to be for ubuntutest instead of ubuntu, as we use
ubuntutest series in this test.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> breezy_autotest = ppa_source.distroseries
    >>> removeSecurityProxy(cprov.archive).distribution = (
    ...     breezy_autotest.distribution)
    >>> hoary_test = breezy_autotest.distribution.getSeries(
    ...     'hoary-test')
    >>> hoary_test.nominatedarchindep = hoary_test["i386"]
    >>> fake_chroot = test_publisher.addMockFile('fake_chroot.tar.gz')
    >>> trash = hoary_test["i386"].addOrUpdateChroot(fake_chroot)

Perform the source-only copy.

    >>> ppa_copied_source = ppa_source.copyTo(
    ...     hoary_test, PackagePublishingPocket.RELEASE, cprov.archive)

    >>> ppa_copied_source = IStore(SourcePackagePublishingHistory).get(
    ...     SourcePackagePublishingHistory, ppa_copied_source.id)

createMissingBuilds will not create any builds because this is an
intra-archive copy:

    >>> ppa_source.createMissingBuilds()
    []

    >>> ppa_copied_source.createMissingBuilds()
    []

In the sampledata, both, hoary-test and breezy-autotest derives from
ubuntu/warty. To make it more realistic we will make hoary-test derive
from breezy-autotest and test if the build algorithm copes with it.

This simulates a rebuild in of the same source in a more recent
distroseries, like rebuilding SRUs for constant sources.

    >>> breezy_autotest.previous_series = None
    >>> hoary_test.previous_series = breezy_autotest

    >>> ppa_source.createMissingBuilds()
    []

    >>> ppa_copied_source.createMissingBuilds()
    []

Now, let's check the opposite, as if the copy was from a more recent
distroseries to a older one, like a backport rebuild.

    >>> breezy_autotest.previous_series = hoary_test
    >>> hoary_test.previous_series = None

    >>> ppa_source.createMissingBuilds()
    []

    >>> ppa_copied_source.createMissingBuilds()
    []

It is also possible to copy sources and binaries to another
distroseries within the same PPA. That's usually the case for
architecture-independent sources.

    >>> ppa_source = test_publisher.getPubSource(
    ...     sourcename='mno',
    ...     archive=cprov.archive, version="999",
    ...     status=PackagePublishingStatus.PUBLISHED)

    >>> ppa_binaries = test_publisher.getPubBinaries(
    ...     binaryname='mno-bin',
    ...     pub_source=ppa_source,
    ...     status=PackagePublishingStatus.PUBLISHED)

Let's perform the copy of the source and its i386 binary.

    >>> series = hoary_test
    >>> pocket = PackagePublishingPocket.RELEASE
    >>> archive = cprov.archive

    >>> copied_source = ppa_source.copyTo(series, pocket, archive)

    >>> ppa_binary_i386 = ppa_binaries[0]
    >>> print(ppa_binary_i386.displayname)
    mno-bin 999 in breezy-autotest i386

    >>> copied_binary = ppa_binary_i386.copyTo(series, pocket, archive)

The source and binary are present in hoary-test:

    >>> copied_source = IStore(SourcePackagePublishingHistory).get(
    ...     SourcePackagePublishingHistory, copied_source.id)
    >>> print(copied_source.displayname)
    mno 999 in hoary-test

    >>> for bin in copied_source.getPublishedBinaries():
    ...     print(bin.displayname)
    mno-bin 999 in hoary-test amd64
    mno-bin 999 in hoary-test i386

So, no builds are created.

    >>> copied_source.createMissingBuilds()
    []


getSourceAndBinaryLibraryFiles
==============================

This method retrieves LibraryFileAlias records for all source and binary
files associated with this publication.

Using the same Ubuntu source publishing example as above:

    >>> for file in source.getSourceAndBinaryLibraryFiles():
    ...     print(file.filename)
    ghi-bin_666_hppa.deb
    ghi-bin_666_i386.deb
    ghi_666.dsc

We can also publish a package in a PPA and query on its files:

    >>> ppa_source = test_publisher.getPubSource(
    ...     sourcename='pqr',
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     archive=cprov.archive)
    >>> ppa_binaries= test_publisher.getPubBinaries(
    ...     binaryname='pqr-bin',
    ...     pub_source=ppa_source,
    ...     status=PackagePublishingStatus.PUBLISHED)

    >>> for file in ppa_source.getSourceAndBinaryLibraryFiles():
    ...     print(file.filename)
    pqr-bin_666_all.deb
    pqr_666.dsc


Publishing records age
======================

Both ISourcePackagePublishingHistory and IBinaryPackagePublishingHistory
implement the 'age' property which return a timedelta representing
"NOW - datecreated".

    >>> ppa_source.age
    datetime.timedelta(...)

    >>> ppa_binaries[0].age
    datetime.timedelta(...)


Binary and Binary File Publishing
=================================

Symmetric behaviour is offered for BinaryPackagePublishing,
BinaryPackageFile and IBinaryPackagePublishingHistory

    >>> from lp.soyuz.interfaces.files import (
    ...     IBinaryPackageFile)

    >>> bpph = IStore(BinaryPackagePublishingHistory).get(
    ...     BinaryPackagePublishingHistory, 15)
    >>> print(bpph.displayname)
    mozilla-firefox 0.9 in woody i386

    >>> IBinaryPackagePublishingHistory.providedBy(bpph)
    True

    >>> any_file = bpph.files[-1]
    >>> IBinaryPackageFile.providedBy(any_file)
    True

    >>> for pub_file in bpph.files:
    ...     print(pub_file.libraryfile.filename)
    mozilla-firefox_0.9_i386.deb

Binary publishing records also have a download count, which contains
the number of downloads of this binary package release in this archive.

    >>> print(bpph.getDownloadCount())
    0

    >>> from datetime import date
    >>> from lp.services.worlddata.interfaces.country import ICountrySet
    >>> australia = getUtility(ICountrySet)['AU']
    >>> uk = getUtility(ICountrySet)['GB']

    >>> bpph.archive.updatePackageDownloadCount(
    ...     bpph.binarypackagerelease, date(2010, 2, 19), None, 2)
    >>> bpph.archive.updatePackageDownloadCount(
    ...     bpph.binarypackagerelease, date(2010, 2, 21), australia, 10)
    >>> bpph.archive.updatePackageDownloadCount(
    ...     bpph.binarypackagerelease, date(2010, 2, 21), uk, 4)

    >>> print(bpph.getDownloadCount())
    16

We can also use getDownloadCounts to find the raw download counts per
day and country.

    >>> for b in bpph.getDownloadCounts():
    ...     print(b.day)
    ...     print(b.country.name if b.country is not None else None)
    2010-02-21 Australia
    2010-02-21 United Kingdom
    2010-02-19 None

getDownloadCounts lets us filter by date.

    >>> [b.day for b in bpph.getDownloadCounts(start_date=date(2010, 2, 21))]
    [datetime.date(2010, 2, 21), datetime.date(2010, 2, 21)]
    >>> [b.day for b in bpph.getDownloadCounts(end_date=date(2010, 2, 20))]
    [datetime.date(2010, 2, 19)]
    >>> [b.day for b in bpph.getDownloadCounts(
    ...     start_date=date(2010, 2, 20), end_date=date(2010, 2, 20))]
    []

We can also get a dict of totals for each day. The keys are strings to
work around lazr.restful's dict limitations. This too has a date filter.

    >>> for day, total in sorted(bpph.getDailyDownloadTotals().items()):
    ...     print('%s: %d' % (day, total))
    2010-02-19: 2
    2010-02-21: 14
    >>> for day, total in sorted(bpph.getDailyDownloadTotals(
    ...         start_date=date(2010, 2, 20)).items()):
    ...     print('%s: %d' % (day, total))
    2010-02-21: 14


IPublishingSet
==============

This utility implements the following methods:

 * newSourcePublication();

which create new publishing records, and:

 * getBuildsForSources();
 * getUnpublishedBuildsForSources();
 * getFilesForSources();
 * getBinaryPublicationsForSources();

which receive a list of `SourcePackagePublishingHistory` objects and
fetch the corresponding information for all of them.

Their returned `ResultSet` (they all use storm natively) follows a
pattern:

 * (`SourcePackagePublishingHistory`, <object>, [prejoins,])

This way the useful references gets cached and the callsites can group
the results as necessary.

The `IPublishingSet` methods are also used to implement the corresponding
features in `ISourcePackagePublishingHistory`:

 * getBuilds -> IPublishingSet.getBuildsForSources;
 * getSourceAndBinaryLibraryFiles -> IPublishingSet.getFilesForSources;
 * getPublishedBinaries -> IPublishingSet.getBinaryPublicationsForSources;

So, they were already tested implicitly before in this file, they
simply use the IPublishing methods passing only a single source
publication. Now we will document how they work for multiple source
publications.

    >>> publishing_set = getUtility(IPublishingSet)
    >>> verifyObject(IPublishingSet, publishing_set)
    True


Creating new publication records
--------------------------------

newSourcePublication() will create a source publication record. It is
already implicitly tested above via the copyTo method which uses it to
create new records.  However, it has one extra feature which is
important for PPAs - it will ensure that the published component is
always 'main'.

When copying publications from non-main components in the primary archive,
the PPA publication will always be main:

    >>> test_source_pub = test_publisher.getPubSource(
    ...     sourcename='overrideme', component='universe')
    >>> ppa_pub = publishing_set.newSourcePublication(
    ...     archive=mark.archive,
    ...     sourcepackagerelease=test_source_pub.sourcepackagerelease,
    ...     distroseries=mark.archive.distribution.currentseries,
    ...     component=test_source_pub.component,
    ...     section=test_source_pub.section,
    ...     pocket=test_source_pub.pocket)
    >>> print(ppa_pub.component.name)
    main

IPublishingSet is an essential component for
`ArchiveSourcePublications` feature, see more  information below in
its corresponding test section.

We will assembly a list of source publications based on what was
ever published in Celso's PPA.

    >>> cprov_sources = list(cprov.archive.getPublishedSources())
    >>> len(cprov_sources)
    8
    >>> for spph in cprov_sources:
    ...     print(spph.displayname)
    cdrkit 1.0 in breezy-autotest
    iceweasel 1.0 in warty
    jkl 666 in hoary-test
    jkl 666 in breezy-autotest
    mno 999 in hoary-test
    mno 999 in breezy-autotest
    pmount 0.1-1 in warty
    pqr 666 in breezy-autotest

Now that we have a set of source publications let's get the builds in
its context.

    >>> cprov_builds = publishing_set.getBuildsForSources(cprov_sources)

It returns a `ResultSet` and it contains 3-element tuples as
`SourcePackagePublishingHistory`, `Build` and `DistroArchseries` for
each build found.

    >>> cprov_builds.count()
    7

The `ResultSet` is ordered by ascending
`SourcePackagePublishingHistory.id` and ascending
`DistroArchseries.architecturetag` in this order.

    # The easiest thing we can do here (without printing ids)
    # is to show that sorting a list of the resulting ids+tags does not
    # modify the list.
    >>> ids_and_tags = [(pub.id, arch.architecturetag)
    ...     for pub, build, arch in cprov_builds]
    >>> ids_and_tags == sorted(ids_and_tags)
    True

If a source package is copied from another archive (including the
binaries), then the related builds for that source package will
also be retrievable via the copied source publication.
For example, if a package is built in a private security PPA, and then
later copied out into the primary archive, the builds will then
be available when looking at the copied source package in the primary
archive.

    # Create a new PPA and publish a source with some builds
    # and binaries.
    >>> other_ppa = factory.makeArchive(name="otherppa")
    >>> binaries = test_publisher.getPubBinaries(archive=other_ppa)

The associated builds and binaries will be created in the context of the
other PPA.

    >>> build = binaries[0].binarypackagerelease.build
    >>> source_pub = build.source_package_release.publishings[0]
    >>> print(build.archive.name)
    otherppa

    # Copy the source into Celso's PPA, ensuring that the binaries
    # are alse published there.
    >>> source_pub_cprov = source_pub.copyTo(
    ...     source_pub.distroseries, source_pub.pocket,
    ...     cprov.archive)
    >>> binaries_cprov = test_publisher.publishBinaryInArchive(
    ...     binaries[0].binarypackagerelease, cprov.archive)

Now we will see an extra source in Celso's PPA as well as an extra
build - even though the build's context is not Celso's PPA. Previously
there were 8 sources and builds.

    >>> cprov_sources_new = cprov.archive.getPublishedSources()
    >>> cprov_sources_new.count()
    9

    >>> cprov_builds_new = publishing_set.getBuildsForSources(
    ...     cprov_sources_new)
    >>> cprov_builds_new.count()
    8

Next we'll create two sources with two builds each (the SoyuzTestPublisher
default) and show that the number of unpublished builds for these sources
is correct:

    >>> sources = []
    >>> builds = []
    >>> for count in range(2):
    ...     spph = test_publisher.getPubSource(
    ...     sourcename='stu', architecturehintlist='any')
    ...     missing_builds = spph.createMissingBuilds()
    ...     for build in missing_builds:
    ...         build.updateStatus(BuildStatus.FULLYBUILT)
    ...         builds.append(build)
    ...     sources.append(spph)
    >>> len(builds)
    4

    >>> unpublished_builds = (
    ...     publishing_set.getUnpublishedBuildsForSources(sources))
    >>> unpublished_builds.count()
    4

If we then publish one of the builds, the number of unpublished builds
reflects the change:

    >>> bpr = test_publisher.uploadBinaryForBuild(builds[0], 'foo-bin')
    >>> bpph = test_publisher.publishBinaryInArchive(bpr, sources[0].archive,
    ...     status=PackagePublishingStatus.PUBLISHED)
    >>> unpublished_builds = (
    ...     publishing_set.getUnpublishedBuildsForSources(sources))
    >>> unpublished_builds.count()
    3

Now we retrieve all binary publications for Celso's PPA sources.

    >>> cprov_binaries = publishing_set.getBinaryPublicationsForSources(
    ...     cprov_sources)

The returned `ResultSet` contains 5-element tuples as
(`SourcePackagePublishingHistory`, `BinaryPackagePublishingHistory`,
 `BinaryPackageRelease`, `BinaryPackageName`, `DistroArchSeries`).

    >>> cprov_binaries.count()
    11

This result is ordered by ascending
`SourcePackagePublishingHistory.id`, ascending `BinaryPackageName.name`,
ascending `DistroArchSeries.architecturetag and descending
`BinaryPackagePublishingHistory.id`.

    >>> (source_pub, binary_pub, binary, binary_name,
    ...  arch) = cprov_binaries.last()

    >>> print(source_pub.displayname)
    pqr 666 in breezy-autotest

    >>> print(binary_pub.displayname)
    pqr-bin 666 in breezy-autotest i386

    >>> print(binary.title)
    pqr-bin-666

    >>> print(binary_name.name)
    pqr-bin

    >>> print(arch.displayname)
    ubuntutest Breezy Badger Autotest i386

We can retrieve all files related with Celso's PPA publications.

    >>> cprov_files = publishing_set.getFilesForSources(
    ...     cprov_sources)

This `ResultSet` contains 3-element tuples as
(`SourcePackagePublishingHistory`, `LibraryFileAlias`,
`LibraryFileContent`)

    >>> cprov_files.count()
    14

This result are not ordered since it comes from SQL UNION, so call
sites are responsible to order them appropriately.

    >>> ordered_filenames = sorted(
    ...    file.filename for source, file, content in cprov_files)

    >>> print(ordered_filenames[0])
    firefox_0.9.2.orig.tar.gz

We can also retrieve just the binary files related with Celso's PPA
publications.

    >>> binary_files = publishing_set.getBinaryFilesForSources(
    ...     cprov_sources)
    >>> binary_files = binary_files.config(distinct=True)
    >>> binary_files.count()
    6

Please note how the result set is ordered by the id of `LibraryFileAlias`
(second element of the triple):

    >>> file_ids = [file.id for source, file, content in binary_files]
    >>> file_ids == sorted(file_ids)
    True

    >>> for source, file, content in binary_files:
    ...     print(file.filename)
    mozilla-firefox_0.9_i386.deb
    jkl-bin_666_all.deb
    jkl-bin_666_all.deb
    mno-bin_999_all.deb
    mno-bin_999_all.deb
    pqr-bin_666_all.deb

getChangesFilesForSources(), provided by IPublishingSet, allows
call sites to retrieve all .changes files related to a set of source
publications.

    >>> cprov_changes = publishing_set.getChangesFilesForSources(
    ...     cprov_sources)

    >>> cprov_changes.count()
    6

The returned ResultSet element is tuple containing:

 * `SourcePackagePublishingHistory`;
 * `PackageUpload`;
 * `SourcePackageRelease`;
 * `LibraryFileAlias`;
 * `LibraryFileContent`.

    >>> a_change = cprov_changes[0]

    >>> source_pub, upload, source, file, content = a_change

    >>> print(source_pub.displayname)
    iceweasel 1.0 in warty

    >>> print(upload.displayname)
    iceweasel

    >>> print(source.title)
    iceweasel - 1.0

    >>> print(file.filename)
    mozilla-firefox_0.9_i386.changes

    >>> print(content.md5)
    b14d7265706d0f5b19d5812d59a61d2a

Last but not least the publishing set class allows for the bulk deletion
of publishing history records.

    >>> cprov_sources = sorted(
    ...     cprov.archive.getPublishedSources(
    ...     status=PackagePublishingStatus.PUBLISHED),
    ...     key=operator.attrgetter('id'))
    >>> print(len(cprov_sources))
    6

We will delete the first two source publishing history records and
need to know the number of associated binary publishing history
records.

    >>> cprov_binaries = publishing_set.getBinaryPublicationsForSources(
    ...     cprov_sources)
    >>> cprov_binaries.count()
    9

This is the published binary that will get deleted.

    >>> cprov_binaries = publishing_set.getBinaryPublicationsForSources(
    ...     cprov_sources[:2])
    >>> cprov_binaries.count()
    1

Let's get rid of the first two source publishing history records and their
associated binary publishing records now.

    >>> deleted = publishing_set.requestDeletion(
    ...     cprov_sources[:2], cprov, 'OOPS-934EC47')

The number of published sources will decrease by two as expected.

    >>> cprov_sources = list(
    ...     cprov.archive.getPublishedSources(
    ...     status=PackagePublishingStatus.PUBLISHED))
    >>> print(len(cprov_sources))
    4

Analogously, the number of associated published binaries will be less
by one.

    >>> cprov_binaries = publishing_set.getBinaryPublicationsForSources(
    ...     cprov_sources)
    >>> cprov_binaries.count()
    8


ArchiveSourcePublications
=========================

`ArchiveSourcePublications` wraps `IPublishingSet` methods to build a
set of objects which decorate `ISourcePackagePublishingHistory` with
cached references.

All references related with the given set of source publications are
fetch in a fixed number of queries (3) instead of varying according
the size of the set (3 * N).

    >>> from lp.soyuz.adapters.archivesourcepublication import (
    ...     ArchiveSourcePublications)

We will use all published sources in Celso's PPA as our initial set.

    >>> cprov = getUtility(IPersonSet).getByName('cprov')
    >>> cprov_published_sources = cprov.archive.getPublishedSources(
    ...     status=PackagePublishingStatus.PUBLISHED)
    >>> for spph in cprov_published_sources:
    ...     print(spph.displayname)
    jkl 666 in breezy-autotest
    mno 999 in breezy-autotest
    pmount 0.1-1 in warty
    pqr 666 in breezy-autotest

We use the source publications to initialize
`ArchiveSourcePublications`.

    >>> decorated_set = ArchiveSourcePublications(cprov_published_sources)
    >>> empty_decorated_set = ArchiveSourcePublications([])

`ArchiveSourcePublications` implements __bool__, so callsites can
verify in advance whether there are elements to be iterated or not.

    >>> bool(decorated_set)
    True

    >>> bool(empty_decorated_set)
    False

Note that this check is *cheap* since it's based only on the given set
of source publications and doesn't require the class to fetch the
extra information. The extra information will be only fetch when the
set gets iterated.

The size of the `ArchiveSourcePublications` always matches the given
source publication set size:

    >>> cprov_published_sources.count()
    4

    >>> decorated_sources_list = list(decorated_set)
    >>> len(decorated_sources_list)
    4

The objects loaded have their newer_distroseries_version preloaded.

    >>> actual_pub = decorated_sources_list[0].context
    >>> get_property_cache(actual_pub).newer_distroseries_version

The decorated objects are returned in the same order used in the given
'source_publications'.

    >>> def compare_ids(given, returned):
    ...     given_ids = [obj.id for obj in given]
    ...     returned_ids = [obj.id for obj in returned]
    ...     if given_ids == returned_ids:
    ...        print('Matches')
    ...     else:
    ...        print('Mismatch:', given_ids, returned_ids)

    >>> compare_ids(cprov_published_sources, decorated_set)
    Matches

Now we will shuffle the order of the given publications, ensure they are
different, and check if the order is respected:

    >>> original_sources_list = list(cprov_published_sources)
    >>> shuffled_sources_list = list(cprov_published_sources)

    >>> import random
    >>> while (len(original_sources_list) > 1 and
    ...        shuffled_sources_list == original_sources_list):
    ...     random.shuffle(shuffled_sources_list)

    >>> shuffled_decorated_list = ArchiveSourcePublications(
    ...      shuffled_sources_list)

The shuffled sources list order is respected by
ArchiveSourcePublication.

    >>> compare_ids(shuffled_sources_list, shuffled_decorated_list)
    Matches

And the order is not the same than the original source set.

    >>> compare_ids(original_sources_list, shuffled_decorated_list)
    Mismatch: ...

We will check a little bit of the `ArchiveSourcePublications`
internals. There is one essential method to fetch distinct
information to be cached in the decorated objects:

  * getChangesFileBySources

They exclude the extra references ('prejoins') returned  from the
corresponding `IPublishingSet` methods and group the wanted results as
a dictionary, keyed by `SourcePackagePublishingHistory `, in way they
can be quickly looked up when building `ArchiveSourcePublications`.

    >>> real_pub = cprov_published_sources[1]

getChangesFileBySources() returns a dictionary mapping each individual
source package publication to its corresponding .changes file (as a
LibraryFileAlias).

    >>> all_cprov_sources = cprov.archive.getPublishedSources()
    >>> for spph in all_cprov_sources:
    ...     print(spph.displayname)
    cdrkit 1.0 in breezy-autotest
    foo 666 in breezy-autotest
    iceweasel 1.0 in warty
    jkl 666 in hoary-test
    jkl 666 in breezy-autotest
    mno 999 in hoary-test
    mno 999 in breezy-autotest
    pmount 0.1-1 in warty
    pqr 666 in breezy-autotest

We select the only available publication in Celso's PPA with a valid
.changes file in the sampledata.

    >>> pub_with_changes = all_cprov_sources[2]
    >>> the_source = pub_with_changes.sourcepackagerelease
    >>> the_change = the_source.upload_changesfile
    >>> print(the_change.filename)
    mozilla-firefox_0.9_i386.changes

The same control-publication is reachable in the dictionary returned
by getChangesFileBySources().

    >>> decorated_changes = ArchiveSourcePublications(all_cprov_sources)
    >>> changes_by_source = decorated_changes.getChangesFileBySource()
    >>> decorated_change = changes_by_source.get(pub_with_changes)
    >>> print(decorated_change.filename)
    mozilla-firefox_0.9_i386.changes

Enough internals! What really matters for callsites is that, when
iterated, `ArchiveSourcePublications`returns `ArchiveSourcePublication`
objects that decorates `ISourcePackagePublishingHistory` and have
expensive references for other objects already cached. This makes the
whole difference when rendering PPA pages with many source
publications.

    >>> decorated_pub = list(decorated_set)[1]

    >>> print(decorated_pub)
    <...ArchiveSourcePublication ...>

    >>> verifyObject(ISourcePackagePublishingHistory, decorated_pub)
    True

The 'sourcepackagerelease' attribute from a decorated
`ArchiveSourcePublication` object is also another decorated object,
this way we can cache information refered to:

 * upload_changesfile.

We select an arbitrary source publication from Celso's PPA added by
`SoyuzTestPublisher`. It contains the same corresponding
`PackageUpload.changesfile` in both, the real and the decorated
objects.

    >>> pub_with_changes = cprov_published_sources[1]
    >>> the_source = pub_with_changes.sourcepackagerelease
    >>> changesfile = the_source.upload_changesfile
    >>> print('%s (%s)' % (changesfile.filename, changesfile.content.md5))
    mno_999_source.changes (6168e17ba012fc3db6dc77e255243bd1)

    >>> decorated_pub_with_changes = list(decorated_set)[1]
    >>> decorated_source = decorated_pub_with_changes.sourcepackagerelease
    >>> changesfile = decorated_source.upload_changesfile
    >>> print('%s (%s)' % (changesfile.filename, changesfile.content.md5))
    mno_999_source.changes (6168e17ba012fc3db6dc77e255243bd1)

`ArchiveSourcePublication` also has a decorated version of the
getStatusSummaryForBuilds() method.

    >>> print_build_status_summary(
    ...     decorated_pub.getStatusSummaryForBuilds())
    FULLYBUILT
    i386 build of mno 999 in ubuntutest breezy-autotest RELEASE


IPublishingSet.getBuildStatusSummariesForSourceIdsAndArchive()
==============================================================

This extra method on IPublishingSet allows a summary of the build status
for a set of sources to be presented. The corresponding archive is a
required parameter that ensures that this method only
returns information about builds from the specified archive (as this method
is used via the API via IArchive.getBuildSummariesForSourceIds).

First we'll create two source publishing history records:

    >>> firefox_source_pub = test_publisher.getPubSource(
    ...     sourcename='firefox-test')
    >>> binaries = test_publisher.getPubBinaries(
    ...     pub_source=firefox_source_pub,
    ...     status=PackagePublishingStatus.PUBLISHED)
    >>> foo_pub = test_publisher.getPubSource(sourcename='foobar-test')
    >>> binaries = test_publisher.getPubBinaries(pub_source=foo_pub,
    ...     status=PackagePublishingStatus.PUBLISHED)

    >>> from lp.registry.interfaces.distribution import (
    ...     IDistributionSet)
    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> ubuntu_test = getUtility(IDistributionSet)['ubuntutest']

Create a small function for displaying the results:

    >>> def print_build_summary(summary):
    ...     print("%s\n%s\nRelevant builds:\n%s" % (
    ...         summary['status'].title,
    ...         summary['status'].description,
    ...         "\n".join(
    ...             " - %s" % build.title for build in summary['builds'])
    ...     ))

    >>> def print_build_summaries(summaries):
    ...     count = 0
    ...     for source_id, summary in sorted(summaries.items()):
    ...         count += 1
    ...         print("Source number: %s" % count)
    ...         print_build_summary(summary)

And then grab the build summaries for firefox and foo:

    >>> build_summaries = \
    ...     publishing_set.getBuildStatusSummariesForSourceIdsAndArchive(
    ...         [firefox_source_pub.id, foo_pub.id],
    ...         ubuntu_test.main_archive)
    >>> print_build_summaries(build_summaries)
    Source number: 1
    FULLYBUILT
    All builds were built successfully.
    Relevant builds:
     - i386 build of firefox-test 666 in ubuntutest breezy-autotest RELEASE
    Source number: 2
    FULLYBUILT
    All builds were built successfully.
    Relevant builds:
     - i386 build of foobar-test 666 in ubuntutest breezy-autotest RELEASE

Any of the source ids passed into
getBuildStatusSummariesForSourceIdsAndArchive that do not belong to the
required archive parameter will be ignored:

    >>> build_summaries = \
    ...     publishing_set.getBuildStatusSummariesForSourceIdsAndArchive(
    ...         [firefox_source_pub.id, foo_pub.id],
    ...         archive=ubuntu.main_archive)
    >>> print_build_summaries(build_summaries)
