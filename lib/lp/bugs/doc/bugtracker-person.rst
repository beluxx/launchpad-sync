The BugTrackerPerson interface
==============================

The IBugTrackerPerson interfaces allows Launchpad to link Persons to
bugtrackers. BugTrackerPersons are created using the
linkPersonToSelf() method of IBugTracker.

    >>> from zope.component import getUtility
    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.bugs.tests.externalbugtracker import new_bugtracker

    >>> sample_person = getUtility(IPersonSet).getByName("name12")

    >>> bugtracker = new_bugtracker(BugTrackerType.BUGZILLA)

We'll rename the bugtracker to make the tests more readable.

    >>> from lp.testing.dbuser import lp_dbuser

    >>> with lp_dbuser():
    ...     bugtracker.name = "bugzilla-checkwatches"
    ...

    >>> bugtracker_person = bugtracker.linkPersonToSelf(
    ...     "some-name-i-made-up", sample_person
    ... )

    >>> print(bugtracker_person.name)
    some-name-i-made-up

    >>> print(bugtracker_person.person.name)
    name12

    >>> print(bugtracker_person.bugtracker.name)
    bugzilla-checkwatches

A name can only be registered with a bugtracker once. Trying to link a
new person to a bugtracker using an existing name will cause an error.

    >>> foo_bar = getUtility(IPersonSet).getByName("name16")
    >>> bugtracker_person = bugtracker.linkPersonToSelf(
    ...     "some-name-i-made-up", foo_bar
    ... )
    Traceback (most recent call last):
      ...
    lp.bugs.interfaces.bugtrackerperson.BugTrackerPersonAlreadyExists: Name
    'some-name-i-made-up' is already in use for bugtracker
    'bugzilla-checkwatches'.

The BugTrackerPerson record for a given name on a given bugtracker can
be retrieved by calling BugTracker.getLinkedPersonByName().

    >>> bugtracker_person = bugtracker.getLinkedPersonByName(
    ...     "some-name-i-made-up"
    ... )

    >>> print(bugtracker_person.name)
    some-name-i-made-up

    >>> print(bugtracker_person.person.name)
    name12


ensurePersonForSelf()
---------------------

IBugTracker has a method, ensurePersonForSelf(), which is
responsible for returning the correct BugTrackerPerson for a given
remote username on on a given bugtracker.

Passing a new remote user's details to ensurePersonForSelf() will
return a new Person record.

    >>> from lp.registry.interfaces.person import PersonCreationRationale

    >>> print(getUtility(IPersonSet).getByEmail("new.person@example.com"))
    None

    >>> new_person = bugtracker.ensurePersonForSelf(
    ...     display_name="New Person",
    ...     email="new.person@example.com",
    ...     rationale=PersonCreationRationale.BUGIMPORT,
    ...     creation_comment="whilst testing ensurePersonForSelf().",
    ... )

    >>> print(new_person.displayname)
    New Person

There won't be a BugTrackerPerson record linking 'New Person' to the
bugtracker since we have an email address for 'New Person'. That means
that we can always retrieve them reliably when we encounter them in a
remote bugtracker.

    >>> bugtracker_person = bugtracker.getLinkedPersonByName("New Person")
    >>> print(bugtracker_person)
    None

Calling ensurePersonForSelf() with the same details will return the
same person.

    >>> other_person = bugtracker.ensurePersonForSelf(
    ...     display_name="New Person",
    ...     email="new.person@example.com",
    ...     rationale=PersonCreationRationale.BUGIMPORT,
    ...     creation_comment="whilst testing ensurePersonForSelf().",
    ... )

    >>> print(other_person.name)
    new-person

    >>> print(new_person.name)
    new-person

ensurePersonForSelf() can also handle remote users whose email
addresses aren't provided.

    >>> noemail_person = bugtracker.ensurePersonForSelf(
    ...     display_name="No-Email-Person",
    ...     email=None,
    ...     rationale=PersonCreationRationale.BUGIMPORT,
    ...     creation_comment="whilst testing ensurePersonForSelf().",
    ... )

    >>> print(noemail_person.name)
    no-email-person-bugzilla-checkwatches

A BugTrackerPerson record will have been created to map
'No-Email-Person' on our example bugtracker to
'no-email-person-bugzilla-checkwatches-1' in Launchpad.

    >>> bugtracker_person = bugtracker.getLinkedPersonByName(
    ...     "No-Email-Person"
    ... )

    >>> bugtracker_person.person == noemail_person
    True

ensurePersonForSelf() handles situations in which bugtrackers have
been renamed, too, and avoids name collisions when doing so.

We'll create a person, 'noemail,' on our example bugtracker.

    >>> new_person = bugtracker.ensurePersonForSelf(
    ...     display_name="noemail",
    ...     email=None,
    ...     rationale=PersonCreationRationale.BUGIMPORT,
    ...     creation_comment="whilst testing.",
    ... )

    >>> print(new_person.name)
    noemail-bugzilla-checkwatches

    >>> bugtracker_person = bugtracker.getLinkedPersonByName("noemail")

    >>> print(bugtracker_person.bugtracker.name)
    bugzilla-checkwatches

    >>> print(bugtracker_person.person.name)
    noemail-bugzilla-checkwatches

    >>> transaction.commit()

If we rename the BugTracker and then create another with the same name,
calling ensurePersonForSelf() for 'noemail' on that BugTracker
should produce a new Person rather than re-using the existing one.

    >>> other_bug_tracker = new_bugtracker(BugTrackerType.BUGZILLA)

    >>> with lp_dbuser():
    ...     bugtracker.name = "bugzilla-checkwatches-renamed"
    ...     other_bug_tracker.name = "bugzilla-checkwatches"
    ...

A new Person has been created for 'noemail' on other_bug_tracker, even
though that bug tracker's name is the same as one from which we've
imported previously.

    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerSet
    >>> bugtracker = getUtility(IBugTrackerSet).get(bugtracker.id)
    >>> other_bugtracker = getUtility(IBugTrackerSet).get(
    ...     other_bug_tracker.id
    ... )

    >>> original_bugtracker_person = bugtracker.getLinkedPersonByName(
    ...     "noemail"
    ... )

    >>> new_person = other_bugtracker.ensurePersonForSelf(
    ...     "noemail",
    ...     None,
    ...     PersonCreationRationale.BUGIMPORT,
    ...     "while testing, again",
    ... )

    >>> print(original_bugtracker_person.person.name)
    noemail-bugzilla-checkwatches

    >>> print(new_person.name)
    noemail-bugzilla-checkwatches-1

