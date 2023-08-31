Distributions
=============

From the DerivationOverview spec
<https://launchpad.canonical.com/DerivationOverview>:

    A distribution of GNU/Linux comprises a set of packages, an
    installer, possibly a live-CD, some amount of metadata associated with
    the arrangement of those elements and also a lot of information on
    managing it.

In Launchpad, one distribution is mapped to one row in the Distribution
table.  To retrieve a distribution, use the IDistributionSet utility. If
you've already used IPersonSet to retrieve a Person, or IBugTaskSet to
retrieve a task, this syntax should look familiar.

The IDistributionSet utility is accessed in the usual fashion:

    >>> from lp.registry.interfaces.distribution import (
    ...     IDistribution,
    ...     IDistributionSet,
    ... )
    >>> from lp.translations.interfaces.hastranslationimports import (
    ...     IHasTranslationImports,
    ... )
    >>> distroset = getUtility(IDistributionSet)

To retrieve a specific distribution, use IDistributionSet.get:

    >>> ubuntu = distroset.get(1)
    >>> print(ubuntu.name)
    ubuntu

The distribution has a useful string representation containing its display
name in quotes and its name in parentheses.

    >>> ubuntu
    <Distribution 'Ubuntu' (ubuntu)>

Or, to grab one by name, use either getByName() or __getitem__().  They both
can be used to look up distributions by their aliases too.

    >>> gentoo = distroset.getByName("gentoo")
    >>> print(gentoo.name)
    gentoo
    >>> print(distroset["gentoo"].name)
    gentoo

    # Need to login as an LP admin to set a project's aliases.
    >>> login("foo.bar@canonical.com")
    >>> gentoo.setAliases(["jackass"])
    >>> for alias in gentoo.aliases:
    ...     print(alias)
    ...
    jackass
    >>> login(ANONYMOUS)
    >>> print(distroset["jackass"].name)
    gentoo
    >>> print(distroset.getByName("jackass").name)
    gentoo

Let's make sure a distribution object properly implements its interfaces.

    >>> IDistribution.providedBy(gentoo)
    True
    >>> verifyObject(IDistribution, gentoo)
    True
    >>> IHasTranslationImports.providedBy(gentoo)
    True
    >>> verifyObject(IHasTranslationImports, gentoo)
    True

Once you've got a distribution, you can retrieve a source package if you
have a SourcePackageName object for it.

    >>> from lp.registry.model.sourcepackagename import SourcePackageName
    >>> from lp.registry.interfaces.distributionsourcepackage import (
    ...     IDistributionSourcePackage,
    ... )
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.interfaces.distributionsourcepackagerelease import (
    ...     IDistributionSourcePackageRelease,
    ... )

    >>> evo = (
    ...     IStore(SourcePackageName)
    ...     .find(SourcePackageName, name="evolution")
    ...     .one()
    ... )
    >>> evo_ubuntu = ubuntu.getSourcePackage(evo)
    >>> print(evo_ubuntu.name)
    evolution

    >>> IDistributionSourcePackage.providedBy(evo_ubuntu)
    True

    >>> from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
    >>> sourcepackagerelease = (
    ...     IStore(SourcePackageRelease)
    ...     .find(SourcePackageRelease, sourcepackagename=evo, version="1.0")
    ...     .one()
    ... )
    >>> print(sourcepackagerelease.name)
    evolution

    >>> evo_ubuntu_rel = ubuntu.getSourcePackageRelease(sourcepackagerelease)
    >>> IDistributionSourcePackageRelease.providedBy(evo_ubuntu_rel)
    True

You can also get a release by name:

    >>> hoary = ubuntu.getSeries("hoary")
    >>> print(hoary.name)
    hoary

Or by version:

    >>> v504 = ubuntu.getSeries("5.04")
    >>> print(v504.name)
    hoary

You can list development distroseriess:

    >>> devdists = ubuntu.getDevelopmentSeries()
    >>> for devdist in devdists:
    ...     print(devdist.name)
    ...
    hoary

You can list the series for a distribution,

    >>> for series in ubuntu.series:
    ...     print(series.name)
    ...
    breezy-autotest
    grumpy
    hoary
    warty

as well as the distribution architecture series for a distribution:

    >>> for architecture in ubuntu.architectures:
    ...     print(architecture.displayname)
    ...
    Ubuntu Breezy Badger Autotest i386
    Ubuntu Hoary hppa
    Ubuntu Hoary i386
    Ubuntu Warty hppa
    Ubuntu Warty i386

