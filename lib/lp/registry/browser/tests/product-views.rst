=============
Product Pages
=============

The browser module for product has many view classes that should be
tested in this pages test.  As it is this test is pretty sparse.


Product View
============

The page at /product_name includes overview information about the product.


Effective Driver
----------------

The `effective_driver` property on the view shows the product driver,
if one exists.  If the product does not have a driver, then the driver
for the project is returned.  If the product has no project or the
project has no driver then None is returned.

    >>> from lp.testing import ANONYMOUS
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> login("foo.bar@canonical.com")
    >>> mozilla = getUtility(IProjectGroupSet).getByName("mozilla")
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> mark = getUtility(IPersonSet).getByName("mark")

Neither Mozilla nor Firefox has a driver set.

    >>> print(mozilla.driver)
    None
    >>> print(firefox.driver)
    None

Thus the effective driver for Firefox is None.
    >>> view = create_initialized_view(firefox, name="+index")
    >>> print(view.effective_driver)
    None

Setting the driver for the Mozilla project trickles down to Firefox.

    >>> mozilla.driver = mark

But since the effective_driver is a cached property it will not show
up on this view instance.

    >>> print(view.effective_driver)
    None

Creating a new view shows the new driver.

    >>> view = create_initialized_view(firefox, name="+index")
    >>> print(view.effective_driver.name)
    mark

Setting the driver for Firefox shows that it is used for the product,
after a new view is obtained.

    >>> firefox.driver = cprov
    >>> print(view.effective_driver.name)
    mark
    >>> view = create_initialized_view(firefox, name="+index")
    >>> print(view.effective_driver.name)
    cprov


Displaying Commercial Subscription Information
----------------------------------------------

Only project maintainers, Launchpad administrators, and Launchpad
Commercial members are to see commercial subscription information on
the product overview page.

For product maintainers the property is true.  Sample Person
(test@canonical.com) is the owner of the Firefox product.

    >>> login("test@canonical.com")
    >>> view = create_initialized_view(firefox, name="+index")
    >>> print(view.show_commercial_subscription_info)
    True

For Launchpad admins the property is true.

    >>> login("foo.bar@canonical.com")
    >>> view = create_initialized_view(firefox, name="+index")
    >>> print(view.show_commercial_subscription_info)
    True

For Launchpad commercial members the property is true.

    >>> login("commercial-member@canonical.com")
    >>> view = create_initialized_view(firefox, name="+index")
    >>> print(view.show_commercial_subscription_info)
    True

But for a no-privileges user the property is false.

    >>> login("no-priv@canonical.com")
    >>> view = create_initialized_view(firefox, name="+index")
    >>> print(view.show_commercial_subscription_info)
    False

And for an anonymous user it is false.

    >>> login(ANONYMOUS)
    >>> view = create_initialized_view(firefox, name="+index")
    >>> print(view.show_commercial_subscription_info)
    False


Reviewing a project's licensing
===============================

Launchpad admins and members of the registry experts team can review a
project's licences.

The Commercial Admin user is not in the registry admins team so they
cannot access the page.

    >>> login("commercial-member@canonical.com")
    >>> view = create_initialized_view(firefox, name="+index")

    >>> view = create_initialized_view(firefox, name="+review-license")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized:
    (<Product..., 'project_reviewed', 'launchpad.Moderate')

Mark is in the registry admins team and is allowed to access the page.

    >>> login("mark@example.com")
    >>> view = create_initialized_view(firefox, name="+review-license")
    >>> print(view.label)
    Review project

Adding the Commercial Admin to the registry experts team will give
them access.

    >>> commercial_member = getUtility(IPersonSet).getByEmail(
    ...     "commercial-member@canonical.com"
    ... )
    >>> registry_experts = getUtility(IPersonSet).getByName("registry")
    >>> ignored = registry_experts.addMember(commercial_member, reviewer=mark)
    >>> transaction.commit()
    >>> login("commercial-member@canonical.com")
    >>> view = create_initialized_view(firefox, name="+review-license")
    >>> print(view.label)
    Review project

The view allow the reviewer to see and change project privileges and
judge the licences.

    >>> view.field_names
    ['project_reviewed', 'license_approved', 'active', 'reviewer_whiteboard']

