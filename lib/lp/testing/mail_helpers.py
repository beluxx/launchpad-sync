# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions dealing with emails in tests."""

import email
import operator

import six
import transaction
from zope.component import getUtility

from lp.registry.interfaces.persontransferjob import (
    IExpiringMembershipNotificationJobSource,
    IMembershipNotificationJobSource,
    ISelfRenewalNotificationJobSource,
    ITeamInvitationNotificationJobSource,
    ITeamJoinNotificationJobSource,
    )
from lp.services.config import config
from lp.services.job.runner import JobRunner
from lp.services.log.logger import DevNullLogger
from lp.services.mail import stub


def pop_notifications(sort_key=None, commit=True):
    """Return generated emails as email messages.

    A helper function which optionally commits the transaction, so
    that the notifications are queued in stub.test_emails and pops these
    notifications from the queue.

    :param sort_key: define sorting function.  sort_key specifies a
    function of one argument that is used to extract a comparison key from
    each list element.  (See the sorted() Python built-in.)
    :param commit: whether to commit before reading email (defaults to True).
    """
    if commit:
        transaction.commit()
    if sort_key is None:
        sort_key = operator.itemgetter('To')

    notifications = []
    for fromaddr, toaddrs, raw_message in stub.test_emails:
        notification = email.message_from_bytes(raw_message)
        notification['X-Envelope-To'] = ', '.join(toaddrs)
        notification['X-Envelope-From'] = fromaddr
        notifications.append(notification)
    stub.test_emails = []

    return sorted(notifications, key=sort_key)


def sort_addresses(header):
    """Sort an address-list in an email header field body."""
    addresses = {address.strip() for address in header.split(',')}
    return ", ".join(sorted(addresses))


def print_emails(include_reply_to=False, group_similar=False,
                 include_rationale=False, include_for=False,
                 notifications=None, include_notification_type=False,
                 decode=False):
    """Pop all messages from stub.test_emails and print them with
     their recipients.

    Since the same message may be sent more than once (for different
    recipients), setting 'group_similar' will print each distinct
    message only once and group all recipients of that message
    together in the 'To:' field.  It will also strip the first line of
    the email body.  (The line with "Hello Foo," which is likely
    distinct for each recipient.)

    :param include_reply_to: Include the reply-to header if True.
    :param group_similar: Group messages sent to multiple recipients if True.
    :param include_rationale: Include the X-Launchpad-Message-Rationale
        header.
    :param include_for: Include the X-Launchpad-Message-For header.
    :param notifications: Use the provided list of notifications instead of
        the stack.
    :param include_notification_type: Include the
        X-Launchpad-Notification-Type header.
    :param decode: Decode message payloads if True.
    """
    distinct_bodies = {}
    if notifications is None:
        notifications = pop_notifications()
    for message in notifications:
        recipients = {
            recipient.strip()
            for recipient in message['To'].split(',')}
        body = message.get_payload(decode=decode)
        if group_similar:
            # Strip the first line as it's different for each recipient.
            body = body[body.find(b'\n' if decode else '\n') + 1:]
        if body in distinct_bodies and group_similar:
            message, existing_recipients = distinct_bodies[body]
            distinct_bodies[body] = (
                message, existing_recipients.union(recipients))
        else:
            distinct_bodies[body] = (message, recipients)
    for body in sorted(distinct_bodies):
        message, recipients = distinct_bodies[body]
        print('From:', message['From'])
        print('To:', ", ".join(sorted(recipients)))
        if include_reply_to:
            print('Reply-To:', message['Reply-To'])
        rationale_header = 'X-Launchpad-Message-Rationale'
        if include_rationale and rationale_header in message:
            print('%s: %s' % (rationale_header, message[rationale_header]))
        for_header = 'X-Launchpad-Message-For'
        if include_for and for_header in message:
            print('%s: %s' % (for_header, message[for_header]))
        notification_type_header = 'X-Launchpad-Notification-Type'
        if include_notification_type and notification_type_header in message:
            print('%s: %s' % (
                notification_type_header, message[notification_type_header]))
        print('Subject:', message['Subject'])
        print(six.ensure_text(body))
        print("-" * 40)


def print_distinct_emails(include_reply_to=False, include_rationale=True,
                          include_for=False, include_notification_type=True,
                          decode=False):
    """A convenient shortcut for `print_emails`(group_similar=True)."""
    return print_emails(group_similar=True,
                        include_reply_to=include_reply_to,
                        include_rationale=include_rationale,
                        include_for=include_for,
                        include_notification_type=include_notification_type,
                        decode=decode)


def run_mail_jobs():
    """Process job queues that send out emails.

    If a new job type is added that sends emails, this function can be
    extended to run those jobs, so that testing emails doesn't require a
    bunch of different function calls to process different queues.
    """
    # Circular import.
    from lp.testing.pages import permissive_security_policy

    # Commit the transaction to make sure that the JobRunner can find
    # the queued jobs.
    transaction.commit()
    for interface in (
            IExpiringMembershipNotificationJobSource,
            IMembershipNotificationJobSource,
            ISelfRenewalNotificationJobSource,
            ITeamInvitationNotificationJobSource,
            ITeamJoinNotificationJobSource,
            ):
        job_source = getUtility(interface)
        logger = DevNullLogger()
        dbuser_name = getattr(config, interface.__name__).dbuser
        with permissive_security_policy(dbuser_name):
            runner = JobRunner.fromReady(job_source, logger)
            runner.runAll()
