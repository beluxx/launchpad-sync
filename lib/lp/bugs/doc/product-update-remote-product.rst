Updating Product.remote_product
===============================

The remote_product attribute of a Product is used to present links for
filing and searching bugs in the Product's bug tracker, in case it's not
using Launchpad to track its bugs. We don't expect users to set the
remote_product themselves, so we have a script that tries to set this
automatically.

    >>> from lp.registry.model.product import Product
    >>> from lp.services.database.interfaces import IStore
    >>> store = IStore(Product)
    >>> store.execute("UPDATE Product SET remote_product = 'not-None'")
    <storm...>

    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> from lp.services.log.logger import FakeLogger, BufferLogger
    >>> from lp.bugs.scripts.updateremoteproduct import (
    ...     RemoteProductUpdater)
    >>> from lp.testing.faketransaction import FakeTransaction
    >>> updater = RemoteProductUpdater(FakeTransaction(), BufferLogger())


Testing
-------

To help testing, there is a method, _getExternalBugTracker(), that
creates the ExternalBugTracker for the given BugTracker.

    >>> rt = factory.makeBugTracker(
    ...     bugtrackertype=BugTrackerType.RT,
    ...     base_url=u'http://rt.example.com/')
    >>> rt_external = updater._getExternalBugTracker(rt)
    >>> rt_external.__class__.__name__
    'RequestTracker'
    >>> print(rt_external.baseurl)
    http://rt.example.com

For testing, _getExternalBugTracker() can be overridden to return an
ExternalBugTracker that doesn't require network access.

    >>> class FakeExternalBugTracker:
    ...
    ...     def initializeRemoteBugDB(self, bug_ids):
    ...         print("Initializing DB for bugs: [%s]." %
    ...             ", ".join("'%s'" % bug_id for bug_id in bug_ids))
    ...
    ...     def getRemoteProduct(self, remote_bug):
    ...         return 'product-for-bug-%s' % remote_bug


    >>> class NoNetworkRemoteProductUpdater(RemoteProductUpdater):
    ...
    ...     external_bugtracker_to_return = FakeExternalBugTracker
    ...
    ...     def _getExternalBugTracker(self, bug_tracker):
    ...         return self.external_bugtracker_to_return()


update()
--------

The update method simply loops over all the bug tracker types that can
track more than one product, and calls updateByBugTrackerType(). Any bug
tracker type that isn't specified as being for a single product is being
looped over. The EMAILADDRESS one is special, though. It could be used
for more than one product, but we have no way of interacting with it, so
it's skipped as well.

    >>> class TrackerTypeCollectingUpdater(RemoteProductUpdater):
    ...     def __init__(self):
    ...         self.logger = BufferLogger()
    ...         self.looped_over_bug_tracker_types = set()
    ...     def updateByBugTrackerType(self, bugtracker_type):
    ...         self.looped_over_bug_tracker_types.add(bugtracker_type)

    >>> from lp.bugs.interfaces.bugtracker import (
    ...     SINGLE_PRODUCT_BUGTRACKERTYPES)
    >>> multi_product_trackers = set(
    ...     bugtracker_type for bugtracker_type in BugTrackerType.items
    ...     if bugtracker_type not in SINGLE_PRODUCT_BUGTRACKERTYPES)
    >>> multi_product_trackers.remove(BugTrackerType.EMAILADDRESS)

    >>> updater = TrackerTypeCollectingUpdater()
    >>> updater.update()
    >>> for item in multi_product_trackers.symmetric_difference(
    ...         updater.looped_over_bug_tracker_types):
    ...     print(item)


updateByBugTrackerType()
------------------------

The updateByBugTrackerType() method looks at the bug watches that are
linked to the product, to decide what remote_product should be set to.
It accepts a single parameter, the type of the bug tracker that should
be updated.


No bug watches
..............

If there are no bug watches, nothing will be done.

    >>> bugzilla_product = factory.makeProduct(
    ...     name=u'bugzilla-product', official_malone=False)
    >>> bugzilla = factory.makeBugTracker(
    ...     bugtrackertype=BugTrackerType.BUGZILLA)
    >>> bugzilla_product.bugtracker = bugzilla
    >>> rt_product = factory.makeProduct(
    ...     name=u'rt-product', official_malone=False)
    >>> rt = factory.makeBugTracker(
    ...     bugtrackertype=BugTrackerType.RT)
    >>> rt_product.bugtracker = rt

    >>> list(bugzilla_product.getLinkedBugWatches())
    []
    >>> updater.updateByBugTrackerType(BugTrackerType.RT)
    >>> print(bugzilla_product.remote_product)
    None
    >>> print(rt_product.remote_product)
    None


Linked bug watches
..................

If there are bug watches for a product having a None remote_product, an
arbitrary bug watch will be retrieved, and queried for its remote
product. Products having a bug tracker of a different type than the
given one are ignored.

    >>> from lp.testing.dbuser import lp_dbuser

    >>> updater = NoNetworkRemoteProductUpdater(
    ...     FakeTransaction(), BufferLogger())

    >>> with lp_dbuser():
    ...     bugzilla_bugtask = factory.makeBugTask(target=bugzilla_product)
    ...     bugzilla_bugwatch = factory.makeBugWatch(
    ...         '42', bugtracker=bugzilla, bug=bugzilla_bugtask.bug)
    ...     bugzilla_bugtask.bugwatch = bugzilla_bugwatch
    ...     rt_bugtask = factory.makeBugTask(target=rt_product)
    ...     rt_bugwatch = factory.makeBugWatch(
    ...         '84', bugtracker=rt, bug=rt_bugtask.bug)
    ...     rt_bugtask.bugwatch = rt_bugwatch

    >>> updater.updateByBugTrackerType(BugTrackerType.RT)
    Initializing DB for bugs: ['84'].

    >>> print(rt_product.remote_product)
    product-for-bug-84

    >>> print(bugzilla_product.remote_product)
    None


