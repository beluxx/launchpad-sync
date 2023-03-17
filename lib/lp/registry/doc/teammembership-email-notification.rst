Mail notifications for membership changes
=========================================

Whenever a membership status is changed, we should notify the team
admins and the member whose membership changed. There's a few cases
where we might want to notify only the team admins, but in most of the
cases we'll be sending two similar (but not identical) notifications:
one for all team admins and another for the member.

    >>> from operator import itemgetter

    >>> def setStatus(
    ...     membership, status, reviewer=None, comment=None, silent=False
    ... ):
    ...     """Set the status of the given membership.
    ...
    ...     Also sets the reviewer and comment, calling flush_database_updates
    ...     and transaction.commit after, to ensure the changes are flushed to
    ...     the database.
    ...     """
    ...     membership.setStatus(
    ...         status, reviewer, comment=comment, silent=silent
    ...     )
    ...     flush_database_updates()
    ...     transaction.commit()

    >>> from lp.services.mail import stub
    >>> from lp.testing.mail_helpers import (
    ...     pop_notifications,
    ...     print_distinct_emails,
    ...     run_mail_jobs,
    ... )

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import (
    ...     IPersonSet,
    ...     TeamMembershipRenewalPolicy,
    ...     TeamMembershipPolicy,
    ... )
    >>> from lp.registry.interfaces.teammembership import (
    ...     ITeamMembershipSet,
    ...     TeamMembershipStatus,
    ... )
    >>> personset = getUtility(IPersonSet)
    >>> membershipset = getUtility(ITeamMembershipSet)
    >>> mark = personset.getByName("mark")
    >>> kamion = personset.getByName("kamion")
    >>> sampleperson = personset.getByName("name12")
    >>> ubuntu_team = personset.getByName("ubuntu-team")
    >>> open_team = factory.makeTeam(
    ...     membership_policy=TeamMembershipPolicy.OPEN
    ... )
    >>> from lp.testing.sampledata import ADMIN_EMAIL
    >>> admin_person = personset.getByEmail(ADMIN_EMAIL)

In open teams joining and leaving the team generates no notifications.

    >>> ignored = login_person(admin_person)
    >>> base_mails = len(stub.test_emails)
    >>> new_person = factory.makePerson()
    >>> ignored = login_person(new_person)
    >>> new_person.join(open_team)
    >>> membership = membershipset.getByPersonAndTeam(new_person, open_team)
    >>> membership.status.title
    'Approved'

    >>> run_mail_jobs()
    >>> len(stub.test_emails) - base_mails
    0

    >>> new_person.leave(open_team)
    >>> run_mail_jobs()
    >>> len(stub.test_emails) - base_mails
    0

