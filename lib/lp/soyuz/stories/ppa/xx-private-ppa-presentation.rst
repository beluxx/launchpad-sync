Private Personal Package Archives Presentation
==============================================

Private PPAs are presented differently to standard PPAs.  This pagetest
describes the appearance.

Standard presentation
---------------------

Public PPAs appear like any other launchpad page.

    >>> browser.open("http://launchpad.test/~cprov/+archive")
    >>> from lp.services.beautifulsoup import BeautifulSoup
    >>> body_el = BeautifulSoup(browser.contents).find('body')
    >>> 'private' in body_el['class']
    False

Private presentation
--------------------

Let's create a private PPA for Celso and see what it looks like.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login('admin@canonical.com')
    >>> cprov = getUtility(IPersonSet).getByName('cprov')
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> private_ppa = factory.makeArchive(
    ...     owner=cprov, name="p3a", distribution=ubuntu, private=True)
    >>> logout()

When the PPA is private it gains the standard Launchpad
presentation for private items.

    >>> cprov_browser = setupBrowser(
    ...     auth='Basic celso.providelo@canonical.com:test')
    >>> cprov_browser.open("http://launchpad.test/~cprov/+archive/p3a")
    >>> body_el = BeautifulSoup(cprov_browser.contents).find('body')
    >>> 'private' in body_el['class']
    True
