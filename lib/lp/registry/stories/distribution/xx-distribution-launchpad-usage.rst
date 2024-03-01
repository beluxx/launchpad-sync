Distribution Launchpad usage
============================

The distribution overview page has links to allow you to configure which
services use Launchpad.

Unprivileged Launchpad users cannot access the page for changing these
details.

    >>> user_browser.open("http://launchpad.test/ubuntu")
    >>> user_browser.getLink("Change details")
    Traceback (most recent call last):
      ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.getLink("Configure publisher")
    Traceback (most recent call last):
      ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.open("http://launchpad.test/ubuntu/+edit")
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

Create a restricted processor.

    >>> login("admin@canonical.com")
    >>> ign = factory.makeProcessor(
    ...     name="arm", restricted=True, build_by_default=False
    ... )
    >>> logout()

The distribution's registrant can access the page and change the usage.

    >>> registrant = setupBrowser(
    ...     auth="Basic celso.providelo@canonical.com:test"
    ... )
    >>> registrant.open("http://launchpad.test/ubuntu/+edit")
    >>> print(registrant.url)
    http://launchpad.test/ubuntu/+edit

    >>> print(registrant.getControl(name="field.translations_usage").value[0])
    LAUNCHPAD
    >>> print(registrant.getControl(name="field.official_malone").value)
    True
    >>> print(registrant.getControl(name="field.enable_bug_expiration").value)
    True
    >>> print(registrant.getControl(name="field.blueprints_usage").value[0])
    LAUNCHPAD
    >>> print(registrant.getControl(name="field.answers_usage").value[0])
    LAUNCHPAD
    >>> print(
    ...     bool(
    ...         registrant.getControl(name="field.require_virtualized").value
    ...     )
    ... )
    False
    >>> print(registrant.getControl(name="field.processors").value)
    ['386', 'amd64', 'hppa']

    >>> registrant.getControl(name="field.translations_usage").value = [
    ...     "UNKNOWN"
    ... ]
    >>> registrant.getControl("Change", index=3).click()

Just like Launchpad administrators can.

    >>> admin_browser.open("http://launchpad.test/ubuntu")
    >>> admin_browser.getLink("Change details").click()
    >>> print(admin_browser.title)
    Change Ubuntu details...
    >>> print(
    ...     admin_browser.getControl(name="field.translations_usage").value[0]
    ... )
    UNKNOWN
    >>> print(admin_browser.getControl(name="field.official_malone").value)
    True
    >>> print(
    ...     admin_browser.getControl(name="field.enable_bug_expiration").value
    ... )
    True
    >>> print(
    ...     admin_browser.getControl(name="field.blueprints_usage").value[0]
    ... )
    LAUNCHPAD
    >>> print(admin_browser.getControl(name="field.answers_usage").value[0])
    LAUNCHPAD

    >>> admin_browser.getControl(name="field.enable_bug_expiration").value = (
    ...     False
    ... )
    >>> admin_browser.getControl(name="field.official_malone").value = False
    >>> admin_browser.getControl(name="field.blueprints_usage").value = [
    ...     "UNKNOWN"
    ... ]
    >>> admin_browser.getControl(name="field.answers_usage").value = [
    ...     "UNKNOWN"
    ... ]
    >>> admin_browser.getControl("Change", index=3).click()

    >>> print(admin_browser.url)
    http://launchpad.test/ubuntu

Only administrators can configure the publisher for the distribution:

    >>> admin_browser.getLink("Configure publisher").click()
    >>> print(admin_browser.title)
    Publisher configuration for...

    >>> admin_browser.getControl(name="field.root_dir").value = (
    ...     "/tmp/root_dir"
    ... )
    >>> admin_browser.getControl(name="field.base_url").value = (
    ...     "http://base.url/"
    ... )
    >>> admin_browser.getControl(name="field.copy_base_url").value = (
    ...     "http://copy.base.url/"
    ... )
    >>> admin_browser.getControl("Save").click()

    >>> print(admin_browser.url)
    http://launchpad.test/ubuntu


enable_bug_expiration and JavaScript
====================================

JavaScript is used to constrain enable_bug_expiration to distributions
that use Launchpad to track bugs. If the form is submitted before the
page has loaded, the enable_bug_expiration will not be disabled by the
JavaScript function. The constraint is enforced by the view class--the
data is corrected instead of returning a error to the user.

Foo Bar updates Ubuntu to use Launchpad to track bugs, and enables
bug expiration.

    >>> admin_browser.getLink("Change details").click()
    >>> admin_browser.getControl(name="field.enable_bug_expiration").value = (
    ...     True
    ... )
    >>> admin_browser.getControl(name="field.official_malone").value = True
    >>> admin_browser.getControl("Change", index=3).click()

    >>> content = find_main_content(admin_browser.contents)

Foo Bar chooses to switch the bug tracker again, but this time they
do not change the expiration check box, and they do the whole
operation before the page complete loading.

    >>> admin_browser.getLink("Change details").click()
    >>> print(admin_browser.getControl(name="field.official_malone").value)
    True

    >>> print(
    ...     admin_browser.getControl(name="field.enable_bug_expiration").value
    ... )
    True

    >>> admin_browser.getControl(name="field.official_malone").value = False
    >>> admin_browser.getControl("Change", index=3).click()

    >>> content = find_main_content(admin_browser.contents)
