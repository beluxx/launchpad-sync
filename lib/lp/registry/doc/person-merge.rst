Merging
=======

For many reasons (i.e. a gina run) we could have duplicated accounts in
Launchpad. Once a duplicated account is identified, we need to allow the
user to merge two accounts into a single one, because both represent the
same person and they're there just because each of those was created
using a different email address.

    >>> from zope.component import getUtility
    >>> from lp.services.database.sqlbase import sqlvalues
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.personmerge import merge_people
    >>> from lp.testing import login, ANONYMOUS

    >>> login(ANONYMOUS)
    >>> personset = getUtility(IPersonSet)
    >>> name16 = personset.getByName('name16')
    >>> sample = personset.getByName('name12')
    >>> admins = personset.getByName('admins')
    >>> marilize = personset.getByName('marilize')


Sanity checks
-------------

We can't merge an account that still has email addresses attached to it

    >>> merge_people(marilize, sample, None)
    Traceback (most recent call last):
    ...
    AssertionError: ...


Preparing test person for the merge
-----------------------------------

Merging people involves updating the merged person relationships. Let's
put the person we will merge into some of those.

    # To assign marilize as the ubuntu team owner, we must log on as the
    # previous owner.

    >>> login('mark@example.com')

    >>> ubuntu_team = personset.getByName('ubuntu-team')
    >>> ubuntu_team.teamowner = marilize

    >>> ubuntu_translators = personset.getByName('ubuntu-translators')
    >>> ignored = ubuntu_translators.addMember(marilize, marilize)
    >>> rosetta_admins = personset.getByName('rosetta-admins')
    >>> ignored = rosetta_admins.addMember(marilize, marilize)

Karma gets reassigned to the person we merge into. Let's assign karma to
Marilize and save it for later comparison.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> marilize_karma = marilize.assignKarma('bugfixed', product=firefox)
    >>> saved_marilize_karma_id = marilize_karma.id
    >>> print(marilize_karma.person.name)
    marilize

    >>> sampleperson_old_karma = sample.karma

Branches whose owner is being merged are uniquified by appending '-N'
where N is a unique integer. We create "peoplemerge" and "peoplemerge-1"
branches owned by marilize, and a "peoplemerge" and "peoplemerge-1"
branches owned by 'Sample Person' to test that branch name uniquifying
works.

Branches with smaller IDs will be processed first, so we create
"peoplemerge" first, and it will be renamed "peoplemerge-2". The extant
"peoplemerge-1" branch will be renamed "peoplemerge-1-1". The
"peoplemerge-0" branch will not be renamed since it will not conflict.

That is not a particularly sensible way of renaming branches, but it is
simple to implement, and it be should extremely rare for the case to
occur.

    >>> peoplemerge = factory.makePersonalBranch(
    ...     name='peoplemerge', owner=sample)
    >>> peoplemerge1 = factory.makePersonalBranch(
    ...     name='peoplemerge-1', owner=sample)
    >>> peoplemerge0 = factory.makePersonalBranch(
    ...     name='peoplemerge-0', owner=marilize)
    >>> peoplemerge2 = factory.makePersonalBranch(
    ...     name='peoplemerge', owner=marilize)
    >>> peoplemerge11 = factory.makePersonalBranch(
    ...     name='peoplemerge-1', owner=marilize)

'Sample Person' is a deactivated member of the 'Ubuntu Translators'
team, while marilize is an active member. After the merge, 'Sample
Person' will be an active member of that team.

    >>> sample in ubuntu_translators.inactivemembers
    True

    >>> marilize in ubuntu_translators.activemembers
    True

marilize happens to have an LoginToken.

    >>> from lp.services.verification.interfaces.logintoken import (
    ...     ILoginTokenSet)
    >>> from lp.services.verification.interfaces.authtoken import (
    ...     LoginTokenType)
    >>> token = getUtility(ILoginTokenSet).new(
    ...     marilize, marilize.preferredemail.email, 'willdie@example.com',
    ...     LoginTokenType.VALIDATEEMAIL)

Do the merge!
-------------

    # Now we remove the only email address marilize had, so that we can merge
    # it.  First we need to change its status, though, because we can't delete
    # a person's preferred email.

    >>> from lp.services.identity.interfaces.emailaddress import (
    ...     EmailAddressStatus)
    >>> email = marilize.preferredemail
    >>> email.status = EmailAddressStatus.VALIDATED
    >>> email.destroySelf()
    >>> import transaction
    >>> transaction.commit()

    >>> merge_people(marilize, sample, None)


Merge results
-------------