You can use the has_published_binaries property to find out if the
distribution has any binaries on disk.  This is useful when searching for
packages and you need to tailor any user messages about what types of packages
are available.

    >>> ubuntu.has_published_binaries
    True

    >>> gentoo.has_published_binaries
    False

You can use the has_published_sources property to find out if the
distribution has any published sources.

    >>> ubuntu.has_published_sources
    True

    >>> gentoo.has_published_sources
    False


Distribution Sorting
--------------------

If you ask for all the distributions in the DistributionSet you should get
Ubuntu (and all flavours of it) first and the rest alphabetically:

    >>> for item in distroset.getDistros():
    ...     print(item.name)
    ...
    ubuntu
    kubuntu
    ubuntutest
    debian
    gentoo
    guadalinex
    redhat

DistributionSet also defines __iter__ as a shortcut to getDistros().

    >>> list(distroset) == distroset.getDistros()
    True


Searching for DistributionSourcePackages
........................................

The distribution also allows you to look for source packages that match
a certain string through the magic of full text indexing (fti). For instance:

    >>> packages = ubuntu.searchSourcePackageCaches("mozilla")
    >>> for distro_source_package_cache, source_name, rank in packages:
    ...     print(
    ...         "%-17s rank:%s"
    ...         % (distro_source_package_cache.name, type(rank))
    ...     )
    ...
    mozilla-firefox   rank:<... 'float'>

The search also matches on exact package names which fti doesn't like,
and even on substrings:

    >>> packages = ubuntu.searchSourcePackageCaches("linux-source-2.6.15")
    >>> print(packages.count())
    1
    >>> packages = ubuntu.searchSourcePackageCaches("a")
    >>> for distro_source_package_cache, source_name, rank in packages:
    ...     print(
    ...         "%s: %-17s rank:%s"
    ...         % (
    ...             distro_source_package_cache.__class__.__name__,
    ...             distro_source_package_cache.name,
    ...             type(rank),
    ...         )
    ...     )
    ...
    DistributionSourcePackageCache: alsa-utils        rank:<... 'NoneType'>
    DistributionSourcePackageCache: commercialpackage rank:<... 'NoneType'>
    DistributionSourcePackageCache: foobar            rank:<... 'NoneType'>
    DistributionSourcePackageCache: mozilla-firefox   rank:<... 'NoneType'>
    DistributionSourcePackageCache: netapplet         rank:<... 'NoneType'>

The searchSourcePackages() method just returns a decorated version
of the results from searchSourcePackageCaches():

    >>> packages = ubuntu.searchSourcePackages("a")
    >>> for dsp in packages:
    ...     print("%s: %s" % (dsp.__class__.__name__, dsp.name))
    ...
    DistributionSourcePackage: alsa-utils
    DistributionSourcePackage: commercialpackage
    DistributionSourcePackage: foobar
    DistributionSourcePackage: mozilla-firefox
    DistributionSourcePackage: netapplet

searchSourcePackages() also has a has_packaging parameter that
it just passes on to searchSourcePackageCaches(), and it restricts
the results based on whether the source package has an entry
in the Packaging table linking it to an upstream project.

    >>> packages = ubuntu.searchSourcePackages("a", has_packaging=True)
    >>> for dsp in packages:
    ...     print("%s: %s" % (dsp.__class__.__name__, dsp.name))
    ...
    DistributionSourcePackage: alsa-utils
    DistributionSourcePackage: mozilla-firefox
    DistributionSourcePackage: netapplet
    >>> packages = ubuntu.searchSourcePackages("a", has_packaging=False)
    >>> for dsp in packages:
    ...     print("%s: %s" % (dsp.__class__.__name__, dsp.name))
    ...
    DistributionSourcePackage: commercialpackage
    DistributionSourcePackage: foobar

searchSourcePackages() also has a publishing_distroseries parameter that
it just passes on to searchSourcePackageCaches(), and it restricts the
results based on whether the source package has an entry in the
SourcePackagePublishingHistory table for the given distroseries.

    >>> packages = ubuntu.searchSourcePackages(
    ...     "a", publishing_distroseries=ubuntu.currentseries
    ... )
    >>> for dsp in packages:
    ...     print("%s: %s" % (dsp.__class__.__name__, dsp.name))
    ...
    DistributionSourcePackage: alsa-utils
    DistributionSourcePackage: netapplet


