Team Membership/Participation
=============================

When a person joins a team, we store the relationship in the TeamMembership
table. In this table we store the membership status, the join date and the
expiry date. TeamMembership stores only direct members. However, when a
member of a team is in fact another team (in the case of Team Y is a member
of Team X), the membership is transitive (members of Team Y are also a
member of team X). For this reason the TeamParticipation table exists: it
represents all the people who are /effective members/ of the team.

First of all, create some teams:

    >>> import pytz
    >>> from datetime import datetime, timedelta
    >>> from lp.registry.interfaces.person import (
    ...     TeamMembershipRenewalPolicy,
    ...     TeamMembershipPolicy,
    ...     )
    >>> from lp.registry.interfaces.teammembership import TeamMembershipStatus

XXX: This doctest needs a lot of cleanups!
-- Guilherme Salgado, 2006-12-15

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> personset = getUtility(IPersonSet)
    >>> jblack = personset.getByName('jblack')
    >>> nopriv = personset.getByName('no-priv')
    >>> jdub = personset.getByName('jdub')
    >>> reviewer = nopriv
    >>> t1 = personset.newTeam(
    ...     jblack, 't1', 't1',
    ...     membership_policy=TeamMembershipPolicy.OPEN)
    >>> t2 = personset.newTeam(
    ...     nopriv, 't2', 't2',
    ...     membership_policy=TeamMembershipPolicy.OPEN)
    >>> t3 = personset.newTeam(
    ...     jdub, 't3', 't3',
    ...     membership_policy=TeamMembershipPolicy.MODERATED)
    >>> t4 = personset.newTeam(
    ...     nopriv, 't4', 't4',
    ...     membership_policy=TeamMembershipPolicy.OPEN)
    >>> t5 = personset.newTeam(
    ...     nopriv, 't5', 't5',
    ...     membership_policy=TeamMembershipPolicy.OPEN)
    >>> t6 = personset.newTeam(
    ...     jdub, 't6', 't6',
    ...     membership_policy=TeamMembershipPolicy.MODERATED)

    # Make sure the teams have predictable (and different) creation dates as
    # some of our tests depend on that.
    >>> from zope.security.proxy import removeSecurityProxy
    >>> oldest = t1.datecreated
    >>> removeSecurityProxy(t2).datecreated = oldest + timedelta(hours=1)
    >>> removeSecurityProxy(t3).datecreated = oldest + timedelta(hours=2)
    >>> removeSecurityProxy(t4).datecreated = oldest + timedelta(hours=3)
    >>> removeSecurityProxy(t5).datecreated = oldest + timedelta(hours=4)
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> flush_database_updates()


Adding new members
------------------

One way of adding new members to a team is by having the user themselves
join the team they want.

    >>> salgado = personset.getByName('salgado')
    >>> ignored = login_person(salgado)
    >>> salgado.join(t3)
    >>> salgado.join(t4)

Note that since t3 is a MODERATED team, Salgado is not really added as a
member of that team --somebody has to approve his membership first:

    >>> for m in t4.allmembers:
    ...     print(m.displayname)
    Guilherme Salgado
    No Privileges Person

    >>> for m in t3.allmembers:
    ...     print(m.displayname)
    Jeff Waugh
    >>> ignored = login_person(t3.teamowner)
    >>> t3.setMembershipData(salgado, TeamMembershipStatus.APPROVED, reviewer)
    >>> flush_database_updates()
    >>> for m in t3.allmembers:
    ...     print(m.displayname)
    Guilherme Salgado
    Jeff Waugh

The join() method is not allowed for teams whose membership policy is
RESTRICTED. And it'll be a no-op in case the user has already joined the
given team.

    >>> launchpad = personset.getByName('launchpad')
    >>> launchpad.membership_policy == TeamMembershipPolicy.RESTRICTED
    True
    >>> ignored = login_person(salgado)
    >>> salgado.join(launchpad)
    Traceback (most recent call last):
    ...
    lp.registry.errors.JoinNotAllowed: This is a restricted team

    >>> salgado.join(t3)
    >>> salgado in t3.activemembers
    True
    >>> salgado.join(t4)
    >>> salgado in t4.activemembers
    True

