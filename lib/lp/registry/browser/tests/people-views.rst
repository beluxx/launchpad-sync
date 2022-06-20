==============================
Searching for people and teams
==============================

The view behind the /people page provides searching for people and teams.  The
view knows how many people and teams are currently registered in Launchpad.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login('admin@canonical.com')
    >>> person_set = getUtility(IPersonSet)

    >>> view = create_initialized_view(person_set, '+index')
    >>> view.number_of_people
    48
    >>> view.number_of_teams
    17


Search state
============

The view can state if the view is a teams only or people only search.

    >>> view.is_teams_only
    False

    >>> view.is_people_only
    False

The property is_teams_only is true when the searchfor field is teamsonly.

    >>> form = dict(searchfor='teamsonly')
    >>> view = create_initialized_view(person_set, '+index', form=form)
    >>> view.is_teams_only
    True

    >>> view.is_people_only
    False

The property is_people_only is true when the searchfor field is peopleonly.

    >>> form = dict(searchfor='peopleonly')
    >>> view = create_initialized_view(person_set, '+index', form=form)
    >>> view.is_teams_only
    False

    >>> view.is_people_only
    True


Batch navigator
===============

The view returns a batch navigator for searching through sets of teams,
people, or both.  By default, both are searched for the given name.  There is
one person and one team matching the 'test' string.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> def print_batch(batch):
    ...     for thing in batch.currentBatch():
    ...         naked_thing = removeSecurityProxy(thing)
    ...         print(naked_thing)

    >>> form = dict(name='test')
    >>> view = create_initialized_view(person_set, '+index', form=form)
    >>> print_batch(view.searchPeopleBatchNavigator())
    <Person at ... name12 (Sample Person)>
    <Person at ... testing-spanish-team (testing Spanish team)>

Searching for just people returns Sample Person.

    >>> form['searchfor'] = 'peopleonly'
    >>> view = create_initialized_view(person_set, '+index', form=form)
    >>> print_batch(view.searchPeopleBatchNavigator())
    <Person at ... name12 (Sample Person)>

Searching for just teams returns the testing Spanish team.

    >>> form['searchfor'] = 'teamsonly'
    >>> view = create_initialized_view(person_set, '+index', form=form)
    >>> print_batch(view.searchPeopleBatchNavigator())
    <Person at ... testing-spanish-team (testing Spanish team)>
