========================================
Logging in using the TestOpenID provider
========================================

A user with an existing account may log into Launchpad using the OpenID
provider available on testopenid.test.

First we will set up the helper view that lets us test the final
portion of the authentication process:

    >>> from openid.consumer.consumer import Consumer
    >>> from openid.fetchers import setDefaultFetcher
    >>> from openid.store.memstore import MemoryStore
    >>> from lp.testopenid.testing.helpers import (
    ...     complete_from_browser, make_identifier_select_endpoint,
    ...     ZopeFetcher)
    >>> setDefaultFetcher(ZopeFetcher())

The authentication process is started by the relying party issuing a
checkid_setup request, sending the user to Launchpad:

    >>> openid_store = MemoryStore()
    >>> consumer = Consumer(session={}, store=openid_store)

    >>> request = consumer.beginWithoutDiscovery(
    ...     make_identifier_select_endpoint())
    >>> browser.open(request.redirectURL(
    ...     'http://testopenid.test/',
    ...     'http://testopenid.test/+echo'))

At this point, the user is presented with a login form:

    >>> print(browser.title)
    Login

If the email address isn't registered, an error is shown:

    >>> browser.getControl(name='field.email').value = 'does@not.exist'
    >>> browser.getControl('Continue').click()
    >>> print(browser.title)
    Login
    >>> for tag in find_tags_by_class(browser.contents, 'error'):
    ...     print(extract_text(tag))
    There is 1 error.
    Unknown email address.

If the email address matches an account, the user is logged in and
returned to the relying party, with the user's identity URL:

    >>> browser.getControl(name='field.email').value = 'mark@example.com'
    >>> browser.getControl('Continue').click()
    >>> print(browser.url)
    http://testopenid.test/+echo?...
    >>> info = complete_from_browser(consumer, browser)
    >>> print(info.status)
    success
    >>> print(info.endpoint.claimed_id)
    http://testopenid.test/+id/mark_oid

    # Clean up the changes we did to the openid module.
    >>> setDefaultFetcher(None)
