Person admin pages
==================

Admistrators can access a subset of any IPerson's fields from the UI.
The PersonAdministerView is registered under the +review name.

    >>> from lp.services.webapp.authorization import check_permission
    >>> from lp.services.webapp.interfaces import IOpenLaunchBag

    >>> login("foo.bar@canonical.com")
    >>> admin = getUtility(IOpenLaunchBag).user
    >>> user = factory.makePerson(name="a-user", email="zaphod@example.place")
    >>> view = create_initialized_view(user, "+review")
    >>> check_permission("launchpad.Admin", view)
    True
    >>> print(view.errors)
    []
    >>> view.field_names
    ['name', 'display_name',
     'personal_standing', 'personal_standing_reason',
     'require_strong_email_authentication']
    >>> view.label
    'Review person'

The template for the view is shared with the +reviewaccount view, so
the is_viewing_person view property is provide to verify that the context
is an IPerson or IAccount.

    >>> view.is_viewing_person
    True

The PersonAdministerView allows Launchpad admins to change some
of a user's attributes.

    >>> form = {
    ...     "field.name": "zaphod",
    ...     "field.display_name": "Zaphod Beeblebrox",
    ...     "field.personal_standing": "POOR",
    ...     "field.personal_standing_reason": "Zaphod's just this guy.",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(user, "+review", form=form)
    >>> print(view.errors)
    []
    >>> print(user.name)
    zaphod
    >>> print(user.display_name)
    Zaphod Beeblebrox
    >>> user.personal_standing
    <DBItem PersonalStanding.POOR, ...>
    >>> print(user.personal_standing_reason)
    Zaphod's just this guy.
    >>> user.require_strong_email_authentication
    False

Non administrators cannot access the +review view

    >>> ignored = login_person(user)
    >>> view = create_initialized_view(user, "+review")
    >>> check_permission("launchpad.Admin", view)
    False


Reviewing a person's account
----------------------------

The +reviewaccount allows admins to see and edit user account information.
Non-admins cannot access it.

    >>> view = create_view(user, "+reviewaccount")
    >>> check_permission("launchpad.Admin", view)
    False

An admin can see a user's account information.

    >>> ignored = login_person(admin)
    >>> view = create_initialized_view(
    ...     user, "+reviewaccount", principal=admin
    ... )
    >>> check_permission("launchpad.Admin", view)
    True
    >>> print(view.errors)
    []
    >>> view.field_names
    ['status', 'comment']
    >>> view.label
    "Review person's account"

The context is an IAccount, so the is_viewing_person property is False.

    >>> view.context
    <Account ...>
    >>> view.is_viewing_person
    False

The view displays non-editable user information too so that the admin does
not need to look in the db.

    >>> for email in view.email_addresses:
    ...     print(email)
    ...
    zaphod@example.place

The admin can change the user's account information.

    >>> form = {
    ...     "field.status": "ACTIVE",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(user, "+reviewaccount", form=form)
    >>> print(view.errors)
    []

An admin can suspend a user's account using the +reviewaccount view. When
an account is suspended, the preferred email address is disabled.

    >>> user.account_status
    <DBItem AccountStatus.ACTIVE, ...>
    >>> print(user.account_status_history)
    None

    >>> form = {
    ...     "field.status": "SUSPENDED",
    ...     "field.comment": "Wanted by the galactic police.",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(user, "+reviewaccount", form=form)
    >>> print(view.errors)
    []
    >>> transaction.commit()
    >>> user.account_status
    <DBItem AccountStatus.SUSPENDED, ...>
    >>> user.account_status_history
    '... name16: Active -> Suspended: Wanted by the galactic police.\n'
    >>> print(user.preferredemail)
    None

No one can force account status to an invalid transition:

    >>> form = {
    ...     "field.status": "ACTIVE",
    ...     "field.status_history": "Zaphod's a hoopy frood.",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(user, "+reviewaccount", form=form)
    >>> [e.args[2] for e in view.errors]
    [AccountStatusError(...'The status cannot change from Suspended to
    Active')]


An admin can deactivate a suspended user's account too. Unlike the act of
suspension, reactivation does not change the user's email addresses; the
user must log in to restore the email addresses using the reactivate step.

    >>> form = {
    ...     "field.status": "DEACTIVATED",
    ...     "field.comment": "Zaphod's a hoopy frood.",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(user, "+reviewaccount", form=form)
    >>> print(view.errors)
    []
    >>> user.account_status
    <DBItem AccountStatus.DEACTIVATED, ...>
    >>> user.account_status_history
    "... name16: Active -> Suspended: Wanted by the galactic police.\n...
    name16: Suspended -> Deactivated: Zaphod's a hoopy frood.\n"
    >>> print(user.preferredemail)
    None


An admin can mark an account as belonging to a user who has died.

    >>> form = {
    ...     "field.status": "DECEASED",
    ...     "field.comment": "In memoriam.",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(user, "+reviewaccount", form=form)
    >>> print(view.errors)
    []
    >>> user.account_status
    <DBItem AccountStatus.DECEASED, ...>
    >>> user.account_status_history
    "... name16: Active -> Suspended: Wanted by the galactic police.\n...
    name16: Suspended -> Deactivated: Zaphod's a hoopy frood.\n...
    name16: Deactivated -> Deceased: In memoriam.\n"
