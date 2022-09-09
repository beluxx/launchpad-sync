Archive Permissions
===================

The ArchivePermission table gives us a way of looking up permissions for
operations in the archive context.  The IArchivePermission utility adds
an easy way of accessing the data through convenient helpers.

Two main operations are supported: upload and queue administration.

    >>> from lp.testing import verifyObject
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.enums import ArchivePermissionType
    >>> from lp.soyuz.interfaces.archivepermission import (
    ...     IArchivePermission,
    ...     IArchivePermissionSet,
    ... )
    >>> from lp.soyuz.model.archivepermission import ArchivePermission

    >>> permission_set = getUtility(IArchivePermissionSet)

The ArchivePermission context class implements the IArchivePermission
interface.

    >>> random_permission = IStore(ArchivePermission).get(
    ...     ArchivePermission, 1
    ... )
    >>> verifyObject(IArchivePermission, random_permission)
    True

It's possible to make a direct permission enquiry using the method
'checkAuthenticated'.  The "Ubuntu Team" has a few permissions set in
the sample data that we can check.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> ubuntu_team = getUtility(IPersonSet).getByName("ubuntu-team")
    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> main_component = getUtility(IComponentSet)["main"]

We can now find out if "Ubuntu Team" has permission to upload to the
main component.

    >>> main_permissions = permission_set.checkAuthenticated(
    ...     ubuntu_team,
    ...     ubuntu.main_archive,
    ...     ArchivePermissionType.UPLOAD,
    ...     main_component,
    ... )
    >>> main_permissions.count()
    1

    >>> [main_permission] = main_permissions

The fact that an ArchivePermission object is returned means that the
Ubuntu Team is indeed permissioned to upload to the main archive.  It
has a number of useful properties that can be checked:

    >>> print(main_permission.date_created)
    2006-10-16...

    >>> print(main_permission.archive.displayname)
    Primary Archive for Ubuntu Linux

    >>> main_permission.permission
    <DBItem ArchivePermissionType.UPLOAD, (1) Archive Upload Rights>

    >>> print(main_permission.person.name)
    ubuntu-team

    >>> print(main_permission.component_name)
    main

    >>> print(main_permission.source_package_name)
    None

The checkAuthenticated() call is also able to check someone's
permission on a SourcePackageName, which gives a smaller radius of
permission than allowing access to the whole component.  Just pass
a SourcePackageName as the "item" parameter:

    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet,
    ... )
    >>> alsa_utils = getUtility(ISourcePackageNameSet)["alsa-utils"]
    >>> alsa_permissions = permission_set.checkAuthenticated(
    ...     ubuntu_team,
    ...     ubuntu.main_archive,
    ...     ArchivePermissionType.UPLOAD,
    ...     alsa_utils,
    ... )

Ubuntu Team does not have permission to upload to alsa-utils,
specifically (which is moot anyway because they have access to the
component, but this demonstrates package-level permissioning):

    >>> alsa_permissions.count()
    0

When passing a person to checkAuthenticated() who is a member of a team
that has permission, the matching ArchivePermission record(s) for the
team are returned.  This allows team-level permissions to be set.

    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> mark.inTeam(ubuntu_team)
    True

    >>> all_main_permissions = permission_set.uploadersForComponent(
    ...     ubuntu.main_archive, main_component
    ... )
    >>> for permission in all_main_permissions:
    ...     print(permission.person.name)
    ...
    ubuntu-team

    >>> permission_set.checkAuthenticated(
    ...     mark,
    ...     ubuntu.main_archive,
    ...     ArchivePermissionType.UPLOAD,
    ...     main_component,
    ... ).count()
    1

checkAuthenticated() does not know about any other item types, and
passing a type that it does not know about results in an AssertionError:

    >>> permission_set.checkAuthenticated(
    ...     ubuntu_team,
    ...     ubuntu.main_archive,
    ...     ArchivePermissionType.UPLOAD,
    ...     ubuntu,
    ... )
    Traceback (most recent call last):
    ...
    AssertionError: 'item' ... is not an IComponent, IPackageset,
    ISourcePackageName or PackagePublishingPocket