Searching for binary packages
.............................

searchBinaryPackages() does a name substring match to find binary
packages related to the distribution. It returns
DistributionSourcePackageCache objects, which makes it very easy to
associate the binary name with its source.

Searching for an exact match on a valid binary name returns the
expected results:

    >>> results = ubuntu.searchBinaryPackages(
    ...     "mozilla-firefox", exact_match=True
    ... )
    >>> for result in results:
    ...     print(result.name)
    ...
    mozilla-firefox

An exact match search with no matches on any package name returns
an empty result set:

    >>> results = ubuntu.searchBinaryPackages("mozilla", exact_match=True)
    >>> results.count()
    0

Loosening to substring matches gives another result:

    >>> results = ubuntu.searchBinaryPackages("mozilla", exact_match=False)
    >>> print(results[0])
    <...DistributionSourcePackageCache instance ...

    >>> for result in results:
    ...     print(result.name)
    ...
    mozilla-firefox
    >>> for result in results:
    ...     print(result.binpkgnames)
    ...
    mozilla-firefox mozilla-firefox-data

The results of searchBinaryPackages() are simply ordered alphabetically
for the moment until we have a better FTI rank to order with.

    >>> results = ubuntu.searchBinaryPackages("m")
    >>> for result in results:
    ...     print(result.name)
    ...
    mozilla-firefox
    pmount


Finding distroseriess and pockets from distribution names
.........................................................

A distribution knows what distroseriess it has. Those distroseriess have
pockets which have suffixes used by the archive publisher. Because we
sometimes need to talk about distroseriess such as ubuntu/hoary-security
we need some way to decompose that into the distroseries and the pocket.
Distribution can do that for us.

If we ask for a totally unknown distroseries, we raise NotFoundError
    >>> ubuntu.getDistroSeriesAndPocket("unknown")
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...'unknown'

If we ask for a plain distroseries, it should come back with the RELEASE
pocket as the pocket.
    >>> dr, pocket = ubuntu.getDistroSeriesAndPocket("hoary")
    >>> print(dr.name)
    hoary
    >>> print(pocket.name)
    RELEASE

If we ask for a security pocket in a known distroseries it should come out
on the other side.
    >>> dr, pocket = ubuntu.getDistroSeriesAndPocket("hoary-security")
    >>> print(dr.name)
    hoary
    >>> print(pocket.name)
    SECURITY

Find the backports pocket, too:
    >>> dr, pocket = ubuntu.getDistroSeriesAndPocket("hoary-backports")
    >>> print(dr.name)
    hoary
    >>> print(pocket.name)
    BACKPORTS

If we ask for a valid distroseries which doesn't have a given pocket it should
raise NotFoundError for us
    >>> ubuntu.getDistroSeriesAndPocket("hoary-bullshit")
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...'hoary-bullshit'


Upload related stuff
....................

When uploading to a distribution we need to query its uploaders. Each
uploader record is in fact an ArchivePermission record that tells us
what component is uploadable to by what person or group of people.

    >>> from operator import attrgetter
    >>> for permission in sorted(ubuntu.uploaders, key=attrgetter("id")):
    ...     assert not permission.archive.is_ppa
    ...     print(permission.component.name)
    ...     print(permission.person.displayname)
    ...
    universe
    Ubuntu Team
    restricted
    Ubuntu Team
    main
    Ubuntu Team
    partner
    Canonical Partner Developers


Launchpad Usage
...............

A distribution can specify if it uses Malone, Rosetta, or Answers
officially. Ubuntu uses all of them:

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities

    >>> ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    >>> ubuntu.official_malone
    True
    >>> print(ubuntu.answers_usage.name)
    LAUNCHPAD
    >>> print(ubuntu.blueprints_usage.name)
    LAUNCHPAD
    >>> print(ubuntu.translations_usage.name)
    LAUNCHPAD

The bug_tracking_usage property currently only tracks official_malone.

    >>> print(ubuntu.bug_tracking_usage.name)
    LAUNCHPAD

While the other attributes track the other official_ attributes.

    >>> print(ubuntu.official_answers)
    True
    >>> print(ubuntu.answers_usage.name)
    LAUNCHPAD
    >>> print(ubuntu.official_blueprints)
    True
    >>> print(ubuntu.blueprints_usage.name)
    LAUNCHPAD

