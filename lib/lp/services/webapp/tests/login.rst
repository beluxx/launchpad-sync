======================
Logging into Launchpad
======================

Launchpad is an OpenID Relying Party that uses the Login Service as its fixed
OpenID Provider. Because of that, when a user clicks the 'Log in / Register'
link, they'll be sent to the OP to authenticate.

Set handleErrors to True so that the Unauthorized exception is handled by
the publisher and we get redirected to the +login page.

    >>> from lp.testing.browser import Browser
    >>> from lp.testing.layers import BaseLayer
    >>> root_url = BaseLayer.appserver_root_url()
    >>> browser = Browser()
    >>> browser.handleErrors = True
    >>> browser.open("%s/people/?name=foo&searchfor=all" % root_url)
    >>> browser.getLink("Log in / Register").click()

On a browser with JS support, this page would've been automatically
submitted (thanks to the onload handler), but testbrowser doesn't support
JS, so we have to submit the form manually.

    >>> print(browser.contents)
    <html>...<body onload="document.forms[0].submit();"...
    >>> browser.getControl("Continue").click()

The OpenID Provider will ask us to authenticate.

    >>> print(browser.title)
    Login
    >>> from lp.services.webapp.tests.test_login import (
    ...     fill_login_form_and_submit,
    ... )
    >>> fill_login_form_and_submit(browser, "test@canonical.com")

Once authenticated, we're redirected back to the page where we started, with
the query args preserved.

    >>> print(browser.vhost)
    http://launchpad.test
    >>> browser.urlpath
    '/people'
    >>> import re
    >>> print(pretty(sorted(re.sub(".*\?", "", browser.url).split("&"))))
    ['name=foo', 'searchfor=all']

If we load the +login page while already logged in, it will say we're already
logged in and ask us to log out if we're somebody else.

    >>> browser.open("%s/+login" % root_url)
    >>> print(extract_text(find_main_content(browser.contents)))
    You are already logged in...

The same thing works if the user has non-ASCII characters in their display
name.

    >>> from lp.testing import (
    ...     ANONYMOUS,
    ...     login,
    ... )
    >>> from lp.testing.factory import LaunchpadObjectFactory

    >>> login(ANONYMOUS)
    >>> factory = LaunchpadObjectFactory()
    >>> person = factory.makePerson(
    ...     email="unicode@example.com",
    ...     name="unicode",
    ...     displayname="Un\xedc\xf6de Person",
    ... )
    >>> browser = Browser()
    >>> browser.handleErrors = True
    >>> browser.open("%s/people/?name=foo&searchfor=all" % root_url)
    >>> browser.getLink("Log in / Register").click()
    >>> print(browser.contents)
    <html>...<body onload="document.forms[0].submit();"...
    >>> browser.getControl("Continue").click()
    >>> print(browser.title)
    Login
    >>> fill_login_form_and_submit(browser, "unicode@example.com")
    >>> print(browser.vhost)
    http://launchpad.test
    >>> browser.urlpath
    '/people'
    >>> import re
    >>> print(pretty(sorted(re.sub(".*\?", "", browser.url).split("&"))))
    ['name=foo', 'searchfor=all']