IArchivePermissionSet also has some helpers to make it very easy to
check permissions.

permissionsForPerson() returns all the permission records for the supplied
person:

    >>> permission_set.permissionsForPerson(
    ...     ubuntu.main_archive, ubuntu_team
    ... ).count()
    7

uploadersForComponent() returns ArchivePermission records where a person
or team has permission to upload to the supplied component:

    >>> import operator
    >>> uploaders = permission_set.uploadersForComponent(
    ...     ubuntu.main_archive, main_component
    ... )
    >>> for uploader in sorted(uploaders, key=operator.attrgetter("id")):
    ...     print(uploader.person.name)
    ...
    ubuntu-team

The component argument can also be a string type and it's converted
internally to a component object:

    >>> uploaders = permission_set.uploadersForComponent(
    ...     ubuntu.main_archive, "main"
    ... )

If the string is not a valid component, a NotFound exception is thrown:

    >>> uploaders = permission_set.uploadersForComponent(
    ...     ubuntu.main_archive, "badcomponent"
    ... )
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.ComponentNotFound:
    No such component: 'badcomponent'.

If the component argument is not passed, it will return
ArchivePermission records for all matching components:

    >>> uploaders = permission_set.uploadersForComponent(ubuntu.main_archive)
    >>> for uploader in sorted(uploaders, key=operator.attrgetter("id")):
    ...     print(uploader.person.name, uploader.component.name)
    ...
    ubuntu-team universe
    ubuntu-team restricted
    ubuntu-team main

componentsForUploader() returns ArchivePermission records for all the
components that the supplied user has permission to upload to.

    >>> def showComponentUploaders(archive, person):
    ...     permissions = permission_set.componentsForUploader(
    ...         archive, person
    ...     )
    ...     for permission in sorted(
    ...         permissions, key=operator.attrgetter("id")
    ...     ):
    ...         print(permission.component.name)
    ...

    >>> showComponentUploaders(ubuntu.main_archive, mark)
    universe
    restricted
    main

uploadersForPackage() returns the ArchivePermission records where a person
or team has permission to upload to the supplied source package name:

    >>> permission_set.uploadersForPackage(
    ...     ubuntu.main_archive, alsa_utils
    ... ).count()
    0

You can also pass a string package name instead of an ISourcePackageName:

    >>> permission_set.uploadersForPackage(
    ...     ubuntu.main_archive, "alsa-utils"
    ... ).count()
    0

Passing a non-existent package name will cause a
NoSuchSourcePackageName to be thrown.

    >>> uploaders = permission_set.uploadersForPackage(
    ...     ubuntu.main_archive, "fakepackage"
    ... )
    Traceback (most recent call last):
    ...
    lp.registry.errors.NoSuchSourcePackageName:
    No such source package: 'fakepackage'.

Similarly, packagesForUploader() returns the ArchivePermission records where
the supplied user has permission to upload to packages.

    >>> def showPersonsPackages(archive, person):
    ...     packages = permission_set.packagesForUploader(archive, person)
    ...     for permission in sorted(packages, key=operator.attrgetter("id")):
    ...         print(permission.sourcepackagename.name)
    ...

    >>> carlos = getUtility(IPersonSet).getByName("carlos")
    >>> showPersonsPackages(ubuntu.main_archive, carlos)
    mozilla-firefox

If you're a member of a team that has permission, the team permission is
returned.  Here, cprov is a member of ubuntu-team:

    >>> discard = ArchivePermission(
    ...     archive=ubuntu.main_archive,
    ...     person=ubuntu_team,
    ...     sourcepackagename=alsa_utils,
    ...     permission=ArchivePermissionType.UPLOAD,
    ... )
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> showPersonsPackages(ubuntu.main_archive, cprov)
    alsa-utils

