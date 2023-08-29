Person and Account
==================

The Person object is responsible for updating the status of its
Account object.


Activating user accounts
------------------------

A user may activate their account that was created by an automated
process. Matsubara's account was created during a code import.

    >>> from zope.component import getUtility
    >>> from lp.blueprints.enums import SpecificationFilter
    >>> from lp.services.identity.interfaces.emailaddress import (
    ...     IEmailAddressSet,
    ... )

    >>> emailset = getUtility(IEmailAddressSet)
    >>> emailaddress = emailset.getByEmail("matsubara@async.com.br")
    >>> matsubara = emailaddress.person
    >>> matsubara.is_valid_person
    False
    >>> matsubara.account_status
    <DBItem AccountStatus.NOACCOUNT, ...>
    >>> print(matsubara.preferredemail)
    None

The account can only be activated by the user who is claiming
the profile. Sample Person cannot claim it.

    >>> login("test@canonical.com")
    >>> matsubara.account.reactivate(comment="test")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...'launchpad.View')

Matsubara can.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> login("matsubara@async.com.br")
    >>> matsubara.account.reactivate(comment="test")
    >>> matsubara.setPreferredEmail(emailaddress)
    >>> import transaction
    >>> transaction.commit()
    >>> matsubara.is_valid_person
    True
    >>> matsubara.account.status
    <DBItem AccountStatus.ACTIVE, ...>
    >>> removeSecurityProxy(matsubara.account).status_history
    '...: Unactivated -> Active: test\n'
    >>> print(removeSecurityProxy(matsubara.preferredemail).email)
    matsubara@async.com.br


Deactivating user accounts
--------------------------

Any user can deactivate their own account, in case they don't want it
anymore or they don't want to be shown as Launchpad users.

As seen below, Foo Bar has a bunch of stuff assigned/owned to/by them in
Launchpad which we'll want to be reassigned/unassigned if their account is
deactivated.  Unfortunately, Foo Bar has no specifications assigned to
them, so we'll assign one just to prove that deactivating their account
will cause this spec to be reassigned.


    >>> foobar_preferredemail = emailset.getByEmail("foo.bar@canonical.com")
    >>> foobar = foobar_preferredemail.person
    >>> foobar.specifications(None).is_empty()
    False

    >>> from lp.blueprints.model.specification import Specification
    >>> from lp.registry.model.person import Person
    >>> from lp.services.database.interfaces import IStore
    >>> spec = (
    ...     IStore(Specification)
    ...     .find(Specification, _assignee=None)
    ...     .order_by("id")
    ...     .first()
    ... )
    >>> spec.assignee = foobar

    >>> for membership in foobar.team_memberships:
    ...     print(membership.team.name)
    ...
    canonical-partner-dev
    guadamen
    hwdb-team
    admins
    launchpad-buildd-admins
    launchpad
    testing-spanish-team
    name18
    ubuntu-team
    vcs-imports

    >>> for email in foobar.validatedemails:
    ...     print(email.email)
    ...
    admin@canonical.com

    >>> print(foobar.name)
    name16

    >>> print(foobar.preferredemail.email)
    foo.bar@canonical.com

    >>> [coc.active for coc in foobar.signedcocs]
    [True]

    >>> from lp.bugs.interfaces.bugtasksearch import BugTaskSearchParams
    >>> params = BugTaskSearchParams(foobar, assignee=foobar)
    >>> foobar.searchTasks(params).is_empty()
    False

    >>> foobar.specifications(
    ...     foobar, filter=[SpecificationFilter.ASSIGNEE]
    ... ).is_empty()
    False

    >>> foobar_pillars = []
    >>> for pillar_name in foobar.getAffiliatedPillars(foobar):
    ...     pillar = pillar_name.pillar
    ...     if pillar.owner == foobar or pillar.driver == foobar:
    ...         foobar_pillars.append(pillar_name)
    ...
    >>> len(foobar_pillars) > 0
    True

    >>> foobar_teams = list(Person.selectBy(teamowner=foobar))
    >>> len(foobar_teams) > 0
    True

    >>> foobar.is_valid_person
    True

    >>> comment = (
    ...     "I'm a person who doesn't want to be listed "
    ...     "as a Launchpad user."
    ... )

The deactivate method is restricted to the user themselves --not
even launchpad admins can use it.

    >>> login("mark@example.com")
    >>> foobar.deactivate(comment=comment)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...'launchpad.Special')

    >>> login("foo.bar@canonical.com")
    >>> foobar.deactivate(comment=comment)
    >>> transaction.commit()

Deactivating an account changes many of the person's attributes.  It
adds a '-deactivatedaccount' suffix to the person's name...

    >>> print(foobar.name)
    name16-deactivatedaccount

...an account status of DEACTIVATED...

    >>> foobar.account.status
    <DBItem AccountStatus.DEACTIVATED...

    >>> removeSecurityProxy(foobar.account).status_history
    "... name16: Active -> Deactivated:
    I'm a person who doesn't want to be listed as a Launchpad user.\n"

...to have no team memberships...

    >>> [membership.team.name for membership in foobar.team_memberships]
    []

...and no validated/preferred email addresses...

    >>> [email.email for email in foobar.validatedemails]
    []

    >>> print(getattr(foobar.preferredemail, "email", None))
    None

...no signed codes of conduct...

    >>> [coc.active for coc in foobar.signedcocs]
    [False]

...no assigned bug tasks...

    >>> foobar.searchTasks(params).is_empty()
    True

...no assigned specs...

    >>> foobar.specifications(
    ...     foobar, filter=[SpecificationFilter.ASSIGNEE]
    ... ).is_empty()
    True

...no owned teams...

    >>> Person.selectBy(teamowner=foobar).is_empty()
    True

...no owned or driven pillars...

    >>> foobar.getAffiliatedPillars(foobar).is_empty()
    True

...and, finally, to not be considered a valid person in Launchpad.

    >>> transaction.commit()
    >>> foobar.is_valid_person
    False

It's also important to note that the teams/pillars owned/driven by Foo
Bar are now owned/driven by the registry admins team.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> registry_experts = getUtility(ILaunchpadCelebrities).registry_experts

    >>> registry_pillars = set(registry_experts.getAffiliatedPillars(foobar))
    >>> registry_pillars.issuperset(foobar_pillars)
    True

    >>> registry_teams = set(Person.selectBy(teamowner=registry_experts))
    >>> registry_teams.issuperset(foobar_teams)
    True


Reactivating user accounts
--------------------------

Accounts can be reactivated.

    >>> foobar.reactivate(
    ...     "User reactivated the account using reset password.",
    ...     preferred_email=foobar_preferredemail,
    ... )
    >>> transaction.commit()  # To see the changes on other stores.
    >>> foobar.account.status
    <DBItem AccountStatus.ACTIVE...

    >>> removeSecurityProxy(foobar.account).status_history
    "... name16: Active -> Deactivated: I'm a person
    who doesn't want to be listed as a Launchpad user.\n...:
    Deactivated -> Active:
    User reactivated the account using reset password.\n"

The person name is fixed if it was altered when it was deactivated.

    >>> print(foobar.name)
    name16
