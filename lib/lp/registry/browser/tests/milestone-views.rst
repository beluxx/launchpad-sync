Milestone pages
===============

Users can directly see and edit milestones through the milestone views.

    >>> person = factory.makePerson(name='puffin-owner')
    >>> product = factory.makeProduct(name="puffin", owner=person)
    >>> series = factory.makeProductSeries(product=product, name="awk")
    >>> milestone = factory.makeMilestone(productseries=series, name="kakapo")

The default url for a milestone is to the main site.

    >>> from lp.testing import test_tales
    >>> from lp.services.webapp.servers import LaunchpadTestRequest

    >>> request = LaunchpadTestRequest(SERVER_URL='http://bugs.launchpad.net')
    >>> login(ANONYMOUS, request)
    >>> print(test_tales("milestone/fmt:url", milestone=milestone))
    http://launchpad.test/puffin/+milestone/kakapo

Milestone defines several menus.

    >>> from lp.registry.browser.milestone import (
    ...     MilestoneContextMenu, MilestoneInlineNavigationMenu,
    ...     MilestoneOverviewMenu, MilestoneOverviewNavigationMenu)
    >>> from lp.testing.menu import check_menu_links

    >>> check_menu_links(MilestoneContextMenu(milestone))
    True
    >>> check_menu_links(MilestoneOverviewMenu(milestone))
    True
    >>> check_menu_links(MilestoneOverviewNavigationMenu(milestone))
    True
    >>> check_menu_links(MilestoneInlineNavigationMenu(milestone))
    True

The MilestoneView used can be adapted to a MilestoneInlineNavigationMenu
for use with inline presentation of milestones.

    >>> from lp.services.webapp.interfaces import INavigationMenu
    >>> from lp.services.webapp.canonicalurl import nearest_adapter

    >>> view = create_view(milestone, name='+productseries-table-row')
    >>> nearest_adapter(view, INavigationMenu, name='overview')
    <lp.registry.browser.milestone.MilestoneInlineNavigationMenu ...>

The MilestoneView provides access to the milestone and to its release if
it has one.

    >>> ignored = login_person(person)
    >>> view = create_view(milestone, '+index')
    >>> print(view.context.name)
    kakapo

    >>> print(view.milestone.name)
    kakapo

    >>> print(view.release)
    None

    >>> release = factory.makeProductRelease(milestone)
    >>> view = create_view(milestone, '+index')
    >>> print(view.release.version)
    kakapo

The view makes the HTML page title.

    >>> print(view.page_title)
    Puffin kakapo

Bugs and specifications targeted to the milestone are accessible too.
The has_bugs_or_specs boolean property can be used to verify if the
milestone has any bugs or specifications.

    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus

    >>> view.has_bugs_or_specs
    False

    >>> bug = factory.makeBug(title="kiwi")
    >>> bugtask = factory.makeBugTask(bug=bug, target=milestone.product)
    >>> bugtask.transitionToStatus(BugTaskStatus.FIXCOMMITTED, person)
    >>> bugtask.transitionToAssignee(person)
    >>> bugtask.milestone = milestone
    >>> spec = factory.makeSpecification(
    ...     product=milestone.product, title='dodo')
    >>> spec.milestone = milestone

    >>> view = create_view(milestone, '+index')
    >>> view.has_bugs_or_specs
    True

    >>> for bugtask in view.bugtasks:
    ...     print(bugtask.bug.title)
    kiwi

    >>> for spec in view.specifications:
    ...     print(spec.title)
    dodo

On a IDistroSeries/IProductSeries main page, we use this view to list detailed
information about the context's milestones. However, generating the summary of
bugs/blueprints for a milestone is rather expensive, so we only do that for
active milestones.

    >>> milestone.active
    True
    >>> view.should_show_bugs_and_blueprints
    True

    >>> milestone.active = False
    >>> view.should_show_bugs_and_blueprints
    False

