# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A stub IMailer for use in development and unittests."""

import email
from logging import getLogger

from zope.component import getUtility
from zope.interface import implementer
from zope.sendmail.interfaces import IMailer

from lp.services.compat import message_as_bytes


@implementer(IMailer)
class StubMailer:
    """
    Overrides the from_addr and to_addrs arguments and passes the
    email on to the IMailer
    """

    def __init__(self, from_addr, to_addrs, mailer, rewrite=False):
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.mailer = mailer
        self.rewrite = rewrite

    def send(self, from_addr, to_addrs, message):
        log = getLogger('lp.services.mail')
        log.info('Email from %s to %s being redirected to %s' % (
            from_addr, ', '.join(to_addrs), ', '.join(self.to_addrs)
            ))

        # Optionally rewrite headers. Everything works without doing this,
        # as it is the message envelope (created by the MTA) rather than the
        # headers that determine the actual To: address. However, this might
        # be required to bypass some spam filters.
        if self.rewrite:
            message = email.message_from_bytes(message)
            message['X-Orig-To'] = message['To']
            message['X-Orig-Cc'] = message['Cc']
            message['X-Orig-From'] = message['From']
            del message['To']
            del message['Cc']
            del message['From']
            del message['Reply-To']
            message['To'] = ', '.join(self.to_addrs)
            message['From'] = self.from_addr
            message = message_as_bytes(message)

        sendmail = getUtility(IMailer, self.mailer)
        sendmail.send(self.from_addr, self.to_addrs, message)

    def vote(self, fromaddr, toaddrs, message):
        pass

    def abort(self):
        # We don't do any work until send() is called, so aborting is trivial.
        pass


test_emails = []


@implementer(IMailer)
class TestMailer:
    """
    Stores (from_addr, to_addrs, message) in the test_emails module global list
    where unittests can examine them.

    Tests or their harnesses will need to clear out the test_emails list.
    """

    def send(self, from_addr, to_addrs, message):
        test_emails.append((from_addr, to_addrs, message))

    def vote(self, fromaddr, toaddrs, message):
        pass

    def abort(self):
        # We don't do any work until send() is called, so aborting is trivial.
        pass
