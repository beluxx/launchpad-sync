ProjectGroups
=============

A ProjectGroup is a group of Products, making it possible to for
example see all bugs in the ProjectGroup's Product, or make them share a
common external bug tracker.

    # Some basic imports
    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.projectgroup import (
    ...     IProjectGroup,
    ...     IProjectGroupSet,
    ...     )
    >>> projectset = getUtility(IProjectGroupSet)

    # Some setup
    >>> import transaction
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from zope.component import getUtility
    >>> login('admin@canonical.com')
    >>> evolution = getUtility(IProductSet).getByName('evolution')
    >>> evolution.translations_usage = ServiceUsage.LAUNCHPAD
    >>> login('test@canonical.com')
    >>> transaction.commit()

Creating new projects
---------------------

When creating a new project there are a bunch of things we need to provide.
While some of them (homepageurl, icon, logo and mugshot) are optional, others
(name, displayname, title, summary, description and owner) are required).

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> no_priv = getUtility(IPersonSet).getByName('no-priv')
    >>> test_project = projectset.new(
    ...     name='project-test', display_name='Test Project',
    ...     title='Just a test project', homepageurl=None,
    ...     summary='Mandatory summary', description='blah',
    ...     owner=no_priv)
    >>> print(test_project.name)
    project-test


Looking up existing projects
----------------------------

To fetch a project we use IProjectGroupSet.getByName() or
IProjectGroupSet.__getitem__. The former will, by default, return active and
inactive projects, while the latter returns only active ones. Both can be
used to look up projects by their aliases, though.

    >>> gnome = projectset['gnome']
    >>> print(gnome.name)
    gnome
    >>> print(projectset.getByName('gnome').name)
    gnome

    # Need to login as an LP admin to set a project's aliases.
    >>> login('foo.bar@canonical.com')
    >>> gnome.setAliases(['dwarf'])
    >>> for alias in gnome.aliases:
    ...     print(alias)
    dwarf
    >>> login(ANONYMOUS)
    >>> print(projectset['dwarf'].name)
    gnome
    >>> print(projectset.getByName('dwarf').name)
    gnome

Make sure that a project provides the IProjectGroup interface.

    >>> verifyObject(IProjectGroup, gnome)
    True
    >>> IProjectGroup.providedBy(gnome)
    True

If there is no project with the specified name, a NotFoundError will be
raised.

    >>> projectset['non-existant']
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...

The same will happen if we set a product to be inactive. This is a good
way of hiding bogus projects, without actually deleting them from the
db, since the __getitem__ method of IProjectGroupSet is used to traverse to
the project.

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> login("foo.bar@canonical.com")
    >>> gnome.active = False
    >>> flush_database_updates()


    >>> gnome = getUtility(IProjectGroupSet)['gnome']
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...

The inactive project will still be accessible using
IProjectGroupSet.getByName(), though.

    >>> gnome = getUtility(IProjectGroupSet).getByName('gnome')
    >>> print(gnome.name)
    gnome
    >>> gnome.active
    False

getByName() also accepts an argument to ignore inactive projects.

    >>> projectgroups = getUtility(IProjectGroupSet)
    >>> print(projectgroups.getByName('gnome', ignore_inactive=True))
    None

Products which are part of a project
------------------------------------

The products which are part of a given project are given by a project's
.products property. Note that only active products are included and they're
ordered by their names.

    >>> for product in gnome.products:
    ...     print(product.displayname)
    Evolution
    GNOME Terminal
    Gnome Applets
    NetApplet
    gnomebaker

    >>> netapplet = gnome.getProduct('netapplet')

    # Unlink the source packages so the project can be deactivated.
    >>> from lp.testing import unlink_source_packages
    >>> unlink_source_packages(netapplet)
    >>> netapplet.active = False
    >>> flush_database_updates()
    >>> from lp.services.propertycache import clear_property_cache
    >>> clear_property_cache(gnome)
    >>> for product in gnome.products:
    ...     print(product.displayname)
    Evolution
    GNOME Terminal
    Gnome Applets
    gnomebaker

    # Re-activate netapplet so that we don't interfere in other tests below.
    >>> netapplet.active = True
    >>> flush_database_updates()


Specification Listings
----------------------

