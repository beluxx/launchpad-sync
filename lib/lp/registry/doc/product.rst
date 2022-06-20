Product
=======

Launchpad keeps track of the "upstream" world as well as the "distro" world.
The anchorpiece of the "upstream" world is the Product, which is a piece of
software. It can be part of a ProjectGroup or it can be standalone.

    >>> from zope.component import getUtility
    >>> from lp.app.errors import NotFoundError
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import (
    ...     IProduct,
    ...     IProductSet,
    ...     )
    >>> from lp.translations.interfaces.hastranslationimports import (
    ...     IHasTranslationImports)
    >>> from lp.testing import login
    >>> from lp.testing import verifyObject

Let's log in as Foo Bar to ensure we have the privileges to do what we're
going to demonstrate.

    >>> login("foo.bar@canonical.com")

Now lets get the utility we use to interact with sets of products.

    >>> productset = getUtility(IProductSet)

We also need to do some setup for other tests, which need alsa-utils
configured for services.

    >>> from lp.app.enums import ServiceUsage
    >>> evolution = getUtility(IProductSet).getByName('evolution')
    >>> evolution.translations_usage = ServiceUsage.LAUNCHPAD
    >>> alsa = getUtility(IProductSet).getByName('alsa-utils')
    >>> alsa.translations_usage = ServiceUsage.LAUNCHPAD
    >>> transaction.commit()

Verify that p (a Product object) correctly implements IProduct.

    >>> p = productset.get(5)
    >>> verifyObject(IProduct, p)
    True

and IHasTranslationImports.

    >>> verifyObject(IHasTranslationImports, p)
    True

Make sure that a product provides the IProduct interface.

    >>> IProduct.providedBy(p)
    True

and the IHasTranslationImports.

    >>> IHasTranslationImports.providedBy(p)
    True

Let's get a product from the sample data. We happen to know that product
with id 5 should be evolution:

    >>> print(p.name)
    evolution

Let's call that evo from now onwards just so the tests can be clearer.

    >>> evo = p

To fetch a product we use IProductSet.getByName() or IProductSet.__getitem__.
The former will, by default, return active and inactive products, while the
later returns only active ones. Both can be used to look up products by their
aliases, though.

    >>> a52dec = productset.getByName('a52dec')
    >>> print(a52dec.name)
    a52dec
    >>> print(productset['a52dec'].name)
    a52dec

    >>> a52dec.setAliases(['a51dec'])
    >>> for alias in a52dec.aliases:
    ...     print(alias)
    a51dec
    >>> print(productset['a51dec'].name)
    a52dec
    >>> print(productset.getByName('a51dec').name)
    a52dec

Since we have some POTemplates for evolution, we should have a primary
translatable for that product:

    >>> print(evo.primary_translatable.displayname)
    trunk

We can also see how many translatables it has:

    >>> for series in evo.translatable_series:
    ...     print(series.displayname)
    trunk

But for a52dec, where we have no translatable series or Ubuntu package, the
primary_translatable is nonexistent:

    >>> print(a52dec.primary_translatable)
    None

Now, to test the active flag. If we disabled a product:

    # Unlink the source packages so the project can be deactivated.
    >>> from lp.testing import unlink_source_packages
    >>> unlink_source_packages(a52dec)
    >>> a52dec.active = False

It should no longer be retrievable via ProductSet's __getitem__:

    >>> try:
    ...   productset[a52dec.name]
    ... except NotFoundError:
    ...   pass

But it should be retrievable via getByname().

    >>> print(productset.getByName('a52dec').name)
    a52dec

getByName() also accepts an argument to ignore inactive products.

    >>> print(productset.getByName('a52dec', ignore_inactive=True))
    None

