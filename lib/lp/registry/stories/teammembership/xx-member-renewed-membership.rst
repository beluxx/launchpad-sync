Renewing your own memberships
=============================

Depending on a team's renewal policy, a team member may be allowed to
renew their own membership. That is allowed for teams which have ONDEMAND
as the renewal policy and for active memberships which are about to
expire. Also note that this can only be done by the members themselves or
by an administrator of a member team.

We'll use Karl's membership on the Mirror Administrators team to
demonstrate that. That team's renewal policy is not ONDEMAND and the
membership is not about to expire, so it can't be renewed unless we make
some changes.

    >>> from lp.testing import ANONYMOUS, login, logout
    >>> login(ANONYMOUS)
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import (
    ...     IPersonSet,
    ...     TeamMembershipRenewalPolicy,
    ... )
    >>> from lp.registry.interfaces.teammembership import ITeamMembershipSet
    >>> personset = getUtility(IPersonSet)
    >>> membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
    ...     personset.getByName("karl"),
    ...     personset.getByName("ubuntu-mirror-admins"),
    ... )
    >>> print(membership.dateexpires)
    None
    >>> membership.team.renewal_policy != TeamMembershipRenewalPolicy.ONDEMAND
    True
    >>> logout()

Even though there won't be a link to the page in which it would
otherwise be possible to renew that membership, the user could manually
craft the URL to get to it, so in this case the page will simply say the
membership can't be renewed and explain why.

    >>> browser = setupBrowser(auth="Basic karl@canonical.com:test")
    >>> browser.open(
    ...     "http://launchpad.test/~karl/+expiringmembership/"
    ...     "ubuntu-mirror-admins"
    ... )
    >>> browser.getControl("Renew")
    Traceback (most recent call last):
    ...
    LookupError: label ...'Renew'
    ...
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Renew membership of Karl Tilbury in Mirror Administrators
    This membership cannot be renewed because Mirror Administrators
    (ubuntu-mirror-admins) is not a team that allows its members to renew
    their own memberships.

