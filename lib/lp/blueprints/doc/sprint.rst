Sprints / Meetings
==================

Sprints or meetings can be coordinated using Launchpad.

    >>> from datetime import datetime, timedelta, timezone
    >>> from zope.component import getUtility
    >>> from lp.blueprints.interfaces.sprint import ISprintSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> sprintset = getUtility(ISprintSet)

To find a sprint by name, use:

    >>> gentoo = sprintset["gentoo"]

The major pillars, product, distribution and project, have some
properties which give us the sprints relevant to them.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet

    >>> productset = getUtility(IProductSet)
    >>> projectset = getUtility(IProjectGroupSet)
    >>> distroset = getUtility(IDistributionSet)
    >>> firefox = productset.getByName("firefox")
    >>> ubuntu = distroset.getByName("ubuntu")
    >>> mozilla = projectset.getByName("mozilla")

Make a new sprint and add some relevant specifications to it.

    >>> futurista = factory.makeSprint(
    ...     name="futurista",
    ...     time_starts=datetime.now(timezone.utc) + timedelta(days=1),
    ... )
    >>> firefox_spec = firefox.specifications(futurista.owner)[0]
    >>> _ = firefox_spec.linkSprint(futurista, futurista.owner)
    >>> ubuntu_spec = ubuntu.specifications(futurista.owner)[0]
    >>> _ = ubuntu_spec.linkSprint(futurista, futurista.owner)

We have coming_sprints, giving us up to 5 relevant events that are up-
and-coming (sorted by the starting date):

    >>> for sprint in firefox.coming_sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...
    futurista ...-...-...

    >>> for sprint in ubuntu.coming_sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...
    futurista ...-...-...

    >>> for sprint in mozilla.coming_sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...
    futurista ...-...-...

And we have sprints, giving us all sprints relevant to that pillar
(sorted descending by the starting date):

    >>> for sprint in firefox.sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...
    futurista ...-...-...
    ubz 2005-10-07

    >>> for sprint in ubuntu.sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...
    futurista ...-...-...

    >>> for sprint in mozilla.sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...
    futurista ...-...-...
    ubz 2005-10-07

We also have past_sprints, giving all sprints relevant to that pillar
that are not coming sprints.

    >>> for sprint in firefox.past_sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...
    ubz 2005-10-07

    >>> for sprint in ubuntu.past_sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...

    >>> for sprint in mozilla.past_sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...
    ubz 2005-10-07

Now, these sprint APIs show only sprints with specifications that are
approved, not ones where the only specs are proposed.  So, we'll change
the specs related to the Ubuntu "futurista" sprint to "proposed", and
then check the coming sprints and all sprints.

    >>> from lp.blueprints.enums import SprintSpecificationStatus

We're directly using the database classes here, bypassing the security
proxies because this is just set-up for the next step, it's not the
exact functionality we're testing.

    >>> from lp.blueprints.model.sprint import SprintSet
    >>> futurista = SprintSet()["futurista"]
    >>> for sprintspec in futurista.specificationLinks():
    ...     sprintspec.status = SprintSpecificationStatus.PROPOSED
    ...

Flush the updates to the database so we'll see them.

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.services.propertycache import clear_property_cache
    >>> flush_database_updates()
    >>> clear_property_cache(ubuntu)

See, there are no ubuntu sprints.

    >>> for sprint in ubuntu.sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...

    >>> for sprint in ubuntu.coming_sprints:
    ...     print(sprint.name, sprint.time_starts.strftime("%Y-%m-%d"))
    ...


Specification Listings
----------------------

We should be able to get lists of specifications in different states
related to a sprint.

Basically, we can filter by completeness, and by whether or not the spec
is informational.

    >>> ubz = sprintset["ubz"]

    >>> from lp.blueprints.enums import SpecificationFilter

First, there should be no informational specs for ubz:

    >>> filter = [SpecificationFilter.INFORMATIONAL]
    >>> ubz.specifications(None, filter=filter).count()
    1

There are 0 completed specs for UBZ:

    >>> filter = [SpecificationFilter.COMPLETE]
    >>> ubz.specifications(None, filter=filter).count()
    0

