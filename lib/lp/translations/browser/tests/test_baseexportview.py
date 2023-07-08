# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest
from datetime import timedelta

import transaction

from lp.services.database.interfaces import IPrimaryStore
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessDatabaseLayer
from lp.translations.browser.productseries import (
    ProductSeriesTranslationsExportView,
)
from lp.translations.browser.sourcepackage import (
    SourcePackageTranslationsExportView,
)
from lp.translations.interfaces.translationfileformat import (
    TranslationFileFormat,
)
from lp.translations.model.poexportrequest import POExportRequest


def wipe_queue(queue):
    """Erase all export queue entries."""
    IPrimaryStore(POExportRequest).execute("DELETE FROM POExportRequest")


class BaseExportViewMixin(TestCaseWithFactory):
    """Test behaviour of objects subclassing BaseExportView."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        super().setUp()

    def createTranslationTemplate(self, name, priority=0):
        """Attaches a template to appropriate container."""
        raise NotImplementedError(
            "This must be provided by an executable test."
        )

    def test_uses_translations_no_templates(self):
        # With no templates in an object, it's not using translations yet.
        self.assertFalse(self.view.uses_translations)

    def test_uses_translations_obsolete_templates(self):
        # With an obsolete template, it's not considered to use translations.
        template = self.createTranslationTemplate("obsolete")
        template.iscurrent = False
        self.assertFalse(self.view.uses_translations)

    def test_uses_translations_current_templates(self):
        # If there is a current template, it is marked as using translations.
        self.createTranslationTemplate("current")
        self.assertTrue(self.view.uses_translations)

    def test_getDefaultFormat(self):
        # With no templates in an object, default format is None.
        self.assertIsNone(self.view.getDefaultFormat())

        # With one template added, it's format is returned.
        template1 = self.createTranslationTemplate("one")
        template1.source_file_format = TranslationFileFormat.XPI
        self.assertEqual(
            TranslationFileFormat.XPI, self.view.getDefaultFormat()
        )

        # With multiple templates, format with a lower ID is returned
        # if they are different, where PO (1) < XPI (3).
        template2 = self.createTranslationTemplate("two")
        template2.source_file_format = TranslationFileFormat.PO
        self.assertEqual(
            TranslationFileFormat.PO, self.view.getDefaultFormat()
        )

        # Obsolete templates do not affect default file format.
        template2.iscurrent = False
        self.assertEqual(
            TranslationFileFormat.XPI, self.view.getDefaultFormat()
        )

    def test_processForm_empty(self):
        # With no templates, empty ResultSet is returned for templates,
        # and None for PO files.
        templates, translations = self.view.processForm()
        self.assertEqual(([], None), (list(templates), None))

        # With just obsolete templates, empty results are returned again.
        template1 = self.createTranslationTemplate("one")
        template1.iscurrent = False
        templates, translations = self.view.processForm()
        self.assertEqual(([], None), (list(templates), None))

    def test_processForm_templates(self):
        # With a template, a ResultSet is returned for it.
        template1 = self.createTranslationTemplate("one", priority=1)
        templates, translations = self.view.processForm()
        self.assertEqual([template1.id], list(templates))

        # With more than one template, they are both returned
        # ordered by decreasing priority.
        template2 = self.createTranslationTemplate("two", priority=2)
        templates, translations = self.view.processForm()
        self.assertEqual([template2.id, template1.id], list(templates))

    def test_processForm_translations(self):
        # With a template, but no PO files, None is returned for translations.
        template1 = self.createTranslationTemplate("one")
        templates, translations = self.view.processForm()
        self.assertIsNone(translations)

        # Adding a PO file to this template makes it returned.
        pofile_sr = self.factory.makePOFile("sr", potemplate=template1)
        templates, translations = self.view.processForm()
        self.assertContentEqual([pofile_sr.id], translations)

        # If there are two PO files on the same template, they are
        # both returned.
        pofile_es = self.factory.makePOFile("es", potemplate=template1)
        templates, translations = self.view.processForm()
        self.assertContentEqual([pofile_sr.id, pofile_es.id], translations)

        # With more than one template, PO files from both are returned.
        template2 = self.createTranslationTemplate("two", priority=2)
        pofile_sr2 = self.factory.makePOFile("sr", potemplate=template2)
        templates, translations = self.view.processForm()
        self.assertContentEqual(
            [pofile_sr.id, pofile_es.id, pofile_sr2.id], translations
        )


class TestProductSeries(BaseExportViewMixin):
    """Test implementation of BaseExportView on ProductSeries."""

    def createTranslationTemplate(self, name, priority=0):
        potemplate = self.factory.makePOTemplate(
            name=name, productseries=self.container
        )
        potemplate.priority = priority
        return potemplate

    def setUp(self):
        super().setUp()
        self.container = self.factory.makeProductSeries()
        self.view = ProductSeriesTranslationsExportView(
            self.container, LaunchpadTestRequest()
        )


class TestSourcePackage(BaseExportViewMixin):
    """Test implementation of BaseExportView on ProductSeries."""

    def createTranslationTemplate(self, name, priority=0):
        potemplate = self.factory.makePOTemplate(
            name=name,
            distroseries=self.container.distroseries,
            sourcepackagename=self.container.sourcepackagename,
        )
        potemplate.priority = priority
        return potemplate

    def setUp(self):
        super().setUp()
        self.container = self.factory.makeSourcePackage()
        self.view = SourcePackageTranslationsExportView(
            self.container, LaunchpadTestRequest()
        )


class TestPOExportQueueStatusDescriptions(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def setUp(self):
        super().setUp()
        self.container = self.factory.makeProductSeries()
        self.view = ProductSeriesTranslationsExportView(
            self.container, LaunchpadTestRequest()
        )

    def test_describeQueueSize(self):
        self.assertEqual(
            "The export queue is currently empty.",
            self.view.describeQueueSize(0),
        )

        self.assertEqual(
            "There is 1 file request on the export queue.",
            self.view.describeQueueSize(1),
        )

        self.assertEqual(
            "There are 2 file requests on the export queue.",
            self.view.describeQueueSize(2),
        )

    def test_describeBacklog(self):
        backlog = None
        self.assertEqual("", self.view.describeBacklog(backlog).strip())

        backlog = timedelta(hours=2)
        self.assertEqual(
            "The backlog is approximately 2 hours.",
            self.view.describeBacklog(backlog).strip(),
        )

    def test_export_queue_status(self):
        self.view.initialize()
        queue = self.view.request_set
        wipe_queue(queue)

        requester = self.factory.makePerson()

        size = self.view.describeQueueSize(0)
        backlog = self.view.describeBacklog(None)
        status = "%s %s" % (size, backlog)
        self.assertEqual(status.strip(), self.view.export_queue_status.strip())

        potemplate = self.factory.makePOTemplate()
        queue.addRequest(requester, potemplates=[potemplate])
        transaction.commit()

        size = self.view.describeQueueSize(1)
        backlog = self.view.describeBacklog(queue.estimateBacklog())
        status = "%s %s" % (size, backlog)
        self.assertEqual(status.strip(), self.view.export_queue_status.strip())


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestProductSeries))
    suite.addTest(loader.loadTestsFromTestCase(TestSourcePackage))
    suite.addTest(
        loader.loadTestsFromTestCase(TestPOExportQueueStatusDescriptions)
    )
    return suite
