Using BugTracker Login Tokens
=============================

Launchpad offers an XML-RPC interface for generating bug tracker tokens.

    >>> import xmlrpc.client
    >>> from zope.component import getUtility
    >>> from lp.testing.xmlrpc import XMLRPCTestTransport
    >>> from lp.services.verification.interfaces.logintoken import (
    ...     ILoginTokenSet,
    ... )
    >>> bugtracker_api = xmlrpc.client.ServerProxy(
    ...     "http://xmlrpc-private.launchpad.test:8087/bugs",
    ...     transport=XMLRPCTestTransport(),
    ... )

    >>> token_string = bugtracker_api.newBugTrackerToken()
    >>> token = getUtility(ILoginTokenSet)[token_string]

These LoginTokens are used by Launchpad to authenticate with external
bug trackers. We pass the token to the bug tracker and it then makes a
POST request to the token's canonical URL to validate it.

    >>> from lp.services.webapp import canonical_url
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> test_request = LaunchpadTestRequest(method="POST")
    >>> token_url = canonical_url(
    ...     token,
    ...     request=test_request,
    ...     rootsite="mainsite",
    ...     view_name="+bugtracker-handshake",
    ... )

    >>> print(token_url)
    http://launchpad.test/token/.../+bugtracker-handshake

Visiting the token's +bugtracker-handshake URL will result in an HTTP
200 response if the token is valid.

    >>> from zope.component import getMultiAdapter
    >>> view = getMultiAdapter(
    ...     (token, test_request), name="+bugtracker-handshake"
    ... )
    >>> view()
    'Handshake token validated.'

    >>> print(test_request.response.getStatus())
    200

The token has now been consumed.

    >>> token = getUtility(ILoginTokenSet)[token_string]
    >>> print(token.date_consumed is not None)
    True

If we try to access the +bugtracker-handshake URL again, we will receive
an HTTP 410 (Gone) response.

    >>> view = getMultiAdapter(
    ...     (token, test_request), name="+bugtracker-handshake"
    ... )
    >>> view()
    'Token has already been used or is invalid.'

    >>> print(test_request.response.getStatus())
    410

Only POST requests are valid when accessing a +bugtracker-handshake URL.
If we attempt another request method, such as a GET, we will receive an
HTTP 405 (Method Not Allowed) response.

    >>> token_string = bugtracker_api.newBugTrackerToken()
    >>> token = getUtility(ILoginTokenSet)[token_string]
    >>> test_request = LaunchpadTestRequest(method="GET")

    >>> view = getMultiAdapter(
    ...     (token, test_request), name="+bugtracker-handshake"
    ... )
    >>> view()
    'Only POST requests are accepted for bugtracker handshakes.'

    >>> print(test_request.response.getStatus())
    405

However, since the request was invalid the token will not have been
consumed.

    >>> token = getUtility(ILoginTokenSet)[token_string]
    >>> print(token.date_consumed)
    None
