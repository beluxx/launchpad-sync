Sending Mail
============

simple_mail can be used to send mail easily:

    >>> from lp.services.mail.sendmail import simple_sendmail
    >>> msgid = simple_sendmail(
    ...     from_addr='foo.bar@canonical.com',
    ...     to_addrs='test@canonical.com',
    ...     subject=u'Subject',
    ...     body=u'Content')

The mail get sent when the transaction gets commited:

    >>> import transaction
    >>> transaction.commit()

Now let's look at the sent email:

    >>> import email
    >>> from lp.services.mail import stub
    >>> from_addr, to_addr, raw_message = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_message)
    >>> msg['To']
    'test@canonical.com'
    >>> msg['From']
    'foo.bar@canonical.com'
    >>> msg['Subject']
    'Subject'
    >>> print(msg.get_payload(decode=True).decode())
    Content

Make sure bulk headers are set for vacation programs.

    >>> msg['Precedence']
    'bulk'

In cases where the sender is a Person with a preferred email address,
it's better to use simple_sendmail_from_person. It works just like
simple_sendmail, except that it expects a person instead of an address.
simple_sendmail_from_person has the advantage that it makes sure that
the person's name is encoded properly.

    >>> from lp.services.mail.sendmail import simple_sendmail_from_person
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> foo_bar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
    >>> msgid = simple_sendmail_from_person(
    ...     person=foo_bar,
    ...     to_addrs='test@canonical.com',
    ...     subject=u'Subject',
    ...     body=u'Content')

    >>> transaction.commit()
    >>> from_addr, to_addr, raw_message = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_message)
    >>> msg['To']
    'test@canonical.com'
    >>> msg['From']
    'Foo Bar <foo.bar@canonical.com>'
    >>> msg['Subject']
    'Subject'
    >>> print(msg.get_payload(decode=True).decode())
    Content
    >>> msg['Precedence']
    'bulk'

simple_sendmail_from_person uses the Person's preferred email address:

    >>> login('test@canonical.com')
    >>> from lp.services.identity.interfaces.emailaddress import (
    ...     IEmailAddressSet)
    >>> sample_person = getUtility(IPersonSet).getByEmail(
    ...     'test@canonical.com')
    >>> testing  = getUtility(IEmailAddressSet).getByEmail(
    ...     'testing@canonical.com')
    >>> sample_person.setPreferredEmail(testing)

    >>> print(sample_person.preferredemail.email)
    testing@canonical.com
    >>> msgid = simple_sendmail_from_person(
    ...     person=sample_person,
    ...     to_addrs='test@canonical.com',
    ...     subject=u'Subject',
    ...     body=u'Content')

    >>> transaction.commit()
    >>> found = False
    >>> for from_addr, to_addr, raw_message in stub.test_emails:
    ...     msg = email.message_from_bytes(raw_message)
    ...     if msg['From'] == 'Sample Person <testing@canonical.com>':
    ...         found = True
    >>> assert found
    >>> stub.test_emails = []


To make a header appear more than once in the sent message (e.g.
X-Launchpad-Bug), you can pass a headers dict whose keys are the header names
and whose values are the header body values. If a value is a list or a tuple,
the header will appear more than once in the output message.

    >>> msgid = simple_sendmail(
    ...     from_addr='foo.bar@canonical.com',
    ...     to_addrs='test@canonical.com',
    ...     subject=u'Subject',
    ...     body=u'Content',
    ...     headers={
    ...         'X-Foo': "test", 'X-Bar': ["first value", "second value"]})

    >>> transaction.commit()

    >>> from_addr, to_addr, raw_message = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_message)
    >>> msg["X-Foo"]
    'test'
    >>> msg.get_all("X-Bar")
    ['first value', 'second value']

simple_sendmail accepts the subject and body as unicode strings, but
the from_addr and to_addrs have to be str objects containing ASCII
only.

    >>> msgid = simple_sendmail(
    ...     from_addr='Foo Bar <foo.bar@canonical.com>',
    ...     to_addrs='Sample Person <test@canonical.com>',
    ...     subject=u'\xc4mnesrad',
    ...     body=u'Inneh\xe5ll')
    >>> transaction.commit()

