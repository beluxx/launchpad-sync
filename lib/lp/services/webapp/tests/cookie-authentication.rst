The feeds vhost should not set the cookie. Since it is running
on http instead of https, it cannot read the secure cookie on https,
so it cannot tell that it will end up overwriting the existing cookie.

    >>> from lp.testing.layers import BaseLayer
    >>> feeds_root_url = BaseLayer.appserver_root_url('feeds')
    >>> browser.open('%s/announcements.atom' % feeds_root_url)
    >>> print(browser.vhost)
    http://feeds.launchpad.test
    >>> browser.urlpath
    '/announcements.atom'
    >>> len(browser.cookies)
    0

Our cookies need to have their domain attribute set to ensure that they
are sent to other vhosts in the same domain.

    >>> blueprints_root_url = BaseLayer.appserver_root_url('blueprints')
    >>> browser.open('%s/+login' % blueprints_root_url)

    # On a browser with JS support, this page would've been automatically
    # submitted (thanks to the onload handler), but testbrowser doesn't
    # support JS, so we have to submit the form manually.
    >>> print(browser.contents)
    <html>...<body onload="document.forms[0].submit();"...
    >>> browser.getControl('Continue').click()

    >>> from lp.services.webapp.tests.test_login import (
    ...     fill_login_form_and_submit)
    >>> fill_login_form_and_submit(browser, 'foo.bar@canonical.com')
    >>> print(extract_text(find_tag_by_id(browser.contents, 'logincontrol')))
    Foo Bar (name16) ...

    # Open a page again so that we see the cookie for a launchpad.test request
    # and not a testopenid.test request (as above).
    >>> browser.open(blueprints_root_url)
    >>> len(browser.cookies)
    1
    >>> browser.cookies.keys()
    ['launchpad_tests']
    >>> session_cookie_name = browser.cookies.keys()[0]
    >>> browser.cookies.getinfo(session_cookie_name)['domain']
    '.launchpad.test'

If we visit another vhost in the domain, we remain logged in.

    >>> root_url = BaseLayer.appserver_root_url()
    >>> browser.open(root_url)
    >>> print(browser.vhost)
    http://launchpad.test
    >>> browser.urlpath
    '/'
    >>> print(extract_text(find_tag_by_id(browser.contents, 'logincontrol')))
    Foo Bar (name16) ...
    >>> browser.cookies.getinfo(session_cookie_name)['domain']
    '.launchpad.test'

Even if the browser passes in a cookie, the feeds vhost should not set one.

    >>> browser.open('%s/announcements.atom' % feeds_root_url)
    >>> print(browser.vhost)
    http://feeds.launchpad.test
    >>> browser.urlpath
    '/announcements.atom'
    >>> print(browser.headers.get('Set-Cookie'))
    None

# XXX stub 20060816 bug=56601: We need to test that for https: URLs, the
# secure attribute is set on the cookie.
