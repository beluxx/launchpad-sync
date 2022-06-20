Calculating bug heat
====================

Launchpad bugs each have a 'heat' rating. This is an indicator of how
problematic a given bug is to the community and can be used to determine
which bugs should be tackled first.

A bug's heat is calculated automatically when it is created.

    >>> bug_owner = factory.makePerson()
    >>> bug = factory.makeBug(owner=bug_owner)
    >>> bug.heat
    6

Updating bug heat on-the-fly
----------------------------

The update_bug_heat method updates a Bug's heat using data already in
the database. update_bug_heat() uses a stored procedure in the database to
calculate the heat overall.

We'll create a new bug with a heat of 0 for the sake of testing.

    >>> bug_owner = factory.makePerson()
    >>> bug = factory.makeBug(owner=bug_owner)
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(bug).heat = 0

Calling update_bug_heat() will update the bug's heat. Since this new bug has
one subscriber (the bug owner) and one affected user (ditto) its
heat after update will be 6.

    >>> from lp.bugs.model.bug import update_bug_heat
    >>> update_bug_heat([bug.id])
    >>> bug.heat
    6


Events which trigger bug heat updates
-------------------------------------

There are several events which will cause a bug's heat to be updated.
First, as stated above, heat will be calculated when the bug is created.

    >>> bug = factory.makeBug(owner=bug_owner)
    >>> bug.heat
    6

Marking a bug as private also gives it an extra 150 heat points.

    >>> changed = bug.setPrivate(True, bug_owner)
    >>> bug.heat
    156

Setting the bug as security related adds another 250 heat points.

    >>> changed = bug.setSecurityRelated(True, bug_owner)
    >>> bug.heat
    406

Marking the bug public removes 150 heat points.

    >>> changed = bug.setPrivate(False, bug_owner)
    >>> bug.heat
    256

And marking it not security-related removes 250 points.

    >>> changed = bug.setSecurityRelated(False, bug_owner)
    >>> bug.heat
    6

Adding a subscriber to the bug increases its heat by 2 points.

    >>> new_subscriber = factory.makePerson()
    >>> more_subscriber = factory.makePerson()
    >>> subscription = bug.subscribe(new_subscriber, new_subscriber)
    >>> subscription = bug.subscribe(more_subscriber, more_subscriber)
    >>> bug.heat
    10

When a user unsubscribes, the bug loses 2 points of heat.

    >>> bug.unsubscribe(new_subscriber, new_subscriber)
    >>> bug.heat
    8

Should a user mark themselves as affected by the bug, it will gain 4
points of heat.

    >>> bug.markUserAffected(new_subscriber)
    >>> bug.heat
    12

If a user who was previously affected marks themself as not affected,
the bug loses 4 points of heat.

    >>> bug.markUserAffected(new_subscriber, False)
    >>> bug.heat
    8

If a user who wasn't affected by the bug marks themselve as explicitly
unaffected, the bug's heat doesn't change.

    >>> unaffected_person = factory.makePerson()
    >>> bug.markUserAffected(unaffected_person, False)
    >>> bug.heat
    8

Marking the bug as a duplicate won't change its heat, but it will add 10
points of heat to the bug it duplicates: 6 points for the duplication
and 4 points for the subscribers that the duplicated bug inherits.

    >>> duplicated_bug = factory.makeBug()
    >>> duplicated_bug.heat
    6

    >>> bug.markAsDuplicate(duplicated_bug)
    >>> bug.heat
    8

    >>> duplicated_bug.heat
    16

Unmarking the bug as a duplicate restores its heat and updates the
duplicated bug's heat.

    >>> bug.markAsDuplicate(None)
    >>> bug.heat
    8

    >>> duplicated_bug.heat
    6

A number of other changes, handled by the Bug's addChange() method, will
cause heat to be recalculated, even if the heat itself may not actually
change.

For example, updating the bug's description calls the addChange() event,
and will cause the bug's heat to be recalculated.

We'll set the bug's heat to 0 first to demonstrate this.

    >>> removeSecurityProxy(bug).heat = 0

    >>> from datetime import datetime, timedelta
    >>> from pytz import timezone
    >>> from lp.services.utils import utc_now

    >>> from lp.bugs.adapters.bugchange import BugDescriptionChange
    >>> change = BugDescriptionChange(
    ...     when=utc_now(),
    ...     person=bug.owner, what_changed='description',
    ...     old_value=bug.description, new_value='Some text')
    >>> bug.addChange(change)
    >>> bug.heat
    8


