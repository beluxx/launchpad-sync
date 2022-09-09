Edit person time zone information
=================================

A person's time zone is only editable by people who have launchpad.Edit on
the person, which is that person and admins.

    >>> login("test@canonical.com")
    >>> zzz = factory.makePerson(
    ...     name="zzz", time_zone="Africa/Maseru", email="zzz@foo.com"
    ... )
    >>> logout()

A user cannot set another user's +editlocation page.

    >>> nopriv_browser = setupBrowser(auth="Basic no-priv@canonical.com:test")
    >>> nopriv_browser.open("http://launchpad.test/~zzz/+editlocation")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

A user can set their own time zone:

    >>> self_browser = setupBrowser(auth="Basic zzz@foo.com:test")
    >>> self_browser.open("http://launchpad.test/~zzz")
    >>> self_browser.getLink("Set location and time zone").click()
    >>> self_browser.getControl(name="field.time_zone").value = [
    ...     "Europe/Madrid"
    ... ]
    >>> self_browser.getControl("Update").click()

    >>> login("zzz@foo.com")
    >>> print(zzz.time_zone)
    Europe/Madrid
    >>> logout()

And when they come back to change it later, they'll see it there as the
selected value.

    >>> self_browser.open("http://launchpad.test/~zzz")
    >>> self_browser.getLink("Set location and time zone").click()
    >>> print(self_browser.getControl(name="field.time_zone").value)
    ['Europe/Madrid']
