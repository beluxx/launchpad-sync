Bug statistics portlet
======================

The distribution, project group and project bug listings contain a
portlet that shows bug statistics for the target. Each statistic is a
link to filter the listing to show just those bugs. This portlet is
served in a separate request; the request is issued via Javascript and
inserted into the page later.

Distribution
------------

    >>> path = "debian"

If the user is not logged-in a subscribe link is shown along with some
general stats.

    >>> from lp.bugs.tests.bug import (
    ...     print_bugfilters_portlet_unfilled,
    ...     print_bugfilters_portlet_filled,
    ... )
    >>> print_bugfilters_portlet_unfilled(anon_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs - CVE reports


    >>> print_bugfilters_portlet_filled(anon_browser, path)
    1 New bug
    3 Open bugs
    0 In-progress bugs
    0 Critical bugs
    0 High importance bugs
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    2 Open CVE bugs - CVE reports

Once the user has identified themselves, show information on assigned and
reported bugs.

    >>> print_bugfilters_portlet_unfilled(user_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs assigned to me
    Bugs reported by me
    Bugs affecting me
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs - CVE reports


    >>> print_bugfilters_portlet_filled(user_browser, path)
    1 New bug
    3 Open bugs
    0 In-progress bugs
    0 Critical bugs
    0 High importance bugs
    <BLANKLINE>
    0 Bugs assigned to me
    0 Bugs reported by me
      Bugs affecting me
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    2 Open CVE bugs - CVE reports

The content includes a link to the distribution CVE report.

    >>> print(user_browser.getLink("CVE report").url)
    http://bugs.launchpad.test/debian/+cve


Distribution Series
-------------------

    >>> path = "debian/woody"

If the user is not logged-in general stats are shown. There is also a
link to review nominations.

    >>> print_bugfilters_portlet_unfilled(anon_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs - CVE reports

    >>> print_bugfilters_portlet_filled(anon_browser, path)
    2 New bugs
    2 Open bugs
    0 In-progress bugs
    0 Critical bugs
    0 High importance bugs
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    1 Open CVE bug - CVE report

Once the user has identified themselves, show information on assigned and
reported bugs.

    >>> print_bugfilters_portlet_unfilled(user_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs assigned to me
    Bugs reported by me
    Bugs affecting me
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs - CVE reports

    >>> print_bugfilters_portlet_filled(user_browser, path)
    2 New bugs
    2 Open bugs
    0 In-progress bugs
    0 Critical bugs
    0 High importance bugs
    <BLANKLINE>
    0 Bugs assigned to me
    0 Bugs reported by me
      Bugs affecting me
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    1 Open CVE bug - CVE report

The content includes a link to the distribution CVE report.

    >>> print(user_browser.getLink("CVE report").url)
    http://bugs.launchpad.test/debian/woody/+cve


Distribution Source Package
---------------------------

    >>> path = "debian/+source/mozilla-firefox"

If the user is not logged-in general stats are shown.

    >>> print_bugfilters_portlet_unfilled(anon_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs

    >>> print_bugfilters_portlet_filled(anon_browser, path)
    1 New bug
    3 Open bugs
    0 In-progress bugs
    0 Critical bugs
    0 High importance bugs
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    2 Open CVE bugs

Once the user has identified themselves, show information on assigned and
reported bugs.

    >>> print_bugfilters_portlet_unfilled(user_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs assigned to me
    Bugs reported by me
    Bugs affecting me
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs

    >>> print_bugfilters_portlet_filled(user_browser, path)
    1 New bug
    3 Open bugs
    0 In-progress bugs
    0 Critical bugs
    0 High importance bugs
    <BLANKLINE>
    0 Bugs assigned to me
    0 Bugs reported by me
      Bugs affecting me
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    2 Open CVE bugs

Note that the "CVE reports" link is not shown above; distribution
source packages do not have a CVE reports page.

    >>> print(user_browser.getLink("CVE report").url)
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError


Source Package in Distribution Series
-------------------------------------

    >>> path = "debian/woody/+source/mozilla-firefox"

If the user is not logged-in general stats are shown. There is no
option to subscribe to bug mail.

    >>> print_bugfilters_portlet_unfilled(anon_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs

    >>> print_bugfilters_portlet_filled(anon_browser, path)
    2 New bugs
    2 Open bugs
    0 In-progress bugs
    0 Critical bugs
    0 High importance bugs
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    1 Open CVE bug

Once the user has identified themselves, show information on assigned and
reported bugs.

    >>> print_bugfilters_portlet_unfilled(user_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs assigned to me
    Bugs reported by me
    Bugs affecting me
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs

    >>> print_bugfilters_portlet_filled(user_browser, path)
    2 New bugs
    2 Open bugs
    0 In-progress bugs
    0 Critical bugs
    0 High importance bugs
    <BLANKLINE>
    0 Bugs assigned to me
    0 Bugs reported by me
      Bugs affecting me
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    1 Open CVE bug

Note that the "CVE reports" link is not shown above; source packages
do not have a CVE reports page.

    >>> print(user_browser.getLink("CVE report").url)
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError


Project group
-------------

    >>> path = "mozilla"

If the user is not logged-in general stats are shown.

    >>> print_bugfilters_portlet_unfilled(anon_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs

    >>> print_bugfilters_portlet_filled(anon_browser, path)
    4 New bugs
    4 Open bugs
    0 In-progress bugs
    1 Critical bug
    0 High importance bugs
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    1 Open CVE bug

Once the user has identified themselves, show information on assigned
and reported bugs.

    >>> print_bugfilters_portlet_unfilled(user_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs assigned to me
    Bugs reported by me
    Bugs affecting me
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs


    >>> print_bugfilters_portlet_filled(user_browser, path)
    4 New bugs
    4 Open bugs
    0 In-progress bugs
    1 Critical bug
    0 High importance bugs
    <BLANKLINE>
    0 Bugs assigned to me
    0 Bugs reported by me
      Bugs affecting me
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    1 Open CVE bug

Note that the "CVE reports" link is not shown above; project groups do
not have a CVE reports page.

    >>> print(user_browser.getLink("CVE report").url)
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError


Project
-------

    >>> path = "firefox"

If the user is not logged-in general stats are shown.

    >>> print_bugfilters_portlet_unfilled(anon_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs - CVE reports

    >>> print_bugfilters_portlet_filled(anon_browser, path)
    3 New bugs
    3 Open bugs
    0 In-progress bugs
    1 Critical bug
    0 High importance bugs
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    1 Open CVE bug - CVE report

Once the user has identified themselves, information on assigned
bugs is also shown.

    >>> print_bugfilters_portlet_unfilled(user_browser, path)
    New bugs
    Open bugs
    In-progress bugs
    Critical bugs
    High importance bugs
    <BLANKLINE>
    Bugs assigned to me
    Bugs reported by me
    Bugs affecting me
    <BLANKLINE>
    Bugs fixed elsewhere
    Bugs with patches
    Open CVE bugs - CVE reports


    >>> print_bugfilters_portlet_filled(user_browser, path)
    3 New bugs
    3 Open bugs
    0 In-progress bugs
    1 Critical bug
    0 High importance bugs
    <BLANKLINE>
    0 Bugs assigned to me
    0 Bugs reported by me
      Bugs affecting me
    <BLANKLINE>
      Bugs fixed elsewhere
    0 Bugs with patches
    1 Open CVE bug - CVE report


The content includes a link to the distribution CVE report.

    >>> print(user_browser.getLink("CVE report").url)
    http://bugs.launchpad.test/firefox/+cve
