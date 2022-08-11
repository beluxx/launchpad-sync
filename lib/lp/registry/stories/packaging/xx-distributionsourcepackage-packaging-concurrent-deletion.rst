Concurrent Deletion of Packaging
================================

When two browsers are used to concurrently delete the same packaging
association, only one of them can succeed. The other one does not oops
and displays a meaningful error message.

The No Privilege User may open the same page in two browser tabs.

    >>> first_browser = setupBrowser(auth='Basic test@canonical.com:test')
    >>> first_browser.open('http://launchpad.test/ubuntu/+source/alsa-utils')

    >>> second_browser = setupBrowser(auth='Basic test@canonical.com:test')
    >>> second_browser.open('http://launchpad.test/ubuntu/+source/alsa-utils')

Then the user click the "Delete Link" button in the first tab. The
deletion succeeds and the usual informational message is displayed.

    >>> link = first_browser.getLink(
    ...     url='/ubuntu/warty/+source/alsa-utils/+remove-packaging')
    >>> link.click()
    >>> first_browser.getControl('Unlink').click()
    >>> content = first_browser.contents
    >>> for tag in find_tags_by_class(content, 'error'):
    ...     print(extract_text(tag))
    >>> for tag in find_tags_by_class(content, 'informational'):
    ...     print(extract_text(tag))
    Removed upstream association between alsa-utils trunk series and Warty.

A few minutes later, the user sees the same packaging association in the
second tab, and clicks the "Delete Link" button again.

The packaging object has been deleted already, so this action cannot
succeed.

    >>> second_browser.getLink(
    ...     url='/ubuntu/warty/+source/alsa-utils/+remove-packaging').click()
    >>> content = second_browser.contents
    >>> for tag in find_tags_by_class(content, 'informational'):
    ...     print(extract_text(tag))
    >>> for tag in find_tags_by_class(content, 'error'):
    ...     print(extract_text(tag))
    This upstream association was deleted already.
