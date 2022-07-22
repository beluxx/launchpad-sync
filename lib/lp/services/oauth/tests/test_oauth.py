# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the OAuth database classes."""

__all__ = []

import unittest

from storm.zope.interfaces import IZStorm
from zope.component import getUtility

from lp.services.database.interfaces import MAIN_STORE, PRIMARY_FLAVOR
from lp.services.oauth.model import (
    OAuthAccessToken,
    OAuthConsumer,
    OAuthRequestToken,
)
from lp.testing.layers import DatabaseFunctionalLayer


class BaseOAuthTestCase(unittest.TestCase):
    """Base tests for the OAuth database classes."""

    layer = DatabaseFunctionalLayer

    def test__getStore_should_return_the_main_primary_store(self):
        """We want all OAuth classes to use the primary store.
        Otherwise, the OAuth exchanges will fail because the authorize
        screen won't probably find the new request token on the standby
        store.
        """
        zstorm = getUtility(IZStorm)
        self.assertEqual(
            "%s-%s" % (MAIN_STORE, PRIMARY_FLAVOR),
            zstorm.get_name(self.class_._getStore()),
        )


class OAuthAccessTokenTestCase(BaseOAuthTestCase):
    class_ = OAuthAccessToken


class OAuthRequestTokenTestCase(BaseOAuthTestCase):
    class_ = OAuthRequestToken


class OAuthConsumerTestCase(BaseOAuthTestCase):
    class_ = OAuthConsumer


def test_suite():
    return unittest.TestSuite(
        (
            unittest.makeSuite(OAuthAccessTokenTestCase),
            unittest.makeSuite(OAuthRequestTokenTestCase),
            unittest.makeSuite(OAuthConsumerTestCase),
        )
    )