queueAdminsForComponent() returns the ArchivePermission records where a
person or team has permission to administer an archive's package
queues in that component.

    >>> def showQueueAdmins(archive, component):
    ...     archive_admins = permission_set.queueAdminsForComponent(
    ...         archive, component
    ...     )
    ...     for archive_admin in sorted(
    ...         archive_admins, key=operator.attrgetter("id")
    ...     ):
    ...         print(archive_admin.person.name)
    ...

    >>> showQueueAdmins(ubuntu.main_archive, main_component)
    ubuntu-team
    name12

componentsForQueueAdmin() returns the ArchivePermission records for all
the components that the supplied user has permission to administer in
the distroseries queue. It can be passed a single archive or an
enumeration of archives.

    >>> name12 = getUtility(IPersonSet).getByName("name12")
    >>> permissions = permission_set.componentsForQueueAdmin(
    ...     ubuntu.main_archive, name12
    ... )
    >>> for permission in sorted(permissions, key=operator.attrgetter("id")):
    ...     print(permission.component.name)
    ...
    main
    restricted
    universe
    multiverse

    >>> no_team = getUtility(IPersonSet).getByName("no-team-memberships")
    >>> permissions = permission_set.componentsForQueueAdmin(
    ...     ubuntu.all_distro_archives, no_team
    ... )
    >>> for permission in sorted(permissions, key=operator.attrgetter("id")):
    ...     print(permission.component.name)
    ...
    universe
    multiverse


Amending Permissions
~~~~~~~~~~~~~~~~~~~~

There are some methods that will enable the caller to add and delete
PackageSet based permissions.  They require no special permission to use
because these methods should only ever be called from inside other security
proxied objects like IArchive.

newPackageUploader() creates a permission for a person to upload to a
specific package:

    >>> new_permission = permission_set.newPackageUploader(
    ...     ubuntu.main_archive, carlos, "alsa-utils"
    ... )
    >>> showPersonsPackages(ubuntu.main_archive, carlos)
    mozilla-firefox
    alsa-utils

Calling again with the same parameters simply returns the existing
permission.

    >>> dup_permission = permission_set.newPackageUploader(
    ...     ubuntu.main_archive, carlos, "alsa-utils"
    ... )
    >>> new_permission.id == dup_permission.id
    True

deletePackageUploader() removes it:

    >>> permission_set.deletePackageUploader(
    ...     ubuntu.main_archive, carlos, "alsa-utils"
    ... )
    >>> showPersonsPackages(ubuntu.main_archive, carlos)
    mozilla-firefox

newComponentUploader() creates a permission for a person to upload to a
specific component:

    >>> new_permission = permission_set.newComponentUploader(
    ...     ubuntu.main_archive, mark, "multiverse"
    ... )
    >>> showComponentUploaders(ubuntu.main_archive, mark)
    universe
    restricted
    main
    multiverse

Calling again with the same parameters simply returns the existing
permission.

    >>> dup_permission = permission_set.newComponentUploader(
    ...     ubuntu.main_archive, mark, "multiverse"
    ... )
    >>> new_permission.id == dup_permission.id
    True

deleteComponentUploader() removes it:

    >>> permission_set.deleteComponentUploader(
    ...     ubuntu.main_archive, mark, "multiverse"
    ... )
    >>> showComponentUploaders(ubuntu.main_archive, mark)
    universe
    restricted
    main

newQueueAdmin() creates a permission for a person to administer a
specific component in the distroseries queues:

    >>> new_permission = permission_set.newQueueAdmin(
    ...     ubuntu.main_archive, carlos, "main"
    ... )
    >>> showQueueAdmins(ubuntu.main_archive, main_component)
    ubuntu-team
    name12
    carlos

