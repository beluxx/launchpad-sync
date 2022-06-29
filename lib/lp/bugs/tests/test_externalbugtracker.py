# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test related to ExternalBugtracker test infrastructure."""

__all__ = []

import unittest

from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.systemdocs import LayeredDocFileSuite, setUp, tearDown


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(
        LayeredDocFileSuite(
            "bugzilla-xmlrpc-transport.rst",
            setUp=setUp,
            tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
        )
    )
    suite.addTest(
        LayeredDocFileSuite(
            "bugzilla-api-xmlrpc-transport.rst",
            setUp=setUp,
            tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
        )
    )
    suite.addTest(
        LayeredDocFileSuite(
            "trac-xmlrpc-transport.rst",
            setUp=setUp,
            tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
        )
    )
    suite.addTest(
        LayeredDocFileSuite(
            "externalbugtracker-xmlrpc-transport.rst",
            setUp=setUp,
            tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
        )
    )

    return suite