We should be able to generate filtered lists of specs on a project.

    >>> mozilla = getUtility(IProjectGroupSet).getByName('mozilla')
    >>> from lp.blueprints.enums import SpecificationFilter

First, there should be only one informational spec for mozilla:

    >>> filter = [SpecificationFilter.INFORMATIONAL]
    >>> for spec in mozilla.specifications(None, filter=filter):
    ...    print(spec.name)
    extension-manager-upgrades


There are no completed specs for mozilla:

    >>> filter = [SpecificationFilter.COMPLETE]
    >>> for spec in mozilla.specifications(None, filter=filter):
    ...    print(spec.name)


And there are five incomplete specs:

    >>> filter = [SpecificationFilter.INCOMPLETE]
    >>> mozilla.specifications(None, filter=filter).count()
    5

We can filter for specifications that contain specific text:

    >>> for spec in mozilla.specifications(None, filter=[u'install']):
    ...     print(spec.name)
    extension-manager-upgrades


Inactive products are excluded from the listings.

    >>> filter = [SpecificationFilter.INCOMPLETE]
    >>> mozilla.specifications(None, filter=filter).count()
    5

    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet).getByName('firefox')

    # Unlink the source packages so the project can be deactivated.
    >>> from lp.testing import unlink_source_packages
    >>> unlink_source_packages(firefox)
    >>> firefox.active = False
    >>> flush_database_updates()
    >>> filter = [SpecificationFilter.INCOMPLETE]
    >>> mozilla.specifications(None, filter=filter).count()
    0

Reset firefox so we don't mess up later tests.

    >>> firefox.active = True
    >>> flush_database_updates()

We can get all the specifications via the visible_specifications property,
and all valid specifications via the valid_specifications method:

    >>> for spec in mozilla.visible_specifications:
    ...    print(spec.name)
    svg-support
    canvas
    extension-manager-upgrades
    mergewin
    e4x

    >>> for spec in mozilla.valid_specifications():
    ...    print(spec.name)
    svg-support
    canvas
    extension-manager-upgrades
    mergewin
    e4x


Specification Listings for a ProjectGroupSeries
-----------------------------------------------

An IProjectGroupSeries object can be retrieved by IProjectGroup.getSeries.

    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSeries
    >>> mozilla_series_1_0 = mozilla.getSeries('1.0')
    >>> mozilla_series_1_0
    <lp.registry.model.projectgroup.ProjectGroupSeries object at...

    >>> IProjectGroupSeries.providedBy(mozilla_series_1_0)
    True

If no series with the given name exists, IProjectGroup.getSeries returns None.

    >>> print(mozilla.getSeries('nonsense'))
    None

IProjectGroupSeries.visible_specifications lists all specifications
assigned to a series. Currently, no specifications are assigned to the
Mozilla series 1.0.

    >>> specs = mozilla_series_1_0.visible_specifications
    >>> specs.count()
    0

If a specification is assigned to series 1.0, it appears in
mozilla_1_0_series.visible_specifications.

    >>> filter = [SpecificationFilter.INFORMATIONAL]
    >>> extension_manager_upgrades = mozilla.specifications(
    ...     None, filter=filter)[0]
    >>> series_1_0 = firefox.getSeries('1.0')
    >>> extension_manager_upgrades.proposeGoal(series_1_0, no_priv)
    >>> for spec in mozilla_series_1_0.visible_specifications:
    ...     print(spec.name)
    extension-manager-upgrades

This specification is not listed for other series.

    >>> mozilla_trunk = mozilla.getSeries('trunk')
    >>> print(mozilla_trunk.visible_specifications.count())
    0

Filtered lists of project series related specifications are generated
the same way as for project related specifications.

    >>> for spec in mozilla_series_1_0.specifications(None, filter=filter):
    ...     print(spec.name)
    extension-manager-upgrades

If all existing specifications are assigned to the 1.0 series,...

    >>> for spec in mozilla.visible_specifications:
    ...     spec.proposeGoal(series_1_0, no_priv)

we have the save five incomplete specs in the series 1.0 as we have for the
project itself.

    >>> filter = [SpecificationFilter.INCOMPLETE]
    >>> for spec in mozilla_series_1_0.specifications(None, filter=filter):
    ...     print(spec.name)
    svg-support
    canvas
    extension-manager-upgrades
    mergewin
    e4x

 Searching for text is also possible.

    >>> for spec in mozilla_series_1_0.specifications(
    ...     None, filter=[u'install']):
    ...     print(spec.name)
    extension-manager-upgrades

