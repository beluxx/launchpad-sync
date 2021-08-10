# Copyright 2010-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Code of Conduct views."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testtools.matchers import MatchesRegex
from zope.component import getUtility

from lp.registry.interfaces.codeofconduct import (
    ICodeOfConductSet,
    ISignedCodeOfConductSet,
    )
from lp.registry.model.codeofconduct import SignedCodeOfConduct
from lp.testing import (
    BrowserTestCase,
    login_celebrity,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class TestSignedCodeOfConductAckView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSignedCodeOfConductAckView, self).setUp()
        self.signed_coc_set = getUtility(ISignedCodeOfConductSet)
        self.owner = self.factory.makePerson()
        self.admin = login_celebrity('admin')

    def test_view_properties(self):
        view = create_initialized_view(self.signed_coc_set, name="+new")
        self.assertEqual(
            'Register a code of conduct signature', view.label)
        self.assertEqual(view.label, view.page_title)
        self.assertEqual(['owner'], view.field_names)
        url = 'http://launchpad.test/codeofconduct/console'
        self.assertEqual(url, view.next_url)
        self.assertEqual(url, view.cancel_url)

    def test_register_coc_signed_on_paper(self):
        form = {
            'field.owner': self.owner.name,
            'field.actions.add': 'Register',
            }
        view = create_initialized_view(
            self.signed_coc_set, name="+new", form=form,
            principal=self.admin)
        self.assertEqual([], view.errors)
        results = self.signed_coc_set.searchByUser(self.owner)
        self.assertEqual(1, results.count())
        signed_coc = results[0]
        self.assertEqual(self.admin, signed_coc.recipient)


class SignCodeOfConductTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(SignCodeOfConductTestCase, self).setUp()
        user = self.factory.makePerson()
        gpg_key = self.factory.makeGPGKey(user)
        self.signed_coc = self.sign_coc(user, gpg_key)
        self.admin = login_celebrity('admin')

    def sign_coc(self, user, gpg_key):
        """Return a SignedCodeOfConduct using dummy text."""
        signed_coc = SignedCodeOfConduct(
            owner=user, signing_key_fingerprint=gpg_key.fingerprint,
            signedcode="Dummy CoC signed text.", active=True)
        return signed_coc

    def verify_common_view_properties(self, view):
        self.assertEqual(['admincomment'], view.field_names)
        self.assertEqual(
            view.page_title, view.label)
        url = 'http://launchpad.test/codeofconduct/console/%d' % (
            self.signed_coc.id)
        self.assertEqual(url, view.next_url)
        self.assertEqual(url, view.cancel_url)

    def verify_admincomment_required(self, action_name, view_name):
        # Empty comments are not permitted for any state change.
        form = {
            'field.admincomment': '',
            'field.actions.change': action_name,
            }
        view = create_initialized_view(
            self.signed_coc, name=view_name, form=form,
            principal=self.admin)
        self.assertEqual(1, len(view.errors))
        self.assertEqual('admincomment', view.errors[0].field_name)


class TestSignedCodeOfConductActiveView(SignCodeOfConductTestCase):

    def test_view_properties(self):
        self.signed_coc.active = False
        view = create_initialized_view(self.signed_coc, name="+activate")
        self.assertEqual(
            'Activate code of conduct signature', view.label)
        self.assertTrue(view.state)
        self.verify_common_view_properties(view)

    def test_activate(self):
        self.signed_coc.active = False
        form = {
            'field.admincomment': 'The user is sorry.',
            'field.actions.change': 'Activate',
            }
        view = create_initialized_view(
            self.signed_coc, name="+activate", form=form,
            principal=self.admin)
        self.assertEqual([], view.errors)
        self.assertTrue(self.signed_coc.active)
        self.assertEqual(self.admin, self.signed_coc.recipient)
        self.assertEqual(
            'The user is sorry.', self.signed_coc.admincomment)

    def test_admincomment_required(self):
        self.verify_admincomment_required('Activate', '+activate')


class TestSignedCodeOfConductDeactiveView(SignCodeOfConductTestCase):

    def test_view_properties(self):
        self.signed_coc.active = True
        view = create_initialized_view(self.signed_coc, name="+deactivate")
        self.assertEqual(
            'Deactivate code of conduct signature', view.label)
        self.assertFalse(view.state)
        self.verify_common_view_properties(view)

    def test_deactivate(self):
        self.signed_coc.active = True
        form = {
            'field.admincomment': 'The user is bad.',
            'field.actions.change': 'Deactivate',
            }
        view = create_initialized_view(
            self.signed_coc, name="+deactivate", form=form,
            principal=self.admin)
        self.assertEqual([], view.errors)
        self.assertFalse(self.signed_coc.active)
        self.assertEqual(
            'The user is bad.', self.signed_coc.admincomment)

    def test_admincomment_required(self):
        self.verify_admincomment_required('Deactivate', '+deactivate')


class TestCodeOfConductBrowser(BrowserTestCase):
    """Test the download view for the CoC."""

    layer = DatabaseFunctionalLayer

    def test_response(self):
        """Ensure the headers and body are as expected."""
        coc = getUtility(ICodeOfConductSet)['2.0']
        content = coc.content
        browser = self.getViewBrowser(coc, '+download')
        self.assertEqual(content, browser.contents)
        self.assertEqual(str(len(content)), browser.headers['Content-length'])
        disposition = 'attachment; filename="UbuntuCodeofConduct-2.0.txt"'
        self.assertEqual(disposition, browser.headers['Content-disposition'])
        self.assertThat(
            browser.headers['Content-type'],
            MatchesRegex(r'^text/plain;charset="?utf-8"?$'))


class TestAffirmCodeOfConductView(BrowserTestCase):
    """Test the affirmation view for the CoC"""

    layer = DatabaseFunctionalLayer

    def test_affirm(self):
        """Check we can affirm a CoC"""
        user = self.factory.makePerson()
        name = user.name
        displayname = user.displayname
        coc = getUtility(ICodeOfConductSet)['2.0']
        content = coc.content
        browser = self.getViewBrowser(coc, "+affirm", user=user)
        self.assertIn(content, browser.contents)
        browser.getControl('I agree to this Code of Conduct').click()
        browser.getControl('Affirm').click()
        self.assertEqual(
            "http://launchpad.test/~{}/+codesofconduct".format(name),
            browser.url)
        self.assertIn(
            "affirmed by {}".format(displayname),
            browser.contents)
