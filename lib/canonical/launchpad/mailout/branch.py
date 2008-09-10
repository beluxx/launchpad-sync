# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Email notifications related to branches."""

__metaclass__ = type


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.components.branch import BranchDelta
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel, IBranch,
    ICodeMailJobSource)
from canonical.launchpad.mail import (get_msgid, simple_sendmail,
    format_address)
from canonical.launchpad.mailout import text_delta
from canonical.launchpad.mailout.basemailer import BaseMailer
from canonical.launchpad.webapp import canonical_url


def email_branch_modified_notifications(branch, to_addresses,
                                        from_address, contents,
                                        recipients, subject=None):
    """Send notification emails using the branch email template.

    Emails are sent one at a time to the listed addresses.
    """
    branch_title = branch.title
    if branch_title is None:
        branch_title = ''
    if subject is None:
        subject = '[Branch %s] %s' % (branch.unique_name, branch_title)
    headers = {'X-Launchpad-Branch': branch.unique_name}
    if branch.product is not None:
        headers['X-Launchpad-Project'] = branch.product.name

    template = get_email_template('branch-modified.txt')
    for address in to_addresses:
        params = {
            'contents': contents,
            'branch_title': branch_title,
            'branch_url': canonical_url(branch),
            'unsubscribe': '',
            'rationale': ('You are receiving this branch notification '
                          'because you are subscribed to it.'),
            }
        subscription, rationale = recipients.getReason(address)
        # The only time that the subscription will be empty is if the owner
        # of the branch is being notified.
        if subscription is None:
            params['rationale'] = (
                "You are getting this email as you are the owner of "
                "the branch and someone has edited the details.")
        elif not subscription.person.isTeam():
            # Give the users a link to unsubscribe.
            params['unsubscribe'] = (
                "\nTo unsubscribe from this branch go to "
                "%s/+edit-subscription." % canonical_url(branch))
        else:
            # Don't give teams an option to unsubscribe.
            pass
        headers['X-Launchpad-Message-Rationale'] = rationale

        body = template % params
        simple_sendmail(from_address, address, subject, body, headers)


def send_branch_revision_notifications(branch, from_address, message, diff,
                                       subject):
    """Notify subscribers that a revision has been added (or removed)."""
    diff_size = diff.count('\n') + 1

    diff_size_to_email = dict(
        [(item, set()) for item in BranchSubscriptionDiffSize.items])

    recipients = branch.getNotificationRecipients()
    interested_levels = (
        BranchSubscriptionNotificationLevel.DIFFSONLY,
        BranchSubscriptionNotificationLevel.FULL)
    for email_address in recipients.getEmails():
        subscription, ignored = recipients.getReason(email_address)
        if subscription.notification_level in interested_levels:
            diff_size_to_email[subscription.max_diff_lines].add(email_address)

    for max_diff in diff_size_to_email:
        addresses = diff_size_to_email[max_diff]
        if len(addresses) == 0:
            continue
        if max_diff != BranchSubscriptionDiffSize.WHOLEDIFF:
            if max_diff == BranchSubscriptionDiffSize.NODIFF:
                contents = message
            elif diff_size > max_diff.value:
                diff_msg = (
                    'The size of the diff (%d lines) is larger than your '
                    'specified limit of %d lines' % (
                    diff_size, max_diff.value))
                contents = "%s\n%s" % (message, diff_msg)
            else:
                contents = "%s\n%s" % (message, diff)
        else:
            contents = "%s\n%s" % (message, diff)
        email_branch_modified_notifications(
            branch, addresses, from_address, contents, recipients, subject)


def send_branch_modified_notifications(branch, event):
    """Notify the related people that a branch has been modifed."""
    branch_delta = BranchDelta.construct(
        event.object_before_modification, branch, event.user)
    if branch_delta is None:
        return
    # If there is no one interested, then bail out early.
    recipients = branch.getNotificationRecipients()
    # If the person editing the branch isn't in the team of the owner
    # then notify the branch owner of the changes as well.
    if not event.user.inTeam(branch.owner):
        # Existing rationales are kept.
        recipients.add(branch.owner, None, "Owner")

    to_addresses = set()
    interested_levels = (
        BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
        BranchSubscriptionNotificationLevel.FULL)
    for email_address in recipients.getEmails():
        subscription, ignored = recipients.getReason(email_address)
        if (subscription is None or
            subscription.notification_level in interested_levels):
            # The subscription is None if we added the branch owner above.
            to_addresses.add(email_address)

    contents = text_delta(
        branch_delta, ('name', 'title', 'url', 'lifecycle_status'),
        ('summary', 'whiteboard'), IBranch)

    if not contents:
        # The specification was modified, but we don't yet support
        # sending notification for the change.
        return

    from_address = format_address(
        event.user.displayname, event.user.preferredemail.email)
    email_branch_modified_notifications(
        branch, to_addresses, from_address, contents, recipients)


class BranchMailer(BaseMailer):
    """Send email notifications about a branch."""

    def sendAll(self):
        for job in self.queue():
            job.sendMail()

    def generateEmail(self, subscriber):
        """Rather roundabout.  Best not to use..."""
        job = removeSecurityProxy(self.queue([subscriber])[0])
        message = job.toMessage()
        job.destroySelf()
        headers = dict(message.items())
        del headers['Date']
        del headers['From']
        del headers['To']
        del headers['Subject']
        return (headers, message['Subject'], message.get_payload(decode=True))

    @staticmethod
    def _format_user_address(user):
        return format_address(user.displayname, user.preferredemail.email)

    def queue(self, recipient_people=None):
        jobs = []
        source = getUtility(ICodeMailJobSource)
        for email, to_address in self.iterRecipients(recipient_people):
            message_id = self.message_id
            if message_id is None:
                message_id = get_msgid()
            reason, rationale = self._recipients.getReason(email)
            if reason.branch.product is not None:
                branch_project_name = reason.branch.product.name
            else:
                branch_project_name = None
            mail = source.create(
                from_address=self.from_address,
                to_address=to_address,
                rationale=rationale,
                branch_url=reason.branch.unique_name,
                subject=self._getSubject(email),
                body=self._getBody(email),
                footer='',
                message_id=message_id,
                in_reply_to=self._getInReplyTo(),
                reply_to_address = self._getReplyToAddress(),
                branch_project_name = branch_project_name,
                )
            jobs.append(mail)
        return jobs
