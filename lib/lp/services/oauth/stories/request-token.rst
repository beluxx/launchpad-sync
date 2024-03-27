Asking for a request token
==========================

Our sample consumer (whose key is 'foobar123451432') asks Launchpad for
a request token which may later be exchanged for an access token.

    >>> from urllib.parse import urlencode
    >>> data = dict(
    ...     oauth_consumer_key="foobar123451432",
    ...     oauth_version="1.0",
    ...     oauth_signature_method="PLAINTEXT",
    ...     oauth_signature="&",
    ... )
    >>> anon_browser.open(
    ...     "http://launchpad.test/+request-token", data=urlencode(data)
    ... )

    >>> print(anon_browser.contents)
    oauth_token=...&oauth_token_secret=...

The consumer can ask for a JSON representation of the request token,
which will also include information about the available permission
levels.

    >>> import json
    >>> from lp.testing.pages import setupBrowser

    >>> json_browser = setupBrowser()
    >>> json_browser.addHeader("Accept", "application/json")
    >>> json_browser.open(
    ...     "http://launchpad.test/+request-token", data=urlencode(data)
    ... )
    >>> token = json.loads(json_browser.contents)
    >>> sorted(token.keys())
    ['access_levels', 'oauth_token', 'oauth_token_consumer',
     'oauth_token_secret']

    >>> sorted(
    ...     (level["value"], level["title"])
    ...     for level in token["access_levels"]
    ... )
    [('READ_PRIVATE', 'Read Anything'),
     ('READ_PUBLIC', 'Read Non-Private Data'),
     ('UNAUTHORIZED', 'No Access'),
     ('WRITE_PRIVATE', 'Change Anything'),
     ('WRITE_PUBLIC', 'Change Non-Private Data')]

If the consumer key is not yet registered, we register it automatically
so that the application can proceed.

    >>> from zope.component import getUtility
    >>> from lp.testing import login, logout
    >>> from lp.services.oauth.interfaces import IOAuthConsumerSet
    >>> login("salgado@ubuntu.com")
    >>> print(getUtility(IOAuthConsumerSet).getByKey("joe-feed-reader"))
    None

    >>> logout()
    >>> data2 = data.copy()
    >>> data2["oauth_consumer_key"] = "joe-feed-reader"
    >>> anon_browser.open(
    ...     "http://launchpad.test/+request-token", data=urlencode(data2)
    ... )

    >>> print(anon_browser.contents)
    oauth_token=...&oauth_token_secret=...

    >>> login("salgado@ubuntu.com")
    >>> getUtility(IOAuthConsumerSet).getByKey("joe-feed-reader")
    <...OAuthConsumer...
    >>> logout()

If the consumer key is empty, we respond with a 401 status.

    >>> data2 = data.copy()
    >>> data2["oauth_consumer_key"] = ""
    >>> print(
    ...     http(
    ...         r"""
    ... GET /+request-token?%s HTTP/1.1
    ... Host: launchpad.test
    ... """
    ...         % urlencode(data2)
    ...     )
    ... )
    HTTP/1.1 401 Unauthorized
    ...
    WWW-Authenticate: OAuth realm="https://api.launchpad.net"
    ...

The only signature method supported is PLAINTEXT, which consists of the
concatenated values of the consumer secret and token secret, separated
by a & character. That means, in our case, the signature should be only
an '&', since there's no token yet and the consumer secret is empty.

    >>> print(data["oauth_signature"])
    &
    >>> data2 = data.copy()
    >>> data2["oauth_signature"] = "&somesecret"
    >>> print(
    ...     http(
    ...         r"""
    ... GET /+request-token?%s HTTP/1.1
    ... Host: launchpad.test
    ... """
    ...         % urlencode(data2)
    ...     )
    ... )
    HTTP/1.1 401 Unauthorized
    ...

If the consumer tries to sign a request with a different method, it will
get a 400 response.

    >>> data2 = data.copy()
    >>> data2["oauth_signature_method"] = "HMAC-SHA1"
    >>> print(
    ...     http(
    ...         r"""
    ... GET /+request-token?%s HTTP/1.1
    ... Host: launchpad.test
    ... """
    ...         % urlencode(data2)
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