You can also use the IProductSet to see some statistics on products.
The methods use ILaunchpadStatisticSet to get the values. The
ILaunchpadStatisticSet is stored in the 'stats' attribute.

    >>> class FakeStatistics:
    ...     stats = {
    ...         'products_with_translations': 1000,
    ...         'projects_with_bugs': 2000,
    ...         'reviewed_products': 3000}
    ...     def value(self, name):
    ...         return self.stats[name]

    >>> from lp.registry.model.product import ProductSet
    >>> class FakeStatsProductSet(ProductSet):
    ...     """Provide fake statistics, not to depend on sample data."""
    ...     stats = FakeStatistics()

    >>> print(FakeStatsProductSet().count_translatable())
    1000
    >>> print(FakeStatsProductSet().count_buggy())
    2000
    >>> print(FakeStatsProductSet().count_reviewed())
    3000

IProductSet can also retrieve the latest products registered.  By
default the latest five are returned.

    >>> latest = productset.latest(None)
    >>> projects = [project.displayname for project in latest]
    >>> for project in sorted(projects):
    ...     print(project)
    Bazaar
    Derby
    Mega Money Maker
    Obsolete Junk
    Redfish

The quantity can be specified and that many, if available, will be
returned.

    >>> latest = productset.latest(None, quantity=3)
    >>> projects = [project.displayname for project in latest]
    >>> for project in sorted(projects):
    ...     print(project)
    Derby
    Mega Money Maker
    Obsolete Junk


Translatable Products
---------------------

IProductSet will also tell us which products can be translated:

    >>> for product in productset.getTranslatables():
    ...    print(product.name)
    evolution
    alsa-utils

Only active products are listed as translatables.

    # Unlink the source packages so the project can be deactivated.
    >>> from lp.testing import unlink_source_packages
    >>> unlink_source_packages(evo)
    >>> evo.active = False
    >>> for product in productset.getTranslatables():
    ...    print(product.name)
    alsa-utils

    >>> evo.active = True


Package links
-------------

The packaging table allows us to list source and distro source packages
related to a certain upstream:

    >>> alsa = productset.getByName('alsa-utils')
    >>> for sp in alsa.sourcepackages:
    ...     print(sp.name, sp.distroseries.name)
    alsa-utils sid
    alsa-utils warty
    >>> for sp in alsa.distrosourcepackages:
    ...     print(sp.name, sp.distribution.name)
    alsa-utils debian
    alsa-utils ubuntu

For convenience, you can get just the distro source packages for Ubuntu.

    >>> for sp in alsa.ubuntu_packages:
    ...     print(sp.name, sp.distribution.name)
    alsa-utils ubuntu


External Bug Tracker
--------------------

If a product doesn't use Malone, it can specify that it uses an
external bug tracker. It can either use its own bug tracker, or use its
project group's bug tracker. In order to make this logic easier for call
sites, there is a method that takes care of it called
getExternalBugTracker.


Firefox uses Malone as it's bug tracker, so it can't have an external
one.

    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> firefox.bug_tracking_usage
    <DBItem ServiceUsage.LAUNCHPAD, (20) Launchpad>
    >>> print(firefox.bug_tracking_usage.name)
    LAUNCHPAD
    >>> firefox.getExternalBugTracker() is None
    True

This is true even if its project group has a bug tracker specified.

    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerSet

    >>> ignored = login_person(firefox.owner)
    >>> bug_tracker_set = getUtility(IBugTrackerSet)
    >>> gnome_bugzilla = bug_tracker_set.getByName('gnome-bugzilla')
    >>> firefox.projectgroup.bugtracker = gnome_bugzilla
    >>> firefox.getExternalBugTracker() is None
    True

Now, if we say that Firefox doesn't use Malone, its project group's bug
tracker will be returned.

    >>> firefox.official_malone = False
    >>> firefox.bugtracker is None
    True
    >>> print(firefox.bug_tracking_usage.name)
    UNKNOWN
    >>> print(firefox.getExternalBugTracker().name)
    gnome-bugzilla


If Firefox isn't happy with its project group's bug tracker it can choose to
specify its own.

    >>> debbugs = getUtility(IBugTrackerSet).getByName('debbugs')
    >>> firefox.bugtracker = debbugs
    >>> print(firefox.getExternalBugTracker().name)
    debbugs
    >>> print(firefox.bug_tracking_usage.name)
    EXTERNAL


