===========================
Direct user-to-user contact
===========================

A Launchpad user can contact another Launchpad user via a form accessible from
the recipient's user page.  Let's say for example, that No Privileges Person
wants to contact Salgado.

    >>> from lp.services.mail import stub
    >>> del stub.test_emails[:]

    >>> user_browser.open('http://launchpad.test/~salgado')
    >>> user_browser.getLink('Contact this user').click()
    >>> print(user_browser.title)
    Contact this user : Guilherme Salgado

    >>> user_browser.getControl('Subject').value = 'Hi Salgado'
    >>> user_browser.getControl('Message').value = 'Just saying hello'
    >>> user_browser.getControl('Send').click()
    >>> print(user_browser.title)
    Guilherme Salgado in Launchpad

Salgado receives the email message from No Priv.

    >>> len(stub.test_emails)
    1
    >>> from_addr, to_addrs, raw_msg = stub.test_emails.pop()
    >>> print(from_addr)
    bounces@canonical.com
    >>> len(to_addrs)
    1
    >>> print(to_addrs[0])
    Guilherme Salgado <guilherme.salgado@canonical.com>
    >>> print(six.ensure_text(raw_msg))
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    From: No Privileges Person <no-priv@canonical.com>
    To: Guilherme Salgado <guilherme.salgado@canonical.com>
    Subject: Hi Salgado
    ...

No Priv starts to send another message to Salgado, but then changes their
mind.

    >>> user_browser.getLink('Contact this user').click()
    >>> user_browser.getControl('Subject').value = 'Hi Salgado'
    >>> user_browser.getControl('Message').value = 'Hello again'
    >>> user_browser.getLink('Cancel').click()
    >>> print(user_browser.title)
    Guilherme Salgado in Launchpad


Choosing a From: address
========================

Sample Person has multiple registered and validated email addresses.

    >>> browser = setupBrowser(auth='Basic test@canonical.com:test')
    >>> browser.open('http://launchpad.test/~salgado/+contactuser')
    >>> browser.getControl('Subject').value = 'Hi Salgado'
    >>> browser.getControl('Message').value = 'Hello again'

By default, Sample can use their preferred email address.

    >>> print(browser.getControl('From').value)
    ['test@canonical.com']

But they don't have to use their preferred address; they can use one of
their alternative addresses.

    >>> del stub.test_emails[:]
    >>> browser.getControl('From').value = ['testing@canonical.com']
    >>> browser.getControl('Send').click()

    >>> from_addr, to_addrs, raw_msg = stub.test_emails.pop()
    >>> print(six.ensure_text(raw_msg))
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    From: Sample Person <testing@canonical.com>
    To: Guilherme Salgado <guilherme.salgado@canonical.com>
    Subject: Hi Salgado
    ...
