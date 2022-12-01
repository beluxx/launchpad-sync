Builder View Classes and Pages
==============================

    >>> from zope.component import getMultiAdapter, getUtility
    >>> from lp.buildmaster.interfaces.builder import IBuilderSet
    >>> from lp.soyuz.interfaces.binarypackagebuild import (
    ...     IBinaryPackageBuildSet,
    ... )
    >>> from lp.services.webapp.servers import LaunchpadTestRequest

    >>> login(ANONYMOUS)
    >>> builder = getUtility(IBuilderSet).get(1)

Get a "mock" request:

    >>> mock_form = {}
    >>> request = LaunchpadTestRequest(form=mock_form)

Let's instantiate the view for +index:

    >>> builder_view = getMultiAdapter((builder, request), name="+index")

    >>> print(builder_view.page_title)
    Builder ...Bob The Builder...

The BuilderView provides a helper for the text to use on the toggle
mode button.

    >>> print(builder_view.toggle_mode_text)
    Switch to manual-mode


Builder history
---------------

Let's instantiate a view for +history:

    >>> builder_view = getMultiAdapter((builder, request), name="+history")
    >>> print(builder_view.page_title)
    Build history

    setupBuildList, build a batched list of build records and store it
    in view.batch, also store the batch navigator in view.batchnav. it
    simply returns None:

    >>> builder_view.setupBuildList()

As expected we have a 'batched' list with the size requested in
mock_form:

    >>> len(builder_view.batchnav.currentBatch())
    5


Builder edit
------------

Let's instantiate the view for +edit and check that the correct title,
fields and actions are displayed:

This page requires launchpad.Edit permission and the builder is owned
by mark. we nee to log in as mark or any other member of admin team

    >>> from lp.testing.views import create_initialized_view
    >>> login("foo.bar@canonical.com")
    >>> builder_view = create_initialized_view(builder, name="+edit")
    >>> print(builder_view.page_title)
    Change details for builder ...Bob The Builder...

    >>> for field_name in builder_view.field_names:
    ...     print(field_name)
    ...
    name
    title
    processors
    url
    manual
    owner
    virtualized
    builderok
    failnotes
    vm_host
    vm_reset_protocol
    open_resources
    restricted_resources
    active

    >>> for action in builder_view.actions:
    ...     print(action.label)
    ...
    Change

The BuilderEditView also has a next_url property for redirecting after
a successful form submission.

    >>> print(builder_view.next_url)
    http://launchpad.test/builders/bob

The BuilderEditView can be used to update the relevant fields on the
builder.

    >>> def print_builder_info(builder):
    ...     print(
    ...         "%s: manual=%s, vm_host=%s."
    ...         % (
    ...             builder.name,
    ...             builder.manual,
    ...             builder.vm_host,
    ...         )
    ...     )
    ...
    >>> print_builder_info(builder)
    bob: manual=False, vm_host=None.

    >>> builder_view = create_initialized_view(
    ...     builder,
    ...     name="+edit",
    ...     method="POST",
    ...     form={
    ...         "field.name": "biscoito",
    ...         "field.manual": "on",
    ...         "field.vm_host": "foobar-host.ppa",
    ...         "field.actions.update": "Change",
    ...     },
    ... )

    >>> print_builder_info(builder)
    biscoito: manual=True, vm_host=foobar-host.ppa.

After editing a builder, a relevant notification is added to the view.

    >>> for notification in builder_view.request.notifications:
    ...     print(notification.message)
    ...
    The builder &quot;Bob The Builder&quot; was updated successfully.


Builders building private jobs
------------------------------

In order to restrict access to private PPA details in general, we also
need to be able to hide the fact that a builder is building a private
PPA job.

This feature is evaluated on the view layer, since it varies according
to the user who is trying to access a given content.

Before checking if it works as expected we will setup an environment
where builder 'Frog' is building a job from Celso's private PPA.

    >>> from lp.buildmaster.interfaces.builder import IBuilderSet
    >>> from lp.buildmaster.model.buildqueue import BuildQueue
    >>> from lp.registry.interfaces.person import IPersonSet

    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> cprov_private_ppa = factory.makeArchive(owner=cprov, private=True)

