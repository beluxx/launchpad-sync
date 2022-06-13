# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os.path

from debian.deb822 import Changes
from testtools.matchers import (
    Equals,
    Is,
    MatchesSetwise,
    MatchesStructure,
    )
import transaction

from lp.code.enums import RevisionStatusArtifactType
from lp.code.model.revisionstatus import RevisionStatusArtifact
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database.interfaces import IStore
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.runner import JobRunner
from lp.services.job.tests import (
    block_on_job,
    pop_remote_notifications,
    )
from lp.services.mail.sendmail import format_address_for_person
from lp.soyuz.enums import (
    ArchiveJobType,
    BinaryPackageFileType,
    BinaryPackageFormat,
    PackageUploadStatus,
    )
from lp.soyuz.model.archivejob import (
    ArchiveJob,
    ArchiveJobDerived,
    CIBuildUploadJob,
    PackageUploadNotificationJob,
    )
from lp.soyuz.tests import datadir
from lp.testing import (
    admin_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.layers import (
    CeleryJobLayer,
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.mail_helpers import pop_notifications


class TestArchiveJob(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_instantiate(self):
        # ArchiveJob.__init__() instantiates a ArchiveJob instance.
        archive = self.factory.makeArchive()

        metadata = ('some', 'arbitrary', 'metadata')
        archive_job = ArchiveJob(
            archive, ArchiveJobType.PACKAGE_UPLOAD_NOTIFICATION, metadata)

        self.assertEqual(archive, archive_job.archive)
        self.assertEqual(
            ArchiveJobType.PACKAGE_UPLOAD_NOTIFICATION, archive_job.job_type)

        # When we actually access the ArchiveJob's metadata it gets
        # deserialized from JSON, so the representation returned by
        # archive_job.metadata will be different from what we originally
        # passed in.
        metadata_expected = ('some', 'arbitrary', 'metadata')
        self.assertEqual(metadata_expected, archive_job.metadata)


class TestArchiveJobDerived(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_create_explodes(self):
        # ArchiveJobDerived.create() will blow up because it needs to be
        # subclassed to work properly.
        archive = self.factory.makeArchive()
        self.assertRaises(
            AttributeError, ArchiveJobDerived.create, archive)


class TestPackageUploadNotificationJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_getOopsVars(self):
        upload = self.factory.makePackageUpload(
            status=PackageUploadStatus.ACCEPTED)
        job = PackageUploadNotificationJob.create(
            upload, summary_text='Fake summary')
        expected = [
            ('job_id', job.context.job.id),
            ('archive_id', upload.archive.id),
            ('archive_job_id', job.context.id),
            ('archive_job_type', 'Package upload notification'),
            ('packageupload_id', upload.id),
            ('packageupload_status', 'Accepted'),
            ('summary_text', 'Fake summary'),
            ]
        self.assertEqual(expected, job.getOopsVars())

    def test_metadata(self):
        upload = self.factory.makePackageUpload(
            status=PackageUploadStatus.ACCEPTED)
        job = PackageUploadNotificationJob.create(
            upload, summary_text='Fake summary')
        expected = {
            'packageupload_id': upload.id,
            'packageupload_status': 'Accepted',
            'summary_text': 'Fake summary',
            }
        self.assertEqual(expected, job.metadata)
        self.assertEqual(upload, job.packageupload)
        self.assertEqual(
            PackageUploadStatus.ACCEPTED, job.packageupload_status)
        self.assertEqual('Fake summary', job.summary_text)

    def test_run(self):
        # Running a job produces a notification.  Detailed tests of which
        # notifications go to whom live in the PackageUpload and
        # PackageUploadMailer tests.
        distroseries = self.factory.makeDistroSeries()
        creator = self.factory.makePerson()
        changes = Changes({"Changed-By": format_address_for_person(creator)})
        upload = self.factory.makePackageUpload(
            distroseries=distroseries, archive=distroseries.main_archive,
            changes_file_content=changes.dump().encode("UTF-8"))
        upload.addSource(self.factory.makeSourcePackageRelease())
        self.factory.makeComponentSelection(
            upload.distroseries, upload.sourcepackagerelease.component)
        upload.setAccepted()
        job = PackageUploadNotificationJob.create(
            upload, summary_text='Fake summary')
        with dbuser(job.config.dbuser):
            JobRunner([job]).runAll()
        [email] = pop_notifications()
        self.assertEqual(format_address_for_person(creator), email['To'])
        self.assertIn('(Accepted)', email['Subject'])
        self.assertIn('Fake summary', email.get_payload()[0].get_payload())


class TestCIBuildUploadJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_getOopsVars(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        build = self.factory.makeCIBuild()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        expected = [
            ("job_id", job.context.job.id),
            ("archive_id", archive.id),
            ("archive_job_id", job.context.id),
            ("archive_job_type", "CI build upload"),
            ("ci_build_id", build.id),
            ("target_distroseries_id", distroseries.id),
            ("target_pocket", "Release"),
            ("target_channel", "edge"),
            ]
        self.assertEqual(expected, job.getOopsVars())

    def test_metadata(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        build = self.factory.makeCIBuild()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        expected = {
            "ci_build_id": build.id,
            "target_distroseries_id": distroseries.id,
            "target_pocket": "Release",
            "target_channel": "edge",
            }
        self.assertEqual(expected, job.metadata)
        self.assertEqual(build, job.ci_build)
        self.assertEqual(distroseries, job.target_distroseries)
        self.assertEqual(PackagePublishingPocket.RELEASE, job.target_pocket)
        self.assertEqual("edge", job.target_channel)

    def test__scanFile_wheel_indep(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        build = self.factory.makeCIBuild()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        path = "wheel-indep/dist/wheel_indep-0.0.1-py3-none-any.whl"
        expected = {
            "name": "wheel-indep",
            "version": "0.0.1",
            "summary": "Example description",
            "description": "Example long description\n",
            "binpackageformat": BinaryPackageFormat.WHL,
            "architecturespecific": False,
            "homepage": "",
            }
        self.assertEqual(expected, job._scanFile(datadir(path)))

    def test__scanFile_wheel_arch(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        build = self.factory.makeCIBuild()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        path = "wheel-arch/dist/wheel_arch-0.0.1-cp310-cp310-linux_x86_64.whl"
        expected = {
            "name": "wheel-arch",
            "version": "0.0.1",
            "summary": "Example description",
            "description": "Example long description\n",
            "binpackageformat": BinaryPackageFormat.WHL,
            "architecturespecific": True,
            "homepage": "http://example.com/",
            }
        self.assertEqual(expected, job._scanFile(datadir(path)))

    def test__scanFile_conda_indep(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        build = self.factory.makeCIBuild()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        path = "conda-indep/dist/noarch/conda-indep-0.1-0.tar.bz2"
        expected = {
            "name": "conda-indep",
            "version": "0.1",
            "summary": "Example summary",
            "description": "Example description",
            "binpackageformat": BinaryPackageFormat.CONDA_V1,
            "architecturespecific": False,
            "homepage": "",
            "user_defined_fields": [("subdir", "noarch")],
            }
        self.assertEqual(expected, job._scanFile(datadir(path)))

    def test__scanFile_conda_arch(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        build = self.factory.makeCIBuild()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        path = "conda-arch/dist/linux-64/conda-arch-0.1-0.tar.bz2"
        expected = {
            "name": "conda-arch",
            "version": "0.1",
            "summary": "Example summary",
            "description": "Example description",
            "binpackageformat": BinaryPackageFormat.CONDA_V1,
            "architecturespecific": True,
            "homepage": "http://example.com/",
            "user_defined_fields": [("subdir", "linux-64")],
            }
        self.assertEqual(expected, job._scanFile(datadir(path)))

    def test__scanFile_conda_v2_indep(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        build = self.factory.makeCIBuild()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        path = "conda-v2-indep/dist/noarch/conda-v2-indep-0.1-0.conda"
        expected = {
            "name": "conda-v2-indep",
            "version": "0.1",
            "summary": "Example summary",
            "description": "Example description",
            "binpackageformat": BinaryPackageFormat.CONDA_V2,
            "architecturespecific": False,
            "homepage": "",
            "user_defined_fields": [("subdir", "noarch")],
            }
        self.assertEqual(expected, job._scanFile(datadir(path)))

    def test__scanFile_conda_v2_arch(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        build = self.factory.makeCIBuild()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        path = "conda-v2-arch/dist/linux-64/conda-v2-arch-0.1-0.conda"
        expected = {
            "name": "conda-v2-arch",
            "version": "0.1",
            "summary": "Example summary",
            "description": "Example description",
            "binpackageformat": BinaryPackageFormat.CONDA_V2,
            "architecturespecific": True,
            "homepage": "http://example.com/",
            "user_defined_fields": [("subdir", "linux-64")],
            }
        self.assertEqual(expected, job._scanFile(datadir(path)))

    def test_run_indep(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        dases = [
            self.factory.makeDistroArchSeries(distroseries=distroseries)
            for _ in range(2)]
        build = self.factory.makeCIBuild(distro_arch_series=dases[0])
        report = build.getOrCreateRevisionStatusReport("build:0")
        report.setLog(b"log data")
        path = "wheel-indep/dist/wheel_indep-0.0.1-py3-none-any.whl"
        with open(datadir(path), mode="rb") as f:
            report.attach(name=os.path.basename(path), data=f.read())
        artifact = IStore(RevisionStatusArtifact).find(
            RevisionStatusArtifact,
            report=report,
            artifact_type=RevisionStatusArtifactType.BINARY).one()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        transaction.commit()

        with dbuser(job.config.dbuser):
            JobRunner([job]).runAll()

        self.assertThat(archive.getAllPublishedBinaries(), MatchesSetwise(*(
            MatchesStructure(
                binarypackagename=MatchesStructure.byEquality(
                    name="wheel-indep"),
                binarypackagerelease=MatchesStructure(
                    ci_build=Equals(build),
                    binarypackagename=MatchesStructure.byEquality(
                        name="wheel-indep"),
                    version=Equals("0.0.1"),
                    summary=Equals("Example description"),
                    description=Equals("Example long description\n"),
                    binpackageformat=Equals(BinaryPackageFormat.WHL),
                    architecturespecific=Is(False),
                    homepage=Equals(""),
                    files=MatchesSetwise(
                        MatchesStructure.byEquality(
                            libraryfile=artifact.library_file,
                            filetype=BinaryPackageFileType.WHL))),
                binarypackageformat=Equals(BinaryPackageFormat.WHL),
                distroarchseries=Equals(das))
            for das in dases)))

    def test_run_arch(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        dases = [
            self.factory.makeDistroArchSeries(distroseries=distroseries)
            for _ in range(2)]
        build = self.factory.makeCIBuild(distro_arch_series=dases[0])
        report = build.getOrCreateRevisionStatusReport("build:0")
        report.setLog(b"log data")
        path = "wheel-arch/dist/wheel_arch-0.0.1-cp310-cp310-linux_x86_64.whl"
        with open(datadir(path), mode="rb") as f:
            report.attach(name=os.path.basename(path), data=f.read())
        artifact = IStore(RevisionStatusArtifact).find(
            RevisionStatusArtifact,
            report=report,
            artifact_type=RevisionStatusArtifactType.BINARY).one()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        transaction.commit()

        with dbuser(job.config.dbuser):
            JobRunner([job]).runAll()

        self.assertThat(archive.getAllPublishedBinaries(), MatchesSetwise(
            MatchesStructure(
                binarypackagename=MatchesStructure.byEquality(
                    name="wheel-arch"),
                binarypackagerelease=MatchesStructure(
                    ci_build=Equals(build),
                    binarypackagename=MatchesStructure.byEquality(
                        name="wheel-arch"),
                    version=Equals("0.0.1"),
                    summary=Equals("Example description"),
                    description=Equals("Example long description\n"),
                    binpackageformat=Equals(BinaryPackageFormat.WHL),
                    architecturespecific=Is(True),
                    homepage=Equals("http://example.com/"),
                    files=MatchesSetwise(
                        MatchesStructure.byEquality(
                            libraryfile=artifact.library_file,
                            filetype=BinaryPackageFileType.WHL))),
                binarypackageformat=Equals(BinaryPackageFormat.WHL),
                distroarchseries=Equals(dases[0]))))

    def test_run_conda(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        dases = [
            self.factory.makeDistroArchSeries(distroseries=distroseries)
            for _ in range(2)]
        build = self.factory.makeCIBuild(distro_arch_series=dases[0])
        report = build.getOrCreateRevisionStatusReport("build:0")
        report.setLog(b"log data")
        path = "conda-arch/dist/linux-64/conda-arch-0.1-0.tar.bz2"
        with open(datadir(path), mode="rb") as f:
            report.attach(name=os.path.basename(path), data=f.read())
        artifact = IStore(RevisionStatusArtifact).find(
            RevisionStatusArtifact,
            report=report,
            artifact_type=RevisionStatusArtifactType.BINARY).one()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        transaction.commit()

        with dbuser(job.config.dbuser):
            JobRunner([job]).runAll()

        self.assertThat(archive.getAllPublishedBinaries(), MatchesSetwise(
            MatchesStructure(
                binarypackagename=MatchesStructure.byEquality(
                    name="conda-arch"),
                binarypackagerelease=MatchesStructure(
                    ci_build=Equals(build),
                    binarypackagename=MatchesStructure.byEquality(
                        name="conda-arch"),
                    version=Equals("0.1"),
                    summary=Equals("Example summary"),
                    description=Equals("Example description"),
                    binpackageformat=Equals(BinaryPackageFormat.CONDA_V1),
                    architecturespecific=Is(True),
                    homepage=Equals("http://example.com/"),
                    files=MatchesSetwise(
                        MatchesStructure.byEquality(
                            libraryfile=artifact.library_file,
                            filetype=BinaryPackageFileType.CONDA_V1))),
                binarypackageformat=Equals(BinaryPackageFormat.CONDA_V1),
                distroarchseries=Equals(dases[0]))))

    def test_run_conda_v2(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution)
        dases = [
            self.factory.makeDistroArchSeries(distroseries=distroseries)
            for _ in range(2)]
        build = self.factory.makeCIBuild(distro_arch_series=dases[0])
        report = build.getOrCreateRevisionStatusReport("build:0")
        report.setLog(b"log data")
        path = "conda-v2-arch/dist/linux-64/conda-v2-arch-0.1-0.conda"
        with open(datadir(path), mode="rb") as f:
            report.attach(name=os.path.basename(path), data=f.read())
        artifact = IStore(RevisionStatusArtifact).find(
            RevisionStatusArtifact,
            report=report,
            artifact_type=RevisionStatusArtifactType.BINARY).one()
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")
        transaction.commit()

        with dbuser(job.config.dbuser):
            JobRunner([job]).runAll()

        self.assertThat(archive.getAllPublishedBinaries(), MatchesSetwise(
            MatchesStructure(
                binarypackagename=MatchesStructure.byEquality(
                    name="conda-v2-arch"),
                binarypackagerelease=MatchesStructure(
                    ci_build=Equals(build),
                    binarypackagename=MatchesStructure.byEquality(
                        name="conda-v2-arch"),
                    version=Equals("0.1"),
                    summary=Equals("Example summary"),
                    description=Equals("Example description"),
                    binpackageformat=Equals(BinaryPackageFormat.CONDA_V2),
                    architecturespecific=Is(True),
                    homepage=Equals("http://example.com/"),
                    files=MatchesSetwise(
                        MatchesStructure.byEquality(
                            libraryfile=artifact.library_file,
                            filetype=BinaryPackageFileType.CONDA_V2))),
                binarypackageformat=Equals(BinaryPackageFormat.CONDA_V2),
                distroarchseries=Equals(dases[0]))))


class TestViaCelery(TestCaseWithFactory):

    layer = CeleryJobLayer

    def test_PackageUploadNotificationJob(self):
        # PackageUploadNotificationJob runs under Celery.
        self.useFixture(FeatureFixture(
            {"jobs.celery.enabled_classes": "PackageUploadNotificationJob"}))
        creator = self.factory.makePerson()
        changes = Changes({"Changed-By": format_address_for_person(creator)})
        upload = self.factory.makePackageUpload(
            changes_file_content=changes.dump().encode())
        with admin_logged_in():
            upload.addSource(self.factory.makeSourcePackageRelease())
            self.factory.makeComponentSelection(
                upload.distroseries, upload.sourcepackagerelease.component)
            upload.setAccepted()
        job = PackageUploadNotificationJob.create(upload)

        with block_on_job():
            transaction.commit()

        self.assertEqual(JobStatus.COMPLETED, job.status)
        self.assertEqual(1, len(pop_remote_notifications()))

    def test_CIBuildUploadJob(self):
        # CIBuildUploadJob runs under Celery.
        self.useFixture(FeatureFixture(
            {"jobs.celery.enabled_classes": "CIBuildUploadJob"}))
        build = self.factory.makeCIBuild()
        das = build.distro_arch_series
        archive = das.distroseries.main_archive
        report = build.getOrCreateRevisionStatusReport("build:0")
        path = "wheel-indep/dist/wheel_indep-0.0.1-py3-none-any.whl"
        with open(datadir(path), mode="rb") as f:
            with person_logged_in(build.git_repository.owner):
                report.attach(name=os.path.basename(path), data=f.read())
        job = CIBuildUploadJob.create(
            build, build.git_repository.owner, archive, das.distroseries,
            PackagePublishingPocket.RELEASE, target_channel="edge")

        with block_on_job():
            transaction.commit()

        self.assertEqual(JobStatus.COMPLETED, job.status)
        self.assertEqual(1, archive.getAllPublishedBinaries().count())
