DistroSeries view classes
=========================

Let's use ubuntu/hoary for these tests.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> hoary = ubuntu.getSeries('hoary')


Administering distroseries
--------------------------

The +admin view allows administrators to change a series. It provides a
label, page_title, and cancel_url

    >>> view = create_initialized_view(hoary, name='+admin')
    >>> print(view.label)
    Administer The Hoary Hedgehog Release

    >>> print(view.page_title)
    Administer The Hoary Hedgehog Release

    >>> print(view.cancel_url)
    http://launchpad.test/ubuntu/hoary

We will use a function to print the details related with the
distroseries being tested.

    >>> def administrate_distroseries(distroseries, form):
    ...     view = create_initialized_view(hoary, name='+admin', form=form)
    ...     print('%d errors' % len(view.errors))
    ...     for error in view.errors:
    ...         try:
    ...             name, title, message = error.args
    ...         except ValueError:
    ...             title, message = error.args
    ...         print('%s: %s' % (title, message))
    ...     print('Name:', distroseries.name)
    ...     print('Version:', distroseries.version)
    ...     print('Changeslist:', distroseries.changeslist)
    ...     print('Status:', distroseries.status.name)

    >>> form = {
    ...     'field.actions.change': 'Change',
    ...     'field.name': 'hoary',
    ...     'field.version': '5.04',
    ...     'field.changeslist': 'hoary-changes@ubuntu.com',
    ...     'field.status': 'DEVELOPMENT',
    ...     }

    >>> login('foo.bar@canonical.com')

    >>> administrate_distroseries(hoary, form)
    0 errors
    Name: hoary
    Version: 5.04
    Changeslist: hoary-changes@ubuntu.com
    Status: DEVELOPMENT

The distroseries 'changeslist' field only accept valid email addresses.

    >>> form['field.changeslist'] = ''
    >>> administrate_distroseries(hoary, form)
    1 errors
    Email changes to: changeslist
    Name: hoary
    Version: 5.04
    Changeslist: hoary-changes@ubuntu.com
    Status: DEVELOPMENT

    >>> form['field.changeslist'] = 'bRoKen_AdDreSs'
    >>> administrate_distroseries(hoary, form)
    1 errors
    Email changes to: Invalid email &#x27;bRoKen_AdDreSs&#x27;.
    Name: hoary
    Version: 5.04
    Changeslist: hoary-changes@ubuntu.com
    Status: DEVELOPMENT

    >>> form['field.changeslist'] = 'foo@bar.com'
    >>> administrate_distroseries(hoary, form)
    0 errors
    Name: hoary
    Version: 5.04
    Changeslist: foo@bar.com
    Status: DEVELOPMENT


When the distroseries is released, i.e. when it goes from an unstable
status (FUTURE, EXPERIMENTAL, DEVELOPMENT, FROZEN) to CURRENT, its
'datereleased' field is set.

    >>> print(hoary.datereleased)
    None

    >>> form['field.status'] = 'CURRENT'
    >>> administrate_distroseries(hoary, form)
    0 errors
    Name: hoary
    Version: 5.04
    Changeslist: foo@bar.com
    Status: CURRENT

    >>> initial_datereleased = hoary.datereleased
    >>> initial_datereleased is not None
    True

Let's commit the current DB status, so errors can be triggered and
will not rollback the changes done until here.

    >>> import transaction
    >>> transaction.commit()

A stable distroseries cannot be made unstable again.

    >>> form['field.status'] = 'EXPERIMENTAL'
    >>> administrate_distroseries(hoary, form)
    1 errors
    Invalid value: token ...'EXPERIMENTAL' not found in vocabulary
    Name: hoary
    Version: 5.04
    Changeslist: foo@bar.com
    Status: CURRENT

