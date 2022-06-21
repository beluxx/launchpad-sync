When editing a bugtask, you may subscribe to the bug report as well, if
you're not already subscribed.

    >>> browser = setupBrowser(auth="Basic foo.bar@canonical.com:test")
    >>> browser.open(
    ...     "http://launchpad.test/firefox/+bug/5/+editstatus")

    >>> browser.getControl("Status").value = ["Confirmed"]
    >>> browser.getControl("Comment on this change (optional)").value = "test"
    >>> browser.getControl(
    ...     "Email me about changes to this bug report").selected = True

    >>> browser.getControl("Save Changes").click()

    >>> print(browser.contents)
    <!DOCTYPE...
    ...You have subscribed to this bug report...

If you're already subscribed, the checkbox is not shown.

    >>> browser.open(
    ...     "http://launchpad.test/firefox/+bug/5/+editstatus")

    >>> browser.getControl("Email me about changes to this bug report")
    Traceback (most recent call last):
      ...
    LookupError: ...

