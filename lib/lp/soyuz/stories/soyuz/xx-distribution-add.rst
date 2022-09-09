Creating new distributions
==========================

A non launchpad admin doesn't see the link to create a new distribution on
the distributions page:

    >>> user_browser.open("http://launchpad.test/distros")
    >>> user_browser.getLink("Register a distribution")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

A launchpad admin sees the link to create a new distribution:

    >>> admin_browser.open("http://launchpad.test/distros")
    >>> admin_browser.getLink("Register a distribution").url
    'http://launchpad.test/distros/+add'

A launchpad admin can create a new distribution:

    >>> user_browser.open("http://launchpad.test/distros/+add")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Create a Test distribution:

    >>> admin_browser.open("http://launchpad.test/distros/+add")
    >>> admin_browser.url
    'http://launchpad.test/distros/+add'

    >>> admin_browser.getControl(name="field.name").value = "test"
    >>> admin_browser.getControl("Display Name").value = "Test Distro"
    >>> admin_browser.getControl("Summary").value = "Test Distro Summary"
    >>> admin_browser.getControl(
    ...     "Description"
    ... ).value = "Test Distro Description"
    >>> admin_browser.getControl("Web site URL").value = "foo.com"
    >>> admin_browser.getControl("Members").value = "mark"

    >>> admin_browser.getControl("Save").click()
    >>> admin_browser.url
    'http://launchpad.test/test'

    >>> admin_browser.contents
    '...Test Distro...'
