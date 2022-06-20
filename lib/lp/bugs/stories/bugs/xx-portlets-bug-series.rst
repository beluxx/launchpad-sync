The series-targeted portlet displays the number of open bugs that have
been accepted as targeting a specific series of a distribution:

This portlet is not available from a distribution's bug page if it
does not use Launchpad for tracking bugs.

    >>> anon_browser.open("http://bugs.launchpad.test/debian/+bugs")
    >>> portlet = find_portlet(anon_browser.contents, "Series-targeted bugs")
    >>> print(portlet)
    None

Change debian to track bugs in Launchpad and the portlet becomes visible.

    >>> from lp.testing.service_usage_helpers import set_service_usage
    >>> set_service_usage('debian', bug_tracking_usage='LAUNCHPAD')

    >>> anon_browser.open("http://bugs.launchpad.test/debian/+bugs")
    >>> portlet = find_portlet(anon_browser.contents, "Series-targeted bugs")
    >>> print(extract_text(portlet))
    Series-targeted bugs
    1
    sarge
    2
    woody

    >>> anon_browser.open("http://bugs.launchpad.test/debian/sarge/+bugs")
    >>> portlet = find_portlet(anon_browser.contents, "Series-targeted bugs")
    >>> print(extract_text(portlet))
    Series-targeted bugs
    1
    sarge
    2
    woody

    >>> anon_browser.open("http://bugs.launchpad.test/ubuntu/+bugs")
    >>> portlet = find_portlet(anon_browser.contents, "Series-targeted bugs")
    >>> print(extract_text(portlet))
    Series-targeted bugs
    1
    hoary
    1
    warty

    >>> print(anon_browser.getLink("hoary").url)
    http://bugs.launchpad.test/ubuntu/hoary/+bugs

The same portlet is also available for project and project series
listings and homepages:

    >>> anon_browser.open("http://bugs.launchpad.test/firefox/+bugs")
    >>> portlet = find_portlet(anon_browser.contents, "Series-targeted bugs")
    >>> print(extract_text(portlet))
    Series-targeted bugs
    1
    1.0

    >>> anon_browser.open("http://bugs.launchpad.test/firefox/1.0/+bugs")
    >>> portlet = find_portlet(anon_browser.contents, "Series-targeted bugs")
    >>> print(extract_text(portlet))
    Series-targeted bugs
    1
    1.0
