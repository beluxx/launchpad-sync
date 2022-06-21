=====================
Team membership views
=====================


Breadcrumbs
-----------

Team membership breadcrumbs uses the member's displayname to create
"<displayname>'s membership".

    >>> from lp.testing.menu import make_fake_request
    >>> from lp.registry.interfaces.teammembership import ITeamMembershipSet

    >>> team_owner = factory.makePerson(name='team-owner')
    >>> super_team = factory.makeTeam(name='us', owner=team_owner)
    >>> membership_set = getUtility(ITeamMembershipSet)
    >>> membership = membership_set.getByPersonAndTeam(
    ...     team_owner, super_team)
    >>> view = create_view(membership, '+index')

    >>> request = make_fake_request(
    ...     'http://launchpad.test/~us/+member/team-owner',
    ...     [super_team, membership, view])
    >>> hierarchy = create_initialized_view(
    ...     membership, '+hierarchy', request=request)
    >>> hierarchy.items
    [<TeamBreadcrumb ... text='\u201cUs\u201d team'>,
     <TeamMembershipBreadcrumb ... text='Team-owner's membership'>]


+member view
------------

The TeamMembershipEditView provides a label that described the membership
state of the IPerson.

    >>> view = create_view(membership, '+index')
    >>> print(view.label)
    Active member Team-owner


+invitations view
-----------------

When a team is invited to join another team, the TeamInvitationsView controls
the ~team/+invitations page.

    >>> team = factory.makeTeam(displayname='Bassists', name='bassists')
    >>> view = create_initialized_view(team, '+invitations')
    >>> print(view.label)
    Invitations for Bassists


+invitation/<team> view
-----------------------

The TeamInvitationView allows a team admin to accept or decline an invitation
to join another team. The invitation is a TeamMembership instance. The view
is applied during the stepto traversal--it is not a named view in ZCML.

    >>> from lp.registry.browser.team import TeamInvitationView

    >>> ignored = login_person(team_owner)
    >>> ignored = super_team.addMember(team, team_owner)
    >>> membership = membership_set.getByPersonAndTeam(team, super_team)
    >>> ignored = login_person(team.teamowner)
    >>> view = TeamInvitationView(membership, request)
    >>> print(view.label)
    Make Bassists a member of Us

The view provides page_title to create a breadcrumb that describes this
use the TeamMembership.

    >>> print(backslashreplace(view.page_title))
    \u201cUs\u201d team invitation
