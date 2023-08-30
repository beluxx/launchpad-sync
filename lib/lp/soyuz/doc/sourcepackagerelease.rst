Source Package Release
======================

The SourcePackageRelease table represents a particular release of a
SourcePackageName, but isn't tied to any particular DistroSeries
as the same release can appear in many.

In a very basic explanation, this table caches the attributes of an
uploaded DSC (Debian Source Control) file.

This model allow us to have more granular control of the fields,
enabling faster searches, faster readings and model constraints.

Basic attributes
----------------

Let's get one from the database:

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
    >>> spr = IStore(SourcePackageRelease).get(SourcePackageRelease, 20)
    >>> print(spr.name)
    pmount
    >>> print(spr.version)
    0.1-1
    >>> spr.dateuploaded
    datetime.datetime(2005, 3, 24, 20, 59, 31, 439579,
        tzinfo=datetime.timezone.utc)

published_archives returns a set of all the archives that this
SourcePackageRelease is published in.

    >>> for archive in spr.published_archives:
    ...     print(archive.displayname)
    ...
    Primary Archive for Ubuntu Linux
    PPA for Celso Providelo

'age' is a special property that performs on-the-fly:
{{{
NOW - dateuploaded
}}}
It returns a timedelta object:

    >>> spr.age
    datetime.timedelta(...)

Check if the result match the locally calculated one:

    >>> from datetime import datetime, timedelta, timezone
    >>> local_now = datetime.now(timezone.utc)

    >>> expected_age = local_now - spr.dateuploaded
    >>> spr.age.days == expected_age.days
    True

Modify dateuploaded to a certain number of days in the past and check
if the 'age' result looks sane:

    >>> spr.dateuploaded = local_now - timedelta(days=10)
    >>> spr.age.days == 10
    True

pmount 0.1-1 has got some builds. including a PPA build.  The 'builds'
property only returns the non-PPA builds.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
    >>> from storm.store import Store
    >>> cprov_ppa = getUtility(IPersonSet).getByName("cprov").archive
    >>> ff_ppa_build = Store.of(cprov_ppa).find(
    ...     BinaryPackageBuild,
    ...     BinaryPackageBuild.source_package_release == spr,
    ...     BinaryPackageBuild.archive == cprov_ppa,
    ... )
    >>> ff_ppa_build.count()
    1
    >>> ff_ppa_build[0].archive.purpose.name
    'PPA'
    >>> spr.builds.count()
    4

All the builds returned are for non-PPA archives:

    >>> for item in set(build.archive.purpose.name for build in spr.builds):
    ...     print(item)
    ...
    PRIMARY

Check that the uploaded changesfile works:

    >>> commercial = IStore(SourcePackageRelease).get(
    ...     SourcePackageRelease, 36
    ... )
    >>> commercial.upload_changesfile.http_url
    'http://.../commercialpackage_1.0-1_source.changes'

Check ISourcePackageRelease.override() behaviour:

    >>> print(spr.component.name)
    main
    >>> print(spr.section.name)
    web

    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> from lp.soyuz.interfaces.section import ISectionSet
    >>> new_comp = getUtility(IComponentSet)["universe"]
    >>> new_sec = getUtility(ISectionSet)["mail"]

Override the current sourcepackagerelease with new component/section
pair:

    >>> spr.override(component=new_comp, section=new_sec)

    >>> print(spr.component.name)
    universe
    >>> print(spr.section.name)
    mail

Abort transaction to avoid error propagation of the new attributes:

    >>> import transaction
    >>> transaction.abort()


Verify the creation of a new ISourcePackageRelease based on the
IDistroSeries API:

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.gpg import IGPGKeySet
    >>> from lp.registry.interfaces.sourcepackage import (
    ...     SourcePackageType,
    ...     SourcePackageUrgency,
    ... )
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet,
    ... )

    >>> hoary = getUtility(IDistributionSet)["ubuntu"]["hoary"]

