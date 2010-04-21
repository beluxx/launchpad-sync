# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests related to bug notifications."""

__metaclass__ = type

import unittest

from zope.event import notify
from zope.interface import providedBy

from lazr.lifecycle.snapshot import Snapshot

from canonical.config import config
from canonical.launchpad.database import BugNotification
from lazr.lifecycle.event import ObjectModifiedEvent
from canonical.launchpad.ftests import login
from lp.bugs.interfaces.bugtask import BugTaskStatus, IUpstreamBugTask
from lp.testing import TestCaseWithFactory
from lp.testing.factory import LaunchpadObjectFactory
from lp.testing.mail_helpers import pop_notifications
from canonical.testing import LaunchpadFunctionalLayer, LaunchpadZopelessLayer


class TestNotificationRecipientsOfPrivateBugs(unittest.TestCase):
    """Test who get notified of changes to private bugs."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        factory = LaunchpadObjectFactory()
        self.product = factory.makeProduct()
        self.product_subscriber = factory.makePerson()
        self.product.addBugSubscription(
            self.product_subscriber, self.product_subscriber)
        self.bug_subscriber = factory.makePerson()
        self.private_bug = factory.makeBug(product=self.product, private=True)
        self.reporter = self.private_bug.owner
        self.private_bug.subscribe(self.bug_subscriber, self.reporter)
        [self.product_bugtask] = self.private_bug.bugtasks
        self.direct_subscribers = set(
            person.name for person in [self.bug_subscriber, self.reporter])

    def test_status_change(self):
        # Status changes are sent to the direct subscribers only.
        bugtask_before_modification = Snapshot(
            self.product_bugtask, providing=providedBy(self.product_bugtask))
        self.product_bugtask.transitionToStatus(
            BugTaskStatus.INVALID, self.private_bug.owner)
        notify(ObjectModifiedEvent(
            self.product_bugtask, bugtask_before_modification, ['status'],
            user=self.reporter))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(notified_people, self.direct_subscribers)

    def test_add_comment(self):
        # Comment additions are sent to the direct subscribers only.
        self.private_bug.newMessage(
            self.reporter, subject='subject', content='content')
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(notified_people, self.direct_subscribers)

    def test_bug_edit(self):
        # Bug edits are sent to direct the subscribers only.
        bug_before_modification = Snapshot(
            self.private_bug, providing=providedBy(self.private_bug))
        self.private_bug.description = 'description'
        notify(ObjectModifiedEvent(
            self.private_bug, bug_before_modification, ['description'],
            user=self.reporter))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(notified_people, self.direct_subscribers)


class TestNotificationsSentForBugExpiration(TestCaseWithFactory):
    """Ensure that sub and question subscribers are notified about bug
    expiration."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestNotificationsSentForBugExpiration, self).setUp()
        login('test@canonical.com')
        product_owner = self.factory.makePerson(
            name='product-owner', email='product-owner@example.com')
        self.product = self.factory.makeProduct(owner=product_owner)
        self.bug = self.factory.makeBug(product=self.product)
        question = self.factory.makeQuestion(target=self.product)
        subscriber = self.factory.makePerson(
            name='question-subscriber', email='subscriber@example.com')
        question.subscribe(subscriber)
        question.linkBug(self.bug)
        pop_notifications()
        self.layer.switchDbUser(config.malone.expiration_dbuser)

    def test_notifications_for_question_subscribers(self):
        # Ensure that notifications are sent to subscribers of a
        # question linked to the expired bug.
        bugtask = self.bug.default_bugtask
        bugtask_before_modification = Snapshot(
            bugtask, providing=IUpstreamBugTask)
        bugtask.transitionToStatus(BugTaskStatus.EXPIRED, self.product.owner)
        bug_modified = ObjectModifiedEvent(
            bugtask, bugtask_before_modification,
            ["status"])
        notify(bug_modified)
        self.assertEqual(
            ['product-owner@example.com', 'subscriber@example.com'],
            [mail['To'] for mail in pop_notifications()])


def test_suite():
    """Return the test suite for the tests in this module."""
    return unittest.TestLoader().loadTestsFromName(__name__)
