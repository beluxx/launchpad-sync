Private teams
=============

Some teams may be private, meaning that only the team members (and LP
admins) can see the team and who are the other members of the team.

A regular user cannot get information about a private team and
Launchpad returns a NotFound error to disguise the fact that the team
even exists.

    >>> login("test@canonical.com")
    >>> from lp.registry.interfaces.person import PersonVisibility
    >>> team_owner = factory.makePerson(name="private-team-owner")
    >>> ignored = login_person(team_owner)
    >>> member1 = factory.makePerson(name="member-one")
    >>> private_team = factory.makeTeam(
    ...     owner=team_owner,
    ...     name="private-team",
    ...     visibility=PersonVisibility.PRIVATE,
    ... )
    >>> response = private_team.addMember(member1, team_owner)
    >>> import transaction
    >>> transaction.commit()
    >>> logout()

    >>> from lazr.restful.testing.webservice import pprint_collection

    # XXX: 2008-08-01, salgado: Notice how the total_size is incorrect here.
    # That ought to be fixed at some point.
    >>> member = user_webservice.get("/~private-team-owner").jsonBody()
    >>> response = user_webservice.get(
    ...     member["memberships_details_collection_link"]
    ... )
    >>> pprint_collection(response.jsonBody())
    resource_type_link: 'http://.../#team_membership-page-resource'
    start: 0
    total_size: 1
    ---

    Salgado can see the team since he's a Launchpad admin.

    >>> member = webservice.get("/~private-team-owner").jsonBody()
    >>> response = webservice.get(
    ...     member["memberships_details_collection_link"]
    ... )
    >>> pprint_collection(response.jsonBody())
    resource_type_link: 'http://.../#team_membership-page-resource'
    start: 0
    total_size: 1
    ---
    ...
    status: 'Administrator'
    team_link: 'http://.../~private-team'
    ...

Similarly, when a public team is a sub-team of a private team, non-members
cannot see the private team in the public team's super_team's attribute.

    >>> owner_browser = setupBrowser(auth="Basic owner@canonical.com:test")
    >>> owner_browser.open("http://launchpad.test/~myteam/+addmember")
    >>> owner_browser.getControl("New member").value = "guadamen"
    >>> owner_browser.getControl("Add Member").click()
    >>> admin_browser.open(
    ...     "http://launchpad.test/~guadamen/+invitation/myteam"
    ... )
    >>> admin_browser.getControl("Accept").click()

    >>> team = user_webservice.get("/~guadamen").jsonBody()
    >>> super_teams = user_webservice.get(
    ...     team["super_teams_collection_link"]
    ... ).jsonBody()
    >>> print(super_teams["entries"])
    []

But a user with the proper permissions can see the private super team.

    >>> team = webservice.get("/~guadamen").jsonBody()
    >>> super_teams = webservice.get(
    ...     team["super_teams_collection_link"]
    ... ).jsonBody()
    >>> print(len(super_teams["entries"]))
    1
    >>> print(super_teams["entries"][0]["self_link"])
    http://api.launchpad.test/beta/~myteam


Changing team visibility
========================

New teams when created have public visibility.  That attribute can be
changed by admins and commercial admins but not by regular users.

Create a webservice object for commercial-admins.

    >>> from zope.component import getUtility
    >>> from lp.testing import ANONYMOUS, login, logout
    >>> from lp.testing.pages import webservice_for_person
    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login(ANONYMOUS)
    >>> commercial_admin = (
    ...     getUtility(IPersonSet)
    ...     .getByName("commercial-admins")
    ...     .activemembers[0]
    ... )
    >>> logout()
    >>> comm_webservice = webservice_for_person(
    ...     commercial_admin, permission=OAuthPermission.WRITE_PRIVATE
    ... )

    >>> print(
    ...     comm_webservice.named_post(
    ...         "/people",
    ...         "newTeam",
    ...         {},
    ...         name="my-new-team",
    ...         display_name="My New Team",
    ...     )
    ... )
    HTTP/1.1 201 Created
    ...
    Location: http://.../~my-new-team
    ...
    >>> team = webservice.get("/~my-new-team").jsonBody()
    >>> print(team["self_link"])
    http://api.launchpad.test/.../~my-new-team
    >>> print(team["visibility"])
    Public

A commercial admin may change the visibility.  There is no helper
method to do it, but it can be changed via a patch.

    >>> import json
    >>> def modify_team(team, representation, method, service):
    ...     "A helper function to send a PUT or PATCH request to a team."
    ...     headers = {"Content-type": "application/json"}
    ...     return service(team, method, json.dumps(representation), headers)
    ...

    >>> print(
    ...     modify_team(
    ...         "/~my-new-team",
    ...         {"visibility": "Private"},
    ...         "PATCH",
    ...         comm_webservice,
    ...     )
    ... )
    HTTP/1.1 209 Content Returned
    ...
    Content-Type: application/json
    ...
    <BLANKLINE>
    {...}

    >>> team = webservice.get("/~my-new-team").jsonBody()
    >>> print(team["visibility"])
    Private

As an admin, Salgado can also change a team's visibility.

    >>> print(
    ...     user_webservice.named_post(
    ...         "/people",
    ...         "newTeam",
    ...         {},
    ...         name="my-new-team-2",
    ...         display_name="My New Team 2",
    ...     )
    ... )
    HTTP/1.1 201 Created
    ...
    Location: http://.../~my-new-team-2
    ...
    >>> team = user_webservice.get("/~my-new-team-2").jsonBody()
    >>> print(team["self_link"])
    http://api.launchpad.test/.../~my-new-team-2
    >>> print(team["visibility"])
    Public

    >>> print(
    ...     modify_team(
    ...         "/~my-new-team-2",
    ...         {"visibility": "Private"},
    ...         "PATCH",
    ...         webservice,
    ...     )
    ... )
    HTTP/1.1 209 Content Returned
    ...
    Content-Type: application/json
    ...
    <BLANKLINE>
    {...}

    >>> team = webservice.get("/~my-new-team-2").jsonBody()
    >>> print(team["visibility"])
    Private

An unprivileged user is not able to change the visibility.

    >>> print(
    ...     user_webservice.named_post(
    ...         "/people",
    ...         "newTeam",
    ...         {},
    ...         name="my-new-team-3",
    ...         display_name="My New Team 3",
    ...     )
    ... )
    HTTP/1.1 201 Created
    ...
    Location: http://.../~my-new-team-3
    ...
    >>> team = user_webservice.get("/~my-new-team-3").jsonBody()
    >>> print(team["self_link"])
    http://api.launchpad.test/.../~my-new-team-3
    >>> print(team["visibility"])
    Public

    >>> print(
    ...     modify_team(
    ...         "/~my-new-team-3",
    ...         {"visibility": "Private"},
    ...         "PATCH",
    ...         user_webservice,
    ...     )
    ... )
    HTTP/1.1 403 Forbidden
    ...
