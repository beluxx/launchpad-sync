DistributionSourcePackageRelease views
======================================

    # Create a brand new publication of 'testing-dspr - 1.0' for tests.
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> stp = SoyuzTestPublisher()
    >>> login("foo.bar@canonical.com")
    >>> stp.prepareBreezyAutotest()
    >>> source = stp.getPubSource("testing-dspr", version="1.0")
    >>> login(ANONYMOUS)

    >>> dspr = stp.ubuntutest.getSourcePackageRelease(
    ...     source.sourcepackagerelease
    ... )

`DistributionSourcePackageReleaseView` provides 'page_title', which
simply mimics the `DistributionSourcePackageRelease.title`.

    >>> dspr_view = create_initialized_view(dspr, name="+index")

    >>> print(dspr.title)
    testing-dspr 1.0 source package in ubuntutest

    >>> print(dspr_view.page_title)
    testing-dspr 1.0 source package in ubuntutest

The 'files' property returns a list of files included in the source
upload encapsulated as `ProxiedSourceLibraryFileAlias` objects. Their
'http_url' points to the LP proxied url which normalizes the path
tofiles allowing them to be downloaded using `dget`.

    >>> for source_file in dspr_view.files:
    ...     print(source_file.filename, source_file.http_url)  # noqa
    ...
    testing-dspr_1.0.dsc
    http://.../ubuntutest/+archive/primary/+sourcefiles/testing-dspr/1.0/testing-dspr_1.0.dsc

The 'sponsor' property indicates whether the upload was 'sponsored' or
not. When the upload was signed by someone else than the source
creator, the upload signer is the sponsor.

    >>> print(dspr.creator.displayname)
    Foo Bar

    >>> print(dspr_view.sponsor)
    None

    # Forcibly change the SPR.creator, so the source becomes 'sponsored'.
    >>> from zope.security.proxy import removeSecurityProxy
    >>> login("foo.bar@canonical.com")
    >>> a_person = factory.makePerson(name="novice")
    >>> removeSecurityProxy(dspr.sourcepackagerelease).creator = a_person
    >>> login(ANONYMOUS)

    >>> dspr_view = create_initialized_view(dspr, name="+index")

    >>> print(dspr.creator.displayname)
    Novice

    >>> print(dspr_view.sponsor.displayname)
    Foo Bar

'currently_published' contains only PUBLISHED publications for this
`DistributionSourcePackageRelease` object. Since the testing DSPR only
contains a PENDING publication (see `SoyuzTestPublisher.getPubSource`)
this property is empty.

    >>> len(dspr_view.currently_published)
    0

It gets populated according to the publishing cycle, and subsequent
copies.

    # Publish the pending testing publication.
    >>> login("foo.bar@canonical.com")
    >>> source.setPublished()
    >>> transaction.commit()
    >>> login(ANONYMOUS)

    >>> dspr_view = create_initialized_view(dspr, name="+index")
    >>> for publishing in dspr_view.currently_published:
    ...     print(publishing.distroseries.name)
    ...
    breezy-autotest

    # Copy the testing publication to another series.
    >>> from lp.soyuz.interfaces.publishing import PackagePublishingPocket
    >>> login("foo.bar@canonical.com")
    >>> release_pocket = PackagePublishingPocket.RELEASE
    >>> hoary = stp.ubuntutest.getSeries("hoary-test")
    >>> copied_source = source.copyTo(
    ...     hoary, release_pocket, stp.ubuntutest.main_archive
    ... )
    >>> copied_source.setPublished()
    >>> transaction.commit()
    >>> login(ANONYMOUS)

    >>> dspr_view = create_initialized_view(dspr, name="+index")
    >>> for publishing in dspr_view.currently_published:
    ...     print(publishing.distroseries.name)
    ...
    hoary-test
    breezy-autotest

'grouped_builds' returns a list of dictionaries which contains
`IBuild`s for a given `IDistroSeries`.

    >>> def print_grouped_builds():
    ...     for build_group in dspr_view.grouped_builds:
    ...         arch_tags = " ".join(
    ...             build.arch_tag for build in build_group["builds"]
    ...         )
    ...         print(
    ...             "%s: %s" % (build_group["distroseries"].name, arch_tags)
    ...         )
    ...     print("END")
    ...

    >>> print_grouped_builds()
    END

    # Create default builds for the testing DSPR.
    >>> login("foo.bar@canonical.com")
    >>> unused = source.createMissingBuilds()
    >>> login(ANONYMOUS)

    >>> dspr_view = create_initialized_view(dspr, name="+index")
    >>> print_grouped_builds()
    breezy-autotest: i386
    END

The returned dictionaries are ordered by descending distroseries
version and their 'builds' are ordered by ascending 'architecturetag'.

    # Create extras builds for the testing DSPR.
    >>> login("foo.bar@canonical.com")
    >>> hoary_amd64 = hoary["amd64"]
    >>> from lp.soyuz.interfaces.binarypackagebuild import (
    ...     IBinaryPackageBuildSet,
    ... )
    >>> unused = getUtility(IBinaryPackageBuildSet).new(
    ...     source.sourcepackagerelease,
    ...     stp.ubuntutest.main_archive,
    ...     hoary_amd64,
    ...     release_pocket,
    ... )
    >>> breezy_hppa = stp.breezy_autotest["hppa"]
    >>> unused = getUtility(IBinaryPackageBuildSet).new(
    ...     source.sourcepackagerelease,
    ...     stp.ubuntutest.main_archive,
    ...     breezy_hppa,
    ...     release_pocket,
    ... )
    >>> login(ANONYMOUS)

    >>> dspr_view = create_initialized_view(dspr, name="+index")
    >>> print_grouped_builds()
    hoary-test: amd64
    breezy-autotest: hppa i386
    END
