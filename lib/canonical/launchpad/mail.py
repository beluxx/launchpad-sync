"""
The One True Way to send mail from the Launchpad application.

Uses zope.app.mail.interfaces.IMailer, so you can subscribe to
IMailSentEvent or IMailErrorEvent to record status.

TODO: We should append a signature to messages sent through
simple_sendmail and sendmail with a message explaining 'this
came from launchpad' and a link to click on to change their
messaging settings -- stub 2004-10-21

"""

from email.Utils import make_msgid, formatdate
from email.Message import Message
from email.MIMEText import MIMEText
from zope.app import zapi
from zope.app.mail.interfaces import IMailer

def simple_sendmail(from_addr, to_addrs, subject, body):
    """Construct an email.Message.Message and pass it to sendmail
   
    Returns the Message-Id
    """
    msg = MIMEText(body.encode('utf8'), 'plain', 'utf8')
    msg['To'] = ', '.join([str(a) for a in to_addrs])
    msg['From'] = from_addr
    msg['Subject'] = subject
    sendmail(msg)

def sendmail(message):
    """Send an email.Message.Message

    If you just need to send dumb ASCII or Unicode, simple_sendmail
    will be easier for you. Sending attachments or multipart messages
    will need to use this method.

    From:, To: and Subject: headers should already be set.
    Message-Id:, Date:, and Reply-To: headers will be set if they are 
    not already. Errors-To: headers will always be set. The more we look
    valid, the less we look like spam.
    
    Uses zope.app.mail.interfaces.IMailer, so you can subscribe to
    IMailSentEvent or IMailErrorEvent to record status.

    Returns the Message-Id
 
    """
    assert isinstance(message, Message), 'Not an email.Message.Message'
    assert 'to' in message, 'No To: header'
    assert 'from' in message, 'No From: header'
    assert 'subject' in message, 'No Subject: header'

    from_addr = message['from']
    to_addrs = (message['to'] or '').split(',') \
            + (message['cc'] or '').split(',')

    # Add a Message-Id: header if it isn't already there
    if 'message-id' not in message:
        message_id = make_msgid('launchpad@canonical')
        message['Message-Id'] = message_id

    # Add a Date: header if it isn't already there
    if 'date' not in message:
        message['Date'] = formatdate()

    # Add a Reply-To: header if it isn't already there
    if 'reply-to' not in message:
        message['Reply-To'] = message['from']

    # Add an Errors-To: header for future bounce handling
    # XXX: Need to put in a valid email address to catch bounces before
    # rollout. Needed even if we don't do bounce processing, so that the
    # poor sod in the To: header doesn't get them -- stub 2004-10-21
    del message['Errors-To']
    message['Errors-To'] = 'nobody@example.com'

    # Add an X-Generated-By header for easy whitelisting
    del message['X-Generated-By']
    message['X-Generated-By'] = 'Launchpad (canonical.com)'

    raw_sendmail(from_addr, to_addrs, message.as_string())

    return message_id

def raw_sendmail(from_addr, to_addrs, raw_message):
    """Send a raw RFC8222 email message. 
    
    All headers and encoding should already be done, as the message is
    spooled out verbatim to the delivery agent.

    You should not need to call this method directly, although it may be
    necessary to pass on signed or encrypted messages.

    """
    assert not isinstance(to_addrs, basestring), 'to_addrs must be a sequence'
    assert isinstance(raw_message, str), 'Not a plain string'
    assert raw_message.decode('ascii'), 'Not ASCII - badly encoded message'
    mailer = zapi.getUtility(IMailer, 'sendmail')
    mailer.send(from_addr, to_addrs, raw_message)

'''
def sendmail(from_addr, to_addrs, subject, body):
    """Send a mail from from_addr to to_addrs with the subject and
    body specified."""
    server = smtplib.SMTP('localhost')
    msg = """\
From: %s
To: %s
Subject: %s

%s""" % (from_addr, ", ".join(to_addrs), subject, body)
    server.sendmail(from_addr, to_addrs, msg)
    server.quit()
'''

