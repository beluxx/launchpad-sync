Private Personal Package Archives
=================================

Private PPAs prevent anyone other than the PPA owner, its team members
or an admin from seeing the PPA.  This page test describes how
this works in practice in the UI.

Define a helper function
------------------------

We'll use this function later to print what PPAs are in the +ppas listing.

    >>> def list_ppas_in_browser_page(browser):
    ...     ppas = [
    ...         extract_text(ppa_row)
    ...         for ppa_row in find_tags_by_class(
    ...             browser.contents, "ppa_batch_row"
    ...         )
    ...     ]
    ...     print("\n".join(ppas))
    ...


Set Up a Private PPA
--------------------

First we'll create a private PPA for Celso.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login("admin@canonical.com")
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> cprov_private_ppa = factory.makeArchive(
    ...     owner=cprov, name="p3a", distribution=ubuntu, private=True
    ... )
    >>> logout()

PPA Listing Page
----------------

The /+ppas page normally shows all PPAs.  However, if they are private
they are not shown to non-authorised users.

    >>> browser.open("http://launchpad.test/ubuntu/+ppas")
    >>> browser.getControl(name="show_inactive").value = True
    >>> browser.getControl("Search", index=0).click()
    >>> list_ppas_in_browser_page(browser)
    PPA for Celso Providelo...
    PPA for Mark Shuttleworth...
    PPA for No Privileges Person...

The owner of the archive will see their own archive in the listing:

    >>> cprov_browser = setupBrowser(
    ...     auth="Basic celso.providelo@canonical.com:test"
    ... )
    >>> cprov_browser.open("http://launchpad.test/ubuntu/+ppas")
    >>> cprov_browser.getControl(name="show_inactive").value = True
    >>> cprov_browser.getControl("Search", index=0).click()
    >>> list_ppas_in_browser_page(cprov_browser)
    PPA for Celso Providelo...
    PPA for Mark Shuttleworth...
    PPA for No Privileges Person...
    PPA named p3a for Celso Providelo...

Let's make a new team PPA for "landscape-developers" and make it
private.

    >>> admin_browser.open("http://launchpad.test/~landscape-developers")

    >>> admin_browser.getLink("Create a new PPA").click()
    >>> admin_browser.getControl(
    ...     name="field.displayname"
    ... ).value = "PPA for Landscape Developers"
    >>> admin_browser.getControl(name="field.accepted").value = True
    >>> admin_browser.getControl("Activate").click()

    >>> admin_browser.getLink("Administer archive").click()
    >>> admin_browser.getControl(name="field.private").value = True
    >>> admin_browser.getControl("Save").click()

A member of a private team PPA will see their team's PPA in the listing.
"name12" is a member of landscape-developers, so is permitted to see
the landscape-developers PPA:

    >>> name12_browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> name12_browser.open("http://launchpad.test/ubuntu/+ppas")
    >>> name12_browser.getControl(name="show_inactive").value = True
    >>> name12_browser.getControl("Search", index=0).click()
    >>> list_ppas_in_browser_page(name12_browser)
    PPA for Celso Providelo...
    PPA for Landscape Developers...
    PPA for Mark Shuttleworth...
    PPA for No Privileges Person...

Administrators will see all private PPAs in the listing:

    >>> admin_browser.open("http://launchpad.test/ubuntu/+ppas")
    >>> admin_browser.getControl(name="show_inactive").value = True
    >>> admin_browser.getControl("Search", index=0).click()
    >>> list_ppas_in_browser_page(admin_browser)
    PPA for Celso Providelo...
    PPA for Landscape Developers...
    PPA for Mark Shuttleworth...
    PPA for No Privileges Person...


Accessing the Archive Pages
---------------------------

A non-privileged user cannot access the private PPA pages.

    >>> browser.open("http://launchpad.test/~cprov/+archive/p3a")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> browser.open("http://launchpad.test/~landscape-developers/+archive")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

"cprov" can access his own PPA page, but not the landscape-developers
one because he is not a member of that team, nor an admin.

    >>> cprov_browser.open("http://launchpad.test/~cprov/")
    >>> print_tag_with_id(cprov_browser.contents, "ppas")
    Personal package archives
    PPA named p3a for Celso Providelo
    PPA for Celso Providelo
    Create a new PPA

    >>> cprov_browser.getLink("PPA named p3a for Celso Providelo").click()

    >>> print(cprov_browser.title)
    PPA named p3a for Celso Providelo : Celso Providelo

When a non-privileged user browses to a profile page for a person or
team that has a private PPA for which they are not authorised to see, the
link to the PPA page is not present.

    >>> browser.open("http://launchpad.test/~landscape-developers")
    >>> print(find_tag_by_id(browser.contents, "ppas"))
    None

    >>> browser.getLink("PPA for Landscape Developers").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

"name12" is a member of landscape-developers, so is permitted to access
the landscape-developers PPA page.

    >>> name12_browser.open("http://launchpad.test/~landscape-developers")
    >>> print_tag_with_id(name12_browser.contents, "ppas")
    Personal package archives
    PPA for Landscape Developers
    Create a new PPA

    >>> name12_browser.getLink("PPA for Landscape Developers").click()

    >>> name12_browser.url
    'http://launchpad.test/~landscape-developers/+archive/ubuntu/ppa'

Administrators can access all private PPAs.

    >>> admin_browser.open("http://launchpad.test/~cprov")
    >>> admin_browser.getLink("PPA named p3a for Celso Providelo").click()
    >>> admin_browser.url
    'http://launchpad.test/~cprov/+archive/ubuntu/p3a'

    >>> admin_browser.open("http://launchpad.test/~landscape-developers")
    >>> admin_browser.getLink("PPA for Landscape Developers").click()
    >>> admin_browser.url
    'http://launchpad.test/~landscape-developers/+archive/ubuntu/ppa'

