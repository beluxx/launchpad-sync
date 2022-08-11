# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the IPerson.createPPA() method."""

from zope.security.interfaces import Unauthorized

from lp.registry.enums import PersonVisibility, TeamMembershipPolicy
from lp.registry.errors import PPACreationError
from lp.registry.interfaces.teammembership import TeamMembershipStatus
from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    TestCaseWithFactory,
    api_url,
    celebrity_logged_in,
    person_logged_in,
)
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import webservice_for_person


class TestCreatePPA(TestCaseWithFactory):
    """Test that the IPerson.createPPA method behaves as expected."""

    layer = DatabaseFunctionalLayer

    def test_default_name(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            ppa = person.createPPA()
        self.assertEqual(ppa.name, "ppa")
        self.assertEqual(2048, ppa.authorized_size)

    def test_private(self):
        with celebrity_logged_in("commercial_admin") as person:
            ppa = person.createPPA(private=True)
        self.assertEqual(True, ppa.private)

    def test_private_without_permission(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            self.assertRaises(PPACreationError, person.createPPA, private=True)

    def test_different_person(self):
        # You cannot make a PPA on another person.
        owner = self.factory.makePerson()
        creator = self.factory.makePerson()
        with person_logged_in(creator):
            self.assertRaises(Unauthorized, getattr, owner, "createPPA")

    def test_suppress_subscription_notifications(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            ppa = person.createPPA(suppress_subscription_notifications=True)
        self.assertEqual(True, ppa.suppress_subscription_notifications)

    def test_private_team_private_ppa(self):
        team_owner = self.factory.makePerson()
        private_team = self.factory.makeTeam(
            owner=team_owner,
            visibility=PersonVisibility.PRIVATE,
            membership_policy=TeamMembershipPolicy.RESTRICTED,
        )
        team_admin = self.factory.makePerson()
        with person_logged_in(team_owner):
            private_team.addMember(
                team_admin, team_owner, status=TeamMembershipStatus.ADMIN
            )
        with person_logged_in(team_admin):
            ppa = private_team.createPPA(private=True)
            self.assertEqual(True, ppa.private)
            self.assertEqual(20480, ppa.authorized_size)

    def test_webservice_accepts_multiline_description(self):
        user = self.factory.makePerson()
        endpoint = api_url(user)
        webservice = webservice_for_person(
            user,
            permission=OAuthPermission.WRITE_PUBLIC,
            default_api_version="devel",
        )

        response = webservice.named_post(
            endpoint, "createPPA", description="a\nb"
        )

        self.assertEqual(201, response.status)