SoyuzTestPublisher is used to make a new publication only in Celso's
private PPA.

    >>> from lp.buildmaster.enums import BuildStatus
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> from lp.soyuz.enums import PackagePublishingStatus

    >>> test_publisher = SoyuzTestPublisher()
    >>> test_publisher.prepareBreezyAutotest()
    >>> private_source_pub = test_publisher.getPubSource(
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     sourcename="privacy-test",
    ...     archive=cprov_private_ppa,
    ... )
    >>> [private_build] = private_source_pub.createMissingBuilds()

Assign the build to the 'frog' builder:

    >>> frog = getUtility(IBuilderSet)["frog"]
    >>> frog.builderok = True
    >>> private_build.updateStatus(BuildStatus.BUILDING, builder=frog)
    >>> private_job = private_build.buildqueue_record
    >>> private_job.builder = frog
    >>> private_job_id = private_job.id

    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> flush_database_caches()

At the content class level, all the information about the current job
is widely available:

 * Frog is OK;
 * Frog 'currentjob' exists;
 * Frog has no 'failnotes';

    >>> print(frog.builderok)
    True

    >>> build_set = getUtility(IBinaryPackageBuildSet)
    >>> build = build_set.getByQueueEntry(frog.currentjob)
    >>> print(build.title)
    i386 build of privacy-test 666 in ubuntutest breezy-autotest RELEASE

    >>> print(frog.failnotes)
    None

Accessing the view for $builder/+index as a Foo Bar, which has
launchpad.View permission on the target archive of the 'currentjob',
all the 'private' information is exposed.

    >>> import transaction
    >>> transaction.commit()
    >>> login("foo.bar@canonical.com")

    >>> empty_request = LaunchpadTestRequest(form={})
    >>> admin_view = getMultiAdapter((frog, empty_request), name="+index")

    >>> print(admin_view.context.builderok)
    True

    >>> build = build_set.getByQueueEntry(admin_view.context.currentjob)
    >>> print(build.title)
    i386 build of privacy-test 666 in ubuntutest breezy-autotest RELEASE

    >>> print(admin_view.context.failnotes)
    None

    >>> import datetime
    >>> import pytz
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(private_job).date_started = datetime.datetime.now(
    ...     pytz.UTC
    ... ) - datetime.timedelta(10)
    >>> print(admin_view.current_build_duration)
    10 days...

Once the private job is gone, Frog 'real' details are exposed publicly
again.

    >>> from storm.store import Store
    >>> store = Store.of(frog)
    >>> login("foo.bar@canonical.com")
    >>> private_job = store.get(BuildQueue, private_job_id)
    >>> private_job.builder = None

    >>> login("no-priv@canonical.com")
    >>> nopriv_view = getMultiAdapter((frog, empty_request), name="+index")

    >>> login(ANONYMOUS)


BuilderSet view
---------------

BuilderSetView offer a way to treat the currently registered builders
in categories. They are:

 * 'Non-virtual build machines': a group of builders capable of building
   'trusted' sources, Ubuntu official packages. The 'non-virtualized'
   build-farm.

 * 'Virtual build machines': a group of builders capable of building
   'untrusted' sources, PPA packages. The 'virtualized' build-farm.

    >>> from lp.buildmaster.interfaces.builder import IBuilderSet
    >>> builderset = getUtility(IBuilderSet)

    >>> builderset_view = getMultiAdapter(
    ...     (builderset, empty_request), name="+index"
    ... )

In order to have a proper dataset for the tests we will populate the
builder table with several builders for different categories and
architectures.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> cprov = getUtility(IPersonSet).getByName("cprov")

    >>> from lp.buildmaster.model.processor import Processor
    >>> i386 = Processor.selectOneBy(name="386")
    >>> amd64 = Processor.selectOneBy(name="amd64")
    >>> hppa = Processor.selectOneBy(name="hppa")

    >>> ignored = factory.makeBuilder(
    ...     name="hamburger", processors=[i386], virtualized=True
    ... )
    >>> ignored = factory.makeBuilder(
    ...     name="cheese", processors=[hppa], virtualized=True
    ... )
    >>> ignored = factory.makeBuilder(
    ...     name="bacon", processors=[amd64], virtualized=True
    ... )
    >>> ignored = factory.makeBuilder(
    ...     name="egg", processors=[i386], virtualized=False
    ... )
    >>> ignored = factory.makeBuilder(
    ...     name="ham", processors=[hppa], virtualized=False, manual=True
    ... )
    >>> ignored = factory.makeBuilder(
    ...     name="prosciuto", processors=[amd64], virtualized=False
    ... )