Inactive products are excluded from the series listings.

    >>> filter = [SpecificationFilter.INCOMPLETE]
    >>> specs = mozilla_series_1_0.specifications(None, filter=filter)
    >>> print(specs.count())
    5

    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> firefox.active = False
    >>> filter = [SpecificationFilter.INCOMPLETE]
    >>> mozilla_series_1_0.specifications(None, filter=filter).count()
    0

Reset firefox so we don't mess up later tests.

    >>> firefox.active = True

We can get all the specifications via the visible_specifications property,
and all valid specifications via the valid_specifications method:

    >>> for spec in mozilla_series_1_0.visible_specifications:
    ...    print(spec.name)
    svg-support
    canvas
    extension-manager-upgrades
    mergewin
    e4x

    >>> for spec in mozilla_series_1_0.valid_specifications():
    ...    print(spec.name)
    svg-support
    canvas
    extension-manager-upgrades
    mergewin
    e4x


Translatables
-------------

A project would have IProduct objects that have resources to translate. This
method return us the ones that are translatable and officially using Rosetta
to handle translations.

    # Revert any change done until now.
    >>> import transaction
    >>> transaction.abort()

A project group with no translatable products is shown by
'has_translatables' being false.

    >>> product = factory.makeProduct()
    >>> project_group = factory.makeProject()
    >>> product.projectgroup = project_group
    >>> project_group.has_translatable()
    False

GNOME Project is a good example that has translations.
It has one translatable product.

    >>> gnome = getUtility(IProjectGroupSet)['gnome']
    >>> gnome.has_translatable()
    True
    >>> translatables = gnome.translatables
    >>> len(translatables)
    1

And that translatable product is 'Evolution'.

    >>> evolution = translatables[0]
    >>> print(evolution.title)
    Evolution

With its 'trunk' series translatable.

    >>> evo_series = evolution.translatable_series
    >>> len(evo_series)
    1
    >>> evo_trunk = evo_series[0]
    >>> print(evo_trunk.name)
    trunk

That is using Rosetta officially.

    >>> print(evolution.translations_usage.name)
    LAUNCHPAD

GNOME project has also another product, netapplet.

    >>> netapplet = gnome.getProduct('netapplet')
    >>> print(netapplet.title)
    NetApplet

But it was not returned from 'translatables' method because it's not using
Rosetta officially.

    >>> print(netapplet.translations_usage.name)
    UNKNOWN

And thus, it doesn't have any translatable series.

    >>> len(netapplet.translatable_series)
    0

Even if it has resources to translate.

    >>> sum([len(list(series.getTranslationTemplates()))
    ...      for series in netapplet.series])
    1


Milestones
----------

A project can have virtual milestones. If any of its products has milestones,
these milestones are also associated with the project.

ProjectGroup.milestones is a list of all active milestones associated with
a project.

    >>> from lp.registry.tests.test_project_milestone import (
    ...     ProjectMilestoneTest)
    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> login('foo.bar@canonical.com')
    >>> test_helper = ProjectMilestoneTest(helper_only=True)
    >>> test_helper.setUpProjectMilestoneTests()
    >>> gnome = getUtility(IProjectGroupSet)['gnome']
    >>> milestones = gnome.milestones
    >>> for milestone in milestones:
    ...     print(milestone.name, 'active:', milestone.active)
    1.2 active: True
    1.1. active: True
    1.1 active: True

ProjectGroup.all_milestones is a list of all milestones associated with a
project.

    >>> milestones = gnome.all_milestones
    >>> for milestone in milestones:
    ...     print(milestone.name, 'active:', milestone.active)
    2.1.6 active: False
    1.0 active: False
    1.3 active: False
    1.2 active: True
    1.1. active: True
    1.1 active: True

ProjectGroup.getMilestone(name) returns the project milestone with the name
`name' or None, if no milestone with this name exists.

    >>> milestone = gnome.getMilestone('1.1')
    >>> print(milestone.name)
    1.1
    >>> milestone = gnome.getMilestone('invalid')
    >>> print(milestone)
    None

For details see doc/milestone.rst and tests/test_project_milestone.py.
