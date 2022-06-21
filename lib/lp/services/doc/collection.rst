Collection
==========

The Collection class is a generic base for the Collection pattern: you
can have a Collection of branches, a Collection of translation templates
and so on.  This is a more flexible and generic version of Sets and
Subsets.

The base Collection class is a very thin wrapper around Storm.  You use
it by deriving your own collection type from it.  In this example, we
look at collections of Kumquats.

Kumquats are very simple things.  All they have is a key to identify
them.

    >>> from storm.locals import Count, Int, Storm
    >>> from lp.registry.model.product import Product
    >>> from lp.services.database.interfaces import IMasterStore

    >>> store = IMasterStore(Product)
    >>> ok = store.execute("CREATE TEMP TABLE Kumquat(id integer UNIQUE)")
    >>> class Kumquat(Storm):
    ...     __storm_table__ = 'Kumquat'
    ...     id = Int(primary=True)
    ...     def __init__(self, id):
    ...         self.id = id
    ...     def __repr__(self):
    ...         return "Kumquat-%d" % self.id

    >>> obj = store.add(Kumquat(1))
    >>> obj = store.add(Kumquat(2))

A custom KumquatCollection class derives from Collection.  The
starting_table attribute tells Collection what it is a collection of.

    >>> from lp.services.database.collection import Collection
    >>> class KumquatCollection(Collection):
    ...     starting_table = Kumquat

The collection starts out "containing" all kumquats.  Nothing is queried
yet until you invoke the "select" method, which returns a Storm result
set.

    >>> collection = KumquatCollection()
    >>> print(list(collection.select().order_by(Kumquat.id)))
    [Kumquat-1, Kumquat-2]

Actually, select() is just shorthand for select(Kumquat).

    >>> print(list(collection.select(Kumquat).order_by(Kumquat.id)))
    [Kumquat-1, Kumquat-2]

You can also query individual columns.

    >>> list(collection.select(Kumquat.id).order_by(Kumquat.id))
    [1, 2]

Since the select method returns a result set, you can even use aggregate
functions.

    >>> [int(count) for count in collection.select(Count())]
    [2]

You can refine the matching conditions using the refine method.
Collections are immutable, so all refinements create modified copies of
the original.

    >>> one = collection.refine(Kumquat.id == 1)
    >>> list(one.select(Kumquat.id))
    [1]

You can join in arbitrary other classes, such as Guava.

    >>> ok = store.execute("CREATE TEMP TABLE Guava(id integer UNIQUE)")
    >>> class Guava(Storm):
    ...     __storm_table__ = 'Guava'
    ...     id = Int(primary=True)
    ...     def __init__(self, id):
    ...         self.id = id
    ...     def __repr__(self):
    ...         return "Guava-%d" % self.id
    >>> obj = store.add(Guava(1))
    >>> obj = store.add(Guava(3))
    >>> join = collection.joinInner(Guava, Guava.id == Kumquat.id)

This includes the ability to return multiple values from the join.

    >>> list(join.select(Kumquat, Guava))
    [(Kumquat-1, Guava-1)]

Outer joins work in the same way.

    >>> join = collection.joinOuter(Guava, Guava.id == Kumquat.id)
    >>> list(join.select(Kumquat, Guava).order_by(Kumquat.id))
    [(Kumquat-1, Guava-1), (Kumquat-2, None)]
