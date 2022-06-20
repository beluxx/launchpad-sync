Logging in
==========

The LoginStatus browser class
-----------------------------

The LoginStatus class is a view support class that handles the logic for
showing the "Log in / Register" link that appears on most pages.

    >>> from lp.app.browser.launchpad import LoginStatus
    >>> class DummyRequest(dict):
    ...
    ...     def __init__(self, appurl, path_info, query):
    ...         self['PATH_INFO'] = path_info
    ...         self['QUERY_STRING'] = query
    ...         self.appurl = appurl
    ...
    ...     def getApplicationURL(self):
    ...         return self.appurl

Generic request without query args.

    >>> request = DummyRequest('http://localhost', '/foo/bar', '')
    >>> context = object()
    >>> status = LoginStatus(context, request)
    >>> status.logged_in
    False
    >>> status.login_shown
    True
    >>> print(status.login_url)
    http://localhost/foo/bar/+login

Virtual hosted request with a trailing slash.

    >>> request = DummyRequest(
    ...     'https://staging.example.com',
    ...     '/++vh++https:staging.example.com:433/++/foo/bar/', '')
    >>> context = object()
    >>> status = LoginStatus(context, request)
    >>> print(status.login_url)
    https://staging.example.com/foo/bar/+login

Virtual hosted request with no trailing slash.

    >>> request = DummyRequest(
    ...     'https://staging.example.com',
    ...     '/++vh++https:staging.example.com:433/++/foo/bar', '')
    >>> context = object()
    >>> status = LoginStatus(context, request)
    >>> print(status.login_url)
    https://staging.example.com/foo/bar/+login

Generic request with trailing slash and query parameters.

    >>> request = DummyRequest(
    ...     'http://localhost', '/foo/bar/', 'x=1&y=2')
    >>> context = object()
    >>> status = LoginStatus(context, request)
    >>> print(status.login_url)
    http://localhost/foo/bar/+login?x=1&y=2

The login page.

    >>> request = DummyRequest(
    ...     'http://localhost', '/foo/bar/+login', '')
    >>> context = object()
    >>> status = LoginStatus(context, request)
    >>> status.logged_in
    False
    >>> status.login_shown
    False

The logout page.

    >>> request = DummyRequest(
    ...     'http://localhost', '/+logout', '')
    >>> context = object()
    >>> status = LoginStatus(context, request)
    >>> status.logged_in
    False
    >>> status.login_shown
    True
    >>> print(status.login_url)
    http://localhost/+login

The +openid-callback page.

    >>> request = DummyRequest(
    ...     'http://localhost', '/+openid-callback', '')
    >>> context = object()
    >>> status = LoginStatus(context, request)
    >>> status.logged_in
    False
    >>> status.login_shown
    True
    >>> print(status.login_url)
    http://localhost/+login

Logging in.

    >>> login('foo.bar@canonical.com')
    >>> request = DummyRequest(
    ...     'http://localhost', '/foo/bar', '')
    >>> context = object()
    >>> status = LoginStatus(context, request)
    >>> status.logged_in
    True
    >>> status.login_shown
    False
