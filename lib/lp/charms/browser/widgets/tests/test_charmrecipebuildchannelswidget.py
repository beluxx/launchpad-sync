# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import re

from zope.formlib.interfaces import (
    IBrowserWidget,
    IInputWidget,
    )
from zope.schema import Dict

from lp.charms.browser.widgets.charmrecipebuildchannels import (
    CharmRecipeBuildChannelsWidget,
    )
from lp.charms.interfaces.charmrecipe import CHARM_RECIPE_ALLOW_CREATE
from lp.services.beautifulsoup import BeautifulSoup
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestCharmRecipeBuildChannelsWidget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestCharmRecipeBuildChannelsWidget, self).setUp()
        self.useFixture(FeatureFixture({CHARM_RECIPE_ALLOW_CREATE: "on"}))
        field = Dict(
            __name__="auto_build_channels",
            title="Source snap channels for automatic builds")
        self.context = self.factory.makeCharmRecipe()
        self.field = field.bind(self.context)
        self.request = LaunchpadTestRequest()
        self.widget = CharmRecipeBuildChannelsWidget(self.field, self.request)

    def test_implements(self):
        self.assertTrue(verifyObject(IBrowserWidget, self.widget))
        self.assertTrue(verifyObject(IInputWidget, self.widget))

    def test_template(self):
        self.assertTrue(
            self.widget.template.filename.endswith(
                "charmrecipebuildchannels.pt"),
            "Template was not set up.")

    def test_hint(self):
        self.assertEqual(
            "The channels to use for build tools when building the charm "
            "recipe.",
            self.widget.hint)

    def test_setUpSubWidgets_first_call(self):
        # The subwidgets are set up and a flag is set.
        self.widget.setUpSubWidgets()
        self.assertTrue(self.widget._widgets_set_up)
        self.assertIsNotNone(getattr(self.widget, "charmcraft_widget", None))
        self.assertIsNotNone(getattr(self.widget, "core_widget", None))
        self.assertIsNotNone(getattr(self.widget, "core18_widget", None))
        self.assertIsNotNone(getattr(self.widget, "core20_widget", None))

    def test_setUpSubWidgets_second_call(self):
        # The setUpSubWidgets method exits early if a flag is set to
        # indicate that the widgets were set up.
        self.widget._widgets_set_up = True
        self.widget.setUpSubWidgets()
        self.assertIsNone(getattr(self.widget, "charmcraft_widget", None))
        self.assertIsNone(getattr(self.widget, "core_widget", None))
        self.assertIsNone(getattr(self.widget, "core18_widget", None))
        self.assertIsNone(getattr(self.widget, "core20_widget", None))

    def test_setRenderedValue_None(self):
        self.widget.setRenderedValue(None)
        self.assertIsNone(self.widget.charmcraft_widget._getCurrentValue())
        self.assertIsNone(self.widget.core_widget._getCurrentValue())
        self.assertIsNone(self.widget.core18_widget._getCurrentValue())
        self.assertIsNone(self.widget.core20_widget._getCurrentValue())

    def test_setRenderedValue_empty(self):
        self.widget.setRenderedValue({})
        self.assertIsNone(self.widget.charmcraft_widget._getCurrentValue())
        self.assertIsNone(self.widget.core_widget._getCurrentValue())
        self.assertIsNone(self.widget.core18_widget._getCurrentValue())
        self.assertIsNone(self.widget.core20_widget._getCurrentValue())

    def test_setRenderedValue_one_channel(self):
        self.widget.setRenderedValue({"charmcraft": "stable"})
        self.assertEqual(
            "stable", self.widget.charmcraft_widget._getCurrentValue())
        self.assertIsNone(self.widget.core_widget._getCurrentValue())
        self.assertIsNone(self.widget.core18_widget._getCurrentValue())
        self.assertIsNone(self.widget.core20_widget._getCurrentValue())

    def test_setRenderedValue_all_channels(self):
        self.widget.setRenderedValue(
            {"charmcraft": "stable", "core": "candidate", "core18": "beta",
             "core20": "edge"})
        self.assertEqual(
            "stable", self.widget.charmcraft_widget._getCurrentValue())
        self.assertEqual(
            "candidate", self.widget.core_widget._getCurrentValue())
        self.assertEqual("beta", self.widget.core18_widget._getCurrentValue())
        self.assertEqual("edge", self.widget.core20_widget._getCurrentValue())

    def test_hasInput_false(self):
        # hasInput is false when there are no channels in the form data.
        self.widget.request = LaunchpadTestRequest(form={})
        self.assertFalse(self.widget.hasInput())

    def test_hasInput_true(self):
        # hasInput is true when there are channels in the form data.
        self.widget.request = LaunchpadTestRequest(
            form={"field.auto_build_channels.charmcraft": "stable"})
        self.assertTrue(self.widget.hasInput())

    def test_hasValidInput_true(self):
        # The field input is valid when all submitted channels are valid.
        # (At the moment, individual channel names are not validated, so
        # there is no "false" counterpart to this test.)
        form = {
            "field.auto_build_channels.charmcraft": "stable",
            "field.auto_build_channels.core": "",
            "field.auto_build_channels.core18": "beta",
            "field.auto_build_channels.core20": "edge",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertTrue(self.widget.hasValidInput())

    def test_getInputValue(self):
        form = {
            "field.auto_build_channels.charmcraft": "stable",
            "field.auto_build_channels.core": "",
            "field.auto_build_channels.core18": "beta",
            "field.auto_build_channels.core20": "edge",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(
            {"charmcraft": "stable", "core18": "beta", "core20": "edge"},
            self.widget.getInputValue())

    def test_call(self):
        # The __call__ method sets up the widgets.
        markup = self.widget()
        self.assertIsNotNone(self.widget.charmcraft_widget)
        self.assertIsNotNone(self.widget.core_widget)
        self.assertIsNotNone(self.widget.core18_widget)
        self.assertIsNotNone(self.widget.core20_widget)
        soup = BeautifulSoup(markup)
        fields = soup.find_all(["input"], {"id": re.compile(".*")})
        expected_ids = [
            "field.auto_build_channels.charmcraft",
            "field.auto_build_channels.core",
            "field.auto_build_channels.core18",
            "field.auto_build_channels.core20",
            ]
        ids = [field["id"] for field in fields]
        self.assertContentEqual(expected_ids, ids)
