Adding BugTasks
===============

If a bug occurs in more than one place, you can request a fix in some
other software. You can request a fix in either a product or a
distribution. Let's start with a product, this is done using
+choose-affected-product, where you choose the actual product the bug
affects and creates the new bugtask.

    >>> login('test@canonical.com')
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> bug_four = getUtility(IBugSet).get(4)
    >>> len(bug_four.bugtasks)
    1
    >>> firefox_task = bug_four.bugtasks[0]

The views registered at +choose-affected-product and +distrotask are in
fact meta views responsible for calling other views in order to guide the
user through the workflow.  The following is a helper function that makes
sure the view is set up properly and returns the actual view rather than
our meta view.

    >>> def get_and_setup_view(context, name, form, method='POST'):
    ...     view = create_view(context, name, form=form, method=method)
    ...     view.initialize()
    ...     # We don't care about the actual rendering of the page, so we
    ...     # override the index template.
    ...     view.view.index = lambda: u''
    ...     return view.view
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form={}, method='GET')


We haven't posted the form, so we'll see one button.

    >>> for action in add_task_view.actions:
    ...     print(action.label)
    Continue

Since we gave the view an upstream product as its context, it can't
guess which product we want to add, so it will ask us to specify it.

    >>> print(add_task_view.widgets['product']._getFormInput())
    None
    >>> add_task_view.step_name
    'choose_product'

It also didn't add any notification prompting us to add packaging
information.

    >>> add_task_view.request.response.notifications
    []


If we POST the form without entering any information, it will complain
that product is required:

    >>> form = {
    ...     'field.actions.continue': '', 'field.product': '',
    ...     'field.__visited_steps__': 'choose_product'}
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    >>> print(add_task_view.getFieldError('product'))
    Required input is missing.


If we supply a valid product, it will move on to the next step.

    >>> form = {
    ...     'field.actions.continue': '', 'field.product': 'evolution',
    ...     'field.add_packaging': 'off',
    ...     'field.__visited_steps__': 'choose_product'}
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    >>> add_task_view.step_name
    'specify_remote_bug_url'

The URL widget is focused, to make it easier to paste the URL directly.

    >>> add_task_view.initial_focus_widget
    'bug_url'

If the validation fails, an error will be displayed.

    >>> form = {
    ...     'field.actions.continue': '', 'field.product': 'firefox',
    ...     'field.__visited_steps__': 'choose_product'}
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    >>> add_task_view.step_name
    'choose_product'
    >>> print(add_task_view.getFieldError('product'))
    A fix for this bug has already been requested for Mozilla Firefox


When adding a product from an upstream task, we always have to choose
the product manually, since it's hard to guess which product that is
most likely to get added. Let's take a look how it works for packages,
which can have packaging links that helps us choose the product.

    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> owner = getUtility(ILaunchBag).user
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> ubuntu_firefox = ubuntu.getSourcePackage('mozilla-firefox')
    >>> create_params = CreateBugParams(
    ...     owner, "Upstream bug", comment="An upstream bug.")
    >>> firefox_bug = ubuntu_firefox.createBug(create_params)
    >>> ubuntu_firefox_task = firefox_bug.bugtasks[0]


If we go to +choose-affected-product from the newly created bug task,
we immediately get directed to the next step with the correct upstream
selected.

    >>> add_task_view = get_and_setup_view(
    ...     ubuntu_firefox_task, '+choose-affected-product', form={},
    ...     method='GET')
    >>> add_task_view.step_name
    'specify_remote_bug_url'
    >>> print(add_task_view.widgets['product'].getInputValue().name)
    firefox

If some package doesn't have a packaging link, a product will have to
be chosen manually, and the user may choose to link the package to the
project..

    >>> ubuntu_thunderbird = ubuntu.getSourcePackage('thunderbird')
    >>> ignore = factory.makeSourcePackagePublishingHistory(
    ...     distroseries=ubuntu.currentseries,
    ...     sourcepackagename=ubuntu_thunderbird.sourcepackagename)
    >>> thunderbird_bug = ubuntu_thunderbird.createBug(create_params)
    >>> ubuntu_thunderbird_task = thunderbird_bug.bugtasks[0]

    >>> add_task_view = get_and_setup_view(
    ...     ubuntu_thunderbird_task, '+choose-affected-product', form={},
    ...     method='GET')

    >>> add_task_view.step_name
    'choose_product'
    >>> add_task_view.field_names
    ['product', 'add_packaging', '__visited_steps__']

    >>> print(add_task_view.widgets['product']._getFormInput())
    None

