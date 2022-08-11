Subscriptions to bug notifications
----------------------------------

Any logged in user can subscribe themselves to bug notifications for any
Launchpad structure, as well as subscribe any of the teams to which
they belong.

    >>> browser.addHeader('Authorization', 'Basic test@canonical.com:test')

We subscribe the Landscape team to Ubuntu.

    >>> browser.open(
    ... 'http://bugs.launchpad.test/ubuntu/+subscribe')
    >>> subscribe_team = browser.getControl('Landscape')
    >>> subscribe_team.selected = True
    >>> browser.getControl('Save these changes').click()

    >>> browser.open(
    ... 'http://bugs.launchpad.test/ubuntu/+subscribe')
    >>> print(extract_text(find_portlet(browser.contents, 'Subscribers')))
    Subscribers
      To all Ubuntu bugs:
        Landscape Developers

And subscribe some people to the Firefox source package in ubuntu.

    >>> browser.open(
    ... 'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox')
    >>> browser.getLink('Subscribe to bug mail').click()
    >>> subscribe_myself = browser.getControl(
    ...    'I want to receive these notifications by email')
    >>> subscribe_myself.selected
    False
    >>> subscribe_myself.selected = True
    >>> subscribe_team = browser.getControl('Landscape')
    >>> subscribe_team.selected
    False
    >>> subscribe_team.selected = True
    >>> browser.getControl('Save these changes').click()

Sample Person and the Landscape team are now subscribed.

    >>> browser.open(
    ...     'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/'
    ...     '+subscribe')
    >>> print(backslashreplace(extract_text(find_portlet(
    ...     browser.contents, 'Subscribers'))))
    Subscribers
      To all bugs in mozilla-firefox in Ubuntu:
        Foo Bar
        Landscape Developers
        Sample Person
      To all Ubuntu bugs:
        Landscape Developers

Sample Person can also unsubscribe themselves and the Landscape team.

    >>> subscribe_myself = browser.getControl(
    ...    'I want to receive these notifications by email')
    >>> subscribe_myself.selected = False
    >>> subscribe_team = browser.getControl('Landscape')
    >>> subscribe_team.selected = False
    >>> browser.getControl('Save these changes').click()
    >>> browser.open(
    ...     'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/'
    ...     '+subscribe')
    >>> print(extract_text(find_portlet(browser.contents, 'Subscribers')))
    Subscribers
      To all bugs in mozilla-firefox in Ubuntu:
        Foo Bar
      To all Ubuntu bugs:
        Landscape Developers


Additional options for distribution drivers
===========================================

When editing the subscriptions for a package, a distribution driver
can subscribe any Launchpad user.

Firstly, we appoint Sample Person as the driver for the distribution.

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.testing import login, logout
    >>> from zope.component import getUtility
    >>> login('foo.bar@canonical.com')
    >>> driver = getUtility(IPersonSet).getByEmail('test@canonical.com')
    >>> from zope.component import getUtility
    >>> ubuntu = getUtility(IDistributionSet).get(1)
    >>> ubuntu.driver = driver
    >>> flush_database_updates()
    >>> logout()

The driver sees an extended form in the +subscribe view, which allows them
to subscribe other people.

    >>> browser.open(
    ...     'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/'
    ...     '+subscribe')
    >>> subscribe_other = browser.getControl('Subscribe someone else:')
    >>> subscribe_other.value = 'no-priv'
    >>> browser.getControl('Save these changes').click()

No Privileges Person is now subscribed...

    >>> for message in find_tags_by_class(browser.contents, 'message'):
    ...     print(message.decode_contents())
    No Privileges Person will now receive an email each time someone reports
    or changes a public bug in "mozilla-firefox in Ubuntu".

    >>> browser.open(
    ...     'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/'
    ...     '+subscribe')
    >>> print(extract_text(find_portlet(browser.contents, 'Subscribers')))
    Subscribers
      To all bugs in mozilla-firefox in Ubuntu:
        Foo Bar
        No Privileges Person
      To all Ubuntu bugs:
        Landscape Developers

