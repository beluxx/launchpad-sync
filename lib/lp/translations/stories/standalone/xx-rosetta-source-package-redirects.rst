Checks that the '+pots/' page redirects always to the '+translations' one.

    >>> print(
    ...     http(
    ...         r"""
    ... GET /ubuntu/hoary/+source/evolution/+pots/ HTTP/1.1
    ... Accept-Language: en-gb,en;q=0.5
    ... Host: translations.launchpad.test
    ... """
    ...     )
    ... )
    HTTP/1.1 303 See Other
    Content-Length: 0
    ...
    Content-Type: text/plain;charset=utf-8
    Location: ../+translations
    ...

Checks that the '+pots' page redirects always to the '+translations' one.

    >>> print(
    ...     http(
    ...         r"""
    ... GET /ubuntu/hoary/+source/evolution/+pots HTTP/1.1
    ... Accept-Language: en-gb,en;q=0.5
    ... Host: translations.launchpad.test
    ... """
    ...     )
    ... )
    HTTP/1.1 303 See Other
    ...
    Location: .../ubuntu/hoary/+source/evolution/+pots...
    ...

Checks that the '+sources/.../+translate' page redirects always to the
'+source/.../+translations' one. This redirect is used by the
Ubuntu Launchpad Integration in old releases of Ubuntu.
This redirect must be supported for at least five years after the release of
Hardy, which is 2013-04.  Please consult with the Ubuntu Desktop team before
removing.

    >>> print(
    ...     http(
    ...         r"""
    ... GET /ubuntu/hoary/+sources/evolution/+translate HTTP/1.1
    ... Accept-Language: en-gb,en;q=0.5
    ... Host: translations.launchpad.test
    ... """
    ...     )
    ... )
    HTTP/1.1 301 Moved Permanently
    Content-Length: 0
    ...
    Content-Type: text/plain;charset=utf-8
    Location: .../+source/evolution/+translations
    ...
