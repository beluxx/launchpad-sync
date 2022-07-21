# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for GPG key on the web."""

from lp.services.webapp import canonical_url
from lp.testing import TestCaseWithFactory, login_person
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.views import create_initialized_view


class TestCanonicalUrl(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_canonical_url(self):
        # The canonical URL of a GPG key is ???
        person = self.factory.makePerson()
        gpgkey = self.factory.makeGPGKey(person)
        self.assertEqual(
            "%s/+gpg-keys/%s"
            % (canonical_url(person, rootsite="api"), gpgkey.fingerprint),
            canonical_url(gpgkey),
        )


class TestPersonGPGView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_edit_pgp_keys_login_redirect(self):
        """+editpgpkeys should redirect to force you to re-authenticate."""
        person = self.factory.makePerson()
        login_person(person)
        view = create_initialized_view(person, "+editpgpkeys")
        response = view.request.response
        self.assertEqual(302, response.getStatus())
        expected_url = "%s/+editpgpkeys/+login?reauth=1" % canonical_url(
            person
        )
        self.assertEqual(expected_url, response.getHeader("location"))