The 'datereleased' value is only set once, even if the distroseries is
modified to SUPPORTED or OBSOLETE and then set back to CURRENT its
initial value remains.

    >>> form['field.status'] = 'SUPPORTED'
    >>> administrate_distroseries(hoary, form)
    0 errors
    Name: hoary
    Version: 5.04
    Changeslist: foo@bar.com
    Status: SUPPORTED

    >>> hoary.datereleased == initial_datereleased
    True

    >>> form['field.status'] = 'CURRENT'
    >>> administrate_distroseries(hoary, form)
    0 errors
    Name: hoary
    Version: 5.04
    Changeslist: foo@bar.com
    Status: CURRENT

    >>> hoary.datereleased == initial_datereleased
    True


Editing distro series
---------------------

The distroseries edit view allows the editor to change series. The form
uses the display_name, title, and description fields.

    >>> driver = factory.makePerson(name='ubuntu-driver')
    >>> hoary.driver = driver
    >>> ignored = login_person(driver)
    >>> view = create_initialized_view(hoary, '+edit')
    >>> print(view.label)
    Edit The Hoary Hedgehog Release details

    >>> print(view.page_title)
    Edit The Hoary Hedgehog Release details

    >>> print(view.cancel_url)
    http://launchpad.test/ubuntu/hoary

    >>> [field.__name__ for field in view.form_fields]
    ['display_name', 'title', 'summary', 'description']

Admins can see the status field for full functionality distributions.

    >>> login('admin@canonical.com')
    >>> view = create_initialized_view(hoary, '+edit')
    >>> [field.__name__ for field in view.form_fields]
    ['display_name', 'title', 'summary', 'description', 'status']

Series that belong to derivative distributions also contain the status field.

    >>> youbuntu = factory.makeDistribution(name='youbuntu')
    >>> yo_series = factory.makeDistroSeries(name='melon')
    >>> yo_series.title = 'Melon'
    >>> youbuntu.official_packages
    False

    >>> yo_driver = factory.makePerson(name='yo-driver')
    >>> youbuntu.driver = yo_driver
    >>> ignored = login_person(yo_driver)
    >>> view = create_initialized_view(yo_series, '+edit')
    >>> print(view.label)
    Edit Melon details

    >>> [field.__name__ for field in view.form_fields]
    ['display_name', 'title', 'summary', 'description', 'status']

    >>> print(view.widgets.get('status')._getFormValue().title)
    Active Development


Creating distro series
----------------------

A distroseries is created using the distroseries view.

    >>> login('foo.bar@canonical.com')

    >>> view = create_view(ubuntu, '+addseries')
    >>> print(view.page_title)
    Add a series
    >>> print(view.label)
    Add a series

    >>> print(view.cancel_url)
    http://launchpad.test/ubuntu
    >>> print(view.next_url)
    None

    >>> view.field_names
    ['name', 'version', 'display_name', 'summary']

A distroseries is created whent the required field are submitted.

    >>> form = {
    ...     'field.name': 'sane',
    ...     'field.display_name': 'Sane Name',
    ...     'field.summary': 'A stable series to introduce fnord.',
    ...     'field.version': '2009.06',
    ...     'field.actions.create': 'Create Series',
    ...     }
    >>> view = create_initialized_view(ubuntu, '+addseries', form=form)
    >>> view.errors
    []
    >>> sane_distroseries = ubuntu.getSeries('sane')
    >>> print(sane_distroseries.name)
    sane

    # Save this series to test name and version constraints.
    >>> transaction.commit()

Administrators can create series, but normal users cannot.

    >>> from lp.services.webapp.authorization import check_permission

    >>> check_permission('launchpad.Driver', view)
    True

    >>> login('no-priv@canonical.com')
    >>> check_permission('launchpad.Driver', view)
    False


Drivers can create distro series
--------------------------------

