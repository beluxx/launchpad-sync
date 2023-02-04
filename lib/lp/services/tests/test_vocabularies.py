# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test registered vocabularies."""

__all__ = []

from zope.component import getUtilitiesFor
from zope.proxy import isProxy
from zope.schema.interfaces import IVocabularyFactory

from lp.testing import TestCase
from lp.testing.layers import FunctionalLayer


class TestVocabularies(TestCase):
    layer = FunctionalLayer

    def test_security_proxy(self):
        """Our vocabularies should be registered with <lp:securedutility>."""
        vocabularies = getUtilitiesFor(IVocabularyFactory)
        for name, vocab in vocabularies:
            # If the vocabulary is not in a security proxy, check
            # whether it is a vocabulary defined by zope, which are
            # not registered with <lp:securedutility> and can be ignored.
            if not isProxy(vocab) and vocab.__module__[:5] != "zope.":
                raise AssertionError(
                    "%s.%s vocabulary is not wrapped in a security proxy."
                    % (vocab.__module__, name)
                )
