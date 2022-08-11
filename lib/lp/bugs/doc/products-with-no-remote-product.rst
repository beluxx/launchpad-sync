Products with no remote_product
===============================

Product.remote_product is used to keep track of which remote product in
an upstream bug tracker, a Product registered in Launchpad corresponds
to. If a Product doesn't have it set, but is associated with an upstream
bug tracker, we want to set this automatically. For this we need a
method to get all the Products needing updating.
IProductSet.getProductsWithNoneRemoteProduct() is used for this.


    >>> from lp.registry.model.product import Product
    >>> from lp.services.database.interfaces import IStore
    >>> store = IStore(Product)
    >>> store.execute("UPDATE Product SET remote_product = 'not-None'")
    <storm...>
    >>> from lp.registry.interfaces.product import IProductSet
    >>> list(getUtility(IProductSet).getProductsWithNoneRemoteProduct())
    []

    >>> from lp.testing.factory import LaunchpadObjectFactory
    >>> factory = LaunchpadObjectFactory()
    >>> product = factory.makeProduct(name=u'no-remote-product')
    >>> print(product.remote_product)
    None

    >>> products = getUtility(IProductSet).getProductsWithNoneRemoteProduct()
    >>> for product in products:
    ...     print(product.name)
    no-remote-product

When we update remote_product automatically, different heuristics are
used depending on which bug tracker is used. Therefore the list of
products can be filtered by bug tracker type.

    >>> login('foo.bar@canonical.com')
    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> bugzilla_product = factory.makeProduct(name=u'bugzilla-product')
    >>> bugzilla = factory.makeBugTracker(
    ...     bugtrackertype=BugTrackerType.BUGZILLA)
    >>> bugzilla_product.bugtracker = bugzilla
    >>> trac_product = factory.makeProduct(name=u'trac-product')
    >>> trac = factory.makeBugTracker(bugtrackertype=BugTrackerType.TRAC)
    >>> trac_product.bugtracker = trac
    >>> products = getUtility(IProductSet).getProductsWithNoneRemoteProduct(
    ...     bugtracker_type=BugTrackerType.BUGZILLA)
    >>> for product in products:
    ...     print(product.name)
    bugzilla-product
