====================
NavigationMenu views
====================

Navigation menus are used to create links to related pages. The menus
are usually bound to a view.

    >>> from zope.component import provideAdapter
    >>> from zope.interface import implementer, Interface
    >>> from lp.services.webapp.interfaces import INavigationMenu
    >>> from lp.services.webapp.menu import (
    ...     enabled_with_permission, Link, NavigationMenu)
    >>> from lp.services.webapp.publisher import LaunchpadView
    >>> from lp.services.webapp.servers import LaunchpadTestRequest

    >>> class IEditMenuMarker(Interface):
    ...     """A marker for a menu and a view."""

    >>> class EditMenu(NavigationMenu):
    ...     """A simple menu."""
    ...     usedfor = IEditMenuMarker
    ...     facet = 'overview'
    ...     title = 'Related pages'
    ...     links = ('edit_thing', 'edit_people', 'admin')
    ...
    ...     def edit_thing(self):
    ...         return Link('+edit', 'Edit thing', icon='edit')
    ...
    ...     def edit_people(self):
    ...         return Link('+edit-people', 'Edit people related to thing')
    ...
    ...     @enabled_with_permission('launchpad.Admin')
    ...     def admin(self):
    ...         return Link('+admin', 'Administer this user')

    >>> @implementer(IEditMenuMarker)
    ... class EditView(LaunchpadView):
    ...     """A simple view."""
    ...     # A hack that reveals secret of how facets work.
    ...     __launchpad_facetname__ = 'overview'

    # Menus are normally registered using the menu ZCML directive.
    >>> provideAdapter(
    ...     EditMenu, [IEditMenuMarker], INavigationMenu, name="overview")


Related pages
=============

The related pages portlet is rendered using a TALES call passing the view
to the named adapter: <tal:menu replace="structure view/@@+related-pages" />

    >>> user = factory.makePerson(name='beaker')
    >>> view = EditView(user, LaunchpadTestRequest())
    >>> menu_view = create_initialized_view(
    ...     view, '+related-pages', principal=user)
    >>> print(menu_view.template.filename)
    /.../navigationmenu-related-pages.pt

The view provides access the menu's title and links. Both the enabled
and disabled links are included.

    >>> print(menu_view.title)
    Related pages
    >>> for link in menu_view.links:
    ...     print(link.enabled, link.url)
    True   http://launchpad.test/~beaker/+edit
    True   http://launchpad.test/~beaker/+edit-people
    False  http://launchpad.test/~beaker/+admin

The view renders the heading using the menu title and a list of the links. A
link is rendered only if its 'enabled' property is true. The template uses the
inline-link rules, if the link has an icon, the classes are set, otherwise a
style attribute is used.

    >>> print(menu_view.render())
    <div id="related-pages" class="portlet">
      <h2>Related pages</h2>
    <BLANKLINE>
      <ul>
    <BLANKLINE>
        <li>
          <a class="menu-link-edit_thing sprite modify edit"
             href="http://launchpad.test/~beaker/+edit">Edit thing</a>
        </li>
    <BLANKLINE>
    <BLANKLINE>
        <li>
            <a class="menu-link-edit_people"
               href="http://launchpad.test/~beaker/+edit-people">Edit
                 people related to thing</a>
        </li>
        ...
    </div>
    <BLANKLINE>

If the link matches the requested URL, then the 'linked' attribute will be
unset, and then only the link icon and text will be displayed, but it will not
be clickable.

    >>> request = LaunchpadTestRequest(
    ...     SERVER_URL='http://launchpad.test/~beaker/+edit')
    >>> print(request.getURL())
    http://launchpad.test/~beaker/+edit

    >>> view = EditView(user, request)
    >>> menu_view = create_initialized_view(
    ...     view, '+related-pages', principal=user)
    >>> for link in menu_view.links:
    ...     print(link.enabled, link.linked, link.url)
    True  False  http://launchpad.test/~beaker/+edit
    True  True   http://launchpad.test/~beaker/+edit-people
    False True   http://launchpad.test/~beaker/+admin

    >>> print(menu_view.render())
    <div id="related-pages" class="portlet">
      <h2>Related pages</h2>
    ...
          <li>
            <span class="menu-link-edit_thing nolink
                  sprite modify edit">Edit thing</span>
          </li>
    ...


Action menus
============

A navigation menu can be presented as an action menu in the side portlets.
The action menu uses the view's enabled_links property to get the list of
links.

    >>> menu_view = create_initialized_view(
    ...     view, '+global-actions', principal=user)
    >>> for link in menu_view.enabled_links:
    ...     print(link.enabled, link.linked, link.url)
    True  False  http://launchpad.test/~beaker/+edit
    True  True   http://launchpad.test/~beaker/+edit-people

The generated markup is for a portlet with the global-actions id.

    >>> print(menu_view.render())
    <div id="global-actions" class="portlet vertical">
      <ul>
        <li>
          <span class="menu-link-edit_thing nolink
              sprite modify edit">Edit thing</span>
        </li>
        <li>
          <a class="menu-link-edit_people"
             href="http://launchpad.test/~beaker/+edit-people">Edit
               people related to thing</a>
        </li>
      </ul>
    </div>
    <BLANKLINE>

If there are no enabled links, no markup is rendered. For example, a menu
may contain links that require special privileges to access.

    >>> EditMenu.links = ('admin',)

    >>> menu_view = create_initialized_view(
    ...     view, '+global-actions', principal=user)
    >>> menu_view.enabled_links
    []

    >>> print(menu_view.render())
    <BLANKLINE>