If neither the project group nor the product have specified a bug tracker,
None will of course be returned.

    >>> firefox.projectgroup.bugtracker = None
    >>> firefox.bugtracker = None
    >>> firefox.getExternalBugTracker() is None
    True


Answer Tracking
---------------

Firefox uses the Answer Tracker as the official application to provide
answers to questions.

    >>> print(firefox.answers_usage.name)
    LAUNCHPAD

Alsa does not use Launchpad to track answers.

    >>> print(alsa.answers_usage.name)
    UNKNOWN

Product Creation
----------------

We can create new products with the createProduct() method:

    >>> from lp.registry.interfaces.product import License
    >>> owner = getUtility(IPersonSet).getByEmail('test@canonical.com')
    >>> product = productset.createProduct(
    ...     owner=owner,
    ...     name='test-product',
    ...     display_name='Test Product',
    ...     title='Test Product',
    ...     summary='A test product',
    ...     description='A description of the test product',
    ...     licenses=(License.GNU_GPL_V2,))

    >>> verifyObject(IProduct, product)
    True

When creating a product, a default product series is created for it:

    >>> product.series.count()
    1
    >>> trunk = product.series[0]
    >>> print(trunk.name)
    trunk

This series is set as the development focus for the product:

    >>> product.development_focus == trunk
    True


Specification Listings
----------------------

We should be able to set whether or not a Product uses specifications
officially.  It defaults to UNKNOWN.

    >>> firefox = productset.getByName('firefox')
    >>> print(firefox.blueprints_usage.name)
    UNKNOWN

We can change it to use LAUNCHPAD.

    >>> from lp.app.enums import ServiceUsage
    >>> firefox.blueprints_usage = ServiceUsage.LAUNCHPAD
    >>> print(firefox.blueprints_usage.name)
    LAUNCHPAD

We should be able to get lists of specifications in different states
related to a product.

Basically, we can filter by completeness, and by whether or not the spec is
informational.

    >>> firefox = productset.getByName('firefox')
    >>> from lp.blueprints.enums import SpecificationFilter

First, there should be only one informational spec for firefox:

    >>> filter = [SpecificationFilter.INFORMATIONAL]
    >>> for spec in firefox.specifications(None, filter=filter):
    ...    print(spec.name)
    extension-manager-upgrades


There are no completed specs for firefox:

    >>> filter = [SpecificationFilter.COMPLETE]
    >>> for spec in firefox.specifications(None, filter=filter):
    ...    print(spec.name)


And there are five incomplete specs:

    >>> filter = [SpecificationFilter.INCOMPLETE]
    >>> firefox.specifications(None, filter=filter).count()
    5

We can filter for specifications that contain specific text:

    >>> for spec in firefox.specifications(None, filter=[u'new']):
    ...     print(spec.name)
    canvas
    e4x


Milestones
----------

We can use IProduct.milestones to get all milestones associated with any
ProductSeries of a product.

    >>> for milestone in firefox.milestones:
    ...     print(milestone.name)
    1.0

Milestones for products can only be created by product/project group owners,
registry experts, or admins.

    >>> from datetime import datetime

    >>> firefox_one_zero = firefox.getSeries('1.0')
    >>> product_owner_email = firefox.owner.preferredemail.email
    >>> login(product_owner_email)
    >>> firefox_milestone = firefox_one_zero.newMilestone(
    ...     name='1.0-rc1', dateexpected=datetime(2018, 10, 1))

They're ordered by dateexpected.

    >>> for milestone in firefox.milestones:
    ...     print('%-7s %s' % (milestone.name, milestone.dateexpected))
    1.0     2056-10-16
    1.0-rc1 2018-10-01

Only milestones which have active=True are returned by the .milestones
property.

    >>> firefox_milestone.active = False
    >>> for milestone in firefox.milestones:
    ...     print(milestone.name)
    1.0

