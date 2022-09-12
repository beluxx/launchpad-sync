When the user attempts to access a bug that doesn't exist, a 404 is
raised.

    >>> print(
    ...     http(
    ...         rb"""
    ... GET http://localhost:8085/bugs/123456 HTTP/1.1
    ... """
    ...     )
    ... )
    HTTP/1.1 404 Not Found
    ...

    >>> print(
    ...     http(
    ...         rb"""
    ... GET http://localhost:8085/bugs/doesntexist HTTP/1.1
    ... """
    ...     )
    ... )
    HTTP/1.1 404 Not Found
    ...
