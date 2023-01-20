Personal Package Archives
=========================

An Archive models a Debian Archive, providing operations like
publication lookups and the complete publishing-pipeline from database
records to disk, including configuration and indexes.

    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.enums import ArchivePurpose, ArchiveStatus
    >>> from lp.soyuz.interfaces.archive import IArchiveSet, IArchive

    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> cprov_archive = cprov.archive

    >>> print(cprov_archive.owner.name)
    cprov
    >>> print(cprov_archive.distribution.name)
    ubuntu
    >>> print(cprov_archive.name)
    ppa
    >>> print(cprov_archive.purpose.name)
    PPA
    >>> print(cprov_archive.displayname)
    PPA for Celso Providelo
    >>> cprov_archive.enabled
    True
    >>> cprov_archive.authorized_size
    1024
    >>> print(cprov_archive.signing_key)
    None
    >>> print(cprov_archive.signing_key_fingerprint)
    None
    >>> cprov_archive.private
    False
    >>> cprov_archive.require_virtualized
    True
    >>> cprov_archive.sources_cached
    3
    >>> cprov_archive.binaries_cached
    3
    >>> cprov_archive.is_ppa
    True
    >>> cprov_archive.is_main
    False
    >>> cprov_archive.is_primary
    False
    >>> cprov_archive.is_partner
    False
    >>> cprov_archive.is_active
    True
    >>> cprov_archive.distribution.main_archive.is_main
    True
    >>> cprov_archive.distribution.main_archive.is_primary
    True
    >>> cprov_archive.total_count
    4
    >>> cprov_archive.pending_count
    0
    >>> cprov_archive.succeeded_count
    3
    >>> cprov_archive.building_count
    0
    >>> cprov_archive.failed_count
    1

    >>> cprov_private_ppa = factory.makeArchive(
    ...     owner=cprov,
    ...     name="myprivateppa",
    ...     distribution=cprov_archive.distribution,
    ... )
    >>> login("foo.bar@canonical.com")
    >>> cprov_private_ppa.private = True
    >>> login(ANONYMOUS)

external_dependencies is a property that can be set only by LP admins and
read by anyone.  It is a text field that should contain a comma-separated
list of sources.list entries in the format:
deb http[s]://[user:pass@]<host>[/path] %(series)s[-pocket] [components]
where the series variable is replaced with the series name of the context
build.  This allows an admin to set external repositories as a source for
build dependencies on the context PPA.  Its default value is None:

    >>> print(cprov_archive.external_dependencies)
    None

Amending it as an unprivileged user results in failure:

    >>> cprov_archive.external_dependencies = "test"
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized:
    (..., 'external_dependencies', 'launchpad.Admin')

As a Launchpad admin, setting this property will work.

    >>> login("admin@canonical.com")
    >>> cprov_archive.external_dependencies = "deb http://foo hardy bar"

Useful properties:

    >>> print(cprov_archive.archive_url)
    http://ppa.launchpad.test/cprov/ppa/ubuntu

Inquire what Distribution Series this archive has published sources to:

    >>> for s in cprov_archive.series_with_sources:
    ...     print(s.name)
    ...
    breezy-autotest
    warty

'purpose' is a read-only attribute, it can't and shouldn't be modified
once a IArchive is created. Changing those values would affect the way
archives are published on disk.

    >>> cprov_archive.purpose = ArchivePurpose.COPY
    Traceback (most recent call last):
    ...
    zope.security.interfaces.ForbiddenAttribute: ('purpose', <Archive at ...>)

'status' tracks the status of an Archive.  Its current values are only
ACTIVE and DELETING.  ACTIVE is the normal value; DELETING is set when
the user has requested the PPA to be deleted.  The actual deletion is done
some time later in a zopeless script.

It is only editable by someone with launchpad.Edit permissions:

    >>> print(cprov_archive.status.name)
    ACTIVE

    >>> cprov_archive.status = ArchiveStatus.DELETING
    >>> print(cprov_archive.status.name)
    DELETING

    >>> login(ANONYMOUS)
    >>> cprov_archive.status = ArchiveStatus.ACTIVE
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> login("admin@canonical.com")
    >>> cprov_archive.status = ArchiveStatus.ACTIVE


'name' is only editable by an LP administrator and only exposed via the
ArchiveRebuild user interface. PRIMARY and PARTNER archives cannot be
renamed, and PPA named can only be changed once the PPA has been
deleted.

    >>> login("celso.providelo@canonical.com")

    >>> cprov_archive.name = "no-it-will-not-change-yet"
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: (..., 'name', 'launchpad.Admin')

When editable, the 'name' field is protected by a constraint that
asserts the archive is indeed a COPY and if the name is valid.

    >>> login("foo.bar@canonical.com")

    >>> cprov_archive.name = "there-we-go"
    Traceback (most recent call last):
    ...
    AssertionError: Only COPY archives and deleted PPAs can be renamed.

We will create a COPY archive and modify its name.

    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> rebuild_owner = factory.makePerson(
    ...     name="juergen", displayname="J\xfcrgen"
    ... )
    >>> rebuild_archive = getUtility(IArchiveSet).new(
    ...     owner=rebuild_owner,
    ...     purpose=ArchivePurpose.COPY,
    ...     distribution=ubuntu,
    ...     name="editable-rebuild",
    ...     enabled=False,
    ...     require_virtualized=False,
    ... )

By default, copy archives are created with their 'publish' flag
turned off, so that the publisher ignores them.

    >>> rebuild_archive.publish
    False

Also, copy archives are typically disabled upon creation so that the owner
has a chance to tweak the archive's dependencies before build activity
starts.

    >>> rebuild_archive.enabled
    False

And, builds for copy archives are to be carried out on non-virtual builders.

    >>> rebuild_archive.require_virtualized
    False

Only 'valid' (traversable) names can be set.

    >>> rebuild_archive.name = "ThereWeGo"
    Traceback (most recent call last):
    ...
    AssertionError: Invalid name given to unproxied object.

Valid names work as expected.

    >>> rebuild_archive.name = "there-we-go"
    >>> print(rebuild_archive.name)
    there-we-go

Please note that copy archive displayname doesn't follow the name change.

    >>> print(backslashreplace(rebuild_archive.displayname))
    Copy archive editable-rebuild for J\xfcrgen

The "is_copy" property allows us to ask an archive whether it's a copy
archive.

    >>> rebuild_archive.is_copy
    True

    >>> cprov_archive.is_copy
    False

Uploads to copy archives are not allowed.

    >>> print(rebuild_archive.checkArchivePermission(cprov))
    False


Published Source and Binary Lookup
----------------------------------

IArchive implements a published source & binary lookup methods,
returning I{Source, Binary}PackagePublishingHistory objects.

    >>> cprov_archive.getPublishedSources().count()
    3

    >>> cprov_archive.getPublishedOnDiskBinaries().count()
    3

    >>> cprov_archive.getAllPublishedBinaries().count()
    4

This lookup also supports various filters - see the api docs for more info.

Binary publication lookups
--------------------------

'getPublishedOnDiskBinaries' returns only unique publications, i.e., it
excludes architecture-independent duplications which is necessary for
having correct publication counters and archive size.

    >>> from lp.soyuz.enums import PackagePublishingStatus
    >>> from lp.soyuz.interfaces.publishing import (
    ...     active_publishing_status,
    ...     inactive_publishing_status,
    ... )

    >>> warty = cprov_archive.distribution["warty"]
    >>> hoary = cprov_archive.distribution["hoary"]
    >>> breezy_autotest = cprov_archive.distribution["breezy-autotest"]
    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket

    >>> def check_bin_pubs(pubs):
    ...     """Print binary publication details."""
    ...     for pub in pubs:
    ...         title = pub.binarypackagerelease.title
    ...         arch_spec = pub.binarypackagerelease.architecturespecific
    ...         pub_arch = pub.distroarchseries.architecturetag
    ...         print("%s (%s) -> %s" % (title, arch_spec, pub_arch))
    ...

The PPA for cprov contains only 4 binary publications, however 'pmount' is
'architecture independent', which means that the same binary (DB) is
published for all available architectures, i386 & hppa:

    >>> all_cprov_bin_pubs = cprov_archive.getAllPublishedBinaries()

    >>> check_bin_pubs(all_cprov_bin_pubs)
    mozilla-firefox-1.0 (True) -> hppa
    mozilla-firefox-1.0 (True) -> i386
    pmount-0.1-1 (False) -> hppa
    pmount-0.1-1 (False) -> i386

'getPublishedOnDiskBinaries' automatically filters multiple publications of
'pmount' considering only the publication to the 'nominatedarchindep'
(defined for each distroseries).

    >>> unique_cprov_bin_pubs = cprov_archive.getPublishedOnDiskBinaries()

    >>> check_bin_pubs(unique_cprov_bin_pubs)
    mozilla-firefox-1.0 (True) -> i386
    pmount-0.1-1 (False) -> i386
    mozilla-firefox-1.0 (True) -> hppa

