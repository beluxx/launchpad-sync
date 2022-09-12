Person Team Branches Portlet
============================

The purpose of this portlet is to indiciate that there are teams
that this person participates in that has branches.

The portlet only appears when the persons teams actually have branches,
and only teams that have branches are shown.

    >>> login(ANONYMOUS)
    >>> eric = factory.makePerson(
    ...     name="eric",
    ...     email="eric@example.com",
    ...     displayname="Eric the Viking",
    ... )
    >>> vikings = factory.makeTeam(name="vikings", owner=eric)

Also give vikings a cool icon.

    >>> icon = factory.makeLibraryFileAlias(
    ...     filename="vikings.png", content_type="image/png"
    ... )
    >>> from lp.testing import run_with_login
    >>> run_with_login(eric, setattr, vikings, "icon", icon)
    >>> logout()

Initially Eric's teams have no branches, so there is not be a portlet
there.

    >>> browser.open("http://code.launchpad.test/~eric")
    >>> portlet = find_tag_by_id(browser.contents, "portlet-team-branches")
    >>> print(portlet)
    None

    >>> login(ANONYMOUS)
    >>> vb = factory.makeAnyBranch(owner=vikings)
    >>> logout()

    >>> browser.open("http://code.launchpad.test/~eric")
    >>> tb = find_tag_by_id(browser.contents, "portlet-team-branches")
    >>> print(extract_text(tb.h2))
    Branches owned by
    >>> print(tb.li)
    <li>
      <img height="14" src="http://.../vikings.png" width="14"/>
      <a href="/~vikings">Vikings</a>
    </li>
