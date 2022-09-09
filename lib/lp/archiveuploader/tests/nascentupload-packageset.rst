In order to prepare the tests below some initialization is required.

    >>> import transaction
    >>> from lp.archiveuploader.nascentupload import NascentUpload
    >>> from lp.archiveuploader.tests import datadir, getPolicy
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet,
    ... )
    >>> from lp.soyuz.enums import ArchivePermissionType
    >>> from lp.soyuz.interfaces.archivepermission import (
    ...     IArchivePermissionSet,
    ... )
    >>> from lp.soyuz.interfaces.packageset import IPackagesetSet
    >>> from lp.testing.dbuser import switch_dbuser

    >>> insecure_policy = getPolicy(
    ...     name="insecure", distro="ubuntu", distroseries="hoary"
    ... )
    >>> ap_set = getUtility(IArchivePermissionSet)
    >>> name16 = getUtility(IPersonSet).getByName("name16")
    >>> bar_name = getUtility(ISourcePackageNameSet).getOrCreateByName("bar")

Let's modify the current ACL rules for ubuntu, moving the upload
rights to all components from 'ubuntu-team' to 'mark':

    >>> switch_dbuser("launchpad")
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.model.archivepermission import ArchivePermission
    >>> new_uploader = getUtility(IPersonSet).getByName("mark")
    >>> store = IStore(ArchivePermission)
    >>> for permission in store.find(ArchivePermission):
    ...     permission.person = new_uploader
    ...
    >>> store.flush()
    >>> switch_dbuser("uploader")

This time the upload will fail because the ACLs don't let
"name16", the key owner, upload a package.

    >>> from lp.services.log.logger import DevNullLogger
    >>> bar_failed = NascentUpload.from_changesfile_path(
    ...     datadir("suite/bar_1.0-1/bar_1.0-1_source.changes"),
    ...     insecure_policy,
    ...     DevNullLogger(),
    ... )

    >>> bar_failed.process()
    >>> bar_failed.is_rejected
    True
    >>> print(bar_failed.rejection_message)
    The signer of this package has no upload rights to this distribution's
    primary archive.  Did you mean to upload to a PPA?


We can grant selective, package set based upload permissions to the user
in order to facilitate uploads.

    >>> def print_permission(result_set):
    ...     for perm in result_set.order_by(
    ...         "person, permission, packageset, explicit"
    ...     ):
    ...         person = perm.person.name
    ...         pset = perm.packageset.name
    ...         if perm.permission == ArchivePermissionType.UPLOAD:
    ...             permission = "UPLOAD"
    ...         elif perm.permission == ArchivePermissionType.QUEUE_ADMIN:
    ...             permission = "QUEUE_ADMIN"
    ...         else:
    ...             permission = "???"
    ...         if perm.explicit == True:
    ...             ptype = "explicit"
    ...         else:
    ...             ptype = "implicit"
    ...         print(
    ...             "%12s: %18s -> %20s (%s)"
    ...             % (person, pset, permission, ptype)
    ...         )
    ...

name16 does not have any package set based upload permissions for 'bar'
at present.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> ubuntu_archive = ubuntu.main_archive
    >>> print_permission(
    ...     ap_set.packagesetsForSourceUploader(ubuntu_archive, "bar", name16)
    ... )


Let's first add an empty package set, grant 'name16' an archive permission
to it and see whether that changes things.

    >>> switch_dbuser("launchpad")

Here goes the empty package set.

    >>> ps_set = getUtility(IPackagesetSet)
    >>> empty_ps = ps_set.new(
    ...     "empty-pkg-set",
    ...     "Empty package set.",
    ...     name16,
    ...     ubuntu.currentseries,
    ... )
    >>> transaction.commit()

And here's name16's upload permission for it.

    >>> ignore_this = ap_set.newPackagesetUploader(
    ...     ubuntu_archive, name16, empty_ps
    ... )

There are still no package sets that include 'bar'.

    >>> print_permission(
    ...     ap_set.packagesetsForSourceUploader(ubuntu_archive, "bar", name16)
    ... )

Let's retry the upload.

    >>> bar_failed = NascentUpload.from_changesfile_path(
    ...     datadir("suite/bar_1.0-1/bar_1.0-1_source.changes"),
    ...     insecure_policy,
    ...     DevNullLogger(),
    ... )

    >>> bar_failed.process()
    >>> bar_failed.is_rejected
    True
    >>> print(bar_failed.rejection_message)
    The signer of this package is lacking the upload rights for the source
    package, component or package set in question.

The error message above makes it clear that the uploader does have *some*
permissions defined but these are not sufficient for the source package at
hand.

Next put in place a package set, add 'bar' to it and define a permission
for the former.

    >>> foo_ps = ps_set.new(
    ...     "foo-pkg-set",
    ...     "Packages that require special care.",
    ...     name16,
    ...     ubuntu.currentseries,
    ... )
    >>> transaction.commit()

Add 'bar' to the 'foo' package set.

    >>> foo_ps.add((bar_name,))

Now 'bar' is included by the 'foo' package set.

    >>> [ps] = ps_set.setsIncludingSource("bar", direct_inclusion=True)
    >>> print(ps.name)
    foo-pkg-set

name16 has no package set based upload privileges for 'bar' yet.

    >>> ap_set.isSourceUploadAllowed(
    ...     ubuntu_archive, "bar", name16, ubuntu.currentseries
    ... )
    False

Now we define a permission for name16 to upload to the 'foo' package set.

    >>> ignore_this = ap_set.newPackagesetUploader(
    ...     ubuntu_archive, name16, foo_ps
    ... )
    >>> print_permission(
    ...     ap_set.packagesetsForSourceUploader(ubuntu_archive, "bar", name16)
    ... )
          name16:   foo-pkg-set ->               UPLOAD (implicit)

And, voila, name16 has a package set based upload authorization for 'bar'.

    >>> ap_set.isSourceUploadAllowed(
    ...     ubuntu_archive, "bar", name16, ubuntu.currentseries
    ... )
    True

With the authorization above the upload should work again.

    >>> switch_dbuser("uploader")
    >>> bar2 = NascentUpload.from_changesfile_path(
    ...     datadir("suite/bar_1.0-1/bar_1.0-1_source.changes"),
    ...     insecure_policy,
    ...     DevNullLogger(),
    ... )
    >>> bar2.process()
    >>> bar2.is_rejected
    False

    >>> print(bar2.rejection_message)

