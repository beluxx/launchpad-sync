Because milestones are associated with products or distros, reassigning
a bugtask to a different product forces the milestone value to None,
even if the user was trying to set the milestone value.

    >>> browser = setupBrowser(auth="Basic foo.bar@canonical.com:test")
    >>> browser.open("http://bugs.launchpad.test/firefox/+bug/1/+editstatus")
    >>> browser.getControl(name="firefox.target.product").value = "evolution"
    >>> browser.getControl("Milestone").value = ["1"]
    >>> browser.getControl("Save Changes").click()

    >>> for message in find_tags_by_class(browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    The milestone setting was ignored because you reassigned the bug
    to...Evolution...

(Revert the change we just made.)

    >>> browser.open(
    ...     "http://bugs.launchpad.test/evolution/+bug/1/+editstatus"
    ... )
    >>> browser.getControl(name="evolution.target.product").value = "firefox"
    >>> browser.getControl("Save Changes").click()

(The "ignore" message doesn't appear when the user didn't set a
milestone.)

    >>> find_tags_by_class(browser.contents, "message")
    []

Likewise, reassigning a bugtask to a different product will clear the
milestone value, if one was set.

    >>> browser.open("http://localhost:9000/firefox/+bug/1/+editstatus")
    >>> browser.getControl("Milestone").value = ["1"]
    >>> browser.getControl("Save Changes").click()

    >>> browser.open("http://localhost:9000/firefox/+bug/1/+editstatus")
    >>> browser.getControl(name="firefox.target.product").value = "evolution"
    >>> browser.getControl("Save Changes").click()

    >>> for message in find_tags_by_class(browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    The Mozilla Firefox 1.0 milestone setting has been removed
    because you reassigned the bug to Evolution.
