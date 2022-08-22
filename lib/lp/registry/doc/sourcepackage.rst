Source Packages
===============

A source package is a thing from which binary packages are built, to
then be installed using a package management tool like apt or rpm.
One named source package in a distro may be used to build several
different named binary packages, on one or more architectures. One named
binary package in a distro may have been built from more than one named
source package (e.g. a different source package may have been used to
build "foo" on i386 vs. "foo" on ppc.)


Named Source Package
--------------------

The are various metadata we're interested in collecting about a bundle
of code used to build binary packages for installation in a particular
distro series. One such thing is the name of that bundle of code. This
is abstracted into a separate SourcePackageName table.

Accessing source package names is done through the ISourcePackageNameSet
utility.

The ISourcePackageNameSet utility is accessed in the usual fashion:

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet)
    >>> sourcepackagenameset = getUtility(ISourcePackageNameSet)

To retrieve a specific source package name, use
ISourcePackageNameSet.get:

    >>> firefox = sourcepackagenameset.get(1)
    >>> print(firefox.name)
    mozilla-firefox

To retrieve a specific source package name by its name, use
ISourcePackageNameSet.queryByName:

    >>> firefox = sourcepackagenameset.queryByName("mozilla-firefox")
    >>> print(firefox.name)
    mozilla-firefox

Source packages have useful string representations containing their name in
quotes.

    >>> firefox
    <SourcePackageName 'mozilla-firefox'>

If the package doesn't exist, queryByName returns None:

    >>> biscoito = sourcepackagenameset.queryByName("biscoito")
    >>> print(biscoito)
    None


Source package meta object
--------------------------

A SourcePackage is a meta representation of a source package that is published
in a distroseries. It provides access to the current and historic information
about the package in the series. Since a SourcePackage is a meta object, it
can be constructed from a SourcePackageName and a distroseries.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.model.sourcepackage import SourcePackage

    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> ubuntu_warty = ubuntu.getSeries('warty')
    >>> firefox_warty_package = SourcePackage(sourcepackagename=firefox,
    ...     distroseries=ubuntu_warty)
    >>> firefox_warty_package
    <SourcePackage ...'Ubuntu'...'warty'...'mozilla-firefox'...>

An instance is commonly retrieved from a distroseries.

    >>> firefox_warty = ubuntu_warty.getSourcePackage('mozilla-firefox')
    >>> firefox_warty == firefox_warty_package
    True


Descriptive attributes
......................

A source package has a name, displayname, title, and a summary.

    >>> print(firefox_warty.name)
    mozilla-firefox

    >>> print(firefox_warty.displayname)
    mozilla-firefox in Ubuntu Warty

    >>> print(firefox_warty.title)
    mozilla-firefox source package in Warty

    >>> print(firefox_warty.summary)
    mozilla-firefox: Mozilla Firefox Web Browser
    mozilla-firefox-data: No summary available for mozilla-firefox-data
    in ubuntu warty.


Latest published component
..........................

The 'latest_published_component' attribute indicates the component where
the package was last published.

    >>> print(firefox_warty.latest_published_component.name)
    main

It's worth noting that the returned component is the one in the latest
publishing record, not the component where the package was last
uploaded. After a package has been uploaded, and a SourcePackageRelease
record has been created, the component may be changed. The
SourcePackageRelease will still have the same component as the original
upload, even though it gets changed in the publishing record.

    # Remove the security proxy to access the non-public
    # _getPublishingHistory method.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> publishing_history = removeSecurityProxy(
    ...     firefox_warty)._getPublishingHistory()
    >>> for publishing in publishing_history:
    ...     print(publishing.status.name, publishing.component.name)
    PENDING main
    PUBLISHED main

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> from lp.soyuz.model.component import Component
    >>> from lp.soyuz.model.publishing import (
    ...     SourcePackagePublishingHistory)

    >>> latest_publishing = IStore(SourcePackagePublishingHistory).get(
    ...     SourcePackagePublishingHistory, publishing_history.last().id)
    >>> universe = IStore(Component).find(Component, name='universe').one()
    >>> latest_publishing.component = universe
    >>> flush_database_caches()

    >>> for release in firefox_warty.distinctreleases:
    ...     print(release.component.name)
    main

    >>> print(firefox_warty.latest_published_component.name)
    universe

Only PUBLISHED records are considered when looking the latest published
component. If there are no PUBLISHED records, None is returned.

    >>> from lp.soyuz.enums import PackagePublishingStatus

    >>> latest_publishing.status = PackagePublishingStatus.SUPERSEDED
    >>> print(firefox_warty.latest_published_component)
    None

SourcePackage traversing is also provided through the available
published versions. Note that all versions ever published in the
SourcePackage context will be reachable.

    >>> pmount_hoary = ubuntu['hoary'].getSourcePackage('pmount')

    >>> for release in pmount_hoary.releases:
    ...     print(release.title, release.publishing_history[0].status.name)
    pmount 0.1-1 source package in Ubuntu SUPERSEDED
    pmount 0.1-2 source package in Ubuntu PUBLISHED

    >>> len(list(pmount_hoary.distinctreleases))
    2