To get all milestones of a given product we have the .all_milestones property.

    >>> for milestone in firefox.all_milestones:
    ...     print(milestone.name)
    1.0.0
    0.9.2
    0.9.1
    0.9
    1.0
    1.0-rc1


Release
-------

All the releases for a Product can be retrieved through the releases property.

    >>> for release in firefox.releases:
    ...     print(release.version)
    0.9
    0.9.1
    0.9.2
    1.0.0

A single release can be retrieved via the getRelease() method by passing the
version argument.

    >>> release = firefox.getRelease('0.9.1')
    >>> print(release.version)
    0.9.1


Products With Branches
----------------------

Products are considered to officially support Launchpad as a location
for their branches after a branch is set for the development focus
series.

    >>> print(firefox.development_focus.branch)
    None
    >>> print(firefox.official_codehosting)
    False
    >>> print(firefox.codehosting_usage.name)
    UNKNOWN
    >>> firefox.development_focus.branch = factory.makeBranch(product=firefox)
    >>> print(firefox.official_codehosting)
    True
    >>> print(firefox.codehosting_usage.name)
    LAUNCHPAD

We can also find all the products that have branches.

    >>> productset.getProductsWithBranches().count()
    6
    >>> for product in productset.getProductsWithBranches():
    ...     print(product.name)
    evolution
    firefox
    gnome-terminal
    iso-codes
    landscape
    thunderbird

Only products that have "active" branches are returned in the query.
Branches that are either Merged or Abandoned are not considered active.

By marking all of Thunderbird's branches as Abandoned, thunderbird will
no longer appear in the result set.

    >>> from lp.code.enums import BranchLifecycleStatus
    >>> from lp.code.interfaces.branchcollection import (
    ...     IAllBranches)
    >>> thunderbird_branches = getUtility(IAllBranches).inProduct(
    ...     productset.getByName('thunderbird')).getBranches()

    # Only an owner, admin, or a bazaar expert can set the
    # branch.lifecycle_status.
    >>> login('foo.bar@canonical.com')
    >>> for branch in thunderbird_branches:
    ...     branch.lifecycle_status = BranchLifecycleStatus.ABANDONED

    >>> for product in productset.getProductsWithBranches():
    ...     print(product.name)
    evolution
    firefox
    gnome-terminal
    iso-codes
    landscape

The getProductsWithBranches method takes an optional parameter that limits
the number of products returned.

    >>> for product in productset.getProductsWithBranches(3):
    ...     print(product.name)
    evolution
    firefox
    gnome-terminal

Only active products are returned.

    >>> evo.active = False
    >>> for product in productset.getProductsWithBranches():
    ...     print(product.name)
    firefox
    gnome-terminal
    iso-codes
    landscape


Products with Git repositories
------------------------------

Products are considered to officially support Launchpad as a location for
their code if they have a default Git repository.

    >>> from lp.code.interfaces.gitrepository import IGitRepositorySet
    >>> firefox.development_focus.branch = None
    >>> print(firefox.official_codehosting)
    False
    >>> print(firefox.codehosting_usage.name)
    UNKNOWN
    >>> getUtility(IGitRepositorySet).setDefaultRepository(
    ...     firefox, factory.makeGitRepository(target=firefox))
    >>> print(firefox.official_codehosting)
    True
    >>> print(firefox.codehosting_usage.name)
    LAUNCHPAD


Primary translatable
--------------------

Primary translatable series in a product should follow series where
development is focused on.  To be able to do changes to facilitate
testing this, we need to log in as a translations administrator.

    >>> login('carlos@canonical.com')
    >>> translations_admin = getUtility(IPersonSet).getByEmail(
    ...     'carlos@canonical.com')

We'll also create new templates, so we need IPOTemplateSet:

    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> potemplate_set = getUtility(IPOTemplateSet)

We're going to be setting the ServiceUsage values for products, so we
need those enums.

    >>> from lp.app.enums import ServiceUsage

