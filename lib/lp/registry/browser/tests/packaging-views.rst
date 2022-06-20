Packaging views
===============

Packaging links connect a sourcepackage to a distroseries and a productseries.


Productseries linking packages
------------------------------

Distro series sourcepackages can be linked to product series using the
+ubuntupkg named view.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities

    >>> ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    >>> hoary = ubuntu.getSeries('hoary')
    >>> sourcepackagename = factory.makeSourcePackageName('hot')
    >>> dsp = factory.makeDSPCache(
    ...     distroseries=hoary, sourcepackagename=sourcepackagename)
    >>> product = factory.makeProduct(name="hot", displayname='Hot')
    >>> productseries = factory.makeProductSeries(
    ...     product=product, name='hotter')
    >>> productseries.sourcepackages
    []
    >>> transaction.commit()

The view has a label and requires a distro series and a source package name.
The distroseries field's vocabulary is the same as the ubuntu.series
attribute.

    >>> view = create_view(productseries, '+ubuntupkg')
    >>> print(view.label)
    Ubuntu source packaging

    >>> print(view.page_title)
    Ubuntu source packaging

    >>> print(view.field_names)
    ['sourcepackagename', 'distroseries']

    >>> print(view.cancel_url)
    http://launchpad.test/hot/hotter

    >>> for series in ubuntu.series:
    ...     print(series.name)
    breezy-autotest
    grumpy
    hoary
    warty
    >>> view.setUpFields()
    >>> for term in view.form_fields['distroseries'].field.vocabulary:
    ...     print(term.token)
    breezy-autotest
    grumpy
    hoary
    warty

    >>> form = {
    ...     'field.distroseries': 'hoary',
    ...     'field.sourcepackagename': 'hot',
    ...     'field.packaging': 'Primary Project',
    ...     'field.actions.continue': 'Continue',
    ...     }
    >>> view = create_initialized_view(
    ...     productseries, '+ubuntupkg', form=form)
    >>> view.errors
    []
    >>> for package in productseries.sourcepackages:
    ...     print(package.name)
    hot

    >>> transaction.commit()


Productseries linking Ubuntu packages
-------------------------------------

The +ubuntupkg named view allows the user to update the current linked
Ubuntu package.

    >>> view = create_initialized_view(productseries, '+ubuntupkg')

    >>> print(view.label)
    Ubuntu source packaging

    >>> print(view.page_title)
    Ubuntu source packaging

    >>> print(view.field_names)
    ['sourcepackagename', 'distroseries']

    >>> print(view.cancel_url)
    http://launchpad.test/hot/hotter

The view restricts the packaging to Ubuntu series, and default is the current
Ubuntu series.

    >>> print(view.default_distroseries.name)
    hoary

    >>> print(view.widgets['distroseries']._getDefault().name)
    hoary

    >>> for term in view.widgets['distroseries'].vocabulary:
    ...     print(term.title)
    Breezy Badger Autotest (6.6.6)
    Grumpy (5.10)
    Hoary (5.04)
    Warty (4.10)

The sourcepackagename is None if the package link was never set. The view's
packaging history is empty, and the sourcepackagename widget is empty.

    >>> new_productseries = factory.makeProductSeries(
    ...     product=product, name='cold')
    >>> view = create_initialized_view(new_productseries, '+ubuntupkg')

    >>> print(view.default_sourcepackagename)
    None

    >>> print(view.widgets.get('sourcepackagename')._getFormValue())
    <BLANKLINE>

    >>> print(view.ubuntu_history)
    []

Series have been packaged in Ubuntu do have the current information and
a history.

    >>> view = create_initialized_view(productseries, '+ubuntupkg')
    >>> print(view.default_sourcepackagename.name)
    hot

    >>> print(view.widgets.get('sourcepackagename')._getFormValue().name)
    hot

    >>> for packaging in view.ubuntu_history:
    ...     print(packaging.distroseries.name)
    ...     print(packaging.sourcepackagename.name)
    hoary hot

The package in the current Ubuntu series can be updated.

    >>> dsp = factory.makeDSPCache(
    ...     distroseries=hoary, sourcepackagename='thunderbird')

    >>> form = {
    ...     'field.sourcepackagename': 'thunderbird',
    ...     'field.actions.continue': 'Update',
    ...     }
    >>> view = create_initialized_view(
    ...     productseries, '+ubuntupkg', form=form)
    >>> view.errors
    []

We now have two source packages linked to our productseries.

    >>> for packaging in view.ubuntu_history:
    ...     print(packaging.distroseries.name)
    ...     print(packaging.sourcepackagename.name)
    hoary thunderbird
    hoary hot

It is not an error to submit the same sourcepackagename information, the
action is ignored because there is no change

    >>> form = {
    ...     'field.sourcepackagename': 'thunderbird',
    ...     'field.actions.continue': 'Update',
    ...     }
    >>> view = create_initialized_view(
    ...     productseries, '+ubuntupkg', form=form)
    >>> view.errors
    []

    >>> for packaging in view.ubuntu_history:
    ...     print(packaging.distroseries.name)
    ...     print(packaging.sourcepackagename.name)
    hoary thunderbird
    hoary hot

