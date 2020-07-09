# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests.
"""

import os

from lp.services.testing import build_test_suite
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.systemdocs import setUp


here = os.path.dirname(os.path.realpath(__file__))


def test_suite():
    suite = build_test_suite(
        here, {}, setUp=lambda test: setUp(test, future=True),
        layer=DatabaseFunctionalLayer)
    return suite