Newly created builders will be in manual mode because we don't want
them going straight into the build farm until tested.

    >>> ham = builderset.getByName("ham")
    >>> ham.manual
    True

The 'Other' builder category is a `BuilderCategory` class, which
contains the following attributes:

 * title: the title that will be presented for this category in the UI;

 * virtualized: whether the category represents the virtualized or
   non-virtualized build-farm;

 * groups: a property that return all `BuilderGroup` instanced
   available in this category ordered by processor name.

    >>> builder_category = builderset_view.nonvirt_builders

    >>> print(builder_category)
    <...BuilderCategory ...>

    >>> print(builder_category.title)
    Non-virtual build status

    >>> print(builder_category.virtualized)
    False

    >>> print(builder_category.groups[0])
    <...BuilderGroup ...>

Similarly to what is done in the UI, we have a helper that prints the
grouped builders within a category in a easy manner.

    >>> def print_category(category):
    ...     for group in category.groups:
    ...         print(
    ...             group.processor_name,
    ...             group.number_of_available_builders,
    ...             group.queue_size,
    ...             group.duration,
    ...         )
    ...

    >>> print_category(builder_category)
    386    2  1  0:00:30
    amd64  1  0  None
    hppa   1  0  None

Each `BuilderGroup` contains the following attributes:

 * processor_name: the `Processor` name of all builders in this group;

 * number_of_available_builders: the number of builders available for
       this processor.

 * queue_size: the number of jobs wainting to be processed for one of
   the builders in this group

 * duration: estimated time that will be used to build all jobs in
       queue (sum(job_duration)/number_of_available_builders)

    >>> [i386_group, amd64_group, hppa_group] = builder_category.groups

    >>> print(i386_group.processor_name)
    386

    >>> print(i386_group.number_of_available_builders)
    2

    >>> print(i386_group.queue_size)
    1

    >>> print(i386_group.duration)
    0:00:30

The 'virtual' builder category is also available in BuilderSetView as a
`BuilderCategory`.

    >>> builder_category = builderset_view.virt_builders

    >>> print(builder_category.title)
    Virtual build status

    >>> print(builder_category.virtualized)
    True

    >>> print_category(builder_category)
    386    2  1  0:00:30
    amd64  1  0  None
    hppa   1  0  None

We change the sampledata to create a pending build in for the 386
processor queue in the PPA category.

    >>> import datetime
    >>> login("foo.bar@canonical.com")
    >>> any_failed_build = cprov.archive.getBuildRecords(
    ...     build_state=BuildStatus.FAILEDTOBUILD
    ... )[0]
    >>> one_minute = datetime.timedelta(seconds=60)
    >>> any_failed_build.retry()
    >>> removeSecurityProxy(
    ...     any_failed_build.buildqueue_record
    ... ).estimated_duration = one_minute
    >>> transaction.commit()
    >>> login(ANONYMOUS)

Now the pending build is included in the right category and group.

    >>> builderset_view = getMultiAdapter(
    ...     (builderset, empty_request), name="+index"
    ... )
    >>> builder_category = builderset_view.virt_builders
    >>> print_category(builder_category)
    386    2  2  0:01:00
    amd64  1  0  None
    hppa   1  0  None

The queue summary lists all processors built by any builder.

    >>> login("foo.bar@canonical.com")
    >>> frog.processors = [i386, hppa]
    >>> login(ANONYMOUS)
    >>> builderset_view = getMultiAdapter(
    ...     (builderset, empty_request), name="+index"
    ... )
    >>> builder_category = builderset_view.virt_builders
    >>> print_category(builder_category)
    386    2  2  0:01:00
    amd64  1  0  None
    hppa   2  0  None
