# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An IMailer that stores messages in a specified mbox file."""

from contextlib import closing
import email
from email.utils import make_msgid
from logging import getLogger
import mailbox

from zope.component import getUtility
from zope.interface import implementer
from zope.sendmail.interfaces import IMailer


COMMASPACE = ', '


@implementer(IMailer)
class MboxMailer:
    """Stores the message in a Unix mailbox file."""

    def __init__(self, filename, overwrite, mailer=None):
        self.filename = filename
        if overwrite:
            # Truncate existing file.  Subsequent opens will always append so
            # this is effectively an overwrite.  Note that because IMailer
            # doesn't have a close() method, we can't leave the file open
            # here, otherwise it will never get closed.
            with open(self.filename, 'w'):
                pass
        self.mailer = mailer

    def send(self, fromaddr, toaddrs, message):
        """See IMailer."""
        env_recips = COMMASPACE.join(toaddrs)
        log = getLogger('lp.services.mail')
        log.info('Email from %s to %s being stored in mailbox %s',
                 fromaddr, env_recips, self.filename)
        msg = email.message_from_string(message)
        # Mimic what MTAs such as Postfix do in transfering the envelope
        # sender into the Return-Path header.  It's okay if the message has
        # multiple such headers.
        msg['Return-Path'] = fromaddr
        # Because it might be useful, copy the envelope recipients into the
        # RFC 2822 headers too.
        msg['X-Envelope-To'] = env_recips
        # Add the Message-ID required by the interface; even though the
        # interface says that the message text doesn't include such a header,
        # zap it first just in case.
        del msg['message-id']
        msg['Message-ID'] = message_id = make_msgid()
        with closing(mailbox.mbox(self.filename)) as mbox:
            mbox.lock()
            try:
                mbox.add(msg)
            finally:
                mbox.unlock()
        if self.mailer is not None:
            # Forward the message on to the chained mailer, if there is one.
            # This allows for example, the mboxMailer to be used in the test
            # suite, which requires that the testMailer eventually gets
            # called.
            chained_mailer = getUtility(IMailer, self.mailer)
            chained_mailer.send(fromaddr, toaddrs, message)
        return message_id

    def vote(self, fromaddr, toaddrs, message):
        pass

    def abort(self):
        # We don't do any work until send() is called, so aborting is trivial.
        pass
