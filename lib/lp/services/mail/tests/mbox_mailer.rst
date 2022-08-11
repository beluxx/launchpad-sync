Test the MboxMailer implementation of the IMailer interface.  There are a few
basic combinations to test.  We want to make sure that overwriting and not
overwriting an existing mbox file both works.  We also want to make sure that
chaining and not chaining mailers works.

Create an overwriting, non-chaining MboxMailer.  The doctest harness creates
the temporary file mbox_filename for us.

    >>> from lp.services.mail.mbox import MboxMailer
    >>> mailer = MboxMailer(mbox_filename, overwrite=True, mailer=None)
    >>> msg_id = mailer.send('geddy@example.com',
    ...             ['jaco@example.com', 'victor@example.com'],
    ...             """\
    ... From: geddy@example.com
    ... To: jaco@example.com
    ... Cc: victor@example.com
    ... Subject: a bug
    ...
    ... There is a bug we should be concerned with.""")
    >>> msg_id
    '<...>'

Read the mbox file and make sure the message we just mailed is in there, and
no other messages.

    >>> import mailbox
    >>> mbox = mailbox.mbox(mbox_filename)
    >>> [msg] = mbox
    >>> msg['from']
    'geddy@example.com'
    >>> msg['to']
    'jaco@example.com'
    >>> msg['cc']
    'victor@example.com'
    >>> msg['subject']
    'a bug'
    >>> msg['return-path']
    'geddy@example.com'
    >>> msg['x-envelope-to']
    'jaco@example.com, victor@example.com'
    >>> msg['message-id'] == msg_id
    True
    >>> mbox.close()

Create another mailer, again that overwrites.  Make sure it actually does
overwrite.

    >>> mailer = MboxMailer(mbox_filename, overwrite=True, mailer=None)
    >>> mailer.send('mick@example.com',
    ...             ['chris@example.com', 'paul@example.com'],
    ...             """\
    ... From: mick@example.com
    ... To: chris@example.com
    ... Cc: paul@example.com
    ... Subject: a bug
    ...
    ... There is a bug we should be concerned with.""")
    '<...>'

    >>> mbox = mailbox.mbox(mbox_filename)
    >>> [msg] = mbox
    >>> msg['from']
    'mick@example.com'
    >>> mbox.close()

Create another mailer, this time one that does not overwrite.  Both the
message we sent above and the message we're about to send should be in the
mbox file.

    >>> from lp.services.mail.mbox import MboxMailer
    >>> mailer = MboxMailer(mbox_filename, overwrite=False, mailer=None)
    >>> mailer.send('carol@example.com',
    ...             ['melissa@example.com'],
    ...             """\
    ... From: carol@example.com
    ... To: melissa@example.com
    ... Subject: a bug
    ...
    ... There is a bug we should be concerned with.""")
    '<...>'

    >>> mbox = mailbox.mbox(mbox_filename)
    >>> [msg1, msg2] = mbox
    >>> msg1['from']
    'mick@example.com'
    >>> msg2['from']
    'carol@example.com'
    >>> mbox.close()

Now test mailer chaining.  Because we don't want these tests to depend on any
other kind of mailer, create two mbox mailers, chaining one to the other.  The
send the message to the last one in the chain and check to make sure that the
message is in both mbox files.  chained_filename is created by the test
harness.

    >>> chained = MboxMailer(chained_filename, overwrite=True, mailer=None)
    >>> from zope.component import provideUtility
    >>> from zope.sendmail.interfaces import IMailer
    >>> provideUtility(chained, IMailer, name='mbox-mailer-test-mailer')

    >>> mailer  = MboxMailer(mbox_filename, overwrite=True,
    ...                      mailer='mbox-mailer-test-mailer')
    >>> mailer.send('sting@example.com',
    ...             ['oteil@example.com'],
    ...             """\
    ... From: sting@example.com
    ... To: oteil@example.com
    ... Subject: a bug
    ...
    ... There is a bug we should be concerned with.""")
    '<...>'

    >>> mbox = mailbox.mbox(mbox_filename)
    >>> [msg] = mbox
    >>> msg['from']
    'sting@example.com'
    >>> mbox.close()

    >>> mbox = mailbox.mbox(chained_filename)
    >>> [msg] = mbox
    >>> msg['from']
    'sting@example.com'
    >>> mbox.close()