...has an entry in the "Remove subscriptions" list...

    >>> remove_other = browser.getControl('\xa0No Privileges Person')

...and can be unsubscribed again.

    >>> remove_other.selected = True
    >>> browser.getControl('Save these changes').click()
    >>> print(find_tags_by_class(
    ...    browser.contents, 'informational message')[0].contents[0])
    No Privileges Person will no longer automatically receive email about
    public bugs in "mozilla-firefox in Ubuntu".
    >>> browser.open(
    ...     'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/'
    ...     '+subscribe')
    >>> print(extract_text(find_portlet(browser.contents, 'Subscribers')))
    Subscribers
      To all bugs in mozilla-firefox in Ubuntu:
        Foo Bar
      To all Ubuntu bugs:
        Landscape Developers

The checkbox to unsubscribe No Privileges Person is no longer present on
the page.

    >>> remove_other = browser.getControl('\xa0No Privileges Person')
    Traceback (most recent call last):
    ...
    LookupError: label ...'\xa0No Privileges Person'
    ...

We clean up by removing Sample Person as the distribution driver.

    >>> login('foo.bar@canonical.com')
    >>> ubuntu.driver = None
    >>> flush_database_updates()
    >>> logout()

An attempt by Sample Person to remove Foo Bar from the subscription list
and to add Sample Person is now silently ignored, because LaunchpadFormView
purges the submitted form data from now unexpected values.

    >>> print(extract_text(find_portlet(browser.contents, 'Subscribers')))
    Subscribers
      To all bugs in mozilla-firefox in Ubuntu:
        Foo Bar
      To all Ubuntu bugs:
        Landscape Developers

    >>> remove_other = browser.getControl('\xa0Foo Bar')
    >>> remove_other.selected = True
    >>> subscribe_other = browser.getControl('Subscribe someone else:')
    >>> subscribe_other.value = 'nopriv'
    >>> browser.getControl('Save these changes').click()
    >>> browser.open(
    ...     'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/'
    ...     '+subscribe')
    >>> print(extract_text(find_portlet(browser.contents, 'Subscribers')))
    Subscribers
      To all bugs in mozilla-firefox in Ubuntu:
        Foo Bar
      To all Ubuntu bugs:
        Landscape Developers

When Sample Person now visits the bug subscription page, they no longer see
the UI elements for the subscription/unsubscription of arbitrary persons.

    >>> browser.open(
    ...     'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/'
    ...     '+subscribe')
    >>> browser.getControl('Subscribe someone else:')
    Traceback (most recent call last):
    ...
    LookupError: label ...'Subscribe someone else:'
    ...

    >>> print(browser.getControl('\xa0Foo Bar'))
    Traceback (most recent call last):
    ...
    LookupError: label ...'\xa0Foo Bar'
    ...


Distribution with a bug supervisor
==================================

If a distribution has a bug supervisor only that team or members of it can
subscribe to all of the distribution's bugs.

First, check the page content for a distribution without a bug supervisor.

    >>> browser.open('http://bugs.launchpad.test/ubuntu/+subscribe')
    >>> text_contents = extract_text(find_main_content(browser.contents))
    >>> "You can choose to receive an email every time" in text_contents
    True

Set a bug supervisor for Ubuntu.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> login('foo.bar@canonical.com')
    >>> ubuntu = removeSecurityProxy(getUtility(IDistributionSet).get(1))
    >>> guadamen = getUtility(IPersonSet).getByName('guadamen')
    >>> ubuntu.bug_supervisor = guadamen
    >>> flush_database_updates()
    >>> logout()

Second, check that the page content for a distribution with a bug supervisor
contains a message about not being able to subscribe.

    >>> browser.open('http://bugs.launchpad.test/ubuntu/+subscribe')
    >>> text_contents = extract_text(find_main_content(browser.contents))
    >>> "You are unable to subscribe to bug reports about" in text_contents
    True