'name' filter supporting partial string matching and 'not-found':

    >>> cprov_archive.getPublishedOnDiskBinaries(name="pmou").count()
    1
    >>> cprov_archive.getAllPublishedBinaries(name="pmou").count()
    2
    >>> cprov_archive.getPublishedOnDiskBinaries(name="foo").count()
    0
    >>> cprov_archive.getAllPublishedBinaries(name="foo").count()
    0

Combining 'name' filter and 'exact_match' flag:

    >>> cprov_archive.getAllPublishedBinaries(
    ...     name="pmou", exact_match=True
    ... ).count()
    0
    >>> cprov_archive.getAllPublishedBinaries(
    ...     name="pmount", exact_match=True
    ... ).count()
    2
    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     name="pmou", exact_match=True
    ... ).count()
    0
    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     name="pmount", exact_match=True
    ... ).count()
    1

It's possible to associate 'name' and 'version' filters:

    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     name="moz", version="1.0"
    ... ).count()
    2

    >>> cprov_archive.getAllPublishedBinaries(
    ...     name="moz", version="1.0"
    ... ).count()
    2

    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     name="moz", version="666"
    ... ).count()
    0

    >>> cprov_archive.getAllPublishedBinaries(
    ...     name="moz", version="666"
    ... ).count()
    0

Both methods do not support passing the 'version' filter if the 'name'
filter is not passed too.

    >>> moz_version_lookup = cprov_archive.getAllPublishedBinaries(
    ...     version="1.0"
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.VersionRequiresName: The 'version' parameter
    can be used only together with the 'name' parameter.

    >>> moz_version_lookup = cprov_archive.getPublishedOnDiskBinaries(
    ...     version="1.0"
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.VersionRequiresName: The 'version' parameter
    can be used only together with the 'name' parameter.

Both methods support 'status' filter:

    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     status=PackagePublishingStatus.PUBLISHED
    ... ).count()
    3

    >>> cprov_archive.getAllPublishedBinaries(
    ...     status=PackagePublishingStatus.PUBLISHED
    ... ).count()
    4

    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     status=active_publishing_status
    ... ).count()
    3

    >>> cprov_archive.getAllPublishedBinaries(
    ...     status=active_publishing_status
    ... ).count()
    4

    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     status=inactive_publishing_status
    ... ).count()
    0

    >>> cprov_archive.getAllPublishedBinaries(
    ...     status=inactive_publishing_status
    ... ).count()
    0

Using 'distroarchseries' filter:

    >>> warty_i386 = warty["i386"]
    >>> warty_hppa = warty["hppa"]

    >>> cprov_archive.getAllPublishedBinaries(
    ...     distroarchseries=warty_i386
    ... ).count()
    2
    >>> cprov_archive.getAllPublishedBinaries(
    ...     distroarchseries=warty_hppa
    ... ).count()
    2

    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     distroarchseries=warty_i386
    ... ).count()
    2
    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     distroarchseries=warty_hppa
    ... ).count()
    1

    >>> cprov_archive.getAllPublishedBinaries(
    ...     distroarchseries=[warty_i386, warty_hppa]
    ... ).count()
    4
    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     distroarchseries=[warty_i386, warty_hppa]
    ... ).count()
    3

Using 'pocket' filter:

    >>> cprov_archive.getAllPublishedBinaries(
    ...     distroarchseries=warty_i386,
    ...     pocket=PackagePublishingPocket.RELEASE,
    ... ).count()
    2
    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     distroarchseries=warty_i386,
    ...     pocket=PackagePublishingPocket.RELEASE,
    ... ).count()
    2

    >>> cprov_archive.getAllPublishedBinaries(
    ...     distroarchseries=warty_i386,
    ...     pocket=PackagePublishingPocket.UPDATES,
    ... ).count()
    0
    >>> cprov_archive.getPublishedOnDiskBinaries(
    ...     distroarchseries=warty_i386,
    ...     pocket=PackagePublishingPocket.UPDATES,
    ... ).count()
    0

Associating 'name' and 'status' filters:

    >>> status_lookup = cprov_archive.getPublishedOnDiskBinaries(
    ...     name="pmount", status=active_publishing_status
    ... )
    >>> status_lookup.count()
    1

    >>> status_lookup = cprov_archive.getAllPublishedBinaries(
    ...     name="pmount", status=active_publishing_status
    ... )
    >>> status_lookup.count()
    2

    >>> status_lookup = cprov_archive.getPublishedOnDiskBinaries(
    ...     name="foo", status=active_publishing_status
    ... )
    >>> status_lookup.count()
    0

    >>> status_lookup = cprov_archive.getAllPublishedBinaries(
    ...     name="foo", status=active_publishing_status
    ... )
    >>> status_lookup.count()
    0

Associating 'name', 'version' and 'status' filters:

    >>> status_lookup = cprov_archive.getPublishedOnDiskBinaries(
    ...     name="pmount", version="0.1-1", status=active_publishing_status
    ... )
    >>> status_lookup.count()
    1

    >>> status_lookup = cprov_archive.getAllPublishedBinaries(
    ...     name="pmount", version="0.1-1", status=active_publishing_status
    ... )
    >>> status_lookup.count()
    2

    >>> status_lookup = cprov_archive.getPublishedOnDiskBinaries(
    ...     name="pmount", version="666", status=active_publishing_status
    ... )
    >>> status_lookup.count()
    0

    >>> status_lookup = cprov_archive.getAllPublishedBinaries(
    ...     name="pmount", version="666", status=active_publishing_status
    ... )
    >>> status_lookup.count()
    0

Associating 'name', 'version', 'status' and 'distroarchseries' filters
and 'exact_match' flag:

    >>> status_lookup = cprov_archive.getAllPublishedBinaries(
    ...     name="pmount",
    ...     version="0.1-1",
    ...     distroarchseries=warty_i386,
    ...     status=active_publishing_status,
    ...     exact_match=True,
    ... )
    >>> status_lookup.count()
    1

    >>> status_lookup = cprov_archive.getAllPublishedBinaries(
    ...     name="pmount",
    ...     version="0.1-1",
    ...     distroarchseries=[warty_i386, warty_hppa],
    ...     status=active_publishing_status,
    ...     exact_match=True,
    ... )
    >>> status_lookup.count()
    2

Package Counters
----------------

IArchive provides properties to calculate the number and the size of
the packages (sources and binaries) currently published in the
archive. They are based in the publication lookup methods.

    >>> cprov_archive.number_of_sources
    3
    >>> cprov_archive.number_of_binaries
    3
    >>> cprov_archive.sources_size
    9923399
    >>> cprov_archive.binaries_size
    3

Additionally we have another property to sum up the sources and the
binaries size and a pre-defined increment related to the files created
in the archive (+1kbytes for each publication)

    >>> pool_size = cprov_archive.sources_size + cprov_archive.binaries_size

    >>> number_of_publications = (
    ...     cprov_archive.number_of_sources + cprov_archive.number_of_binaries
    ... )
    >>> indexes_size = number_of_publications * 1024

    >>> estimated_size = cprov_archive.estimated_size
    >>> estimated_size
    9929546

    >>> estimated_size == pool_size + indexes_size
    True

The 'estimated_size' property automatically excludes duplicated published
files as it happens in the archive filesystem (pool/):

    >>> def print_published_files(archive):
    ...     for pub_source in archive.getPublishedSources():
    ...         for src_file in pub_source.sourcepackagerelease.files:
    ...             print(
    ...                 "%s: %s (%s, %d bytes)"
    ...                 % (
    ...                     src_file.sourcepackagerelease.title,
    ...                     src_file.libraryfile.filename,
    ...                     src_file.filetype.name,
    ...                     src_file.libraryfile.content.filesize,
    ...                 )
    ...             )
    ...

First, let's print the currently published files in cprov's PPA:

    >>> print_published_files(cprov_archive)
    cdrkit - 1.0: foobar-1.0.dsc (DSC, 716 bytes)
    iceweasel - 1.0: firefox_0.9.2.orig.tar.gz (ORIG_TARBALL, 9922560 bytes)
    iceweasel - 1.0: iceweasel-1.0.dsc (DSC, 123 bytes)

Now we will emulate a duplicated reference to the same 'orig.tar.gz',
upstream tarball, as if it was part of two different SourcePackageRelease.

    >>> from lp.services.librarian.interfaces import (
    ...     ILibraryFileAliasSet,
    ... )
    >>> huge_firefox_orig_file = getUtility(ILibraryFileAliasSet)[3]
    >>> cprov_cdrkit_src = cprov_archive.getPublishedSources(
    ...     name="cdrkit"
    ... ).first()
    >>> unused_src_file = cprov_cdrkit_src.sourcepackagerelease.addFile(
    ...     huge_firefox_orig_file
    ... )