Team admins can make any of their teams join other teams as well.
Just like for people, if the team is MODERATED, the membership will
be PENDING, whereas for OPEN teams the membership will be automatically
approved.  Note, though, that in the case of teams we need to pass a
requester to the join() method.

    >>> ubuntu_team = personset.getByName('ubuntu-team')
    >>> ignored = login_person(ubuntu_team.teamowner)
    >>> ubuntu_team.join(t3, ubuntu_team.teamowner)
    >>> t3.membership_policy
    <DBItem TeamMembershipPolicy.MODERATED...
    >>> ubuntu_team in t3.proposedmembers
    True

    >>> t2.membership_policy
    <DBItem TeamMembershipPolicy.OPEN...
    >>> ubuntu_team.join(t2, ubuntu_team.teamowner)
    >>> ubuntu_team in t2.activemembers
    True

    # Clean things up to not upset the other tests.
    >>> ignored = login_person(t2.teamowner)
    >>> t2.setMembershipData(
    ...     ubuntu_team, TeamMembershipStatus.DEACTIVATED, t2.teamowner)
    >>> ubuntu_team in t2.activemembers
    False
    >>> for m in t2.allmembers:
    ...     print(m.displayname)
    No Privileges Person
    >>> login(ANONYMOUS)

Another API for adding members is ITeam.addMember(), which ensures the given
person has a membership entry for that team, regardless of whether the person
was already an active/inactive member or has never been a member before.

Only the team owner or a launchpad admin can call the addMember method.
Other users must use the join method if they are going to add themselves
to a team.

    >>> mark = personset.getByName('mark')
    >>> t3.addMember(salgado, reviewer=mark,
    ...     status=TeamMembershipStatus.ADMIN)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    # Log in as the team owner.
    >>> ignored = login_person(t3.teamowner)