Sometimes the distribution won't have any series, though. In that
case, we won't prompt the user to add a link, since they can't actually
add one.

    >>> gentoo = getUtility(IDistributionSet).getByName('gentoo')
    >>> gentoo.currentseries is None
    True
    >>> gentoo_thunderbird = gentoo.getSourcePackage('thunderbird')
    >>> thunderbird_bug = gentoo_thunderbird.createBug(create_params)
    >>> gentoo_thunderbird_task = thunderbird_bug.bugtasks[0]

    >>> add_task_view = get_and_setup_view(
    ...     gentoo_thunderbird_task, '+choose-affected-product', form={},
    ...     method='GET')
    >>> add_task_view.step_name
    'choose_product'
    >>> print(add_task_view.widgets['product']._getFormInput())
    None

    >>> len(add_task_view.request.response.notifications)
    0

Let's take a look at the second step now, where we may enter the URL of
the remote bug and confirm the bugtask creation.
In order to show that all the events get fired off, let's create an
event listener and register it:

    >>> from zope.interface import Interface
    >>> from lazr.lifecycle.interfaces import IObjectCreatedEvent
    >>> from lp.testing.fixture import ZopeEventHandlerFixture

    >>> def on_created_event(object, event):
    ...     print("ObjectCreatedEvent: %r" % object)

    >>> on_created_listener = ZopeEventHandlerFixture(
    ...     on_created_event, (Interface, IObjectCreatedEvent))
    >>> on_created_listener.setUp()


If an invalid product is specified, or a product that fails the
validation (for example, a bugtask for that product already exists),
the user will be kept in the first step and asked to choose the product.

Note that for the form of the second step to be processed we have to
include its (and all previous) step_name in field.__visited_steps__.

    >>> form = {
    ...     'field.actions.continue': '1',
    ...     'field.product': u'no-such-product',
    ...     'field.add_packaging': 'off',
    ...     'field.__visited_steps__':
    ...         'choose_product|specify_remote_bug_url',
    ...     }
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    >>> add_task_view.step_name
    'choose_product'
    >>> print(add_task_view.widgets['product']._getFormInput())
    no-such-product

    >>> form['field.product'] = u'firefox'
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    >>> add_task_view.step_name
    'choose_product'
    >>> print(add_task_view.widgets['product']._getFormInput())
    firefox

If we specify a valid product, no errors will occur, and a bugtask will
be created:

    >>> form['field.product'] = u'evolution'
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    ObjectCreatedEvent: <BugTask ...>

    >>> for bugtask in bug_four.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    Evolution
    Mozilla Firefox

This worked without any problems since Evolution does use Malone as its
offical bug tracker.

    >>> evolution_task = bug_four.bugtasks[0]
    >>> evolution_task.target.bug_tracking_usage
    <DBItem ServiceUsage.LAUNCHPAD, (20) Launchpad>

    >>> transaction.commit()

If we try to add a task for ALSA, which doesn't use Malone, it won't go
as smoothly as above.

    >>> form['field.product'] = u'alsa-utils'
    >>> form['field.link_upstream_how'] = u'LINK_UPSTREAM'
    >>> form['field.bug_url'] = u''
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)

    >>> add_task_view.step_name
    'specify_remote_bug_url'
    >>> print(add_task_view.widgets['product']._getFormInput())
    alsa-utils

As you can see, we're still in the second step, because the user has
tried to create a bugtask without a bug watch.

    >>> len(add_task_view.errors)
    1
    >>> print(add_task_view.getFieldError('bug_url'))
    Required input is missing.
    >>> add_task_view.next_url is None
    True

The user must explictly choose to create a bugtask without a bug
watch.

    >>> form['field.link_upstream_how'] = u'UNLINKED_UPSTREAM'
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    ObjectCreatedEvent: <BugTask ...>
    >>> print(add_task_view.notifications)
    []
    >>> add_task_view.next_url is not None
    True

    >>> for bugtask in bug_four.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    alsa-utils
    Evolution
    Mozilla Firefox

But since no bug watch was specified, the status and importance
are set to the default values.

    >>> alsa_task = bug_four.bugtasks[0]
    >>> alsa_task.target.bug_tracking_usage
    <DBItem ServiceUsage.UNKNOWN, (10) Unknown>
    >>> alsa_task.status.title
    'New'
    >>> alsa_task.importance.title
    'Undecided'

