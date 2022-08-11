Private Team Creation
=====================

Private teams may only be created by commercial admins
(launchpad.Commercial permission).  This permission is controlled in
the UI by only displaying the 'visibility' control to commercial
admins.

Unprivileged users do not see the visibility widget.

    >>> from lp.registry.interfaces.person import (
    ...     IPersonSet,
    ...     PersonVisibility,
    ...     )
    >>> personset = getUtility(IPersonSet)
    >>> nopriv = personset.getByEmail('no-priv@canonical.com')
    >>> login('no-priv@canonical.com')

    >>> view = create_initialized_view(
    ...     personset, '+newteam',
    ...     form={}, principal=nopriv)
    >>> 'visibility' in [field.__name__ for field in view.form_fields]
    False

Members of the commercial team who are not admins do see the
visibility widget.

    >>> login('commercial-member@canonical.com')
    >>> commercial_member = (
    ...     personset.getByEmail('commercial-member@canonical.com'))
    >>> view = create_initialized_view(
    ...     personset, '+newteam',
    ...     form={}, principal=commercial_member)
    >>> 'visibility' in [field.__name__ for field in view.form_fields]
    True

And real admins see the visibility widget too.

    >>> login('foo.bar@canonical.com')
    >>> foo_bar = personset.getByEmail('foo.bar@canonical.com')
    >>> view = create_initialized_view(
    ...     personset, '+newteam',
    ...     form={}, principal=foo_bar)
    >>> 'visibility' in [field.__name__ for field in view.form_fields]
    True

When creating a private team, the team membership policy must be
'Restricted.'

    >>> login('foo.bar@canonical.com')
    >>> foo_bar = personset.getByEmail('foo.bar@canonical.com')
    >>> form = {
    ...     'field.name': 'super-secret',
    ...     'field.display_name': 'Shhhh',
    ...     'field.defaultmembershipperiod': '365',
    ...     'field.defaultrenewalperiod': '',
    ...     'field.membership_policy': 'OPEN',
    ...     'field.renewal_policy': 'NONE',
    ...     'field.visibility': 'PRIVATE',
    ...     'field.actions.create': 'Create',
    ...     }
    >>> view = create_initialized_view(
    ...     personset, '+newteam',
    ...     form=form, principal=foo_bar)

    >>> print(len(view.request.notifications))
    0

    >>> for error in view.errors:
    ...     print(error)
    Private teams must have a Restricted membership policy.

When the inputs are correct the admin can successfully create the team.

    >>> form = {
    ...     'field.name': 'super-secret2',
    ...     'field.display_name': 'Shhhh',
    ...     'field.defaultmembershipperiod': '365',
    ...     'field.defaultrenewalperiod': '',
    ...     'field.membership_policy': 'RESTRICTED',
    ...     'field.renewal_policy': 'NONE',
    ...     'field.visibility': 'PRIVATE',
    ...     'field.actions.create': 'Create',
    ...     }
    >>> view = create_initialized_view(
    ...     personset, '+newteam',
    ...     form=form, principal=foo_bar)

    >>> print(len(view.request.notifications))
    0
    >>> print(len(view.errors))
    0

Commercial admins can create a team too.

    >>> login('commercial-member@canonical.com')
    >>> form = {
    ...     'field.name': 'secret-team',
    ...     'field.display_name': 'Shhhh',
    ...     'field.defaultmembershipperiod': '365',
    ...     'field.defaultrenewalperiod': '365',
    ...     'field.membership_policy': 'RESTRICTED',
    ...     'field.renewal_policy': 'ONDEMAND',
    ...     'field.visibility': 'PRIVATE',
    ...     'field.actions.create': 'Create',
    ...     }
    >>> view = create_initialized_view(
    ...     personset, '+newteam',
    ...     form=form, principal=commercial_member)

    >>> print(len(view.request.notifications))
    0

    >>> print(len(view.errors))
    0

    >>> import transaction
    >>> transaction.commit()
    >>> secret_team = personset.getByName('secret-team')
    >>> print(secret_team.visibility.name)
    PRIVATE

Admins who attempt to create a new team with the name of an existing
team get the normal error message.

    >>> login('foo.bar@canonical.com')
    >>> form = {
    ...     'field.name': 'secret-team',
    ...     'field.display_name': 'Shhhh',
    ...     'field.defaultmembershipperiod': '365',
    ...     'field.defaultrenewalperiod': '',
    ...     'field.membership_policy': 'RESTRICTED',
    ...     'field.renewal_policy': 'NONE',
    ...     'field.visibility': 'PRIVATE',
    ...     'field.actions.create': 'Create',
    ...     }
    >>> view = create_initialized_view(
    ...     personset, '+newteam',
    ...     form=form, principal=foo_bar)

    >>> print(len(view.request.notifications))
    0

    >>> for error in view.errors:
    ...     print(view.getFieldError(error.field_name))
    secret-team is already in use by another person or team.