The bugtasks are decorated. They are wrapped by the BugTaskListingItem
that has cached information to create badges quickly. The
_bug_badge_properties property provides the additional information that
is used by the decorator.

    >>> view.bugtasks
    [<...BugTaskListingItem ...>]

    >>> for bugtask in view._bug_badge_properties:
    ...     bugtask
    ...     badge_dict = view._bug_badge_properties[bugtask]
    ...     for key in sorted(badge_dict):
    ...         print('%s: %s' % (key, badge_dict[key]))
    <BugTask ...>
        has_branch: False
        has_patch: False
        has_specification: False

    >>> view.bugtasks[0].last_significant_change_date
    datetime.datetime(...)

There bugtask_count_text and specification_count_text properties provide
formatted text descriptions of the bugtasks and specifications. The text
supports plural descriptions.

    >>> print(view.bugtask_count_text)
    1 bug

    >>> print(view.specification_count_text)
    1 blueprint

    >>> bug = factory.makeBug(title="emo")
    >>> bugtask = factory.makeBugTask(bug=bug, target=milestone.product)
    >>> bugtask.transitionToAssignee(person)
    >>> bugtask.milestone = milestone
    >>> spec = factory.makeSpecification(
    ...     product=milestone.product, title='ostrich')
    >>> spec.milestone = milestone

    >>> view = create_view(milestone, '+index')
    >>> print(view.bugtask_count_text)
    2 bugs

    >>> print(view.specification_count_text)
    2 blueprints

Bugtasks are ordered by status (fix released last), and importance
(critical first).

    >>> for bugtask in view.bugtasks:
    ...     assignee = bugtask.assignee
    ...     print(bugtask.bug.title, assignee.name, bugtask.status.title)
    emo   puffin-owner  New
    kiwi  puffin-owner  Fix Committed

The view provides a list of StatusCounts that summarise the targeted
specifications and bugtasks.

    >>> from lp.blueprints.enums import SpecificationImplementationStatus

    >>> bugtask.transitionToAssignee(person)
    >>> engineer = factory.makePerson(name='engineer')
    >>> spec.assignee = engineer
    >>> status = spec.updateLifecycleStatus(person)
    >>> spec.implementation_status = SpecificationImplementationStatus.GOOD
    >>> status = spec.updateLifecycleStatus(person)

    >>> for status_count in view.specification_status_counts:
    ...     print('%s: %s' % (status_count.status.title, status_count.count))
    Unknown: 1
    Good progress: 1

    >>> for status_count in view.bugtask_status_counts:
    ...     print('%s: %s' % (status_count.status.title, status_count.count))
    New: 1
    Fix Committed: 1

The assignment_counts property returns all the users and count of bugs and
specifications assigned to them.

    >>> for status_count in view.assignment_counts:
    ...     print('%s: %s' % (status_count.status.name, status_count.count))
    engineer: 1
    puffin-owner: 2

The user_counts property is the count items assigned to the current user.

    >>> for status_count in view.user_counts:
    ...     print('%s: %s' % (status_count.status, status_count.count))
    bugs: 2

The user_counts property is an empty list if the user is None.

    >>> ignored = login_person(None)
    >>> view = create_view(milestone, '+index')
    >>> view.user_counts
    []

The view uses ProductDownloadFileMixin to provide access to downloadable
files. It implements getReleases() that always returns the view's
release as a set.

    >>> ignored = login_person(person)
    >>> view = create_view(milestone, '+index')
    >>> for release in view.getReleases():
    ...     print(repr(release))
    <ProductRelease ...>

    >>> for release in view.getReleases():
    ...     print(release.version)
    kakapo

The download_files property returns a decorated list of IProductRelease
files. If there is no release, or no files, None is returned.

    >>> print(view.download_files)
    None

If there are files, these files will be returned as a list.

    >>> release_file = release.addReleaseFile(
    ...     'test.txt', b'test', 'text/plain', person,
    ...     signature_filename='test.txt.asc', signature_content=b'123',
    ...     description="test file")
    >>> view = create_view(milestone, '+index')
    >>> for file in view.download_files:
    ...     print(file.libraryfile.filename)
    test.txt


