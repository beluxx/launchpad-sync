/+soft-timeout provides a way of testing if soft timeouts work. In
order to prevent it from being abused, only Launchpad developers may
access that page.

    >>> print(http(r"""
    ... GET /+soft-timeout HTTP/1.1
    ... """))
    HTTP/1.1 303 See Other
    ...
    Location: http://.../+soft-timeout/+login
    ...

Sample Person doesn't have access to the page since they aren't a
Launchpad developer:

    >>> print(http(r"""
    ... GET /+soft-timeout HTTP/1.1
    ... Authorization: Basic dGVzdEBjYW5vbmljYWwuY29tOnRlc3Q=
    ... """))
    HTTP/1.1 403 Forbidden
    ...

Foo Bar is a Launchpad developer, so they have access to the page. Since
no timeout value is set, no soft timeout will be generated, though.

    >>> from lp.services.config import config
    >>> config.database.soft_request_timeout is None
    True

    >>> print(http(r"""
    ... GET /+soft-timeout HTTP/1.1
    ... Authorization: Basic Zm9vLmJhckBjYW5vbmljYWwuY29tOnRlc3Q=
    ... """))
    HTTP/1.1 200 Ok
    ...
    No soft timeout threshold is set.

If we set soft_request_timeout to some value, the page will take
slightly longer then the soft_request_timeout value to generate, thus
causing a soft timeout to be logged.

    >>> from textwrap import dedent
    >>> test_data = (dedent("""
    ...     [database]
    ...     soft_request_timeout: 1
    ...     """))
    >>> config.push('base_test_data', test_data)

    >>> print(http(r"""
    ... GET /+soft-timeout HTTP/1.1
    ... Authorization: Basic Zm9vLmJhckBjYW5vbmljYWwuY29tOnRlc3Q=
    ... """))
    HTTP/1.1 200 Ok
    ...
    Soft timeout threshold is set to 1 ms. This page took ... ms to render.

    >>> oops_capture.oopses[-1]['type']
    'SoftRequestTimeout'

Since the page rendered correctly, we assume it's a soft timeout error,
since otherwise we would have gotten an OOPS page when we tried to
render the page.

Let's reset the config value we changed:

    >>> test_data = config.pop('base_test_data')
