Private Teams
=============


Viewing private teams
---------------------

If a team's visibility attribute is set to Private, Launchpad
admins and members of that team can see the team.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet, PersonVisibility
    >>> login("foo.bar@canonical.com")
    >>> owner = factory.makePerson(name="team-owner")
    >>> priv_team = factory.makeTeam(
    ...     name="private-team",
    ...     displayname="Private Team",
    ...     owner=owner,
    ...     visibility=PersonVisibility.PRIVATE,
    ... )
    >>> person_set = getUtility(IPersonSet)
    >>> cprov = person_set.getByName("cprov")
    >>> ignored = login_person(owner)
    >>> ignored = priv_team.addMember(cprov, reviewer=owner)
    >>> logout()

    >>> admin_browser.open("http://launchpad.test/~private-team")
    >>> admin_browser.title
    'Private Team in Launchpad'

    >>> cprov_browser = setupBrowser(
    ...     auth="Basic celso.providelo@canonical.com:test"
    ... )
    >>> cprov_browser.open("http://launchpad.test/~private-team")
    >>> cprov_browser.title
    'Private Team in Launchpad'

The page indicates that the team is private.

    >>> privacy_info = find_tag_by_id(cprov_browser.contents, "privacy")
    >>> print(extract_text(privacy_info))
    Private team

A normal user cannot see the team.

    >>> user_browser.open("http://launchpad.test/~private-team")
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...

An anonymous user cannot see the team.

    >>> anon_browser.open("http://launchpad.test/~private-team")
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...


Operations on a private team
----------------------------

The team can take on a restricted set of roles, such as being
subscribed to a bug, etc.

A regular user cannot subscribe a private team to a bug.
They get an error indicating the team is NotFound.

    >>> user_browser.open("http://launchpad.test/bugs/13")
    >>> user_browser.getLink("Subscribe someone else").click()
    >>> user_browser.getControl(name="field.person").value = "private-team"
    >>> user_browser.getControl("Subscribe user").click()
    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    Invalid value

A member of the team or an admin can subscribe a private team to a bug.

    >>> cprov_browser.open("http://launchpad.test/bugs/15")
    >>> cprov_browser.getLink("Subscribe someone else").click()
    >>> cprov_browser.getControl(name="field.person").value = "private-team"
    >>> cprov_browser.getControl("Subscribe user").click()
    >>> print_feedback_messages(cprov_browser.contents)
    Private Team team has been subscribed to this bug.

The private team has been subscribed to a bug and although a regular user is
allowed to know of the team's existence, they cannot subscribe that team to
another bug.

    >>> user_browser.open("http://launchpad.test/bugs/5")
    >>> user_browser.getLink("Subscribe someone else").click()
    >>> user_browser.getControl(name="field.person").value = "private-team"
    >>> user_browser.getControl("Subscribe user").click()
    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    Constraint not satisfied
