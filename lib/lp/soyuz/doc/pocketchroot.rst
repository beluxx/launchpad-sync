PocketChroot
============

PocketChroot records combine DistroArchSeries and a Chroot.

Chroot are identified per LibraryFileAlias and we offer three method
based on IDistroArchSeries to handle them: get, add and update.

    >>> from lp.services.librarian.interfaces import ILibraryFileAliasSet
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> from lp.testing import login_admin

    >>> _ = login_admin()


Grab a distroarchseries:

    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> hoary = ubuntu["hoary"]
    >>> hoary_i386 = hoary["i386"]

Grab some files to be used as Chroots (it doesn't really matter what
they are, they simply need to be provide ILFA interface):

    >>> chroot1 = getUtility(ILibraryFileAliasSet)[1]
    >>> chroot2 = getUtility(ILibraryFileAliasSet)[2]

Check if getPocketChroot returns None for unknown chroots:

    >>> p_chroot = hoary_i386.getPocketChroot(PackagePublishingPocket.RELEASE)
    >>> print(p_chroot)
    None

Check if getChroot returns the 'default' argument on not found chroots:

    >>> print(hoary_i386.getChroot(default="duuuuh"))
    duuuuh

Invoke addOrUpdateChroot for missing chroot, so it will insert a new
record in PocketChroot:

    >>> p_chroot1 = hoary_i386.addOrUpdateChroot(chroot=chroot1)
    >>> print(p_chroot1.distroarchseries.architecturetag)
    i386
    >>> print(p_chroot1.pocket.name)
    RELEASE
    >>> print(p_chroot1.chroot.id)
    1

Invoke addOrUpdateChroot on an existing PocketChroot, it will update
the chroot:

    >>> p_chroot2 = hoary_i386.addOrUpdateChroot(chroot=chroot2)
    >>> print(p_chroot2.distroarchseries.architecturetag)
    i386
    >>> print(p_chroot2.pocket.name)
    RELEASE
    >>> print(p_chroot2.chroot.id)
    2
    >>> p_chroot2 == p_chroot1
    True

Ensure chroot was updated by retrieving it from DB again:

    >>> hoary_i386.getPocketChroot(PackagePublishingPocket.RELEASE).chroot.id
    2

Check if getChroot returns the correspondent Chroot LFA instance for
valid chroots.

    >>> chroot = hoary_i386.getChroot()
    >>> chroot.id
    2

PocketChroots can also (per the name) be set for specific pockets:

    >>> chroot3 = getUtility(ILibraryFileAliasSet)[3]
    >>> p_chroot3 = hoary_i386.addOrUpdateChroot(
    ...     chroot=chroot3, pocket=PackagePublishingPocket.UPDATES
    ... )
    >>> print(p_chroot3.distroarchseries.architecturetag)
    i386
    >>> print(p_chroot3.pocket.name)
    UPDATES
    >>> print(p_chroot3.chroot.id)
    3
    >>> hoary_i386.getPocketChroot(PackagePublishingPocket.UPDATES).chroot.id
    3
    >>> hoary_i386.getChroot(pocket=PackagePublishingPocket.UPDATES).id
    3

getPocketChroot falls back to depended-on pockets if necessary:

    >>> hoary_i386.getPocketChroot(PackagePublishingPocket.SECURITY).chroot.id
    2
    >>> print(
    ...     hoary_i386.getPocketChroot(
    ...         PackagePublishingPocket.SECURITY, exact_pocket=True
    ...     )
    ... )
    None
    >>> hoary_i386.getChroot(pocket=PackagePublishingPocket.SECURITY).id
    2
    >>> hoary_i386.removeChroot(pocket=PackagePublishingPocket.UPDATES)
    >>> hoary_i386.getChroot(pocket=PackagePublishingPocket.UPDATES).id
    2

Force transaction commit in order to test DB constraints:

    >>> import transaction
    >>> transaction.commit()
