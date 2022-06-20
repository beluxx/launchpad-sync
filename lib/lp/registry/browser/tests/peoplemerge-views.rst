People Merge Pages
==================

There are a number of views for merging people and teams.

Team Merges
-----------

Create a member of the registry team that is not a member of the admins
team.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.persontransferjob import (
    ...     IPersonMergeJobSource,
    ...     )
    >>> registry_experts = getUtility(ILaunchpadCelebrities).registry_experts
    >>> person_set = getUtility(IPersonSet)
    >>> merge_job_source = getUtility(IPersonMergeJobSource)
    >>> registry_expert= factory.makeRegistryExpert()
    >>> ignored = login_person(registry_expert)

A team (name21) can be merged into another (ubuntu-team).

    >>> print(person_set.getByName('name21').displayname)
    Hoary Gnome Team
    >>> print(person_set.getByName('ubuntu-team').displayname)
    Ubuntu Team

    >>> form = {'field.dupe_person': 'name21',
    ...         'field.target_person': 'ubuntu-team',
    ...         'field.actions.merge': 'Merge'}
    >>> view = create_initialized_view(
    ...     person_set, '+adminteammerge', form=form)
    >>> len(view.errors)
    0
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    A merge is queued and is expected to complete in a few minutes.


Attempting to merge a non-existent team results in an error.

    >>> transaction.commit()
    >>> form = {'field.dupe_person': 'not-a-real-team',
    ...         'field.target_person': 'another-fake-team',
    ...         'field.actions.merge': 'Merge'}
    >>> view = create_initialized_view(
    ...     person_set, '+adminteammerge', form=form)
    >>> len(view.errors)
    2
    >>> for error in view.errors:
    ...     print(error.args[0])
    Invalid value
    Invalid value


People merge
------------

For regular users to merge Launchpad profiles, we require that they confirm
ownership of the merged profile's email addresses, so it's not possible for
them to merge a profile which has no email address.

    >>> _ = login_person(factory.makePerson())

    # First we need to forge a person without a single email address.
    >>> from lp.registry.interfaces.person import PersonCreationRationale
    >>> person = person_set.createPersonWithoutEmail(
    ...     'email-less-person', PersonCreationRationale.UNKNOWN)
    >>> transaction.commit()

    >>> form = {'field.dupe_person': person.name,
    ...        'field.actions.continue': 'Continue'}
    >>> view = create_initialized_view(
    ...     person_set, '+requestmerge', form=form)
    >>> len(view.errors)
    2
    >>> print(view.getFieldError('dupe_person'))
    The duplicate is not a valid person or team.

Admins and registry experts, on the other hand, are allowed to merge people
without a single email address.

    >>> _ = login_person(registry_expert)
    >>> form = {'field.dupe_person': person.name,
    ...         'field.target_person': 'name16',
    ...         'field.actions.merge': 'Merge'}
    >>> view = create_initialized_view(
    ...     person_set, '+adminpeoplemerge', form=form)
    >>> view.errors
    []
    >>> print(view.request.response.getHeader('location'))
    http://launchpad.test/~name16


Delete team
-----------

Users with launchpad.Moderate such as team admins and registry experts
can delete teams.

    >>> from lp.services.webapp.authorization import check_permission

    >>> team_owner = factory.makePerson()
    >>> team_member = factory.makePerson()
    >>> deletable_team = factory.makeTeam(owner=team_owner, name='deletable')
    >>> ignored = login_person(team_owner)
    >>> ignore = deletable_team.addMember(team_member, reviewer=team_owner)
    >>> view = create_initialized_view(deletable_team, '+delete')

    >>> ignored = login_person(team_member)
    >>> check_permission('launchpad.Moderate', view)
    False

    >>> ignored = login_person(registry_expert)
    >>> check_permission('launchpad.Moderate', view)
    True

    >>> ignored = login_person(team_owner)
    >>> check_permission('launchpad.Moderate', view)
    True

The view provides a label, page_title, and cancel url to present the page.

    >>> print(view.label)
    Delete Deletable

    >>> print(view.page_title)
    Delete

    >>> print(view.cancel_url)
    http://launchpad.test/~deletable

The view uses the similar form fields as the team merge view, but it does not
render them because their values are preset. Only the action is rendered,
and it is only rendered if canDelete() returns True.

    >>> from lp.testing.pages import find_tag_by_id

    >>> view = create_initialized_view(
    ...     deletable_team, '+delete', principal=team_owner)
    >>> view.field_names
    ['dupe_person']

    >>> for key, value in sorted(view.default_values.items()):
    ...     print('%s: %s' % (key, value))
    field.delete: True
    field.dupe_person: deletable

    >>> content = find_tag_by_id(view.render(), 'maincontent')
    >>> print(find_tag_by_id(content, 'field.dupe_person'))
    None

    >>> print(find_tag_by_id(content, 'field.delete'))
    None

    >>> print(find_tag_by_id(content, 'field.actions.delete')['value'])
    Delete

    >>> view.canDelete(data={})
    True

The page explains how many users will be removed from the team before it is
deleted.

    >>> from lp.testing.pages import extract_text

    >>> print(extract_text(content))
    Delete Deletable
    Deleting a team is permanent. It cannot be undone.
    Deletable has 2 active members who will be removed before it is deleted...

The user is redirected to /people when a team is deleted.

    >>> form = {'field.actions.delete': 'Delete'}
    >>> view = create_initialized_view(deletable_team, '+delete', form=form)
    >>> view.errors
    []

    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    The team is queued to be deleted.

    >>> print(view.next_url)
    http://launchpad.test/people

And there is a person merge job setup to delete them.

    >>> job = merge_job_source.find(deletable_team).any()
    >>> job.metadata['delete']
    True
    >>> print(job.from_person.name)
    deletable

The delete team view cannot be hacked to delete another team, or change
the team that the merge operation is performed with.

    >>> deletable_team = factory.makeTeam(owner=team_owner, name='delete-me')
    >>> transaction.commit()
    >>> form = {
    ...     'field.target_person': 'rosetta-admins',
    ...     'field.dupe_person': 'landscape-developers',
    ...     'field.actions.delete': 'Delete'}
    >>> view = create_initialized_view(deletable_team, '+delete', form=form)
    >>> for error in view.errors:
    ...     print(error)
    Unable to process submitted data.

    >>> view.request.response.notifications
    []

A team with a mailing list cannot be deleted.

    >>> team, mailing_list = factory.makeTeamAndMailingList(
    ...     'not-deletable', 'rock')
    >>> ignored = login_person(team.teamowner)
    >>> view = create_initialized_view(
    ...     team, '+delete', principal=team.teamowner)
    >>> view.canDelete(data={})
    False

    >>> view.has_mailing_list
    True

    >>> content = find_tag_by_id(view.render(), 'maincontent')
    >>> print(extract_text(content))
    Delete Not Deletable
    Deleting a team is permanent. It cannot be undone.
    This team cannot be deleted until its mailing list is first deactivated,
    then purged after the deactivation is confirmed...

    >>> print(find_tag_by_id(content, 'field.actions.delete'))
    None

Private teams can be deleted by admins.

    >>> from lp.registry.interfaces.person import PersonVisibility

    >>> login('commercial-member@canonical.com')
    >>> private_team = factory.makeTeam(
    ...     name='secret', visibility=PersonVisibility.PRIVATE)
    >>> login('admin@canonical.com')
    >>> form = {'field.actions.delete': 'Delete'}
    >>> view = create_initialized_view(private_team, '+delete', form=form)
    >>> view.errors
    []
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    The team is queued to be deleted.
