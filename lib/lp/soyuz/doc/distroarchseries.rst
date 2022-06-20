==================
Distro Arch Series
==================

    >>> from lp.testing import verifyObject

    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> from lp.soyuz.interfaces.distroarchseriesbinarypackage import (
    ...     IDistroArchSeriesBinaryPackage,
    ...     )
    >>> from lp.soyuz.interfaces.publishing import (
    ...     IBinaryPackagePublishingHistory
    ...     )
    >>> from lp.soyuz.interfaces.section import ISectionSet

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> hoary = ubuntu.getSeries('hoary')

DistroArchSeries are retrieved via __getitem__:

    >>> hoary_i386 = hoary['i386']

or getDistroArchSeries():

    >>> hoary_hppa = hoary.getDistroArchSeries('hppa')

# XXX: daniels 2005-10-17 bug=3257:
#      This needs many more tests to be effective.


Properties
==========

Enabled is a boolean flag that says whether the arch will receive new builds
and publish them.

    >>> print(hoary_i386.enabled)
    True

`DistroSeries.enabled_architectures` is a `ResultSet` containing the
architectures with that flag set.

    >>> hoary_i386 in hoary.enabled_architectures
    True
    >>> from lp.testing import celebrity_logged_in
    >>> with celebrity_logged_in('admin'):
    ...     hoary_i386.enabled = False
    >>> hoary_i386 in hoary.enabled_architectures
    False


DistroArchSeries can tell you about their published releases
============================================================

Check the behaviour of the provided search method, which returns a
list of IDARBPR instances containing the matching packages.

    >>> results = hoary_i386.searchBinaryPackages(text=u'pmount')
    >>> results.count()
    1
    >>> pmount = results[0]

The method works even when we are searching for packages whose names are
not fti-matchable, such as "linux-2.6.12", and substrings:

    >>> warty = ubuntu.getSeries('warty')
    >>> warty_i386 = warty['i386']
    >>> results = warty_i386.searchBinaryPackages(text=u'linux-2.6.12')
    >>> results.count()
    1
    >>> results = warty_i386.searchBinaryPackages(text=u'a')
    >>> for dasbp in results:
    ...     print("%s: %s" % (dasbp.__class__.__name__, dasbp.name))
    DistroArchSeriesBinaryPackageRelease: at
    DistroArchSeriesBinaryPackageRelease: mozilla-firefox
    DistroArchSeriesBinaryPackageRelease: mozilla-firefox
    DistroArchSeriesBinaryPackageRelease: mozilla-firefox-data

    # XXX cprov 2006-03-21: Broken implementation, missing enhances attribute.
    verifyObject(IDistroArchSeriesBinaryPackageRelease, pmount)
    True

Check IDARBP provider

    >>> pmount_hoary_i386 = hoary_i386.getBinaryPackage('pmount')

    >>> verifyObject(IDistroArchSeriesBinaryPackage, pmount_hoary_i386)
    True

    >>> print(pmount_hoary_i386.name)
    pmount


Check some properties of DARBP meta class

Entire publishing history:

    >>> pmount_hoary_i386.publishing_history.count()
    2

Most recent published history row:

    >>> bpph = pmount_hoary_i386.current_published

    # XXX cprov 2006-03-22: The object doesn't pass verifyObject()
    # due the lack of distroarchseriesbinarypackagerelease attribute.

    >>> IBinaryPackagePublishingHistory.providedBy(bpph)
    True

    >>> print(bpph.section.name)
    editors

Perform `post publication` override:

    >>> new_section = getUtility(ISectionSet)['base']
    >>> version = bpph.binarypackagerelease.version
    >>> pmount_hoary_i386_released = pmount_hoary_i386[version]

    >>> from lp.testing import person_logged_in
    >>> pmount_i386_pub = pmount_hoary_i386_released.current_publishing_record
    >>> with person_logged_in(ubuntu.main_archive.owner):
    ...     override = pmount_i386_pub.changeOverride(
    ...         new_section=new_section)
    >>> override.section == new_section
    True
    >>> override.status.name
    'PENDING'
    >>> pub_hist = pmount_hoary_i386.publishing_history
    >>> pub_hist.count()
    3

Override information about 'pmount' is pending publication:

    >>> print(pub_hist[0].status.name)
    PENDING
    >>> print(pub_hist[0].section.name)
    base

Supersede current publication:

    >>> pub = pmount_hoary_i386_released.current_publishing_record
    >>> pub.supersede()
    >>> pmount_hoary_i386.publishing_history.count()
    3

    >>> print(pub.status.name, pub.datesuperseded is not None)
    SUPERSEDED True


DistroArchSeries Lookup
=======================

The architectures related to a specific distroseries can be retrieved
via the 'architectures' property.

    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> warty = ubuntu['warty']
    >>> hoary = ubuntu['hoary']

    >>> def print_architectures(architectures):
    ...     for arch in architectures:
    ...         result = arch.title
    ...         if arch.official or arch.supports_virtualized:
    ...             result += ' ('
    ...         if arch.official:
    ...             result += 'official'
    ...             if arch.supports_virtualized:
    ...                 result += ', '
    ...         if arch.supports_virtualized:
    ...             result += 'ppa'
    ...         if arch.official or arch.supports_virtualized:
    ...             result += ')'
    ...         print(result)

    >>> print_architectures(warty.architectures)
    The Warty Warthog Release for hppa (hppa)
    The Warty Warthog Release for i386 (386) (official, ppa)

