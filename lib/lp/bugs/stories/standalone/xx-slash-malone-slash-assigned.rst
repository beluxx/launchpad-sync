To access /malone/assigned we have to be logged in.

    >>> print(
    ...     http(
    ...         rb"""
    ... GET /bugs/assigned HTTP/1.1
    ... """
    ...     )
    ... )
    HTTP/1.1 303 See Other
    ...
    Location: http://localhost/bugs/assigned/+login
    ...


When we're logged in as Foo Bar we can see our own bugs. Note that
/malone/assigned has been deprecated, in favour of the equivalent
report (at least by intent, if not by design) in FOAF.

    >>> print(
    ...     http(
    ...         rb"""
    ... GET /bugs/assigned HTTP/1.1
    ... Authorization: Basic Zm9vLmJhckBjYW5vbmljYWwuY29tOnRlc3Q=
    ... """
    ...     )
    ... )
    HTTP/1.1 303 See Other
    ...
    Location: http://localhost/~name16/+assignedbugs
    ...
