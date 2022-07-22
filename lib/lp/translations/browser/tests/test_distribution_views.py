# Copyright 2011-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the translations views on a distroseries."""

from fixtures import FakeLogger
from zope.security.interfaces import Unauthorized

from lp.services.webapp import canonical_url
from lp.testing import TestCaseWithFactory, person_logged_in
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.views import create_initialized_view


class TestDistributionSettingsView(TestCaseWithFactory):
    """Test distribution settings (+configure-translations) view."""

    layer = LaunchpadFunctionalLayer

    def test_only_translation_fields(self):
        # No fields other than translation fields are shown
        # in the distribution translation settings form view.
        distribution = self.factory.makeDistribution()
        view = create_initialized_view(
            distribution, "+configure-translations", rootsite="translations"
        )
        self.assertContentEqual(
            [
                "translations_usage",
                "translation_focus",
                "translationgroup",
                "translationpermission",
            ],
            view.field_names,
        )

    def test_unprivileged_users(self):
        # Unprivileged users cannot access distribution translation settings
        # page Distribution:+configure-translations.
        self.useFixture(FakeLogger())
        unprivileged = self.factory.makePerson()
        distribution = self.factory.makeDistribution()
        url = canonical_url(
            distribution,
            view_name="+configure-translations",
            rootsite="translations",
        )
        browser = self.getUserBrowser(user=unprivileged)
        self.assertRaises(Unauthorized, browser.open, url)

    def test_translation_group_owner(self):
        # Translation group owner for a particular distribution has
        # launchpad.TranslationsAdmin privileges on it, meaning they
        # can access Distribution:+configure-translations page.
        group = self.factory.makeTranslationGroup()
        distribution = self.factory.makeDistribution()
        with person_logged_in(distribution.owner):
            distribution.translationgroup = group
        url = canonical_url(
            distribution,
            view_name="+configure-translations",
            rootsite="translations",
        )
        browser = self.getUserBrowser(user=group.owner)
        # No "Unauthorized" exception is thrown.
        browser.open(url)

    def test_distribution_owner(self):
        # Distribution owner of a particular distribution has
        # launchpad.TranslationsAdmin privileges on it, meaning they
        # can access Distribution:+configure-translations page.
        distribution = self.factory.makeDistribution()
        url = canonical_url(
            distribution,
            view_name="+configure-translations",
            rootsite="translations",
        )
        browser = self.getUserBrowser(user=distribution.owner)
        # No "Unauthorized" exception is thrown.
        browser.open(url)