If the official_ attributes are False and the enum hasn't been set,
the usage enums don't know anything.

    >>> ignored = login_person(ubuntu.owner.teamowner)
    >>> ubuntu.official_answers = False
    >>> print(ubuntu.answers_usage.name)
    UNKNOWN

A distribution *cannot* specify that it uses codehosting. Currently there's
no way for a distribution to use codehosting.

    >>> from lp.app.enums import ServiceUsage
    >>> print(ubuntu.codehosting_usage.name)
    NOT_APPLICABLE
    >>> ubuntu.codehosting_usage = ServiceUsage.LAUNCHPAD
    Traceback (most recent call last):
    AttributeError: can't set attribute...

While Debian uses none:

    >>> debian = getUtility(ILaunchpadCelebrities).debian
    >>> print(debian.bug_tracking_usage.name)
    UNKNOWN
    >>> print(debian.translations_usage.name)
    UNKNOWN
    >>> print(debian.answers_usage.name)
    UNKNOWN
    >>> print(debian.codehosting_usage.name)
    NOT_APPLICABLE
    >>> print(debian.blueprints_usage.name)
    UNKNOWN

Gentoo only uses Malone

    >>> print(gentoo.bug_tracking_usage.name)
    LAUNCHPAD
    >>> print(gentoo.translations_usage.name)
    UNKNOWN
    >>> print(gentoo.answers_usage.name)
    UNKNOWN

Launchpad admins and the distro owner can set these fields.

    >>> from lp.app.enums import ServiceUsage
    >>> login("mark@example.com")
    >>> debian = getUtility(ILaunchpadCelebrities).debian
    >>> debian.blueprints_usage = ServiceUsage.LAUNCHPAD
    >>> print(debian.blueprints_usage.name)
    LAUNCHPAD
    >>> debian.official_malone = True
    >>> debian.official_malone
    True
    >>> debian.translations_usage = ServiceUsage.LAUNCHPAD
    >>> debian.translations_usage.name
    'LAUNCHPAD'

    >>> debian_owner = factory.makePerson()
    >>> debian.owner = debian_owner
    >>> ignored = login_person(debian_owner)
    >>> debian.blueprints_usage = ServiceUsage.NOT_APPLICABLE
    >>> print(debian.blueprints_usage.name)
    NOT_APPLICABLE

But others can't.

    >>> login("no-priv@canonical.com")
    >>> debian.blueprints_usage = ServiceUsage.LAUNCHPAD
    Traceback (most recent call last):
    zope.security.interfaces.Unauthorized:
    (..., 'blueprints_usage', 'launchpad.Edit')
    >>> debian.official_malone = True
    Traceback (most recent call last):
    zope.security.interfaces.Unauthorized:
    (..., 'official_malone', 'launchpad.Edit')
    >>> debian.translations_usage = ServiceUsage.LAUNCHPAD
    Traceback (most recent call last):
    zope.security.interfaces.Unauthorized:
    (..., 'translations_usage', 'launchpad.TranslationsAdmin')


Specification Listings
......................

We should be able to get lists of specifications in different states
related to a distro.

Basically, we can filter by completeness, and by whether or not the spec is
informational.

    >>> kubuntu = distroset.getByName("kubuntu")

    >>> from lp.blueprints.enums import SpecificationFilter

First, there should be one informational spec for kubuntu, but it is
complete so it will not show up unless we explicitly ask for complete specs:

    >>> filter = [SpecificationFilter.INFORMATIONAL]
    >>> kubuntu.specifications(None, filter=filter).count()
    0
    >>> filter = [
    ...     SpecificationFilter.INFORMATIONAL,
    ...     SpecificationFilter.COMPLETE,
    ... ]
    >>> kubuntu.specifications(None, filter=filter).count()
    1


There are 2 completed specs for Kubuntu:

    >>> filter = [SpecificationFilter.COMPLETE]
    >>> for spec in kubuntu.specifications(None, filter=filter):
    ...     print(spec.name, spec.is_complete)
    ...
    thinclient-local-devices True
    usplash-on-hibernation True


And there are four incomplete specs:

    >>> filter = [SpecificationFilter.INCOMPLETE]
    >>> for spec in kubuntu.specifications(None, filter=filter):
    ...     print(spec.name, spec.is_complete)
    ...
    cluster-installation False
    revu False
    kde-desktopfile-langpacks False
    krunch-desktop-plan False