On the same form, we can add a bug watch, by specifying the remote bug
URL. If we don't enter a valid URL, we get an error message.

    >>> form['field.product'] = u'gnome-terminal'
    >>> form['field.link_upstream_how'] = u'LINK_UPSTREAM'
    >>> form['field.bug_url'] = u'not-a-url'
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    >>> add_task_view.step_name
    'specify_remote_bug_url'
    >>> print(add_task_view.getFieldError('bug_url'))
    Launchpad does not recognize the bug tracker at this URL.

Note that this caused the transaction to be aborted, thus the
alsa-utils bugtask added earlier is now gone:

    >>> for bugtask in bug_four.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    Evolution
    Mozilla Firefox

If the URL is valid but there's no bugtracker registered with that URL,
we ask the user if they want to register the bugtracker as well.

    >>> form['field.product'] = u'aptoncd'
    >>> form['field.bug_url'] = (
    ...     u'http://bugzilla.somewhere.org/bugs/show_bug.cgi?id=84')
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    >>> add_task_view.step_name
    'bugtracker_creation'

Confirming the bugtracker creation will cause the new task to be added and
linked to the new bug watch.

    >>> form['field.__visited_steps__'] += "|%s" % add_task_view.step_name
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    ObjectCreatedEvent: <BugWatch at ...>
    ObjectCreatedEvent: <BugTask ...>

    >>> for bugtask in bug_four.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    APTonCD
    Evolution
    Mozilla Firefox

    >>> for bugwatch in bug_four.watches:
    ...     print("%s: %s" % (bugwatch.bugtracker.title, bugwatch.remotebug))
    bugzilla.somewhere.org/bugs/: 84

If we specify a URL of an already registered bug tracker, both the task
and the bug watch will be added without any confirmation needed:

    >>> form['field.product'] = u'alsa-utils'
    >>> form['field.bug_url'] = (
    ...     u'http://bugzilla.gnome.org/bugs/show_bug.cgi?id=84')
    >>> form['field.__visited_steps__'] = (
    ...     "choose_product|specify_remote_bug_url")
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    ObjectCreatedEvent: <BugWatch at ...>
    ObjectCreatedEvent: <BugTask ...>

    >>> print(add_task_view.notifications)
    []

    >>> for bugtask in bug_four.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    alsa-utils
    APTonCD
    Evolution
    Mozilla Firefox

    >>> for bugwatch in bug_four.watches:
    ...     print("%s: %s" % (bugwatch.bugtracker.title, bugwatch.remotebug))
    GnomeGBug GTracker: 84
    bugzilla.somewhere.org/bugs/: 84

The bug watch got linked to the created task, and all the bug task's
attributes got initialized to Unknown. The bugtask will be synced with
the bug watch's status later.

    >>> alsa_task = bug_four.bugtasks[0]
    >>> print(alsa_task.bugtargetname)
    alsa-utils
    >>> alsa_task.product.bug_tracking_usage
    <DBItem ServiceUsage.UNKNOWN, (10) Unknown>
    >>> alsa_task.bugwatch == bug_four.watches[0]
    True

    >>> alsa_task.status.title
    'Unknown'
    >>> alsa_task.importance.title
    'Unknown'

If the same bug watch is added to another bug, the bug watch will be
added, but a notification is shown to the user informing them that
another bug links to the same bug.

    >>> bug_five = getUtility(IBugSet).get(5)
    >>> bug_five_task = bug_five.bugtasks[0]
    >>> add_task_view = get_and_setup_view(
    ...     bug_five_task, '+choose-affected-product', form)
    ObjectCreatedEvent: <BugWatch at ...>
    ObjectCreatedEvent: <BugTask ...>

    >>> add_task_view.request.response.getHeader('Location')
    'http://.../+bug/5'

    >>> for notification in add_task_view.request.response.notifications:
    ...     print(notification.message)
    <a href="...">Bug #4</a> also links to the added bug watch
    (gnome-bugzilla #84).

    >>> for bugwatch in bug_five.watches:
    ...     print("%s: %s" % (bugwatch.bugtracker.title, bugwatch.remotebug))
    GnomeGBug GTracker: 84

There's a property for easily retrieving the target for use on the
confirmation page.

    >>> form['field.link_upstream_how'] = u'UNLINKED_UPSTREAM'
    >>> form['field.bug_url'] = u''
    >>> form['field.product'] = u'thunderbird'
    >>> form['field.__visited_steps__'] = u'choose_product'
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)
    >>> add_task_view.errors
    []
    >>> print(add_task_view.getTarget().displayname)
    Mozilla Thunderbird