Milestone product release data
------------------------------

The +productrelease-data named view uses the same view as +index to display
the product release data for a milestone.

    >>> from lp.testing.pages import (
    ...     extract_text, find_tag_by_id)

    >>> view = create_view(
    ...     milestone, '+productrelease-data', principal=person)
    >>> content = find_tag_by_id(view.render(), 'release-data')
    >>> print(find_tag_by_id(content, 'how-to-verify').a['href'])
    /+help-registry/verify-downloads.html

    >>> print(extract_text(find_tag_by_id(content, 'downloads')))
    File                 Description  Downloads  Delete
    test.txt (md5, sig)  test file ...

    >>> print(find_tag_by_id(content, 'delete-files')['type'])
    submit

This release does not not have release notes or a change log.

    >>> print(find_tag_by_id(content, 'release-notes'))
    None

    >>> print(find_tag_by_id(content, 'changelog'))
    None

This release notes and change log do appear when the release has them.

    >>> release.release_notes = 'My release notes'
    >>> release.changelog = 'My changelog'
    >>> view = create_view(
    ...     milestone, '+productrelease-data', principal=person)
    >>> content = find_tag_by_id(view.render(), 'release-data')
    >>> print(extract_text(find_tag_by_id(content, 'release-notes')))
    My release notes

    >>> print(extract_text(find_tag_by_id(content, 'changelog')))
    My changelog

The delete column and delete submit are not rendered if the user does
not have edit permission.

    >>> ignored = login_person(engineer)
    >>> view = create_view(
    ...     milestone, '+productrelease-data', principal=engineer)
    >>> content = find_tag_by_id(view.render(), 'release-data')
    >>> print(extract_text(find_tag_by_id(content, 'downloads')))
    File                 Description  Downloads
    test.txt (md5, sig)  test file ...

    >>> print(find_tag_by_id(content, 'delete-files'))
    None

    >>> ignored = login_person(person)


ProjectGroup milestones
-----------------------

The projectgroup milestones are virtual and cannot be modified. The template
generates CSS that hides the space occupied by the side portlets.

    >>> projectgroup = factory.makeProject(name='flock')
    >>> product.projectgroup = projectgroup
    >>> project_milestone = projectgroup.getMilestone('kakapo')
    >>> view = create_initialized_view(
    ...     project_milestone, '+index', principal=person)
    >>> print(find_tag_by_id(view.render(), 'hide-side-portlets')['type'])
    text/css

A normal milestone does not have the CSS rule.

    >>> view = create_initialized_view(
    ...     milestone, '+index', principal=person)
    >>> print(find_tag_by_id(content, 'hide-side-portlets'))
    None


Editing milestones
------------------

Persons with launchpad.Edit permissions for milestones may edit them.
The MilestoneEditView is responsible for controlling the fields that the
user may edit.

    >>> from lp.services.webapp.authorization import check_permission
    >>> from lp.registry.interfaces.product import IProductSet

    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> ignored = login_person(firefox.owner)
    >>> firefox_1_0 =  firefox.getSeries('1.0')
    >>> milestone = firefox_1_0.newMilestone('1.0.8')

    >>> view = create_initialized_view(milestone, '+edit')
    >>> check_permission('launchpad.Edit', view)
    True

The view allows the user to modify the mutable milestone fields. The
cancel_url property can be used to return to the milestone.

    >>> print(view.label)
    Modify milestone details

    >>> view.field_names
    ['name', 'code_name', 'active', 'dateexpected', 'tags', 'summary',
     'productseries']

    >>> print(view.cancel_url)
    http://launchpad.test/firefox/+milestone/1.0.8