Regular users who try to create a team with a name that is already
taken by a private team get the blacklist message.

    >>> login('no-priv@canonical.com')
    >>> form = {
    ...     'field.name': 'secret-team',
    ...     'field.display_name': 'Shhhh',
    ...     'field.defaultmembershipperiod': '365',
    ...     'field.defaultrenewalperiod': '',
    ...     'field.membership_policy': 'RESTRICTED',
    ...     'field.renewal_policy': 'NONE',
    ...     'field.actions.create': 'Create',
    ...     }
    >>> view = create_initialized_view(
    ...     personset, '+newteam',
    ...     form=form, principal=nopriv)

    >>> print(len(view.request.notifications))
    0

    >>> for error in view.errors:
    ...     print(view.getFieldError(error.field_name))
    The name &#x27;secret-team&#x27; has been blocked by the Launchpad
    administrators.  Contact Launchpad Support if you want to use this
    name.


Private Team Editing
--------------------

The same as when creating a new team, only commercial admins are given
the option of changing a team's visibility.

    >>> launchpad = personset.getByName('launchpad')
    >>> view = create_initialized_view(
    ...     launchpad, '+edit',
    ...     form={}, principal=nopriv)
    >>> 'visibility' in [field.__name__ for field in view.form_fields]
    False

    >>> login('foo.bar@canonical.com')
    >>> foo_bar = personset.getByEmail('foo.bar@canonical.com')
    >>> view = create_initialized_view(
    ...     launchpad, '+edit',
    ...     form={}, principal=foo_bar)
    >>> 'visibility' in [field.__name__ for field in view.form_fields]
    True

And a private team must have restricted membership.

    >>> login('foo.bar@canonical.com')
    >>> foo_bar = personset.getByEmail('foo.bar@canonical.com')

    >>> form = {
    ...     'field.name': 'super-secret3',
    ...     'field.display_name': 'Shhhh',
    ...     'field.defaultmembershipperiod': '365',
    ...     'field.defaultrenewalperiod': '',
    ...     'field.membership_policy': 'OPEN',
    ...     'field.renewal_policy': 'NONE',
    ...     'field.visibility': 'PRIVATE',
    ...     'field.actions.save': 'Save',
    ...     }
    >>> view = create_initialized_view(
    ...     secret_team, '+edit',
    ...     form=form, principal=foo_bar)

    >>> print(len(view.request.notifications))
    0

    >>> for error in view.errors:
    ...     print(error)
    Private teams must have a Restricted membership policy.

Visibility transitions
----------------------

A team can only change visibility if the new state will not leak any
data or put the team into an inconsistent state. Public teams can become
private and vice-versa, as long as they only participate in a set list
of known-OK relationships.

