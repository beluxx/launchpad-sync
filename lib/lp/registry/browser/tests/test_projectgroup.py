# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for project group views."""

__metaclass__ = type

from fixtures import FakeLogger
from lazr.restful.interfaces import IJSONRequestCache
from testtools.matchers import Not
from zope.component import getUtility
from zope.schema.vocabulary import SimpleVocabulary
from zope.security.interfaces import Unauthorized

from lp.app.browser.lazrjs import vocabulary_to_choice_edit_items
from lp.app.enums import InformationType
from lp.registry.browser.tests.test_product import make_product_form
from lp.registry.enums import EXCLUSIVE_TEAM_POLICY
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProductSet
from lp.services.features.testing import FeatureFixture
from lp.services.webapp import canonical_url
from lp.services.webapp.interfaces import ILaunchBag
from lp.testing import (
    celebrity_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import Contains
from lp.testing.sampledata import ADMIN_EMAIL
from lp.testing.views import create_initialized_view


class TestProjectGroupView(TestCaseWithFactory):
    """Tests the +index view."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProjectGroupView, self).setUp()
        self.project_group = self.factory.makeProject(name='group')

    def test_view_data_model(self):
        # The view's json request cache contains the expected data.
        view = create_initialized_view(self.project_group, '+index')
        cache = IJSONRequestCache(view.request)
        policy_items = [(item.name, item) for item in EXCLUSIVE_TEAM_POLICY]
        team_membership_policy_data = vocabulary_to_choice_edit_items(
            SimpleVocabulary.fromItems(policy_items),
            value_fn=lambda item: item.name)
        self.assertContentEqual(
            team_membership_policy_data,
            cache.objects['team_membership_policy_data'])


class TestProjectGroupEditView(TestCaseWithFactory):
    """Tests the edit view."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProjectGroupEditView, self).setUp()
        self.project_group = self.factory.makeProject(name='group')
        # Use a FakeLogger fixture to prevent Memcached warnings to be
        # printed to stdout while browsing pages.
        self.useFixture(FakeLogger())

    def test_links_admin(self):
        # An admin can change details and administer a project group.
        with celebrity_logged_in('admin'):
            user = getUtility(ILaunchBag).user
            view = create_initialized_view(
                self.project_group, '+index', principal=user)
            contents = view.render()
            self.assertThat(contents, Contains("Change details"))
            self.assertThat(contents, Contains("Administer"))

    def test_links_registry_expert(self):
        # A registry expert cannot change details but can administer a project
        # group.
        with celebrity_logged_in('registry_experts'):
            user = getUtility(ILaunchBag).user
            view = create_initialized_view(
                self.project_group, '+index', principal=user)
            contents = view.render()
            self.assertThat(contents, Not(Contains("Change details")))
            self.assertThat(contents, Contains("Administer"))

    def test_links_owner(self):
        # An owner can change details but not administer a project group.
        with person_logged_in(self.project_group.owner):
            user = getUtility(ILaunchBag).user
            view = create_initialized_view(
                self.project_group, '+index', principal=user)
            contents = view.render()
            self.assertThat(contents, Contains("Change details"))
            self.assertThat(contents, Not(Contains("Administer")))

    def test_edit_view_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        browser = self.getUserBrowser(user=admin)
        browser.open(canonical_url(self.project_group, view_name='+edit'))
        browser.open(canonical_url(self.project_group, view_name='+review'))

    def test_edit_view_registry_expert(self):
        registry_expert = self.factory.makeRegistryExpert()
        browser = self.getUserBrowser(user=registry_expert)
        url = canonical_url(self.project_group, view_name='+edit')
        self.assertRaises(Unauthorized, browser.open, url)
        browser.open(canonical_url(self.project_group, view_name='+review'))

    def test_edit_view_owner(self):
        browser = self.getUserBrowser(user=self.project_group.owner)
        browser.open(canonical_url(self.project_group, view_name='+edit'))
        url = canonical_url(self.project_group, view_name='+review')
        self.assertRaises(Unauthorized, browser.open, url)


class TestProjectGroupAddProductViews(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_information_type(self):
        # Information type controls are provided when creating a project via a
        # project group.
        self.useFixture(
            FeatureFixture({u'disclosure.private_projects.enabled': u'on'}))
        form = make_product_form(action=1)
        project = self.factory.makeProject()
        with person_logged_in(project.owner):
            view = create_initialized_view(project, '+newproduct', form=form)
        self.assertIn('information_type_data',
                      IJSONRequestCache(view.request).objects)
        self.assertIsNot(None, view.view.form_fields.get('information_type'))

    def test_information_type_saved(self):
        # Setting information_type to PROPRIETARY via form actually works.
        self.useFixture(
            FeatureFixture({u'disclosure.private_projects.enabled': u'on'}))
        project = self.factory.makeProject()
        form = make_product_form(project.owner, action=2, proprietary=True)
        with person_logged_in(project.owner):
            view = create_initialized_view(project, '+newproduct', form=form)
        self.assertEqual(0, len(view.view.errors))
        product = getUtility(IProductSet).getByName(form['field.name'])
        self.assertEqual(InformationType.PROPRIETARY, product.information_type)