This milestone belongs to a product, so the productseries field is
included in the list of field names. The user can change the field
values.

    >>> print(milestone.name)
    1.0.8

    >>> print(milestone.dateexpected)
    None

    >>> print(milestone.summary)
    None

    >>> milestone.active
    True

    >>> print(milestone.productseries.name)
    1.0

    >>> form = {
    ...     'field.name': '1.0.9',
    ...     'field.dateexpected': '2007-05-11',
    ...     'field.summary': 'a summary',
    ...     'field.active': 'False',
    ...     'field.productseries': '1',
    ...     'field.tags': '',
    ...     'field.actions.update': 'Update',
    ...     }
    >>> view = create_initialized_view(milestone, '+edit', form=form)

    >>> print(milestone.name)
    1.0.9

    >>> print(milestone.dateexpected)
    2007-05-11

    >>> print(milestone.summary)
    a summary

    >>> milestone.active
    False

    >>> print(milestone.productseries.name)
    trunk

The milestone's name is unique to the product or series.

    >>> transaction.commit()
    >>> form = {
    ...     'field.name': '1.0',
    ...     'field.dateexpected': '2007-05-11',
    ...     'field.summary': 'a summary',
    ...     'field.active': 'True',
    ...     'field.productseries': '1',
    ...     'field.tags': '',
    ...     'field.actions.update': 'Update',
    ...     }
    >>> view = create_initialized_view(milestone, '+edit', form=form)
    >>> for error in view.errors:
    ...     print(error.errors)
    The name 1.0 is already used by a milestone in Mozilla Firefox.

    >>> for milestone in milestone.target.milestones:
    ...     print(milestone.name, milestone.code_name)
    1.0 None

The view restricts the productseries field to series that belong to the
product. A series from another product is rejected.

    >>> transaction.commit()
    >>> view = create_initialized_view(milestone, '+edit')
    >>> '100' in view.widgets['productseries'].vocabulary
    False

    >>> form['field.productseries'] = '100'
    >>> view = create_initialized_view(milestone, '+edit', form=form)

    >>> print(milestone.productseries.name)
    trunk

A milestone that belongs to the distroseries has a distroseries field
instead of a productseries field.

    >>> from lp.registry.interfaces.distribution import (
    ...     IDistributionSet)

    >>> ubuntu_distro = getUtility(IDistributionSet).getByName('ubuntu')
    >>> ignored = login_person(ubuntu_distro.owner.teamowner)
    >>> hoary_series =  ubuntu_distro.getSeries('hoary')
    >>> milestone = hoary_series.newMilestone('alpha')
    >>> view = create_initialized_view(milestone, '+edit')
    >>> view.field_names
    ['name', 'code_name', 'active', 'dateexpected', 'tags', 'summary',
    'distroseries']

The distroseries milestone can be updated too.

    >>> form = {
    ...     'field.name': 'omega',
    ...     'field.code_name': 'omega-licious',
    ...     'field.dateexpected': '2007-05-11',
    ...     'field.summary': 'a summary',
    ...     'field.active': 'False',
    ...     'field.distroseries': '5',
    ...     'field.tags': '',
    ...     'field.actions.update': 'Update',
    ...     }
    >>> view = create_initialized_view(milestone, '+edit', form=form)

    >>> print(milestone.name)
    omega

    >>> print(milestone.code_name)
    omega-licious

    >>> print(milestone.dateexpected)
    2007-05-11

    >>> print(milestone.summary)
    a summary

    >>> milestone.active
    False

    >>> print(milestone.distroseries.name)
    grumpy

Like the productseries field, the distroseries field only accepts series
that belong to the distribution.

    >>> transaction.commit()
    >>> view = create_initialized_view(milestone, '+edit')
    >>> '100' in view.widgets['distroseries'].vocabulary
    False

    >>> form['field.distroseries'] = '100'
    >>> view = create_initialized_view(milestone, '+edit', form=form)

    >>> print(milestone.distroseries.name)
    grumpy