If we request a fix in a source package, the distribution's display
name is returned.

    >>> form = {
    ...     'field.distribution': u'debian',
    ...     'field.sourcepackagename': u'evolution'}
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+distrotask', form)
    >>> print(add_task_view.getTarget().displayname)
    Debian


The form also accept binary package names to be entered. The binary
package will be converted to the corresponding source package.

    >>> form = {
    ...     'field.distribution': u'ubuntu',
    ...     'field.actions.continue': '1',
    ...     'field.sourcepackagename': u'mozilla-firefox-data'}
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+distrotask', form)
    ObjectCreatedEvent: <BugTask ...>
    >>> add_task_view.errors
    []

    >>> for bugtask in bug_four.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    alsa-utils
    ...
    mozilla-firefox (Ubuntu)

    >>> on_created_listener.cleanUp()


Registering a product while adding a bugtask
============================================

One of the facilities we have when adding a bugtask is the option to target it
to a newly registered product.  When that option is used, though, we use the
URL of the remote bug to check if the product is not already registered and
present these already-registered products as options to the user.

    >>> form = {
    ...     'field.actions.continue': '1',
    ...     'field.bug_url': 'http://bugs.foo.org/bugs/show_bug.cgi?id=8',
    ...     'field.name': 'foo-product',
    ...     'field.display_name': 'The Foo Product',
    ...     'field.summary': 'The Foo Product'}
    >>> add_task_view = create_view(
    ...     firefox_task, '+affects-new-product', form=form, method='POST')
    >>> add_task_view.initialize()

We have no products using http://bugs.foo.org as its bug tracker, so we have
nothing to present to the user.

    >>> print(add_task_view.existing_products)
    None

Since the user is just creating the product in Launchpad to link to an
upstream they probably aren't interested in maintaining the product for
the long-term.  In recognition of that we set the maintainer to be the
Registry Admins team while keeping the user as the registrant.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> foo_product = getUtility(IProductSet).getByName('foo-product')
    >>> print(foo_product.owner.displayname)
    Registry Administrators
    >>> print(foo_product.registrant.displayname)
    Sample Person

The licence is set to DONT_KNOW for now.
    >>> [license.name for license in foo_product.licenses]
    ['DONT_KNOW']

If the user tries to register another product using a bug URL under
bugs.foo.org, we'll present 'The Foo Product' as a candidate.

    >>> flush_database_updates()
    >>> form['field.name'] = 'bar-product'
    >>> form['field.display_name'] = 'The Bar'
    >>> form['field.summary'] = 'The Bar'
    >>> add_task_view = create_view(
    ...     firefox_task, '+affects-new-product', form=form, method='POST')
    >>> add_task_view.initialize()
    >>> for product in add_task_view.existing_products:
    ...     print(product.name)
    foo-product

    # Now we choose to register the product anyway, as it's not one of the
    # existing ones.
    >>> form['create_new'] = '1'
    >>> add_task_view = create_view(
    ...     firefox_task, '+affects-new-product', form=form, method='POST')
    >>> add_task_view.initialize()

There's a limit on the number of existing products we present to the user in
this way, though.  If there are too many products using a given bugtracker,
we'll present only the ones whose name is similar to what the user entered.

    >>> flush_database_updates()
    >>> dummy = form.pop('create_new')
    >>> form['field.name'] = u'foo'
    >>> form['field.display_name'] = 'Foo, the return'
    >>> form['field.summary'] = 'Foo'
    >>> add_task_view = create_view(
    ...     firefox_task, '+affects-new-product', form=form, method='POST')
    >>> add_task_view.initialize()
    >>> add_task_view.MAX_PRODUCTS_TO_DISPLAY
    10
    >>> for product in add_task_view.existing_products:
    ...     print(product.name)
    bar-product
    foo-product

    >>> add_task_view = create_view(
    ...     firefox_task, '+affects-new-product', form=form, method='POST')
    >>> add_task_view.MAX_PRODUCTS_TO_DISPLAY = 1
    >>> add_task_view.initialize()
    >>> for product in add_task_view.existing_products:
    ...     print(product.name)
    foo-product

