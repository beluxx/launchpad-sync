ProductRelease pages
====================

Views that support the ProductRelease object.


Adding a product release
------------------------

A new ProductRelease can be created using ProductReleaseAddView.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> owner = factory.makePerson(name="app-owner")
    >>> product = factory.makeProduct(name="app", owner=owner)
    >>> series = factory.makeProductSeries(name="simple", product=product)
    >>> naked_milestone = removeSecurityProxy(series).newMilestone("0.1")
    >>> print(naked_milestone.active)
    True

The view explains what that the user is creating a release, and lists
the other releases for the series. There are no other releases yet.

    >>> ignored = login_person(owner)
    >>> view = create_initialized_view(naked_milestone, "+addrelease")
    >>> print(view.label)
    Create a new release for App
    >>> print(view.page_title)
    Create a new release for App

The view creates a checkbox to allow the user to keep the milestone
active, which is normally deactivated when a release is made.

    >>> print(view.widgets["keep_milestone_active"].hint)
    Only select this if bugs or blueprints still need to be targeted to this
    project release's milestone.

Submitting the form data creates the release and deactivates the
milestone.

    >>> form = {
    ...     "field.datereleased": "2007-05-11",
    ...     "field.release_notes": "Initial release.",
    ...     "field.changelog": "commits",
    ...     "field.actions.create": "Create release",
    ...     "field.keep_milestone_active.used": "",  # false
    ... }
    >>> view = create_initialized_view(
    ...     naked_milestone, "+addrelease", form=form
    ... )
    >>> print(view.errors)
    []

    >>> print(view.widget_errors)
    {}

    >>> print(naked_milestone.active)
    False

    >>> for release in series.releases:
    ...     print(
    ...         release.version, release.release_notes, release.datereleased
    ...     )
    ...
    0.1 Initial release. 2007-05-11 00:00:00+00:00

    >>> transaction.commit()

Only one release can be created for the milestone.

    >>> view = create_initialized_view(
    ...     naked_milestone, "+addrelease", form=form
    ... )
    >>> for notice in view.request.response.notifications:
    ...     print(notice.message)
    ...
    A project release already exists for this milestone.

The milestone can be kept active when a release is created by submitting
the keep_milestone_active option as 'on' (the value of the checkbox).

    >>> active_milestone = series.newMilestone("0.2")
    >>> print(active_milestone.active)
    True

    >>> form = {
    ...     "field.datereleased": "2007-05-11",
    ...     "field.release_notes": "Initial release.",
    ...     "field.changelog": "commits",
    ...     "field.actions.create": "Create release",
    ...     "field.keep_milestone_active": "on",
    ... }
    >>> view = create_initialized_view(
    ...     active_milestone, "+addrelease", form=form
    ... )
    >>> print(view.errors)
    []

    >>> print(view.widget_errors)
    {}

    >>> view.request.response.notifications
    []

    >>> print(active_milestone.active)
    True


Creating a release for a series
-------------------------------

It is possible to create a release directly from a series, the release's
milestone can be created via an AJAX command.

The view collects the required release fields, and adds fields to to
set the milestone.

    >>> view = create_initialized_view(series, "+addrelease", principal=owner)
    >>> view.field_names
    ['datereleased', 'release_notes', 'changelog']

    >>> [field.__name__ for field in view.form_fields]
    ['milestone_for_release', 'keep_milestone_active', 'datereleased',
     'release_notes', 'changelog']
    >>> print(view.label)
    Create a new release for App
    >>> print(view.page_title)
    Create a new release for App

The rendered template includes a script that adds a js-action link to
show a formoverlay that updates the milestone_for_release field.

    >>> from lp.testing.pages import find_tag_by_id

    >>> script = find_tag_by_id(view.render(), "milestone-script")
    >>> print(script)
    <script id="milestone-script" type="text/javascript">
        LPJS.use(... 'lp.registry.milestoneoverlay'...
            var milestone_form_uri = '.../app/simple/+addmilestone/++form++';
            var series_uri = '/app/simple';
            ...
            Y.on('domready', function () {
                var select_menu = get_by_id('field.milestone_for_release');
                var create_milestone_link = Y.Node.create(
                    '<a href="+addmilestone" id="create-milestone-link" ' +
                    'class="add js-action sprite">Create milestone</a>'); ...


Editing a a product release
---------------------------

A ProductRelease can be edited using the ProductReleaseEditView.

    >>> release = series.getRelease("0.1")
    >>> print(release.release_notes)
    Initial release.

    >>> form = {
    ...     "field.datereleased": "2007-05-11",
    ...     "field.release_notes": "revised",
    ...     "field.changelog": "commits",
    ...     "field.actions.change": "Change",
    ... }
    >>> view = create_initialized_view(release, "+edit", form=form)
    >>> print(view.label)
    Edit App 0.1 release details

    >>> print(view.page_title)
    Edit App 0.1 release details

    >>> print(view.errors)
    []

    >>> print(view.widget_errors)
    {}

    >>> print(release.release_notes)
    revised


Product release menus
---------------------

The ProductReleaseContextMenu is used to manage links to the work with
a product release.

    >>> from lp.registry.browser.productrelease import (
    ...     ProductReleaseContextMenu,
    ... )
    >>> from lp.testing.menu import check_menu_links

    >>> check_menu_links(ProductReleaseContextMenu(release))
    True


Adding a download file to a release
-----------------------------------

    >>> form = {
    ...     "field.description": "App 0.1 tarball",
    ...     "field.contenttype": "CODETARBALL",
    ...     "field.actions.add": "Upload",
    ... }
    >>> view = create_initialized_view(release, "+adddownloadfile", form=form)
    >>> print(view.label)
    Add a download file to App 0.1

    >>> print(view.page_title)
    Add a download file to App 0.1


Deleting a product release
--------------------------

    >>> form = {
    ...     "field.actions.delete": "Delete Release",
    ... }
    >>> view = create_initialized_view(release, "+delete", form=form)
    >>> print(view.label)
    Delete App 0.1

    >>> print(view.page_title)
    Delete App 0.1

    >>> print(view.errors)
    []

    >>> print(view.widget_errors)
    {}

    >>> release = series.getRelease("0.1")
    >>> print(release)
    None