Calling again with the same parameters simply returns the existing
permission.

    >>> dup_permission = permission_set.newQueueAdmin(
    ...     ubuntu.main_archive, carlos, "main"
    ... )
    >>> new_permission.id == dup_permission.id
    True

deleteQueueAdmin() removes it:

    >>> permission_set.deleteQueueAdmin(ubuntu.main_archive, carlos, "main")
    >>> showQueueAdmins(ubuntu.main_archive, main_component)
    ubuntu-team
    name12

newPocketQueueAdmin() creates a permission for a person to administer a
specific pocket in the distroseries queues, which may or may not be
per-series:

    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket

    >>> def showPocketQueueAdmins(archive, pocket, distroseries=None):
    ...     archive_admins = permission_set.queueAdminsForPocket(
    ...         archive, pocket, distroseries=distroseries
    ...     )
    ...     for archive_admin in sorted(
    ...         archive_admins, key=operator.attrgetter("id")
    ...     ):
    ...         print(archive_admin.person.name)
    ...

    >>> new_permission = permission_set.newPocketQueueAdmin(
    ...     ubuntu.main_archive, carlos, PackagePublishingPocket.SECURITY
    ... )
    >>> new_permission = permission_set.newPocketQueueAdmin(
    ...     ubuntu.main_archive,
    ...     mark,
    ...     PackagePublishingPocket.PROPOSED,
    ...     distroseries=ubuntu.series[0],
    ... )
    >>> showPocketQueueAdmins(
    ...     ubuntu.main_archive, PackagePublishingPocket.SECURITY
    ... )
    carlos
    >>> showPocketQueueAdmins(
    ...     ubuntu.main_archive, PackagePublishingPocket.PROPOSED
    ... )
    mark
    >>> showPocketQueueAdmins(
    ...     ubuntu.main_archive,
    ...     PackagePublishingPocket.PROPOSED,
    ...     distroseries=ubuntu.series[0],
    ... )
    mark
    >>> showPocketQueueAdmins(
    ...     ubuntu.main_archive,
    ...     PackagePublishingPocket.PROPOSED,
    ...     distroseries=ubuntu.series[1],
    ... )

checkAuthenticated returns sensible results for these permissions:

    >>> def countPocketAdminPermissions(person, pocket, distroseries=None):
    ...     return permission_set.checkAuthenticated(
    ...         person,
    ...         ubuntu.main_archive,
    ...         ArchivePermissionType.QUEUE_ADMIN,
    ...         pocket,
    ...         distroseries=distroseries,
    ...     ).count()
    ...

    >>> countPocketAdminPermissions(carlos, PackagePublishingPocket.SECURITY)
    1
    >>> countPocketAdminPermissions(mark, PackagePublishingPocket.PROPOSED)
    1
    >>> countPocketAdminPermissions(
    ...     mark, PackagePublishingPocket.PROPOSED, ubuntu.series[0]
    ... )
    1
    >>> countPocketAdminPermissions(
    ...     mark, PackagePublishingPocket.PROPOSED, ubuntu.series[1]
    ... )
    0
    >>> countPocketAdminPermissions(
    ...     mark, PackagePublishingPocket.SECURITY, ubuntu.series[0]
    ... )
    0

deletePocketQueueAdmin removes them:

    >>> permission_set.deletePocketQueueAdmin(
    ...     ubuntu.main_archive, carlos, PackagePublishingPocket.SECURITY
    ... )
    >>> permission_set.deletePocketQueueAdmin(
    ...     ubuntu.main_archive,
    ...     mark,
    ...     PackagePublishingPocket.PROPOSED,
    ...     distroseries=ubuntu.series[0],
    ... )
    >>> showPocketQueueAdmins(
    ...     ubuntu.main_archive, PackagePublishingPocket.SECURITY
    ... )
    >>> showPocketQueueAdmins(
    ...     ubuntu.main_archive, PackagePublishingPocket.PROPOSED
    ... )
