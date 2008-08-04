# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for the private MailingList API."""

__metaclass__ = type
__all__ = []


import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import login, login_person, ANONYMOUS, logout
from canonical.launchpad.ftests.mailinglists_helper import (
    new_person, new_team)
from canonical.launchpad.xmlrpc.mailinglist import (
    MailingListAPIView, BYUSER, ENABLED)
from canonical.testing import LaunchpadFunctionalLayer


class MailingListAPITestCase(unittest.TestCase):
    """Tests for MailingListAPIView."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Create a team with a list and subscribe self.member to it."""
        login('foo.bar@canonical.com')
        self.team, self.mailing_list = new_team('team-a', with_list=True)
        self.member = new_person('Bob')
        self.member.join(self.team)
        self.mailing_list.subscribe(self.member)
        self.api = MailingListAPIView(None, None)

    def tearDown(self):
        logout()

    def test_getMembershipInformation_with_hidden_email(self):
        """Verify that hidden email addresses are still reported correctly."""
        login_person(self.member)
        self.member.hide_email_addresses = True

        # API runs without a logged in user.
        login(ANONYMOUS)
        self.assertEquals(
            {'team-a': [
                ('archive@mail-archive.dev', '', 0, ENABLED),
                ('bob.person@example.com', 'Bob Person', 0, ENABLED),
                ('bperson@example.org', u'Bob Person', 0, BYUSER),
                ]
            }, self.api.getMembershipInformation([self.team.name]))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
