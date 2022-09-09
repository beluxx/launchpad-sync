The distribution bugs listing includes a portlet showing bug
statistics. Each statistic is "linkified"; when clicked, the listing
will be filtered to show just the bugs counted by that statistic.

This document demonstrates the correct functioning of the various
statistics links.

Debian must enable the Launchpad bug tracker to access bugs.

    >>> from lp.testing.service_usage_helpers import set_service_usage
    >>> set_service_usage("debian", bug_tracking_usage="LAUNCHPAD")

Viewing critical bugs as Sample Person:

    >>> print(
    ...     http(
    ...         rb"""
    ... GET /debian/+bugs?field.status%3Alist=New&field.status%3Alist=Confirmed&field.importance%3Alist=Critical&search=Search HTTP/1.1
    ... Authorization: Basic dGVzdEBjYW5vbmljYWwuY29tOnRlc3Q=
    ... """
    ...     )
    ... )  # noqa
    HTTP/1.1 200 Ok
    ...No results for search...

Viewing bugs "assigned to me", as Sample Person:

    >>> print(
    ...     http(
    ...         rb"""
    ... GET /debian/+bugs?field.status%3Alist=New&field.status%3Alist=Confirmed&field.assignee=name12&search=Search HTTP/1.1
    ... Authorization: Basic dGVzdEBjYW5vbmljYWwuY29tOnRlc3Q=
    ... """
    ...     )
    ... )  # noqa
    HTTP/1.1 200 Ok
    ...1 result...

Viewing untriaged bugs as Sample Person:

    >>> print(
    ...     http(
    ...         rb"""
    ... GET /debian/+bugs?field.status%3Alist=New&search=Search HTTP/1.1
    ... Authorization: Basic dGVzdEBjYW5vbmljYWwuY29tOnRlc3Q=
    ... """
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...1 result...

Viewing unassigned bugs as Sample Person:

    >>> print(
    ...     http(
    ...         rb"""
    ... GET /debian/+bugs?field.status%3Alist=New&field.status%3Alist=Confirmed&field.status-empty-marker=1&field.importance-empty-marker=1&field.assignee=&assignee_option=none&search=Search HTTP/1.1
    ... Authorization: Basic dGVzdEBjYW5vbmljYWwuY29tOnRlc3Q=
    ... """
    ...     )
    ... )  # noqa
    HTTP/1.1 200 Ok
    ...2 results...

Viewing open reported bugs as Sample Person:

    >>> print(
    ...     http(
    ...         rb"""
    ... GET /debian/+bugs?search=Search HTTP/1.1
    ... Authorization: Basic dGVzdEBjYW5vbmljYWwuY29tOnRlc3Q=
    ... """
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...3 results...