As we see below, now we have two references to
'firefox_0.9.2.orig.tar.gz' file.

    >>> print_published_files(cprov_archive)
    cdrkit - 1.0: firefox_0.9.2.orig.tar.gz (ORIG_TARBALL, 9922560 bytes)
    cdrkit - 1.0: foobar-1.0.dsc (DSC, 716 bytes)
    iceweasel - 1.0: firefox_0.9.2.orig.tar.gz (ORIG_TARBALL, 9922560 bytes)
    iceweasel - 1.0: iceweasel-1.0.dsc (DSC, 123 bytes)

Similarly to what happen in the archive disk 'pool', where already
published files satisfy the new reference, the file size is not
computed again in the archive total size.

    >>> estimated_size == cprov_archive.estimated_size
    True

As mentioned before the package counters do not include non-PUBLISHED
packages, to verify this we will mark some package as SUPERSEDED and
see if the counter decreases.

Superseding a source package and verifying that the source counter
decreases.

    >>> cprov_archive.number_of_sources
    3
    >>> cdrkit = cprov_archive.getPublishedSources(name="cdrkit").first()
    >>> cdrkit.supersede()
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.services.database.constants import UTC_NOW
    >>> removeSecurityProxy(cdrkit).scheduleddeletiondate = UTC_NOW

    >>> cprov_archive.number_of_sources
    2

Superseding a binary package and verifying that the binary counter
decreases.

    >>> cprov_archive.number_of_binaries
    3
    >>> cprov_archive.getAllPublishedBinaries(name="mozilla-firefox")[
    ...     0
    ... ].supersede()

    >>> cprov_archive.number_of_binaries
    2


Sources available for deletions
-------------------------------

'getSourcesForDeletion' is the base for '+delete-packages' page on PPA
context it allows us to lookup for `ISourcePackagePublishingHistory`
records which were not deleted yet.

Basically, it returns any PENDING or PUBLISHED source publication or
the ones in any state containing one or more binary publication in
PUBLISHED status, respecting the given name and status filters.

    >>> cprov_archive.getSourcesForDeletion().count()
    2

This method can optionally receive a source package name filter (SQL
LIKE) to restrict its result.

    >>> cprov_archive.getSourcesForDeletion(name="ice").count()
    1

If only the source publication is DELETED, leaving its binary behind,
it continues to be considered 'available for deletion'.

    >>> removal_candidate = cprov_archive.getPublishedSources(
    ...     name="ice"
    ... ).first()
    >>> removal_candidate.getPublishedBinaries().count()
    1

    >>> login("celso.providelo@canonical.com")
    >>> removal_candidate.requestDeletion(cprov, "go away !")

    >>> cprov_archive.getSourcesForDeletion(name="ice").count()
    1

The status filter can be used to only return sources that can be
deleted matching a given status.

    >>> cprov_archive.getSourcesForDeletion(
    ...     name="ice", status=PackagePublishingStatus.DELETED
    ... ).count()
    1

    >>> cprov_archive.getSourcesForDeletion(
    ...     name="ice", status=PackagePublishingStatus.PUBLISHED
    ... ).count()
    0

The status filter can also be a sequence of status.

    >>> irrelevant_status = (
    ...     PackagePublishingStatus.SUPERSEDED,
    ...     PackagePublishingStatus.DELETED,
    ... )

    >>> cprov_archive.getSourcesForDeletion(
    ...     name="ice", status=irrelevant_status
    ... ).count()
    1

The series filter can be used to return only sources from a certain
series:

    >>> cprov_archive.getSourcesForDeletion(distroseries=warty).count()
    2
    >>> cprov_archive.getSourcesForDeletion(distroseries=hoary).count()
    0

The source publication is only excluded from 'deletion list' when it's
scheduled deletion date is set.

    >>> removeSecurityProxy(removal_candidate).scheduleddeletiondate = UTC_NOW
    >>> cprov_archive.getSourcesForDeletion(name="ice").count()
    0

Flush the database caches to invalidate old caches from the
corresponding publishing Postgres views.

    >>> transaction.commit()


Build Lookup
------------

It also implements a build lookup method, which supports, 'name',
'status' and 'pocket'.

This method can return build records for sources matching the given
'name' as in SQL LIKE:

    >>> cd_lookup = cprov_archive.getBuildRecords(name="cd")
    >>> cd_lookup.count()
    1
    >>> print(cd_lookup[0].source_package_release.name)
    cdrkit

    >>> ice_lookup = cprov_archive.getBuildRecords(name="ice")
    >>> ice_lookup.count()
    1
    >>> print(ice_lookup[0].source_package_release.name)
    iceweasel

    >>> cprov_archive.getBuildRecords(name="foo").count()
    0

Or return build records in a specific status:

    >>> from lp.buildmaster.enums import BuildStatus
    >>> cprov_archive.getBuildRecords(
    ...     build_state=BuildStatus.FULLYBUILT
    ... ).count()
    3

    >>> cprov_archive.getBuildRecords(
    ...     build_state=BuildStatus.FAILEDTOBUILD
    ... ).count()
    1

    >>> cprov_archive.getBuildRecords(
    ...     build_state=BuildStatus.NEEDSBUILD
    ... ).count()
    0

And finally build records target to a given pocket:

    >>> cprov_archive.getBuildRecords(
    ...     pocket=PackagePublishingPocket.RELEASE
    ... ).count()
    4

    >>> cprov_archive.getBuildRecords(
    ...     pocket=PackagePublishingPocket.UPDATES
    ... ).count()
    0

All the attributes can be combined in order to refine the result:

    >>> cprov_archive.getBuildRecords(
    ...     name="ice",
    ...     build_state=BuildStatus.FULLYBUILT,
    ...     pocket=PackagePublishingPocket.RELEASE,
    ... ).count()
    1


Archive dependencies
--------------------

An Archive can depend on one or more other archives, such
relationships affects mainly its builds, which will be querying build
dependencies also in dependent archives, and its client system which
will have to enable apt to look for package dependencies in the
dependent archive as well.

Currently only one level of dependency is supported, i.e., PPA X
depends on PPA Y, if PPA W wants to use packages of PPA X it will have
to depend also on PPA Y, otherwise it won't be able to install all the
required dependencies when building.

    >>> def print_dependencies(archive):
    ...     dependencies = archive.dependencies
    ...     if dependencies.is_empty():
    ...         print("No dependencies recorded.")
    ...         return
    ...     for dep in dependencies:
    ...         print(dep.dependency.displayname)
    ...

Celso's PPA has no dependencies stored in the sampledata.

    >>> print_dependencies(cprov.archive)
    No dependencies recorded.

We will make Celso's PPA to depend on Mark's PPA, specifically on its
RELEASE pocket and 'main' component.

    >>> mark = getUtility(IPersonSet).getByName("mark")

    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> main_component = getUtility(IComponentSet)["main"]

    >>> release_pocket = PackagePublishingPocket.RELEASE

    >>> archive_dependency = cprov.archive.addArchiveDependency(
    ...     mark.archive, release_pocket, main_component
    ... )

The `IArchiveDependency` object simply maps the desired relationship.

    >>> print(archive_dependency.archive.displayname)
    PPA for Celso Providelo

    >>> print(archive_dependency.dependency.displayname)
    PPA for Mark Shuttleworth

The `IArchiveDependency` object itself implement a 'title'
property. For PPA dependencies the title defaults to the PPA displayname.

    >>> print(archive_dependency.title)
    PPA for Mark Shuttleworth

The archive dependency is immediately recorded on Celso's PPA.

    >>> print_dependencies(cprov.archive)
    PPA for Mark Shuttleworth

'getArchiveDependency' returns the corresponding `IArchiveDependency`
for a given 'dependency', otherwise it returns None.

    >>> print(
    ...     cprov.archive.getArchiveDependency(
    ...         mark.archive
    ...     ).dependency.displayname
    ... )
    PPA for Mark Shuttleworth

    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> print(cprov.archive.getArchiveDependency(no_priv.archive))
    None

As mentioned above, the archive dependency engine doesn't follow
cross dependencies. When a PPA depends only on Celso's PPA it might
result in issues while building package if a required package
dependency is published in Mark's PPA.

    >>> print_dependencies(no_priv.archive)
    No dependencies recorded.

    >>> ignored = login_person(no_priv)
    >>> archive_dependency = no_priv.archive.addArchiveDependency(
    ...     cprov.archive, release_pocket, main_component
    ... )

    >>> print_dependencies(no_priv.archive)
    PPA for Celso Providelo

`IArchive.addArchiveDependency` raises an error if the given
'dependency' violates the system overall constraints.