Firefox has two series, but no translatable series either:

    >>> firefox = productset.getByName('firefox')
    >>> for firefoxseries in firefox.series:
    ...     print('%s %s' % (
    ...         firefoxseries.displayname,
    ...         list(firefoxseries.getCurrentTranslationTemplates())))
    1.0 []
    trunk []
    >>> print(firefox.primary_translatable)
    None

Development focus series for Firefox is trunk.

    >>> firefox_trunk = firefox.development_focus
    >>> print(firefox_trunk.displayname)
    trunk

But, there's also a 1.0 series for Firefox.

    >>> firefox_10 = firefox.getSeries('1.0')

We can create and associate a new potemplate with Firefox 1.0.

    >>> potemplatesubset = potemplate_set.getSubset(
    ...     productseries=firefox_10)
    >>> firefox_10_pot = potemplatesubset.new('firefox',
    ...                                       'firefox',
    ...                                       'firefox.pot',
    ...                                       translations_admin)

And set that product as using translations officially. We need it so
translations are available.

    >>> firefox.translations_usage = ServiceUsage.LAUNCHPAD

The primary_translatable now points at firefox 1.0:

    >>> print(firefox.primary_translatable.displayname)
    1.0

If we associate a potemplate with Firefox trunk, it will become the primary
translatable because it's a series with development focus.

    >>> potemplatesubset = potemplate_set.getSubset(
    ...     productseries=firefox_trunk)
    >>> firefox_trunk_pot = potemplatesubset.new('firefox',
    ...                                          'firefox',
    ...                                          'firefox.pot',
    ...                                          translations_admin)
    >>> print(firefox.primary_translatable.displayname)
    trunk

If we change the development_focus, primary_translatable changes as well.

    >>> firefox.development_focus = firefox_10
    >>> print(firefox.primary_translatable.displayname)
    1.0


Series list
===========

The series for a product are returned as a sorted list, with the
exception that the current development focus is first.

    >>> firefox_view = create_initialized_view(firefox, '+index')
    >>> sorted_series = firefox_view.sorted_series_list
    >>> for series in sorted_series:
    ...     print(series.name)
    1.0
    trunk

Change the development focus and the sort order changes.  Since the
view is using cached data for the product we must re-instantiate the
view to see the data change reflected.

    >>> first_series = firefox.getSeries(sorted_series[-1].name)
    >>> firefox.development_focus = first_series
    >>> firefox_view = create_initialized_view(firefox, '+index')
    >>> sorted_series = firefox_view.sorted_series_list
    >>> for series in sorted_series:
    ...     print(series.name)
    trunk
    1.0

It is also possible to view just the set of sorted active series.

    >>> firefox_view = create_initialized_view(firefox, '+index')
    >>> sorted_series = firefox_view.sorted_active_series_list
    >>> for series in sorted_series:
    ...     print(series.name)
    trunk
    1.0

Once the 1.0 series is made obsolete, it no longer shows up in the set of
sorted active series.

    >>> from lp.registry.interfaces.series import SeriesStatus
    >>> sorted_series = firefox_view.sorted_active_series_list
    >>> last_series = firefox.getSeries(sorted_series[-1].name)
    >>> last_series.status = SeriesStatus.OBSOLETE
    >>> firefox_view = create_initialized_view(firefox, '+index')
    >>> for series in firefox_view.sorted_active_series_list:
    ...     print(series.name)
    trunk

It is possible for the development series to be obsolete, and in that case, it
still shows up in the list.

    >>> firefox.development_focus.status = SeriesStatus.OBSOLETE
    >>> firefox_view = create_initialized_view(firefox, '+index')
    >>> for series in firefox_view.sorted_active_series_list:
    ...     print(series.name)
    trunk


Changing ownership
==================

A product owner can be changed by the current owner.

    >>> print(firefox.owner.name)
    name12

    >>> mark = getUtility(IPersonSet).getByEmail('mark@example.com')
    >>> print(mark.name)
    mark

    >>> ignored = login_person(firefox.owner)
    >>> firefox.owner = mark

    >>> print(firefox.owner.name)
    mark