Now let's look at the sent email again.

    >>> from_addr, to_addr, raw_message = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_message)

    >>> from email.header import decode_header
    >>> subject_str, charset = decode_header(msg['Subject'])[0]
    >>> print(backslashreplace(subject_str.decode(charset)))
    \xc4mnesrad

    >>> print(backslashreplace(
    ...     msg.get_payload(decode=True).decode(msg.get_content_charset())))
    Inneh\xe5ll


If we use simple_sendmail_from_person, the person's display_name can
contain non-ASCII characters:

    >>> login('foo.bar@canonical.com')
    >>> foo_bar.display_name = u'F\xf6\xf6 B\u0105r'
    >>> msgid = simple_sendmail_from_person(
    ...     person=foo_bar,
    ...     to_addrs='Sample Person <test@canonical.com>',
    ...     subject=u'\xc4mnesrad',
    ...     body=u'Inneh\xe5ll')
    >>> transaction.commit()

    >>> from_addr, to_addr, raw_message = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_message)

    >>> from email.utils import parseaddr
    >>> from_name_encoded, from_addr = parseaddr(msg['From'])
    >>> from_name_str, charset = decode_header(from_name_encoded)[0]
    >>> from_addr
    'foo.bar@canonical.com'
    >>> print(backslashreplace(from_name_str.decode(charset)))
    F\xf6\xf6 B\u0105r

    >>> subject_str, charset = decode_header(msg['Subject'])[0]
    >>> print(backslashreplace(subject_str.decode(charset)))
    \xc4mnesrad

    >>> print(backslashreplace(
    ...     msg.get_payload(decode=True).decode(msg.get_content_charset())))
    Inneh\xe5ll

simple_sendmail_from_person also makes sure that the name gets
surrounded by quotes and quoted if necessary:

    >>> login('foo.bar@canonical.com')
    >>> foo_bar.display_name = u'Foo [Baz] " Bar'
    >>> msgid = simple_sendmail_from_person(
    ...     person=foo_bar,
    ...     to_addrs='Sample Person <test@canonical.com>',
    ...     subject=u'\xc4mnesrad',
    ...     body=u'Inneh\xe5ll')
    >>> transaction.commit()

    >>> from_addr, to_addr, raw_message = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_message)
    >>> parseaddr(msg['From'])
    ('Foo [Baz] " Bar', 'foo.bar@canonical.com')


If we pass a unicode object to send_mail, it will try and covert it.  If a
non-ASCII str object is passed, it will throw a UnicodeDecodeError.

    >>> simple_sendmail(
    ...     from_addr=u'foo.bar@canonical.com',
    ...     to_addrs=b'test@canonical.com',
    ...     subject=u'Subject',
    ...     body=u'Content')
    '...launchpad@...'

    >>> simple_sendmail(
    ...     from_addr=b'F\xf4\xf4 Bar <foo.bar@canonical.com>',
    ...     to_addrs=b'test@canonical.com',
    ...     subject=u'Subject',
    ...     body=u'Content')
    Traceback (most recent call last):
    ...
    UnicodeDecodeError: 'ascii' codec can't decode byte 0xf4 in position 1:
    ordinal not in range(128)

    >>> simple_sendmail(
    ...     from_addr=b'foo.bar@canonical.com',
    ...     to_addrs=u'test@canonical.com',
    ...     subject=u'Subject',
    ...     body=u'Content')
    '...launchpad@...'

    >>> simple_sendmail(
    ...     from_addr=b'Foo Bar <foo.bar@canonical.com>',
    ...     to_addrs=[b'S\xc4\x85mple Person <test@canonical.com>'],
    ...     subject=u'Subject',
    ...     body=u'Content')
    Traceback (most recent call last):
    ...
    UnicodeDecodeError: 'ascii' codec can't decode byte 0xc4 in position 1:
    ordinal not in range(128)

    >>> transaction.abort()

