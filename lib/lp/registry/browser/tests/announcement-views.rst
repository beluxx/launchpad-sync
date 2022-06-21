Announcement Pages
==================

Tests for breadcrumbs, menus, and pages.


Breadcrumbs
-----------

Announcement breadcrumbs use the announcement title.

    >>> from lp.testing.menu import make_fake_request

    >>> product = factory.makeProduct(name='cube')
    >>> owner = product.owner
    >>> announcement = product.announce(
    ...     user=owner, title='A title', summary='A summary')
    >>> view = create_initialized_view(announcement, '+index')

    >>> request = make_fake_request(
    ...     'http://launchpad.test/joy-of-cooking/spam',
    ...     [product, announcement, view])
    >>> hierarchy = create_initialized_view(
    ...     announcement, '+hierarchy', request=request)
    >>> hierarchy.items
    [<PillarBreadcrumb ... text='Cube'>, <TitleBreadcrumb ... text='A title'>]


Menus
-----

The announcement module provides two menus. There is an edit menu for an
announcement.

    >>> from lp.registry.browser.announcement import (
    ...     AnnouncementEditNavigationMenu, AnnouncementCreateNavigationMenu)
    >>> from lp.testing.menu import check_menu_links

    >>> check_menu_links(AnnouncementEditNavigationMenu(announcement))
    True

There is a menu for views for IHasAnnouncements objects to list there
announcements. The product implements IHasAnnouncements.

    >>> check_menu_links(AnnouncementCreateNavigationMenu(product))
    True


Batching
--------

Announcements are presented in batches.  For launchpad.test the batch size is
smaller than in production to ease testing.

    >>> from lp.registry.interfaces.announcement import IAnnouncementSet
    >>> announcement_set = getUtility(IAnnouncementSet)
    >>> view = create_initialized_view(
    ...     announcement_set, '+announcements')
    >>> print(len(list(view.announcements)))
    20
    >>> print(view.batch_size)
    4
    >>> batch = view.announcement_nav.currentBatch()
    >>> print(len(list(batch)))
    4
