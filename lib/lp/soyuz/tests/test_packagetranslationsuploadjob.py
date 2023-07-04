# Copyright 2013-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os

import transaction
from testtools.content import text_content
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.tests import block_on_job
from lp.services.mail.sendmail import format_address_for_person
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.soyuz.interfaces.packagetranslationsuploadjob import (
    IPackageTranslationsUploadJob,
    IPackageTranslationsUploadJobSource,
)
from lp.soyuz.model.packagetranslationsuploadjob import (
    PackageTranslationsUploadJob,
)
from lp.testing import TestCaseWithFactory, person_logged_in, verifyObject
from lp.testing.dbuser import dbuser
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import CeleryJobLayer, LaunchpadZopelessLayer
from lp.testing.script import run_script
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
)


class LocalTestHelper(TestCaseWithFactory):
    def makeJob(self, sourcepackagerelease=None, tar_content=None):
        requester = self.factory.makePerson()
        if sourcepackagerelease is None:
            distroseries = self.factory.makeDistroSeries()
            sourcepackagename = self.factory.getOrMakeSourcePackageName(
                "foobar"
            )
            self.factory.makeSourcePackage(
                sourcepackagename=sourcepackagename,
                distroseries=distroseries,
                publish=True,
            )
            spr = self.factory.makeSourcePackageRelease(
                sourcepackagename=sourcepackagename, distroseries=distroseries
            )
        else:
            spr = sourcepackagerelease
            distroseries = spr.upload_distroseries
            sourcepackagename = spr.sourcepackagename

        libraryfilealias = self.makeTranslationsLFA(tar_content)

        return (
            spr,
            distroseries.getSourcePackage(sourcepackagename),
            getUtility(IPackageTranslationsUploadJobSource).create(
                distroseries, libraryfilealias, sourcepackagename, requester
            ),
        )

    def makeTranslationsLFA(self, tar_content=None):
        """Create an LibraryFileAlias containing dummy translation data."""
        if tar_content is None:
            tar_content = {
                "source/po/foo.pot": b"Foo template",
                "source/po/eo.po": b"Foo translation",
            }
        tarfile_content = LaunchpadWriteTarFile.files_to_bytes(tar_content)
        return self.factory.makeLibraryFileAlias(content=tarfile_content)


class TestPackageTranslationsUploadJob(LocalTestHelper):
    layer = LaunchpadZopelessLayer

    def test_job_implements_IPackageTranslationsUploadJob(self):
        _, _, job = self.makeJob()
        self.assertTrue(verifyObject(IPackageTranslationsUploadJob, job))

    def test_job_source_implements_IPackageTranslationsUploadJobSource(self):
        job_source = getUtility(IPackageTranslationsUploadJobSource)
        self.assertTrue(
            verifyObject(IPackageTranslationsUploadJobSource, job_source)
        )

    def test___repr__(self):
        _, sp, job = self.makeJob()
        self.assertEqual(
            "<PackageTranslationsUploadJob for %s in %s>"
            % (sp.sourcepackagename.name, sp.distroseries),
            repr(job),
        )

    def test_iterReady(self):
        _, _, job1 = self.makeJob()
        removeSecurityProxy(job1).job._status = JobStatus.COMPLETED
        _, _, job2 = self.makeJob()
        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

    def test_getOperationDescription(self):
        _, sp, job = self.makeJob()
        self.assertEqual(
            "uploading translations of %s in %s"
            % (sp.sourcepackagename.name, sp.distroseries),
            job.getOperationDescription(),
        )

    def test_getErrorRecipients_requester(self):
        _, _, job = self.makeJob()
        email = format_address_for_person(job.requester)
        self.assertEqual([email], job.getErrorRecipients())
        removeSecurityProxy(job).requester = None
        self.assertEqual([], job.getErrorRecipients())

    def test_run(self):
        _, _, job = self.makeJob()
        method = FakeMethod()
        removeSecurityProxy(job).attachTranslationFiles = method
        transaction.commit()
        _, job.run()
        self.assertEqual(method.call_count, 1)

    def test_smoke(self):
        tar_content = {
            "source/po/foobar.pot": b"FooBar template",
        }
        spr, sp, job = self.makeJob(tar_content=tar_content)
        transaction.commit()
        env = os.environ.copy()
        env["LP_DEBUG_SQL"] = "1"
        exit_code, out, err = run_script(
            "cronscripts/process-job-source.py",
            args=["-vv", IPackageTranslationsUploadJobSource.getName()],
            env=env,
        )

        self.addDetail("stdout", text_content(out))
        self.addDetail("stderr", text_content(err))

        self.assertEqual(0, exit_code)
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(target=sp)

        self.assertEqual(1, entries_in_queue.count())
        # Check if the file in tar_content is queued:
        self.assertTrue("po/foobar.pot", entries_in_queue[0].path)


class TestViaCelery(LocalTestHelper):
    """PackageTranslationsUploadJob runs under Celery."""

    layer = CeleryJobLayer

    def test_run(self):
        self.useFixture(
            FeatureFixture(
                {
                    "jobs.celery.enabled_classes": (
                        "PackageTranslationsUploadJob"
                    ),
                }
            )
        )

        spr, sp, job = self.makeJob()
        with block_on_job(self):
            transaction.commit()
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(
            target=sp
        ).count()
        self.assertEqual(2, entries_in_queue)


class TestAttachTranslationFiles(LocalTestHelper):
    """Tests for attachTranslationFiles."""

    layer = LaunchpadZopelessLayer

    def test_attachTranslationFiles__no_translation_sharing(self):
        # If translation sharing is disabled, attachTranslationFiles() creates
        # a job in the translation import queue.

        spr, sp, job = self.makeJob()

        self.assertFalse(sp.has_sharing_translation_templates)

        transaction.commit()
        with dbuser("upload_package_translations_job"):
            job.attachTranslationFiles(True)
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(
            target=sp
        ).count()
        self.assertEqual(2, entries_in_queue)

    def test_attachTranslationFiles__translation_sharing(self):
        # If translation sharing is enabled, attachTranslationFiles() only
        # attaches templates.

        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.getOrMakeSourcePackageName("foobar")
        self.factory.makeSourcePackage(
            sourcepackagename=sourcepackagename,
            distroseries=distroseries,
            publish=True,
        )
        spr = self.factory.makeSourcePackageRelease(
            sourcepackagename=sourcepackagename, distroseries=distroseries
        )

        productseries = self.factory.makeProductSeries()
        sourcepackage = spr.upload_distroseries.getSourcePackage(
            spr.sourcepackagename
        )

        self.factory.makePOTemplate(productseries=productseries)
        with person_logged_in(sourcepackage.distroseries.owner):
            sourcepackage.setPackaging(
                productseries, sourcepackage.distroseries.owner
            )

        spr, _, job = self.makeJob(sourcepackagerelease=spr)

        self.assertTrue(sourcepackage.has_sharing_translation_templates)

        transaction.commit()
        with dbuser("upload_package_translations_job"):
            job.attachTranslationFiles(True)
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries = translation_import_queue.getAllEntries(target=sourcepackage)
        self.assertEqual(1, entries.count())
        self.assertTrue(entries[0].path.endswith(".pot"))
