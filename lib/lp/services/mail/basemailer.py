# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base class for sending out emails."""

__all__ = ["BaseMailer", "RecipientReason"]

import logging
import sys
from collections import OrderedDict
from smtplib import SMTPException

from zope.component import getUtility
from zope.error.interfaces import IErrorReportingUtility
from zope.security.management import getSecurityPolicy

from lp.services.mail.helpers import get_email_template
from lp.services.mail.mailwrapper import MailWrapper
from lp.services.mail.notificationrecipientset import NotificationRecipientSet
from lp.services.mail.sendmail import (
    MailController,
    append_footer,
    format_address,
)
from lp.services.utils import text_delta
from lp.services.webapp.authorization import LaunchpadPermissiveSecurityPolicy


class BaseMailer:
    """Base class for notification mailers.

    Subclasses must provide getReason (or reimplement _getTemplateParameters
    or generateEmail).

    It is expected that subclasses may override _getHeaders,
    _getTemplateParams, and perhaps _getBody.
    """

    app = None

    def __init__(
        self,
        subject,
        template_name,
        recipients,
        from_address,
        delta=None,
        message_id=None,
        notification_type=None,
        mail_controller_class=None,
        request=None,
        wrap=False,
        force_wrap=False,
    ):
        """Constructor.

        :param subject: A Python dict-replacement template for the subject
            line of the email.
        :param template: Name of the template to use for the message body.
        :param recipients: A dict of recipient to Subscription.
        :param from_address: The from_address to use on emails.
        :param delta: A Delta object with members "delta_values", "interface"
            and "new_values", such as BranchMergeProposalDelta.
        :param message_id: The Message-Id to use for generated emails.  If
            not supplied, random message-ids will be used.
        :param mail_controller_class: The class of the mail controller to
            use to send the mails.  Defaults to `MailController`.
        :param request: An optional `IErrorReportRequest` to use when
            logging OOPSes.
        :param wrap: Wrap body text using `MailWrapper`.
        :param force_wrap: See `MailWrapper.format`.
        """
        # Running mail notifications with web security is too fragile: it's
        # easy to end up with subtle bugs due to such things as
        # subscriptions from private teams that are inaccessible to the user
        # with the current interaction.  BaseMailer always sends one mail
        # per recipient and thus never leaks information to other users, so
        # it's safer to require a permissive security policy.
        #
        # When converting other notification code to BaseMailer, it may be
        # necessary to move notifications into jobs, to move unit tests to a
        # Zopeless-based layer, or to use the permissive_security_policy
        # context manager.
        assert (
            getSecurityPolicy() == LaunchpadPermissiveSecurityPolicy
        ), "BaseMailer may only be used with a permissive security policy."

        self._subject_template = subject
        self._template_name = template_name
        self._recipients = NotificationRecipientSet()
        for recipient, reason in recipients.items():
            self._recipients.add(recipient, reason, reason.mail_header)
        self.from_address = from_address
        self.delta = delta
        self.message_id = message_id
        self.notification_type = notification_type
        self.logger = logging.getLogger("lp.services.mail.basemailer")
        if mail_controller_class is None:
            mail_controller_class = MailController
        self._mail_controller_class = mail_controller_class
        self.request = request
        self._wrap = wrap
        self._force_wrap = force_wrap

    def _getFromAddress(self, email, recipient):
        return self.from_address

    def _getToAddresses(self, email, recipient):
        return [format_address(recipient.displayname, email)]

    def generateEmail(self, email, recipient, force_no_attachments=False):
        """Generate the email for this recipient.

        :param email: Email address of the recipient to send to.
        :param recipient: The Person to send to.
        :return: (headers, subject, body) of the email.
        """
        from_address = self._getFromAddress(email, recipient)
        to_addresses = self._getToAddresses(email, recipient)
        headers = self._getHeaders(email, recipient)
        subject = self._getSubject(email, recipient)
        body = self._getBody(email, recipient)
        expanded_footer = self._getExpandedFooter(headers, recipient)
        if expanded_footer:
            body = append_footer(body, expanded_footer)
        ctrl = self._mail_controller_class(
            from_address,
            to_addresses,
            subject,
            body,
            headers,
            envelope_to=[email],
        )
        if force_no_attachments:
            ctrl.addAttachment(
                "Excessively large attachments removed.",
                content_type="text/plain",
                inline=True,
            )
        else:
            self._addAttachments(ctrl, email)
        return ctrl

    def _getSubject(self, email, recipient):
        """The subject template expanded with the template params."""
        return self._subject_template % self._getTemplateParams(
            email, recipient
        )

    def _getReplyToAddress(self, email, recipient):
        """Return the address to use for the reply-to header."""
        return None

    def _getHeaders(self, email, recipient):
        """Return the mail headers to use."""
        reason, rationale = self._recipients.getReason(email)
        headers = OrderedDict()
        headers["X-Launchpad-Message-Rationale"] = reason.mail_header
        if reason.subscriber.name is not None:
            headers["X-Launchpad-Message-For"] = reason.subscriber.name
        if self.notification_type is not None:
            headers["X-Launchpad-Notification-Type"] = self.notification_type
        reply_to = self._getReplyToAddress(email, recipient)
        if reply_to is not None:
            headers["Reply-To"] = reply_to
        if self.message_id is not None:
            headers["Message-Id"] = self.message_id
        return headers

    def _addAttachments(self, ctrl, email):
        """Add any appropriate attachments to a MailController.

        Default implementation does nothing.
        :param ctrl: The MailController to add attachments to.
        :param email: The email address of the recipient.
        """
        pass

    def _getTemplateName(self, email, recipient):
        """Return the name of the template to use for this email body."""
        return self._template_name

    def _getTemplateParams(self, email, recipient):
        """Return a dict of values to use in the body and subject."""
        reason, rationale = self._recipients.getReason(email)
        params = {"reason": reason.getReason()}
        if self.delta is not None:
            params["delta"] = self.textDelta()
        return params

    def textDelta(self):
        """Return a textual version of the class delta."""
        return text_delta(
            self.delta,
            self.delta.delta_values,
            self.delta.new_values,
            self.delta.interface,
        )

    def _getBody(self, email, recipient):
        """Return the complete body to use for this email."""
        template = get_email_template(
            self._getTemplateName(email, recipient), app=self.app
        )
        params = self._getTemplateParams(email, recipient)
        body = template % params
        if self._wrap:
            body = (
                MailWrapper().format(body, force_wrap=self._force_wrap) + "\n"
            )
        footer = self._getFooter(email, recipient, params)
        if footer is not None:
            body = append_footer(body, footer)
        return body

    def _getFooter(self, email, recipient, params):
        """Provide a footer to attach to the body, or None."""
        return None

    def _getExpandedFooter(self, headers, recipient):
        """Provide an expanded footer for recipients who have requested it."""
        if not recipient.expanded_notification_footers:
            return None
        lines = []
        for key, value in headers.items():
            if key.startswith("X-Launchpad-"):
                lines.append("%s: %s\n" % (key[2:], value))
        return "".join(lines)

    def sendOne(self, email, recipient):
        """Send notification to one recipient."""
        # We never want SMTP errors to propagate from this function.
        ctrl = self.generateEmail(email, recipient)
        try:
            ctrl.send()
        except SMTPException:
            # If the initial sending failed, try again without
            # attachments.
            ctrl = self.generateEmail(
                email, recipient, force_no_attachments=True
            )
            try:
                ctrl.send()
            except SMTPException:
                error_utility = getUtility(IErrorReportingUtility)
                oops_vars = {
                    "message_id": ctrl.headers.get("Message-Id"),
                    "notification_type": self.notification_type,
                    "recipient": ", ".join(ctrl.to_addrs),
                    "subject": ctrl.subject,
                }
                with error_utility.oopsMessage(oops_vars):
                    oops = error_utility.raising(sys.exc_info(), self.request)
                self.logger.info("Mail resulted in OOPS: %s" % oops.get("id"))

    def sendAll(self):
        """Send notifications to all recipients."""
        for email, recipient in sorted(self._recipients.getRecipientPersons()):
            self.sendOne(email, recipient)


