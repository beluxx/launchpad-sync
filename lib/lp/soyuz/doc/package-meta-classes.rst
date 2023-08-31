Package Meta Classes
^^^^^^^^^^^^^^^^^^^^

There are a bunch of meta classes used for combine information from
our Database Model for packages in a intuitive manner, they are:

    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet,
    ... )
    >>> from lp.registry.model.distribution import Distribution
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.model.distributionsourcepackagerelease import (
    ...     DistributionSourcePackageRelease,
    ... )
    >>> from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease

    >>> from lp.soyuz.interfaces.distributionsourcepackagerelease import (
    ...     IDistributionSourcePackageRelease,
    ... )


DistributionSourcePackage class is tested in:
    distribution-sourcepackage.rst

Combining Distribution and SourcePackageRelease:

    >>> distribution = Distribution.get(1)
    >>> print(distribution.name)
    ubuntu

    >>> src_name = getUtility(ISourcePackageNameSet)["pmount"]
    >>> print(src_name.name)
    pmount

    >>> sourcepackagerelease = (
    ...     IStore(SourcePackageRelease)
    ...     .find(
    ...         SourcePackageRelease,
    ...         sourcepackagename=src_name,
    ...         version="0.1-1",
    ...     )
    ...     .one()
    ... )
    >>> print(sourcepackagerelease.name)
    pmount

    >>> from lp.testing import verifyObject
    >>> dspr = DistributionSourcePackageRelease(
    ...     distribution, sourcepackagerelease
    ... )
    >>> verifyObject(IDistributionSourcePackageRelease, dspr)
    True

    >>> print(dspr.displayname)
    pmount 0.1-1


Querying builds for DistributionSourcePackageRelease
----------------------------------------------------

DistributionSourcePackageRelease objects have a builds() method which
returns all the builds for the source package that have been published
in a main archive.

The build may have been built and published initially in a PPA (such as a
security PPA), but it will only be included in the results if it has also
been published in a main archive.

First, publish a build in the main archive of ubuntutest.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.soyuz.enums import PackagePublishingStatus
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> login("foo.bar@canonical.com")
    >>> ubuntutest = getUtility(IDistributionSet)["ubuntutest"]
    >>> test_publisher = SoyuzTestPublisher()
    >>> test_publisher.prepareBreezyAutotest()
    >>> source_pub = test_publisher.getPubSource(
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     sourcename="foo",
    ...     archive=ubuntutest.main_archive,
    ... )
    >>> [build] = source_pub.createMissingBuilds()

We also need to ensure that a binary pkg release has been published in the
archive:

    >>> binary_pkg_release = test_publisher.uploadBinaryForBuild(
    ...     build, "foo-bin"
    ... )
    >>> binary_pkg_pub_history = test_publisher.publishBinaryInArchive(
    ...     binary_pkg_release, ubuntutest.main_archive
    ... )

Next we create our DistributionSourcePackageRelease.

    >>> breezy_autotest = ubuntutest["breezy-autotest"]
    >>> ubuntutest_dspr_foo = DistributionSourcePackageRelease(
    ...     ubuntutest, source_pub.sourcepackagerelease
    ... )

Create a helper for printing builds:

    >>> def print_builds(builds):
    ...     for build in builds:
    ...         print(
    ...             "%s in %s"
    ...             % (
    ...                 build.source_package_release.name,
    ...                 build.archive.displayname,
    ...             )
    ...         )
    ...

Now we can query the builds:

    >>> print_builds(ubuntutest_dspr_foo.builds)
    foo in Primary Archive for Ubuntu Test

If we add a build to the partner archive, it is included in the
results as well.

    >>> partner_archive = ubuntutest.all_distro_archives[1]
    >>> partner_pub = source_pub.copyTo(
    ...     breezy_autotest, source_pub.pocket, partner_archive
    ... )
    >>> [partner_build] = partner_pub.createMissingBuilds()
    >>> binary_pkg_release = test_publisher.uploadBinaryForBuild(
    ...     partner_build, "foo-bin"
    ... )
    >>> binary_pkg_pub_history = test_publisher.publishBinaryInArchive(
    ...     binary_pkg_release, partner_archive
    ... )

    >>> print_builds(ubuntutest_dspr_foo.builds)
    foo in Partner Archive for Ubuntu Test
    foo in Primary Archive for Ubuntu Test

If we publish the source and binary in a PPA,

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> source_pub = test_publisher.getPubSource(
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     sourcename="bar",
    ...     archive=cprov.archive,
    ... )
    >>> [build] = source_pub.createMissingBuilds()
    >>> binary_pkg_release = test_publisher.uploadBinaryForBuild(
    ...     build, "bar-bin"
    ... )
    >>> binary_pkg_pub_history = test_publisher.publishBinaryInArchive(
    ...     binary_pkg_release, cprov.archive
    ... )
    >>> ubuntutest_dspr_bar = DistributionSourcePackageRelease(
    ...     ubuntutest, source_pub.sourcepackagerelease
    ... )

the build will not be returned.

    >>> print_builds(ubuntutest_dspr_bar.builds)

But if the package is copied into the main archive (and the binary published
there) then it will then be included in the results.

    >>> main_pub = source_pub.copyTo(
    ...     breezy_autotest, source_pub.pocket, ubuntutest.main_archive
    ... )
    >>> binary_pkg_pub_history = test_publisher.publishBinaryInArchive(
    ...     binary_pkg_release, ubuntutest.main_archive
    ... )

    >>> print_builds(ubuntutest_dspr_bar.builds)
    bar in PPA for Celso Providelo

