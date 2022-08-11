Retrieving upload information
=============================

We can retrieve the original upload information in the form of a
`PackageUpload` object for all `SourcePackageRelease` or `Build`
objects uploaded to system.

Both `SourcePackageRelease` and `Build` implement the following
properties:

 * 'package_upload': the `PackageUpload`
 * 'upload_changesfile': the `PackageUpload.changesfile`, an
      `LibraryFileAlias`.

Those fields are always not-null for sources and builds that were
'uploaded' to the system.

The only exception to this rule are packages 'imported' into the system
from other repositories. They do not have any relevant upload
information to be stored.


Auditing the sampledata
=======================

For the sake of consistency, we can implicitly probe the lookups
described above against all existing source publications and builds
in the sampladata.

    # Audit the source publication and builds of a given archive
    # and report missing uploads.
    >>> from lp.buildmaster.enums import BuildStatus
    >>> def check_upload_lookups(archive):
    ...     sources_missing_upload = []
    ...     sources = list(archive.getPublishedSources())
    ...     for source in sources:
    ...         source_release = source.sourcepackagerelease
    ...         package_upload = source_release.package_upload
    ...         changesfile = source_release.upload_changesfile
    ...         if package_upload is None or changesfile is None:
    ...            sources_missing_upload.append(source)
    ...     builds_missing_upload = []
    ...     builds = list(
    ...         archive.getBuildRecords(build_state=BuildStatus.FULLYBUILT))
    ...     for build in builds:
    ...         package_upload = build.package_upload
    ...         changesfile = build.upload_changesfile
    ...         if package_upload is None or changesfile is None:
    ...            builds_missing_upload.append(builds)
    ...     print('* %s' % archive.displayname)
    ...     print('%d of %d sources and %d of %d builds missing uploads' % (
    ...        len(sources_missing_upload), len(sources),
    ...        len(builds_missing_upload), len(builds)))

As we can see from the results below, most of our sampledata are
sources and builds directly imported into the system, not
uploaded. However it's a legitimate scenario that doesn't break the
assumptions done in the lookups.

    >>> from lp.registry.interfaces.distribution import (
    ...     IDistributionSet)
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

    >>> for archive in ubuntu.all_distro_archives:
    ...     check_upload_lookups(archive)
    * Primary Archive for Ubuntu Linux
    17 of 20 sources and 6 of 8 builds missing uploads
    * Partner Archive for Ubuntu Linux
    0 of 1 sources and 1 of 1 builds missing uploads

    >>> for ppa in ubuntu.getAllPPAs():
    ...     check_upload_lookups(ppa)
    * PPA for Celso Providelo
    2 of 3 sources and 3 of 3 builds missing uploads
    * PPA for Mark Shuttleworth
    0 of 1 sources and 0 of 0 builds missing uploads
    * PPA for No Privileges Person
    0 of 0 sources and 0 of 0 builds missing uploads

    >>> ubuntutest = getUtility(IDistributionSet).getByName(
    ...     'ubuntutest')
    >>> for archive in ubuntutest.all_distro_archives:
    ...     check_upload_lookups(archive)
    * Primary Archive for Ubuntu Test
    1 of 1 sources and 0 of 0 builds missing uploads
    * Partner Archive for Ubuntu Test
    0 of 0 sources and 0 of 0 builds missing uploads


Upload lookups in action
========================

We will create a brand new source publication for the subsequent
tests.

    # Create a testing source and its binaries in
    # ubuntutest/breezy-autotest/i386.
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> login('foo.bar@canonical.com')
    >>> test_publisher = SoyuzTestPublisher()
    >>> test_publisher.prepareBreezyAutotest()
    >>> source = test_publisher.getPubSource(
    ...     sourcename='testing', version='1.0')
    >>> binaries = test_publisher.getPubBinaries(
    ...     binaryname='testing-bin', pub_source=source)
    >>> [build] = source.getBuilds()
    >>> transaction.commit()
    >>> login(ANONYMOUS)

The `SourcePackageRelease` 'package_upload' and 'upload_changesfile'

    >>> original_source_upload = source.sourcepackagerelease.package_upload
    >>> print(original_source_upload)
    <lp.soyuz.model.queue.PackageUpload ...>

    >>> source_changesfile = source.sourcepackagerelease.upload_changesfile
    >>> original_source_upload.changesfile == source_changesfile
    True

    >>> print(source_changesfile.filename)
    testing_1.0_source.changes

The `Build` 'package_upload' and 'upload_changesfile'

    >>> original_build_upload = build.package_upload
    >>> print(original_build_upload)
    <...PackageUpload ...>

    >>> build_changesfile = build.upload_changesfile
    >>> original_build_upload.changesfile == build_changesfile
    True

    >>> print(build_changesfile.filename)
    testing-bin_1.0_i386.changes

The `PackageUpload` lookups are not restricted to the status of the
upload, i.e., new, rejected, unapproved or accepted items are returned
as well.

    >>> login('foo.bar@canonical.com')
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.soyuz.enums import PackageUploadStatus
    >>> from lp.soyuz.model.queue import PassthroughStatusValue
    >>> removeSecurityProxy(original_build_upload).status = (
    ...     PassthroughStatusValue(PackageUploadStatus.NEW))
    >>> transaction.commit()
    >>> login(ANONYMOUS)

    >>> original_source_upload == source.sourcepackagerelease.package_upload
    True

    >>> original_build_upload == build.package_upload
    True