class RecipientReason:
    """Reason for sending mail to a recipient."""

    def __init__(self, subscriber, recipient, mail_header, reason_template):
        self.subscriber = subscriber
        self.recipient = recipient
        self.mail_header = mail_header
        self.reason_template = reason_template

    @staticmethod
    def makeRationale(rationale_base, person):
        if person.is_team:
            return "%s @%s" % (rationale_base, person.name)
        else:
            return rationale_base

    def _getTemplateValues(self):
        template_values = {
            "entity_is": "You are",
            "lc_entity_is": "you are",
        }
        if self.recipient != self.subscriber:
            assert self.recipient.hasParticipationEntryFor(
                self.subscriber
            ), "%s does not participate in team %s." % (
                self.recipient.displayname,
                self.subscriber.displayname,
            )
        if self.recipient != self.subscriber or self.subscriber.is_team:
            template_values["entity_is"] = (
                "Your team %s is" % self.subscriber.displayname
            )
            template_values["lc_entity_is"] = (
                "your team %s is" % self.subscriber.displayname
            )
        return template_values

    def getReason(self):
        """Return a string explaining why the recipient is a recipient."""
        return self.reason_template % self._getTemplateValues()

    @classmethod
    def forBuildRequester(cls, requester):
        header = cls.makeRationale("Requester", requester)
        reason = "%(entity_is)s the requester of the build."
        return cls(requester, requester, header, reason)