When the current Ubuntu series changes, the sourcepackagename is not known,
and a new entry can be added to the packaging history.

    >>> from lp.registry.interfaces.series import SeriesStatus

    >>> login('admin@canonical.com')
    >>> hoary.status = SeriesStatus.CURRENT
    >>> grumpy_series = ubuntu.getSeries('grumpy')
    >>> spph = factory.makeSourcePackagePublishingHistory(
    ...     sourcepackagename=sourcepackagename, distroseries=grumpy_series)
    >>> grumpy_series.status = SeriesStatus.FROZEN

    >>> a_user = factory.makePerson(name="hedgehog")
    >>> ignored = login_person(a_user)
    >>> form = {
    ...     'field.sourcepackagename': 'hot',
    ...     'field.actions.continue': 'Update',
    ...     }
    >>> view = create_initialized_view(
    ...     productseries, '+ubuntupkg', form=form)
    >>> view.errors
    []

    >>> print(view.default_distroseries.name)
    grumpy

    >>> print(view.default_sourcepackagename)
    None

    >>> for packaging in view.ubuntu_history:
    ...     print(packaging.distroseries.name)
    ...     print(packaging.sourcepackagename.name)
    grumpy hot
    hoary thunderbird
    hoary hot


Product packages view
----------------------

The +packages named view displays the packages links to the product's series.

    >>> view = create_initialized_view(product, name='+packages')
    >>> print(view.label)
    Linked packages

The view provides the series_batch property.

    >>> def print_packages(view):
    ...     for series in view.series_batch.batch:
    ...         print(series.name)
    ...         for package in series.packagings:
    ...             print('  Package %s: %s' % (
    ...                 package.sourcepackagename.name,
    ...                 package.distroseries.name))
    >>> print_packages(view)
    trunk
    hotter
      Package hot: grumpy
      Package thunderbird: hoary
      Package hot: hoary
    cold

The view provides the distro_packaging property that is a list of
dictionaries for the distributions and their packaging.  The list is
sorted by distribution with Ubuntu first and the rest in alphabetic
order.

    >>> for distro_dict in view.distro_packaging:
    ...     print(distro_dict['distribution'].name)
    ubuntu

A packaging link can be deleted if the owner believes it is an error. The
package linked to hoary is wrong; thunderbird is the wrong sourcepackage.
(Note that the packaging link for thunderbird in the sample data does not
have an owner, so we login as a member of distribution owner team
instead.)

    >>> from lp.testing.pages import find_tag_by_id
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> steve_a = getUtility(IPersonSet).getByName('stevea')
    >>> ignored = login_person(steve_a)
    >>> view = create_initialized_view(
    ...     product, name='+packages', principal=steve_a)
    >>> print_packages(view)
    trunk
    hotter
      Package hot: grumpy
      Package thunderbird: hoary
      Package hot: hoary
    cold

    # There are links to the +remove-packaging page.
    >>> table = find_tag_by_id(view.render(), 'packages-hotter')
    >>> for link in table.find_all('a'):
    ...     if '+remove-packaging' in link['href']:
    ...         print(link['href'])
    http://launchpad.test/ubuntu/grumpy/+source/hot/+remove-packaging
    http://launchpad.test/ubuntu/hoary/+source/thunderbird/+remove-packaging
    http://launchpad.test/ubuntu/hoary/+source/hot/+remove-packaging

    >>> [hoary_package] = [
    ...     package for series in view.series_batch.batch
    ...     for package in series.packagings
    ...     if package.distroseries.name == 'hoary' and
    ...         package.sourcepackagename.name == 'thunderbird']
    >>> form = {'field.actions.unlink': 'Unlink'}
    >>> unlink_view = create_initialized_view(
    ...     hoary_package.sourcepackage, name='+remove-packaging', form=form,
    ...     principal=steve_a)
    >>> unlink_view.errors
    []

    # The view has to be reloaded since view.series_batch is cached.
    >>> view = create_initialized_view(product, name='+packages')
    >>> print_packages(view)
    trunk
    hotter
      Package hot: grumpy
      Package hot: hoary
    cold


Distro series +packaging view
-----------------------------

The DistroSeriesPackagesView shows the packages in a distro series that
are linked to upstream projects.

    >>> view = create_initialized_view(hoary, name='+packaging')
    >>> print(view.label)
    All series packages linked to upstream project series

    >>> print(view.page_title)
    All upstream links

The view provides a property to get prioritized list of series packagings.
The packages that most need more information to send bugs upstream, build
packages, and sync translations are listed first. A distro series can have
thousands of upstream packaging links. The view provides a batch navigator
to access the packagings. The default batch size is 20.

    >>> batch_navigator = view.cached_packagings
    >>> batch_navigator.default_size
    20

    >>> print(batch_navigator.heading)
    packagings

    >>> for packaging in batch_navigator.batch:
    ...     print(packaging.sourcepackagename.name)
    netapplet
    evolution
    hot


Distro series +needs-packaging view
-----------------------------------

The +needs-packaging view lists the source packages that needs packaging
links to an upstream project.

    >>> view = create_initialized_view(hoary, name='+needs-packaging')
    >>> print(view.label)
    Packages that need upstream packaging links

    >>> print(view.page_title)
    Needs upstream links

The view provides the cached_unlinked_packages property to access a
`BatchNavigator` of `ISourcePackages`.

    >>> batch_navigator = view.cached_unlinked_packages
    >>> batch_navigator.default_size
    20

    >>> print(batch_navigator.heading)
    packages

    >>> for summary in batch_navigator.batch:
    ...     print(summary['package'].name)
    pmount
    alsa-utils
    cnews
    libstdc++
    linux-source-2.6.15
    thunderbird
