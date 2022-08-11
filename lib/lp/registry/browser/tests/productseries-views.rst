ProductSeries Views
===================

ProductSeries menus
-------------------

The ProductSeriesOverviewMenu provides the links to the common ProductSeries
views.

    >>> from lp.registry.browser.productseries import (
    ...     ProductSeriesOverviewMenu)
    >>> from lp.testing.menu import check_menu_links

    >>> product = factory.makeProduct(name='app')
    >>> series = factory.makeProductSeries(name='simple', product=product)
    >>> check_menu_links(ProductSeriesOverviewMenu(series))
    True


ProductSeries Involvement links
...............................

The ProductSeries involvement view uses the ProductSeriesInvolvedMenu when
rendering links:

    >>> from lp.app.enums import ServiceUsage
    >>> ignored = login_person(product.owner)
    >>> product.answers_usage = ServiceUsage.LAUNCHPAD
    >>> product.blueprints_usage = ServiceUsage.LAUNCHPAD
    >>> product.official_malone = True
    >>> product.translations_usage = ServiceUsage.LAUNCHPAD
    >>> view = create_view(series, '+get-involved')

    # answers_usage is never LAUNCHPAD for product series.
    >>> print(view.answers_usage.name)
    NOT_APPLICABLE
    >>> print(view.blueprints_usage.name)
    LAUNCHPAD
    >>> print(view.official_malone)
    True
    >>> print(view.translations_usage.name)
    LAUNCHPAD
    >>> print(view.codehosting_usage.name)
    UNKNOWN

    >>> for link in view.enabled_links:
    ...     print(link.url)
    http://bugs.launchpad.test/app/simple/+filebug
    http://translations.launchpad.test/app/simple
    http://blueprints.launchpad.test/app/simple/+addspec


ProductSeries view
------------------

