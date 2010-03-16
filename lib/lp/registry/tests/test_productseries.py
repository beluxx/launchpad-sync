# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ProductSeries and ProductSeriesSet."""

__metaclass__ = type

from unittest import TestLoader

from zope.component import getUtility

from canonical.testing import ZopelessDatabaseLayer
from lp.testing import TestCaseWithFactory
from lp.registry.interfaces.productseries import IProductSeriesSet
from lp.translations.interfaces.translations import (
    TranslationsBranchImportMode)


class TestProductSeriesDrivers(TestCaseWithFactory):
    """Test the 'drivers' attribute of a ProductSeries."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        """Setup a ProjectGroup, a Product and a ProductSeries."""
        super(TestProductSeriesDrivers, self).setUp()
        self.projectgroup = self.factory.makeProject()
        self.product = self.factory.makeProduct(project=self.projectgroup)
        self.series = self.factory.makeProductSeries(product=self.product)

    def test_drivers_nodrivers_group(self):
        # With no drivers set, the project group owner is the driver.
        self.assertContentEqual(
            [self.projectgroup.owner], self.series.drivers)

    def test_drivers_nodrivers_prodcut(self):
        # With no drivers set and without a project group, the product
        # owner is the driver.
        self.product.project = None
        self.assertContentEqual(
            [self.product.owner], self.series.drivers)

    def _setDrivers(self, group=False, product=False, series=False):
        # Set drivers on all levels, as directed.
        if group:
            self.projectgroup_driver = self.factory.makePerson()
            self.projectgroup.driver = self.projectgroup_driver
        if product:
            self.product_driver = self.factory.makePerson()
            self.product.driver = self.product_driver
        if series:
            self.series_driver = self.factory.makePerson()
            self.series.driver = self.series_driver

    def test_drivers_group(self):
        # A driver on the group is reported as one of the drivers of the
        # series.
        self._setDrivers(group=True)
        self.assertContentEqual(
            [self.projectgroup_driver], self.series.drivers)

    def test_drivers_group_product(self):
        # The driver on the group and the product are reported as the drivers
        # of the series.
        self._setDrivers(group=True, product=True)
        self.assertContentEqual(
            [self.projectgroup_driver, self.product_driver],
            self.series.drivers)

    def test_drivers_group_product_series(self):
        # All drivers at all level are reported as the drivers of the series.
        self._setDrivers(group=True, product=True, series=True)
        self.assertContentEqual(
            [self.projectgroup_driver,
             self.product_driver,
             self.series_driver
             ],
            self.series.drivers)

    def test_drivers_product(self):
        # The product driver is the driver if there is no other.
        self._setDrivers(product=True)
        self.assertContentEqual(
            [self.product_driver],
            self.series.drivers)

    def test_drivers_series(self):
        # If only the series has a driver, the project group owner is
        # is reported, too.
        self._setDrivers(series=True)
        self.assertContentEqual(
            [self.projectgroup.owner, self.series_driver],
            self.series.drivers)

    def test_drivers_product_series(self):
        self._setDrivers(product=True, series=True)
        self.assertContentEqual(
            [self.product_driver, self.series_driver], self.series.drivers)

    def test_drivers_group_series(self):
        self._setDrivers(group=True, series=True)
        self.assertContentEqual(
            [self.projectgroup_driver, self.series_driver],
            self.series.drivers)

    def test_drivers_series_nogroup(self):
        # Without a project group, the product owner is reported as driver.
        self._setDrivers(series=True)
        self.product.project = None
        self.assertContentEqual(
            [self.product.owner, self.series_driver],
            self.series.drivers)

    def test_drivers_product_series_nogroup(self):
        self._setDrivers(product=True, series=True)
        self.product.project = None
        self.assertContentEqual(
            [self.product_driver, self.series_driver], self.series.drivers)

    def test_drivers_product_nogroup(self):
        self._setDrivers(product=True)
        self.product.project = None
        self.assertContentEqual(
            [self.product_driver], self.series.drivers)


class TestProductSeriesSet(TestCaseWithFactory):
    """Test ProductSeriesSet."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestProductSeriesSet, self).setUp()
        self.ps_set = getUtility(IProductSeriesSet)

    def _makeSeriesAndBranch(self):
        self.productseries = self.factory.makeProductSeries()
        self.branch = self.factory.makeProductBranch(
            self.productseries.product)
        self.productseries.branch = self.branch

    def test_findByTranslationsImportBranch(self):
        self._makeSeriesAndBranch()
        self.productseries.translations_autoimport_mode = (
            TranslationsBranchImportMode.IMPORT_TEMPLATES)

        self.assertContentEqual(
                [self.productseries],
                self.ps_set.findByTranslationsImportBranch(self.branch))

    def test_findByTranslationsImportBranch_no_autoimport(self):
        self._makeSeriesAndBranch()
        self.productseries.translations_autoimport_mode = (
            TranslationsBranchImportMode.NO_IMPORT)

        self.assertContentEqual(
                [],
                self.ps_set.findByTranslationsImportBranch(self.branch))

    def test_findByTranslationsImportBranch_no_branch(self):
        self._makeSeriesAndBranch()
        self.productseries.branch = None

        self.assertContentEqual(
                [],
                self.ps_set.findByTranslationsImportBranch(self.branch))

    def test_findByTranslationsImportBranch_force_imoprt(self):
        self._makeSeriesAndBranch()
        self.productseries.translations_autoimport_mode = (
            TranslationsBranchImportMode.NO_IMPORT)

        self.assertContentEqual(
                [self.productseries],
                self.ps_set.findByTranslationsImportBranch(self.branch, True))

    def test_findByTranslationsImportBranch_multiple_series(self):
        self._makeSeriesAndBranch()
        self.productseries.translations_autoimport_mode = (
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        second_series = self.factory.makeProductSeries(
            product=self.productseries.product)
        second_series.translations_autoimport_mode = (
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        second_series.branch = self.branch

        self.assertContentEqual(
                [self.productseries, second_series],
                self.ps_set.findByTranslationsImportBranch(self.branch))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
