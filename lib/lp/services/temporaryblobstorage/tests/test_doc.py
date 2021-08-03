# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

import os

from lp.services.testing import build_test_suite
from lp.testing.layers import LaunchpadFunctionalLayer


here = os.path.dirname(os.path.realpath(__file__))

special = {}


def test_suite():
    return build_test_suite(here, special, layer=LaunchpadFunctionalLayer)
