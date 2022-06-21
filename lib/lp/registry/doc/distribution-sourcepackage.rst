Distribution Source Packages
============================

A distribution source package represents a named source package in a
distribution, independent of any particular release of that source
package.

This is useful for, among other things, tracking bugs in source
packages, ensuring that bug reports automatically carry forward from one
distribution series to the next.

Fetching a Distribution Source Package
--------------------------------------

A common way to fetch a distribution source package is to start with the
distribution object:

    >>> from zope.component import getUtility
    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.distributionsourcepackage import (
    ...     IDistributionSourcePackage,
    ...     )
    >>> debian = getUtility(IDistributionSet).getByName("debian")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")

Use IDistribution.getSourcePackage to get a specific package by name:

    >>> debian_firefox = debian.getSourcePackage("mozilla-firefox")
    >>> print(debian_firefox.name)
    mozilla-firefox
    >>> IDistributionSourcePackage.providedBy(debian_firefox)
    True
    >>> verifyObject(IDistributionSourcePackage, debian_firefox)
    True


Descriptive attributes
----------------------

A distribution source package has a name, displayname, title, and a summary.

    >>> dsp = ubuntu.getSourcePackage("pmount")
    >>> print(dsp.name)
    pmount

    >>> print(dsp.displayname)
    pmount in Ubuntu

    >>> print(dsp.title)
    pmount package in Ubuntu

    >>> print(dsp.summary)
    pmount: pmount shortdesc


Publishing-related properties
-----------------------------

Publishing history of 'pmount in Ubuntu':

    >>> for p in dsp.publishing_history:
    ...     print(" ".join((p.sourcepackagerelease.name,
    ...                     p.sourcepackagerelease.version,
    ...                     p.distroseries.name)))
    pmount 0.1-2 hoary
    pmount 0.1-1 hoary

Current publishing records for 'pmount in Ubuntu':

    >>> for p in dsp.current_publishing_records:
    ...     print(" ".join((p.sourcepackagerelease.name,
    ...                     p.sourcepackagerelease.version,
    ...                     p.distroseries.name)))
    pmount 0.1-2 hoary

Current overall publications:

A DistributionSourcePackage has a property called 'latest_overall_publication'
which returns the latest overall relevant publication. Relevant is currently
defined as being either published or obsolete with published being preferred,
sorted by distroseries and component with publications in proposed and
backports excluded.

    >>> from lp.soyuz.enums import PackagePublishingStatus
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> publisher = SoyuzTestPublisher()
    >>> publisher.prepareBreezyAutotest()
    >>> warty = ubuntu['warty']
    >>> hoary = ubuntu['hoary']

This demonstrates the scenario where a newer distroseries becomes obsolete
before an older distroseries. The latest_overall_publication property will
return the publication from the older distroseries because a published
publication is considered more relevant than an obsolete publication.

Note that the component of the package in the newer obsolete distroseries
is 'main' and in the older distroseries it is 'universe'.

    >>> compiz_publication_warty = publisher.getPubSource(
    ...     sourcename='compiz', version='0.01-1ubuntu1', distroseries=warty,
    ...     status=PackagePublishingStatus.PUBLISHED, component='universe')
    >>> compiz_publication_hoary = publisher.getPubSource(
    ...     sourcename='compiz', version='0.01-1ubuntu1', distroseries=hoary,
    ...     status=PackagePublishingStatus.OBSOLETE, component='main')
    >>> compiz = ubuntu.getSourcePackage('compiz')
    >>> print(compiz.latest_overall_publication.component.name)
    universe

When more than one published publication exists in a single distroseries,
latest_overall_publication will favor updates over security and security over
release.

    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> firefox_publication_warty = publisher.getPubSource(
    ...     sourcename='firefox', version='0.01-1ubuntu1', distroseries=hoary,
    ...     status=PackagePublishingStatus.PUBLISHED, component='main',
    ...     pocket=PackagePublishingPocket.RELEASE)
    >>> firefox_publication_hoary = publisher.getPubSource(
    ...     sourcename='firefox', version='0.01-1ubuntu1.1',
    ...     distroseries=hoary, status=PackagePublishingStatus.PUBLISHED,
    ...     component='main', pocket=PackagePublishingPocket.SECURITY)
    >>> firefox = ubuntu.getSourcePackage('firefox')
    >>> print(firefox.latest_overall_publication.pocket.name)
    SECURITY

