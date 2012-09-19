# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests related to bug notification recipients."""

__metaclass__ = type

from zope.component import getUtility

from lp.registry.enums import InformationType
from lp.registry.interfaces.accesspolicy import (
    IAccessArtifactGrantSource,
    IAccessPolicySource,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestBugNotificationRecipients(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_public_bug(self):
        bug = self.factory.makeBug()
        self.assertContentEqual(
            [bug.owner], bug.getBugNotificationRecipients())

    def test_public_bug_with_subscriber(self):
        bug = self.factory.makeBug()
        subscriber = self.factory.makePerson()
        with person_logged_in(bug.owner):
            bug.subscribe(subscriber, bug.owner)
        self.assertContentEqual(
            [bug.owner, subscriber], bug.getBugNotificationRecipients())

    def test_public_bug_with_structural_subscriber(self):
        subscriber = self.factory.makePerson()
        product = self.factory.makeProduct()
        with person_logged_in(subscriber):
            product.addBugSubscription(subscriber, subscriber)
        bug = self.factory.makeBug(target=product)
        self.assertContentEqual(
            [bug.owner, subscriber], bug.getBugNotificationRecipients())

    def test_public_bug_assignee(self):
        assignee = self.factory.makePerson()
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            bug.default_bugtask.transitionToAssignee(assignee)
        self.assertContentEqual(
            [bug.owner, assignee], bug.getBugNotificationRecipients())

    def test_public_bug_with_duplicate_subscriber(self):
        subscriber = self.factory.makePerson()
        bug = self.factory.makeBug()
        dupe = self.factory.makeBug()
        with person_logged_in(dupe.owner):
            dupe.subscribe(subscriber, dupe.owner)
            dupe.markAsDuplicate(bug)
        self.assertContentEqual(
            [bug.owner, dupe.owner, subscriber],
            bug.getBugNotificationRecipients())

    def test_private_bug(self):
        # Only the owner is notified about a private bug.
        owner = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            self.assertContentEqual(
                [owner], bug.getBugNotificationRecipients())

    def test_private_bug_with_subscriber(self):
        # Subscribing a user to a bug grants access, so they will be notified.
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            bug.subscribe(subscriber, owner)
            self.assertContentEqual(
                [owner, subscriber], bug.getBugNotificationRecipients())

    def test_private_bug_with_subscriber_without_access(self):
        # A subscriber without access to a private bug isn't notified.
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        artifact = self.factory.makeAccessArtifact(concrete=bug)
        with person_logged_in(owner):
            bug.subscribe(subscriber, owner)
            getUtility(IAccessArtifactGrantSource).revokeByArtifact(
                [artifact], [subscriber])
            self.assertContentEqual(
                [owner], bug.getBugNotificationRecipients())

    def test_private_bug_with_structural_subscriber(self):
        # A structural subscriber without access does not get notified about
        # a private bug.
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        product = self.factory.makeProduct()
        with person_logged_in(subscriber):
            product.addBugSubscription(subscriber, subscriber)
        bug = self.factory.makeBug(
            target=product, owner=owner,
            information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            self.assertContentEqual(
                [owner], bug.getBugNotificationRecipients())

    def test_private_bug_with_structural_subscriber_with_access(self):
        # When a structural subscriber has access to a private bug, they are
        # notified.
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        product = self.factory.makeProduct()
        with person_logged_in(subscriber):
            product.addBugSubscription(subscriber, subscriber)
        policy = getUtility(IAccessPolicySource).find(
            [(product, InformationType.USERDATA)]).one()
        self.factory.makeAccessPolicyGrant(policy=policy, grantee=subscriber)
        bug = self.factory.makeBug(
            target=product, owner=owner,
            information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            self.assertContentEqual(
                [owner, subscriber], bug.getBugNotificationRecipients())

    def test_private_bug_assignee(self):
        # Assigning a user to a private bug does not give them visibility.
        owner = self.factory.makePerson()
        assignee = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            bug.default_bugtask.transitionToAssignee(assignee)
            self.assertContentEqual(
                [owner], bug.getBugNotificationRecipients())

    def test_private_bug_assignee_with_access(self):
        # An assignee with access will get notified.
        owner = self.factory.makePerson()
        assignee = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        artifact = self.factory.makeAccessArtifact(concrete=bug)
        self.factory.makeAccessArtifactGrant(
            artifact=artifact, grantee=assignee)
        with person_logged_in(owner):
            bug.default_bugtask.transitionToAssignee(assignee)
            self.assertContentEqual(
                [owner, assignee], bug.getBugNotificationRecipients())

    def test_private_bug_with_duplicate_subscriber(self):
        # A subscriber to a duplicate of a private bug will not be notified.
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        dupe = self.factory.makeBug(owner=owner)
        with person_logged_in(owner):
            dupe.subscribe(subscriber, owner)
            dupe.markAsDuplicate(bug)
            self.assertContentEqual(
                [owner], bug.getBugNotificationRecipients())

    def test_private_bug_with_duplicate_subscriber_with_access(self):
        # A subscriber to a duplicate of a private bug will be notified, if
        # they have access.
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        artifact = self.factory.makeAccessArtifact(concrete=bug)
        self.factory.makeAccessArtifactGrant(
            artifact=artifact, grantee=subscriber)
        dupe = self.factory.makeBug(owner=owner)
        with person_logged_in(owner):
            dupe.subscribe(subscriber, owner)
            dupe.markAsDuplicate(bug)
            self.assertContentEqual(
                [owner, subscriber], bug.getBugNotificationRecipients())