Other users (apart from Karl) can't see that page.

    >>> user_browser.open(
    ...     "http://launchpad.test/~karl/+expiringmembership/"
    ...     "ubuntu-mirror-admins"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

If we change the team's renewal policy it still won't be possible for
the user to renew that membership because it's not about to expire.

    >>> login("mark@example.com")
    >>> team = personset.getByName("ubuntu-mirror-admins")
    >>> team.defaultrenewalperiod = 365
    >>> team.renewal_policy = TeamMembershipRenewalPolicy.ONDEMAND
    >>> logout()

    >>> browser.open(
    ...     "http://launchpad.test/~karl/+expiringmembership/"
    ...     "ubuntu-mirror-admins"
    ... )
    >>> browser.getControl("Renew")
    Traceback (most recent call last):
    ...
    LookupError: label ...'Renew'
    ...
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Renew membership of Karl Tilbury in Mirror Administrators
    This membership cannot be renewed because it is not set to expire in
    28 days or less. You or one of the team administrators has already
    renewed it.

If we now change Karl's membership to expire in a couple days, he'll be
able to renew it himself.

See lib/lp/registry/stories/team/xx-team-membership.rst for an explanation
of the expiry._control.attrs TestBrowser voodoo.

    >>> from datetime import datetime, timedelta, timezone
    >>> now = datetime.now(timezone.utc)
    >>> day_after_tomorrow = now + timedelta(days=2)

    >>> team_admin_browser = setupBrowser(auth="Basic mark@example.com:test")
    >>> team_admin_browser.open(
    ...     "http://launchpad.test/~ubuntu-mirror-admins/+member/karl"
    ... )
    >>> team_admin_browser.getControl(name="expires").value = ["date"]
    >>> expiry = team_admin_browser.getControl(
    ...     name="membership.expirationdate"
    ... )
    >>> del expiry._control.attrs["disabled"]
    >>> expiry.value = day_after_tomorrow.date().strftime("%Y-%m-%d")
    >>> team_admin_browser.getControl(name="change").click()

    >>> team_admin_browser.url
    'http://launchpad.test/~ubuntu-mirror-admins/+members'

    >>> browser.open(
    ...     "http://launchpad.test/~karl/+expiringmembership/"
    ...     "ubuntu-mirror-admins"
    ... )
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Renew membership of Karl Tilbury in Mirror Administrators
    This membership is going to expire ... from now. If you want to
    remain a member of Mirror Administrators, you must renew it.
    or Cancel

Karl then renews his membership.

    >>> browser.getControl("Renew").click()
    >>> browser.url
    'http://launchpad.test/~karl'
    >>> for tag in find_tags_by_class(
    ...     browser.contents, "informational message"
    ... ):
    ...     print(tag.decode_contents())
    Membership renewed until ...

Karl can't renew it again, since it's now not set to expire soon.

    >>> browser.open(
    ...     "http://launchpad.test/~karl/+expiringmembership/"
    ...     "ubuntu-mirror-admins"
    ... )
    >>> browser.getControl("Renew")
    Traceback (most recent call last):
    ...
    LookupError: label ...'Renew'
    ...
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Renew membership of Karl Tilbury in Mirror Administrators
    This membership cannot be renewed because it is not set to expire in
    28 days or less. You or one of the team administrators has already
    renewed it.

In the case of subteams whose membership is about to expire, any admin of the
member team can renew the soon-to-expire membership, as long as the parent
team's renewal policy is ONDEMAND.

    >>> login("mark@example.com")
    >>> mirror_admins = personset.getByName("ubuntu-mirror-admins")
    >>> landscape_devs = personset.getByName("landscape-developers")
    >>> ignored = mirror_admins.addMember(
    ...     landscape_devs, mirror_admins.teamowner, force_team_add=True
    ... )
    >>> membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
    ...     landscape_devs, mirror_admins
    ... )
    >>> membership.setExpirationDate(
    ...     now + timedelta(days=1), mirror_admins.teamowner
    ... )
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> flush_database_updates()
    >>> logout()

Logged in as Sample Person (one of landscape developers' admins), we'll
now renew the membership.

    >>> browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> browser.open(
    ...     "http://launchpad.test/~landscape-developers"
    ...     "/+expiringmembership/ubuntu-mirror-admins"
    ... )
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Renew membership of Landscape Developers in Mirror Administrators
    This membership is going to expire ... from now. If you want this team
    to remain a member of Mirror Administrators, you must renew it.
    or Cancel

    >>> browser.getControl("Renew").click()
    >>> browser.url
    'http://launchpad.test/~landscape-developers'
    >>> for tag in find_tags_by_class(
    ...     browser.contents, "informational message"
    ... ):
    ...     print(tag.decode_contents())
    Membership renewed until ...

If the user double clicks or goes back to a cached version of the page
and tries to resubmit the form, it will skip the actual renewal process,
and it will display the same message. This prevents the user from being
confused, which would be the case if a double click on the submit button
provided no information as to whether the membership was renewed.

    >>> browser.goBack()
    >>> browser.getControl("Renew").click()
    >>> browser.url
    'http://launchpad.test/~landscape-developers'
    >>> for tag in find_tags_by_class(
    ...     browser.contents, "informational message"
    ... ):
    ...     print(tag.decode_contents())
    Membership renewed until ...

When the page is loaded again, there is no form since the membership
will no longer be expiring soon.

    >>> browser.open(
    ...     "http://launchpad.test/~landscape-developers"
    ...     "/+expiringmembership/ubuntu-mirror-admins"
    ... )
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Renew membership of Landscape Developers in Mirror Administrators
    This membership cannot be renewed because it is not set to expire in
    28 days or less. Somebody else has already renewed it.

Any user who's not an admin of landscape-developers can't even see that page.

    >>> user_browser.open(
    ...     "http://launchpad.test/~landscape-developers"
    ...     "/+expiringmembership/ubuntu-mirror-admins"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...
