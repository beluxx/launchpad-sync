Distribution series administration
=================================

Administrators
--------------

Launchpad administrators can edit distroseries via two different
pages: 'Change details' and 'Administer'.

    >>> admin_browser.open("http://launchpad.test/ubuntu/hoary")
    >>> print(admin_browser.title)
    Hoary (5.04)...
    >>> admin_browser.getLink("Change details").click()
    >>> print(admin_browser.url)
    http://launchpad.test/ubuntu/hoary/+edit

    >>> print(admin_browser.title)
    Edit The Hoary Hedgehog Release...

    >>> admin_browser.getControl("Display name", index=0).value = "Happy"
    >>> admin_browser.getControl("Change").click()
    >>> print(admin_browser.title)
    Happy (5.04)...

A separate administration page is available via the 'Administer' link.

    >>> admin_browser.open("http://launchpad.test/ubuntu/hoary")
    >>> admin_browser.getLink("Administer").click()
    >>> print(admin_browser.url)
    http://launchpad.test/ubuntu/hoary/+admin

    >>> print(admin_browser.title)
    Administer The Hoary Hedgehog Release...

    >>> admin_browser.getControl("Name", index=0).value = "happy"
    >>> admin_browser.getControl("Version", index=0).value = "5.05"
    >>> admin_browser.getControl("Change").click()
    >>> print(admin_browser.url)
    http://launchpad.test/ubuntu/happy
    >>> print(admin_browser.title)
    Happy (5.05)...


Registry experts
----------------

Registry experts do not have access to the 'Change details' link.

    >>> email = "expert@example.com"
    >>> registry = factory.makeRegistryExpert(email=email)
    >>> logout()
    >>> registry_browser = setupBrowser(auth="Basic %s:test" % email)
    >>> registry_browser.open("http://launchpad.test/ubuntu/happy")
    >>> registry_browser.getLink("Change details").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

And navigating directly to +edit is thwarted.

    >>> registry_browser.open("http://launchpad.test/ubuntu/happy/+edit")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Registry experts do have access to the administration page.

    >>> registry_browser.open("http://launchpad.test/ubuntu/happy")
    >>> registry_browser.getLink("Administer").click()
    >>> print(registry_browser.url)
    http://launchpad.test/ubuntu/happy/+admin

    >>> print(registry_browser.title)
    Administer The Hoary Hedgehog Release...

    >>> registry_browser.getControl("Name", index=0).value = "hoary"
    >>> registry_browser.getControl("Version", index=0).value = "5.04"
    >>> registry_browser.getControl("Change").click()
    >>> print(registry_browser.url)
    http://launchpad.test/ubuntu/hoary
    >>> print(registry_browser.title)
    Happy (5.04)...
