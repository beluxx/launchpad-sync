# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Bug subscription-related email tests."""

from unittest import TestLoader

import transaction

from canonical.testing import DatabaseFunctionalLayer

from lp.services.mail import stub
from lp.testing import TestCaseWithFactory


class TestSubscribedBySomeoneElseNotification(TestCaseWithFactory):
    """Test emails sent when subscribed by someone else."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Run the tests as a logged-in user.
        TestCaseWithFactory.setUp(self, user='test@canonical.com')

    def test_subscribed_by_someone_else_with_notification(self):
        """Test notifications are sent when suppress_notify is False."""
        bug = self.factory.makeBug()
        person_subscribing = self.factory.makePerson()
        person_subscribed = self.factory.makePerson()
        # There are no email notifications before subscribing.
        self.assertEqual(len(stub.test_emails), 0)
        bug_subscription = bug.subscribe(
            person_subscribed, person_subscribing, suppress_notify=False)
        transaction.commit()
        # Ensure the subscription was properly created.
        self.assertEqual(bug_subscription.person, person_subscribed)
        self.assertEqual(bug_subscription.subscribed_by, person_subscribing)
        # Confirm a notification has been sent.
        self.assertEqual(len(stub.test_emails), 1)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
