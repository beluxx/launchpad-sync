PersonRoles
===========

To make it more convenient to check which roles a person has,
the IPersonRoles adapter is provided. It's main use is to easily check if a
person is the member of a celebrity team or is a celebrity person. In
addition, methods for common checks are provided, too.

The IPersonRoles interface is closely tight to the ILaunchpadCelebrities
interface. Any addition or removal of a person celebrity must be reflected in
adding or removing the corresponding property in IPersonRoles. Luckily the
celebrities.rst doctest includes a check for this and will give useful
information on which attribute needs to be added or removed. Both interfaces
are found in the same file. There is no need to adapt the implementation
class PersonRoles, though (thanks to __getattr__).

PersonRoles is most prominent in AuthenticationBase in security.py. The user
parameter to checkAuthenticated is a PersonRoles object (was a Person object).


The person object and the adapter
---------------------------------

PersonRoles is registered as an unnamed adapter for IPersonRoles.

    >>> from lp.registry.interfaces.role import IPersonRoles
    >>> person = factory.makePerson()
    >>> print(IPersonRoles(person))
    <PersonRoles ...>

The original Person object can be reached through the person attribute.

    >>> roles = IPersonRoles(person)
    >>> print(roles.person is person)
    True


Celebrity persons
-----------------

There are a number of celebrity persons defined in ILaunchpadCelebrities.
PersonRoles has a corresponding attribute of the same name prefixed with
"in_" to check if the person in question is a member of this celebrity or is
this celebrity. The following tests are identical.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
    >>> print(person.inTeam(rosetta_experts))
    False

    >>> print(roles.in_rosetta_experts)
    False

The test will succeed once we make person a member of the team. Need to be an
admin to do that.

    >>> login("foo.bar@canonical.com")
    >>> rosetta_experts.addMember(person, rosetta_experts.teamowner)
    (True, ...Approved>)
    >>> print(roles.in_rosetta_experts)
    True

To stay consistent, all attributes are prefixed with "in_" although the
attribute names of ILaunchpadCelebrities are not all lexically correct
plurals, nor are all the attributes teams. This makes for odd sounding
attribute names in IPersonRoles.

    >>> print(roles.in_admin)
    False
    >>> print(roles.in_janitor)
    False

    >>> janitor = getUtility(ILaunchpadCelebrities).janitor
    >>> janitor_roles = IPersonRoles(janitor)
    >>> print(janitor_roles.in_janitor)
    True


inTeam
------

The Person.inTeam method is available directly through PersonRoles. This can
be used to check for any non-celebrity team.

    >>> new_team = factory.makeTeam()
    >>> new_team.addMember(person, new_team.teamowner)
    (True, ...Approved>)
    >>> print(person.inTeam(new_team))
    True

    >>> print(roles.inTeam(new_team))
    True


isOwner, isDriver
-----------------

We can easily check for ownership and drivership. If an object
provides IHasDrivers, its ancestors' drivers will be checked too.

    >>> product = factory.makeProduct(owner=person)
    >>> print(roles.isOwner(product))
    True

    >>> driver = factory.makePerson()
    >>> driver_roles = IPersonRoles(driver)
    >>> print(driver_roles.isDriver(product))
    False
    >>> product.driver = driver
    >>> print(driver_roles.isDriver(product))
    True
    >>> productseries = factory.makeProductSeries(product=product)
    >>> print(driver_roles.isDriver(productseries))
    True


isOneOf
-------

Finally, sometimes a person may be one of multiple roles for an object. The
method isOneOf makes checking all of these a breeze.

    >>> spec = factory.makeSpecification()
    >>> spec.assignee = person
    >>> print(roles.isOwner(spec))
    False
    >>> print(roles.isOneOf(spec, ["owner", "approver", "assignee"]))
    True
