# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

import os

from zope.security.management import setSecurityPolicy

from lp.services.testing import build_test_suite
from lp.services.webapp.authorization import LaunchpadSecurityPolicy
from lp.testing.dbuser import switch_dbuser
from lp.testing.layers import LaunchpadFunctionalLayer, LaunchpadZopelessLayer
from lp.testing.systemdocs import (
    LayeredDocFileSuite,
    setGlobs,
    setUp,
    tearDown,
)

here = os.path.dirname(os.path.realpath(__file__))


def branchscannerSetUp(test):
    """Setup the user for the branch scanner tests."""
    switch_dbuser("branchscanner")
    setUp(test)


def zopelessLaunchpadSecuritySetUp(test):
    """Set up a LaunchpadZopelessLayer test to use LaunchpadSecurityPolicy.

    To be able to use switch_dbuser in a test, we need to run in the
    Zopeless environment. The Zopeless environment normally runs using the
    LaunchpadPermissiveSecurityPolicy. If we want the test to cover
    functionality used in the webapp, it needs to use the
    LaunchpadSecurityPolicy.
    """
    setGlobs(test)
    test.old_security_policy = setSecurityPolicy(LaunchpadSecurityPolicy)


def zopelessLaunchpadSecurityTearDown(test):
    setSecurityPolicy(test.old_security_policy)


special = {
    "codeimport-machine.rst": LayeredDocFileSuite(
        "../doc/codeimport-machine.rst",
        setUp=zopelessLaunchpadSecuritySetUp,
        tearDown=zopelessLaunchpadSecurityTearDown,
        layer=LaunchpadZopelessLayer,
    ),
    "revision.rst": LayeredDocFileSuite(
        "../doc/revision.rst",
        setUp=branchscannerSetUp,
        tearDown=tearDown,
        layer=LaunchpadZopelessLayer,
    ),
    "codeimport-result.rst": LayeredDocFileSuite(
        "../doc/codeimport-result.rst",
        setUp=setUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer,
    ),
    "branch-merge-proposal-notifications.rst": LayeredDocFileSuite(
        "../doc/branch-merge-proposal-notifications.rst",
        setUp=setUp,
        tearDown=tearDown,
        layer=LaunchpadZopelessLayer,
    ),
    "branch-notifications.rst": LayeredDocFileSuite(
        "../doc/branch-notifications.rst",
        setUp=setUp,
        tearDown=tearDown,
        layer=LaunchpadZopelessLayer,
    ),
    "codereviewcomment.rst": LayeredDocFileSuite(
        "../doc/codereviewcomment.rst",
        setUp=setUp,
        tearDown=tearDown,
        layer=LaunchpadZopelessLayer,
    ),
}


def test_suite():
    return build_test_suite(here, special)
