Delete a productseries
======================

A project series can be made by accident and the project owner or driver
may choose to delete it. Sample Person is the owner of the Firefox
project and they want to delete the trunk series because development
is really happening in the 1.0 series.

    >>> owner_browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> owner_browser.open("http://launchpad.test/firefox/trunk")
    >>> print(owner_browser.title)
    Series trunk : Mozilla Firefox

    >>> owner_browser.getLink("Delete series").click()
    >>> print(owner_browser.title)
    Delete Mozilla Firefox trunk series...

The trunk series is the focus of development. It cannot be deleted.
The owner learns that they must make another series the focus of development
first. There is no delete button on the page.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(owner_browser.contents, "cannot-delete")
    ...     )
    ... )
    You cannot delete a series that is the focus of development. Make
    another series the focus of development before deleting this one.
    You cannot delete a series that is linked to packages in distributions.
    You can remove the links from the project packaging page.

    >>> owner_browser.getControl("Delete this Series")
    Traceback (most recent call last):
     ...
    LookupError: ...

Sample person chooses to cancel the action and make the 1.0 series the focus
of development. They then remove the linked package which they believe is
bogus.

    >>> owner_browser.getLink("Cancel").click()
    >>> owner_browser.open("http://launchpad.test/firefox/+edit")
    >>> print(owner_browser.title)
    Change Mozilla Firefox's details...

    >>> owner_browser.getControl("Development focus").value = ["2"]
    >>> owner_browser.getControl("Change").click()
    >>> print(owner_browser.title)
    Mozilla Firefox in Launchpad

    >>> owner_browser.getLink("All packages").click()
    >>> link = owner_browser.getLink(
    ...     url="/ubuntu/warty/+source/mozilla-firefox/+remove-packaging"
    ... )
    >>> link.click()
    >>> owner_browser.getControl("Unlink").click()

Then they return to delete trunk. They are informed that deletion is
permanent, and that the milestones, releases, and files will also be
deleted. The milestones and releases are linked.

    >>> owner_browser.getLink("trunk series").click()
    >>> owner_browser.getLink("Delete series").click()
    >>> print(owner_browser.title)
    Delete Mozilla Firefox trunk series...

    >>> contents = find_main_content(owner_browser.contents)
    >>> print(extract_text(find_tag_by_id(contents, "milestones-and-files")))
    The associated milestones and releases
    and their files will be also be deleted:

    >>> print(extract_text(find_tag_by_id(contents, "milestones")))
    0.9.2 "One (secure) Tree Hill"
    0.9.1 "One Tree Hill (v2)"
    0.9 "One Tree Hill"
    1.0

    >>> print(owner_browser.getLink('0.9.2 "One (secure) Tree Hill"'))
    <Link text='0.9.2 "One (secure) Tree Hill"' ...>

    >>> print(extract_text(find_tag_by_id(contents, "files")))
    firefox_0.9.2.orig.tar.gz

    >>> print(
    ...     extract_text(find_tag_by_id(contents, "bugtasks-and-blueprints"))
    ... )
    Support E4X in EcmaScript

The owner deletes the series and the project page is displayed. They read
that the series was deleted, and can not see a link to it anymore.

    >>> owner_browser.getControl("Delete this Series").click()
    >>> print(owner_browser.title)
    Mozilla Firefox in Launchpad

    >>> print_feedback_messages(owner_browser.contents)
    Series trunk deleted.

    >>> owner_browser.getLink("trunk")
    Traceback (most recent call last):
     ...
    zope.testbrowser.browser.LinkNotFoundError

A series with translations can never be deleted. The project owner or
release manager sees the explanation when they try to delete the series.

    >>> owner_browser.open("http://launchpad.test/evolution/trunk")
    >>> owner_browser.getLink("Delete series").click()
    >>> print(owner_browser.title)
    Delete Evolution trunk series ...

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(owner_browser.contents, "cannot-delete")
    ...     )
    ... )
    You ...
    This series cannot be deleted because it has translations.
