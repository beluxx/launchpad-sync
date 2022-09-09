==================
Mailing list pages
==================

Most of the mailing list view tests unfortunately live as page tests
currently.  See lib/lp/registry/stories/mailinglists/*.rst


Requesting a mailing list
=========================

Both team owners and team administrators can request a mailing list.  Here,
Sample Person creates the team, thus becoming its owner.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet

    >>> person_set = getUtility(IPersonSet)
    >>> sample_person = person_set.getByEmail("test@canonical.com")
    >>> aardvarks = factory.makeTeam(
    ...     sample_person, "The Electric Aardvark Sausages", name="aardvarks"
    ... )

Sample Person can access the +mailinglist page.

    >>> from lp.services.webapp.authorization import check_permission

    >>> login("test@canonical.com")
    >>> view = create_initialized_view(aardvarks, "+mailinglist")
    >>> check_permission("launchpad.Moderate", view)
    True

No Privileges Person is added as a member of the Aardvarks.

    >>> no_priv = person_set.getByEmail("no-priv@canonical.com")
    >>> ignored = aardvarks.addMember(no_priv, sample_person)

But regular members can't access the +mailinglist page.

    >>> login("no-priv@canonical.com")
    >>> view = create_initialized_view(aardvarks, "+mailinglist")
    >>> check_permission("launchpad.Moderate", view)
    False

Sample Person trusts No Privileges Person so they make no-priv a team
administrator.

    >>> from lp.registry.interfaces.teammembership import (
    ...     ITeamMembershipSet,
    ...     TeamMembershipStatus,
    ... )

    >>> login("test@canonical.com")
    >>> team_membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
    ...     no_priv, aardvarks
    ... )
    >>> team_membership.status
    <DBItem TeamMembershipStatus.APPROVED...
    >>> ignored = team_membership.setStatus(
    ...     TeamMembershipStatus.ADMIN, sample_person
    ... )

Now No Privileges Person has permission to request mailing lists.

    >>> login("no-priv@canonical.com")
    >>> view = create_initialized_view(aardvarks, "+mailinglist")
    >>> check_permission("launchpad.Moderate", view)
    True


Purging lists
=============

A team mailing list can, under certain circumstances, be purged by a
Mailing List Expert or Launchpad administrator.  Purging is an assertion
that there are no data structures on the Mailman side that we care
about.  This is not enforced by Launchpad, and a purging a list invokes
no communication between the two systems.

    >>> team_one, list_one = factory.makeTeamAndMailingList(
    ...     "team-one", "no-priv"
    ... )

    >>> the_owner = team_one.teamowner

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> celebrities = getUtility(ILaunchpadCelebrities)
    >>> an_expert = list(celebrities.registry_experts.allmembers)[0]
    >>> an_admin = list(celebrities.admin.allmembers)[0]

    >>> def create_view(principal, form=None):
    ...     login_person(principal)
    ...     return create_initialized_view(
    ...         team_one, "+mailinglist", form=form
    ...     )
    ...

Nobody can purge an active mailing list, the team owner...

    >>> view = create_view(the_owner)
    >>> print(view.label)
    Mailing list configuration
    >>> view.list_can_be_purged
    False

...a mailing list expert...

    >>> view = create_view(an_expert)
    >>> view.list_can_be_purged
    False

...or a Launchpad administrator.

    >>> view = create_view(an_admin)
    >>> view.list_can_be_purged
    False

Even subverting the form will not trick Launchpad into purging the list.

    # Commit the current transaction, because when the view encounters an
    # error, it aborts the transaction, blowing away the setup state.
    >>> transaction.commit()

    >>> view = create_view(
    ...     an_admin, {"field.actions.purge_list": "Purge this Mailing List"}
    ... )
    >>> print("\n".join(view.errors))
    This list cannot be purged.

Now the team owner deactivates the mailing list.  When this completes
successfully, the mailing list will have been archived and removed on the
Mailman side.

    >>> from lp.registry.tests.mailinglists_helper import mailman

    >>> login("no-priv@canonical.com")
    >>> list_one.deactivate()
    >>> mailman.act()
    >>> transaction.commit()

The team owner can purge their list, as well as a Launchpad administrator and
a mailing list expert.

    >>> login(ANONYMOUS)
    >>> view = create_view(the_owner)
    >>> view.list_can_be_purged
    True

    >>> view = create_view(an_admin)
    >>> view.list_can_be_purged
    True

    >>> view = create_view(an_expert)
    >>> view.list_can_be_purged
    True


Like it never existed
=====================

A list which has been purged acts, for all intents and purposes, as if the
mailing list doesn't exist.  For example, once purged, it can be re-requested,
but not re-activated.

    >>> list_one.purge()
    >>> view = create_view(the_owner)
    >>> view.list_can_be_created
    True
    >>> view.list_can_be_deactivated
    False
    >>> view.list_can_be_reactivated
    False
    >>> view.list_application_can_be_cancelled
    False

Of course, while purged, the mailing list cannot be purged again.

    >>> view = create_view(an_expert)
    >>> view.list_can_be_purged
    False