All the arguments to create an ISourcePackageRelease are obtained when
processing a source upload, see more details in nascentupload.rst.
Some of the 20 required arguments are foreign keys or DB constants:

    >>> arg_name = getUtility(ISourcePackageNameSet)["pmount"]
    >>> arg_comp = getUtility(IComponentSet)["universe"]
    >>> arg_sect = getUtility(ISectionSet)["web"]
    >>> arg_key = getUtility(IGPGKeySet).getByFingerprint(
    ...     "ABCDEF0123456789ABCDDCBA0000111112345678"
    ... )
    >>> arg_maintainer = hoary.owner
    >>> arg_creator = hoary.owner
    >>> arg_urgency = SourcePackageUrgency.LOW
    >>> arg_recipebuild = factory.makeSourcePackageRecipeBuild()
    >>> changelog = None

The other arguments are strings:

    >>> version = "0.0.99"
    >>> dsc = "smashed dsc..."
    >>> copyright = "smashed debian/copyright ..."
    >>> changelog_entry = "contiguous text..."
    >>> archhintlist = "any"
    >>> builddepends = "cdbs, debhelper (>= 4.1.0), libsysfs-dev, libhal-dev"
    >>> builddependsindep = ""
    >>> dsc_maintainer_rfc822 = "Foo Bar <foo@bar.com>"
    >>> dsc_standards_version = "2.6.1"
    >>> dsc_format = "1.0"
    >>> dsc_binaries = "pmount"
    >>> archive = hoary.main_archive

Having proper arguments in hand we can create a new
ISourcePackageRelease, it will automatically set the
'upload_distroseries' to the API entry point, in this case Hoary.

    >>> new_spr = hoary.createUploadedSourcePackageRelease(
    ...     sourcepackagename=arg_name,
    ...     version=version,
    ...     format=SourcePackageType.DPKG,
    ...     maintainer=arg_maintainer,
    ...     builddepends=builddepends,
    ...     builddependsindep=builddependsindep,
    ...     architecturehintlist=archhintlist,
    ...     component=arg_comp,
    ...     creator=arg_creator,
    ...     urgency=arg_urgency,
    ...     changelog=changelog,
    ...     changelog_entry=changelog_entry,
    ...     dsc=dsc,
    ...     dscsigningkey=arg_key,
    ...     section=arg_sect,
    ...     dsc_maintainer_rfc822=dsc_maintainer_rfc822,
    ...     dsc_standards_version=dsc_standards_version,
    ...     dsc_format=dsc_format,
    ...     dsc_binaries=dsc_binaries,
    ...     archive=archive,
    ...     copyright=copyright,
    ...     build_conflicts=None,
    ...     build_conflicts_indep=None,
    ...     source_package_recipe_build=arg_recipebuild,
    ... )

    >>> print(new_spr.upload_distroseries.name)
    hoary
    >>> print(new_spr.version)
    0.0.99
    >>> new_spr.upload_archive.id == hoary.main_archive.id
    True
    >>> print(new_spr.copyright)
    smashed debian/copyright ...
    >>> new_spr.source_package_recipe_build == arg_recipebuild
    True

Throw away the DB changes:

    >>> transaction.abort()

Let's get a sample SourcePackageRelease:

    >>> spr_test = IStore(SourcePackageRelease).get(SourcePackageRelease, 20)
    >>> print(spr_test.name)
    pmount


Package sizes
-------------

The size of a source package can be obtained via the getPackageSize() method.
It returns the sum of the size of all files comprising the source package (in
kilo-bytes).

    >>> spr = IStore(SourcePackageRelease).get(SourcePackageRelease, 14)
    >>> print(spr.name)
    mozilla-firefox
    >>> spr.getPackageSize()
    9690.0

Verify that empty packages have a size of zero.

    >>> from lp.registry.model.sourcepackagename import SourcePackageName
    >>> linux_src = SourcePackageName.selectOneBy(name="linux-source-2.6.15")
    >>> spr = (
    ...     IStore(SourcePackageRelease)
    ...     .find(
    ...         SourcePackageRelease,
    ...         sourcepackagename=linux_src,
    ...         version="2.6.15.3",
    ...     )
    ...     .one()
    ... )
    >>> spr.getPackageSize()
    0.0


