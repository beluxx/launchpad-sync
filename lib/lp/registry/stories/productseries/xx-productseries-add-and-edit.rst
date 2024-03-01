Adding and editing product series
=================================

Adding a series
---------------

Only product owners  and drivers can add a series to product. This means that
only Sample Person can add series in the Firefox product. No Privileges
Person won't even see the link nor can access the page directly.

    >>> user_browser.open("http://launchpad.test/firefox")
    >>> user_browser.getLink("Register a series").click()
    Traceback (most recent call last):
      ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.open("http://launchpad.test/firefox/+addseries")
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

But Sample Person will and be able to add a series.

    >>> browser.addHeader("Authorization", "Basic test@canonical.com:test")
    >>> browser.open("http://launchpad.test/firefox")
    >>> browser.getLink("Register a series").click()
    >>> print(browser.url)
    http://launchpad.test/firefox/+addseries

    >>> print(
    ...     find_main_content(browser.contents).find("h1").decode_contents()
    ... )
    Register a new Mozilla Firefox release series

After checking that the page +addseries is there, we try to add a new series.

    >>> browser.getControl("Name").value = "stable"
    >>> browser.getControl("Summary").value = "Product series add testing"
    >>> browser.getControl("Branch").value = "~mark/firefox/release-0.9.2"
    >>> browser.getControl("Release URL pattern").value = (
    ...     "ftp://ftp.mozilla.org/pub/mozilla/firefox-*.tar.gz"
    ... )
    >>> browser.getControl("Register Series").click()

Now we are redirected to the Overview page of the product series we just added

    >>> browser.url
    'http://launchpad.test/firefox/stable'

    >>> print(extract_text(find_tag_by_id(browser.contents, "description")))
    Product series add testing

    >>> browser.getLink("lp://dev/~mark/firefox/release-0.9.2")
    <Link ... url='http://code.launchpad.test/~mark/firefox/release-0.9.2'>


Editing a series
----------------

Now we test if we can edit the new added series. First we check if we
can reach the +edit page.

    >>> browser.getLink("Change details").click()
    >>> browser.url
    'http://launchpad.test/firefox/stable/+edit'
    >>> browser.getControl("Name").value
    'stable'
    >>> browser.getControl("Status").displayValue
    ['Active Development']

Then we edit the information about the series. First we try to use a
name already in use and an invalid release URL pattern:

    >>> browser.getControl("Name").value = "1.0"
    >>> browser.getControl("Summary").value = (
    ...     "Testing the edit of productseries"
    ... )
    >>> browser.getControl("Release URL pattern").value = "file:///etc"
    >>> browser.getControl("Change").click()

We'll get a nice error message for the three problems:

    >>> for tag in find_tags_by_class(browser.contents, "message"):
    ...     print(extract_text(tag))
    ...
    There are 2 errors.
    1.0 is already in use by another series.
    Invalid release URL pattern.

We now change it to a unique name, a different status, and pick a branch
of firefox:

    >>> browser.getControl("Name").value = "unstable"
    >>> browser.getControl("Status").displayValue = ["Experimental"]
    >>> browser.getControl("Branch").value = "main"
    >>> browser.getControl("Release URL pattern").value = (
    ...     "http://ftp.mozilla.org/pub/mozilla.org/firefox-*.tar.gz"
    ... )
    >>> browser.getControl("Change").click()

    >>> browser.url
    'http://launchpad.test/firefox/unstable'

The new values are then shown in the series' page.

    >>> content = find_tag_by_id(browser.contents, "series-details")
    >>> print(extract_text(find_tag_by_id(content, "series-name")))
    Series: unstable

And if we try to add another series with the same name to same product, we
should get a nice error message.

    >>> browser.open("http://launchpad.test/firefox/+addseries")

    >>> browser.getControl("Name").value = "unstable"
    >>> browser.getControl("Summary").value = "The same name"
    >>> browser.getControl("Register Series").click()

    >>> for message in find_tags_by_class(browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    There is 1 error.
    unstable is already in use by another series.


Product series bug subscriptions
--------------------------------

To receive email notifications about bugs pertaining to a product series,
we can create structural bug subscriptions.

    >>> browser.open("http://launchpad.test/firefox/unstable")
    >>> browser.getLink("Subscribe to bug mail").click()
    >>> print(browser.url)
    http://launchpad.test/firefox/unstable/+subscribe
    >>> print(browser.title)
    Subscribe : Series unstable : Bugs : Mozilla Firefox
