# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Launchpad specific tests of bzrlib behavior."""

__metaclass__ = type
__all__ = []

import unittest

class TestBzrlib(unittest.TestCase):
    def test_has_cextensions(self):
        """Ensure Bazaar C extensions are being used."""
        try:
            import bzrlib._dirstate_helpers_pyx
        except ImportError:
            self.fail("Bzr not built with C extensions.")


def testsuite():
    return unittest.TestLoader().loadTestsFromName(__name__)