The reviewer cannot deactivate a project if it is linked
to a source package.

    >>> firefox.active
    True

    >>> form = {
    ...     "field.active.used": "",  # unchecked
    ...     "field.reviewer_whiteboard": "Looks bogus",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(
    ...     firefox, name="+review-license", form=form
    ... )
    >>> view.errors
    [...This project cannot be deactivated since it is linked to
    ...source packages</a>.']

The reviewer can deactivate a project if they conclude it is bogus.

    >>> product = factory.makeProduct(name="tomato", title="Tomato")
    >>> product.active
    True

    >>> form = {
    ...     "field.active.used": "",  # unchecked
    ...     "field.reviewer_whiteboard": "Looks bogus",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(
    ...     product, name="+review-license", form=form
    ... )
    >>> view.errors
    []
    >>> product.active
    False
    >>> print(product.reviewer_whiteboard)
    Looks bogus

The reviewer can reactivate the project.

    >>> form = {
    ...     "field.active": "on",
    ...     "field.reviewer_whiteboard": "Reinstated old project",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(
    ...     firefox, name="+review-license", form=form
    ... )

    >>> view.errors
    []
    >>> firefox.active
    True
    >>> print(firefox.reviewer_whiteboard)
    Reinstated old project

A project with proprietary licence cannot be approved; the owner must
purchase a commercial subscription.

    >>> from lp.registry.interfaces.product import License

    >>> login("test@canonical.com")
    >>> firefox.licenses = [License.OTHER_PROPRIETARY]

    >>> login("commercial-member@canonical.com")
    >>> firefox.license_approved
    False

    >>> form = {
    ...     "field.active": "on",
    ...     "field.reviewer_whiteboard": "Approved",
    ...     "field.license_approved": "on",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(
    ...     firefox, name="+review-license", form=form
    ... )
    >>> for error in view.errors:
    ...     print(error)
    ...
    Proprietary projects may not be manually approved to use Launchpad.
    Proprietary projects must be granted a commercial subscription
    to be allowed to use Launchpad.
    >>> firefox.license_approved
    False
    >>> print(firefox.reviewer_whiteboard)
    None

A project with additional licence information must be approved by a reviewer.
If the reviewer does not approve the project, just review, the project does
not qualify for free hosting. The owner must purchase a commercial
subscription.

    >>> login("test@canonical.com")
    >>> firefox.licenses = [License.GNU_GPL_V2]
    >>> firefox.license_info = "May not be used for commercial purposes"

    >>> login("commercial-member@canonical.com")
    >>> firefox.license_approved
    False

    >>> form = {
    ...     "field.active": "on",
    ...     "field.reviewer_whiteboard": "This is not a free license",
    ...     "field.project_reviewed": "on",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(
    ...     firefox, name="+review-license", form=form
    ... )
    >>> view.errors
    []
    >>> firefox.project_reviewed
    True
    >>> firefox.license_approved
    False
    >>> firefox.qualifies_for_free_hosting
    False

The owner can correct the licence information and have it re-reviewed for
approval.

    >>> login("test@canonical.com")
    >>> firefox.licenses = [License.GNU_GPL_V2]
    >>> firefox.license_info = "Free as cats."

    >>> login("commercial-member@canonical.com")
    >>> firefox.license_approved
    False

    >>> form = {
    ...     "field.active": "on",
    ...     "field.reviewer_whiteboard": "This is not a free licence",
    ...     "field.license_approved": "on",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(
    ...     firefox, name="+review-license", form=form
    ... )
    >>> view.errors
    []
    >>> firefox.project_reviewed
    True
    >>> firefox.license_approved
    True
    >>> firefox.qualifies_for_free_hosting
    True

If the owner updated the licence by adding an Other/Open Source licences,
the project must be reviewed again

    >>> login("test@canonical.com")
    >>> firefox.licenses = [License.GNU_GPL_V2, License.OTHER_OPEN_SOURCE]
    >>> firefox.license_info = "Some images are cc-sa."

    >>> login("commercial-member@canonical.com")
    >>> firefox.license_approved
    False

    >>> form = {
    ...     "field.active": "on",
    ...     "field.reviewer_whiteboard": "This is not a free license",
    ...     "field.license_approved": "on",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(
    ...     firefox, name="+review-license", form=form
    ... )
    >>> view.errors
    []
    >>> firefox.project_reviewed
    True
    >>> firefox.license_approved
    True
    >>> firefox.qualifies_for_free_hosting
    True


Adding a product series
=======================

Drivers, which include project driver and owners can access the
+addseries view.

    >>> from lp.services.webapp.authorization import check_permission

    >>> ignored = login_person(firefox.owner)
    >>> view = create_view(firefox, name="+addseries")
    >>> check_permission("launchpad.Driver", view)
    True

    >>> firefox.driver = factory.makePerson()
    >>> ignored = login_person(firefox.driver)
    >>> view = create_view(firefox, name="+addseries")
    >>> check_permission("launchpad.Driver", view)
    True

The +addseries view provides a label and a page_title. There is a cancel_url
too.

    >>> print(view.label)
    Register a new Mozilla Firefox release series

    >>> print(view.page_title)
    Register a new Mozilla Firefox release series

    >>> print(view.cancel_url)
    http://launchpad.test/firefox

The view allows the driver to set series name, summary, branch and
releasefileglob fields.

    >>> view.field_names
    ['name', 'summary', 'branch', 'releasefileglob']

    >>> form = {
    ...     "field.name": "master",
    ...     "field.summary": "The primary development series.",
    ...     "field.releasefileglob": "ftp://mozilla.org/firefox.*bz2",
    ...     "field.branch": "",
    ...     "field.actions.add": "Register Series",
    ... }
    >>> view = create_initialized_view(firefox, name="+addseries", form=form)
    >>> print(view.series.name)
    master

    >>> print(view.series.summary)
    The primary development series.

    >>> print(view.series.releasefileglob)
    ftp://mozilla.org/firefox.*bz2


Viewing series for a product
============================

All the product series can be viewed in batches.

    >>> product = factory.makeProduct()
    >>> for name in ("stable", "testing", "1.1", "1.2", "extra"):
    ...     series = factory.makeProductSeries(product=product, name=name)
    ...
    >>> view = create_view(product, name="+series")
    >>> batch = view.batched_series.currentBatch()
    >>> print(batch.total())
    6
    >>> for series in batch:
    ...     print(series.name)
    ...
    trunk
    1.2
    1.1
    testing
    stable


Product index view
==================

+index portlets
---------------

The index page of a product only shows the application portlets that it
officially supports.

    >>> from lp.testing.pages import find_tag_by_id

    >>> product = factory.makeProduct(name="cucumber")
    >>> owner = product.owner
    >>> ignored = login_person(owner)
    >>> question = factory.makeQuestion(target=product)
    >>> faq = factory.makeFAQ(target=product)
    >>> bug = factory.makeBug(target=product)
    >>> blueprint = factory.makeSpecification(product=product)

    >>> view = create_initialized_view(
    ...     product, name="+index", principal=owner
    ... )
    >>> content = find_tag_by_id(view.render(), "maincontent")
    >>> print(find_tag_by_id(content, "portlet-latest-faqs"))
    None
    >>> print(find_tag_by_id(content, "portlet-latest-questions"))
    None
    >>> print(find_tag_by_id(content, "portlet-latest-bugs"))
    None
    >>> print(find_tag_by_id(content, "portlet-blueprints"))
    None

The portlet are rendered when a product officially uses the Launchpad
Answers, Blueprints, and Bugs applications.

    >>> from lp.app.enums import ServiceUsage
    >>> product.answers_usage = ServiceUsage.LAUNCHPAD
    >>> product.blueprints_usage = ServiceUsage.LAUNCHPAD
    >>> product.official_malone = True

    >>> view = create_initialized_view(
    ...     product, name="+index", principal=owner
    ... )
    >>> content = find_tag_by_id(view.render(), "maincontent")
    >>> print(find_tag_by_id(content, "portlet-latest-faqs")["id"])
    portlet-latest-faqs
    >>> print(find_tag_by_id(content, "portlet-latest-questions")["id"])
    portlet-latest-questions
    >>> print(find_tag_by_id(content, "portlet-latest-bugs")["id"])
    portlet-latest-bugs
    >>> print(find_tag_by_id(content, "portlet-blueprints")["id"])
    portlet-blueprints
