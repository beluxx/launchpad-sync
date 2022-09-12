Sometimes a stale bookmark or hand-hacked URL causes invalid form data
to be sent to the server. In this case, an UnexpectedFormData exception
is raised.

    >>> browser.open(
    ...     "http://localhost/ubuntu/+bugs?search=Search&field.status=Fred"
    ... )
    Traceback (most recent call last):
      ...
    lp.app.errors.UnexpectedFormData: Unexpected value for field 'status'...

    >>> browser.open(
    ...     "http://localhost/ubuntu/+bugs?search=Search&orderby=foobar"
    ... )
    Traceback (most recent call last):
      ...
    lp.app.errors.UnexpectedFormData: Unknown sort column 'foobar'

    >>> browser.open(
    ...     "http://launchpad.test/firefox/+bugs?"
    ...     "field.status_upstream=hide_open"
    ... )
    Traceback (most recent call last):
      ...
    lp.app.errors.UnexpectedFormData: Unexpected value for field
    'status_upstream'...

When a UnexpectedFormData is raised, we display a custom error page to the
user.

    >>> output = str(
    ...     http(
    ...         rb"""
    ... GET /ubuntu/+bugs?search=Search&field.status=Fred HTTP/1.1
    ... """
    ...     )
    ... )
    >>> "HTTP/1.1 500 Internal Server Error" in output
    True
    >>> "Unexpected form data" in output
    True
    >>> message = (
    ...     "Launchpad doesn't understand the form data submitted in"
    ...     " this request"
    ... )
    >>> message in output
    True
