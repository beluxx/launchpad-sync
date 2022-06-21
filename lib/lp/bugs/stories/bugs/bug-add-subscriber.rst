Non-Personal Subscriptions
==========================

In addition to subscribing / unsubscribing yourself, it is possible to add a
person as a subscriber to the bug. You would use this feature to subscribe
someone else to the bug.

Anonymous users should not be able to subscribe someone else to a bug.

    >>> anon_browser.open('http://bugs.launchpad.test/firefox/+bug/1')
    >>> anon_browser.getLink('Subscribe someone else').click()
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

No Privileges wants to subscribe David Allouche to the bug because they know
that he's interested in that feature.

    >>> user_browser.open('http://bugs.launchpad.test/firefox/+bug/1')
    >>> user_browser.getLink('Subscribe someone else').click()
    >>> user_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1/+addsubscriber'

If No Privileges has a sudden change of heart, there's a cancel link
that will return the browser to the bug page.

    >>> cancel_link = user_browser.getLink('Cancel')
    >>> cancel_link.url
    'http://bugs.launchpad.test/firefox/+bug/1'

By looking at the 'Subscribers' portlet, they see that David Allouche is not
currently subscribed to the bug:

    >>> from lp.bugs.tests.bug import (
    ...     print_also_notified, print_direct_subscribers)

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/bugs/1/'
    ...     '+bug-portlet-subscribers-details')
    >>> print_direct_subscribers(user_browser.contents)
    Sample Person
    Steve Alexander
    >>> print_also_notified(user_browser.contents)
    Also notified:
    Foo Bar
    Mark Shuttleworth

They subscribe David Allouche to the bug using his Launchpad username.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/firefox/+bug/1/+addsubscriber')
    >>> user_browser.getControl("Person").value = 'ddaa'
    >>> user_browser.getControl("Subscribe user").click()
    >>> user_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'

They are notified that David Allouche has been subscribed.

    >>> for tag in find_tags_by_class(user_browser.contents,
    ...     'informational message'):
    ...     print(extract_text(tag))
    David Allouche has been subscribed to this bug.

The subscribers portlet now contains the new subscriber's name.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/bugs/1/'
    ...     '+bug-portlet-subscribers-details')
    >>> print_direct_subscribers(user_browser.contents)
    David Allouche (Unsubscribe)
    Sample Person
    Steve Alexander

David got a notification, saying that he was subscribed to the bug.

    >>> from lp.services.mail import stub
    >>> len(stub.test_emails)
    1
    >>> print(six.ensure_text(stub.test_emails[0][2]))
    MIME-Version: 1.0
    ...
    To: david.allouche@canonical.com
    Reply-To: Bug ... <...@bugs.launchpad.net>
    ...
    X-Launchpad-Message-Rationale: Subscriber
    X-Launchpad-Message-For: ddaa
    ...
    You have been subscribed to a public bug by No Privileges Person
    (no-priv):
    ...
    http://bugs.launchpad.test/bugs/...

He subscribes the Landscape developers team.

    >>> user_browser.open('http://bugs.launchpad.test/firefox/+bug/1')
    >>> user_browser.getLink('Subscribe someone else').click()
    >>> user_browser.getControl("Person").value = 'landscape-developers'
    >>> user_browser.getControl("Subscribe user").click()
    >>> user_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'

He is notified that Landscape developers team has been subscribed.

    >>> for tag in find_tags_by_class(user_browser.contents,
    ...     'informational message'):
    ...     print(extract_text(tag))
    Landscape Developers team has been subscribed to this bug.

The subscribers portlet displays the new subscribed team.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/bugs/1/'
    ...     '+bug-portlet-subscribers-details')
    >>> print_direct_subscribers(user_browser.contents)
    David Allouche (Unsubscribe)
    Landscape Developers (Unsubscribe)
    Sample Person
    Steve Alexander


Subscription of private teams
-----------------------------

Private teams can be subscribed to bugs. Any logged in user can see
the private team in the subscribers list. Additionally if they are a member
of the private team they can unsubscribe the team.

Create a private team with Foo Bar as the owner.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet, PersonVisibility
    >>> login('foo.bar@canonical.com')
    >>> foobar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
    >>> priv_team = factory.makeTeam(name='private-team',
    ...     displayname='Private Team',
    ...     owner=foobar,
    ...     visibility=PersonVisibility.PRIVATE)
    >>> logout()
    >>> foobar_browser = setupBrowser(auth='Basic foo.bar@canonical.com:test')
    >>> foobar_browser.open('http://bugs.launchpad.test/firefox/+bug/1')
    >>> foobar_browser.getLink('Subscribe someone else').click()
    >>> foobar_browser.getControl("Person").value = 'private-team'
    >>> foobar_browser.getControl("Subscribe user").click()
    >>> foobar_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'
    >>> foobar_browser.open(
    ...     'http://bugs.launchpad.test/bugs/1/'
    ...     '+bug-portlet-subscribers-details')
    >>> print_direct_subscribers(foobar_browser.contents)
    David Allouche (Unsubscribe)
    Landscape Developers (Unsubscribe)
    Private Team (Unsubscribe)
    Sample Person (Unsubscribe)
    Steve Alexander (Unsubscribe)

Someone not in the team will see the private team in the subscribers list but
cannot unsubscribe them.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/bugs/1/'
    ...     '+bug-portlet-subscribers-details')
    >>> print_direct_subscribers(user_browser.contents)
    David Allouche (Unsubscribe)
    Landscape Developers (Unsubscribe)
    Private Team
    Sample Person
    Steve Alexander

An anonymous user will not be shown the private team in the subscribers
list.

    >>> anon_browser.open(
    ...     'http://bugs.launchpad.test/bugs/1/'
    ...     '+bug-portlet-subscribers-details')
    >>> print_direct_subscribers(anon_browser.contents)
    David Allouche
    Landscape Developers
    Sample Person
    Steve Alexander

The activity log also does not show subscribed private teams.  If we
look at the activity log for the bug used above, we'll see that David Allouche
and Landscape Developers have been subscribed, but we will not see an
entry in the activity log for Private Team.

    >>> def print_row(row):
    ...     print(' | '.join(
    ...         extract_text(cell) for cell in row(('th', 'td'))))
    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/firefox/+bug/1/+activity')
    >>> main_content = find_main_content(user_browser.contents)
    >>> for row in main_content.table('tr'):
    ...     print_row(row)
    Date | Who | What changed | Old value | New value | Message
    ...
    ... | ... | ... |  |  | added subscriber David Allouche
    ... | ... | ... |  |  | added subscriber Landscape Developers
