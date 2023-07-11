Distribution Soyuz
==================

Distributions are built by the Soyuz build system which creates many
objects for the distribution.


    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> from lp.soyuz.enums import PackagePublishingStatus

    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> debian = getUtility(IDistributionSet).getByName("debian")


Handling Personal Package Archives
----------------------------------

`IDistribution` provides a series of methods to lookup PPAs:

 * getAllPPAs
 * searchPPAs
 * getPendingAcceptancePPAs
 * getPendingPublicationPPAs

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> mark = getUtility(IPersonSet).getByName("mark")


Iteration over all PPAs
~~~~~~~~~~~~~~~~~~~~~~~

getAllPPAs method provides all returns, as the suggests, all PPAs for
the distribution in question:

    >>> for archive in ubuntu.getAllPPAs():
    ...     print(archive.owner.name)
    ...
    cprov
    mark
    no-priv

    >>> for archive in debian.getAllPPAs():
    ...     print(archive.owner.name)
    ...


Searching PPAs
~~~~~~~~~~~~~~

Via searchPPAs, the callsites are able to look for PPA given a string
matching Person.fti or PPA Archive.fti (description content) and also
restrict the result to active/inactive (whether the PPA contains or not
valid publications).

searchPPAs also considers the packages caches available for PPAs, for
further information see doc/package-cache.rst.

There is only one 'active' PPA:

    >>> cprov.archive.getPublishedSources().count()
    3

    >>> mark.archive.getPublishedSources().count()
    1

    >>> no_priv.archive.getPublishedSources().count()
    0

    >>> result = ubuntu.searchPPAs()
    >>> for archive in result:
    ...     print(archive.owner.name)
    ...
    cprov
    mark

PPAs can be reached passing a filter matching (via fti) its description
and its  'contents description' (see package-cache.rst).

    >>> for owner in [cprov, mark, no_priv]:
    ...     print("%s: %s" % (owner.name, owner.archive.description))
    ...
    cprov: packages to help my friends.
    mark: packages to help the humanity (you know, ubuntu)
    no-priv: I am not allowed to say, I have no privs.

    >>> result = ubuntu.searchPPAs(text="friend")
    >>> for archive in result:
    ...     print(archive.owner.name)
    ...
    cprov

    >>> result = ubuntu.searchPPAs(text="oink")
    >>> for archive in result:
    ...     print(archive.owner.name)
    ...

    >>> result = ubuntu.searchPPAs(text="packages")
    >>> for archive in result:
    ...     print(archive.owner.name)
    ...
    cprov
    mark

    >>> result = ubuntu.searchPPAs(text="help")
    >>> for archive in result:
    ...     print(archive.owner.name)
    ...
    cprov
    mark

Including 'inactive' PPAs:

    >>> result = ubuntu.searchPPAs(show_inactive=True)
    >>> for archive in result:
    ...     print(archive.owner.name)
    ...
    cprov
    mark
    no-priv

    >>> result = ubuntu.searchPPAs(text="priv", show_inactive=True)
    >>> for archive in result:
    ...     print(archive.owner.name)
    ...
    no-priv

    >>> result = ubuntu.searchPPAs(text="ubuntu", show_inactive=True)
    >>> for archive in result:
    ...     print(archive.owner.name)
    ...
    mark

The searchPPAs() method only returns the PPAs of active users.

    >>> from lp.services.identity.interfaces.account import AccountStatus
    >>> login("admin@canonical.com")
    >>> no_priv.setAccountStatus(AccountStatus.SUSPENDED, None, "spammer!")

    >>> result = ubuntu.searchPPAs(text="priv", show_inactive=True)
    >>> for archive in result:
    ...     print(archive.owner.name)
    ...

    >>> no_priv.setAccountStatus(AccountStatus.DEACTIVATED, None, "oops")
    >>> no_priv.setAccountStatus(AccountStatus.ACTIVE, None, "login")


Retrieving only pending-acceptance PPAs
---------------------------------------

'getPendingAcceptancePPAs' lookup will only return PPA which have
Package Upload (queue) records in ACCEPTED state.  It is used in
'process-accepted' in '--ppa' mode to avoid querying all PPAs:

Nothing is pending-acceptance in sampledata:

    >>> ubuntu.getPendingAcceptancePPAs().count()
    0

Create a NEW PackageUpload record for cprov PPA:

    >>> hoary = ubuntu["hoary"]
    >>> login("mark@example.com")
    >>> queue = hoary.createQueueEntry(
    ...     pocket=PackagePublishingPocket.RELEASE,
    ...     archive=cprov.archive,
    ...     changesfilename="foo",
    ...     changesfilecontent=b"bar",
    ... )
    >>> queue.status.name
    'NEW'

Records in NEW do not make cprov PPA pending-acceptance:

    >>> ubuntu.getPendingAcceptancePPAs().count()
    0

Neither in UNAPPROVED:

    >>> queue.setUnapproved()
    >>> queue.status.name
    'UNAPPROVED'

    >>> ubuntu.getPendingAcceptancePPAs().count()
    0

Only records in ACCEPTED does:

    >>> queue.setAccepted()
    >>> queue.status.name
    'ACCEPTED'

    >>> pending_ppas = ubuntu.getPendingAcceptancePPAs()
    >>> [pending_ppa] = pending_ppas
    >>> pending_ppa.id == cprov.archive.id
    True

Records in DONE also do not trigger pending-acceptance state in PPAs:

    >>> queue.setDone()
    >>> queue.status.name
    'DONE'

    >>> ubuntu.getPendingAcceptancePPAs().count()
    0


Retrieving only pending-acceptance PPAs
---------------------------------------

