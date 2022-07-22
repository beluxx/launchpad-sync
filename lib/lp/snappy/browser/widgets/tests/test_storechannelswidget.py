# Copyright 2017-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import re

from zope.formlib.interfaces import (
    IBrowserWidget,
    IInputWidget,
    WidgetInputError,
)
from zope.schema import List

from lp.app.validators import LaunchpadValidationError
from lp.registry.enums import StoreRisk
from lp.services.beautifulsoup import BeautifulSoup
from lp.services.webapp.escaping import html_escape
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.snappy.browser.widgets.storechannels import StoreChannelsWidget
from lp.snappy.vocabularies import SnapStoreChannelVocabulary
from lp.testing import TestCaseWithFactory, verifyObject
from lp.testing.layers import DatabaseFunctionalLayer


class TestStoreChannelsWidget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        field = List(__name__="channels", title="Store channels")
        self.context = self.factory.makeSnap()
        field = field.bind(self.context)
        request = LaunchpadTestRequest()
        self.widget = StoreChannelsWidget(field, None, request)

    def test_implements(self):
        self.assertTrue(verifyObject(IBrowserWidget, self.widget))
        self.assertTrue(verifyObject(IInputWidget, self.widget))

    def test_template(self):
        self.assertTrue(
            self.widget.template.filename.endswith("storechannels.pt"),
            "Template was not set up.",
        )

    def test_setUpSubWidgets_first_call(self):
        # The subwidgets are set up and a flag is set.
        self.widget.setUpSubWidgets()
        self.assertTrue(self.widget._widgets_set_up)
        self.assertIsNotNone(getattr(self.widget, "track_widget", None))
        self.assertIsInstance(
            self.widget.risks_widget.vocabulary, SnapStoreChannelVocabulary
        )
        self.assertTrue(self.widget.has_risks_vocabulary)
        self.assertIsNotNone(getattr(self.widget, "branch_widget", None))

    def test_setUpSubWidgets_second_call(self):
        # The setUpSubWidgets method exits early if a flag is set to
        # indicate that the widgets were set up.
        self.widget._widgets_set_up = True
        self.widget.setUpSubWidgets()
        self.assertIsNone(getattr(self.widget, "track_widget", None))
        self.assertIsNone(getattr(self.widget, "risks_widget", None))
        self.assertIsNone(getattr(self.widget, "branch_widget", None))
        self.assertIsNone(self.widget.has_risks_vocabulary)

    def test_setRenderedValue_empty(self):
        self.widget.setRenderedValue([])
        self.assertIsNone(self.widget.track_widget._getCurrentValue())
        self.assertIsNone(self.widget.risks_widget._getCurrentValue())

    def test_setRenderedValue_no_track_or_branch(self):
        # Channels do not include a track or branch
        risks = ["candidate", "edge"]
        self.widget.setRenderedValue(risks)
        self.assertIsNone(self.widget.track_widget._getCurrentValue())
        self.assertEqual(risks, self.widget.risks_widget._getCurrentValue())
        self.assertIsNone(self.widget.branch_widget._getCurrentValue())

    def test_setRenderedValue_with_track(self):
        # Channels including a track
        channels = ["2.2/candidate", "2.2/edge"]
        self.widget.setRenderedValue(channels)
        self.assertEqual("2.2", self.widget.track_widget._getCurrentValue())
        self.assertEqual(
            ["candidate", "edge"], self.widget.risks_widget._getCurrentValue()
        )
        self.assertIsNone(self.widget.branch_widget._getCurrentValue())

    def test_setRenderedValue_with_branch(self):
        # Channels including a branch
        channels = ["candidate/fix-123", "edge/fix-123"]
        self.widget.setRenderedValue(channels)
        self.assertIsNone(self.widget.track_widget._getCurrentValue())
        self.assertEqual(
            ["candidate", "edge"], self.widget.risks_widget._getCurrentValue()
        )
        self.assertEqual(
            "fix-123", self.widget.branch_widget._getCurrentValue()
        )

    def test_setRenderedValue_with_track_and_branch(self):
        # Channels including a track and branch
        channels = ["2.2/candidate/fix-123", "2.2/edge/fix-123"]
        self.widget.setRenderedValue(channels)
        self.assertEqual("2.2", self.widget.track_widget._getCurrentValue())
        self.assertEqual(
            ["candidate", "edge"], self.widget.risks_widget._getCurrentValue()
        )
        self.assertEqual(
            "fix-123", self.widget.branch_widget._getCurrentValue()
        )

    def test_setRenderedValue_invalid_value(self):
        # Multiple channels, different tracks or branches, unsupported
        self.assertRaisesWithContent(
            ValueError,
            "Channels belong to different tracks: "
            "['2.2/candidate', '2.1/edge']",
            self.widget.setRenderedValue,
            ["2.2/candidate", "2.1/edge"],
        )
        self.assertRaisesWithContent(
            ValueError,
            "Channels belong to different branches: "
            "['candidate/fix-123', 'edge/fix-124']",
            self.widget.setRenderedValue,
            ["candidate/fix-123", "edge/fix-124"],
        )
        self.assertRaisesWithContent(
            ValueError,
            "Channels belong to different tracks: "
            "['2.2/candidate', 'edge/fix-123']",
            self.widget.setRenderedValue,
            ["2.2/candidate", "edge/fix-123"],
        )

    def test_hasInput_false(self):
        # hasInput is false when there is no risk set in the form data.
        self.widget.request = LaunchpadTestRequest(
            form={"field.channels.track": "track"}
        )
        self.assertFalse(self.widget.hasInput())

    def test_hasInput_true(self):
        # hasInput is true if there are risks set in the form data.
        self.widget.request = LaunchpadTestRequest(
            form={"field.channels.risks": ["beta"]}
        )
        self.assertTrue(self.widget.hasInput())

    def test_hasValidInput_false(self):
        # The field input is invalid if any of the submitted parts are
        # invalid.
        form = {
            "field.channels.track": "",
            "field.channels.risks": ["invalid"],
            "field.channels.branch": "",
        }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertFalse(self.widget.hasValidInput())

    def test_hasValidInput_true(self):
        # The field input is valid when all submitted parts are valid.
        form = {
            "field.channels.track": "track",
            "field.channels.risks": ["stable", "beta"],
            "field.channels.branch": "branch",
        }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertTrue(self.widget.hasValidInput())

    def assertGetInputValueError(self, form, message):
        self.widget.request = LaunchpadTestRequest(form=form)
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)
        self.assertEqual(html_escape(message), self.widget.error())

    def test_getInputValue_invalid_track(self):
        # An error is raised when the track includes a '/'.
        form = {
            "field.channels.track": "tra/ck",
            "field.channels.risks": ["beta"],
            "field.channels.branch": "",
        }
        self.assertGetInputValueError(form, "Track name cannot include '/'.")

    def test_getInputValue_invalid_branch(self):
        # An error is raised when the branch includes a '/'.
        form = {
            "field.channels.track": "",
            "field.channels.risks": ["beta"],
            "field.channels.branch": "bra/nch",
        }
        self.assertGetInputValueError(form, "Branch name cannot include '/'.")

    def test_getInputValue_no_track_or_branch(self):
        self.widget.request = LaunchpadTestRequest(
            form={
                "field.channels.track": "",
                "field.channels.risks": ["beta", "edge"],
                "field.channels.branch": "",
            }
        )
        expected = ["beta", "edge"]
        self.assertEqual(expected, self.widget.getInputValue())

    def test_getInputValue_with_track(self):
        self.widget.request = LaunchpadTestRequest(
            form={
                "field.channels.track": "track",
                "field.channels.risks": ["beta", "edge"],
                "field.channels.branch": "",
            }
        )
        expected = ["track/beta", "track/edge"]
        self.assertEqual(expected, self.widget.getInputValue())

    def test_getInputValue_with_branch(self):
        self.widget.request = LaunchpadTestRequest(
            form={
                "field.channels.track": "",
                "field.channels.risks": ["beta", "edge"],
                "field.channels.branch": "fix-123",
            }
        )
        expected = ["beta/fix-123", "edge/fix-123"]
        self.assertEqual(expected, self.widget.getInputValue())

    def test_getInputValue_with_track_and_branch(self):
        self.widget.request = LaunchpadTestRequest(
            form={
                "field.channels.track": "track",
                "field.channels.risks": ["beta", "edge"],
                "field.channels.branch": "fix-123",
            }
        )
        expected = ["track/beta/fix-123", "track/edge/fix-123"]
        self.assertEqual(expected, self.widget.getInputValue())

    def test_call(self):
        # The __call__ method sets up the widgets.
        markup = self.widget()
        self.assertIsNotNone(self.widget.track_widget)
        self.assertIsNotNone(self.widget.risks_widget)
        soup = BeautifulSoup(markup)
        fields = soup.find_all(["input"], {"id": re.compile(".*")})
        expected_ids = [
            "field.channels.risks.%d" % i for i in range(len(StoreRisk))
        ]
        expected_ids.append("field.channels.track")
        expected_ids.append("field.channels.branch")
        ids = [field["id"] for field in fields]
        self.assertContentEqual(expected_ids, ids)
