  Change the owner of the mozilla project.


  Logged in as no-priv@canonical.com we can't do that, because they're not the
  owner of the project nor a member of admins.

    >>> print(
    ...     http(
    ...         r"""
    ... GET /mozilla/+reassign HTTP/1.1
    ... Authorization: Basic no-priv@canonical.com:test
    ... """
    ...     )
    ... )
    HTTP/1.1 403 Forbidden
    ...


  Now we're logged in as mark@example.com and he's the owner of the admins team,
  so he can do everything.

    >>> print(
    ...     http(
    ...         r"""
    ... GET /mozilla/+reassign HTTP/1.1
    ... Authorization: Basic mark@example.com:test
    ... """
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...
    ...Current:...
    ...
    ...New:...
    ...


  Here he changes the owner to himself.

    >>> print(
    ...     http(
    ...         r"""
    ... POST /mozilla/+reassign HTTP/1.1
    ... Authorization: Basic mark@example.com:test
    ... Referer: https://launchpad.test/
    ...
    ... field.owner=mark&field.existing=existing"""
    ...         r"""&field.actions.change=Change"""
    ...     )
    ... )
    HTTP/1.1 303 See Other
    ...
    Location: http://localhost/mozilla
    ...



  Here we see the new owner: Mark Shuttleworth

    >>> print(
    ...     http(
    ...         r"""
    ... GET /mozilla/ HTTP/1.1
    ... Authorization: Basic mark@example.com:test
    ... """
    ...     )
    ... )
    HTTP/1.1 200 Ok
    Content-Length: ...
    Content-Type: text/html;charset=utf-8
    ...
    ...Maintainer:...
    ...
    ...Mark Shuttleworth...
    ...
