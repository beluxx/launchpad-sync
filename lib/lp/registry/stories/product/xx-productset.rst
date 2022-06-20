================
Product Set Page
================

Under "/projects" there are several pages for various administration tasks.

The pages are "+review-licenses", "+new", and "+all".

Review project licences
-----------------------

The page +review-licenses is accessible from the /projects page via
the "Review licences" link, which is conditionally available
based on permissions.

A member of the Launchpad registry experts team may successfully access the
+review-licenses via the link.

    >>> login('foo.bar@canonical.com')
    >>> from zope.component import getUtility
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> registry_member = factory.makePerson(
    ...     name='reggie', email='reggie@example.com')
    >>> celebs = getUtility(ILaunchpadCelebrities)
    >>> registry = celebs.registry_experts
    >>> ignored = registry.addMember(registry_member, registry.teamowner)
    >>> logout()

    >>> registry_browser = setupBrowser(
    ...     auth='Basic reggie@example.com:test')
    >>> registry_browser.open(
    ...     'http://launchpad.test/projects/')
    >>> registry_browser.getLink("Review projects").click()
    >>> registry_browser.url
    'http://launchpad.test/projects/+review-licenses'
    >>> print(registry_browser.title)
    Review projects...


View all projects
=================

The unprivileged user can see "+all".

    >>> user_browser.open('http://launchpad.test/projects/+all')
    >>> print(user_browser.title)
    Projects registered in Launchpad...

The commercial user can also view "+all".

    >>> registry_browser.open('http://launchpad.test/projects/+all')
    >>> print(registry_browser.title)
    Projects registered in Launchpad...


Create a project
================

The unprivileged user can see "+new".

    >>> user_browser.open('http://launchpad.test/projects/+new')
    >>> print(user_browser.title)
    Register a project in Launchpad...

The commercial user can also view "+new".

    >>> registry_browser.open('http://launchpad.test/projects/+new')
    >>> print(registry_browser.title)
    Register a project in Launchpad...

The commercial user can also view "+new".

    >>> registry_browser.open('http://launchpad.test/projects/+new')
    >>> print(registry_browser.title)
    Register a project in Launchpad...