Here another user will choose to report a bug on the existing project.
Note that we use another user to make sure our code doesn't attempt to
change the bugtracker of the existing project, as that wouldn't make
sense and could fail when the user didn't have the necessary rights on the
project in question.

    >>> login('no-priv@canonical.com')
    >>> dummy = form.pop('field.actions.continue')
    >>> form['field.existing_product'] = 'foo-product'
    >>> form['field.actions.use_existing_product'] = 1
    >>> bugtask_one = getUtility(IBugSet).get(1).bugtasks[0]
    >>> add_task_view = create_view(
    ...     bugtask_one, '+affects-new-product', form=form, method='POST')
    >>> add_task_view.initialize()
    >>> add_task_view.errors
    []
    >>> login('test@canonical.com')


IAddBugTaskForm Interface Definition
====================================

IAddBugTaskForm, which is used as the schema for the views tested above,
has some attributes which are identical to those of IBugTask However, we
must ensure that IAddBugTask defines its own attributes rather than
borrowing those of IBugTask, since doing so has produced OOPSes (bug
129406).

    >>> from lp.bugs.interfaces.bugtask import (
    ...     IAddBugTaskForm,
    ...     IBugTask,
    ...     )
    >>> IAddBugTaskForm['product'] is IBugTask['product']
    False

    >>> IAddBugTaskForm['distribution'] is IBugTask['distribution']
    False

    >>> IAddBugTaskForm['sourcepackagename'] is IBugTask['sourcepackagename']
    False



Getting the upstream bug filing URL for a product
=================================================

Products that don't use Launchpad for bug tracking can be linked to
external bug trackers. In order to make it easier for users to file bugs
on upstream bug trackers, it's possible to get the bug filing and search
URLs for a Product's upstream bug tracker using its
`upstream_bugtracker_links` property.

We'll link a product to an upstream bug tracker to demonstrate this.

    >>> login('foo.bar@canonical.com')
    >>> bugtracker = factory.makeBugTracker('http://example.com')
    >>> product = factory.makeProduct(name='frobnitz')
    >>> product.official_malone = False
    >>> product.bugtracker = bugtracker
    >>> product.remote_product = u'foo'

    >>> def print_links(links_dict):
    ...     if links_dict is None:
    ...         print(None)
    ...         return
    ...
    ...     for key in sorted(links_dict):
    ...         print("%s: %s" % (key, links_dict[key]))

upstream_bugtracker_links is a dict of `bug_filing_url` and `bug_search_url`.
The bug filing link includes the summary and description of the bug; the
search link includes the summary only.

    >>> form = {
    ...     'field.actions.continue': '', 'field.product': 'frobnitz',
    ...     'field.add_packaging': 'off',
    ...     'field.__visited_steps__': 'choose_product'}
    >>> add_task_view = get_and_setup_view(
    ...     firefox_task, '+choose-affected-product', form)

    >>> print_links(add_task_view.upstream_bugtracker_links)
    bug_filing_url:
    ...?product=foo&short_desc=Reflow%20...&long_desc=Originally%20...
    bug_search_url: ...query.cgi?product=foo&short_desc=Reflow%20problems...

If the product's `bugtracker` isn't specified its
`upstream_bugtracker_links` property will be None.

    >>> product.bugtracker = None
    >>> print_links(add_task_view.upstream_bugtracker_links)
    None

Similarly, if the product's `remote_product` attribute is None and its
bug tracker is one which requires an upstream product, bug bug_filing_url
and bug_search_url will be None.

    >>> product.bugtracker = bugtracker
    >>> product.remote_product = None
    >>> print_links(add_task_view.upstream_bugtracker_links)
    bug_filing_url: None
    bug_search_url: None

However, some remote bug trackers, notably Trac, only track one product
at a time. They don't need a remote product in order to provide a bug
filing URL, so the `upstream_bugtracker_links` for products linked to such
bug trackers will always be a usable URL.

    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> trac_bugtracker = factory.makeBugTracker(
    ...     'http://trac.example.com', BugTrackerType.TRAC)
    >>> product.bugtracker = trac_bugtracker

    >>> print_links(add_task_view.upstream_bugtracker_links)
    bug_filing_url: http://trac.example.com/newticket?summary=Reflow%20...
    bug_search_url: http://trac.example.com/search?ticket=on&q=Reflow%20...
