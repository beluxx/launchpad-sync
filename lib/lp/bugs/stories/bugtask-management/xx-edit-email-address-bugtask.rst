Editing Email Address bugtasks
==============================

    >>> import transaction
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.testing import ANONYMOUS, login, logout

    >>> from zope.security.proxy import removeSecurityProxy
    >>> def widget_visibility(user, url):
    ...     naked_email = removeSecurityProxy(user.preferredemail)
    ...     browser = setupBrowser("Basic %s:test" % naked_email.email)
    ...     transaction.commit()
    ...     logout()
    ...     browser.open(url)
    ...     try:
    ...         browser.getControl("Status")
    ...     except LookupError:
    ...         status = False
    ...     else:
    ...         status = True
    ...     try:
    ...         browser.getControl("Importance")
    ...     except LookupError:
    ...         importance = False
    ...     else:
    ...         importance = True
    ...     return status, importance
    ...

    >>> def print_widget_visibility(user, url):
    ...     status, importance = widget_visibility(user, url)
    ...     print("Status: %s\nImportance: %s" % (status, importance))
    ...


"Normal" (not Email Address) bugtasks
-------------------------------------

Normally, it's not possible to edit the status or importance of a
bugtask associated with a bugwatch that is linked to an external bug
tracker, because status and importance are updated by checkwatches.

To prepare, we must add a task that references a bug tracked
elsewhere:

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/"
    ...     "jokosher/+bug/12/+choose-affected-product"
    ... )
    >>> user_browser.getControl("Project").value = "gnome-terminal"
    >>> user_browser.getControl("Continue").click()
    >>> user_browser.getControl("I have the URL").selected = True
    >>> user_browser.getControl(name="field.bug_url").value = (
    ...     "http://mantis.bugtracker/view.php?id=1234"
    ... )
    >>> user_browser.getControl("Add to Bug Report").click()
    >>> user_browser.getControl(
    ...     "Register Bug Tracker and Add to Bug Report"
    ... ).click()

    >>> user_browser.url
    'http://bugs.launchpad.test/gnome-terminal/+bug/12'

The product owner cannot see the Status or Importance widgets:

    >>> login("foo.bar@canonical.com")
    >>> gnome_terminal = getUtility(IProductSet).getByName("gnome-terminal")

    >>> login(ANONYMOUS)
    >>> print(gnome_terminal.owner.name)
    name12
    >>> print_widget_visibility(
    ...     user=gnome_terminal.owner,
    ...     url=(
    ...         "http://bugs.launchpad.test/"
    ...         "gnome-terminal/+bug/12/+editstatus"
    ...     ),
    ... )
    Status: False
    Importance: False

Nor can an ordinary user:

    >>> login("foo.bar@canonical.com")
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> print_widget_visibility(
    ...     user=no_priv,
    ...     url=(
    ...         "http://bugs.launchpad.test/"
    ...         "gnome-terminal/+bug/12/+editstatus"
    ...     ),
    ... )
    Status: False
    Importance: False

And the bug supervisor can't see the widgets either.

    >>> login("foo.bar@canonical.com")
    >>> gnome_terminal.bug_supervisor = no_priv
    >>> print_widget_visibility(
    ...     user=no_priv,
    ...     url=(
    ...         "http://bugs.launchpad.test/"
    ...         "gnome-terminal/+bug/12/+editstatus"
    ...     ),
    ... )
    Status: False
    Importance: False


Email Address bugtasks
----------------------

The status and importance of a bugtask with an email address bugwatch
will be editable.

To prepare, we add a task that references a bug that's tracked by
email:

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/"
    ...     "gnome-terminal/+bug/12/+choose-affected-product"
    ... )
    >>> user_browser.getControl("Project").value = "alsa-utils"
    >>> user_browser.getControl("Continue").click()
    >>> user_browser.getControl("I have already emailed").selected = True
    >>> user_browser.getControl(
    ...     name="field.upstream_email_address_done"
    ... ).value = "bugs@example.com"
    >>> user_browser.getControl("Add to Bug Report").click()

    >>> user_browser.url
    'http://bugs.launchpad.test/alsa-utils/+bug/12'

The owner can see the Status and Importance widgets.

    >>> login("foo.bar@canonical.com")
    >>> alsa_utils = getUtility(IProductSet).getByName("alsa-utils")

    >>> login(ANONYMOUS)
    >>> print(alsa_utils.owner.name)
    mark

    >>> print_widget_visibility(
    ...     user=alsa_utils.owner,
    ...     url=(
    ...         "http://bugs.launchpad.test/" "alsa-utils/+bug/12/+editstatus"
    ...     ),
    ... )
    Status: True
    Importance: True

An ordinary user can see the Status widget. They can't see the
Importance widget because they would not normally be permitted to alter
the importance of a bugtask in Alsa Utils.

    >>> login("foo.bar@canonical.com")
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")

    >>> print_widget_visibility(
    ...     user=no_priv,
    ...     url=(
    ...         "http://bugs.launchpad.test/" "alsa-utils/+bug/12/+editstatus"
    ...     ),
    ... )
    Status: True
    Importance: False

A bug supervisor can see both.

    >>> login("foo.bar@canonical.com")
    >>> alsa_utils.bug_supervisor = no_priv
    >>> print_widget_visibility(
    ...     user=no_priv,
    ...     url=(
    ...         "http://bugs.launchpad.test/" "alsa-utils/+bug/12/+editstatus"
    ...     ),
    ... )
    Status: True
    Importance: True