If the member was added (i.e. they weren't already a member of the team),
addMember returns a tuple with True plus the new membership status.

    >>> t3.addMember(
    ...     salgado, reviewer=mark, status=TeamMembershipStatus.ADMIN)
    (True, <DBItem TeamMembershipStatus.ADMIN...)
    >>> from lp.registry.interfaces.teammembership import ITeamMembershipSet
    >>> membershipset = getUtility(ITeamMembershipSet)
    >>> flush_database_updates()
    >>> membership = membershipset.getByPersonAndTeam(salgado, t3)
    >>> membership.last_changed_by == mark
    True
    >>> membership.status == TeamMembershipStatus.ADMIN
    True
    >>> salgado in t3.activemembers
    True

addMember returns (True, PROPOSED) also when the member is added as a
proposed member.

    >>> marilize = personset.getByName('marilize')
    >>> t3.addMember(
    ...     marilize, reviewer=mark, status=TeamMembershipStatus.PROPOSED)
    (True, <DBItem TeamMembershipStatus.PROPOSED...)
    >>> flush_database_updates()
    >>> marilize in t3.activemembers
    False

If addMember is called with a person that is already a member, it
returns a tuple with False and the current status of the membership.

    >>> t3.addMember(
    ...     salgado, reviewer=mark, status=TeamMembershipStatus.ADMIN)
    (False, <DBItem TeamMembershipStatus.ADMIN...)
    >>> t3.addMember(
    ...     marilize, reviewer=mark, status=TeamMembershipStatus.PROPOSED)
    (False, <DBItem TeamMembershipStatus.PROPOSED...)

As expected, the membership object implements ITeamMembership.

    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.teammembership import ITeamMembership
    >>> verifyObject(ITeamMembership, membership)
    True

Note that, by default, the ITeam.addMember() API works slightly different
when the added member is a team. In that case the team will actually be
invited to be a member and one of the team's admins will have to accept the
invitation before the team is made a member.

    >>> ignored = login_person(t1.teamowner)

    # If the reviewer were also an admin of the team being added,
    # the status would go to APPROVED instead of INVITED.
    >>> t2.teamowner != t1.teamowner
    True
    >>> t1.addMember(t2, reviewer=t1.teamowner)
    (True, <DBItem TeamMembershipStatus.INVITED...)
    >>> membership = membershipset.getByPersonAndTeam(t2, t1)
    >>> membership.status == TeamMembershipStatus.INVITED
    True
    >>> for m in t1.allmembers:
    ...     print(m.displayname)
    James Blackwell

Once one of the t2 admins approve the membership, t2 is shown as a member
of t1 and the owner of t2 is an indirect member.

    >>> ignored = login_person(t2.teamowner)
    >>> t2.acceptInvitationToBeMemberOf(t1, comment='something')
    >>> for m in t1.activemembers:
    ...     print(m.displayname)
    James Blackwell
    t2
    >>> for m in t1.allmembers:
    ...     print(m.displayname)
    James Blackwell
    No Privileges Person
    t2

A team admin can also decline an invitation made to their team.

    >>> t2.addMember(t3, reviewer=mark)
    (True, <DBItem TeamMembershipStatus.INVITED...)
    >>> ignored = login_person(t3.teamowner)
    >>> t3.declineInvitationToBeMemberOf(t2, comment='something')
    >>> membership = membershipset.getByPersonAndTeam(t3, t2)
    >>> membership.status == TeamMembershipStatus.INVITATION_DECLINED
    True

In some cases it's necessary to bypass the invitation workflow and directly
add teams as members of other teams. We can do that by passing an extra
force_team_add=True to addMember(). We'll use that to add t3 as a member of
t2, thus making all t3 members be considered members of t2 as well.

    >>> ignored = login_person(t2.teamowner)

    # If the reviewer is also an admin of the team being added,
    # force_team_add is unnecessary, and we can't prove that that
    # argument works.
    >>> t3.teamowner != t2.teamowner
    True
    >>> t2.addMember(t3, reviewer=t2.teamowner, force_team_add=True)
    (True, <DBItem TeamMembershipStatus.APPROVED...)
    >>> for m in t2.allmembers:
    ...     print(m.displayname)
    Guilherme Salgado
    Jeff Waugh
    No Privileges Person
    t3

And members of t1 as well, since t2 is a member of t1.

    >>> for m in t1.allmembers:
    ...     print(m.displayname)
    Guilherme Salgado
    James Blackwell
    Jeff Waugh
    No Privileges Person
    t2
    t3


Passing in force_team_add=True is not necessary if the reviewer is the
admin of the team being added.

    >>> ignored = login_person(t3.teamowner)
    >>> t6.addMember(t3, reviewer=t3.teamowner)
    (True, <DBItem TeamMembershipStatus.APPROVED...)
    >>> for m in t6.allmembers:
    ...     print(m.displayname)
    Guilherme Salgado
    Jeff Waugh
    t3

Can we add t2 as a member of t3? No, we prevent this kind of loop, and users
can't do this because our vocabularies won't allow members that would cause
loops.

    >>> foobar = personset.getByEmail('foo.bar@canonical.com')
    >>> ignored = login_person(foobar)
    >>> t3.addMember(t2, reviewer)
    Traceback (most recent call last):
    ...
    AssertionError: Team 't3' is a member of 't2'. As a consequence, 't2'
    can't be added as a member of 't3'

Adding t2 as a member of t5 will add all t2 members as t5 members too.

    >>> t5.addMember(t2, reviewer, force_team_add=True)
    (True, <DBItem TeamMembershipStatus.APPROVED...)
    >>> for m in t5.allmembers:
    ...     print(m.displayname)
    Guilherme Salgado
    Jeff Waugh
    No Privileges Person
    t2
    t3

Adding t5 and t1 as members of t4 will add all t5 and t1 members as t4
members too.

    >>> t4.addMember(t5, reviewer, force_team_add=True)
    (True, <DBItem TeamMembershipStatus.APPROVED...)
    >>> t4.addMember(t1, reviewer, force_team_add=True)
    (True, <DBItem TeamMembershipStatus.APPROVED...)
    >>> for m in t4.allmembers:
    ...     print(m.displayname)
    Guilherme Salgado
    James Blackwell
    Jeff Waugh
    No Privileges Person
    t1
    t2
    t3
    t5

    >>> flush_database_updates()

After adding all this mess, this is what we have:

(This table doesn't include the team owner (Foo Bar), but since they're the
owner they're also a direct member of all teams)
=============================================================
||  Team      ||  Direct Members   ||  Indirect Members    ||
=============================================================
||   T1       ||  T2               ||  T3, Salgado         ||
||   T2       ||  T3               ||  Salgado             ||
||   T3       ||  Salgado          ||                      ||
||   T4       ||  T5, T1, Salgado  ||  T2, T3              ||
||   T5       ||  T2               ||  T3, Salgado         ||


We can use IPerson.findPathToTeam() to check some of the relationships drawn
above, either from a person to a given team ...

    >>> for team in salgado.findPathToTeam(t1):
    ...     print(team.name)
    t3
    t2
    t1
    >>> for team in salgado.findPathToTeam(t5):
    ...     print(team.name)
    t3
    t2
    t5
    >>> for team in salgado.findPathToTeam(t3):
    ...     print(team.name)
    t3

... or from a team to another one:

    >>> for team in t3.findPathToTeam(t4):
    ...     print(team.name)
    t2
    t1
    t4

t2 can't use its leave() method to leave t5 because it's a team and teams
take no actions. One of t5 administrators have to go and remove t2 from t5
if t2 shouldn't be a member of t5 anymore.

    >>> ignored = login_person(t5.teamowner)
    >>> t5.setMembershipData(t2, TeamMembershipStatus.DEACTIVATED, reviewer)

Removing t2 from t5 will have implications in all teams that have t5 as a
(direct or indirect) member.

t5 had only one member and two other indirect members. Now that t2 is not its
member anymore, it doesn't have any members apart from its owner.

    >>> for m in t5.allmembers:
    ...     print(m.displayname)
    No Privileges Person

Removing t2 from t5 won't remove it from t4, because t2 is also a member of
t1, which is a member of t4.

    >>> for m in t4.allmembers:
    ...     print(m.displayname)
    Guilherme Salgado
    James Blackwell
    Jeff Waugh
    No Privileges Person
    t1
    t2
    t3
    t5

Nothing changes in t1, because t5 wasn't one of its members.

    >>> for m in t1.allmembers:
    ...     print(m.displayname)
    Guilherme Salgado
    James Blackwell
    Jeff Waugh
    No Privileges Person
    t2
    t3

If 'Guilherme Salgado' decides to leave t3, he'll also be removed from t1
and t2, but not from t4, because he's a direct member of t4.

    >>> ignored = login_person(salgado)
    >>> salgado.leave(t3)
    >>> salgado in t1.allmembers
    False
    >>> salgado in t2.allmembers
    False
    >>> salgado in t4.allmembers
    True


This is what we have now, after removing t2 from t5 and Salgado from t3.

(This table doesn't include the team owner (Foo Bar), but since they're the
owner they're also a direct member of all teams)
=============================================================
||  Team      ||  Members          ||  Indirect Members    ||
=============================================================
||   T1       ||  T2               ||  T3                  ||
||   T2       ||  T3               ||                      ||
||   T3       ||                   ||                      ||
||   T4       ||  T5, T1, Salgado  ||  T2, T3              ||
||   T5       ||                   ||                      ||


Now, if I add a new member to t3, will it be added to t2, t1 and t4 as well?
Let's see...

    >>> cprov = getUtility(IPersonSet).getByName('cprov')
    >>> t3.addMember(cprov, reviewer)
    (True, <DBItem TeamMembershipStatus.APPROVED...)
    >>> [m.displayname for m in t3.allmembers]
    [...'Celso Providelo'...

    >>> [m.displayname for m in t2.allmembers]
    [...'Celso Providelo'...

    >>> [m.displayname for m in t1.allmembers]
    [...'Celso Providelo'...

    >>> [m.displayname for m in t4.allmembers]
    [...'Celso Providelo'...


It's important to note that even if the owner leaves the team, which
removes their membership, they will still be the team's owner and retain
their rights over it. This ensures we'll never have teams which can't be
managed. This does not imply that the owner will be a member of the team.

    >>> ignored = login_person(t5.teamowner)
    >>> t5.teamowner.leave(t5)
    >>> flush_database_updates()
    >>> [m.displayname for m in t5.allmembers]
    []
    >>> t5.teamowner.inTeam(t5)
    False

The team owner can make themselves a member again even if the team is
restricted:

    >>> t5.teamowner.join(t5, requester=t5.teamowner)
    >>> flush_database_updates()
    >>> t5.teamowner in t5.allmembers
    True
    >>> t5.teamowner.inTeam(t5)
    True

And escalate their privileges back to administrator:

    >>> membership = membershipset.getByPersonAndTeam(t5.teamowner, t5)
    >>> membership.setStatus(TeamMembershipStatus.ADMIN, t5.teamowner)
    True

Changing membership data
------------------------

The only bits of a TeamMembership that can be changed are its status, expiry
date, reviewer[comment] and the date the user joined. From these ones, the
most interesting ones are the status and expiry date, which can only be set
through a specific API (setStatus() and setExpirationDate()) protected with
the launchpad.Edit permission. Also, since we don't want team admins to change
the expiry date of their own memberships, the setExpirationDate() method does
an extra check to ensure that doesn't happen.

    # Foo Bar is a launchpad admin, but even so they can't change a
    # membership's status/expiry-date by hand.
    >>> ignored = login_person(foobar)
    >>> membership = foobar.team_memberships[0]
    >>> membership.status = None
    Traceback (most recent call last):
    ...
    zope.security.interfaces.ForbiddenAttribute: ...

    >>> membership.dateexpires = None
    Traceback (most recent call last):
    ...
    zope.security.interfaces.ForbiddenAttribute: ...

Foo Bar asked to join Warty Security Team on 2006-01-26 and they've been doing
good work, so we'll approve their membership.

    >>> warty_team = getUtility(IPersonSet).getByName('name20')
    >>> membership = membershipset.getByPersonAndTeam(foobar, warty_team)
    >>> print(membership.status.title)
    Proposed
    >>> print(membership.date_created.strftime("%Y-%m-%d"))
    2006-01-26
    >>> print(membership.datejoined)
    None

When we approve their membership, the datejoined will contain the date that it
was approved. It returns True to indicate that the status was changed.

    >>> membership.setStatus(TeamMembershipStatus.APPROVED, foobar)
    True
    >>> print(membership.status.title)
    Approved
    >>> utc_now = datetime.now(pytz.timezone('UTC'))
    >>> membership.datejoined.date() == utc_now.date()
    True

If setStatus is called again with the same status, it returns False,
to indicate that the status didn't change.

    >>> membership.setStatus(TeamMembershipStatus.APPROVED, foobar)
    False

Other status updates won't change datejoined, regardless of the status.
That's because datejoined stores the date in which the membership was first
made active.

    >>> buildd_admins = getUtility(IPersonSet).getByName(
    ...     'launchpad-buildd-admins')
    >>> foobar_on_buildd = membershipset.getByPersonAndTeam(
    ...     foobar, buildd_admins)
    >>> print(foobar_on_buildd.status.title)
    Administrator
    >>> foobar_on_buildd.datejoined <= utc_now
    True

    >>> foobar_on_buildd.setStatus(
    ...     TeamMembershipStatus.DEACTIVATED, foobar)
    True
    >>> print(foobar_on_buildd.status.title)
    Deactivated
    >>> foobar_on_buildd.datejoined <= utc_now
    True

    >>> foobar_on_buildd.setStatus(
    ...     TeamMembershipStatus.APPROVED, foobar)
    True
    >>> print(foobar_on_buildd.status.title)
    Approved
    >>> foobar_on_buildd.datejoined <= utc_now
    True

When changing the expiry date we need to provide a date in the future and,
as mentioned above, the change can't be done by a team admin to their own
membership.

We're still logged in as Foo Bar, which is a launchpad admin and thus
can change any membership's expiry date (even their own), as long as
the new expiry date is not in the past.

    >>> foobar == foobar_on_buildd.team.teamowner
    True
    >>> foobar_on_buildd.canChangeExpirationDate(foobar)
    True
    >>> one_day_ago = datetime.now(pytz.timezone('UTC')) - timedelta(days=1)
    >>> tomorrow = datetime.now(pytz.timezone('UTC')) + timedelta(days=1)
    >>> foobar_on_buildd.setExpirationDate(one_day_ago, foobar)
    Traceback (most recent call last):
    ...
    AssertionError: ...
    >>> foobar_on_buildd.setExpirationDate(tomorrow, foobar)

Team owners and admins can also renew any memberships of the team they
own or administer.

    >>> landscape = getUtility(IPersonSet).getByName(
    ...     'landscape-developers')
    >>> sampleperson = getUtility(IPersonSet).getByName(
    ...     'name12')
    >>> sampleperson_on_landscape = membershipset.getByPersonAndTeam(
    ...     sampleperson, landscape)
    >>> print(landscape.teamowner.name)
    name12
    >>> sampleperson_on_landscape.canChangeExpirationDate(sampleperson)
    True
    >>> sampleperson_on_landscape.setExpirationDate(tomorrow, sampleperson)

    >>> cprov_on_buildd = membershipset.getByPersonAndTeam(
    ...     cprov, buildd_admins)
    >>> print(buildd_admins.teamowner.name)
    name16
    >>> print(cprov_on_buildd.status.title)
    Administrator
    >>> foobar_on_buildd.canChangeExpirationDate(cprov)
    True
    >>> foobar_on_buildd.setExpirationDate(tomorrow, cprov)


Flagging expired memberships
----------------------------

The expired memberships are flagged by a cronscript that runs daily. This
script simply flags all active memberships which reached their expiry date as
expired.

To find out which memberships are already expired, we use
TeamMembershipSet.getMembershipsToExpire(). As you can see, we don't have any
membership to expire right now.

    >>> [(membership.person.name, membership.team.name)
    ...  for membership in membershipset.getMembershipsToExpire()]
    []

Let's change the expiry date of an active membership, so we have something
that should be expired. Since we can't set an expiry date in the past for a
membership using setExpirationDate(), we'll have to cheat and access the
dateexpires attribute directly.

    >>> foobar_on_admins = membershipset.getByPersonAndTeam(
    ...     personset.getByName('name16'), personset.getByName('admins'))
    >>> foobar_on_admins.dateexpires is None
    True
    >>> foobar_on_admins.status.title
    'Administrator'
    >>> login('foo.bar@canonical.com')
    >>> removeSecurityProxy(foobar_on_admins).dateexpires = one_day_ago
    >>> flush_database_updates()

    >>> for membership in membershipset.getMembershipsToExpire():
    ...     print('%s: %s' % (membership.person.name, membership.team.name))
    name16: admins

And here we change the expiry date of a membership that's already
deactivated, so it should not be flagged as expired.

    >>> sp_on_ubuntu_translators = membershipset.getByPersonAndTeam(
    ...     personset.getByName('name12'),
    ...     personset.getByName('ubuntu-translators'))
    >>> sp_on_ubuntu_translators.dateexpires is None
    True
    >>> sp_on_ubuntu_translators.status.title
    'Deactivated'
    >>> removeSecurityProxy(
    ...     sp_on_ubuntu_translators).dateexpires = one_day_ago
    >>> flush_database_updates()

    >>> for membership in membershipset.getMembershipsToExpire():
    ...     print('%s: %s' % (membership.person.name, membership.team.name))
    name16: admins

The getMembershipsToExpire() method also accepts an optional 'when' argument.
When that argument is provided, we get the memberships that are supposed to
expire on that date or before.

    >>> mark_on_ubuntu_team = membershipset.getByPersonAndTeam(
    ...     personset.getByName('mark'),
    ...     personset.getByName('ubuntu-team'))
    >>> mark_on_ubuntu_team.dateexpires is not None
    True
    >>> mark_on_ubuntu_team.status.title
    'Administrator'

    >>> when = mark_on_ubuntu_team.dateexpires + timedelta(days=1)
    >>> for membership in membershipset.getMembershipsToExpire(when=when):
    ...     print('%s: %s' % (membership.person.name, membership.team.name))
    mark: ubuntu-team
    name16: admins
    ubuntu-team: guadamen
    name16: launchpad-buildd-admins
    name12: landscape-developers


Renewing team memberships
-------------------------

A team membership can be renewed before it has been expired by either
changing its dateexpires (which can be done only by admins of the
membership's team) or by using IPerson.renewTeamMembership, which is
accessible only to the membership's member a few days before it expires.
Also, for a member to renew their own membership, it's necessary that the
team's renewal policy is set to ONDEMAND and that the membership is
still active.

    >>> karl = personset.getByName('karl')
    >>> mirror_admins = personset.getByName('ubuntu-mirror-admins')
    >>> karl_on_mirroradmins = membershipset.getByPersonAndTeam(
    ...     karl, mirror_admins)
    >>> tomorrow = datetime.now(pytz.timezone('UTC')) + timedelta(days=1)
    >>> print(karl_on_mirroradmins.status.title)
    Approved
    >>> print(karl_on_mirroradmins.dateexpires)
    None

The member themselves can't change the expiration date of their membership.

    >>> ignored = login_person(karl)
    >>> karl_on_mirroradmins.setExpirationDate(tomorrow, karl)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Only a team admin can.

    >>> ignored = login_person(mirror_admins.teamowner)
    >>> karl_on_mirroradmins.setExpirationDate(
    ...     tomorrow, mirror_admins.teamowner)
    >>> karl_on_mirroradmins.dateexpires == tomorrow
    True

If the team's renewal policy is ONDEMAND, the membership can be renewed
by the member themselves. (That is only true because this membership is
active and set to expire tomorrow).

    >>> print(karl_on_mirroradmins.team.renewal_policy.name)
    NONE
    >>> karl_on_mirroradmins.canBeRenewedByMember()
    False
    >>> ondemand = TeamMembershipRenewalPolicy.ONDEMAND
    >>> karl_on_mirroradmins.team.renewal_policy = ondemand

    # When a user renews their own membership, we use the team's default
    # renewal period, so we must specify that for the mirror admins
    # team.
    >>> mirror_admins.defaultrenewalperiod = 365
    >>> flush_database_updates()

    >>> karl_on_mirroradmins.canBeRenewedByMember()
    True

    >>> ignored = login_person(karl)
    >>> karl.renewTeamMembership(mirror_admins)


Now the membership can't be renewed by the member as it's not going to
expire soon.

    >>> karl_on_mirroradmins.dateexpires == tomorrow + timedelta(days=365)
    True
    >>> karl_on_mirroradmins.canBeRenewedByMember()
    False
    >>> print(karl_on_mirroradmins.status.title)
    Approved


Querying team memberships
-------------------------

You can check a person's direct memberships by using team_memberships:

    >>> for membership in salgado.team_memberships:
    ...     print('%s: %s' % (membership.team.name, membership.status.title))
    hwdb-team: Approved
    landscape-developers: Approved
    admins: Administrator
    t4: Approved

And you can check which direct memberships a team has by using
member_memberships:

    >>> for membership in t3.member_memberships:
    ...     print('%s: %s' %
    ...           (membership.person.name, membership.status.title))
    cprov: Approved
    jdub: Administrator

A team has a number of other methods that return the people which are members
of it, all based on Person.getMembersByStatus:

    >>> for person in t3.approvedmembers:
    ...     print(person.unique_displayname)
    Celso Providelo (cprov)

(which is the same as saying

    >>> for person in t3.getMembersByStatus(TeamMembershipStatus.APPROVED):
    ...     print(person.unique_displayname)
    Celso Providelo (cprov)

except shorter)

We can also change the sort order of the results of getMembersByStatus.

    >>> ignored = login_person(cprov)
    >>> cprov.leave(t3)
    >>> flush_database_updates()

    >>> deactivated = TeamMembershipStatus.DEACTIVATED
    >>> for person in t3.getMembersByStatus(deactivated):
    ...     print(person.unique_displayname)
    Celso Providelo (cprov)
    Guilherme Salgado (salgado)

    >>> orderBy = '-TeamMembership.date_joined'
    >>> for person in t3.getMembersByStatus(deactivated, orderBy=orderBy):
    ...     print(person.unique_displayname)
    Celso Providelo (cprov)
    Guilherme Salgado (salgado)


Finding team administrators
---------------------------

Another convenient method is getDirectAdministrators(), which returns the
admin members plus the owner in case they are not one of the admin members.

    >>> for admin in t3.adminmembers:
    ...     print(admin.unique_displayname)
    Jeff Waugh (jdub)
    >>> list(t3.getDirectAdministrators()) == list(t3.adminmembers)
    True

    >>> from lp.testing import person_logged_in
    >>> owner = factory.makePerson()
    >>> adminless_team = factory.makeTeam(owner=owner)
    >>> with person_logged_in(owner):
    ...     owner.leave(adminless_team)
    >>> adminless_team.adminmembers.count() == 0
    True
    >>> list(adminless_team.getDirectAdministrators()) == [owner]
    True

Note that the team administrators can contain teams, so if you want to
check if a user is an admin of the team, you should use inTeam() to
check if the user is a member of these administrators. For example,
cprov isn't a direct administrator of the guadamen team, but he is
an indirect administrator by being a member of the Ubuntu team (which
is a direct administrator of the guadamen team):

    >>> guadamen_team = personset.getByName('guadamen')
    >>> for person in guadamen_team.getDirectAdministrators():
    ...     print(person.name)
    name16
    ubuntu-team

    >>> from lp.services.webapp.authorization import check_permission
    >>> ubuntu_team = personset.getByName('ubuntu-team')
    >>> cprov.inTeam(ubuntu_team)
    True
    >>> foobar in guadamen_team.getDirectAdministrators()
    True
    >>> cprov in guadamen_team.getDirectAdministrators()
    False
    >>> login('celso.providelo@canonical.com')
    >>> check_permission('launchpad.Edit', guadamen_team)
    True

There is also the getAdministratedTeams() method that returns all the
teams for which the person/team has admin rights.

    >>> cprov_team = factory.makeTeam(owner=cprov, name="cprov-team")
    >>> for team in cprov.getAdministratedTeams():
    ...     print(team.name)
    canonical-partner-dev
    cprov-team
    guadamen
    launchpad-buildd-admins

If a team is merged it will not show up in the set of administered teams.

    >>> from lp.registry.personmerge import merge_people
    >>> login('foo.bar@canonical.com')
    >>> membershipset.deactivateActiveMemberships(
    ...     cprov_team, "Merging", foobar)
    >>> merge_people(cprov_team, guadamen_team, cprov_team.teamowner)
    >>> for team in cprov.getAdministratedTeams():
    ...     print(team.name)
    canonical-partner-dev
    guadamen
    launchpad-buildd-admins


Querying a person for team participation
----------------------------------------

Team membership is direct; team participation is indirect, people being
participants of teams by virtue of being members of other teams which are in
turn members of these teams.

We can ask a person what teams they participate in. The
teams_participated_in attribute works recursively, listing all teams the
person is an active member of as well as teams those teams are an active
member of.

    >>> login('celso.providelo@canonical.com')
    >>> print('\n'.join(sorted(
    ...     team.name for team in salgado.teams_participated_in)))
    admins
    hwdb-team
    landscape-developers
    mailing-list-experts
    t4

Adding admins as a member of t1 will make Salgado a member of t1 as well.

    >>> admins = getUtility(IPersonSet).getByName('admins')
    >>> ignored = login_person(t1.teamowner)
    >>> t1.addMember(admins, reviewer=t1.teamowner, force_team_add=True)
    (True, <DBItem TeamMembershipStatus.APPROVED...)
    >>> flush_database_updates()
    >>> print('\n'.join(sorted(
    ...     team.name for team in salgado.teams_participated_in)))
    admins
    hwdb-team
    landscape-developers
    mailing-list-experts
    t1
    t4

On the other hand, making t3 a member of admins won't change anything
for Salgado.

    >>> ignored = login_person(foobar)
    >>> admins.addMember(t3, reviewer=admins.teamowner, force_team_add=True)
    (True, <DBItem TeamMembershipStatus.APPROVED...)
    >>> flush_database_updates()
    >>> print('\n'.join(sorted(
    ...     team.name for team in salgado.teams_participated_in)))
    admins
    hwdb-team
    landscape-developers
    mailing-list-experts
    t1
    t4
