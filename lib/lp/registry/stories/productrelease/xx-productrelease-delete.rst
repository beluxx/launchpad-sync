Deleting product releases
=========================

The main page of a product series includes a list of releases of that series.
The 0.9.2 milestone has a release.

    >>> user_browser.open("http://launchpad.test/firefox/trunk")
    >>> print(user_browser.title)
    Series trunk : Mozilla Firefox

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(user_browser.contents, "series-trunk")
    ...     )
    ... )
    Version                    Expected   Released     Summary
    Mozilla Firefox 0.9.2 ...  None       2004-10-15   ...

A User with launchpad.Edit rights for a release can see the delete link and
access the delete page. A user without the necessary rights won't see the
link and cannot access the +delete page.

    >>> user_browser.getLink("0.9.2").click()
    >>> print(user_browser.title)
    0.9.2 "One (secure) Tree Hill" : Mozilla Firefox

    >>> user_browser.getLink(url="/firefox/trunk/0.9.2/+delete")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.open("http://launchpad.test/firefox/trunk/0.9.2/+delete")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Salgado has the necessary rights, so he sees the link and the +delete page.

    >>> salgados_browser = setupBrowser(auth="Basic salgado@ubuntu.com:test")
    >>> salgados_browser.open("http://launchpad.test/firefox/trunk/0.9.2")
    >>> salgados_browser.getLink("Delete release").click()
    >>> print(salgados_browser.title)
    Delete Mozilla Firefox 0.9.2...

The 0.9.2 release has some files associated with it. Salgado reads that
they will be deleted too.

    >>> text = extract_text(find_main_content(salgados_browser.contents))
    >>> print(backslashreplace(text))
    Delete Mozilla Firefox 0.9.2 \u201cOne (secure) Tree Hill\u201d
    ...
    Are you sure you want to delete the 0.9.2 release of
    Mozilla Firefox trunk series?
    The following files must be deleted:
    firefox_0.9.2.orig.tar.gz...

Salgado chooses the delete button, then reads that the action is successful.

    >>> salgados_browser.getControl("Delete Release").click()
    >>> print(salgados_browser.title)
    Series trunk : Mozilla Firefox

    >>> print_feedback_messages(salgados_browser.contents)
    Release 0.9.2 deleted.

Milestone 0.9.2 no longer has a release. The release column explains that
the milestone is inactive.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(salgados_browser.contents, "series-trunk")
    ...     )
    ... )
    ... # noqa
    Version                   Expected              Released      Summary
    Mozilla Firefox 0.9.2...  Set date  Change details   This is an inactive ...
