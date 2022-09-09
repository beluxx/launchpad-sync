Team contact address
====================

Team admins are allowed to set the contact method used by Launchpad to
send notifications to that team.  The possible contact methods are:

    - Hosted mailing list:  Notifications are sent to this team's
                            mailing list hosted on Launchpad. The
                            mailing list may have a customized message
                            sent to new subscribers.  See
                            .../stories/mailinglists/lifecycle.rst

    - None:  There's no way to contact the team as a whole, so any
             notification is sent to every member of the team.

    - Another address:  All notifications are sent to the given email
                        address (stored as the team's preferredemail).

    >>> browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> browser.open("http://launchpad.test/~landscape-developers")
    >>> browser.getLink(url="+contactaddress").click()
    >>> browser.title
    'Landscape Developers contact address...

A warning is rendered about the privacy implications of using a mailing list
or external contact address.

    >>> from lp.services.beautifulsoup import BeautifulSoup
    >>> soup = BeautifulSoup(browser.contents)
    >>> print(soup.find(id="email-warning").decode())
    <p ... Email sent to a mailing list or external contact address may ...

As we can see, the landscape-developers team has no contact address.

    >>> from lp.testing.pages import strip_label

    >>> control = browser.getControl(name="field.contact_method")
    >>> [strip_label(label) for label in control.displayValue]
    ['Each member individually']


External address
----------------

Changing the contact address to an external address will require the
user to go through the email address confirmation process.

    >>> browser.getControl("Another email address").selected = True
    >>> browser.getControl(
    ...     name="field.contact_address"
    ... ).value = "foo@example.com"
    >>> browser.getControl("Change").click()
    >>> browser.title
    'Landscape Developers in Launchpad'
    >>> print_feedback_messages(browser.contents)
    A confirmation message has been sent to...

    >>> from lp.services.mail import stub
    >>> from_addr, to_addrs, raw_msg = stub.test_emails.pop()
    >>> stub.test_emails
    []

    # Extract the link (from the email we just sent) the user will have to
    # use to finish the registration process.
    >>> from lp.services.verification.tests.logintoken import (
    ...     get_token_url_from_email,
    ... )
    >>> token_url = get_token_url_from_email(raw_msg)
    >>> token_url
    'http://launchpad.test/token/...'
    >>> to_addrs
    ['foo@example.com']

Follow the token link, to confirm the new email address.

    >>> browser.open(token_url)
    >>> browser.title
    'Confirm email address'
    >>> browser.getControl("Continue").click()

    >>> browser.title
    'Landscape Developers in Launchpad'
    >>> print_feedback_messages(browser.contents)
    Email address successfully confirmed.

    >>> browser.getLink(url="+contactaddress").click()
    >>> browser.title
    'Landscape Developers contact address...
    >>> control = browser.getControl(name="field.contact_method")
    >>> [strip_label(label) for label in control.displayValue]
    ['Another email address']
    >>> browser.getControl(name="field.contact_address").value
    'foo@example.com'