Release-related properties
..........................

Releases of 'pmount in Ubuntu':

    >>> for release in dsp.releases:
    ...     print(release.version)
    0.1-2
    0.1-1

We can also get the releases of 'pmount in Ubuntu' along with the
relevant publishing information:

    >>> for release, pubs in dsp.getReleasesAndPublishingHistory():
    ...     print(release.version)
    ...     for pub in pubs:
    ...         print(' * %s - %s' % (pub.distroseries.name, pub.status.name))
    0.1-2
     * hoary - PUBLISHED
    0.1-1
     * hoary - SUPERSEDED

Current release of 'pmount in Ubuntu':

    >>> print(dsp.currentrelease.version)
    0.1-2

Check if 'currentrelease' works with version containing letters
(bug # 6040):

    >>> dsp2 = ubuntu.getSourcePackage("alsa-utils")
    >>> print(dsp2.currentrelease.version)
    1.0.9a-4ubuntu1

    >>> dsp3 = ubuntu.getSourcePackage("cnews")
    >>> print(dsp3.currentrelease.version)
    cr.g7-37

Distribution Source Package Branches
....................................

We can use the getBranches() API from IHasBranches to get the related branches
for a DSP.

    >>> fred = factory.makePerson(name='fred')
    >>> branch = factory.makePackageBranch(
    ...     distroseries=hoary, sourcepackagename='pmount', name='tip',
    ...     owner=fred)
    >>> [branch] = list(dsp.getBranches())
    >>> print(branch.unique_name)
    ~fred/ubuntu/hoary/pmount/tip

Grabbing DSPRs
..............

To list the current 'pmount in Ubuntu' ISourcePackages, use
get_distroseries_packages():

    >>> for sp in dsp.get_distroseries_packages():
    ...     print('%s %s' % (sp.name, sp.distroseries.name))
    pmount hoary

To retrieve a version of 'pmount in Ubuntu' as an
IDistributionSourcePackageRelease (IDSPR) or None if not found, use
getVersion():

    >>> dsp.getVersion('1.0') is None
    True

    >>> pmount_dspr = dsp.getVersion('0.1-1')
    >>> print(pmount_dspr.title)
    pmount 0.1-1 source package in Ubuntu

    >>> for pub in pmount_dspr.publishing_history:
    ...     print(pub.distroseries.name, pub.status.name)
    hoary SUPERSEDED

'getVersion' also returns IDSPRs for REMOVED versions which allows
developers to investigate history of files already removed from the
archive (bug #60440):

    >>> ubuntutest = getUtility(IDistributionSet)["ubuntutest"]
    >>> alsa_dsp = ubuntutest.getSourcePackage("alsa-utils")
    >>> alsa_dspr = alsa_dsp.getVersion('1.0.9a-4')
    >>> print(alsa_dspr.title)
    alsa-utils 1.0.9a-4 source package in ubuntutest

    >>> for pub in alsa_dspr.publishing_history:
    ...     is_removed = pub.dateremoved is not None
    ...     print(pub.distroseries.name, pub.status.name, is_removed)
    breezy-autotest DELETED True

__hash__
--------

DistributionSourcePackage defines a custom __hash__ method, so that
different instances, representing the same packages, have the same hash.

    >>> pmount = ubuntu.getSourcePackage('pmount')
    >>> pmount_again = ubuntu.getSourcePackage('pmount')
    >>> pmount is pmount_again
    False
    >>> hash(pmount) == hash(pmount_again)
    True
    >>> pmount == pmount_again
    True

This means that packages can be used as keys in dictionaries.

    >>> pmount_marker = object()
    >>> firefox_marker = object()
    >>> mapping = {
    ...     pmount: pmount_marker,
    ...     ubuntu.getSourcePackage('mozilla-firefox'): firefox_marker,
    ...     }
    >>> mapping[pmount_again] is pmount_marker
    True
    >>> mapping[ubuntu.getSourcePackage('mozilla-firefox')] is firefox_marker
    True

Upstream links
--------------

DistributionSourcePackages can be linked to upstream Products. You can
retrieve a DistributionSourcePackage's upstream product using its
upstream_product property.

    >>> firefox = ubuntu.getSourcePackage('mozilla-firefox')
    >>> print(firefox.upstream_product.displayname)
    Mozilla Firefox

If the package isn't linked to an upstream product, upstream_product
will be None.

    >>> print(pmount.upstream_product)
    None

Finding archives where this package is published
------------------------------------------------

A distribution source package can also find which archives
versions of a given source package have been published in.

    # First create some PPAs.
    >>> login('foo.bar@canonical.com')
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> publisher = SoyuzTestPublisher()
    >>> publisher.prepareBreezyAutotest()
    >>> ubuntu_test = publisher.distroseries.distribution
    >>> ppa_nightly = factory.makeArchive(
    ...     name="nightly", distribution=ubuntu_test)
    >>> ppa_beta = factory.makeArchive(
    ...     name="beta", distribution=ubuntu_test)

    # Next publish some sources in them.
    >>> gedit_nightly_src_hist = publisher.getPubSource(
    ...     sourcename="gedit", archive=ppa_nightly,
    ...     creator=ppa_nightly.owner,
    ...     status=PackagePublishingStatus.PUBLISHED)
    >>> gedit_beta_src_hist = publisher.getPubSource(
    ...     sourcename="gedit", archive=ppa_beta,
    ...     creator=ppa_beta.owner,
    ...     status=PackagePublishingStatus.PUBLISHED)
    >>> gedit_main_src_hist = publisher.getPubSource(
    ...     sourcename="gedit", archive=ubuntu_test.main_archive,
    ...     creator=ppa_nightly.owner,
    ...     status=PackagePublishingStatus.PUBLISHED)

    # Give the creators of the above source packages some
    # karma for their efforts.
    >>> ppa_beta_owner_id = ppa_beta.owner.id
    >>> ppa_nightly_owner_id = ppa_nightly.owner.id

    >>> from lp.testing.dbuser import switch_dbuser
    >>> switch_dbuser('karma')
    >>> from lp.registry.model.karma import KarmaTotalCache
    >>> cache_entry = KarmaTotalCache(person=ppa_beta_owner_id,
    ...     karma_total=200)
    >>> cache_entry = KarmaTotalCache(person=ppa_nightly_owner_id,
    ...     karma_total=201)
    >>> switch_dbuser('launchpad')

The results of findRelatedArchives() are sorted so that archive containing
the package created by the person with the greatest karma is first:

    >>> gedit_src = ubuntu_test.getSourcePackage('gedit')
    >>> ppa_versions_for_gedit = gedit_src.findRelatedArchives()
    >>> for ppa in ppa_versions_for_gedit:
    ...     print(ppa.displayname)
    PPA named nightly for Person...
    PPA named beta for Person...

You can choose to exclude a certain archive from the results - useful
if you want to find all *other* related archives:

    >>> ppa_versions_for_gedit = gedit_src.findRelatedArchives(
    ...     exclude_archive=ppa_nightly)
    >>> for ppa in ppa_versions_for_gedit:
    ...     print(ppa.displayname)
    PPA named beta for Person...

Although findRelatedArchives() defaults to PPAs, it can be used to find
packages in other archives too:

    >>> archive_versions_for_gedit = gedit_src.findRelatedArchives(
    ...     archive_purpose=None)
    >>> for archive in archive_versions_for_gedit:
    ...     print(archive.displayname)
    Primary Archive for Ubuntu Test
    PPA named nightly for Person...
    PPA named beta for Person...