And there are three incomplete specs:

    >>> filter = [SpecificationFilter.INCOMPLETE]
    >>> for spec in ubz.specifications(None, filter=filter):
    ...     print(spec.name, spec.is_complete)
    ...
    svg-support False
    extension-manager-upgrades False
    e4x False

If we ask for all specs, we get them in the order of priority.

    >>> filter = [SpecificationFilter.ALL]
    >>> for spec in ubz.specifications(None, filter=filter):
    ...     print(spec.priority.title, spec.name)
    ...
    High svg-support
    Medium extension-manager-upgrades
    Not e4x

And if we ask just for specs, we get them all

    >>> for spec in ubz.specifications(None):
    ...     print(spec.name, spec.is_complete)
    ...
    svg-support False
    extension-manager-upgrades False
    e4x False

Inactive products are excluded from the listings.

    >>> from lp.testing import login
    >>> from lp.registry.interfaces.product import IProductSet

    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> login("foo.bar@canonical.com")

    # Unlink the source packages so the project can be deactivated.

    >>> from lp.testing import unlink_source_packages
    >>> unlink_source_packages(firefox)
    >>> firefox.active = False
    >>> flush_database_updates()
    >>> ubz.specifications(None).count()
    0

Reset firefox so we don't mess up later tests.

    >>> firefox.active = True
    >>> flush_database_updates()


Sprint Driver
-------------

Each sprint had a driver - the person (or team) that can decide on the
list of blueprints for discussion. The driver is stored in the `driver`
attribute.

    >>> person_set = getUtility(IPersonSet)
    >>> paris = sprintset["paris"]
    >>> sample_person = person_set.getByEmail("test@canonical.com")
    >>> nopriv_person = person_set.getByEmail("no-priv@canonical.com")
    >>> admin_person = person_set.getByEmail("foo.bar@canonical.com")

We can use the `isDriver` method on sprint objects to determine whether
a user is considered a driver for a sprint.

    >>> paris.isDriver(nopriv_person)
    False

sample_person is the driver for the paris sprint.

    >>> paris.driver == sample_person
    True

Obviously, we'd expect isDriver to return true for them.

    >>> paris.isDriver(sample_person)
    True

Administrators are always considered drivers for any sprint.

    >>> paris.isDriver(admin_person)
    True


Sprint attendance
-----------------

The sprint attend() method adds a user's attendance to a sprint.

    >>> person = factory.makePerson(name="mustard")
    >>> time_starts = datetime(2005, 10, 7, 9, 0, 0, 0, timezone.utc)
    >>> time_ends = datetime(2005, 10, 17, 19, 5, 0, 0, timezone.utc)
    >>> sprint_attendance = ubz.attend(person, time_starts, time_ends, True)

The attend() method can update a user's attendance if there is already a
ISprintAttendance for the user.

    >>> print(sprint_attendance.attendee.name)
    mustard

    >>> print(sprint_attendance.time_starts)
    2005-10-07 09:00:00+00:00

    >>> print(sprint_attendance.time_ends)
    2005-10-17 19:05:00+00:00

    >>> print(sprint_attendance.is_physical)
    True

    >>> time_starts = datetime(2005, 10, 8, 9, 0, 0, 0, timezone.utc)
    >>> time_ends = datetime(2005, 10, 16, 19, 5, 0, 0, timezone.utc)
    >>> new_attendance = ubz.attend(person, time_starts, time_ends, False)
    >>> print(new_attendance.attendee.name)
    mustard

    >>> print(new_attendance.time_starts)
    2005-10-08 09:00:00+00:00

    >>> print(new_attendance.time_ends)
    2005-10-16 19:05:00+00:00

    >>> print(new_attendance.is_physical)
    False

The sprint attendances property returns a list of SprintAttendance
objects.

    >>> ubz.attendances
    [<...SprintAttendance ...>]

    >>> for attendance in ubz.attendances:
    ...     print(attendance.attendee.name)
    ...
    mustard


Sprint deletion
---------------

The sprint destroySelf() method deletes a sprint.

    >>> ubz.destroySelf()
    >>> sprintset["ubz"]
