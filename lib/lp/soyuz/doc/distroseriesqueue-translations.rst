Upload processing queue with translations
=========================================

This test covers the use case when a package includes translations and is
uploaded into the system.

    >>> from lp.buildmaster.interfaces.processor import IProcessorSet
    >>> from lp.soyuz.model.publishing import SourcePackagePublishingHistory
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.distroseries import (
    ...     IDistroSeriesSet,
    ... )
    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> from lp.soyuz.enums import PackagePublishingStatus
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet,
    ... )

    >>> from lp.archiveuploader.nascentupload import NascentUpload
    >>> from lp.archiveuploader.tests import datadir, getPolicy

    >>> from lp.testing.gpgkeys import import_public_test_keys
    >>> import_public_test_keys()

    >>> from lp.services.database.constants import UTC_NOW

    >>> from lp.soyuz.model.packagetranslationsuploadjob import (
    ...     PackageTranslationsUploadJob,
    ... )

    # We need to setup our test environment and create the needed objects.
    >>> distro_series_set = getUtility(IDistroSeriesSet)
    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> hoary = distro_series_set.queryByName(ubuntu, "hoary")

# Create the Dapper distro series.
    >>> dapper = ubuntu.newSeries(
    ...     "dapper",
    ...     "Dapper",
    ...     "Dapper",
    ...     "Dapper",
    ...     "Dapper",
    ...     "06.04",
    ...     hoary,
    ...     hoary.owner,
    ... )

# And an AMD 64 arch series.
    >>> dapper_amd64 = dapper.newArch(
    ...     "amd64",
    ...     getUtility(IProcessorSet).getByName("amd64"),
    ...     True,
    ...     dapper.owner,
    ... )

Only uploads to the RELEASE, UPDATES, SECURITY and PROPOSED pockets are
considered for import. An upload to the BACKPORT pocket won't appear in the
queue:

# We are going to import the pmount build into RELEASE pocket.
    >>> pmount_sourcepackagename = getUtility(ISourcePackageNameSet)["pmount"]
    >>> source_package_release = factory.makeSourcePackageRelease(
    ...     distroseries=dapper,
    ...     sourcepackagename=pmount_sourcepackagename,
    ...     version="0.9.7-2ubuntu2",
    ...     maintainer=dapper.owner,
    ...     creator=dapper.owner,
    ...     component="main",
    ...     section_name="base",
    ...     urgency="low",
    ...     architecturehintlist="i386",
    ... )

    >>> publishing_history = SourcePackagePublishingHistory(
    ...     distroseries=dapper.id,
    ...     sourcepackagerelease=source_package_release.id,
    ...     sourcepackagename=source_package_release.sourcepackagename,
    ...     _format=source_package_release.format,
    ...     component=source_package_release.component.id,
    ...     section=source_package_release.section.id,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     datecreated=UTC_NOW,
    ...     pocket=PackagePublishingPocket.RELEASE,
    ...     archive=dapper.main_archive,
    ... )

# Do the upload into the system.

    >>> from lp.soyuz.interfaces.binarypackagebuild import (
    ...     IBinaryPackageBuildSet,
    ... )
    >>> build = getUtility(IBinaryPackageBuildSet).new(
    ...     source_package_release,
    ...     dapper.main_archive,
    ...     dapper_amd64,
    ...     PackagePublishingPocket.RELEASE,
    ... )

    >>> buildd_policy = getPolicy(
    ...     name="buildd", distro="ubuntu", distroseries="dapper"
    ... )

    >>> from lp.services.log.logger import FakeLogger
    >>> pmount_upload = NascentUpload.from_changesfile_path(
    ...     datadir("pmount_0.9.7-2ubuntu2_amd64.changes"),
    ...     buildd_policy,
    ...     FakeLogger(),
    ... )
    >>> pmount_upload.process(build=build)
    DEBUG Beginning processing.
    DEBUG pmount_0.9.7-2ubuntu2_amd64.changes can be unsigned.
    DEBUG Verifying the changes file.
    DEBUG Verifying files in upload.
    DEBUG Verifying binary pmount_0.9.7-2ubuntu2_amd64.deb
    DEBUG Verifying timestamps in pmount_0.9.7-2ubuntu2_amd64.deb
    DEBUG Finding and applying overrides.
    DEBUG Checking for pmount/0.9.7-2ubuntu2/amd64 binary ancestry
    DEBUG pmount: (binary) NEW
    DEBUG Finished checking upload.

 # It was not rejected.
    >>> pmount_upload.is_rejected
    False

