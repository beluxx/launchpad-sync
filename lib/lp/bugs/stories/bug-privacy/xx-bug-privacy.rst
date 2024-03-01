Foo Bar, an LP admin, is about to make bug #2 private.

    >>> browser = setupBrowser(auth="Basic foo.bar@canonical.com:test")
    >>> browser.open(
    ...     "http://bugs.launchpad.test/debian/+source/mozilla-firefox/"
    ...     "+bug/2/+secrecy"
    ... )

Foo Bar is not Cc'd on this bug, but is able to set the bug private
anyway, because they are an admin.

    >>> browser.getControl("Private", index=1).selected = True
    >>> browser.getControl("Change").click()
    >>> print(browser.url)
    http://bugs.launchpad.test/debian/+source/mozilla-firefox/+bug/2

When we go back to the secrecy form, the previously set value is pre-selected.

    >>> browser.open(
    ...     "http://bugs.launchpad.test/debian/+source/mozilla-firefox/"
    ...     "+bug/2/+secrecy"
    ... )
    >>> browser.getControl("Private", index=1).selected
    True

Foo Bar files a security (private) bug on Ubuntu. They get redirected to the
bug page.

    >>> browser = setupBrowser("Basic foo.bar@canonical.com:test")
    >>> browser.open("http://launchpad.test/ubuntu/+filebug")

The Ubuntu maintainer, Ubuntu Team, will be subscribed.

    >>> browser.getControl(name="field.title", index=0).value = (
    ...     "a private bug"
    ... )
    >>> browser.getControl("Continue").click()

    >>> browser.getControl(name="packagename_option").value = ["choose"]
    >>> browser.getControl(name="field.packagename").value = "evolution"
    >>> browser.getControl(name="field.comment").value = "secret info"
    >>> browser.getControl("Private Security").selected = True
    >>> browser.getControl("Submit Bug Report").click()

    >>> bug_id = browser.url.split("/")[-1]
    >>> print(browser.url.replace(bug_id, "BUG-ID"))
    http://bugs.launchpad.test/ubuntu/+source/evolution/+bug/BUG-ID

    >>> print(browser.contents)
    <!DOCTYPE...
    ...Security-related bugs are by default private...

Foo Bar sees the private bug they filed.

    >>> browser.open("http://launchpad.test/ubuntu/+bugs")
    >>> print(browser.contents.replace(bug_id, "BUG-ID"))
    <!DOCTYPE...
    ...
    ...Ubuntu...
    ...<a...>...BUG-ID...</a>...

Foo Bar is subscribed to the bug.

    >>> from operator import attrgetter
    >>> from zope.component import getUtility
    >>> from lp.testing import login, logout
    >>> from lp.bugs.interfaces.bug import IBugSet

    >>> login("foo.bar@canonical.com")

    >>> bug = getUtility(IBugSet).get(bug_id)

    >>> for subscriber in sorted(
    ...     bug.getDirectSubscribers(), key=attrgetter("name")
    ... ):
    ...     print(subscriber.name)
    name16

    >>> logout()


Anonymous users cannot see private bugs filed on distros, of course!

Not directly.

    >>> anon_browser.open("http://launchpad.test/bugs/14")
    Traceback (most recent call last):
      ...
    zope.publisher.interfaces.NotFound: ...

And not in bug listings.

    >>> anon_browser.open("http://launchpad.test/ubuntu/+bugs")
    >>> "a private bug" not in anon_browser.contents
    True

A user not subscribed to a private bug will not be able to see the bug.

Neither directly.

    >>> browser = setupBrowser("Basic no-privs@canonical.com:test")
    >>> browser.open("http://launchpad.test/bugs/14")
    Traceback (most recent call last):
      ...
    zope.publisher.interfaces.NotFound: ...

Nor in a search listing.

    >>> browser.open("http://launchpad.test/ubuntu/+bugs")
    >>> "a private bug" not in browser.contents
    True

First, some setup. Find out what the latest [private] bug reported on
Ubuntu evolution is, so we can avoid hardcoding its ID here:

    >>> from zope.component import getUtility
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.bugs.interfaces.bugtasksearch import BugTaskSearchParams
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet,
    ... )
    >>> from lp.testing import login, logout

    >>> login("foo.bar@canonical.com")
    >>> launchbag = getUtility(ILaunchBag)
    >>> evo = getUtility(ISourcePackageNameSet).queryByName("evolution")
    >>> params = BugTaskSearchParams(
    ...     user=launchbag.user, sourcepackagename=evo, orderby="-id"
    ... )

    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> latest_evo_task = ubuntu.searchTasks(params)[0]
    >>> latest_evo_bug = latest_evo_task.bug.id
    >>> logout()

Unsubscribing from a private bug redirects you to the bug listing (see
further down for an exception to this rule.) Let's demonstrate by having
Foo Bar, an admin, subscribe Sample Person to a private bug.

    >>> browser = setupBrowser(auth="Basic foo.bar@canonical.com:test")
    >>> add_subscriber_url = (
    ...     "http://launchpad.test/ubuntu/+source/evolution/+bug/%s"
    ...     "/+addsubscriber" % latest_evo_bug
    ... )
    >>> browser.open(add_subscriber_url)
    >>> browser.getControl("Person").value = "name12"
    >>> browser.getControl("Subscribe user").click()
    >>> browser.url
    'http://bugs.launchpad.test/ubuntu/+source/evolution/+bug/...'
