# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for translation import queue views."""

from datetime import datetime
from pytz import timezone
from unittest import TestLoader

from zope.component import getMultiAdapter
from zope.security.proxy import removeSecurityProxy

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.layers import TranslationsLayer, setFirstLayer
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from lp.registry.model.sourcepackage import SourcePackage
from lp.testing import TestCaseWithFactory
from lp.translations.model.translationimportqueue import (
    TranslationImportQueue)


class TestTranslationImportQueueEntryView(TestCaseWithFactory):
    """Tests for the queue entry review form."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestTranslationImportQueueEntryView, self).setUp(
            'foo.bar@canonical.com')
        self.queue = TranslationImportQueue()
        self.uploader = self.factory.makePerson()

    def _makeProductSeries(self):
        """Set up a product series for a translatable product."""
        product = self.factory.makeProduct()
        product.official_rosetta = True
        return product.getSeries('trunk')

    def _makeView(self, entry):
        """Create view for a queue entry."""
        request = LaunchpadTestRequest()
        setFirstLayer(request, TranslationsLayer)
        view = getMultiAdapter((entry, request), name='+index')
        view.initialize()
        return view

    def _makeEntry(self, productseries=None, distroseries=None,
                   sourcepackagename=None):
        filename = self.factory.getUniqueString() + '.pot'
        contents = self.factory.getUniqueString()
        entry = self.queue.addOrUpdateEntry(
            filename, contents, False, self.uploader,
            productseries=productseries, distroseries=distroseries,
            sourcepackagename=sourcepackagename)
        return removeSecurityProxy(entry)

    def test_import_target_productseries(self):
        # If the entry's attached to a ProductSeries, that's what
        # import_target returns.
        series = self._makeProductSeries()
        entry = self._makeEntry(productseries=series)
        view = self._makeView(entry)

        self.assertEqual(series, view.import_target)

    def test_import_target_sourcepackage(self):
        # If the entry has a DistroSeries and a SourcePackageName, the
        # import_target is the corresponding SourcePackage.
        series = self.factory.makeDistroSeries()
        packagename = self.factory.makeSourcePackageName()
        package = SourcePackage(packagename, series)
        entry = self._makeEntry(
            distroseries=series, sourcepackagename=packagename)
        view = self._makeView(entry)

        self.assertEqual(package, view.import_target)

    def test_productseries_templates_link(self):
        # productseries_templates_link counts and, if appropriate links
        # to, the series' templates.
        series = self._makeProductSeries()
        entry = self._makeEntry(productseries=series)
        view = self._makeView(entry)

        # If there are no templates, there is no link.
        self.assertEqual("no templates", view.productseries_templates_link)

        # For one template, there is a link.  Its text uses the
        # singular.
        self.factory.makePOTemplate(productseries=series)
        self.assertIn('1 template', view.productseries_templates_link)
        self.assertNotIn('1 templates', view.productseries_templates_link)
        url = canonical_url(series, rootsite='translations') + '/+templates'
        self.assertIn(url, view.productseries_templates_link)

    def test_product_translatable_series(self):
        # If the entry belongs to a productseries, product_translatable_series
        # lists the product's translatable series.
        series = self._makeProductSeries()
        product = series.product
        entry = self._makeEntry(productseries=series)
        view = self._makeView(entry)

        # No translatable series.
        series_text = view.product_translatable_series
        self.assertEqual("Project has no translatable series.", series_text)

        # One translatable series.
        extra_series = self.factory.makeProductSeries(product=product)
        self.factory.makePOTemplate(productseries=extra_series)
        series_text = view.product_translatable_series
        self.assertIn("Project has translatable series:", series_text)
        # A link follows, and the sentence ends in a period.
        self.assertEqual('</a>.', series_text[-5:])

        # Two translatable series.
        extra_series = self.factory.makeProductSeries(product=product)
        self.factory.makePOTemplate(productseries=extra_series)
        series_text = view.product_translatable_series
        # The links to the series are separated by a comma.
        self.assertIn("</a>, <a ", series_text)
        # The sentence ends in a period.
        self.assertEqual('</a>.', series_text[-5:])

        # Many translatable series.  The list is cut short; there's an
        # ellipsis to indicate this.
        series_count = len(product.translatable_series)
        for counter in xrange(series_count, view.max_series_to_display + 1):
            extra_series = self.factory.makeProductSeries(product=product)
            self.factory.makePOTemplate(productseries=extra_series)
        series_text = view.product_translatable_series
        # The list is cut short.
        displayed_series_count = series_text.count('</a>')
        self.assertNotEqual(
            len(product.translatable_series), displayed_series_count)
        self.assertEqual(view.max_series_to_display, displayed_series_count)
        # The list of links ends with an ellipsis.
        self.assertEqual('</a>, ...', series_text[-9:])

    def test_status_change_date(self):
        # status_change_date describes the date of the entry's last
        # status change.
        series = self._makeProductSeries()
        product = series.product
        entry = self._makeEntry(productseries=series)
        view = self._makeView(entry)

        # If the date equals the upload date, there's no need to show
        # anything.
        self.assertEqual('', view.status_change_date)

        # If there is a difference, there's a human-readable
        # description.
        UTC = timezone('UTC')
        entry.dateimported = datetime(year=2005, month=11, day=29, tzinfo=UTC)
        entry.date_status_changed = datetime(
            year=2007, month=8, day=14, tzinfo=UTC)
        self.assertEqual(
            "Last changed on 2007-08-14.", view.status_change_date)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
