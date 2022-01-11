# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the testing module."""

import os

from lp.services.config import config
from lp.services.features import (
    getFeatureFlag,
    uninstall_feature_controller,
    )
from lp.testing import (
    feature_flags,
    set_feature_flag,
    TestCase,
    YUIUnitTestCase,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestFeatureFlags(TestCase):

    layer = DatabaseFunctionalLayer

    def test_set_feature_flags_raises_if_not_available(self):
        """set_feature_flags raises an error if there is no feature
        controller available for the current thread.
        """
        # Remove any existing feature controller for the sake of this
        # test (other tests will re-add it). This prevents weird
        # interactions in a parallel test environment.
        uninstall_feature_controller()
        self.assertRaises(AssertionError, set_feature_flag, 'name', 'value')

    def test_flags_set_within_feature_flags_context(self):
        """In the feature_flags context, set/get works."""
        self.useContext(feature_flags())
        set_feature_flag('name', 'value')
        self.assertEqual('value', getFeatureFlag('name'))

    def test_flags_unset_outside_feature_flags_context(self):
        """get fails when used outside the feature_flags context."""
        with feature_flags():
            set_feature_flag('name', 'value')
        self.assertIs(None, getFeatureFlag('name'))


class TestYUIUnitTestCase(TestCase):

    def test_id(self):
        test = YUIUnitTestCase()
        test.initialize("foo/bar/baz.html")
        self.assertEqual(test.test_path, test.id())

    def test_id_is_normalized_and_relative_to_root(self):
        test = YUIUnitTestCase()
        test_path = os.path.join(config.root, "../bar/baz/../bob.html")
        test.initialize(test_path)
        self.assertEqual("../bar/bob.html", test.id())