'pmount_0.1-1' in hoary is SUPERSEDED but not yet 'removed from disk'.

    >>> pub = removeSecurityProxy(ubuntu.main_archive.getPublishedSources(
    ...     distroseries=ubuntu['hoary'], name=u'pmount',
    ...     version=u'0.1-1').one())
    >>> pub.datesuperseded is not None
    True
    >>> pub.dateremoved is None
    True

We will emulate disk-removal to ensure it will continue to be reachable.
See bug #179028 for further information.

    >>> from datetime import timedelta
    >>> pub.dateremoved = pub.datesuperseded + timedelta(days=1)

    >>> for release in pmount_hoary.releases:
    ...     print(release.title, release.publishing_history[0].status.name)
    pmount 0.1-1 source package in Ubuntu SUPERSEDED
    pmount 0.1-2 source package in Ubuntu PUBLISHED

    >>> len(list(pmount_hoary.distinctreleases))
    2

We will leave the pmount_0.1-1 marked as 'removed from disk' because we
do want it to affect the next test cases.


Distribution Source Packages
----------------------------

In some cases it's useful to be able to refer to a source package at a
distribution level, independent of any particular distroseries. For
example, with Malone, a bug is usually filed on a distribution
sourcepackage (filing a bug on a specific distroseries actually means
something quite different, but is outside the scope of this document.)

To retrieve a distribution source package, use the getSourcePackage
method on a distribution:

    >>> from lp.registry.interfaces.distributionsourcepackage import (
    ...     IDistributionSourcePackage)
    >>> ubuntu_firefox = ubuntu.getSourcePackage(firefox)
    >>> IDistributionSourcePackage.providedBy(ubuntu_firefox)
    True

    >>> print(ubuntu_firefox.name)
    mozilla-firefox

    >>> print(backslashreplace(ubuntu_firefox.title))
    mozilla-firefox package in Ubuntu

    >>> print(ubuntu_firefox.displayname)
    mozilla-firefox in Ubuntu

    >>> ubuntu_firefox.distribution == ubuntu
    True

    >>> ubuntu_firefox.sourcepackagename == firefox
    True

Distro sourcepackages know how to compare to each other:

    >>> debian = getUtility(IDistributionSet).getByName('debian')
    >>> ubuntu_firefox_also = ubuntu.getSourcePackage(firefox)
    >>> debian_firefox = debian.getSourcePackage(firefox)

    >>> ubuntu_firefox_also == ubuntu_firefox
    True

    >>> ubuntu_firefox != debian_firefox
    True

You can search for bugs in an IDistroSourcePackage using the
.searchTasks method:

    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> from lp.bugs.interfaces.bugtasksearch import BugTaskSearchParams
    >>> params = BugTaskSearchParams(
    ...     status=BugTaskStatus.NEW, user=None)
    >>> tasks = ubuntu_firefox.searchTasks(params)
    >>> tasks.count()
    1

    >>> tasks[0].id
    17


Packaging
---------

Distribution packages are linked to upstream productseries through the
packaging process. Here we test the code that links all of those.

First, let's get some useful objects from the db.

    >>> from lp.registry.model.sourcepackagename import SourcePackageName
    >>> firefox = SourcePackageName.byName('mozilla-firefox')
    >>> pmount = SourcePackageName.byName('pmount')

    >>> from lp.registry.model.distroseries import DistroSeries
    >>> warty = DistroSeries.get(1)
    >>> hoary = DistroSeries.get(3)

Now let's make sure that we can see a productseries for a source
package.

    >>> from lp.registry.model.sourcepackage import SourcePackage
    >>> sp = SourcePackage(sourcepackagename=firefox, distroseries=hoary)
    >>> print(sp.productseries.name)
    1.0


