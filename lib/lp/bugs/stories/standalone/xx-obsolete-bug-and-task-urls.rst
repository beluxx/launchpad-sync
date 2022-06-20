We recently made obsolete two URLs in Launchpad:

1. The Anorak bug listing URL:

    >>> print(http(br"""
    ... GET http://localhost:8085/bugs/bugs HTTP/1.1
    ... Accept-Language: en-ca,en-us;q=0.8,en;q=0.5,fr-ca;q=0.3
    ... """))
    HTTP/1.1 404 Not Found
    ...

There is currently no replacement for this URL, but
/bugs/$bug.id will continue to work, for the time being.

2. The tasks namespace:

    >>> print(http(br"""
    ... GET http://localhost:8085/malone/tasks HTTP/1.1
    ... Accept-Language: en-ca,en-us;q=0.8,en;q=0.5,fr-ca;q=0.3
    ... """))
    HTTP/1.1 404 Not Found
    ...

Tasks are now accessed "contextually", like
/firefox/+bugs/$bug.id. The entire /bugs/tasks namespace
has been obsoleted, to prevent user confusion over which ID to use
when referring to a bug.
