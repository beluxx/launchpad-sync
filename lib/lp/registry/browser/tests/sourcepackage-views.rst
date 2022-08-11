SourcePackage views
===================

Edit packaging view
-------------------

    >>> product = factory.makeProduct(name='bonkers', displayname='Bonkers')
    >>> productseries = factory.makeProductSeries(
    ...     name='crazy', product=product)
    >>> distribution = factory.makeDistribution(
    ...     name='youbuntu', displayname='Youbuntu')
    >>> distroseries = factory.makeDistroSeries(
    ...     name='busy', distribution=distribution)
    >>> sourcepackagename = factory.makeSourcePackageName(name='bonkers')
    >>> package = factory.makeSourcePackage(
    ...     sourcepackagename=sourcepackagename, distroseries=distroseries)

    >>> view = create_initialized_view(package, name='+edit-packaging')
    >>> print(view.label)
    Link to an upstream project

    >>> print(view.page_title)
    Link to an upstream project

    >>> print(view.view.cancel_url)
    http://launchpad.test/youbuntu/busy/+source/bonkers


The view allows the logged in user to change product series field. The
value of the product field is None by default because it is not required
to create a source package.

    # The product field is added in setUpFields().
    >>> view.view.field_names
    ['__visited_steps__']
    >>> [form_field.__name__ for form_field in view.view.form_fields]
    ['__visited_steps__', 'product']

    >>> print(view.view.widgets.get('product')._getFormValue())
    <BLANKLINE>

    >>> print(package.productseries)
    None

This is a multistep view. In the first step, the product is specified.

    >>> print(view.view.__class__.__name__)
    SourcePackageChangeUpstreamStepOne
    >>> print(view.view.request.form)
    {'field.__visited_steps__': 'sourcepackage_change_upstream_step1'}

    >>> ignored = login_person(product.owner)
    >>> form = {
    ...     'field.product': 'bonkers',
    ...     'field.actions.continue': 'Continue',
    ...     }
    >>> form.update(view.view.request.form)
    >>> view = create_initialized_view(
    ...     package, name='+edit-packaging', form=form,
    ...     principal=product.owner)
    >>> view.view.errors
    []

In the second step, one of the series of the previously selected
product can be chosen from a list of options.

    >>> print(view.view.__class__.__name__)
    SourcePackageChangeUpstreamStepTwo
    >>> print(view.view.request.form['field.__visited_steps__'])
    sourcepackage_change_upstream_step1|sourcepackage_change_upstream_step2
    >>> [term.token for term in view.view.widgets['productseries'].vocabulary]
    ['trunk', 'crazy']

    >>> form = {
    ...     'field.__visited_steps__': 'sourcepackage_change_upstream_step2',
    ...     'field.product': 'bonkers',
    ...     'field.productseries': 'crazy',
    ...     'field.actions.continue': 'continue',
    ...     }
    >>> view = create_initialized_view(
    ...     package, name='+edit-packaging', form=form,
    ...     principal=product.owner)

    >>> ignored = view.view.render()
    >>> print(view.view.next_url)
    http://launchpad.test/youbuntu/busy/+source/bonkers

    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    Upstream link updated.

    >>> print(package.productseries.name)
    crazy

    >>> transaction.commit()

The form shows the current product if it is set.

    >>> view = create_initialized_view(package, name='+edit-packaging')

    >>> print(view.view.widgets.get('product')._getFormValue().name)
    bonkers

If the same product as the current product series is selected,
then the current product series will be the selected option.

    >>> form = {
    ...     'field.product': 'bonkers',
    ...     'field.actions.continue': 'Continue',
    ...     }
    >>> form.update(view.view.request.form)
    >>> view = create_initialized_view(
    ...     package, name='+edit-packaging', form=form,
    ...     principal=product.owner)
    >>> print(view.view.widgets.get('productseries')._getFormValue().name)
    crazy

