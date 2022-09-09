Logging into a Mantis instance
------------------------------

Mantis is... special. In a headless/batch environment we must do a
little dance in order to log in. Thankfully, we can encapsulate this
neatly in a requests hook.


mantis_login_hook
=================

    >>> from requests import Response
    >>> from lp.bugs.externalbugtracker.mantis import mantis_login_hook

    >>> def run_hook(url, status_code=302):
    ...     response = Response()
    ...     response.status_code = status_code
    ...     response.headers["Location"] = url
    ...     response = mantis_login_hook(response)
    ...     print(response.headers["Location"])
    ...

It has one simple responsibility, which is to intercept redirections
to the login page, at which point it rewrites the URL to go straight
to the login form handler with a default user name and password.

Normally the hook makes no modifications to the URL:

    >>> run_hook("https://mantis.example.com/")
    https://mantis.example.com/

    >>> run_hook("http://mantis.example.com/view.php?id=123")
    http://mantis.example.com/view.php?id=123

The hook doesn't touch any non-redirect responses.

    >>> run_hook(
    ...     "http://mantis.example.com/login_page.php"
    ...     "?return=%2Fview.php%3Fid%3D3301",
    ...     status_code=200,
    ... )
    http://.../login_page.php?return=%2Fview.php%3Fid%3D3301

When Mantis redirects us to the login page, the hook comes into
play. Note how Mantis adds a "return" query parameter: if we log in
successfully, Mantis will redirect us to the page this specifies.

    >>> run_hook(
    ...     "http://mantis.example.com/login_page.php"
    ...     "?return=%2Fview.php%3Fid%3D3301"
    ... )
    http://.../login.php?username=guest&password=guest&return=...

If Mantis does not specify a "return" query parameter an error will be
raised.

Apart from the fact that we rely on Mantis to return us to the page we
originally requested, this can also mean that we failed to log in:
when Mantis redirects back to the login page with an error it forgets
the "return" parameter.

    >>> run_hook("http://mantis.example.com/login_page.php")
    Traceback (most recent call last):
      ...
    lp.bugs.externalbugtracker.base.BugTrackerConnectError:
    http://mantis.example.com/login_page.php: Mantis redirected us to the
    login page but did not set a return path.

In all likelihood, this warning will be followed in the log by an
error.
