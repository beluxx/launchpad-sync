============================================
Adding a new architecture to a distro series
============================================

Launchpad admins are allowed to add a new arch (also called 'port') to a
given distro series.

    >>> admin_browser.open("http://launchpad.test/ubuntu/hoary")
    >>> admin_browser.getLink("Add architecture").click()
    >>> print(admin_browser.title)
    Add a port of The Hoary...

There is a cancel link.

    >>> admin_browser.getLink("Cancel")
    <Link text='Cancel' url='http://launchpad.test/ubuntu/hoary'>

To register a new architecture one has to specify the architecture tag, the
processor and whether or not that architecture is officially supported
and/or has PPA support.

    >>> admin_browser.getControl("Architecture Tag").value = "ia64"
    >>> admin_browser.getControl("Processor:").value = ["amd64"]
    >>> admin_browser.getControl("Official Support").selected = True
    >>> admin_browser.getControl("Continue").click()
    >>> print(admin_browser.title)
    ia64 : Hoary (5.04) : Ubuntu

Architecture tag is restricted to the usual Launchpad name format.

    >>> admin_browser.open("http://launchpad.test/ubuntu/hoary")
    >>> admin_browser.getLink("Add architecture").click()
    >>> admin_browser.getControl("Architecture Tag").value = "foo bar"
    >>> admin_browser.getControl("Continue").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    Invalid name 'foo bar'. ...

Other users won't see the link nor the page where a new port can be
registered.

    >>> user_browser.open("http://launchpad.test/ubuntu/hoary")
    >>> user_browser.getLink("Add architecture")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.open("http://launchpad.test/ubuntu/hoary/+addport")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...