Users without launchpad.Edit permissions cannot access the view.

    >>> from lp.registry.interfaces.person import IPersonSet

    >>> no_priv = getUtility(IPersonSet).getByName('no-priv')
    >>> ignored = login_person(no_priv)
    >>> view = create_initialized_view(milestone, '+edit')
    >>> check_permission('launchpad.Edit', view)
    False


Adding milestones
-----------------

The AddMilestoneView is used to create a new milestone.

    >>> owner = firefox.owner
    >>> ignored = login_person(owner)
    >>> view = create_initialized_view(firefox_1_0, '+addmilestone')
    >>> print(view.label)
    Register a new milestone

    >>> view.field_names
    ['name', 'code_name', 'dateexpected', 'tags', 'summary']

The view provides an action_url and cancel_url properties that form
submitting the form or aborting the action.

    >>> print(view.action_url)
    http://launchpad.test/firefox/1.0/+addmilestone

    >>> print(view.cancel_url)
    http://launchpad.test/firefox/1.0

Only the name of the milestone is required.

    >>> form = {
    ...     'field.name': '1.1',
    ...     'field.actions.register': 'Register Milestone',
    ...     }
    >>> view = create_initialized_view(
    ...     firefox_1_0, '+addmilestone', form=form)
    >>> for milestone in firefox_1_0.milestones:
    ...     print(milestone.name, milestone.code_name)
    1.1 None

The milestone name is unique to a product or distribution. The view
cannot create a duplicate milestone.

    >>> transaction.commit()
    >>> form = {
    ...     'field.name': '1.1',
    ...     'field.code_name': 'impossible',
    ...     'field.actions.register': 'Register Milestone',
    ...     }
    >>> view = create_initialized_view(
    ...     firefox_1_0, '+addmilestone', form=form)
    >>> for error in view.errors:
    ...     print(error.errors)
    The name 1.1 is already used by a milestone in Mozilla Firefox.

    >>> for milestone in firefox_1_0.milestones:
    ...     print(milestone.name, milestone.code_name)
    1.1 None

An empty code_name or summary (submitted via AJAX) is converted to None.

    >>> form = {
    ...     'field.name': '2.1',
    ...     'field.code_name': ' ',
    ...     'field.summary': ' ',
    ...     'field.actions.register': 'Register Milestone',
    ...     }
    >>> view = create_initialized_view(
    ...     firefox_1_0, '+addmilestone', form=form)
    >>> for milestone in firefox_1_0.milestones:
    ...     print(milestone.name, milestone.code_name, milestone.summary)
    2.1 None None
    1.1 None None


Distroseries driver and milestones
----------------------------------

The driver of a series that doesn't manage its packages in Ubuntu is a
release manager and can create milestones.

    >>> distroseries = factory.makeDistroSeries(name='pumpkin')
    >>> driver = factory.makePerson(name='a-driver')
    >>> ignored = login_person(distroseries.distribution.owner)
    >>> distroseries.driver = driver
    >>> ignored = login_person(driver)

    >>> form = {
    ...     'field.name': 'pie',
    ...     'field.actions.register': 'Register Milestone',
    ...     }
    >>> view = create_initialized_view(
    ...     distroseries, '+addmilestone', form=form)
    >>> milestone = distroseries.milestones[0]
    >>> print(milestone.name)
    pie

The driver has access to the milestone.

    >>> view = create_initialized_view(milestone, '+edit')
    >>> check_permission('launchpad.Edit', view)
    True

The driver of a series that does have packages cannot create a
milestone.

    >>> ignored = login_person(ubuntu_distro.owner.teamowner)
    >>> hoary_series.driver = driver
    >>> ignored = login_person(driver)

    >>> view = create_initialized_view(hoary_series, '+addmilestone')
    >>> check_permission('launchpad.Edit', view)
    False

Nor can the driver edit it.

    >>> milestone = factory.makeMilestone(distribution=ubuntu_distro)
    >>> view = create_initialized_view(milestone, '+edit')
    >>> check_permission('launchpad.Edit', view)
    False


Deleting milestones
-------------------

