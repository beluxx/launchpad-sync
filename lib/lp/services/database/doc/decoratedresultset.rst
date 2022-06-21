DecoratedResultSet
==================

Within Launchpad we often want to return related data for a ResultSet
but not have every call site know how that data is structured - they
should not need to know how to go about loading related Persons for
a BugMessage, or how to calculate whether a Person is valid. Nor do
we want to return a less capable object - that prohibits late slicing
and sorting.

DecoratedResultSet permits some preprocessing of Storm ResultSet
objects at the time the query executes. This can be used to present
content classes which are not backed directly in the database, to
eager load multiple related tables and present just one in the result,
and so on.

First, we'll create the un-decorated result set of all distributions:

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from storm.store import Store
    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> store = Store.of(ubuntu)
    >>> from lp.registry.model.distribution import Distribution
    >>> result_set = store.find(Distribution)

Creating the decorator function
-------------------------------

We create a decorator function that we want to be applied to any
results obtained from our undecorated result set. For instance,
we can turn a model object into a string:

    >>> def result_decorator(distribution):
    ...     return "Dist name is: %s" % distribution.name

Creating the DecoratedResultSet
-------------------------------

The original result set and the decorator function are then used to
create the decorated result set:

    >>> from lp.services.database.decoratedresultset import (
    ...     DecoratedResultSet)
    >>> decorated_result_set = DecoratedResultSet(result_set,
    ...     result_decorator)


Using the DecoratedResultSet
----------------------------

The DecoratedResultSet implements the normal ResultSet interface (by
definition), so all the normal methods can be used. Iterating over the
decorated result set produces the decorated results:

    >>> for dist in decorated_result_set:
    ...     print(dist)
    Dist name is: debian
    Dist name is: gentoo
    ...
    Dist name is: ubuntutest

Splicing works as normal:

    >>> for dist in decorated_result_set[1:3]:
    ...     print(dist)
    Dist name is: gentoo
    Dist name is: guadalinex

It's also possible to ask the set to return both the normal and
decorated results:

    >>> decorated_result_set.config(return_both=True)
    <lp.services.database.decoratedresultset.DecoratedResultSet object at ...>
    >>> for dist in decorated_result_set:
    ...     print(pretty(dist))
    (<Distribution 'Debian' (debian)>, 'Dist name is: debian')
    (<Distribution 'Gentoo' (gentoo)>, 'Dist name is: gentoo')
    ...
    (<Distribution 'ubuntutest' (ubuntutest)>, 'Dist name is: ubuntutest')
    >>> print(pretty(decorated_result_set.first()))
    (<Distribution 'Debian' (debian)>, 'Dist name is: debian')

This works even if there are multiple levels:

    >>> drs_squared = DecoratedResultSet(
    ...     decorated_result_set, lambda x: len(x)).config(return_both=True)
    >>> for dist in drs_squared:
    ...     print(dist)
    (<Distribution 'Debian' (debian)>, 20)
    (<Distribution 'Gentoo' (gentoo)>, 20)
    ...
    (<Distribution 'ubuntutest' (ubuntutest)>, 24)

Some methods of the DecoratedResultSet are not actually decorated and
just work like normally:

    >>> decorated_result_set.count()
    7

    >>> decorated_result_set.max(Distribution.id)
    8

The patched count() method
--------------------------

There was a bug in the Storm API whereby calling count (or other aggregates)
on a storm ResultSet does not respect the distinct
config option (https://bugs.launchpad.net/storm/+bug/217644):

    >>> from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
    >>> from lp.soyuz.model.publishing import BinaryPackagePublishingHistory
    >>> results = store.find(BinaryPackageRelease,
    ...     BinaryPackageRelease.id ==
    ...         BinaryPackagePublishingHistory.binarypackagereleaseID)
    >>> results = results.config(distinct=True)
    >>> len(list(results))
    14

But this bug appears to be fixed, so we no longer override count():

    >>> results.count()
    14
    >>> def dummy_result_decorator(result):
    ...     return result
    >>> decorated_results = DecoratedResultSet(results,
    ...     dummy_result_decorator)
    >>> len(list(results))
    14
    >>> decorated_results.count()
    14


Bulk operations
---------------

Views or API calls often need to perform operations that are expensive
when performed separately on each record. DecoratedResultSet's
bulk_decorator argument permits operations to be performed over large
chunks of results at once.

    >>> def all_ones(rows):
    ...     print("that's a chunk of %d" % len(rows))
    ...     return (1 for row in rows)
    >>> drs = DecoratedResultSet(results, bulk_decorator=all_ones)
    >>> list(drs)
    that's a chunk of 14
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    >>> drs.any()
    that's a chunk of 1
    1

pre_iter_hook is like bulk_decorator, except that the return value is
ignored in favour of the original results.

    >>> class FakeResultSet(list):
    ...     def count(self, *args, **kwargs):
    ...         return len(self)
    ...     def first(self, *args, **kwargs):
    ...         return self[0]
    ...     def last(self, *args, **kwargs):
    ...         return self[-1]
    ...     def any(self, *args, **kwargs):
    ...         return self[-1]
    ...     def one(self, *args, **kwargs):
    ...         return self[-1]
    ...     def order_by(self, *args, **kwargs):
    ...         return FakeResultSet(self)
    ...     def config(self, *args, **kwargs):
    ...         pass
    ...     def copy(self, *args, **kwargs):
    ...         return FakeResultSet(self)
    >>> rs = FakeResultSet(list(range(1, 5)))
    >>> def my_pih(result_set):
    ...     print('this should run once only, count: %s' % len(result_set))
    >>> def my_deco(result):
    ...     print('> original value : %s' % result)
    ...     return (result * 2)

    >>> my_drs = DecoratedResultSet(rs, my_deco, my_pih)
    >>> for res in my_drs:
    ...     print(' decorated result: %s' % res)
    this should run once only, count: 4
    > original value : 1
     decorated result: 2
    > original value : 2
     decorated result: 4
    > original value : 3
     decorated result: 6
    > original value : 4
     decorated result: 8


Calculating row numbers
-----------------------

DecoratedResultSet can inform its hooks about slice data if slice_info=True is
passed.

    >>> def pre_iter(rows, slice):
    ...     print("pre iter", len(rows), slice.start, slice.stop)
    >>> def decorate(row, row_index):
    ...     print("row", row.id, row_index)
    >>> _ = result_set.order_by(Distribution.id)
    >>> drs = DecoratedResultSet(
    ...     result_set, decorate, pre_iter, slice_info=True)

We need enough rows to play with:

    >>> drs.count()
    7

    >>> _ = list(drs[1:3])
    pre iter 2 1 3
    row 2 1
    row 3 2

Half open slicing is supported too:

    >>> _ = list(drs[:3])
    pre iter 3 0 3
    row 1 0
    row 2 1
    row 3 2

    >>> _ = list(drs[2:])
    pre iter 5 2 7
    row 3 2
    row 4 3
    row 5 4
    row 7 5
    row 8 6

And of course empty slices:

    >>> _ = list(drs[3:3])
    pre iter 0 3 3