'dependency' is already recorded (duplicated).

    >>> no_priv.archive.addArchiveDependency(
    ...     cprov.archive, release_pocket, main_component
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.ArchiveDependencyError: This dependency is
    already registered.

'dependency' and target archive are the same.

    >>> no_priv.archive.addArchiveDependency(
    ...     no_priv.archive, release_pocket, main_component
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.ArchiveDependencyError: An archive should not
    depend on itself.

A 'dependency' can be added for any type of archive, PPA, PRIMARY, PARTNER or
COPY.

    >>> ubuntu = no_priv.archive.distribution
    >>> primary_dependency = no_priv.archive.addArchiveDependency(
    ...     ubuntu.main_archive,
    ...     PackagePublishingPocket.UPDATES,
    ...     getUtility(IComponentSet)["universe"],
    ... )

Other dependencies than PPAs have an extended 'title', which includes
the target 'pocket' and a human-readable reference to the components
involved.

    >>> print(primary_dependency.title)
    Primary Archive for Ubuntu Linux - UPDATES (main, universe)

They also expose the name of the component directly, for use in the API.

    >>> print(primary_dependency.component_name)
    universe

See further implications of archive dependencies in
doc/archive-dependencies.rst.

Only one dependency per archive can be added.

    >>> no_priv.archive.addArchiveDependency(
    ...     ubuntu.main_archive,
    ...     PackagePublishingPocket.RELEASE,
    ...     getUtility(IComponentSet)["main"],
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.ArchiveDependencyError: This dependency is
    already registered.

Thus archive dependency removal can be performed simply by passing the
dependency target.

    >>> no_priv.archive.removeArchiveDependency(ubuntu.main_archive)

Non-PPA dependencies can have empty 'component', which has a slightly
more concise title.

    >>> primary_component_dep = no_priv.archive.addArchiveDependency(
    ...     ubuntu.main_archive, PackagePublishingPocket.SECURITY
    ... )

    >>> print(primary_component_dep.title)
    Primary Archive for Ubuntu Linux - SECURITY

In this case the component name is None.

    >>> print(primary_component_dep.component_name)
    None

However only PRIMARY archive dependencies support pockets other than
RELEASE or other components than 'main'.

    >>> no_priv.archive.addArchiveDependency(
    ...     mark.archive, PackagePublishingPocket.UPDATES, main_component
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.ArchiveDependencyError: Non-primary archives
    only support the RELEASE pocket.

    >>> no_priv.archive.addArchiveDependency(
    ...     mark.archive,
    ...     release_pocket,
    ...     getUtility(IComponentSet)["universe"],
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.ArchiveDependencyError: Non-primary archives
    only support the 'main' component.

'removeArchiveDependency' allow us to purge a recorded
`ArchiveDependency` corresponding to the given 'dependency', 'pocket'
and 'component'.

    >>> print_dependencies(no_priv.archive)
    PPA for Celso Providelo
    Primary Archive for Ubuntu Linux

    >>> no_priv.archive.removeArchiveDependency(cprov.archive)
    >>> no_priv.archive.removeArchiveDependency(ubuntu.main_archive)

    >>> print_dependencies(no_priv.archive)
    No dependencies recorded.

Attempts to remove a non-existent dependency results in a AssertionError.

    >>> no_priv.archive.removeArchiveDependency(mark.archive)
    Traceback (most recent call last):
    ...
    AssertionError: This dependency does not exist.

Creating a package copy request from an IArchive
------------------------------------------------

The IArchive interface includes a convenience method for creating a
package copy request:

    >>> from lp.testing.factory import (
    ...     remove_security_proxy_and_shout_at_engineer,
    ... )
    >>> requestor = factory.makePerson(name="me-copy")
    >>> copy_target = factory.makeCopyArchiveLocation(
    ...     distribution=ubuntu, name="my-copy-archive", owner=requestor
    ... )
    >>> naked_copy_target = remove_security_proxy_and_shout_at_engineer(
    ...     copy_target
    ... )
    >>> pcr = ubuntu.main_archive.requestPackageCopy(
    ...     naked_copy_target, requestor
    ... )
    >>> print(pcr)
    Package copy request
    source = primary/hoary/-/RELEASE
    target = my-copy-archive/hoary/-/RELEASE
    copy binaries: False
    requester: me-copy
    status: NEW
    ...

The requestPackageCopy method can also take an optional suite name:

    >>> package_copy_request = ubuntu.main_archive.requestPackageCopy(
    ...     naked_copy_target, requestor, suite="hoary-updates"
    ... )
    >>> print(package_copy_request)
    Package copy request
    source = primary/hoary/-/UPDATES
    target = my-copy-archive/hoary/-/RELEASE
    copy binaries: False
    requester: me-copy
    status: NEW
    ...

IArchiveSet Utility
-------------------

This utility provides useful methods to deal with IArchive in other
parts of the system.

    >>> archive_set = getUtility(IArchiveSet)

A new Archive can be created by passing a name and an owner

    >>> name16 = getUtility(IPersonSet).getByName("name16")
    >>> sandbox_archive = archive_set.new(
    ...     purpose=ArchivePurpose.PPA, owner=name16
    ... )

    >>> verifyObject(IArchive, sandbox_archive)
    True

    >>> sandbox_archive.owner == name16
    True

PPAs are created with the name attribute set to 'ppa' by default.

    >>> print(sandbox_archive.name)
    ppa

We can take the opportunity to check if the default 'authorized_size'
corresponds to what we state in our policy, 8192 MiB:

    >>> name16.archive.authorized_size
    8192

An archive is also associated with a distribution.  This can be found on
the distribution property.  The default distribution is "ubuntu":

    >>> print(sandbox_archive.distribution.name)
    ubuntu

An Archive can be retrieved via IPerson.archive property:

    >>> name16.archive == sandbox_archive
    True

IArchiveSet.getByDistroPurpose retrieves an IArchive given a distribution
and an ArchivePurpose:

    >>> ubuntutest = getUtility(IDistributionSet)["ubuntutest"]
    >>> partner_archive = getUtility(IArchiveSet).getByDistroPurpose(
    ...     ubuntutest, ArchivePurpose.PARTNER
    ... )
    >>> print(partner_archive.name)
    partner
    >>> print(partner_archive.is_partner)
    True
    >>> print(partner_archive.is_primary)
    False
    >>> print(partner_archive.is_main)
    True

It explicitly fails when purpose is PPA, since such lookup should be
restricted by archive owner.

    >>> getUtility(IArchiveSet).getByDistroPurpose(ubuntu, ArchivePurpose.PPA)
    Traceback (most recent call last):
    ...
    AssertionError: This method should not be used to lookup PPAs. Use
    'getPPAByDistributionAndOwnerName' instead.

As mentioned in the error message, getPPAByDistributionAndOwnerName()
should be used instead. See below.

Similarly, IArchiveSet.getByDistroAndName() retrieves an IArchive given a
distribution and the archive name.  Returned archives are always distribution
archives; that is PPAs are not considered.

XXX Julian 2008-09-24 We need to add a getByOwnerAndName() to fetch PPAs
at some point, but it's not needed right now.

    >>> partner_archive = getUtility(IArchiveSet).getByDistroAndName(
    ...     ubuntutest, "partner"
    ... )
    >>> print(partner_archive.displayname)
    Partner Archive for Ubuntu Test

Passing an invalid name will cause an empty result set.

    >>> bogus = getUtility(IArchiveSet).getByDistroAndName(
    ...     ubuntutest, "bogus"
    ... )
    >>> print(bogus)
    None

IArchive.archive_url will return a URL for the archive that the builder can
use to retrieve files from it.  Internal paths and urls supplied via the
PunlisherConfig require us to log in as an admin:

    >>> login("admin@canonical.com")
    >>> print(partner_archive.archive_url)
    http://archive.launchpad.test/ubuntutest-partner

    >>> print(sandbox_archive.archive_url)
    http://ppa.launchpad.test/name16/ppa/ubuntu

    >>> print(
    ...     getUtility(IArchiveSet)
    ...     .getByDistroPurpose(ubuntutest, ArchivePurpose.PRIMARY)
    ...     .archive_url
    ... )
    http://archive.launchpad.test/ubuntutest

COPY archives use a URL format of <distro-name>-<archive-name>:

    >>> print(naked_copy_target.archive.is_copy)
    True
    >>> print(naked_copy_target.archive.archive_url)
    http://rebuild-test.internal/ubuntu-my-copy-archive/ubuntu

If the archive is private, the url may be different as private PPAs
are published to a secure location.

    >>> login("celso.providelo@canonical.com")
    >>> print(cprov_archive.archive_url)
    http://ppa.launchpad.test/cprov/ppa/ubuntu

    >>> print(cprov_private_ppa.archive_url)
    http://private-ppa.launchpad.test/cprov/myprivateppa/ubuntu

IArchive.allowUpdatesToReleasePocket returns whether the archive is allowed
to publish to the RELEASE pocket no matter what state the distroseries is in.

    >>> partner_archive.allowUpdatesToReleasePocket()
    True

    >>> cprov_archive.allowUpdatesToReleasePocket()
    True

    >>> getUtility(IArchiveSet).getByDistroPurpose(
    ...     ubuntutest, ArchivePurpose.PRIMARY
    ... ).allowUpdatesToReleasePocket()
    False

getPPAByDistributionAndOwnerName method allow PPA lookups based on a
distribution, person name and the PPA name. This method is used in
`PackageLocation` to provide a homogeneous way to refer to a Location
(archive, distribution, distroseries, pocket).

    >>> cprov_archive == archive_set.getPPAByDistributionAndOwnerName(
    ...     ubuntu, "cprov", "ppa"
    ... )
    True

    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> mark.archive == archive_set.getPPAByDistributionAndOwnerName(
    ...     ubuntu, "mark", "ppa"
    ... )
    True

Iteration over the own utility is performed against all archives,
including PPA, PRIMARY, PARTNER and COPY:

    >>> from lp.testing import celebrity_logged_in
    >>> with celebrity_logged_in("admin"):
    ...     archive_purposes = [
    ...         archive.purpose.name for archive in archive_set
    ...     ]
    ...
    >>> len(archive_purposes)
    17

    >>> print(sorted(set(archive_purposes)))
    ['COPY', 'PARTNER', 'PPA', 'PRIMARY']

'getPPAsForUser' returns all the PPAs a given user participates in. It
uses `TeamParticipation` relationships to calculate all the PPAs the
user is allowed to upload or copy packages to.

Celso only participates in his own PPAs.

    >>> for ppa in archive_set.getPPAsForUser(cprov):
    ...     print(ppa.displayname)
    ...
    PPA for Celso Providelo
    PPA named myprivateppa for Celso Providelo

However 'cprov' is also a member of 'launchpad-buildd-admins' team,
which doesn't have a PPA yet.

    >>> lp_buildd_team = getUtility(IPersonSet).getByName(
    ...     "launchpad-buildd-admins"
    ... )

    >>> cprov.inTeam(lp_buildd_team)
    True

    >>> lp_buildd_team.archive is None
    True

When the 'launchpad-buildd-admins' PPA gets created, 'getPPAsForUser'
immediately recognises 'cprov' rights on it.

    >>> buildd_archive = archive_set.new(
    ...     owner=lp_buildd_team,
    ...     purpose=ArchivePurpose.PPA,
    ...     distribution=ubuntu,
    ...     description="Yo !",
    ... )

    >>> for ppa in archive_set.getPPAsForUser(cprov):
    ...     print(ppa.displayname)
    ...
    PPA for Celso Providelo
    PPA for Launchpad Buildd Admins
    PPA named myprivateppa for Celso Providelo

The same happens for specific upload rights granted on 3rd-party
PPAs. When 'No Privileges' gets upload rights to Celso's PPA,
it gets listed by `getPPAsForUser`.

    >>> for ppa in archive_set.getPPAsForUser(no_priv):
    ...     print(ppa.displayname)
    ...
    PPA for No Privileges Person

    >>> cprov_archive.newComponentUploader(no_priv, "main")
    <lp.soyuz.model.archivepermission.ArchivePermission ...>

    >>> for ppa in archive_set.getPPAsForUser(no_priv):
    ...     print(ppa.displayname)
    ...
    PPA for Celso Providelo
    PPA for No Privileges Person

This also works via indirect team memberships.  Let's make a dummy team
and user and give the team access to cprov's PPA:

    >>> uploader_team = factory.makeTeam(owner=cprov, name="uploader-team")
    >>> indirect_uploader = factory.makePerson(name="indirect-uploader")
    >>> cprov_archive.newComponentUploader(uploader_team, "main")
    <lp.soyuz.model.archivepermission.ArchivePermission ...>

'indirect_uploader' currently can't upload to cprov's PPA:

    >>> for ppa in archive_set.getPPAsForUser(indirect_uploader):
    ...     print(ppa.displayname)
    ...

But if we make them part of the uploader_team they'll gain access:

    >>> ignored = uploader_team.addMember(
    ...     indirect_uploader, indirect_uploader
    ... )
    >>> for ppa in archive_set.getPPAsForUser(indirect_uploader):
    ...     print(ppa.displayname)
    ...
    PPA for Celso Providelo

When there is no active PPA for the team a user participates the
method returns an empty SelectResults.

    >>> jblack = getUtility(IPersonSet).getByName("jblack")

    >>> jblack_ppas = archive_set.getPPAsForUser(jblack)

    >>> jblack_ppas.count()
    0

'getPPADistributionsForUser' returns the distinct distributions for all the
PPAs that a given user participates in.

    >>> for distribution in archive_set.getPPADistributionsForUser(cprov):
    ...     print(distribution.display_name)
    ...
    Ubuntu
    >>> for distribution in archive_set.getPPADistributionsForUser(no_priv):
    ...     print(distribution.display_name)
    ...
    Ubuntu
    >>> for distribution in archive_set.getPPADistributionsForUser(
    ...     indirect_uploader
    ... ):
    ...     print(distribution.display_name)
    Ubuntu
    >>> for distribution in archive_set.getPPADistributionsForUser(jblack):
    ...     print(distribution.display_name)
    ...

The method getPrivatePPAs() will return a result set of all PPAs that are
private.

    >>> p3as = archive_set.getPrivatePPAs()
    >>> for p3a in p3as:
    ...     print(p3a.displayname)
    ...
    PPA named myprivateppa for Celso Providelo

'getLatestPPASourcePublicationsForDistribution' returns up to 5
lastest source publications available for a given distribution ordered
by descending 'datecreated'.

    >>> latest_uploads = (
    ...     archive_set.getLatestPPASourcePublicationsForDistribution(ubuntu)
    ... )
    >>> latest_uploads.count()
    4

It doesn't filter by status, so pending (copied), deleted and
superseded publications continue to be presented.

    >>> def print_latest_uploads():
    ...     latest_uploads = (
    ...         archive_set.getLatestPPASourcePublicationsForDistribution(
    ...             ubuntu
    ...         )
    ...     )
    ...     for pub in latest_uploads:
    ...         print(
    ...             pub.displayname, pub.status.name, pub.archive.owner.name
    ...         )
    ...

    >>> print_latest_uploads()
    cdrkit 1.0 in breezy-autotest SUPERSEDED cprov
    iceweasel 1.0 in breezy-autotest PUBLISHED mark
    pmount 0.1-1 in warty PUBLISHED cprov
    iceweasel 1.0 in warty DELETED cprov

When we copy a source from Celso's PPA to Mark's PPA, it will be
presented as a new record in the results.

    >>> cprov_iceweasel = latest_uploads[1]
    >>> copy = cprov_iceweasel.copyTo(
    ...     ubuntu["hoary"], PackagePublishingPocket.RELEASE, mark.archive
    ... )

    >>> print_latest_uploads()
    iceweasel 1.0 in hoary PENDING mark
    cdrkit 1.0 in breezy-autotest SUPERSEDED cprov
    iceweasel 1.0 in breezy-autotest PUBLISHED mark
    pmount 0.1-1 in warty PUBLISHED cprov
    iceweasel 1.0 in warty DELETED cprov

When we do another copy the result will be limited, so the previous
last publication (Celso's deleted iceweasel) will be excluded.

    >>> cprov_cdrkit = latest_uploads[1]
    >>> copy = cprov_cdrkit.copyTo(
    ...     ubuntu["hoary"], PackagePublishingPocket.RELEASE, mark.archive
    ... )

    >>> print_latest_uploads()
    cdrkit 1.0 in hoary PENDING mark
    iceweasel 1.0 in hoary PENDING mark
    cdrkit 1.0 in breezy-autotest SUPERSEDED cprov
    iceweasel 1.0 in breezy-autotest PUBLISHED mark
    pmount 0.1-1 in warty PUBLISHED cprov

Private source publications are excluded from this list, the fact that
they exist should never leak. If we copy the package to Celso's private
PPA the list is not updated.  The same happens for uploaded sources, since
they are essentially another source publication in this context.

    >>> from lp.testing import person_logged_in
    >>> with person_logged_in(cprov):
    ...     copy = cprov_cdrkit.copyTo(
    ...         ubuntu["hoary"],
    ...         PackagePublishingPocket.RELEASE,
    ...         cprov_private_ppa,
    ...     )
    ...

    >>> print_latest_uploads()
    cdrkit 1.0 in hoary PENDING mark
    iceweasel 1.0 in hoary PENDING mark
    cdrkit 1.0 in breezy-autotest SUPERSEDED cprov
    iceweasel 1.0 in breezy-autotest PUBLISHED mark
    pmount 0.1-1 in warty PUBLISHED cprov

Publications in disabled archives are also excluded, since normal users
can't see them.

    >>> login("admin@canonical.com")
    >>> cprov_cdrkit.archive.disable()
    >>> print_latest_uploads()
    cdrkit 1.0 in hoary PENDING mark
    iceweasel 1.0 in hoary PENDING mark
    iceweasel 1.0 in breezy-autotest PUBLISHED mark
    >>> cprov_cdrkit.archive.enable()

'getMostActivePPAsForDistribution' returns a list of dictionaries
containing up to 5 PPAs with the highest number of publications in the
last 7 days. Each dictionary contains the following keys:

 * 'archive': The `IArchive` object;
 * 'uploads': the number of sources uploaded in the last 7 days.

The list is ordered by descending number of uploads and then database
record ID.

    >>> most_active_ppas = archive_set.getMostActivePPAsForDistribution(
    ...     ubuntu
    ... )
    >>> len(most_active_ppas)
    1

As expected only Mark's PPA had activity, all the sampledata records
are old.

    >>> def print_most_active_ppas():
    ...     most_active_ppas = archive_set.getMostActivePPAsForDistribution(
    ...         ubuntu
    ...     )
    ...     for most_active in most_active_ppas:
    ...         print(
    ...             most_active["archive"].displayname, most_active["uploads"]
    ...         )
    ...

    >>> print_most_active_ppas()
    PPA for Mark Shuttleworth 2

We will create a new PPA and some activity.

    >>> name12 = getUtility(IPersonSet).getByName("name12")
    >>> name12_archive = archive_set.new(
    ...     owner=name12, distribution=None, purpose=ArchivePurpose.PPA
    ... )

    >>> a_pub = cprov_archive.getPublishedSources().first()
    >>> def create_activity(where, how_many):
    ...     for i in range(how_many):
    ...         a_pub.copyTo(
    ...             ubuntu["hoary"], PackagePublishingPocket.RELEASE, where
    ...         )
    ...

    >>> create_activity(cprov_private_ppa, 20)
    >>> create_activity(sandbox_archive, 10)
    >>> create_activity(name12.archive, 4)
    >>> create_activity(no_priv.archive, 4)
    >>> create_activity(lp_buildd_team.archive, 8)
    >>> import transaction
    >>> transaction.commit()

Celso's private PPA is not listed despite having the highest number of
uploads.

    >>> print_most_active_ppas()
    PPA for Foo Bar 10
    PPA for Launchpad Buildd Admins 8
    PPA for No Privileges Person 4
    PPA for Sample Person 4
    PPA for Mark Shuttleworth 2

If we give lots of activity to Celso's public PPA the previous
last item (Mark's PPA) will now be excluded as the results are
limited to 5 items.

    >>> create_activity(cprov_archive, 20)
    >>> transaction.commit()
    >>> print_most_active_ppas()
    PPA for Celso Providelo 20
    PPA for Foo Bar 10
    PPA for Launchpad Buildd Admins 8
    PPA for No Privileges Person 4
    PPA for Sample Person 4


A general way to get specific archives for a distribution
---------------------------------------------------------

IArchiveSet also includes the helper method `getArchivesForDistribution`
which can be used to get archives of a specific purpose(s) for a distribution
(note: the sample data currently contains one copy archive for ubuntu, and
one has been created above):

First create a function to print the names of a set of archives and
its relevant attributes.

    >>> def print_archive_names(archives):
    ...     print("Name Owner Private Enabled")
    ...     for a in archives:
    ...         print(a.name, a.owner.name, a.private, a.enabled)
    ...

Anonymous lookups return only public and enabled archives for the
given purpose:

    >>> archive_set = getUtility(IArchiveSet)
    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu, purposes=ArchivePurpose.COPY
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    my-copy-archive  me-copy       False    True

The method `getArchivesForDistribution` can also be used with multiple
purposes. First we'll check how many partner archives are in the DB:

    >>> partner_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu, purposes=ArchivePurpose.PARTNER
    ... )
    >>> print_archive_names(partner_archives)
    Name             Owner         Private  Enabled
    partner          ubuntu-team   False    True

And then use `getArchivesForDistribution` to get all copy and partner
archives:

    >>> copy_n_partner_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu, purposes=[ArchivePurpose.COPY, ArchivePurpose.PARTNER]
    ... )
    >>> print_archive_names(copy_n_partner_archives)
    Name             Owner         Private  Enabled
    my-copy-archive  me-copy       False    True
    partner          ubuntu-team   False    True

First we create four copy archives for ubuntu:

    >>> copy_owner1 = factory.makePerson(name="copy-owner1")
    >>> copy_owner2 = factory.makePerson(name="copy-owner2")
    >>> ultimate_copy = factory.makeCopyArchiveLocation(
    ...     distribution=ubuntu, name="ultimate-copy", owner=copy_owner1
    ... )
    >>> fine_copy = factory.makeCopyArchiveLocation(
    ...     distribution=ubuntu, name="fine-copy", owner=copy_owner2
    ... )
    >>> true_copy = factory.makeCopyArchiveLocation(
    ...     distribution=ubuntu,
    ...     name="true-copy",
    ...     owner=copy_owner2,
    ...     enabled=False,
    ... )

One of the new copy archives will be owned by a team:

    >>> from lp.registry.interfaces.person import TeamMembershipPolicy
    >>> team = getUtility(IPersonSet).newTeam(
    ...     mark, "t1", "t1", membership_policy=TeamMembershipPolicy.MODERATED
    ... )
    >>> copy = factory.makeCopyArchiveLocation(
    ...     distribution=ubuntu, name="team-archive", owner=team
    ... )

Now the `getArchivesForDistribution` finds the relevant COPY archives:

    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu, purposes=[ArchivePurpose.COPY]
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    fine-copy        copy-owner2   False    True
    my-copy-archive  me-copy       False    True
    team-archive     t1            False    True
    ultimate-copy    copy-owner1   False    True

The `getArchivesForDistribution` method can also be used to get an
archive using an archive name:

    >>> primary_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu, name="primary"
    ... )
    >>> print_archive_names(primary_archives)
    Name             Owner         Private  Enabled
    primary          ubuntu-team   False    True

After making two of the archives private, the getArchivesForDistribution()
method will by default only return public archives:

    >>> login("foo.bar@canonical.com")
    >>> my_copy_archive = archive_set.getArchivesForDistribution(
    ...     ubuntu, name="my-copy-archive"
    ... )[0]
    >>> my_copy_archive.private = True
    >>> team_archive = archive_set.getArchivesForDistribution(
    ...     ubuntu, name="team-archive"
    ... )[0]
    >>> team_archive.private = True

    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu, purposes=[ArchivePurpose.COPY]
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    fine-copy        copy-owner2   False    True
    ultimate-copy    copy-owner1   False    True

Similarly, a user who has no privs for the private archive will not see
the private archives:

    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu, purposes=[ArchivePurpose.COPY], user=cprov
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    fine-copy        copy-owner2   False    True
    ultimate-copy    copy-owner1   False    True

The owner of the archive will also see their private archive in the results:

    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu, purposes=[ArchivePurpose.COPY], user=my_copy_archive.owner
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    fine-copy        copy-owner2   False    True
    my-copy-archive  me-copy       True     True
    ultimate-copy    copy-owner1   False    True

An admin will see all the private and disabled archives in the results
if requested:

    >>> foobar = getUtility(IPersonSet).getByName("name16")
    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu,
    ...     purposes=[ArchivePurpose.COPY],
    ...     user=foobar,
    ...     exclude_disabled=False,
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    fine-copy        copy-owner2   False    True
    my-copy-archive  me-copy       True     True
    team-archive     t1            True     True
    there-we-go      juergen       False    False
    true-copy        copy-owner2   False    False
    ultimate-copy    copy-owner1   False    True

Passing `check_permissions=False` skips the user permission checks:

    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu, purposes=[ArchivePurpose.COPY], check_permissions=False
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    fine-copy        copy-owner2   False    True
    my-copy-archive  me-copy       True     True
    team-archive     t1            True     True
    ultimate-copy    copy-owner1   False    True

If exclude_disabled is set to True no disabled archives will be
included:

    >>> foobar = getUtility(IPersonSet).getByName("name16")
    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu,
    ...     purposes=[ArchivePurpose.COPY],
    ...     user=foobar,
    ...     exclude_disabled=True,
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    fine-copy        copy-owner2   False    True
    my-copy-archive  me-copy       True     True
    team-archive     t1            True     True
    ultimate-copy    copy-owner1   False    True

And if the archive is owned by a team, then anyone in the team will also
be able to view the private team archive:

    >>> ignore = team.addMember(cprov, team.teamowner)
    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu, purposes=[ArchivePurpose.COPY], user=cprov
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    fine-copy        copy-owner2   False    True
    team-archive     t1            True     True
    ultimate-copy    copy-owner1   False    True

A separate argument allows forcing the inclusion of all disabled archives
the user has access to, so it doesn't include the archive
of juergen that is disabled.

    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu,
    ...     purposes=[ArchivePurpose.COPY],
    ...     user=copy_owner2,
    ...     exclude_disabled=False,
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    fine-copy        copy-owner2   False    True
    true-copy        copy-owner2   False    False
    ultimate-copy    copy-owner1   False    True

A separate argument allows excluding archives that have never had any
publications, allowing jobs to skip over trivial cases.

    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu,
    ...     purposes=[ArchivePurpose.COPY],
    ...     user=copy_owner2,
    ...     exclude_pristine=True,
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled

    >>> _ = factory.makeSourcePackagePublishingHistory(
    ...     archive=removeSecurityProxy(fine_copy).archive
    ... )
    >>> _ = factory.makeSourcePackagePublishingHistory(
    ...     archive=removeSecurityProxy(ultimate_copy).archive
    ... )
    >>> ubuntu_copy_archives = archive_set.getArchivesForDistribution(
    ...     ubuntu,
    ...     purposes=[ArchivePurpose.COPY],
    ...     user=copy_owner2,
    ...     exclude_pristine=True,
    ... )
    >>> print_archive_names(ubuntu_copy_archives)
    Name             Owner         Private  Enabled
    fine-copy        copy-owner2   False    True
    ultimate-copy    copy-owner1   False    True


Archive Permission Checking
---------------------------

IArchive has two public methods, checkArchivePermission() and
canAdministerQueue() that check a user's permission to upload and/or
administer a distroseries upload queue respectively.  See
archivepermission.rst for more details.

    >>> ubuntu_team = getUtility(IPersonSet).getByName("ubuntu-team")
    >>> carlos = getUtility(IPersonSet).getByName("carlos")

    >>> ubuntu.main_archive.checkArchivePermission(carlos, main_component)
    False

    >>> ubuntu.main_archive.canAdministerQueue(carlos, main_component)
    False

    >>> ubuntu.main_archive.checkArchivePermission(
    ...     ubuntu_team, main_component
    ... )
    True

    >>> ubuntu.main_archive.canAdministerQueue(ubuntu_team, main_component)
    True

checkArchivePermission() can also check someone's permission to upload
a specific source package.  Carlos, who does not have permission to
upload to any Ubuntu components, has permission to upload
"mozilla-firefox".

    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet,
    ... )
    >>> mozilla = getUtility(ISourcePackageNameSet).queryByName(
    ...     "mozilla-firefox"
    ... )
    >>> ubuntu.main_archive.checkArchivePermission(carlos, mozilla)
    True

Cprov does not have permission, however.

    >>> ubuntu.main_archive.checkArchivePermission(cprov, mozilla)
    False

checkArchivePermission() also works in the same way for PPAs.  By
default, it allows anyone in the PPA owning team to upload.

    >>> cprov_archive.checkArchivePermission(cprov)
    True

    >>> cprov_archive.checkArchivePermission(carlos)
    False

We can also create an ArchivePermission entry for carlos to be able to upload
to someone else's PPA, even though he is not the owner.

    >>> joes_ppa = factory.makeArchive()
    >>> discard = joes_ppa.newComponentUploader(carlos, "main")

Carlos can now upload to Joe's PPA:

    >>> joes_ppa.checkArchivePermission(carlos)
    True

Note that when creating a new permission, trying to specify a component other
than 'main' results in an exception being raised, because components are not
really applicable for PPAs.  'main' is used because *something* needs to be
specified to satisfy database constraints, and it makes the most sense since
that's the component that PPA packages are published in.  In the future,
packagesets will replace components entirely as the ACL mechanism, so this
anacronism can be removed.

    >>> joes_ppa.newComponentUploader(carlos, "universe")
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.InvalidComponent: Component for PPAs should be
    'main'

You'll get the same error if you use a component object that's not main.

    >>> universe = getUtility(IComponentSet)["universe"]
    >>> joes_ppa.newComponentUploader(carlos, universe)
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.InvalidComponent: Component for PPAs should be
    'main'

As important as the right to upload packages to Joe's PPA, Carlos
also got the corresponding permissions on it.

    >>> from lp.services.webapp.authorization import check_permission
    >>> login("carlos@canonical.com")

    >>> check_permission("launchpad.View", joes_ppa)
    True

    >>> check_permission("launchpad.Append", joes_ppa)
    True

So even if Joe's PPA suddenly becomes private, Carlos rights will be
preserved.

    >>> login("foo.bar@canonical.com")
    >>> joes_ppa.private = True

    >>> login("carlos@canonical.com")

    >>> check_permission("launchpad.View", joes_ppa)
    True

    >>> check_permission("launchpad.Append", joes_ppa)
    True

On the other hand, if Joe's PPA is disabled, only the view
permissions are kept. No one has permission to upload or copy sources
to it.

    >>> login("foo.bar@canonical.com")
    >>> joes_ppa.disable()

    >>> login("carlos@canonical.com")
    >>> check_permission("launchpad.Append", joes_ppa)
    False

    >>> ignored = login_person(joes_ppa.owner)
    >>> check_permission("launchpad.Append", joes_ppa)
    False

Similarly to private PPAs, disabled public PPAs can only be viewed by
owners or uploaders.

    >>> login("foo.bar@canonical.com")
    >>> discard = cprov_archive.newComponentUploader(carlos, "main")
    >>> cprov_archive.disable()

    >>> login(ANONYMOUS)
    >>> check_permission("launchpad.View", cprov_archive)
    False

    >>> login("david.allouche@canonical.com")
    >>> check_permission("launchpad.View", cprov_archive)
    False

    >>> login("carlos@canonical.com")
    >>> check_permission("launchpad.View", cprov_archive)
    True

    >>> login("celso.providelo@canonical.com")
    >>> check_permission("launchpad.View", cprov_archive)
    True

Re-enable Celso's PPA.

    >>> login("foo.bar@canonical.com")
    >>> cprov_archive.enable()

Rebuild archives
----------------

For further information about how ArchiveRebuild works see
archive-rebuilds.rst. Here we will just document why the creation and
lookup of COPY archives are a little different than the rest of the
archives.

When creating archives with COPY purpose, the 'name' field is
mandatory, since it's user defined. There is no default name for
them.

Creating new COPY archive without passing a name results in an
AssertionError.

    >>> login("foo.bar@canonical.com")
    >>> rebuild_archive = getUtility(IArchiveSet).new(
    ...     owner=cprov, purpose=ArchivePurpose.COPY, distribution=ubuntutest
    ... )
    Traceback (most recent call last):
    ...
    AssertionError: 'COPY' purpose has no default name.

Passing the 'name', in addition to the owner, purpose and
distribution, does the trick.

    >>> rebuild_archive = getUtility(IArchiveSet).new(
    ...     owner=cprov,
    ...     purpose=ArchivePurpose.COPY,
    ...     distribution=ubuntutest,
    ...     name="test-rebuild-one",
    ... )

As mentioned before, the rebuild archive name should be traversable
otherwise an error is raised.

    >>> getUtility(IArchiveSet).new(
    ...     owner=cprov,
    ...     purpose=ArchivePurpose.COPY,
    ...     distribution=ubuntutest,
    ...     name="Very@Wrong!Name",
    ... )
    Traceback (most recent call last):
    ...
    AssertionError: Invalid name given to unproxied object.

The name is used as provided, so callsites should validate it when
necessary.

    >>> print(rebuild_archive.name)
    test-rebuild-one

Another difference is the lookup, we can use getByDistroPurpose(),
however we have to pass 'name', otherwise a error is raised.

    >>> getUtility(IArchiveSet).getByDistroPurpose(
    ...     ubuntutest, ArchivePurpose.COPY
    ... )
    Traceback (most recent call last):
    ...
    AssertionError: 'COPY' purpose has no default name.

Passing the name it behaves exactly it does for primary archive
purposes (PRIMARY and PARTNER). When no matching archive is found,
None is returned.

    >>> candidate = getUtility(IArchiveSet).getByDistroPurpose(
    ...     ubuntutest, ArchivePurpose.COPY, name="does-not-exist"
    ... )
    >>> print(candidate)
    None

If there is a matching archive it is returned.

    >>> candidate = getUtility(IArchiveSet).getByDistroPurpose(
    ...     ubuntutest, ArchivePurpose.COPY, name="test-rebuild-one"
    ... )
    >>> print(candidate.name)
    test-rebuild-one


Synchronising sources from other archives
-----------------------------------------

IArchive.syncSources is a convenience wrapper around the copying code
in lp.soyuz.scripts.packagecopier.  It allows the caller to
provide a list of sources that can be copied to the context archive.

First we use the SoyuzTestPublisher to make some test publications in
hoary:

    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> test_publisher = SoyuzTestPublisher()
    >>> test_publisher.addFakeChroots(hoary)
    >>> unused = test_publisher.setUpDefaultDistroSeries(hoary)
    >>> discard = test_publisher.getPubSource(
    ...     sourcename="package1",
    ...     version="1.0",
    ...     archive=cprov.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> discard = test_publisher.getPubSource(
    ...     sourcename="package1",
    ...     version="1.1",
    ...     archive=cprov.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> discard = test_publisher.getPubSource(
    ...     sourcename="package2",
    ...     version="1.0",
    ...     archive=cprov.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> discard = test_publisher.getPubSource(
    ...     sourcename="pack",
    ...     version="1.0",
    ...     archive=cprov.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )

Now we have package1 1.0 and 1.1, and package2 1.0 in cprov's PPA.  We
can ask syncSources to synchronise these packages into mark's PPA in the
release pocket, but to do so we must have edit permissions on the archive.

    >>> sources = ["package1", "package2"]
    >>> mark.archive.syncSources(
    ...     sources, cprov.archive, "release", person=None
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Let's log in as mark and it will work:

    >>> login("mark@example.com")

    >>> mark.archive.syncSources(
    ...     sources, cprov.archive, "release", person=mark
    ... )

    >>> mark_one = mark.archive.getPublishedSources(name="package1").one()
    >>> print(mark_one.sourcepackagerelease.version)
    1.1
    >>> mark_two = mark.archive.getPublishedSources(name="package2").one()
    >>> print(mark_two.sourcepackagerelease.version)
    1.0

Notice that the latest version of package_one was copied, ignoring the
older one.

Repeating this source copy gives an error:

    >>> mark.archive.syncSources(
    ...     sources, cprov.archive, "release", person=mark
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.CannotCopy: package1 1.1 in hoary (same
    version already building in the destination archive for Hoary) package2
    1.0 in hoary (same version already building in the destination archive for
    Hoary)

Repeating this copy with binaries also gives an error:

    >>> mark.archive.syncSources(
    ...     sources,
    ...     cprov.archive,
    ...     "release",
    ...     include_binaries=True,
    ...     person=mark,
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.CannotCopy: package1 1.1 in hoary (source has
    no binaries to be copied) package2 1.0 in hoary (source has no binaries to
    be copied)

Specifying non-existent source names, pocket names or distroseries names
all result in a NotFound exception:

    >>> mark.archive.syncSources(
    ...     ["bogus"], cprov.archive, "release", person=mark
    ... )
    Traceback (most recent call last):
    ...
    lp.registry.errors.NoSuchSourcePackageName: No such source package:
    'bogus'.

    >>> mark.archive.syncSources(
    ...     sources, cprov.archive, "badpocket", person=mark
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.PocketNotFound: No such pocket: 'BADPOCKET'.

    >>> mark.archive.syncSources(
    ...     sources,
    ...     cprov.archive,
    ...     "release",
    ...     to_series="badseries",
    ...     person=mark,
    ... )
    Traceback (most recent call last):
    ...
    lp.registry.errors.NoSuchDistroSeries: No such distribution series:
    'badseries'.

If a package exists but not in the source archive, we get an error:

    >>> mark.archive.syncSources(["pack"], mark.archive, "release")
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.CannotCopy: None of the supplied package names
    are published in PPA for Mark Shuttleworth.

If a package exists in multiple distroseries, we can use the `from_series`
parameter to select the distroseries to synchronise from:

    >>> test_publisher.addFakeChroots(breezy_autotest)
    >>> discard = test_publisher.getPubSource(
    ...     sourcename="package-multiseries",
    ...     version="1.0",
    ...     archive=cprov.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> discard = test_publisher.getPubSource(
    ...     sourcename="package-multiseries",
    ...     version="1.1",
    ...     distroseries=breezy_autotest,
    ...     archive=cprov.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> mark.archive.syncSources(
    ...     ["package-multiseries"],
    ...     cprov.archive,
    ...     "release",
    ...     from_series="hoary",
    ...     person=mark,
    ... )
    >>> mark_multiseries = mark.archive.getPublishedSources(
    ...     name="package-multiseries"
    ... ).one()
    >>> print(mark_multiseries.sourcepackagerelease.version)
    1.0

We can also specify a single source to be copied with the `syncSource`
call.  This allows a version to be specified so older versions can be
pulled.

Set up v1.0 and 1.1 of "package3":

    >>> discard = test_publisher.getPubSource(
    ...     sourcename="package3", version="1.0", archive=cprov.archive
    ... )
    >>> discard = test_publisher.getPubSource(
    ...     sourcename="package3", version="1.1", archive=cprov.archive
    ... )
    >>> discard = test_publisher.getPubSource(
    ...     sourcename="package3", version="1.2", archive=cprov.archive
    ... )

The underlying package discovery has the ability to do substring matches
on the supplied package names.  However, this feature is not being used
as it's potentially dangerous, since through the API there is no "are
you sure!" type transaction.

When copying a single package, if we supply a package name of "pack" it will
only match one of the test packages we created above rather than all of them.

As with syncSources() you need to have edit permission on the archive.

    >>> login(ANONYMOUS)
    >>> mark.archive.syncSource(
    ...     "pack", "1.0", cprov.archive, "release", person=None
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Login as mark to continue.

    >>> login("mark@example.com")
    >>> mark.archive.syncSource(
    ...     "pack", "1.0", cprov.archive, "release", person=mark
    ... )
    >>> pack = mark.archive.getPublishedSources(
    ...     name="pack", exact_match=True
    ... ).one()
    >>> print(pack.sourcepackagerelease.version)
    1.0

If the supplied package exists but not in the source archive, we get an error:

    >>> mark.archive.syncSource("package3", "1.0", mark.archive, "release")
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.CannotCopy: package3 is not published in PPA
    for Mark Shuttleworth.

Copy package3 1.0 explicitly:

    >>> mark.archive.syncSource(
    ...     "package3", "1.0", cprov.archive, "release", person=mark
    ... )
    >>> mark_three = mark.archive.getPublishedSources(name="package3").one()
    >>> print(mark_three.sourcepackagerelease.version)
    1.0

It's also possible to copy the source and its binaries at the same time,
by specifying the "include_binaries" boolean.

'built-source' is a source package with 2 binaries in Celso's PPA:

    >>> built_source = test_publisher.getPubSource(
    ...     sourcename="built-source", version="1.0", archive=cprov.archive
    ... )
    >>> binaries = test_publisher.getPubBinaries(
    ...     pub_source=built_source, binaryname="from-built-source"
    ... )
    >>> len(binaries)
    2

It s not present in Mark's PPA.

    >>> mark.archive.getPublishedSources(name="built-source").count()
    0

'built-source' and its binaries can be copied from Celso's to Mark's
PPA like this:

    >>> mark.archive.syncSource(
    ...     "built-source",
    ...     "1.0",
    ...     cprov.archive,
    ...     "release",
    ...     include_binaries=True,
    ...     person=mark,
    ... )

Now, Mark's PPA has 'built-source' source and it's 2 binaries.

    >>> copy = mark.archive.getPublishedSources(name="built-source").one()
    >>> copy.getPublishedBinaries().count()
    2

If copying packages into a PPA, you can only copy into the "release" pocket,
or a CannotCopy exception is thrown.

    >>> mark.archive.syncSource(
    ...     "package3", "1.2", cprov.archive, "updates", person=mark
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.CannotCopy: PPA uploads must be for the
    RELEASE pocket.

syncSource() will always use only the latest publication of the
specific source, ignoring the previous ones. Multiple publications can
be resulted from copies and/or overrides of the copy candidates in the
source archive.

    # Create a copy candidate (override_1.0) in ubuntu primary archive
    # and override its section. Resulting in 2 publications in the
    # source archive.
    >>> from lp.soyuz.interfaces.section import ISectionSet
    >>> source_old = test_publisher.getPubSource(
    ...     sourcename="overridden", version="1.0"
    ... )
    >>> python_section = getUtility(ISectionSet).ensure("python")
    >>> copy_candidate = source_old.changeOverride(new_section=python_section)

    >>> source_archive = copy_candidate.archive
    >>> source_archive.getPublishedSources(name="overridden").count()
    2

    >>> print(copy_candidate.section.name)
    python

When syncing 'overridden_1.0' to Mark's PPA, the latest publication,
the one published in 'python' section, will be used.

    >>> mark.archive.syncSource(
    ...     source_name="overridden",
    ...     version="1.0",
    ...     from_archive=source_archive,
    ...     to_pocket="release",
    ...     person=mark,
    ... )

    >>> copy = mark.archive.getPublishedSources(name="overridden").one()
    >>> print(copy.section.name)
    python