The DeleteMilestoneView allows users to edit permissions to delete
Milestones. The view is restricted to owners of the project and drivers
of the series.

    >>> ignored = login_person(owner)
    >>> milestone = firefox_1_0.newMilestone('1.0.10')
    >>> print(milestone.name)
    1.0.10

    >>> view = create_initialized_view(milestone, '+delete')
    >>> check_permission('launchpad.Edit', view)
    True

The view provides a few properties to access the dependent artifacts.
This milestone does not have any bugtasks, specifications, a product
release or product release files.

    >>> view.bugtasks
    []

    >>> view.specifications
    []

    >>> print(view.product_release)
    None

    >>> view.product_release_files
    []

The milestone is deleted when the delete action is called.

    >>> form = {
    ...     'field.actions.delete': 'Delete Milestone',
    ...     }
    >>> view = create_initialized_view(milestone, '+delete', form=form)
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    Milestone 1.0.10 deleted.

    >>> print(firefox.getMilestone('1.0.10'))
    None

The view will delete the dependent product release and release files if
they exist. It will also untarget bugtasks and specifications from the
milestone.

    >>> from datetime import datetime
    >>> from pytz import UTC

    >>> milestone = firefox_1_0.newMilestone('1.0.11')
    >>> release = milestone.createProductRelease(
    ...     owner, datetime.now(UTC))
    >>> release_file = release.addReleaseFile(
    ...     'test', b'test', 'text/plain', owner, description="test file")
    >>> specification = factory.makeSpecification(product=firefox)
    >>> specification.milestone = milestone
    >>> bug = factory.makeBug(target=firefox)
    >>> bugtask = bug.bugtasks[0]
    >>> bugtask.milestone = milestone
    >>> subscription = milestone.addSubscription(owner, owner)
    >>> [subscription for subscription in owner.structural_subscriptions]
    [<...StructuralSubscription ...>]

    >>> view = create_initialized_view(milestone, '+delete')
    >>> for bugtask in view.bugtasks:
    ...     print(bugtask.milestone.name)
    1.0.11

    >>> for spec in view.specifications:
    ...     print(spec.milestone.name)
    1.0.11

    >>> print(view.product_release.version)
    1.0.11

    >>> for file_ in view.product_release_files:
    ...     print(file_.description)
    test file

    >>> view = create_initialized_view(milestone, '+delete', form=form)
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    Milestone 1.0.11 deleted.

    >>> print(firefox.getMilestone('1.0.11'))
    None

    >>> print(firefox_1_0.getRelease('1.0.11'))
    None

    >>> print(specification.milestone)
    None

    >>> print(bugtask.milestone)
    None

    >>> [subscription for subscription in owner.structural_subscriptions]
    []

No Privileges Person cannot access this view because they are neither the
project owner or series driver.

    >>> milestone = firefox_1_0.newMilestone('1.0.12')
    >>> ignored = login_person(no_priv)
    >>> view = create_initialized_view(milestone, '+delete')
    >>> check_permission('launchpad.Edit', view)
    False

Milestones with private bugs can be deleted. There is one caveate, the person
deleting the milestone must have permssion to access the bug for it to be
untargeted. It is possible for the owner or release manager to not have access
to a private bug that was targeted to a milestone by a driver.

    >>> ignored = login_person(owner)
    >>> milestone = firefox_1_0.newMilestone('1.0.13')
    >>> from lp.app.enums import InformationType
    >>> private_bug = factory.makeBug(
    ...     target=firefox, information_type=InformationType.USERDATA)
    >>> private_bugtask = bug.bugtasks[0]
    >>> private_bugtask.milestone = milestone
    >>> view = create_initialized_view(milestone, '+delete')
    >>> for bugtask in view.bugtasks:
    ...     print(bugtask.milestone.name)
    1.0.13

    >>> view = create_initialized_view(milestone, '+delete', form=form)
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    Milestone 1.0.13 deleted.

    >>> transaction.commit()
    >>> print(private_bugtask.milestone)
    None
