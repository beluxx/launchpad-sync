This page checks that we can see a list of bugs on the distroseries,
specifically Hoary.

    >>> browser.open("http://localhost/ubuntu/hoary/+bugs")
    >>> print(browser.title)
    Hoary (5.04) : Bugs : Ubuntu

This page checks that we can see a list of bugs on the distributions, in
this case Ubuntu.

    >>> browser.open("http://localhost/ubuntu/+bugs")
    >>> print(browser.title)
    Bugs : Ubuntu...

Comments are intended to be contributions to a bug report that further
the goal of solving the problem at hand. Any logged in user can add a
comment to a bug.

In this case, let's add a simple comment to bug #2 as user Foo
Bar. First, let's clear out the notification table:

    >>> from lp.bugs.model.bugnotification import BugNotification
    >>> from lp.services.database.interfaces import IStore
    >>> store = IStore(BugNotification)
    >>> store.execute("DELETE FROM BugNotification", noresult=True)

    >>> user_browser.open(
    ...     "http://localhost/debian/+source/mozilla-firefox/+bug/2"
    ... )
    >>> user_browser.getControl(
    ...     name="field.comment"
    ... ).value = "This is a test comment."
    >>> user_browser.getControl("Post Comment", index=-1).click()

    >>> user_browser.url
    'http://bugs.launchpad.test/debian/+source/mozilla-firefox/+bug/2'

    >>> print(user_browser.contents)
    <...
    ...This is a test comment...


After the comment has been submitted, a notification is added:

    >>> IStore(BugNotification).find(BugNotification).count()
    1