Passing `bulk=False` to simple_sendmail disables the adding of the bulk
precedence header to the email's headers.

    >>> msgid = simple_sendmail(
    ...     from_addr='feedback@launchpad.net',
    ...     to_addrs='test@canonical.com',
    ...     subject=u'Forgot password',
    ...     body=u'Content',
    ...     bulk=False)
    >>> transaction.commit()

The message is the same as the one from the simple_sendmail test except
that the precedence header was not added.

    >>> from_addr, to_addr, raw_message = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_message)
    >>> msg['To']
    'test@canonical.com'
    >>> msg['From']
    'feedback@launchpad.net'
    >>> msg['Subject']
    'Forgot password'
    >>> print(msg.get_payload(decode=True).decode())
    Content
    >>> print(msg['Precedence'])
    None


sendmail
========

simple_sendmail creates a Message instance, and sends it via another
function, sendmail. sendmail() can also be used directly if you want to
send more complicated emails, like emails with attachments.

    >>> from email.mime.text import MIMEText
    >>> from lp.services.mail.sendmail import sendmail

Let's send a mail using that function. We only create a simple message
to test with, though.

    >>> msg = MIMEText("Some content")
    >>> msg['From'] = 'foo.bar@canonical.com'
    >>> msg['To'] = 'test@canonical.com'
    >>> msg['Subject'] = "test"
    >>> msgid = sendmail(msg)
    >>> transaction.commit()

sendmail automatically adds Return-Path and Errors-To headers to
provide better bounce handling.

    >>> from lp.services.config import config
    >>> from_addr, to_add, raw_message = stub.test_emails.pop()
    >>> sent_msg = email.message_from_bytes(raw_message)
    >>> sent_msg['Return-Path'] == config.canonical.bounce_address
    True
    >>> sent_msg['Errors-To'] == config.canonical.bounce_address
    True

It must also add a Precedence: bulk header so that automatic replies
(e.g. vacation programs) don't try to respond to them.

    >>> sent_msg['Precedence']
    'bulk'

It's possible to set Return-Path manually if needed.

    >>> msg.replace_header('Return-Path', '<>')
    >>> msgid = sendmail(msg)
    >>> transaction.commit()

    >>> from_addr, to_add, raw_message = stub.test_emails.pop()
    >>> sent_msg = email.message_from_bytes(raw_message)
    >>> sent_msg['Return-Path']
    '<>'

If we want to bounce messages, we can manually specify which addresses
the mail should be sent to. When we do this, the 'To' and 'CC' headers
are ignored.

    >>> msg = MIMEText("Some content")
    >>> msg['From'] = 'foo.bar@canonical.com'
    >>> msg['To'] = 'test@canonical.com'
    >>> msg['CC'] = 'foo.bar@canonical.com'
    >>> msg['Subject'] = "test"
    >>> msgid = sendmail(msg, to_addrs=['no-priv@canonical.com'])
    >>> transaction.commit()

    >>> from_addr, to_addrs, raw_message = stub.test_emails.pop()
    >>> for to_addr in to_addrs:
    ...     print(to_addr)
    no-priv@canonical.com

    >>> sent_msg = email.message_from_bytes(raw_message)
    >>> sent_msg['To']
    'test@canonical.com'
    >>> sent_msg['CC']
    'foo.bar@canonical.com'

Since sendmail() gets the addresses to send to from the email header,
it needs to take care of unfolding the headers, so that they don't
contain any line breaks.

    >>> folded_message = email.message_from_bytes(b"""Subject: required
    ... From: Not used
    ...  <from.address@example.com>
    ... To: To Address
    ...  <to.address@example.com>
    ... CC: CC Address
    ...  <cc.address@example.com>
    ...
    ... Content
    ... """)
    >>> msgid = sendmail(folded_message)
    >>> transaction.commit()
    >>> from_addr, to_addrs, raw_message = stub.test_emails.pop()
    >>> from_addr
    'bounces@canonical.com'
    >>> sorted(to_addrs)
    ['CC Address <cc.address@example.com>',
     'To Address <to.address@example.com>']