At this point, no translations uploads have been registered for this
package.

    >>> from lp.registry.model.sourcepackage import SourcePackage
    >>> dapper_pmount = SourcePackage(pmount_sourcepackagename, dapper)
    >>> print(len(dapper_pmount.getLatestTranslationsUploads()))
    0

    >>> success = pmount_upload.do_accept(build=build)
    DEBUG Creating queue entry
    ...

    # And all things worked.
    >>> success
    True

# Ensure 'deb' is NEW and 'translation' is recognized, i.e., ACCEPTED
# XXX julian 2007-05-27 Commented out for now because getNotificationSummary
# no longer exists and this content is impossible to check at the moment
# since no email is generated because the recipients are not LP Persons.
# (So why is it being checked in the first place?)
#>>> print(pmount_upload.getNotificationSummary())
#NEW: pmount_0.9.7-2ubuntu2_amd64.deb
#OK: pmount_0.9.7-2ubuntu2_amd64_translations.tar.gz

The upload now shows up as the latest translations upload for the
package.

    >>> latest_translations_uploads = list(
    ...     dapper_pmount.getLatestTranslationsUploads()
    ... )
    >>> print(len(latest_translations_uploads))
    1

We'll get back to that uploaded file later.

    >>> latest_translations_upload = latest_translations_uploads[0]

# Check the import queue content, it should be empty.
    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue,
    ... )
    >>> translation_import_queue = getUtility(ITranslationImportQueue)
    >>> translation_import_queue.getAllEntries(target=ubuntu).count()
    0

# We need to commit the transaction to be able to use the librarian files.
    >>> import transaction
    >>> transaction.commit()

An upload to the RELEASE pocket will add items to the import queue:

    >>> from lp.soyuz.enums import PackageUploadStatus
    >>> queue_item = dapper.getPackageUploads(status=PackageUploadStatus.NEW)[
    ...     0
    ... ]

    >>> spph_creator = factory.makePerson(name="john-doe")

The source package needs to be published because rosetta translations
publisher will query for the latest publication to know the destination
component.

    >>> spph = factory.makeSourcePackagePublishingHistory(
    ...     sourcepackagerelease=queue_item.sourcepackagerelease,
    ...     distroseries=queue_item.distroseries,
    ...     pocket=queue_item.pocket,
    ...     creator=spph_creator,
    ... )
    >>> queue_item.customfiles[0].publish()

When publish() runs, it creates a PackageTranslationsUploadJob that will
process the package translation files. We need to find and run it to be
able to verify the imported files.
    >>> def runPendingPackageTranslationsUploadJob():
    ...     job = list(PackageTranslationsUploadJob.iterReady())[0]
    ...     job.run()
    ...

    >>> runPendingPackageTranslationsUploadJob()

As we can see from the translation import queue content, the importer is
the person pointed by findPersonToNotify, or the latest spph creator,
or rosetta-admins. In this case, as findPersonToNotify returns nothing,
the spph creator is the requester.

    >>> for entry in translation_import_queue.getAllEntries(target=ubuntu):
    ...     print(
    ...         "%s/%s by %s: %s"
    ...         % (
    ...             entry.distroseries.name,
    ...             entry.sourcepackagename.name,
    ...             entry.importer.name,
    ...             entry.path,
    ...         )
    ...     )
    ...
    dapper/pmount by john-doe: po/es_ES.po
    dapper/pmount by john-doe: po/ca.po
    dapper/pmount by john-doe: po/de.po
    dapper/pmount by john-doe: po/cs.po
    dapper/pmount by john-doe: po/es.po
    dapper/pmount by john-doe: po/fr.po
    dapper/pmount by john-doe: po/hr.po
    dapper/pmount by john-doe: po/nb.po
    dapper/pmount by john-doe: po/pmount.pot
    dapper/pmount by john-doe: po/it_IT.po