Check that 'Sample Person' has indeed become an active member of 'Ubuntu
Translators'

    >>> sample in ubuntu_translators.activemembers
    True

    >>> sample.inTeam(ubuntu_translators)
    True

Check that the branches have been renamed properly.

    >>> from lp.code.interfaces.branchnamespace import (
    ...     get_branch_namespace)
    >>> sample_junk = get_branch_namespace(sample)
    >>> sample_junk.getByName('peoplemerge') == peoplemerge
    True

    >>> sample_junk.getByName('peoplemerge-0') == peoplemerge0
    True

    >>> sample_junk.getByName('peoplemerge-1') == peoplemerge1
    True

    >>> sample_junk.getByName('peoplemerge-2') == peoplemerge2
    True

    >>> sample_junk.getByName('peoplemerge-1-1') == peoplemerge11
    True

The Karma that was previously assigned to marilize is now assigned to
name12 (Sample Person).

    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> flush_database_caches()
    >>> saved_marilize_karma_id == marilize_karma.id
    True

    >>> print(marilize_karma.person.name)
    name12

Note that we don't bother migrating karma caches - it will just be reset
next time the caches are rebuilt.

    >>> sample.karma == sampleperson_old_karma
    True

A merged person gets a -merged suffix on its name.

    >>> from storm.store import Store
    >>> store = Store.of(marilize)
    >>> results = store.execute(
    ...     "SELECT id FROM Person WHERE name='marilize-merged'")
    >>> results.get_one()[0] == marilize.id
    True

    >>> results = store.execute(
    ...     "SELECT person, team, status from TeamMembership WHERE "
    ...     "person = %s and team = %s" % sqlvalues(
    ...     sample.id, rosetta_admins.id))
    >>> results.get_one()
    (12, 30, 2)

    >>> sample.inTeam(rosetta_admins)
    True

    >>> results = store.execute(
    ...     "SELECT p1.name FROM Person as p1, Person as p2 "
    ...     "WHERE p1.id = p2.teamowner and p2.name = 'ubuntu-team'")
    >>> print(results.get_one()[0])
    name12

The person that has been merged is flagged. We can use this to eliminate
merged persons from lists etc.

    >>> results = store.execute(
    ...     "SELECT merged FROM Person WHERE name='marilize-merged'")
    >>> results.get_one()[0]
    12

    >>> results = store.execute(
    ...     "SELECT merged FROM Person WHERE name='name12'")
    >>> results.get_one()[0] is None
    True

An email is sent to the user informing them that they should review their
email and mailing list subscription settings.

    >>> from lp.registry.interfaces.personnotification import (
    ...     IPersonNotificationSet)

    >>> notification_set = getUtility(IPersonNotificationSet)
    >>> notifications = notification_set.getNotificationsToSend()
    >>> notifications.count()
    1

    >>> notification = notifications[0]
    >>> print(notification.person.name)
    name12

    >>> print(notification.subject)
    Launchpad accounts merged

    >>> print(notification.body)
    The Launchpad account named 'marilize-merged' was merged into the account
    named 'name12'. ...

    You can review and update your email and subscription settings at:

        https://launchpad.net/name12/+editemails ...

sample has not been transferred marilize's logintoken.

    >>> list(getUtility(ILoginTokenSet).searchByEmailRequesterAndType(
    ...     'willdie@example.com', sample, LoginTokenType.VALIDATEEMAIL))
    []

Person decoration
-----------------

Several tables "extend" the Person table by having additional
information that is UNIQUEly keyed to Person.id. We have a utility
function that merges information in those tables, we test it here.

We will use PersonLocation as an example. There are many permutations
and combinations, we will exercise them all, and in each case we'll
create, and then delete, the needed two people.

    >>> from lp.registry.model.person import PersonSet, Person
    >>> from lp.registry.interfaces.person import PersonCreationRationale
    >>> personset = PersonSet()

    >>> skip = []
    >>> def decorator_refs(store, winner, loser):
    ...    results = store.execute(
    ...        "SELECT person, last_modified_by FROM PersonLocation "
    ...        "WHERE person IN (%(loser)d, %(winner)d)"
    ...        "      OR last_modified_by IN (%(loser)d, %(winner)d)"
    ...        "ORDER BY date_created" % {
    ...        'winner': winner.id, 'loser': loser.id})
    ...    result = ''
    ...    for line in results.get_all():
    ...        for item in line:
    ...            if item == winner.id: result += 'winner, '
    ...            elif item == loser.id: result += 'loser, '
    ...            else: result += str(item) + ', '
    ...        result += '\n'
    ...    return result.strip()
    >>> def new_players():
    ...  lead = 99
    ...  while True:
    ...     lead += 1
    ...     name = str(lead)
    ...     lp = PersonCreationRationale.OWNER_CREATED_LAUNCHPAD
    ...     winner = Person(
    ...         name=name+'.winner', display_name='Merge Winner',
    ...         creation_rationale=lp)
    ...     loser = Person(
    ...         name=name+'.loser', display_name='Merge Loser',
    ...         creation_rationale=lp)
    ...     yield winner, loser
    >>> endless_supply_of_players = new_players()