Accessing SourcePackageReleases
-------------------------------

SourcePackageReleases are accessible according to the archives where
they are published.

We will use SoyuzTestPublisher to create new publications.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher

    >>> test_publisher = SoyuzTestPublisher()

    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> hoary = ubuntu.getSeries("hoary")
    >>> test_publisher.addFakeChroots(hoary)
    >>> unused = test_publisher.setUpDefaultDistroSeries(hoary)

If a SourcePackageRelease is only published in a private PPA, only
users with access (launchpad.View) to that archive will be able to get
the same permission on it.

    >>> cprov = getUtility(IPersonSet).getByName("cprov")

    >>> login("foo.bar@canonical.com")
    >>> cprov_private_ppa = factory.makeArchive(
    ...     owner=cprov, private=True, name="pppa"
    ... )

    >>> private_publication = test_publisher.getPubSource(
    ...     archive=cprov_private_ppa
    ... )

    >>> test_sourcepackagerelease = private_publication.sourcepackagerelease
    >>> print(test_sourcepackagerelease.title)
    foo - 666

    >>> published_archives = test_sourcepackagerelease.published_archives
    >>> for archive in published_archives:
    ...     print(archive.displayname)
    ...
    PPA named pppa for Celso Providelo

'foo - 666' sourcepackagerelease is only published in Celso's Private
PPA. So, Only Celso and administrators can get 'launchpad.View' on it.

    >>> from lp.services.webapp.authorization import check_permission

    >>> login("no-priv@canonical.com")
    >>> check_permission("launchpad.View", test_sourcepackagerelease)
    False

    >>> login("celso.providelo@canonical.com")
    >>> check_permission("launchpad.View", test_sourcepackagerelease)
    True

    >>> login("foo.bar@canonical.com")
    >>> check_permission("launchpad.View", test_sourcepackagerelease)
    True

Once the SourcePackageRelease in question gets copied to a public
archive, let's say Ubuntu primary archive, it will become publicly
available.

    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket

    >>> public_publication = private_publication.copyTo(
    ...     hoary, PackagePublishingPocket.RELEASE, ubuntu.main_archive
    ... )

'foo - 666' is now published in Celso's private PPA and the Ubuntu
primary archive, which is public.

    >>> published_archives = test_sourcepackagerelease.published_archives
    >>> for archive in published_archives:
    ...     print(archive.displayname)
    ...
    Primary Archive for Ubuntu Linux
    PPA named pppa for Celso Providelo

And we can see it's publicly available now, as expected.

    >>> login(ANONYMOUS)
    >>> check_permission("launchpad.View", test_sourcepackagerelease)
    True

    >>> login("no-priv@canonical.com")
    >>> check_permission("launchpad.View", test_sourcepackagerelease)
    True

    >>> login("celso.providelo@canonical.com")
    >>> check_permission("launchpad.View", test_sourcepackagerelease)
    True

    >>> login("foo.bar@canonical.com")
    >>> check_permission("launchpad.View", test_sourcepackagerelease)
    True

Another common scenario is that once the package is unembargoed from the
private PPA, it gets deleted from that private PPA.  At this point the
package is still public:

    >>> private_publication.requestDeletion(cprov)
    >>> transaction.commit()
    >>> login("no-priv@canonical.com")
    >>> check_permission("launchpad.View", test_sourcepackagerelease)
    True

The next stage of the lifecycle is for the remaining publication to be
superseded.  The package will still be public after that happens.

    >>> login("foo.bar@canonical.com")
    >>> unused = public_publication.supersede()
    >>> transaction.commit()
    >>> login("no-priv@canonical.com")
    >>> check_permission("launchpad.View", test_sourcepackagerelease)
    True

published_archives shows the superseded/deleted publications still:

    >>> published_archives = test_sourcepackagerelease.published_archives
    >>> for archive in published_archives:
    ...     print(archive.displayname)
    ...
    Primary Archive for Ubuntu Linux
    PPA named pppa for Celso Providelo
