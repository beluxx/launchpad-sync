Bugtask importance
==================

It is possible to set the bug importance using the bugtask edit form.

    >>> admin_browser.open('http://bugs.launchpad.test/bugs/10')
    >>> importance_control = admin_browser.getControl('Importance')
    >>> print('\n'.join(importance_control.displayOptions))
    Undecided
    Critical
    High
    Medium
    Low
    Wishlist

Note that the `UNKNOWN` option, which is a valid value for
`BugTask.importance` isn't showing here. This value can't be set by
users - only bug watches use it.

Only the bug supervisor, or a user with launchpd.Edit on the respective
product or distro, can edit Importance.

    >>> import transaction
    >>> from zope.component import getUtility

    >>> from lp.testing import ANONYMOUS, login, logout
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet

    >>> login("foo.bar@canonical.com")

    >>> personset = getUtility(IPersonSet)
    >>> no_priv = personset.getByName("no-priv")
    >>> mark = personset.getByName("mark")
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")

    >>> from zope.security.proxy import removeSecurityProxy
    >>> def user_sees_importance_widget(user, url):
    ...     naked_email = removeSecurityProxy(user.preferredemail)
    ...     transaction.commit()
    ...     logout()
    ...     browser = setupBrowser(
    ...         "Basic %s:test" % naked_email.email)
    ...     browser.open(url)
    ...     try:
    ...         browser.getControl("Importance")
    ...     except LookupError:
    ...         return False
    ...     else:
    ...         return True

For a product bug supervisor.

    >>> login("foo.bar@canonical.com")
    >>> firefox.bug_supervisor = no_priv
    >>> user_sees_importance_widget(
    ...     user=no_priv,
    ...     url="http://bugs.launchpad.test/firefox/+bug/1/+editstatus")
    True

For a product owner.

    >>> login(ANONYMOUS)
    >>> print(firefox.owner.name)
    name12

    >>> login("foo.bar@canonical.com")
    >>> sample_person = personset.getByName("name12")
    >>> user_sees_importance_widget(
    ...     user=sample_person,
    ...     url="http://bugs.launchpad.test/firefox/+bug/1/+editstatus")
    True

For someone else. We'll unset no_priv as the bug supervisor, and note that
they can no longer see the widget.

    >>> login("foo.bar@canonical.com")
    >>> firefox.bug_supervisor = None
    >>> user_sees_importance_widget(
    ...     user=no_priv,
    ...     url="http://bugs.launchpad.test/firefox/+bug/1/+editstatus")
    False

For a distribution bug supervisor.

    >>> login("foo.bar@canonical.com")
    >>> ubuntu.bug_supervisor = no_priv
    >>> user_sees_importance_widget(
    ...     user=no_priv,
    ...     url='http://bugs.launchpad.test/'
    ...         'ubuntu/+source/mozilla-firefox/+bug/1/+editstatus')
    True

For a distribution owner.

    >>> login("foo.bar@canonical.com")
    >>> mark.inTeam(ubuntu.owner)
    True

    >>> user_sees_importance_widget(
    ...     user=mark,
    ...     url='http://bugs.launchpad.test/'
    ...         'ubuntu/+source/mozilla-firefox/+bug/1/+editstatus')
    True

For someone else, on Ubuntu.

    >>> login("foo.bar@canonical.com")
    >>> ubuntu.bug_supervisor = None
    >>> user_sees_importance_widget(
    ...     user=no_priv,
    ...     url='http://bugs.launchpad.test/'
    ...         'ubuntu/+source/mozilla-firefox/+bug/1/+editstatus')
    False
