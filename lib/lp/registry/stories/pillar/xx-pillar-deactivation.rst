Pillar deactivation and reactivation
====================================

This test demonstrates what happens when you deactivate and reactivate
pillars (Projects, Project Groups and Distributions).

XXX: Distributions can't yet be marked inactive, so this test won't
cover that part of the change. See bug #156263 for more details.
    -- kiko, 2007-10-23

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.pillar import IPillarNameSet
    >>> from lp.registry.interfaces.product import IProduct
    >>> from lp.testing import unlink_source_packages
    >>> pillar_set = getUtility(IPillarNameSet)
    >>> def toggleProject(name):
    ...     login("admin@canonical.com")
    ...     pillar = pillar_set.getByName(name)
    ...     if IProduct.providedBy(pillar) and pillar.active:
    ...         # A product cannot be deactivated if
    ...         # it is linked to source packages.
    ...         unlink_source_packages(pillar)
    ...     pillar.active = not pillar.active
    ...     logout()
    ...

We start off with active and visible projects:

    >>> anon_browser.open(
    ...     "http://launchpad.test/projects/+index?text=firefox"
    ... )
    >>> anon_browser.getLink(url="/firefox").click()
    >>> anon_browser.title
    'Mozilla Firefox in Launchpad'

    >>> anon_browser.open(
    ...     "http://launchpad.test/projects/+index?text=mozilla"
    ... )
    >>> anon_browser.getLink(url="/mozilla").click()
    >>> anon_browser.title
    'The Mozilla Project in Launchpad'

We then choose to disable them via each project's +review:

    >>> toggleProject("firefox")
    >>> toggleProject("mozilla")

The projects are now no longer publicly visible:

    >>> anon_browser.open(
    ...     "http://launchpad.test/projects/+index?text=mozilla"
    ... )
    >>> anon_browser.getLink(url="/firefox")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> anon_browser.getLink(url="/mozilla")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> anon_browser.open("http://launchpad.test/firefox")
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...

    >>> anon_browser.open("http://launchpad.test/mozilla")
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...

But an administrator can still see them if they traverse directly, and
they'll see an informative message. They can then reactivate them..

    >>> admin_browser.open("http://launchpad.test/firefox")
    >>> print(
    ...     find_tag_by_id(
    ...         admin_browser.contents, "project-inactive"
    ...     ).decode_contents()
    ... )
     This project is currently inactive...
    >>> toggleProject("firefox")

    >>> admin_browser.open("http://launchpad.test/mozilla")
    >>> print(
    ...     find_tag_by_id(
    ...         admin_browser.contents, "project-inactive"
    ...     ).decode_contents()
    ... )
     This project is currently inactive...
    >>> toggleProject("mozilla")

And they are back to normal:

    >>> anon_browser.open(
    ...     "http://launchpad.test/projects/+index?text=firefox"
    ... )
    >>> anon_browser.getLink(url="/firefox").click()
    >>> anon_browser.title
    'Mozilla Firefox in Launchpad'
    >>> print(find_tag_by_id(anon_browser.contents, "project-inactive"))
    None

    >>> anon_browser.open(
    ...     "http://launchpad.test/projects/+index?text=mozilla"
    ... )
    >>> anon_browser.getLink(url="/mozilla").click()
    >>> anon_browser.title
    'The Mozilla Project in Launchpad'
    >>> print(find_tag_by_id(anon_browser.contents, "project-inactive"))
    None