'getPendingPublicationPPAs'lookup will only return PPA which have
PENDING publishing records, it's used in 'publish-distro' in '--ppa'
mode to avoiding querying all PPAs.

Nothing is pending-publication in sampledata:

    >>> ubuntu.getPendingPublicationPPAs().count()
    0

We can make Celso's PPA pending publication by copying a published
source to another location within the PPA.

    >>> cprov_src = cprov.archive.getPublishedSources().first()

    >>> warty = ubuntu["warty"]
    >>> pocket_release = PackagePublishingPocket.RELEASE
    >>> src_pub = cprov_src.copyTo(warty, pocket_release, cprov.archive)
    >>> print(src_pub.status.name)
    PENDING

    >>> [pending_ppa] = ubuntu.getPendingPublicationPPAs()
    >>> pending_ppa.id == cprov.archive.id
    True

Publishing the record will exclude Celso's PPA from pending-publication
state:

    >>> src_pub.setPublished()

    >>> ubuntu.getPendingPublicationPPAs().count()
    0

We can also make Celso's PPA pending publication by deleting a published
source.

    >>> login("celso.providelo@canonical.com")
    >>> cprov_src.requestDeletion(cprov, "go away !")
    >>> src_pub = cprov_src

    >>> [pending_ppa] = ubuntu.getPendingPublicationPPAs()
    >>> pending_ppa.id == cprov.archive.id
    True

If scheduleddeletiondate or dateremoved are set then the PPA is no
longer pending. process-death-row will do the rest.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.services.database.constants import UTC_NOW
    >>> login("mark@example.com")
    >>> removeSecurityProxy(src_pub).scheduleddeletiondate = UTC_NOW
    >>> ubuntu.getPendingPublicationPPAs().count()
    0
    >>> removeSecurityProxy(src_pub).scheduleddeletiondate = None
    >>> ubuntu.getPendingPublicationPPAs().count()
    1
    >>> removeSecurityProxy(src_pub).dateremoved = UTC_NOW
    >>> ubuntu.getPendingPublicationPPAs().count()
    0

A binary pending publication also moves a PPA to the pending-publication
state. In order to test this behaviour we will copy some binaries within
Celso's PPA.

    >>> cprov_bin = factory.makeBinaryPackagePublishingHistory(
    ...     archive=cprov.archive, status=PackagePublishingStatus.PUBLISHED
    ... )
    >>> spr = cprov_bin.binarypackagerelease.build.source_package_release
    >>> spr.publishings.first().setPublished()
    >>> pending_binaries = cprov_bin.copyTo(
    ...     warty, pocket_release, cprov.archive
    ... )

The copied binaries are pending publication, thus Celso's PPA gets
listed in the PPA pending-publication results.

    >>> for pub in pending_binaries:
    ...     print(pub.status.name)
    ...
    PENDING
    PENDING

    >>> [pending_ppa] = ubuntu.getPendingPublicationPPAs()
    >>> pending_ppa.id == cprov.archive.id
    True

Publishing the binaries will exclude Celso's PPA from pending-
publication results:

    >>> for pub in pending_binaries:
    ...     pub.setPublished()
    ...

    >>> ubuntu.getPendingPublicationPPAs().count()
    0

A binary deletion will also make Celso's PPA pending publication.

    >>> login("celso.providelo@canonical.com")
    >>> cprov_bin.requestDeletion(cprov, "go away !")
    >>> bin_pub = cprov_bin

    >>> [pending_ppa] = ubuntu.getPendingPublicationPPAs()
    >>> pending_ppa.id == cprov.archive.id
    True

    >>> login("mark@example.com")
    >>> removeSecurityProxy(bin_pub).scheduleddeletiondate = UTC_NOW
    >>> ubuntu.getPendingPublicationPPAs().count()
    0
    >>> removeSecurityProxy(bin_pub).scheduleddeletiondate = None
    >>> ubuntu.getPendingPublicationPPAs().count()
    1
    >>> removeSecurityProxy(bin_pub).dateremoved = UTC_NOW
    >>> ubuntu.getPendingPublicationPPAs().count()
    0


Distribution Archives
---------------------

`IDistribution.all_distro_archives` returns all archives associated with
the distribution.  This list does not, therefore, include PPAs.

    >>> ubuntutest = getUtility(IDistributionSet)["ubuntutest"]
    >>> for archive in ubuntutest.all_distro_archives:
    ...     print(archive.purpose.title)
    ...
    Primary Archive
    Partner Archive

`IDistribution.getArchiveByComponent` retrieves an IArchive given a
component name.  If the component is unknown, None is returned.

    >>> partner_archive = ubuntutest.getArchiveByComponent("partner")
    >>> print(partner_archive.displayname)
    Partner Archive for Ubuntu Test

    >>> other_archive = ubuntutest.getArchiveByComponent("dodgycomponent")
    >>> print(other_archive)
    None

Multiple components, specially the debian-compatibility ones points to
the PRIMARY archive. This relationship is established so we can import
their packages in the correct archive.

    >>> main_archive = ubuntutest.getArchiveByComponent("main")
    >>> print(main_archive.displayname)
    Primary Archive for Ubuntu Test

    >>> non_free_archive = ubuntutest.getArchiveByComponent("non-free")
    >>> print(non_free_archive.displayname)
    Primary Archive for Ubuntu Test

    >>> non_free_firmware_archive = ubuntutest.getArchiveByComponent(
    ...     "non-free-firmware"
    ... )
    >>> print(non_free_firmware_archive.displayname)
    Primary Archive for Ubuntu Test

    >>> contrib_archive = ubuntutest.getArchiveByComponent("contrib")
    >>> print(contrib_archive.displayname)
    Primary Archive for Ubuntu Test