First, we will test a merge where there is no decoration.

    >>> winner, loser = next(endless_supply_of_players)
    >>> print(decorator_refs(store, winner, loser))
    <BLANKLINE>

    >>> from lp.registry.personmerge import _merge_person_decoration
    >>> _merge_person_decoration(winner, loser, skip,
    ...     'PersonLocation', 'person', ['last_modified_by',])

"Skip" should have been updated with the table and unique reference
column name.

    >>> print(pretty(skip))
    [('personlocation', 'person')]

There should still be no columns that reference the winner or loser.

    >>> print(decorator_refs(store, winner, loser))
    <BLANKLINE>

OK, now, this time, we will add some decorator information to the winner
but not the loser.

    >>> winner, loser = next(endless_supply_of_players)
    >>> winner.setLocation(None, None, 'America/Santiago', winner)
    >>> print(decorator_refs(store, winner, loser))
    winner, winner,

    >>> _merge_person_decoration(winner, loser, skip,
    ...     'PersonLocation', 'person', ['last_modified_by',])

There should now still be one decorator, with all columns pointing to
the winner:

    >>> print(decorator_refs(store, winner, loser))
    winner, winner,

This time, we will have a decorator for the person that is being merged
INTO another person, but nothing on the target person.

    >>> winner, loser = next(endless_supply_of_players)
    >>> loser.setLocation(None, None, 'America/Santiago', loser)
    >>> print(decorator_refs(store, winner, loser))
    loser, loser,

    >>> _merge_person_decoration(winner, loser, skip,
    ...     'PersonLocation', 'person', ['last_modified_by',])

There should now still be one decorator, with all columns pointing to
the winner:

    >>> print(decorator_refs(store, winner, loser))
    winner, winner,

Now, we want to show what happens when there is a decorator for both the
to_person and the from_person. We expect that the from_person record
will remain as noise but non-unique columns will have been updated to
point to the winner, and the to_person will be unaffected.

    >>> winner, loser = next(endless_supply_of_players)
    >>> winner.setLocation(None, None, 'America/Santiago', winner)
    >>> loser.setLocation(None, None, 'America/New_York', loser)
    >>> print(decorator_refs(store, winner, loser))
    winner, winner,
    loser, loser,

    >>> _merge_person_decoration(winner, loser, skip,
    ...     'PersonLocation', 'person', ['last_modified_by',])
    >>> print(decorator_refs(store, winner, loser))
    winner, winner,
    loser, winner,


Merging teams
-------------

Merging of teams is also possible and uses the same API used for merging
people.  Note, though, that when merging teams, its polls will not be
carried over to the remaining team.  Team memberships, on the other
hand, are carried over just like when merging people.

    >>> from datetime import datetime, timedelta
    >>> import pytz
    >>> from lp.registry.interfaces.poll import IPollSubset, PollSecrecy
    >>> test_team = personset.newTeam(sample, 'test-team', 'Test team')
    >>> launchpad_devs = personset.getByName('launchpad')
    >>> ignored = launchpad_devs.addMember(
    ...     test_team, reviewer=launchpad_devs.teamowner, force_team_add=True)
    >>> today = datetime.now(pytz.timezone('UTC'))
    >>> tomorrow = today + timedelta(days=1)
    >>> poll = IPollSubset(test_team).new(
    ...     u'test-poll', u'Title', u'Proposition', today, tomorrow,
    ...     PollSecrecy.OPEN, allowspoilt=True)

    # test_team has a superteam, one active member and a poll.

    >>> for team in test_team.super_teams:
    ...     print(team.name)
    launchpad

    >>> print(test_team.teamowner.name)
    name12

    >>> for member in test_team.allmembers:
    ...     print(member.name)
    name12

    >>> list(IPollSubset(test_team).getAll())
    [<lp.registry.model.poll.Poll object at ...]

    # Landscape-developers has no super teams, two members and no polls.

    >>> landscape = personset.getByName('landscape-developers')
    >>> [team.name for team in landscape.super_teams]
    []

    >>> print(landscape.teamowner.name)
    name12

    >>> for member in landscape.allmembers:
    ...     print(member.name)
    salgado
    name12

    >>> list(IPollSubset(landscape).getAll())
    []
