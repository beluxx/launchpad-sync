# Copyright 2008 Canonical Ltd.  All rights reserved.

from unittest import TestLoader

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel,
    EmailAddressStatus)
from canonical.launchpad.mailout.codereviewmessage import (
    CodeReviewMessageMailer)
from canonical.launchpad.testing import TestCaseWithFactory


class TestCodeReviewMessage(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, 'foo.bar@canonical.com')

    def makeMessageAndSubscriber(self):
        sender = self.factory.makePerson(
            displayname='Foo Bar', email='foo.bar@example.com',
            email_address_status=EmailAddressStatus.VALIDATED)
        code_message = self.factory.makeCodeReviewMessage(sender)
        subscriber = self.factory.makePerson(
            displayname='Baz Qux', email='baz.qux@example.com',
            email_address_status=EmailAddressStatus.VALIDATED)
        code_message.branch_merge_proposal.source_branch.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        return code_message, subscriber

    def test_for_creation(self):
        code_message, subscriber = self.makeMessageAndSubscriber()
        mailer = CodeReviewMessageMailer.forCreation(code_message)
        self.assertEqual(code_message.message.subject,
                         mailer._subject_template)
        self.assertEqual(set([subscriber]),
                         mailer._recipients.getRecipientPersons())
        self.assertEqual(
            code_message.branch_merge_proposal, mailer.merge_proposal)
        self.assertEqual('Foo Bar <foo.bar@example.com>', mailer.from_address)
        self.assertEqual(code_message, mailer.code_review_message)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