The form requires a product. An error is raised if the field is left
empty.

    >>> form = {
    ...     'field.__visited_steps__': 'sourcepackage_change_upstream_step1',
    ...     'field.product': '',
    ...     'field.actions.continue': 'Continue',
    ...     }
    >>> view = create_initialized_view(
    ...     package, name='+edit-packaging', form=form,
    ...     principal=product.owner)
    >>> for error in view.view.errors:
    ...     print(pretty(error.args))
    ('product', 'Project', RequiredMissing('product'))

Submitting the same product series as the current packaging is not an error,
but there is no notification message that the upstream link was updated.

    >>> form = {
    ...     'field.__visited_steps__': 'sourcepackage_change_upstream_step2',
    ...     'field.product': 'bonkers',
    ...     'field.productseries': 'crazy',
    ...     'field.actions.continue': 'Continue',
    ...     }
    >>> view = create_initialized_view(
    ...     package, name='+edit-packaging', form=form,
    ...     principal=product.owner)
    >>> print(view.view)
    <...SourcePackageChangeUpstreamStepTwo object...>
    >>> print(view.view.next_url)
    http://launchpad.test/youbuntu/busy/+source/bonkers
    >>> view.view.errors
    []

    >>> print(view.request.response.notifications)
    []


Upstream associations portlet
-----------------------------

The upstreams associations portlet either displays the upstream
information if it is already set or gives the user the opportunity to
suggest the association.  The suggestion is based on a
ProductVocabulary query using the source package name.

Since the bonkers source project was associated previously with the
bonkers project, the portlet will display that information.

    >>> view = create_initialized_view(package, name='+portlet-associations')
    >>> for product in view.product_suggestions:
    ...     print(product.name)
    bonkers

    >>> from lp.testing.pages import (
    ...     extract_text, find_tag_by_id)
    >>> content = find_tag_by_id(view.render(), 'upstreams')
    >>> for link in content.find_all('a'):
    ...     print(link['href'])
    /bonkers
    /bonkers/crazy
    .../+source/bonkers/+edit-packaging
    .../+source/bonkers/+remove-packaging

    >>> print(extract_text(content))
    Bonkers...crazy...
    Bug supervisor: no
    Bug tracker: no
    Branch: no
    There are no registered releases for the Bonkers ⇒ crazy.

A new source project that is not linked to an upstream will result in
the portlet showing the suggested project.

    >>> product = factory.makeProduct(name='lernid', displayname='Lernid')
    >>> sourcepackagename = factory.makeSourcePackageName(name='lernid')
    >>> package = factory.makeSourcePackage(
    ...     sourcepackagename=sourcepackagename, distroseries=distroseries)

    >>> view = create_initialized_view(package, name='+portlet-associations')
    >>> for product in view.product_suggestions:
    ...     print(product.name)
    lernid

    >>> content = extract_text(find_tag_by_id(view.render(), 'no-upstreams'))
    >>> print(content)
    Launchpad doesn’t know which project and series this package belongs to.
    ...
    Is the following project the upstream for this source package?
    Registered upstream project:
    Lernid
    Choose another upstream project
    Register the upstream project

The form does not steal focus because it is not the primary purpose of the
page.

    >>> print(view.initial_focus_widget)
    None

If there are multiple potential matches, the first 9 are shown. The 10th
item is reserved for the "Choose another upstream project" option.

    >>> product = factory.makeProduct(
    ...     name='lernid-dev', displayname='Lernid Dev')
    >>> view = create_initialized_view(package, name='+portlet-associations')
    >>> for product in view.product_suggestions:
    ...     print(product.name)
    lernid
    lernid-dev

    >>> view.max_suggestions
    9

    >>> content = extract_text(find_tag_by_id(view.render(), 'no-upstreams'))
    >>> print(content)
    Launchpad doesn’t know which project and series this package belongs to.
    ...
    Is one of these projects the upstream for this source package?
    Registered upstream project:
    Lernid...
    Lernid Dev...
    Choose another upstream project
    Register the upstream project