Getting bugs whose heat is outdated
-----------------------------------

It's possible to get the set of bugs whose heat hasn't been updated for
a given amount of time by calling IBugSet's getBugsWithOutdatedHeat()
method.

First, we'll set the heat_last_updated of all bugs so that none of them are
out of date.

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.model.bug import Bug
    >>> from lp.services.database.interfaces import IStore
    >>> IStore(Bug).find(Bug).set(
    ...     heat_last_updated=datetime.now(timezone('UTC')))

If we call getBugsWithOutdatedHeat() now, the set that is returned will
be empty because all the bugs have been recently updated.
getBugsWithOutdatedHeat() takes a single parameter, cutoff, which is the
oldest a bug's heat can be before it gets included in the returned set.

    >>> yesterday = datetime.now(timezone('UTC')) - timedelta(days=1)
    >>> getUtility(IBugSet).getBugsWithOutdatedHeat(yesterday).count()
    0

If we make a bug's heat older than the cutoff that we pass to
getBugsWithOutdatedHeat() it will appear in the set returned by
getBugsWithOutdatedHeat().

    >>> old_heat_bug = factory.makeBug()
    >>> naked_bug = removeSecurityProxy(old_heat_bug)
    >>> naked_bug.heat = 0
    >>> naked_bug.heat_last_updated = datetime.now(
    ...     timezone('UTC')) - timedelta(days=2)

    >>> outdated_bugs = getUtility(IBugSet).getBugsWithOutdatedHeat(
    ...     yesterday)
    >>> outdated_bugs.count()
    1

    >>> outdated_bugs[0] == old_heat_bug
    True

getBugsWithOutdatedHeat() also returns bugs whose heat has never been
updated.

    >>> new_bug = factory.makeBug()

We'll set the new bug's heat_last_updated to None manually.

    >>> removeSecurityProxy(new_bug).heat_last_updated = None

    >>> outdated_bugs = getUtility(IBugSet).getBugsWithOutdatedHeat(
    ...     yesterday)
    >>> outdated_bugs.count()
    2

    >>> new_bug in outdated_bugs
    True


The BugHeatUpdater class
---------------------------

The BugHeatUpdater class is used to create bug heat calculation jobs for
bugs with out-of-date heat.

    >>> from lp.scripts.garbo import BugHeatUpdater
    >>> from lp.services.log.logger import FakeLogger

We'll commit the transaction so that the BugHeatUpdater updates the
right bugs.

    >>> transaction.commit()
    >>> update_bug_heat = BugHeatUpdater(FakeLogger())

BugHeatUpdater implements ITunableLoop and as such is callable. Calling
it as a method will recalculate the heat for all the out-of-date bugs.

There are two bugs with heat more than a day old:

    >>> getUtility(IBugSet).getBugsWithOutdatedHeat(yesterday).count()
    2

The updater gets the cutoff from a feature flag. By default no bugs are
considered outdated.

    >>> update_bug_heat(chunk_size=1)
    DEBUG Updating heat for 0 bugs

    >>> getUtility(IBugSet).getBugsWithOutdatedHeat(yesterday).count()
    2

If we set the cutoff to a day ago, calling our BugHeatUpdater will update the
heat of those bugs.

    >>> from lp.services.features.testing import FeatureFixture
    >>> flag = FeatureFixture(
    ...     {'bugs.heat_updates.cutoff': yesterday.isoformat()})

    >>> with flag:
    ...     update_bug_heat(chunk_size=1)
    DEBUG Updating heat for 1 bugs

IBugSet.getBugsWithOutdatedHeat() will now return 1 item.

    >>> getUtility(IBugSet).getBugsWithOutdatedHeat(yesterday).count()
    1

Update the rest in one big chunk.

    >>> with flag:
    ...     update_bug_heat(chunk_size=1000)
    DEBUG Updating heat for 1 bugs

IBugSet.getBugsWithOutdatedHeat() will now return an empty set since all
the bugs have been updated.

    >>> getUtility(IBugSet).getBugsWithOutdatedHeat(yesterday).count()
    0