# Abort the transaction so we can check the same upload in a different
# pocket.
    >>> transaction.abort()

# The import queue content should be empty now that the transaction is
# reverted.
    >>> translation_import_queue.getAllEntries(target=ubuntu).count()
    0

An upload to the BACKPORTS pocket will not add items to the import queue:

    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> dapper = distro_series_set.queryByName(ubuntu, "dapper")
    >>> queue_item = dapper.getPackageUploads(PackageUploadStatus.NEW)[0]
    >>> queue_item.pocket = PackagePublishingPocket.BACKPORTS
    >>> spph = factory.makeSourcePackagePublishingHistory(
    ...     sourcepackagerelease=queue_item.sourcepackagerelease,
    ...     distroseries=queue_item.distroseries,
    ...     pocket=queue_item.pocket,
    ... )

    >>> queue_item.customfiles[0].publish()

# And this time, we see that there are no entries imported in the queue.
    >>> translation_import_queue.getAllEntries(target=ubuntu).count()
    0

# Let's abort the transaction so we can check the same upload in a different
# pocket.
    >>> transaction.abort()

But an upload to the UPDATE pocket will add items to the import queue:

    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> dapper = distro_series_set.queryByName(ubuntu, "dapper")
    >>> queue_item = dapper.getPackageUploads(PackageUploadStatus.NEW)[0]
    >>> queue_item.pocket = PackagePublishingPocket.UPDATES
    >>> spph = factory.makeSourcePackagePublishingHistory(
    ...     sourcepackagerelease=queue_item.sourcepackagerelease,
    ...     distroseries=queue_item.distroseries,
    ...     pocket=queue_item.pocket,
    ... )

    >>> queue_item.customfiles[0].publish()
    >>> runPendingPackageTranslationsUploadJob()

As we can see from the translation import queue content, as the publication
has no creator specified, it falls back to rosetta-admins as the requester.

    >>> print(spph.creator)
    None

    >>> for entry in translation_import_queue.getAllEntries(target=ubuntu):
    ...     print(
    ...         "%s/%s by %s: %s"
    ...         % (
    ...             entry.distroseries.name,
    ...             entry.sourcepackagename.name,
    ...             entry.importer.name,
    ...             entry.path,
    ...         )
    ...     )
    ...
    dapper/pmount by rosetta-admins: po/es_ES.po
    dapper/pmount by rosetta-admins: po/ca.po
    dapper/pmount by rosetta-admins: po/de.po
    dapper/pmount by rosetta-admins: po/cs.po
    dapper/pmount by rosetta-admins: po/es.po
    dapper/pmount by rosetta-admins: po/fr.po
    dapper/pmount by rosetta-admins: po/hr.po
    dapper/pmount by rosetta-admins: po/nb.po
    dapper/pmount by rosetta-admins: po/pmount.pot
    dapper/pmount by rosetta-admins: po/it_IT.po

# Let's abort the transaction so we can check the same upload in a different
# pocket.
    >>> transaction.abort()

Uploads to restricted component are accepted too.

    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> dapper = distro_series_set.queryByName(ubuntu, "dapper")
    >>> restricted_component = getUtility(IComponentSet)["restricted"]
    >>> queue_item = dapper.getPackageUploads(PackageUploadStatus.NEW)[0]

# Change the component where this package was attached.
    >>> queue_item.builds[0].build.source_package_release.override(
    ...     component=restricted_component
    ... )
    >>> queue_item.customfiles[0].publish()
    >>> runPendingPackageTranslationsUploadJob()

As we can see from the translation import queue content.

    >>> for entry in translation_import_queue.getAllEntries(target=ubuntu):
    ...     print(
    ...         "%s/%s by %s: %s"
    ...         % (
    ...             entry.distroseries.name,
    ...             entry.sourcepackagename.name,
    ...             entry.importer.name,
    ...             entry.path,
    ...         )
    ...     )
    ...
    dapper/pmount by rosetta-admins: po/es_ES.po
    dapper/pmount by rosetta-admins: po/ca.po
    dapper/pmount by rosetta-admins: po/de.po
    dapper/pmount by rosetta-admins: po/cs.po
    dapper/pmount by rosetta-admins: po/es.po
    dapper/pmount by rosetta-admins: po/fr.po
    dapper/pmount by rosetta-admins: po/hr.po
    dapper/pmount by rosetta-admins: po/nb.po
    dapper/pmount by rosetta-admins: po/pmount.pot
    dapper/pmount by rosetta-admins: po/it_IT.po