Linkified changelogs are available through SourcePackageReleaseView: XXX
julian 2007-09-17 This is duplicating the page test. Instead it should
be more like the bug number linkification just below.

    >>> from zope.component import queryMultiAdapter
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> mock_form = {}
    >>> request = LaunchpadTestRequest(form=mock_form)
    >>> dsp = ubuntu.getSourcePackage(pmount)
    >>> dspr = dsp.getVersion('0.1-2')
    >>> dspr_view = queryMultiAdapter((dspr, request), name="+changelog")
    >>> print(dspr_view.changelog_entry)
    This is a placeholder changelog for pmount 0.1-2

    >>> dspr = dsp.getVersion('0.1-1')
    >>> dspr_view = queryMultiAdapter((dspr, request), name="+changelog")
    >>> print(dspr_view.changelog_entry)
    pmount (0.1-1) hoary; urgency=low
    <BLANKLINE>
     * Fix description (Malone #1)
     * Fix debian (Debian #2000)
     * Fix warty (Warty Ubuntu #1)
    <BLANKLINE>
     -- Sample Person &lt;email address hidden&gt; ... Feb 2006 12:10:08 +0300
    <BLANKLINE>
    <BLANKLINE>

The view will linkify bug numbers of the format "LP: #number" in the
changelog if number is a valid bug ID (see
``lib/lp/soyuz/stories/soyuz/xx-sourcepackage-changelog.rst``).


Comparing Sourcepackages
------------------------

Lastly, note that sourcepackages know how to compare to each other:

    >>> hoary_firefox_one = SourcePackage(
    ...     sourcepackagename=firefox, distroseries=hoary)
    >>> hoary_firefox_two = SourcePackage(
    ...     sourcepackagename=firefox, distroseries=hoary)
    >>> warty_firefox = SourcePackage(
    ...     sourcepackagename=firefox, distroseries=warty)

    >>> hoary_firefox_one == hoary_firefox_two
    True

    >>> hoary_firefox_one != warty_firefox
    True

    >>> hoary_firefox_one == warty_firefox
    False

And they can be used as dictionary keys also:

    >>> hash(hoary_firefox_one) == hash(hoary_firefox_two)
    True

    >>> hash(hoary_firefox_one) != hash(warty_firefox)
    True

    >>> a_map = {}
    >>> a_map[hoary_firefox_one] = 'hoary'
    >>> a_map[warty_firefox] = 'warty'
    >>> print(a_map[hoary_firefox_two])
    hoary

    >>> print(a_map[warty_firefox])
    warty


Direct Packagings
-----------------

The direct packaging returns the IPackaging related to the source
package.

    >>> sp = hoary.getSourcePackage(pmount)
    >>> print(sp.direct_packaging)
    None

    >>> print(hoary_firefox_one.direct_packaging.productseries.title)
    Mozilla Firefox 1.0 series

    >>> print(warty_firefox.direct_packaging.productseries.title)
    Mozilla Firefox trunk series


Release History
---------------

The distinct release history for a SourcePackage is obtained via
'distinctreleases' property.

We will use `SoyuzTestPublisher` for creating source releases in Ubuntu
warty and hoary series.

    >>> from lp.soyuz.tests.test_publishing import (
    ...     SoyuzTestPublisher)
    >>> test_publisher = SoyuzTestPublisher()

    >>> login('foo.bar@canonical.com')

    >>> ignore = test_publisher.setUpDefaultDistroSeries(ubuntu_warty)
    >>> warty_source = test_publisher.getPubSource(
    ...     sourcename="test-source", version='1.0')

    >>> ubuntu_hoary = ubuntu.getSeries('hoary')
    >>> hoary_source = test_publisher.getPubSource(
    ...     sourcename="test-source", version='1.1',
    ...     distroseries=ubuntu_hoary)

    >>> login(ANONYMOUS)

Warty, hoary and grumpy SourcePackages only consider their corresponding
versions, their history is isolated by series.

    >>> def print_releases(sourcepackage):
    ...     releases = sourcepackage.distinctreleases
    ...     if releases.count() == 0:
    ...         print('No releases available')
    ...         return
    ...     for release in releases:
    ...         print(release.title)

    >>> warty_sp = ubuntu_warty.getSourcePackage('test-source')
    >>> print_releases(warty_sp)
    test-source - 1.0

    >>> hoary_sp = ubuntu_hoary.getSourcePackage('test-source')
    >>> print_releases(hoary_sp)
    test-source - 1.1

    >>> ubuntu_grumpy = ubuntu.getSeries('grumpy')
    >>> grumpy_sp = ubuntu_grumpy.getSourcePackage('test-source')
    >>> print_releases(grumpy_sp)
    No releases available

The SourcePackage history can overlap if releases are copied across
distroseries. The 'test-source - 1.0' is copied from warty to hoary and
is present in the history for both.

    >>> login('foo.bar@canonical.com')
    >>> copied_source = warty_source.copyTo(
    ...     ubuntu_hoary, warty_source.pocket, warty_source.archive)
    >>> login(ANONYMOUS)

    >>> print_releases(warty_sp)
    test-source - 1.0

    >>> print_releases(hoary_sp)
    test-source - 1.1
    test-source - 1.0

We will create new source releases in warty and verify the ResultSet
returned from 'distinctreleases' is ordered by descending source
version.

    >>> login('foo.bar@canonical.com')

    >>> lower_source = test_publisher.getPubSource(
    ...     sourcename="test-source", version='0.9')

    >>> higher_source = test_publisher.getPubSource(
    ...     sourcename="test-source", version='1.2')

    >>> login(ANONYMOUS)

    >>> print_releases(warty_sp)
    test-source - 1.2
    test-source - 1.0
    test-source - 0.9


Interface implementation
------------------------

SourcePackage implements IHasTranslationImports interface:

    >>> from lp.testing import verifyObject
    >>> from lp.translations.interfaces.hastranslationimports import (
    ...     IHasTranslationImports)
    >>> IHasTranslationImports.providedBy(warty_firefox)
    True

    >>> verifyObject(IHasTranslationImports, warty_firefox)
    True