Users who are appointed as drivers of a distribution that doesn't use
Launchpad for package management can create a series.

    >>> ignored = login_person(yo_driver)
    >>> view = create_view(youbuntu, name='+addseries')
    >>> check_permission('launchpad.Moderate', view)
    True

    >>> yo_form = dict(form)
    >>> yo_form['field.name'] = 'island'
    >>> yo_form['field.display_name'] = 'Island'
    >>> view = create_initialized_view(
    ...     youbuntu, name='+addseries', form=yo_form, principal=yo_driver)
    >>> view.errors
    []

    >>> yo_series = youbuntu.getSeries('island')
    >>> print(yo_series.display_name)
    Island

But drivers of distributions that use Soyuz officially (eg. Ubuntu)
cannot create series, as that could have serious consequences for the
primary archive.

    >>> ubuntu.official_packages
    True

    >>> ignored = login_person(ubuntu.owner.teamowner)
    >>> ubuntu.driver = yo_driver
    >>> ignored = login_person(yo_driver)
    >>> view = create_view(youbuntu, name='+addseries')
    >>> check_permission('launchpad.Edit', view)
    False


Drivers editing distro series
.............................

The series driver (release manager) can edit a series if the series
doesn't manage its packages in Launchpad.

    >>> print(yo_series.driver.name)
    yo-driver

    >>> ignored = login_person(yo_driver)
    >>> view = create_view(yo_series, name='+edit')
    >>> check_permission('launchpad.Edit', view)
    True

    >>> yo_form = dict(form)
    >>> del yo_form['field.actions.create']
    >>> yo_form['field.display_name'] = 'Mountain'
    >>> yo_form['field.summary'] = 'Mountain summary'
    >>> yo_form['field.actions.change'] = 'Change'
    >>> view = create_initialized_view(
    ...     yo_series, name='+edit', form=yo_form, principal=yo_driver)
    >>> view.errors
    []

    >>> print(yo_series.display_name)
    Mountain

Drivers of packages with packages such as Ubuntu cannot edit a series.

    >>> ignored = login_person(ubuntu.owner.teamowner)
    >>> hoary.driver = yo_driver
    >>> ignored = login_person(yo_driver)

    >>> view = create_view(hoary, name='+edit')
    >>> check_permission('launchpad.Edit', view)
    False


Distroseries name
-----------------

The distroseries name is unique.

    >>> login('foo.bar@canonical.com')

    >>> form['field.name'] = 'sane'
    >>> form['field.version'] = '2009.07'
    >>> view = create_initialized_view(ubuntu, '+addseries', form=form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    sane is already in use by another series.

The distroseries name cannot contain spaces.

    >>> form['field.name'] = 'insane name'
    >>> view = create_initialized_view(ubuntu, '+addseries', form=form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    Invalid name 'insane name'...


Distroseries version
--------------------

Versions cannot contain spaces.

    >>> form['field.name'] = '6-06-series'
    >>> form['field.version'] = '6.06 LTS'
    >>> view = create_initialized_view(ubuntu, '+addseries', form=form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    6.06 LTS is not a valid version

The distroseries version must be a valid debversion.

    >>> form['field.version'] = 'Hardy-6.06-LTS'
    >>> view = create_initialized_view(ubuntu, '+addseries', form=form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    &#x27;Hardy-6.06-LTS&#x27;: Could not parse version...

The distroseries version is unique to a distribution. Version '2009.06'
cannot be reused by another Ubuntu series.

    >>> print(sane_distroseries.version)
    2009.06

    >>> form['field.name'] = 'experimental'
    >>> form['field.version'] = '2009.06'
    >>> view = create_initialized_view(ubuntu, '+addseries', form=form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    2009.06 is already in use by another version in this distribution.

But version '2009.06' can be used by another distribution.

    >>> other_distro = factory.makeDistribution(name='other-distro')
    >>> view = create_initialized_view(other_distro, '+addseries', form=form)
    >>> view.errors
    []

    >>> experimental_distroseries = other_distro.getSeries('experimental')
    >>> print(experimental_distroseries.version)
    2009.06
