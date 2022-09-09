Developer exceptions
====================

Launchpad developers get tracebacks and a linkified OOPS if an exception
occurs. Other users get no traceback and only the OOPS ID.

To be able to test, a page that generates HTTP 500 errors is registered.
Accessing that page gives us the OOPS error page.

    >>> from zope.interface import Interface
    >>> from zope.publisher.interfaces.browser import IDefaultBrowserLayer
    >>> from lp.testing.fixture import ZopeAdapterFixture

    >>> class ErrorView:
    ...     """A broken view"""
    ...
    ...     def __call__(self, *args, **kw):
    ...         raise Exception("Oops")
    ...
    >>> error_view_fixture = ZopeAdapterFixture(
    ...     ErrorView, (None, IDefaultBrowserLayer), Interface, "error-test"
    ... )
    >>> error_view_fixture.setUp()

As our test runner runs in 'always show tracebacks' mode, we need to
switch this off for these tests to work

    >>> from lp.services.config import config
    >>> from textwrap import dedent
    >>> test_data = dedent(
    ...     """
    ...     [canonical]
    ...     show_tracebacks: False
    ...     """
    ... )
    >>> config.push("test_data", test_data)
    >>> config.canonical.show_tracebacks
    False

Anonymous users don't get tracebacks.

    >>> result = http(
    ...     r"""
    ... GET /error-test HTTP/1.1
    ... """
    ... )
    >>> "Traceback" in str(result)
    False

And the OOPS ID is displayed but not linkified.

    >>> print(find_main_content(str(result)))
    <...
    <h1 class="exception">Oops!</h1>
    ...
    <code class="oopsid">OOPS-...</code>)
    ...

Launchpad developers logged in via Basic Auth get tracebacks.
In this case, we are logged in as the foo.bar@canonical.com user.

    >>> result = http(
    ...     r"""
    ... GET /error-test HTTP/1.1
    ... Authorization: Basic Zm9vLmJhckBjYW5vbmljYWwuY29tOnRlc3Q=
    ... """
    ... )
    >>> "Traceback" in str(result)
    True

And the OOPS ID is displayed and linkified.

    >>> print(find_main_content(str(result)))
    <...
    <h1 class="exception">Oops!</h1>
    ...
    <a href=...oopsid=OOPS-...><code class="oopsid">OOPS-...</code></a>)
    ...

Other users logged in via basic auth don't get tracebacks. In this
case, Carlos.

    >>> result = http(
    ...     r"""
    ... GET /error-test HTTP/1.1
    ... Authorization: Basic Y2FybG9zQGNhbm9uaWNhbC5jb206dGVzdA==
    ... """
    ... )
    >>> "Traceback" in str(result)
    False

And the OOPS ID is displayed but not linkified.

    >>> print(find_main_content(str(result)))
    <...
    <h1 class="exception">Oops!</h1>
    ...
    <code class="oopsid">OOPS-...</code>)
    ...

To avoid affecting other tests, reset the show_tracebacks config item and
unregister the adapter.

    >>> test_config_data = config.pop("test_data")
    >>> config.canonical.show_tracebacks
    True
    >>> error_view_fixture.cleanUp()


http handle_errors
==================

lp.testing.pages.http accepts the handle_errors parameter in case you
want to see tracebacks instead of error pages.

    >>> print(
    ...     http(
    ...         r"""
    ... GET /whatever HTTP/1.1
    ... """,
    ...         handle_errors=False,
    ...     )
    ... )
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...
