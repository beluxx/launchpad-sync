# Copyright 2018-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import re

from zope.formlib.interfaces import (
    IBrowserWidget,
    IInputWidget,
    )
from zope.schema import Dict

from lp.services.beautifulsoup import BeautifulSoup
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.snappy.browser.widgets.snapbuildchannels import (
    SnapBuildChannelsWidget,
    )
from lp.snappy.interfaces.snap import SNAP_SNAPCRAFT_CHANNEL_FEATURE_FLAG
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestSnapBuildChannelsWidget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapBuildChannelsWidget, self).setUp()
        field = Dict(
            __name__="auto_build_channels",
            title="Source snap channels for automatic builds")
        self.context = self.factory.makeSnap()
        self.field = field.bind(self.context)
        self.request = LaunchpadTestRequest()
        self.widget = SnapBuildChannelsWidget(self.field, self.request)

    def test_implements(self):
        self.assertTrue(verifyObject(IBrowserWidget, self.widget))
        self.assertTrue(verifyObject(IInputWidget, self.widget))

    def test_template(self):
        self.assertTrue(
            self.widget.template.filename.endswith("snapbuildchannels.pt"),
            "Template was not set up.")

    def test_hint_no_feature_flag(self):
        self.assertEqual(
            'The channels to use for build tools when building the snap '
            'package.\n'
            'If unset, or if the channel for snapcraft is set to "apt", '
            'the default is to install snapcraft from the source archive '
            'using apt.',
            self.widget.hint)

    def test_hint_feature_flag_apt(self):
        self.useFixture(
            FeatureFixture({SNAP_SNAPCRAFT_CHANNEL_FEATURE_FLAG: "apt"}))
        widget = SnapBuildChannelsWidget(self.field, self.request)
        self.assertEqual(
            'The channels to use for build tools when building the snap '
            'package.\n'
            'If unset, or if the channel for snapcraft is set to "apt", '
            'the default is to install snapcraft from the source archive '
            'using apt.',
            widget.hint)

    def test_hint_feature_flag_real_channel(self):
        self.useFixture(
            FeatureFixture({SNAP_SNAPCRAFT_CHANNEL_FEATURE_FLAG: "stable"}))
        widget = SnapBuildChannelsWidget(self.field, self.request)
        self.assertEqual(
            'The channels to use for build tools when building the snap '
            'package.\n'
            'If unset, the default is to install snapcraft from the "stable" '
            'channel.  Setting the channel for snapcraft to "apt" causes '
            'snapcraft to be installed from the source archive using '
            'apt.',
            widget.hint)

    def test_setUpSubWidgets_first_call(self):
        # The subwidgets are set up and a flag is set.
        self.widget.setUpSubWidgets()
        self.assertTrue(self.widget._widgets_set_up)
        self.assertIsNotNone(getattr(self.widget, "core_widget", None))
        self.assertIsNotNone(getattr(self.widget, "core18_widget", None))
        self.assertIsNotNone(getattr(self.widget, "core20_widget", None))
        self.assertIsNotNone(getattr(self.widget, "snapcraft_widget", None))

    def test_setUpSubWidgets_second_call(self):
        # The setUpSubWidgets method exits early if a flag is set to
        # indicate that the widgets were set up.
        self.widget._widgets_set_up = True
        self.widget.setUpSubWidgets()
        self.assertIsNone(getattr(self.widget, "core_widget", None))
        self.assertIsNone(getattr(self.widget, "core18_widget", None))
        self.assertIsNone(getattr(self.widget, "core20_widget", None))
        self.assertIsNone(getattr(self.widget, "snapcraft_widget", None))

    def test_setRenderedValue_None(self):
        self.widget.setRenderedValue(None)
        self.assertIsNone(self.widget.core_widget._getCurrentValue())
        self.assertIsNone(self.widget.core18_widget._getCurrentValue())
        self.assertIsNone(self.widget.core20_widget._getCurrentValue())
        self.assertIsNone(self.widget.snapcraft_widget._getCurrentValue())

    def test_setRenderedValue_empty(self):
        self.widget.setRenderedValue({})
        self.assertIsNone(self.widget.core_widget._getCurrentValue())
        self.assertIsNone(self.widget.core18_widget._getCurrentValue())
        self.assertIsNone(self.widget.core20_widget._getCurrentValue())
        self.assertIsNone(self.widget.snapcraft_widget._getCurrentValue())

    def test_setRenderedValue_one_channel(self):
        self.widget.setRenderedValue({"snapcraft": "stable"})
        self.assertIsNone(self.widget.core_widget._getCurrentValue())
        self.assertIsNone(self.widget.core18_widget._getCurrentValue())
        self.assertIsNone(self.widget.core20_widget._getCurrentValue())
        self.assertEqual(
            "stable", self.widget.snapcraft_widget._getCurrentValue())

    def test_setRenderedValue_all_channels(self):
        self.widget.setRenderedValue(
            {"core": "candidate", "core18": "beta", "core20": "edge",
             "snapcraft": "stable"})
        self.assertEqual(
            "candidate", self.widget.core_widget._getCurrentValue())
        self.assertEqual("beta", self.widget.core18_widget._getCurrentValue())
        self.assertEqual("edge", self.widget.core20_widget._getCurrentValue())
        self.assertEqual(
            "stable", self.widget.snapcraft_widget._getCurrentValue())

    def test_hasInput_false(self):
        # hasInput is false when there are no channels in the form data.
        self.widget.request = LaunchpadTestRequest(form={})
        self.assertFalse(self.widget.hasInput())

    def test_hasInput_true(self):
        # hasInput is true when there are channels in the form data.
        self.widget.request = LaunchpadTestRequest(
            form={"field.auto_build_channels.snapcraft": "stable"})
        self.assertTrue(self.widget.hasInput())

    def test_hasValidInput_true(self):
        # The field input is valid when all submitted channels are valid.
        # (At the moment, individual channel names are not validated, so
        # there is no "false" counterpart to this test.)
        form = {
            "field.auto_build_channels.core": "",
            "field.auto_build_channels.core18": "beta",
            "field.auto_build_channels.core20": "edge",
            "field.auto_build_channels.snapcraft": "stable",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertTrue(self.widget.hasValidInput())

    def test_getInputValue(self):
        form = {
            "field.auto_build_channels.core": "",
            "field.auto_build_channels.core18": "beta",
            "field.auto_build_channels.core20": "edge",
            "field.auto_build_channels.snapcraft": "stable",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(
            {"core18": "beta", "core20": "edge",
             "snapcraft": "stable"},
            self.widget.getInputValue())

    def test_call(self):
        # The __call__ method sets up the widgets.
        markup = self.widget()
        self.assertIsNotNone(self.widget.core_widget)
        self.assertIsNotNone(self.widget.core18_widget)
        self.assertIsNotNone(self.widget.core20_widget)
        self.assertIsNotNone(self.widget.snapcraft_widget)
        soup = BeautifulSoup(markup)
        fields = soup.find_all(["input"], {"id": re.compile(".*")})
        expected_ids = [
            "field.auto_build_channels.core",
            "field.auto_build_channels.core18",
            "field.auto_build_channels.core20",
            "field.auto_build_channels.snapcraft",
            ]
        ids = [field["id"] for field in fields]
        self.assertContentEqual(expected_ids, ids)
