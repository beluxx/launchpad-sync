# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test IBugSubscriptionFilter adapters"""

from lp.bugs.adapters.bugsubscriptionfilter import (
    bugsubscriptionfilter_to_distribution,
    bugsubscriptionfilter_to_product,
)
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.product import IProduct
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class BugSubscriptionFilterTestCase(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_bugsubscriptionfilter_to_product_with_product(self):
        product = self.factory.makeProduct()
        subscription_filter = self.factory.makeBugSubscriptionFilter(
            target=product
        )
        self.assertEqual(
            product, bugsubscriptionfilter_to_product(subscription_filter)
        )
        self.assertEqual(product, IProduct(subscription_filter))

    def test_bugsubscriptionfilter_to_product_with_productseries(self):
        product = self.factory.makeProduct()
        series = product.development_focus
        subscription_filter = self.factory.makeBugSubscriptionFilter(
            target=series
        )
        self.assertEqual(
            product, bugsubscriptionfilter_to_product(subscription_filter)
        )
        self.assertEqual(product, IProduct(subscription_filter))

    def test_bugsubscriptionfilter_to_distribution_with_distribution(self):
        distribution = self.factory.makeDistribution()
        subscription_filter = self.factory.makeBugSubscriptionFilter(
            distribution
        )
        self.assertEqual(
            distribution,
            bugsubscriptionfilter_to_distribution(subscription_filter),
        )
        self.assertEqual(distribution, IDistribution(subscription_filter))

    def test_bugsubscriptionfilter_to_distroseries_with_distribution(self):
        distribution = self.factory.makeDistribution()
        series = self.factory.makeDistroSeries(distribution=distribution)
        subscription_filter = self.factory.makeBugSubscriptionFilter(
            target=series
        )
        self.assertEqual(
            distribution,
            bugsubscriptionfilter_to_distribution(subscription_filter),
        )
        self.assertEqual(distribution, IDistribution(subscription_filter))