# Let's abort the transaction so we can check the same upload in a different
# component.
    >>> transaction.abort()

But the ones into universe are not accepted.

    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> dapper = distro_series_set.queryByName(ubuntu, "dapper")
    >>> universe_component = getUtility(IComponentSet)["universe"]
    >>> queue_item = dapper.getPackageUploads(PackageUploadStatus.NEW)[0]

# Change the component where this package was attached.
    >>> queue_item.builds[0].build.source_package_release.override(
    ...     component=universe_component
    ... )
    >>> queue_item.customfiles[0].publish()

This time, we don't get any entry in the import queue.

    >>> translation_import_queue.getAllEntries(target=ubuntu).count()
    0

# Let's abort the transaction so we can check the same upload in a different
# component.
    >>> transaction.abort()


Translations from PPA build
---------------------------

For now we simply ignore translations for archives other than the
Distribution archives (i.e. PPAs).

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.enums import ArchivePurpose
    >>> from lp.soyuz.interfaces.archive import IArchiveSet

    >>> foobar_archive = getUtility(IArchiveSet).new(
    ...     purpose=ArchivePurpose.PPA,
    ...     owner=getUtility(IPersonSet).getByName("name16"),
    ... )

    >>> dapper = getUtility(IDistributionSet)["ubuntu"]["dapper"]
    >>> queue_item = dapper.getPackageUploads(PackageUploadStatus.NEW)[0]
    >>> queue_item.archive = foobar_archive

    >>> queue_item.customfiles[0].publish(FakeLogger())
    DEBUG Publishing custom pmount,
    pmount_0.9.7-2ubuntu2_amd64_translations.tar.gz to ubuntu/dapper
    DEBUG Skipping translations since its purpose is not in
    MAIN_ARCHIVE_PURPOSES and the archive is not whitelisted.

# And this time, we see that there are no entries imported in the queue.
    >>> translation_import_queue.getAllEntries(target=ubuntu).count()
    0
    >>> transaction.abort()


Translations from a rebuild
---------------------------

Translations coming from rebuilt packages are also ignored.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.interfaces.archive import ArchivePurpose, IArchiveSet

    >>> foobar_archive = getUtility(IArchiveSet).new(
    ...     purpose=ArchivePurpose.COPY,
    ...     owner=getUtility(IPersonSet).getByName("name16"),
    ...     name="rebuilds",
    ... )

    >>> dapper = getUtility(IDistributionSet)["ubuntu"]["dapper"]
    >>> queue_item = dapper.getPackageUploads(PackageUploadStatus.NEW)[0]
    >>> queue_item.archive = foobar_archive

    >>> queue_item.customfiles[0].publish(FakeLogger())
    DEBUG Publishing custom pmount,
    pmount_0.9.7-2ubuntu2_amd64_translations.tar.gz to ubuntu/dapper
    DEBUG Skipping translations since its purpose is not in
    MAIN_ARCHIVE_PURPOSES and the archive is not whitelisted.

# And this time, we see that there are no entries imported in the queue.
    >>> translation_import_queue.getAllEntries(target=ubuntu).count()
    0

Translations tarball
~~~~~~~~~~~~~~~~~~~~

The LibraryFileAlias returned by getLatestTranslationsUploads on the
source package points to a tarball with translations files for the
package.

    >>> import io
    >>> import tarfile
    >>> tarball = io.BytesIO(latest_translations_upload.read())
    >>> archive = tarfile.open("", "r|gz", tarball)
    >>> translation_files = sorted(
    ...     [
    ...         entry.name
    ...         for entry in archive.getmembers()
    ...         if entry.name.endswith(".po") or entry.name.endswith(".pot")
    ...     ]
    ... )
    >>> for filename in translation_files:
    ...     print(filename)
    ...
    ./source/po/ca.po
    ./source/po/cs.po
    ./source/po/de.po
    ...
    ./source/po/pmount.pot