Now Robert Collins proposes himself as a member of the Ubuntu Team. This
generates a notification email only to Ubuntu Team administrators.

    >>> lifeless = personset.getByName("lifeless")
    >>> ignored = login_person(lifeless)
    >>> lifeless.join(ubuntu_team)
    >>> membership = membershipset.getByPersonAndTeam(lifeless, ubuntu_team)
    >>> membership.status.title
    'Proposed'

    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    5

    >>> print_distinct_emails(include_reply_to=True, decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>,
        Jeff Waugh <jeff.waugh@ubuntulinux.com>
    Reply-To: robertc@robertcollins.net
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-pending
    Subject: lifeless wants to join
    <BLANKLINE>
    Robert Collins (lifeless) wants to be a member of Ubuntu Team (ubuntu-
    team), but this is a moderated team, so that membership has to be
    approved.  You can approve, decline or leave it as proposed by following
    the link below.
    <BLANKLINE>
        http://launchpad.test/~ubuntu-team/+member/lifeless
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Mark Shuttleworth <mark@example.com>
    Reply-To: robertc@robertcollins.net
    X-Launchpad-Message-Rationale: Owner (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-pending
    Subject: lifeless wants to join
    ...
    You received this email because you are the owner of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------

Declining a proposed member should generate notifications for both the
member and each of the team's admins.

    # Need to be logged in as a team admin to be able to change memberships of
    # that team.

    >>> login("mark@example.com")
    >>> setStatus(membership, TeamMembershipStatus.DECLINED, reviewer=mark)

addMember() has queued up a job to send out the emails. We'll run the
job now.

    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    6

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>,
        Jeff Waugh <jeff.waugh@ubuntulinux.com>,
        Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-change
    Subject: lifeless declined by mark
    <BLANKLINE>
    The membership status of Robert Collins (lifeless) in the team Ubuntu
    Team (ubuntu-team) was changed by Mark Shuttleworth (mark) from
    Proposed to Declined.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Robert Collins <robertc@robertcollins.net>
    X-Launchpad-Message-Rationale: Member (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-change
    Subject: lifeless declined by mark
    <BLANKLINE>
    The status of your membership in the team Ubuntu Team (ubuntu-team) was
    changed by Mark Shuttleworth (mark) from Proposed to Declined.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are the affected member.
    <BLANKLINE>
    ----------------------------------------

The same goes for approving a proposed member.

    >>> daf = getUtility(IPersonSet).getByName("daf")
    >>> daf.join(ubuntu_team)
    >>> daf_membership = membershipset.getByPersonAndTeam(daf, ubuntu_team)
    >>> daf_membership.status.title
    'Proposed'

    # Remove notification of daf's membership pending approval from
    # stub.test_emails

    >>> run_mail_jobs()
    >>> _ = pop_notifications()

    >>> setStatus(
    ...     daf_membership,
    ...     TeamMembershipStatus.APPROVED,
    ...     reviewer=mark,
    ...     comment="This is a nice guy; I like him",
    ... )
    >>> run_mail_jobs()
    >>> stub.test_emails.sort(key=itemgetter(1))
    >>> len(stub.test_emails)
    6

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>,
        Jeff Waugh <jeff.waugh@ubuntulinux.com>,
        Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-change
    Subject: daf approved by mark
    <BLANKLINE>
    The membership status of Dafydd Harries (daf) in the team Ubuntu Team
    (ubuntu-team) was changed by Mark Shuttleworth (mark) from Proposed to
    Approved.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    Mark Shuttleworth said:
     This is a nice guy; I like him
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Dafydd Harries <daf@canonical.com>
    X-Launchpad-Message-Rationale: Member (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-change
    Subject: daf approved by mark
    <BLANKLINE>
    The status of your membership in the team Ubuntu Team (ubuntu-team) was
    changed by Mark Shuttleworth (mark) from Proposed to Approved.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    Mark Shuttleworth said:
     This is a nice guy; I like him
    -- 
    <BLANKLINE>
    You received this email because you are the affected member.
    <BLANKLINE>
    ----------------------------------------

The same for deactivating a membership.

    >>> setStatus(
    ...     daf_membership, TeamMembershipStatus.DEACTIVATED, reviewer=mark
    ... )
    >>> run_mail_jobs()
    >>> stub.test_emails.sort(key=itemgetter(1))
    >>> len(stub.test_emails)
    6

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>,
        Jeff Waugh <jeff.waugh@ubuntulinux.com>,
        Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-change
    Subject: daf deactivated by mark
    <BLANKLINE>
    The membership status of Dafydd Harries (daf) in the team Ubuntu Team
    (ubuntu-team) was changed by Mark Shuttleworth (mark) from Approved to
    Deactivated.
    <http://launchpad.test/~ubuntu-team>
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Dafydd Harries <daf@canonical.com>
    X-Launchpad-Message-Rationale: Member (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-change
    Subject: daf deactivated by mark
    <BLANKLINE>
    The status of your membership in the team Ubuntu Team (ubuntu-team) was
    changed by Mark Shuttleworth (mark) from Approved to Deactivated.
    <http://launchpad.test/~ubuntu-team>
    -- 
    <BLANKLINE>
    You received this email because you are the affected member.
    <BLANKLINE>
    ----------------------------------------

Team admins can propose their teams using the join() method as well, but
in that case we'll use the requester's (the person proposing the team as
the other's member) email address in the 'Reply-To' header of the
message sent.

    >>> admins = personset.getByName("admins")
    >>> admins.join(ubuntu_team, requester=mark)
    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    5

    >>> print_distinct_emails(include_reply_to=True, decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>,
        Jeff Waugh <jeff.waugh@ubuntulinux.com>
    Reply-To: mark@example.com
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-pending
    Subject: admins wants to join
    <BLANKLINE>
    Mark Shuttleworth (mark) wants to make Launchpad Administrators
    (admins) a member of Ubuntu Team (ubuntu-team), but this is a moderated
    team, so that membership has to be approved.  You can approve, decline
    or leave it as proposed by following the link below.
    <BLANKLINE>
        http://launchpad.test/~ubuntu-team/+member/admins
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Mark Shuttleworth <mark@example.com>
    Reply-To: mark@example.com
    X-Launchpad-Message-Rationale: Owner (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-pending
    Subject: admins wants to join
     ...
    You received this email because you are the owner of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------


Adding new members
------------------

When a person is added as a member of a team by one of that team's
administrators, an email is sent to all team administrators and to the
new member.

    >>> cprov = personset.getByName("cprov")
    >>> marilize = personset.getByName("marilize")
    >>> ignored = ubuntu_team.addMember(marilize, reviewer=cprov)
    >>> run_mail_jobs()

Now, the emails have been sent.

    >>> len(stub.test_emails)
    6

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Marilize Coetzee <marilize@hbd.com>
    X-Launchpad-Message-Rationale: Member (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-new
    Subject: You have been added to ubuntu-team
    <BLANKLINE>
    Celso Providelo (cprov) added you as a member of Ubuntu Team (ubuntu-
    team).
      <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are the new member.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>,
        Jeff Waugh <jeff.waugh@ubuntulinux.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-new
    Subject: marilize joined ubuntu-team
    <BLANKLINE>
    Marilize Coetzee (marilize) has been added as a member of Ubuntu Team
    (ubuntu-team) by Celso Providelo (cprov). Follow the link below for more
    details.
    <BLANKLINE>
        http://launchpad.test/~ubuntu-team/+member/marilize
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Owner (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-new
    Subject: marilize joined ubuntu-team
      ...
    You received this email because you are the owner of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------

By default, if the newly added member is actually a team, we'll only
send an invitation to the team's admins, telling them that the
membership will only be activated if they accept the invitation.

    >>> mirror_admins = personset.getByName("ubuntu-mirror-admins")
    >>> mirror_admins.getTeamAdminsEmailAddresses()
    ['mark@example.com']

    >>> ignored = ubuntu_team.addMember(mirror_admins, reviewer=cprov)
    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    1

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-mirror-admins)
    X-Launchpad-Notification-Type: team-membership-invitation
    Subject: Invitation for ubuntu-mirror-admins to join
    <BLANKLINE>
    Celso Providelo (cprov) has invited Mirror Administrators (ubuntu-
    mirror-admins) (which you are an administrator of) to join Ubuntu Team
    (ubuntu-team).
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    You can accept or decline this invitation on the following page:
    <BLANKLINE>
        http://launchpad.test/~ubuntu-mirror-admins/+invitation/ubuntu-team
    <BLANKLINE>
    Regards,
    The Launchpad team
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Mirror
    Administrators team.
    <BLANKLINE>
    ----------------------------------------

If one of the admins accept the invitation, then a notification is sent
to the team which just became a member and to the admins of the hosting
team.

    >>> comment = "Of course I want to be part of ubuntu!"
    >>> mirror_admins.acceptInvitationToBeMemberOf(ubuntu_team, comment)
    >>> flush_database_updates()
    >>> run_mail_jobs()

    >>> len(stub.test_emails)
    6

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>,
        Jeff Waugh <jeff.waugh@ubuntulinux.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-invitation-accepted
    Subject: Invitation to ubuntu-mirror-admins accepted by mark
    <BLANKLINE>
    Mark Shuttleworth (mark) has accepted the invitation to make Mirror
    Administrators (ubuntu-mirror-admins) a member of Ubuntu Team (ubuntu-
    team).
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    Mark Shuttleworth said:
     Of course I want to be part of ubuntu!
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Karl Tilbury <karl@canonical.com>,
        Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Member (ubuntu-team) @ubuntu-mirror-admins
    X-Launchpad-Notification-Type: team-membership-invitation-accepted
    Subject: Invitation to ubuntu-mirror-admins accepted by mark
    <BLANKLINE>
    Mark Shuttleworth (mark) has accepted the invitation to make Mirror
    Administrators (ubuntu-mirror-admins) a member of Ubuntu Team (ubuntu-
    team).
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    Mark Shuttleworth said:
     Of course I want to be part of ubuntu!
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because your team Mirror Administrators is the
    affected member.
    <BLANKLINE>
    ----------------------------------------

Similarly, a notification is sent if the invitation is declined.

    >>> landscape = personset.getByName("landscape-developers")
    >>> ignored = ubuntu_team.addMember(landscape, reviewer=cprov)

    # Reset stub.test_emails as we don't care about the notification triggered
    # by the addMember() call.

    >>> run_mail_jobs()
    >>> stub.test_emails = []

    >>> comment = "Landscape has nothing to do with ubuntu, unfortunately."
    >>> landscape.declineInvitationToBeMemberOf(ubuntu_team, comment)
    >>> flush_database_updates()
    >>> run_mail_jobs()

    >>> len(stub.test_emails)
    7

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>,
        Jeff Waugh <jeff.waugh@ubuntulinux.com>,
        Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-invitation-declined
    Subject: Invitation to landscape-developers declined by mark
    <BLANKLINE>
    Mark Shuttleworth (mark) has declined the invitation to make Landscape
    Developers (landscape-developers) a member of Ubuntu Team (ubuntu-team).
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    Mark Shuttleworth said:
     Landscape has nothing to do with ubuntu, unfortunately.
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Guilherme Salgado <guilherme.salgado@canonical.com>,
        Sample Person <test@canonical.com>
    X-Launchpad-Message-Rationale: Member (ubuntu-team) @landscape-developers
    X-Launchpad-Notification-Type: team-membership-invitation-declined
    Subject: Invitation to landscape-developers declined by mark
    <BLANKLINE>
    Mark Shuttleworth (mark) has declined the invitation to make Landscape
    Developers (landscape-developers) a member of Ubuntu Team (ubuntu-team).
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    Mark Shuttleworth said:
     Landscape has nothing to do with ubuntu, unfortunately.
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because your team Landscape Developers is the
    affected member.
    <BLANKLINE>
    ----------------------------------------

It's also possible to forcibly add a team as a member of another one, by
passing force_team_add=True to the addMember() method.

    >>> launchpad = personset.getByName("launchpad")
    >>> ignored = ubuntu_team.addMember(
    ...     launchpad, reviewer=cprov, force_team_add=True
    ... )
    >>> flush_database_updates()
    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    5

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Foo Bar <foo.bar@canonical.com>
    X-Launchpad-Message-Rationale: Member (ubuntu-team) @launchpad
    X-Launchpad-Notification-Type: team-membership-new
    Subject: launchpad joined ubuntu-team
     ...
    You received this email because your team Launchpad Developers is the
    new member.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Jeff Waugh <jeff.waugh@ubuntulinux.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-new
    Subject: launchpad joined ubuntu-team
    <BLANKLINE>
    Launchpad Developers (launchpad) has been added as a member of Ubuntu
    Team (ubuntu-team) by Celso Providelo (cprov). Follow the link below for
    more details.
    <BLANKLINE>
        http://launchpad.test/~ubuntu-team/+member/launchpad
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Owner (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-new
    Subject: launchpad joined ubuntu-team
     ...
    You received this email because you are the owner of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------


Membership expiration warnings
------------------------------

When we get close to the expiration date of a given membership, an
expiration warning is sent to the member, so that they can contact the
team's administrators (or renew it themselves if they have the necessary
permissions) in case they want to retain that membership. This is done by
the flag-expired-memberships cronscript, which uses
ITeamMembership.sendExpirationWarningEmail to do its job.

    >>> from datetime import datetime, timedelta, timezone
    >>> utc_now = datetime.now(timezone.utc)

In the case of the beta-testers team, the email is sent only to the
team's owner, who doesn't have the necessary rights to renew the
membership of their team, so they're instructed to contact one of the
ubuntu-team's admins.

    >>> beta_testers = personset.getByName("launchpad-beta-testers")
    >>> beta_testers_on_ubuntu_team = membershipset.getByPersonAndTeam(
    ...     beta_testers, ubuntu_team
    ... )
    >>> beta_testers_on_ubuntu_team.setExpirationDate(
    ...     utc_now + timedelta(days=9), mark
    ... )
    >>> flush_database_updates()
    >>> beta_testers_on_ubuntu_team.sendExpirationWarningEmail()
    >>> run_mail_jobs()
    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Launchpad Beta Testers Owner <beta-admin@launchpad.net>
    X-Launchpad-Message-Rationale: Member (ubuntu-team)
                                   @launchpad-beta-testers
    X-Launchpad-Notification-Type: team-membership-expiration-warning
    Subject: launchpad-beta-testers will expire soon from ubuntu-team
    <BLANKLINE>
    On ..., 9 days from now, the membership
    of Launchpad Beta Testers (launchpad-beta-testers) (which you are the
    owner of) in the Ubuntu Team (ubuntu-team) Launchpad team is due to
    expire.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    To prevent this membership from expiring, you should get in touch
    with one of the team's administrators:
    Alexander Limi (limi) <http://launchpad.test/~limi>
    Colin Watson (kamion) <http://launchpad.test/~kamion>
    Foo Bar (name16) <http://launchpad.test/~name16>
    Jeff Waugh (jdub) <http://launchpad.test/~jdub>
    Mark Shuttleworth (mark) <http://launchpad.test/~mark>
    <BLANKLINE>
    If the membership does expire, we'll send you one more message to let
    you know it's happened.
    <BLANKLINE>
    Thanks for using Launchpad!
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because your team Launchpad Beta Testers is the
    affected member.
    <BLANKLINE>
    ----------------------------------------

If the team's renewal policy is ONDEMAND, though, the member is invited
to renew their own membership.

    >>> ubuntu_team.renewal_policy = TeamMembershipRenewalPolicy.ONDEMAND
    >>> ubuntu_team.defaultrenewalperiod = 365
    >>> kamion_on_ubuntu_team = membershipset.getByPersonAndTeam(
    ...     kamion, ubuntu_team
    ... )
    >>> kamion_on_ubuntu_team.setExpirationDate(
    ...     utc_now + timedelta(days=9), mark
    ... )
    >>> flush_database_updates()
    >>> kamion_on_ubuntu_team.sendExpirationWarningEmail()
    >>> run_mail_jobs()
    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Colin Watson <colin.watson@ubuntulinux.com>
    X-Launchpad-Message-Rationale: Member (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-expiration-warning
    Subject: Your membership in ubuntu-team is about to expire
    <BLANKLINE>
    On ..., 9 days from now, your membership
    in the Ubuntu Team (ubuntu-team) Launchpad team
    is due to expire.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    If you want, you can renew this membership at
    <http://launchpad.test/~kamion/+expiringmembership/ubuntu-team>
    <BLANKLINE>
    If your membership does expire, we'll send you one more message to let
    you know it's happened.
    <BLANKLINE>
    Thanks for using Launchpad!
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are the affected member.
    <BLANKLINE>
    ----------------------------------------

    >>> beta_testers_on_ubuntu_team.sendExpirationWarningEmail()
    >>> run_mail_jobs()
    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Launchpad Beta Testers Owner <beta-admin@launchpad.net>
    X-Launchpad-Message-Rationale: Member (ubuntu-team)
                                   @launchpad-beta-testers
    X-Launchpad-Notification-Type: team-membership-expiration-warning
    Subject: launchpad-beta-testers will expire soon from ubuntu-team
    <BLANKLINE>
    On ..., 9 days from now, the membership
    of Launchpad Beta Testers (launchpad-beta-testers) (which you are the
    owner of) in the Ubuntu Team (ubuntu-team) Launchpad team is due to
    expire.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    If you want, you can renew this membership at
    <http://launchpad.test/~launchpad-beta-testers/+expiringmembership/...>
    <BLANKLINE>
    If the membership does expire, we'll send you one more message to let
    you know it's happened.
    <BLANKLINE>
    Thanks for using Launchpad!
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because your team Launchpad Beta Testers is the
    affected member.
    <BLANKLINE>
    ----------------------------------------

If the team's renewal policy is NONE but the member has the necessary
rights to change the expiration date of their own membership (i.e. by
being the team's owner), the notification they get will contain a link to
their membership page, where they can extend it.

    >>> landscape.renewal_policy = TeamMembershipRenewalPolicy.NONE
    >>> print(landscape.teamowner.preferredemail.email)
    test@canonical.com

    >>> sampleperson_on_landscape = membershipset.getByPersonAndTeam(
    ...     sampleperson, landscape
    ... )
    >>> sampleperson_on_landscape.setExpirationDate(
    ...     utc_now + timedelta(days=9), sampleperson
    ... )
    >>> flush_database_updates()
    >>> sampleperson_on_landscape.sendExpirationWarningEmail()
    >>> run_mail_jobs()
    >>> print_distinct_emails(decode=True)  # noqa
    From: Landscape Developers <noreply@launchpad.net>
    To: Sample Person <test@canonical.com>
    X-Launchpad-Message-Rationale: Member (landscape-developers)
    X-Launchpad-Notification-Type: team-membership-expiration-warning
    Subject: Your membership in landscape-developers is about to expire
    <BLANKLINE>
    On ..., 9 days from now, your membership
    in the Landscape Developers (landscape-developers) Launchpad team is due
    to expire.
    <http://launchpad.test/~landscape-developers>
    <BLANKLINE>
    To stay a member of this team you should extend your membership at
    <http://launchpad.test/~landscape-developers/+member/name12>
    <BLANKLINE>
    If your membership does expire, we'll send you one more message to let
    you know it's happened.
    <BLANKLINE>
    Thanks for using Launchpad!
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are the affected member.
    <BLANKLINE>
    ----------------------------------------


Memberships renewed by the members themselves
---------------------------------------------

Another possible renewal policy for teams is ONDEMAND, which means that
team members are invited to renew their membership once it gets close to
their expiration date. When a member renews their own membership, a
notification is sent to all team admins.

    >>> karl = personset.getByName("karl")
    >>> mirror_admins = personset.getByName("ubuntu-mirror-admins")
    >>> karl_on_mirroradmins = membershipset.getByPersonAndTeam(
    ...     karl, mirror_admins
    ... )
    >>> tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    >>> print(karl_on_mirroradmins.status.title)
    Approved

    >>> print(karl_on_mirroradmins.dateexpires)
    None

    >>> ignored = login_person(mirror_admins.teamowner)
    >>> karl_on_mirroradmins.setExpirationDate(
    ...     tomorrow, mirror_admins.teamowner
    ... )
    >>> ondemand = TeamMembershipRenewalPolicy.ONDEMAND
    >>> karl_on_mirroradmins.team.renewal_policy = ondemand
    >>> mirror_admins.defaultrenewalperiod = 365
    >>> flush_database_updates()

    >>> ignored = login_person(karl)
    >>> karl.renewTeamMembership(mirror_admins)
    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    1

    >>> print_distinct_emails(decode=True)  # noqa
    From: Mirror Administrators <noreply@launchpad.net>
    To: Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-mirror-admins)
    X-Launchpad-Notification-Type: team-membership-renewed
    Subject: karl extended their membership
    <BLANKLINE>
    Karl Tilbury (karl) renewed their own membership in the Mirror
    Administrators (ubuntu-mirror-admins) team until ...
    <http://launchpad.test/~ubuntu-mirror-admins>
    <BLANKLINE>
    Regards,
    The Launchpad team
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are an admin of the Mirror
    Administrators team.
    <BLANKLINE>
    ----------------------------------------


Some special cases
------------------

When creating a new team, the owner has their membership's status changed
from approved to admin, but they won't get a notification of that.

    >>> team = personset.newTeam(mark, "testteam", "Test")
    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    0

    # Other tests expect an empty stub.test_emails, but if this one above
    # fails, I don't want a non-empty stub.test_emails to cause the tests
    # below to fail too.

    >>> stub.test_emails = []

If cprov is made an administrator of ubuntu_team, he'll only get one
email notification.

    >>> cprov = personset.getByName("cprov")
    >>> cprov_membership = membershipset.getByPersonAndTeam(
    ...     cprov, ubuntu_team
    ... )
    >>> login("mark@example.com")
    >>> setStatus(cprov_membership, TeamMembershipStatus.ADMIN, reviewer=mark)
    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    6

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>,
        Jeff Waugh <jeff.waugh@ubuntulinux.com>,
        Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-change
    Subject: cprov made admin by mark
    <BLANKLINE>
    The membership status of Celso Providelo (cprov) in the team Ubuntu Team
    (ubuntu-team) was changed by Mark Shuttleworth (mark) from Approved to
    Administrator.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    -- 
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Celso Providelo <celso.providelo@canonical.com>
    X-Launchpad-Message-Rationale: Member (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-change
    Subject: cprov made admin by mark
    <BLANKLINE>
    The status of your membership in the team Ubuntu Team (ubuntu-team) was
    changed by Mark Shuttleworth (mark) from Approved to Administrator.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    -- 
    You received this email because you are the affected member.
    <BLANKLINE>
    ----------------------------------------

If a team admin changes their own membership, the notification sent will
clearly say that the change was performed by the user themselves, and it
will only be sent to the team administrators.

    >>> jdub = getUtility(IPersonSet).getByName("jdub")
    >>> jdub_membership = membershipset.getByPersonAndTeam(jdub, ubuntu_team)
    >>> setStatus(
    ...     jdub_membership, TeamMembershipStatus.APPROVED, reviewer=jdub
    ... )
    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    5

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Celso Providelo <celso.providelo@canonical.com>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>,
        Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-change
    Subject: Membership change: jdub in ubuntu-team
    <BLANKLINE>
    The membership status of Jeff Waugh (jdub) in the team Ubuntu Team
    (ubuntu-team) was changed by the user from Administrator to
    Approved.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    -- 
    You received this email because you are an admin of the Ubuntu Team team.
    <BLANKLINE>
    ----------------------------------------

Deactivating the membership of a team also generates notifications for
the team which had the membership deactivated and to the administrators
of the hosting team. Note that the notification sent to the team whose
membership was deactivated will not talk about "your membership" as it
wouldn't make sense to the members of the team reading it.

    >>> mirror_admins_membership = membershipset.getByPersonAndTeam(
    ...     mirror_admins, ubuntu_team
    ... )
    >>> setStatus(
    ...     mirror_admins_membership,
    ...     TeamMembershipStatus.DEACTIVATED,
    ...     reviewer=mark,
    ...     silent=False,
    ... )
    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    6

    >>> print_distinct_emails(decode=True)  # noqa
    From: Ubuntu Team <noreply@launchpad.net>
    To: Alexander Limi <limi@plone.org>,
        Celso Providelo <celso.providelo@canonical.com>,
        Colin Watson <colin.watson@ubuntulinux.com>,
        Foo Bar <foo.bar@canonical.com>
    X-Launchpad-Message-Rationale: Admin (ubuntu-team)
    X-Launchpad-Notification-Type: team-membership-change
    Subject: ubuntu-mirror-admins deactivated by mark
    <BLANKLINE>
    The membership status of Mirror Administrators (ubuntu-mirror-admins) in
    the team Ubuntu Team (ubuntu-team) was changed by Mark Shuttleworth
    (mark) from Approved to Deactivated.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    -- 
    You received this email because you are an admin of the Ubuntu Team team.
    ----------------------------------------
    From: Ubuntu Team <noreply@launchpad.net>
    To: Karl Tilbury <karl@canonical.com>,
        Mark Shuttleworth <mark@example.com>
    X-Launchpad-Message-Rationale: Member (ubuntu-team) @ubuntu-mirror-admins
    X-Launchpad-Notification-Type: team-membership-change
    Subject: ubuntu-mirror-admins deactivated by mark
    <BLANKLINE>
    The membership status of Mirror Administrators (ubuntu-mirror-admins) in
    the team Ubuntu Team (ubuntu-team) was changed by Mark Shuttleworth
    (mark) from Approved to Deactivated.
    <http://launchpad.test/~ubuntu-team>
    <BLANKLINE>
    -- 
    You received this email because your team Mirror Administrators is the
    affected member.
    ----------------------------------------

Deactivating memberships can also be done silently (no email
notifications sent) by Launchpad Administrators.

    >>> dumper = getUtility(IPersonSet).getByName("dumper")
    >>> hwdb_admins = personset.getByName("hwdb-team")
    >>> dumper_hwdb_membership = membershipset.getByPersonAndTeam(
    ...     dumper, hwdb_admins
    ... )
    >>> print(dumper_hwdb_membership.status.title)
    Approved

    >>> ignored = login_person(admin_person)
    >>> setStatus(
    ...     dumper_hwdb_membership,
    ...     TeamMembershipStatus.DEACTIVATED,
    ...     reviewer=admin_person,
    ...     silent=True,
    ... )
    >>> run_mail_jobs()
    >>> len(stub.test_emails)
    0

    >>> print(dumper_hwdb_membership.status.title)
    Deactivated

People who are not Launchpad Administrators, may not change other's
membership statues silently.

    >>> kamion = getUtility(IPersonSet).getByName("kamion")
    >>> stevea = getUtility(IPersonSet).getByName("stevea")
    >>> ignored = login_person(kamion)
    >>> ubuntu_team = personset.getByName("ubuntu-team")
    >>> kamion_ubuntu_team_membership = membershipset.getByPersonAndTeam(
    ...     kamion, ubuntu_team
    ... )
    >>> stevea_ubuntu_team_membership = membershipset.getByPersonAndTeam(
    ...     stevea, ubuntu_team
    ... )
    >>> print(kamion_ubuntu_team_membership.status.title)
    Administrator

    >>> print(stevea_ubuntu_team_membership.status.title)
    Approved

    >>> setStatus(
    ...     stevea_ubuntu_team_membership,
    ...     TeamMembershipStatus.DEACTIVATED,
    ...     reviewer=kamion,
    ...     silent=True,
    ... )
    Traceback (most recent call last):
    lp.registry.errors.UserCannotChangeMembershipSilently: ...

    >>> print(stevea_ubuntu_team_membership.status.title)
    Approved


Joining a team with a mailing list
----------------------------------

When a user joins a team with a mailing list, the new member's
notification email contain subscription information.

    >>> owner = factory.makePerson(name="team-owner")
    >>> ignored = login_person(owner)
    >>> team_one, list_one = factory.makeTeamAndMailingList(
    ...     "team-one", owner.name
    ... )
    >>> _ = pop_notifications()
    >>> member = factory.makePerson(
    ...     name="team-member", email="team-member@example.com"
    ... )
    >>> ignored = team_one.addMember(member, owner)
    >>> run_mail_jobs()
    >>> print_distinct_emails(decode=True)  # noqa
    From: Team One ...
    To: Team-member <team-member...>
    X-Launchpad-Message-Rationale: Member (team-one)
    X-Launchpad-Notification-Type: team-membership-new
    Subject: You have been added to team-one
    <BLANKLINE>
    Team-owner (team-owner) added you as a member of Team One (team-one).
      <http://launchpad.test/~team-one>
    <BLANKLINE>
    If you would like to subscribe to the team list, use the link below
    to update your Mailing List Subscription preferences.
      <http://launchpad.test/~/+editmailinglists>
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because you are the new member.
    <BLANKLINE>
    ----------------------------------------

When a team join a team with a mailing list, the new member notification
emails contain subscription information.

    >>> team_two = factory.makeTeam(
    ...     name="team-two", email="team-two@example.com", owner=owner
    ... )
    >>> ignored = team_one.addMember(team_two, owner, force_team_add=True)
    >>> run_mail_jobs()
    >>> print_distinct_emails(include_for=True, decode=True)  # noqa
    From: Team One ...
    To: Team Two <team-two...>
    X-Launchpad-Message-Rationale: Member (team-one) @team-two
    X-Launchpad-Message-For: team-two
    X-Launchpad-Notification-Type: team-membership-new
    Subject: team-two joined team-one
    <BLANKLINE>
    Team-owner (team-owner) added Team Two (team-two) (which you are a
    member of) as a member of Team One (team-one).
      <http://launchpad.test/~team-one>
    <BLANKLINE>
    If you would like to subscribe to the team list, use the link below
    to update your Mailing List Subscription preferences.
      <http://launchpad.test/~/+editmailinglists>
    <BLANKLINE>
    -- 
    <BLANKLINE>
    You received this email because your team Team Two is the new member.
    <BLANKLINE>
    ----------------------------------------
