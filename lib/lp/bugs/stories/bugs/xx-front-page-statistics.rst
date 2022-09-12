Launchpad Bug Statistics
========================

The Bugs front page shows some statistics:

* number of bugs that are filed in Launchpad
* number of links to external bugs
* number of external bug trackers registered
* number of CVE bug links

    >>> anon_browser.open("http://bugs.launchpad.test/")
    >>> statistics = find_portlet(anon_browser.contents, "Statistics")
    >>> print(extract_text(statistics))
    Statistics
    15 bugs reported across 7 projects
    including 12 links to 8 bug trackers
    4 bugs are shared across multiple projects
    and 2 bugs are related to CVE entries

And offers handy links to a listing of all upstream bug trackers
registered in Launchpad...

    >>> anon_browser.getLink("bug trackers").click()
    >>> anon_browser.title
    'Bug trackers registered in Launchpad'

...and to Launchpad's CVE tracker.

    >>> anon_browser.goBack(1)
    >>> anon_browser.getLink("CVE entries").click()
    >>> anon_browser.title
    'Launchpad CVE tracker'