Choosing the "Choose another upstream project" option redirects the user
to the +edit-packaging page where the user can search for a project.

    >>> form = {
    ...     'field.upstream': 'OTHER_UPSTREAM',
    ...     'field.actions.link': 'Link to Upstream Project',
    ...     }
    >>> view = create_initialized_view(
    ...     package, name='+portlet-associations', form=form)
    >>> view.errors
    []
    >>> print(view.next_url)
    http://launchpad.test/youbuntu/busy/+source/lernid/+edit-packaging


Upstream connections view
-------------------------

The view includes a property for determining if the project has a bug
tracker, though the rules are somewhat complicated.

If the view's package has no productseries set then has_bugtracker is False.


    >>> product = factory.makeProduct(name='stinky', displayname='Stinky')
    >>> productseries = factory.makeProductSeries(
    ...     name='stinkyseries', product=product)
    >>> distroseries = factory.makeDistroSeries(
    ...     name='wonky', distribution=distribution)
    >>> sourcepackagename = factory.makeSourcePackageName(
    ...     name='stinkypackage')
    >>> package = factory.makeSourcePackage(
    ...     sourcepackagename=sourcepackagename, distroseries=distroseries)

    >>> view = create_initialized_view(
    ...     package, name='+upstream-connections')

    >>> print(package.productseries)
    None
    >>> print(view.has_bugtracker)
    False

So let's set the product series so we can do more interesting testing.

    >>> package.setPackaging(productseries, product.owner)
    >>> print(package.productseries.name)
    stinkyseries

If a product is not part of a project group and its bug tracker is not
set then the view property is false.

    >>> view = create_initialized_view(
    ...     package, name='+upstream-connections')

    >>> print(product.bug_tracking_usage.name)
    UNKNOWN
    >>> print(product.bugtracker)
    None
    >>> print(view.has_bugtracker)
    False

Having official_malone set results in has_bugtracker being true.

    >>> ignored = login_person(product.owner)
    >>> product.official_malone = True
    >>> print(view.has_bugtracker)
    True

Having a bug_tracker set also results in has_bugtracker being true (a
bit of a tautology you'd think).

    >>> product.official_malone = False
    >>> bugtracker = factory.makeBugTracker()
    >>> product.bugtracker = bugtracker
    >>> print(view.has_bugtracker)
    True

If the product has no bug tracker and is in a project group with no
bug tracker then the property is false.

    >>> product.bugtracker = None
    >>> projectgroup = factory.makeProject()
    >>> print(projectgroup.bugtracker)
    None
    >>> product.projectgroup = projectgroup
    >>> print(view.has_bugtracker)
    False

If the product's project group does have a bug tracker then the product
inherits it.

    >>> ignored = login_person(projectgroup.owner)
    >>> projectgroup.bugtracker = bugtracker
    >>> print(view.has_bugtracker)
    True


Remove packaging view
---------------------

This view allows removal of the packaging link from the sourcepackage
to the project series.

    >>> view = create_initialized_view(package, name='+remove-packaging')
    >>> print(view.label)
    Unlink an upstream project

    >>> print(view.page_title)
    Unlink an upstream project

    >>> print(view.cancel_url)
    http://launchpad.test/youbuntu/wonky/+source/stinkypackage

    >>> user = package.packaging.owner
    >>> ignored = login_person(user)
    >>> form = {'field.actions.unlink': 'Unlink'}
    >>> view = create_initialized_view(
    ...     package, name='+remove-packaging', form=form, principal=user)
    >>> view.errors
    []

    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    Removed upstream association between Stinky stinkyseries series and Wonky.

If somebody attempts to remove this packaging link a second time,
they get a message telling them that the link has already been
deleted.

    >>> view = create_initialized_view(
    ...     package, name='+remove-packaging', form=form, principal=user)
    >>> view.errors
    []

    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    The packaging link has already been deleted.

    >>> view = create_initialized_view(package, name='+portlet-associations')
    >>> print(extract_text(find_tag_by_id(view.render(), 'no-upstreams')))
    Launchpad doesn’t know which project ...
    There are no projects registered in Launchpad that are a potential
    match for this source package. Can you help us find one?
    Registered upstream project:
    Choose another upstream project
    Register the upstream project
