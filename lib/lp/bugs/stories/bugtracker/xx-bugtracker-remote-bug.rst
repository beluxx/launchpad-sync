Remote Bug Information Pages
============================

Launchpad provides the ability for bugs to "watch" remote bugs.  You
can easily see which remote bugs a Launchpad bug watches by looking at
the "Remote Bug Watches" portlet on the bug's page.

To see what Launchpad bugs are watching a particular remote bug, we
use a URL of the form /bugs/bugtrackers/$bugtrackername/$remotebug.

If there are multiple Launchpad bugs watching a particular remote bug,
then a list of the relevant Launchpad bugs:

    >>> browser.open("http://launchpad.test/bugs/bugtrackers/mozilla.org/42")

    >>> print_location(browser.contents)
    Hierarchy: Bug trackers > The Mozilla.org Bug Tracker
    Tabs:
    * Launchpad Home - http://launchpad.test/
    * Code - http://code.launchpad.test/
    * Bugs (selected) - http://bugs.launchpad.test/
    * Blueprints - http://blueprints.launchpad.test/
    * Translations - http://translations.launchpad.test/
    * Answers - http://answers.launchpad.test/
    Main heading: Remote Bug #42 in The Mozilla.org Bug Tracker

    >>> print(extract_text(find_tag_by_id(browser.contents, "watchedbugs")))
    Bug #1: Firefox does not support SVG
    Bug #2: Blackhole Trash folder

If there is only a single bug watching the remote bug, then we skip
the list page and redirect the user directly to that bug's page:

    >>> browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/mozilla.org/2000"
    ... )
    >>> print(browser.url)
    http://bugs.launchpad.test/firefox/+bug/1

If there are no bug watches for a particular remote bug, then a Not
Found page is generated:

    >>> browser.handleErrors = True
    >>> browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/mozilla.org/99999"
    ... )
    Traceback (most recent call last):
    ...
    urllib.error.HTTPError: HTTP Error 404: Not Found
    >>> browser.handleErrors = False


Private Bugs
------------

If a bug is marked private, and multiple Launchpad bugs are watching a
particular remote bug, we do not expose the title of the remote bug.

Mark bug 1 as private:

    >>> browser.addHeader("Authorization", "Basic test@canonical.com:test")
    >>> browser.open("http://bugs.launchpad.test/firefox/+bug/1/+secrecy")
    >>> browser.getControl("Private", index=1).selected = True
    >>> browser.getControl("Change").click()
    >>> browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'

List Launchpad bugs watching Mozilla bug 42:

    >>> anon_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/mozilla.org/42"
    ... )

    >>> print_location(anon_browser.contents)
    Hierarchy: Bug trackers > The Mozilla.org Bug Tracker
    Tabs:
    * Launchpad Home - http://launchpad.test/
    * Code - http://code.launchpad.test/
    * Bugs (selected) - http://bugs.launchpad.test/
    * Blueprints - http://blueprints.launchpad.test/
    * Translations - http://translations.launchpad.test/
    * Answers - http://answers.launchpad.test/
    Main heading: Remote Bug #42 in The Mozilla.org Bug Tracker

    >>> print(
    ...     extract_text(find_tag_by_id(anon_browser.contents, "watchedbugs"))
    ... )
    Bug #1: (Private)
    Bug #2: Blackhole Trash folder

The bug title is still provided if the user can view the private bug:

    >>> browser.open("http://launchpad.test/bugs/bugtrackers/mozilla.org/42")
    >>> print(extract_text(find_tag_by_id(browser.contents, "watchedbugs")))
    Bug #1: Firefox does not support SVG
    Bug #2: Blackhole Trash folder

For the case where the private bug is the only one watching the given
remote bug, we don't perform the redirect ahead of time (i.e. before the
user logs in):

    >>> anon_browser.open(
    ...     "http://bugs.launchpad.test/bugs/bugtrackers/mozilla.org/2000"
    ... )
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...

Set the bug back to public:

    >>> browser.open("http://bugs.launchpad.test/firefox/+bug/1/+secrecy")
    >>> browser.getControl("Public", index=1).selected = True
    >>> browser.getControl("Change").click()
    >>> browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'