If we ask for all specs, we get them in the order of priority.

    >>> filter = [SpecificationFilter.ALL]
    >>> for spec in kubuntu.specifications(None, filter=filter):
    ...     print(spec.priority.title, spec.name)
    ...
    Essential cluster-installation
    High revu
    Medium thinclient-local-devices
    Low usplash-on-hibernation
    Undefined kde-desktopfile-langpacks
    Not krunch-desktop-plan


And if we ask just for specs, we get the incomplete ones.

    >>> for spec in kubuntu.specifications(None):
    ...     print(spec.name, spec.is_complete)
    ...
    cluster-installation False
    revu False
    kde-desktopfile-langpacks False
    krunch-desktop-plan False

We can filter for specifications that contain specific text:

    >>> for spec in kubuntu.specifications(None, filter=["package"]):
    ...     print(spec.name)
    ...
    revu

We can get only valid specs (those that are not obsolete or superseded):

    >>> from lp.blueprints.enums import SpecificationDefinitionStatus
    >>> login("mark@example.com")
    >>> for spec in kubuntu.specifications(None):
    ...     # Do this here, otherwise, the change will be flush before
    ...     # updateLifecycleStatus() acts and an IntegrityError will be
    ...     # raised.
    ...     owner = spec.owner
    ...     if spec.name in ["cluster-installation", "revu"]:
    ...         spec.definition_status = (
    ...             SpecificationDefinitionStatus.OBSOLETE
    ...         )
    ...     if spec.name in ["krunch-desktop-plan"]:
    ...         spec.definition_status = (
    ...             SpecificationDefinitionStatus.SUPERSEDED
    ...         )
    ...     shim = spec.updateLifecycleStatus(owner)
    ...
    >>> for spec in kubuntu.valid_specifications():
    ...     print(spec.name)
    ...
    kde-desktopfile-langpacks


Milestones
----------

We can use IDistribution.milestones to get all milestones associated with any
series of a distribution.

    >>> from datetime import datetime
    >>> for milestone in debian.milestones:
    ...     print(milestone.name)
    ...
    3.1
    3.1-rc1

    >>> woody = debian["woody"]

Milestones for distros can only be created by distro owners or admins.

    >>> login("no-priv@canonical.com")
    >>> woody.newMilestone(
    ...     name="impossible", dateexpected=datetime(2028, 10, 1)
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized:
    (<DistroSeries ...'woody'>, 'newMilestone', 'launchpad.Edit')
    >>> login("mark@example.com")
    >>> debian_milestone = woody.newMilestone(
    ...     name="woody-rc1", dateexpected=datetime(2028, 10, 1)
    ... )

They're ordered by dateexpected.

    >>> for milestone in debian.milestones:
    ...     print(
    ...         "%s: %s"
    ...         % (
    ...             milestone.name,
    ...             milestone.dateexpected.strftime("%Y-%m-%d"),
    ...         )
    ...     )
    ...
    3.1: 2056-05-16
    3.1-rc1: 2056-02-16
    woody-rc1: 2028-10-01

Only milestones which have visible=True are returned by the .milestones
property.

    >>> debian_milestone.active = False
    >>> for milestone in debian.milestones:
    ...     print(milestone.name)
    ...
    3.1
    3.1-rc1

To get all milestones of a given distro we have the .all_milestones property.

    >>> for milestone in debian.all_milestones:
    ...     print(milestone.name)
    ...
    3.1
    3.1-rc1
    woody-rc1


Archives
--------

A distribution archive (primary, partner, debug or copy) can be retrieved
by name using IDistribution.getArchive.

    >>> def display_archive(archive):
    ...     print(
    ...         "%s %s %s"
    ...         % (
    ...             archive.distribution.name,
    ...             archive.owner.name,
    ...             archive.name,
    ...         )
    ...     )
    ...
    >>> display_archive(ubuntu.getArchive("primary"))
    ubuntu ubuntu-team primary
    >>> display_archive(ubuntu.getArchive("partner"))
    ubuntu ubuntu-team partner
    >>> display_archive(debian.getArchive("primary"))
    debian mark primary
    >>> ubuntu.getArchive("ppa")
    >>> debian.getArchive("partner")