remote_product already set
..........................

If a product already has remote_product set, it will not be updated.

    >>> with lp_dbuser():
    ...     rt_product = factory.makeProduct(official_malone=False)
    ...     rt = factory.makeBugTracker(
    ...         bugtrackertype=BugTrackerType.RT)
    ...     rt_product.bugtracker = rt
    ...     rt_bugtask = factory.makeBugTask(target=rt_product)
    ...     rt_bugwatch = factory.makeBugWatch(
    ...         '84', bugtracker=rt, bug=rt_bugtask.bug)
    ...     rt_bugtask.bugwatch = rt_bugwatch

    >>> rt_product.remote_product = u'already-set'
    >>> updater = NoNetworkRemoteProductUpdater(
    ...     FakeTransaction(), BufferLogger())
    >>> updater.updateByBugTrackerType(BugTrackerType.RT)
    >>> print(rt_product.remote_product)
    already-set


Transaction handling
....................

To avoid long-running write transactions, the transaction is committed
after each product's remote_product has been updated.

    >>> with lp_dbuser():
    ...     for index in range(3):
    ...         rt_product = factory.makeProduct(official_malone=False)
    ...         rt = factory.makeBugTracker(
    ...             bugtrackertype=BugTrackerType.RT)
    ...         rt_product.bugtracker = rt
    ...         rt_bugtask = factory.makeBugTask(target=rt_product)
    ...         rt_bugwatch = factory.makeBugWatch(
    ...             '84', bugtracker=rt, bug=rt_bugtask.bug)
    ...         rt_bugtask.bugwatch = rt_bugwatch

    >>> updater = NoNetworkRemoteProductUpdater(
    ...     FakeTransaction(log_calls=True), BufferLogger())
    >>> updater.print_method_calls = False
    >>> updater.updateByBugTrackerType(BugTrackerType.RT)
    Initializing DB for bugs: ['84'].
    COMMIT
    Initializing DB for bugs: ['84'].
    COMMIT
    Initializing DB for bugs: ['84'].
    COMMIT


Error handling
..............

If the ExternalBugTracker raises any BugWatchUpdateErrors,
updateByBugTrackerType() will simply log the error and then continue.
This is a simplistic approach but it means that problems with one bug
tracker don't break the run for all bug trackers.

    >>> with lp_dbuser():
    ...     new_rt_product = factory.makeProduct(
    ...         name='fooix', official_malone=False)
    ...     new_rt_product.bugtracker = rt
    ...     new_rt_bugtask = factory.makeBugTask(target=new_rt_product)
    ...     new_rt_bugwatch = factory.makeBugWatch(
    ...         '42', bugtracker=rt, bug=new_rt_bugtask.bug)
    ...     new_rt_bugtask.bugwatch = new_rt_bugwatch

    >>> from lp.bugs.externalbugtracker.base import (
    ...     BugNotFound, BugWatchUpdateError)
    >>> class BrokenOnInitExternalBugTracker(
    ...         FakeExternalBugTracker):
    ...     def initializeRemoteBugDB(self, bug_ids):
    ...         raise BugWatchUpdateError("This here is an error")

    >>> updater.logger = FakeLogger()
    >>> updater.external_bugtracker_to_return = (
    ...     BrokenOnInitExternalBugTracker)
    >>> updater.updateByBugTrackerType(BugTrackerType.RT)
    INFO  1 projects using RT needing updating.
    DEBUG Trying to update fooix
    ERROR Unable to set remote_product for 'fooix': This here is an error

    >>> class BrokenOnGetRemoteProductExternalBugTracker(
    ...         FakeExternalBugTracker):
    ...     def getRemoteProduct(self, remote_bug):
    ...         raise BugNotFound("Didn't find bug %s." % remote_bug)

    >>> updater.external_bugtracker_to_return = (
    ...     BrokenOnGetRemoteProductExternalBugTracker)
    >>> updater.updateByBugTrackerType(BugTrackerType.RT)
    INFO  1 projects using RT needing updating.
    DEBUG Trying to update fooix
    Initializing DB for bugs: ['42'].
    ERROR Unable to set remote_product for 'fooix': Didn't find bug 42.

AssertionErrors are also handled.

    >>> class RaisesAssertionErrorExternalBugTracker(FakeExternalBugTracker):
    ...     def initializeRemoteBugDB(self, bug_ids):
    ...         assert True == False, "True isn't False!"

    >>> updater.external_bugtracker_to_return = (
    ...     RaisesAssertionErrorExternalBugTracker)
    >>> updater.updateByBugTrackerType(BugTrackerType.RT)
    INFO  1 projects using RT needing updating.
    DEBUG Trying to update fooix
    ERROR Unable to set remote_product for 'fooix': True isn't False!

