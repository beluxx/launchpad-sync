# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI.test tests."""

__metaclass__ = type
__all__ = []

from canonical.testing.layers import YUITestLayer
from lp.testing import (
    build_yui_unittest_suite,
    YUIUnitTestCase,
    )


class SoyuzYUIUnitTestCase(YUIUnitTestCase):

    layer = YUITestLayer
    suite_name = 'SoyuzYUIUnitTests'


def test_suite():
    app_testing_path = 'lp/soyuz/javascript/tests'
    return build_yui_unittest_suite(app_testing_path, SoyuzYUIUnitTestCase)