The default view for the productseries includes a script that augments the
'Create milestone' link to show a formoverlay to create a milestone and
update the milestones and releases table.

    >>> from lp.testing.pages import find_tag_by_id

    >>> login('foo.bar@canonical.com')
    >>> view = create_view(series, '+index', principal=product.owner)
    >>> script = find_tag_by_id(view.render(), 'milestone-script')
    >>> print(script)
    <script id="milestone-script" type="text/javascript">
        LPJS.use(... 'lp.registry.milestoneoverlay',
                      'lp.registry.milestonetable'...
            var series_uri = '/app/simple';
            var milestone_form_uri = '.../app/simple/+addmilestone/++form++';
            var milestone_row_uri =
                '/app/+milestone/{name}/+productseries-table-row';
            var milestone_rows_id = '#milestone-rows';...
            Y.on('domready', function () {
                var create_milestone_link = Y.one(
                    '.menu-link-create_milestone');
                create_milestone_link.addClass('js-action');...
                Y.lp.registry.milestoneoverlay.attach_widget(config);...
                Y.lp.registry.milestonetable.setup(table_config);...

If the Create milestone link is not enabled, the script is not present.

    >>> a_user = factory.makePerson(name="hedgehog")
    >>> ignored = login_person(a_user)
    >>> view = create_view(series, '+index', principal=a_user)
    >>> content = view.render()
    >>> print(find_tag_by_id(content, 'milestone-script'))
    None
    >>> 'var milestone_form_uri' in content
    False

The view also sets the class of the milestone and releases table which can
be removed by the in-page script. If the product series has no milestones,
the class table is 'listing hidden'.

    >>> ignored = login_person(product.owner)
    >>> view = create_view(series, '+index', principal=product.owner)
    >>> print(view.milestone_table_class)
    listing hidden

    >>> table = find_tag_by_id(view.render(), 'series-simple')
    >>> print(' '.join(table['class']))
    listing hidden

When the product series has milestones, the class is just 'listing'.

    >>> milestone = series.newMilestone('12', code_name='twelve')
    >>> view = create_view(series, '+index')
    >>> print(view.milestone_table_class)
    listing

Obsolete series are less interesting that other series. The ProductSeriesView
has an is_obsolete property that templates can check when choosing the content
to display.

    >>> from lp.registry.interfaces.series import SeriesStatus

    >>> print(series.status.title)
    Active Development
    >>> view.is_obsolete
    False

    >>> series.status = SeriesStatus.OBSOLETE
    >>> view = create_view(series, '+index')
    >>> view.is_obsolete
    True

The view provides access to the latest release if it has one.

    >>> from lp.registry.interfaces.product import IProductSet

    >>> print(view.latest_release_with_download_files)
    None

    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> series_with_downloads = firefox.getSeries('trunk')
    >>> view = create_initialized_view(series_with_downloads, name='+index')
    >>> print(view.latest_release_with_download_files.version)
    0.9.2

The view also provides a link to register a new code import.

    >>> print(view.request_import_link)
    http://code.launchpad.test/firefox/+new-import


Edit ProductSeries
------------------

The productseries +edit view provides a label and page_title for the page.

    >>> view = create_initialized_view(series, '+edit')
    >>> print(view.label)
    Edit App simple series

    >>> print(view.page_title)
    Edit App simple series

The view provides a cancel_url and a next_url.

    >>> print(view.cancel_url)
    http://launchpad.test/app/simple

    >>> print(view.next_url)
    http://launchpad.test/app/simple


Administer Productseries
------------------------

The productseries +review view allows an admin to administer the name and
parent project.

    >>> from lp.services.webapp.authorization import check_permission

    >>> login('admin@canonical.com')
    >>> view = create_initialized_view(series, '+review')
    >>> check_permission('launchpad.Admin', view)
    True

    >>> view.field_names
    ['product', 'name']

The view provides a label and page_title.

    >>> print(view.label)
    Administer App simple series

    >>> print(view.page_title)
    Administer App simple series

The view provides a cancel_url and a next_url.

    >>> print(view.cancel_url)
    http://launchpad.test/app/simple

Users without edit permission cannot access the view.

    >>> ignored = login_person(a_user)
    >>> view = create_view(series, name='+review')
    >>> check_permission('launchpad.Admin', view)
    False


Delete ProductSeries
--------------------

Users with edit permission may delete a project's series. This person is
often the project's owner or series driver who has setup the series by
mistake.

    >>> from datetime import datetime
    >>> from pytz import UTC
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> celebrities = getUtility(ILaunchpadCelebrities)

    >>> test_date = datetime(2009, 5, 1, 19, 34, 24, tzinfo=UTC)
    >>> product = factory.makeProduct(name="field", displayname='Field')
    >>> productseries = factory.makeProductSeries(
    ...     product=product, name='rabbit', date_created=test_date)
    >>> ignored = login_person(celebrities.admin.teamowner)
    >>> productseries.releasefileglob = 'http://eg.dom/rabbit/*'

Users without edit permission cannot access the view.

    >>> from lp.services.webapp.authorization import check_permission

    >>> login('no-priv@canonical.com')
    >>> view = create_view(productseries, name='+delete')
    >>> check_permission('launchpad.Edit', view)
    False

The project owner can access the view.

    >>> ignored = login_person(product.owner)
    >>> view = create_view(productseries, name='+delete')
    >>> check_permission('launchpad.Edit', view)
    True

Registry experts can also access the view.

    >>> ignored = login_person(celebrities.registry_experts.teamowner)
    >>> check_permission('launchpad.Edit', view)
    True

The delete view has a label and page_title to explain what it does.

    >>> print(view.label)
    Delete Field rabbit series

    >>> print(view.page_title)
    Delete Field rabbit series

The view has a a next_url to the product used when the delete is successful,
though it is None by default. There is a cancel_url that links to the series.

    >>> print(view.next_url)
    None

    >>> print(view.cancel_url)
    http://launchpad.test/field/rabbit

There are helper properties that list the associates objects with the
series, the most important of which are milestones. Bugtasks and
specifications that will be unassigned, and release files that will be
deleted are available.

    >>> list(view.milestones)
    []
    >>> view.bugtasks
    []
    >>> view.specifications
    []
    >>> view.product_release_files
    []
    >>> view.has_linked_branch
    False

Most series that are deleted do not have any related objects, but a small
portion do.

    >>> milestone_one = productseries.newMilestone('0.1', code_name='one')
    >>> release_one = milestone_one.createProductRelease(
    ...     product.owner, test_date)
    >>> milestone_one.active = False
    >>> milestone_two = productseries.newMilestone('0.2', code_name='two')
    >>> specification = factory.makeSpecification(product=product)
    >>> specification.milestone = milestone_one
    >>> bug = factory.makeBug(target=product)
    >>> bugtask = bug.bugtasks[0]
    >>> bugtask.milestone = milestone_two

    >>> owner = product.owner
    >>> series_specification = factory.makeSpecification(product=product)
    >>> series_specification.proposeGoal(productseries, owner)
    >>> series_bugtask = factory.makeBugTask(bug=bug, target=productseries)
    >>> subscription = productseries.addSubscription(owner, owner)
    >>> filter = subscription.newBugFilter()
    >>> productseries.branch = factory.makeBranch()

    >>> view = create_view(productseries, name='+delete')
    >>> for milestone in view.milestones:
    ...     print(milestone.name)
    0.2
    0.1
    >>> view.has_bugtasks_and_specifications
    True
    >>> for bugtask in view.bugtasks:
    ...     if bugtask.milestone is not None:
    ...         print(bugtask.milestone.name)
    ...     else:
    ...         print(bugtask.target.name)
    rabbit
    0.2
    >>> for spec in view.specifications:
    ...     if spec.milestone is not None:
    ...         print(spec.milestone.name)
    ...     else:
    ...         print(spec.goal.name)
    rabbit
    0.1

    >>> view.has_linked_branch
    True

    # Listing and deleting product release files is done in
    # product-release-views because they require the Librarian to be running.

Series that are the active focus of development cannot be deleted. The
view's can_delete property checks this rule.

    >>> productseries.is_development_focus
    False
    >>> view.can_delete
    True

    >>> active_series = product.getSeries('trunk')
    >>> active_series.is_development_focus
    True
    >>> active_view = create_view(active_series, '+delete')
    >>> active_view.can_delete
    False

The delete action will not delete a series that is the active focus of
development.

    >>> form = {
    ...     'field.actions.delete': 'Delete this Series',
    ...     }
    >>> active_view = create_initialized_view(
    ...     active_series, '+delete', form=form)
    >>> for error in active_view.errors:
    ...     print(error)
    You cannot delete a series that is the focus of development. Make another
    series the focus of development before deleting this one.
    >>> print(active_series.product.name)
    field

The delete action will not delete a series that is linked to a package.

    >>> from lp.registry.interfaces.packaging import (
    ...     IPackagingUtil, PackagingType)

    >>> sourcepackagename = factory.makeSourcePackageName('sausage')
    >>> distro_series = factory.makeDistroSeries()
    >>> linked_series = factory.makeProductSeries(product=product)
    >>> packaging = getUtility(IPackagingUtil).createPackaging(
    ...     linked_series, sourcepackagename, distro_series,
    ...     PackagingType.PRIME, owner=owner)
    >>> linked_view = create_initialized_view(linked_series, '+delete')

    >>> linked_view.has_linked_packages
    True

    >>> linked_view.can_delete
    False

    >>> form = {
    ...     'field.actions.delete': 'Delete this Series',
    ...     }
    >>> linked_view = create_initialized_view(
    ...     linked_series, '+delete', form=form)
    >>> for error in linked_view.errors:
    ...     print(error)
    You cannot delete a series that is linked to packages in distributions.
    You can remove the links from the <a ...>project packaging</a> page.


Calling the view's delete action on a series that can be deleted will
untarget the bugtasks and specifications that are targeted to the
series' milestones. The milestones, releases, and release files are
deleted. Bugs and blueprints targeted to the series are unassigned.
Series structural subscriptions are removed. Branch links are removed.

    >>> view = create_initialized_view(productseries, '+delete', form=form)
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    Series rabbit deleted.

    >>> print(view.next_url)
    http://launchpad.test/field
    >>> [milestone for milestone in product.all_milestones]
    []
    >>> [release for release in  product.releases]
    []
    >>> print(specification.milestone)
    None
    >>> print(bugtask.milestone)
    None
    >>> bugtask.related_tasks
    []
    >>> print(series_specification.milestone)
    None
    >>> [subscription for subscription in owner.structural_subscriptions]
    []

The series was not actually deleted because there are problematic objects
like translations. The series are assigned to the Obsolete Junk project.
The series name is changed to 'product_name-series_name-date_created' to
avoid conflicts. The linked branch is removed.

    >>> from zope.component import getUtility

    >>> obsolete_junk = celebrities.obsolete_junk
    >>> productseries.product == obsolete_junk
    True
    >>> print(productseries.name)
    field-rabbit-20090501-193424

The series status is set to obsolete and the releasefileglob was set to None.

    >>> print(productseries.status.title)
    Obsolete
    >>> print(productseries.releasefileglob)
    None

A series cannot be deleted if it is has translation templates.

    >>> translated_series = factory.makeProductSeries(product=product)
    >>> product.translations_usage = ServiceUsage.LAUNCHPAD
    >>> po_template = factory.makePOTemplate(
    ...     name='gibberish', productseries=translated_series)
    >>> translated_view = create_initialized_view(
    ...     translated_series, '+delete')
    >>> translated_view.has_translations
    True

    >>> translated_view.can_delete
    False

    >>> form = {
    ...     'field.actions.delete': 'Delete this Series',
    ...     }
    >>> translated_view = create_initialized_view(
    ...     translated_series, '+delete', form=form)
    >>> for error in translated_view.errors:
    ...     print(error)
    This series cannot be deleted because it has translations.

The view reports all the reason why a series cannot be deleted.

    >>> sourcepackagename = factory.makeSourcePackageName('tomato')
    >>> packaging = getUtility(IPackagingUtil).createPackaging(
    ...     active_series, sourcepackagename, distro_series,
    ...     PackagingType.PRIME, owner=owner)
    >>> po_template = factory.makePOTemplate(
    ...     name='gibberish', productseries=active_series)
    >>> form = {
    ...     'field.actions.delete': 'Delete this Series',
    ...     }
    >>> view = create_initialized_view(active_series, '+delete', form=form)
    >>> for error in view.errors:
    ...     print(error)
    You cannot delete a series that is the focus of development. Make another
    series the focus of development before deleting this one.
    You cannot delete a series that is linked to packages in distributions.
    You can remove the links from the <a ...>project packaging</a> page.
    This series cannot be deleted because it has translations.
