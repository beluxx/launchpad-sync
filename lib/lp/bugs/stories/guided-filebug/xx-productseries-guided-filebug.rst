Filing a bug from the product series page
=========================================

The product series Bugs frontpage includes a link to report a bug.

    >>> user_browser.open("http://bugs.launchpad.test/firefox/trunk")
    >>> report_bug = user_browser.getLink("Report a bug")
    >>> report_bug is not None
    True

The link leads to the general product +filebug page, since we don't
support filing bugs on a product series directly.

    >>> report_bug.click()
    >>> user_browser.url
    'http://bugs.launchpad.test/firefox/+filebug'
    >>> print(user_browser.title)
    Report a bug : Bugs : Mozilla Firefox
