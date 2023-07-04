# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for webapp glue."""

from lp.services.features import getFeatureFlag, webapp
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.errorlog import globalErrorUtility
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    CaptureOops,
    TestCase,
    TestCaseWithFactory,
    layers,
    login_as,
)


class TestScopesFromRequest(TestCase):
    layer = layers.BaseLayer

    def test_pageid_scope_normal(self):
        request = LaunchpadTestRequest()
        scopes = webapp.ScopesFromRequest(request)
        request.setInWSGIEnvironment("launchpad.pageid", "foo:bar")
        self.assertTrue(scopes.lookup("pageid:"))
        self.assertTrue(scopes.lookup("pageid:foo"))
        self.assertTrue(scopes.lookup("pageid:foo:bar"))
        self.assertFalse(scopes.lookup("pageid:foo:bar#quux"))

    def test_pageid_scope_collection(self):
        request = LaunchpadTestRequest()
        scopes = webapp.ScopesFromRequest(request)
        request.setInWSGIEnvironment("launchpad.pageid", "scoped:thing:#type")
        self.assertTrue(scopes.lookup("pageid:"))
        self.assertTrue(scopes.lookup("pageid:scoped"))
        self.assertTrue(scopes.lookup("pageid:scoped:thing"))
        self.assertTrue(scopes.lookup("pageid:scoped:thing:#type"))
        self.assertFalse(scopes.lookup("pageid:scoped:thing:#type:other"))

    def test_pageid_scope_empty(self):
        request = LaunchpadTestRequest()
        scopes = webapp.ScopesFromRequest(request)
        request.setInWSGIEnvironment("launchpad.pageid", "")
        self.assertTrue(scopes.lookup("pageid:"))
        self.assertFalse(scopes.lookup("pageid:foo"))
        self.assertFalse(scopes.lookup("pageid:foo:bar"))

    def test_default(self):
        request = LaunchpadTestRequest()
        scopes = webapp.ScopesFromRequest(request)
        self.assertTrue(scopes.lookup("default"))

    def test_unknown_scope(self):
        # Asking about an unknown scope is not an error.
        request = LaunchpadTestRequest()
        scopes = webapp.ScopesFromRequest(request)
        scopes.lookup("not-a-real-scope")


class TestDBScopes(TestCaseWithFactory):
    layer = layers.DatabaseFunctionalLayer

    def test_team_scope_outside_team(self):
        request = LaunchpadTestRequest()
        scopes = webapp.ScopesFromRequest(request)
        self.factory.loginAsAnyone(request)
        self.assertFalse(scopes.lookup("team:nonexistent"))

    def test_team_scope_in_team(self):
        request = LaunchpadTestRequest()
        scopes = webapp.ScopesFromRequest(request)
        member = self.factory.makePerson()
        team = self.factory.makeTeam(members=[member])
        login_as(member, request)
        self.assertTrue(scopes.lookup("team:%s" % team.name))


class TestFeaturesIntoOops(TestCaseWithFactory):
    layer = layers.DatabaseFunctionalLayer

    def test_get_features_into_oops(self):
        with FeatureFixture({"feature_name": "value"}):
            with CaptureOops() as capture:
                request = LaunchpadTestRequest()

                self.assertEqual(getFeatureFlag("feature_name"), "value")

                # Simulate an oops here.
                globalErrorUtility.raising(None, request=request)

                oops = capture.oopses[0]
                self.assertTrue("features.usedScopes" in oops)
                self.assertTrue("features.usedFlags" in oops)
                self.assertEqual(
                    oops["features.usedFlags"],
                    "%r" % {"feature_name": "value"},
                )
