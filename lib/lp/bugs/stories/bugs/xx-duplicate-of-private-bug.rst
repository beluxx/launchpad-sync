Showing a duplicate of a private bug
====================================

When showing a duplicate of a private bug, the title of the private
bug is not included in the page if the user does not have permission
to view the private bug.

First we mark a bug as private:

    >>> admin_browser.open(
    ...     "http://bugs.launchpad.test/"
    ...     "debian/+source/mozilla-firefox/+bug/8/+secrecy"
    ... )
    >>> admin_browser.getControl("Private", index=1).selected = True
    >>> admin_browser.getControl("Change").click()
    >>> print(admin_browser.url)
    http://bugs.launchpad.test/debian/+source/mozilla-firefox/+bug/8

    >>> print(admin_browser.title)
    Bug #8 ...Printing doesn't work...

    >>> print(extract_text(find_tag_by_id(admin_browser.contents, "privacy")))
    This report contains Private information...

Next we mark another bug as a duplicate of the private bug:

    >>> admin_browser.open(
    ...     "http://bugs.launchpad.test/"
    ...     "ubuntu/+source/linux-source-2.6.15/+bug/10/+duplicate"
    ... )
    >>> admin_browser.getControl("Duplicate Of").value = "8"
    >>> admin_browser.getControl("Set Duplicate").click()

As a privileged user the title of the private bug can be found in the
duplicate bug page:

    >>> def print_messages(browser):
    ...     for tag in find_tags_by_class(browser.contents, "message"):
    ...         print(tag.decode_contents())
    ...

    >>> print(
    ...     find_tag_by_id(
    ...         admin_browser.contents, "duplicate-of"
    ...     ).decode_contents()
    ... )
    bug #8

But when accessing it as an unprivileged user the title of the private
bug cannot be found in the messages on the duplicate bug page:

    >>> user_browser.open(admin_browser.url)
    >>> print(find_tag_by_id(user_browser.contents, "duplicate-of"))
    None

The same is true when viewing the duplicate bug anonymously:

    >>> anon_browser.open(admin_browser.url)
    >>> print(find_tag_by_id(anon_browser.contents, "duplicate-of"))
    None