DistroArchSeries for which we support PPA building can be obtained via
another distroseries method called 'virtualized_architectures'.

For testing purposes we can compare the results of a
manually-calculated set of warty architectures for which we support
PPA  and the actual value returned from the 'ppa_architecture'
property.

    >>> expected_ppa_archs = [arch for arch in warty.architectures
    ...                       if arch.supports_virtualized is True]
    >>> print_architectures(expected_ppa_archs)
    The Warty Warthog Release for i386 (386) (official, ppa)

    >>> print_architectures(warty.virtualized_architectures)
    The Warty Warthog Release for i386 (386) (official, ppa)

Let's activate ppa support for hoary/hppa and check if
'virtualized_architectures' will include it this time.

    >>> print_architectures(hoary.virtualized_architectures)
    The Hoary Hedgehog Release for i386 (386) (official, ppa)

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> login('foo.bar@canonical.com')

    >>> hoary['hppa'].processor.supports_virtualized = True
    >>> flush_database_updates()

    >>> print_architectures(hoary.virtualized_architectures)
    The Hoary Hedgehog Release for hppa (hppa) (ppa)
    The Hoary Hedgehog Release for i386 (386) (official, ppa)

There is also `DistroSeries.buildable_architectures` which returns a
`ResultSet` containing only the `DistroArchSeries` with available
chroots tarballs (the ones for which we can build packages).

In the sampledata, none of the hoary architectures have chroot
tarballs. Once it is available the corresponding architecture is
returned.

    >>> hoary.buildable_architectures.count()
    0

    # Create a chroot tarball for hoary/hppa.
    >>> chroot = factory.makeLibraryFileAlias()
    >>> unused = hoary.getDistroArchSeries('hppa').addOrUpdateChroot(chroot)

    # Create a chroot tarball for hoary-updates/hppa too, to make sure that
    # this doesn't result in duplicate architectures.
    >>> updates_chroot = factory.makeLibraryFileAlias()
    >>> unused = hoary.getDistroArchSeries('hppa').addOrUpdateChroot(
    ...     updates_chroot, pocket=PackagePublishingPocket.UPDATES)

    >>> print_architectures(hoary.buildable_architectures)
    The Hoary Hedgehog Release for hppa (hppa) (ppa)

The architecture also has a 'chroot_url' attribute directly referencing
the file.

    >>> print(hoary.getDistroArchSeries('hppa').chroot_url)
    http://.../filename...
    >>> hoary.getDistroArchSeries('hppa').chroot_url == \
    ...     chroot.http_url
    True

If there is no chroot, chroot_url will be None.

    >>> print(hoary.getDistroArchSeries('i386').chroot_url)
    None

`DistroSeries.buildable_architectures` results are ordered
alphabetically by 'architecturetag'.

    # Create a chroot tarball for hoary/i386.
    >>> unused = hoary.getDistroArchSeries('i386').addOrUpdateChroot(chroot)

    >>> print_architectures(hoary.buildable_architectures)
    The Hoary Hedgehog Release for hppa (hppa) (ppa)
    The Hoary Hedgehog Release for i386 (386) (official, ppa)

An architecture can have an associated filter that controls which packages
are included in it.  It has an `isSourceIncluded` method that allows
querying inclusion by `SourcePackageName`.

    >>> from lp.soyuz.enums import DistroArchSeriesFilterSense

    >>> spns = [factory.makeSourcePackageName() for _ in range(3)]
    >>> hoary.getDistroArchSeries('i386').isSourceIncluded(spns[0])
    True

    >>> packageset_include = factory.makePackageset(distroseries=hoary)
    >>> packageset_include.add(spns[:2])
    >>> hoary.getDistroArchSeries('i386').setSourceFilter(
    ...     packageset_include, DistroArchSeriesFilterSense.INCLUDE,
    ...     factory.makePerson())
    >>> packageset_exclude = factory.makePackageset(distroseries=hoary)
    >>> packageset_exclude.add(spns[1:])
    >>> hoary.getDistroArchSeries('hppa').setSourceFilter(
    ...     packageset_exclude, DistroArchSeriesFilterSense.EXCLUDE,
    ...     factory.makePerson())

    >>> hoary.getDistroArchSeries('i386').isSourceIncluded(spns[0])
    True
    >>> hoary.getDistroArchSeries('i386').isSourceIncluded(spns[1])
    True
    >>> hoary.getDistroArchSeries('i386').isSourceIncluded(spns[2])
    False
    >>> hoary.getDistroArchSeries('hppa').isSourceIncluded(spns[0])
    True
    >>> hoary.getDistroArchSeries('hppa').isSourceIncluded(spns[1])
    False
    >>> hoary.getDistroArchSeries('hppa').isSourceIncluded(spns[2])
    False