Public teams can be made private if the only artifacts they have are
those permitted by private teams.

    >>> def createTeamArtifacts(team, team_owner):
    ...     # A bug subscription.
    ...     bug = factory.makeBug()
    ...     bug.subscribe(team, team_owner)
    ...     bugtask = bug.default_bugtask
    ...     bugtask.transitionToAssignee(team)
    ...     # A branch subscription.
    ...     from lp.code.enums import (
    ...         BranchSubscriptionDiffSize,
    ...         BranchSubscriptionNotificationLevel,
    ...         CodeReviewNotificationLevel)
    ...     branch = factory.makeBranch()
    ...     branch.subscribe(
    ...         team,
    ...         BranchSubscriptionNotificationLevel.DIFFSONLY,
    ...         BranchSubscriptionDiffSize.WHOLEDIFF,
    ...         CodeReviewNotificationLevel.STATUS, team_owner)
    ...     # A Git repository subscription.
    ...     repository = factory.makeGitRepository()
    ...     repository.subscribe(
    ...         team,
    ...         BranchSubscriptionNotificationLevel.DIFFSONLY,
    ...         BranchSubscriptionDiffSize.WHOLEDIFF,
    ...         CodeReviewNotificationLevel.STATUS, team_owner)
    ...     # A PPA.
    ...     from lp.soyuz.enums import ArchivePurpose
    ...     from lp.soyuz.interfaces.archive import IArchiveSet
    ...     from lp.registry.interfaces.distribution import (
    ...         IDistributionSet)
    ...     ubuntu = getUtility(IDistributionSet)['ubuntu']
    ...     archive_set = getUtility(IArchiveSet)
    ...     private_archive = archive_set.new(
    ...         owner=team, purpose=ArchivePurpose.PPA,
    ...         distribution=ubuntu, name=team.name+'-archive',
    ...         require_virtualized=False)
    ...     private_archive.private = True
    ...     # A private PPA subscription.
    ...     login('foo.bar@canonical.com')
    ...     another_team = factory.makeTeam(
    ...         owner=team_owner,
    ...         visibility=PersonVisibility.PRIVATE)
    ...     # We must login as the archive owner to add the subscription.
    ...     login_person(team_owner)
    ...     private_archive.newSubscription(
    ...         subscriber=another_team,
    ...         registrant=team_owner)


    >>> login('foo.bar@canonical.com')
    >>> team = factory.makeTeam(
    ...     owner=foo_bar,
    ...     visibility=PersonVisibility.PUBLIC)

    >>> createTeamArtifacts(team, foo_bar)

    >>> form = {
    ...     'field.visibility': 'PRIVATE',
    ...     'field.membership_policy': 'RESTRICTED',
    ...     'field.actions.save': 'Save',
    ...     }
    >>> view = create_initialized_view(
    ...     team, '+edit',
    ...     form=form, principal=foo_bar)
    >>> print(len(view.request.notifications))
    0
    >>> print(len(view.errors))
    0

If the team has any other artifacts then it will not be allowed to
change to Private.

    >>> team = factory.makeTeam(
    ...     owner=foo_bar,
    ...     visibility=PersonVisibility.PUBLIC)

    >>> createTeamArtifacts(team, foo_bar)

    >>> bug_tracker = factory.makeBugTracker()
    >>> bug_tracker.owner = team

    >>> form = {
    ...     'field.visibility': 'PRIVATE',
    ...     'field.membership_policy': 'RESTRICTED',
    ...     'field.actions.save': 'Save',
    ...     }
    >>> view = create_initialized_view(
    ...     team, '+edit',
    ...     form=form, principal=foo_bar)
    >>> print(len(view.request.notifications))
    0
    >>> for error in view.errors:
    ...     print(error)
    This team cannot be converted to Private since it is referenced by a
    bugtracker.

All changes are aborted when a data validation error occurs.  The
display_name for the team is the old value.

    >>> transaction.commit()
    >>> super_secret2 = personset.getByName('super-secret2')
    >>> print(super_secret2.name)
    super-secret2

    >>> print(super_secret2.display_name)
    Shhhh



Use of 'private-' prefix
------------------------

Commercial admins can create private projects with the 'private-' prefix.

    >>> login('foo.bar@canonical.com')
    >>> form = {
    ...     'field.name': 'private-super-secret',
    ...     'field.display_name': 'Shhhh',
    ...     'field.defaultmembershipperiod': '365',
    ...     'field.defaultrenewalperiod': '',
    ...     'field.membership_policy': 'RESTRICTED',
    ...     'field.renewal_policy': 'NONE',
    ...     'field.visibility': 'PRIVATE',
    ...     'field.actions.create': 'Create',
    ...     }
    >>> view = create_initialized_view(
    ...     personset, '+newteam',
    ...     form=form, principal=foo_bar)

    >>> print(len(view.request.notifications))
    0
    >>> print(len(view.errors))
    0

When trying to register a project with a 'private-' prefix, regular
users will get a blacklist message.

    >>> login('no-priv@canonical.com')
    >>> form = {
    ...     'field.name': 'private-top-secret',
    ...     'field.display_name': 'Shhhh',
    ...     'field.defaultmembershipperiod': '365',
    ...     'field.defaultrenewalperiod': '',
    ...     'field.membership_policy': 'RESTRICTED',
    ...     'field.renewal_policy': 'NONE',
    ...     'field.visibility': 'PRIVATE',
    ...     'field.actions.create': 'Create',
    ...     }
    >>> view = create_initialized_view(
    ...     personset, '+newteam',
    ...     form=form, principal=nopriv)

    >>> print(len(view.request.notifications))
    0

    >>> for error in view.errors:
    ...     print(view.getFieldError(error.field_name))
    The name &#x27;private-top-secret&#x27; has been blocked by the
    Launchpad administrators. Contact Launchpad Support if you want to
    use this name.
