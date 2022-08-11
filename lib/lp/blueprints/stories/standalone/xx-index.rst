=====================
Blueprints index page
=====================
Enabling Firefox
----------------

For a product to work in blueprints, it must be active, so we'll activate
blueprints for firefox.

    >>> from zope.component import getUtility
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.registry.interfaces.product import IProductSet
    >>> login('admin@canonical.com')
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> firefox.blueprints_usage = ServiceUsage.LAUNCHPAD
    >>> transaction.commit()
    >>> logout()

The blueprints index page allows users to search for blueprints within
a single Launchpad project or across all projects.

Users can see the latest blueprints available for the whole system:

    >>> user_browser.open('http://blueprints.launchpad.test/')
    >>> print(extract_text(find_main_content(user_browser.contents)))
    Blueprints
    All projects...
    Recently registered
        The Krunch Desktop Plan
        KDE Desktop File Language Packs
        The REVU Review Tracking System
        Facilitate mass installs of Ubuntu using Netboot configuration
        CD Media Integrity Check
    Recently completed
        Activating Usplash during Hibernation
        Support for local devices on Ubuntu thin clients...

Users can search for a particular blueprint by entering a search string.
For example, let's search for blueprints with the string 'svg' in their
name and title, across all projects:

    >>> browser.open('http://blueprints.launchpad.test/')
    >>> browser.getControl(name='field.search_text').value = 'svg'
    >>> browser.getControl(name='field.scope').value = ['all']
    >>> browser.getControl(name='field.actions.search').click()
    >>> print(browser.url)
    http://blueprints.launchpad.test/?searchtext=svg

There is one such blueprint for the Firefox project, and it is listed
among the results:

    >>> print(extract_text(find_tag_by_id(browser.contents, 'specs-table')))
    Support Native SVG Objects
    ...

We try the same search within the Firefox project only, expecting to
find the same result:

    >>> browser.open('http://blueprints.launchpad.test/')
    >>> browser.getControl(name='field.search_text').value = 'svg'
    >>> browser.getControl(name='field.scope').value = ['project']
    >>> browser.getControl(name='field.scope.target').value = 'firefox'
    >>> browser.getControl(name='field.actions.search').click()
    >>> print(browser.url)
    http://blueprints.launchpad.test/firefox?searchtext=svg
    >>> print(browser.getLink('svg-support').attrs['title'])
    Support Native SVG Objects

The search form forces us to choose either searching within all projects
or searching within one project, using radio button controls, but it is
possible for a client to request the results directly (for example, if
the client is a robot, and is not interacting with the form we set up).
If no value is supplied for the scope parameter, we assume that the
client wanted to search all projects.

We request a URL with the search text `svg` and no scope parameter. We
can expect the search to be performed over all projects, just like when
selecting the `all` scope:

    >>> browser.open('http://blueprints.launchpad.test/specs?'
    ...     'field.actions.search=Find+Blueprints&field.scope.target='
    ...     '&field.search_text=svg')
    >>> print(browser.url)
    http://blueprints.launchpad.test/?searchtext=svg
    >>> print(extract_text(find_tag_by_id(browser.contents, 'specs-table')))
    Support Native SVG Objects
    ...
