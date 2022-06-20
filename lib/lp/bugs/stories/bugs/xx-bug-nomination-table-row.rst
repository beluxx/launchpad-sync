Bug nominations
===============

Bug nominations are displayed in the table at the top of the bug page,
using the +bugtasks-and-nominations-table-row view. This view allows
privileged users, i.e., users that have launchpad.Driver permission on
the distroseries or productseries, to approve or decline the
nomination.

no-priv cannot approve or decline their nomination, because they do not
have the launchpad.Driver permission.

    >>> from zope.component import getUtility

    >>> from lp.testing import login, logout
    >>> from lp.services.webapp.authorization import check_permission
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.registry.interfaces.distribution import IDistributionSet

    >>> login("no-priv@canonical.com")

    >>> bug_one = getUtility(IBugSet).get(1)
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> ubuntu_hoary = ubuntu.getSeries("hoary")
    >>> ubuntu_hoary_nomination = bug_one.getNominationFor(ubuntu_hoary)

    >>> check_permission("launchpad.Driver", ubuntu_hoary_nomination.target)
    False

    >>> logout()

    >>> user_browser.open(
    ...     "http://launchpad.test/distros/ubuntu/+source/mozilla-firefox/"
    ...     "+bug/1/nominations/2/+bugtasks-and-nominations-table-row")

no-priv will, of course, see their nomination.

    >>> user_browser.contents
    '...Nominated...for...Hoary...by...No Privileges Person...'

But not the Approve or Decline buttons.

    >>> user_browser.getControl("Approve")
    Traceback (most recent call last):
      ...
    LookupError: ...

    >>> user_browser.getControl("Decline")
    Traceback (most recent call last):
      ...
    LookupError: ...

no-priv can't access the +edit-form (the view that renders the submit
buttons) directly either.

    >>> user_browser.open(
    ...     "http://launchpad.test/distros/ubuntu/+source/mozilla-firefox/"
    ...     "+bug/1/nominations/2/+edit-form")
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

But if we log in as a user that does have launchpad.Driver permission,
we will see the approve/decline links.

First, when the task is in Proposed state, the (privileged) user sees
Approve and Decline buttons.

    >>> login("foo.bar@canonical.com")
    >>> check_permission("launchpad.Driver", ubuntu_hoary_nomination.target)
    True
    >>> ubuntu_hoary_nomination.isProposed()
    True
    >>> logout()

    >>> browser = setupBrowser("Basic foo.bar@canonical.com:test")
    >>> browser.open(
    ...     "http://launchpad.test/distros/ubuntu/+source/mozilla-firefox/"
    ...     "+bug/1/nominations/2/+bugtasks-and-nominations-table-row")

    >>> approve_button = browser.getControl("Approve")
    >>> decline_button = browser.getControl("Decline")

Clicking "Decline" declines the nomination.

    >>> decline_button.click()

    >>> login("foo.bar@canonical.com")
    >>> ubuntu_hoary_nomination = bug_one.getNominationFor(ubuntu_hoary)
    >>> ubuntu_hoary_nomination.isDeclined()
    True
    >>> logout()

Now only the "Approve" button shows.

    >>> browser = setupBrowser("Basic foo.bar@canonical.com:test")
    >>> browser.open(
    ...     "http://launchpad.test/distros/ubuntu/+source/mozilla-firefox/"
    ...     "+bug/1/nominations/2/+bugtasks-and-nominations-table-row")

    >>> browser.contents
    '...Declined...for...Hoary...by...Foo Bar...'

    >>> approve_button = browser.getControl("Approve")
    >>> browser.getControl("Decline")
    Traceback (most recent call last):
      ...
    LookupError: ...

Clicking "Approve" approves the nomination.

    >>> approve_button.click()

    >>> login("foo.bar@canonical.com")
    >>> ubuntu_hoary_nomination = bug_one.getNominationFor(ubuntu_hoary)
    >>> ubuntu_hoary_nomination.isApproved()
    True
    >>> logout()

