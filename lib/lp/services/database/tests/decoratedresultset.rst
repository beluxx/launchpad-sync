DecoratedResultSet
==================

This doctest checks that all the methods that the DecoratedResultSet
decorates (that are not already tested as part of the documentation) do
indeed implement the IResultSet interface correctly.

Please see doc/decoratedresultset.rst for the documentation.

First we'll setup the decorated result set using a properly proxied
ResultSet:

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from storm.store import Store
    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> store = Store.of(ubuntu)
    >>> from lp.registry.model.distribution import Distribution
    >>> result_set = store.find(Distribution)

    >>> from zope.security.checker import ProxyFactory
    >>> proxied_result_set = ProxyFactory(result_set)
    >>> print(proxied_result_set)
    <security proxied storm.store.ResultSet ...>

    >>> def result_decorator(distribution):
    ...     return "Dist name is: %s" % distribution.name
    ...

    >>> def pre_iter_hook(values):
    ...     print(len(values), "elements in result set")
    ...

    >>> from lp.services.database.decoratedresultset import DecoratedResultSet
    >>> decorated_result_set = DecoratedResultSet(
    ...     proxied_result_set, result_decorator, pre_iter_hook
    ... )

copy()
------

The decorated copy method calls the orgininal result sets copy method
and then returns a new decorated result set composed of the new
copy:

    >>> result_copy = decorated_result_set.copy()

Make sure that the new result set is actually different:

    >>> result_copy != decorated_result_set
    True
    >>> result_copy.result_set != decorated_result_set.result_set
    True

But it still contains the expected results:

    >>> for distro in result_copy:
    ...     print(distro)
    ...
    7 elements in result set
    Dist name is: debian
    ...
    Dist name is: ubuntutest

config()
--------

The decorated config method updates the config of the original result set:

    >>> from zope.security.proxy import removeSecurityProxy
    >>> naked_result_set = removeSecurityProxy(
    ...     decorated_result_set.result_set
    ... )
    >>> naked_result_set._distinct
    False
    >>> returned_result = decorated_result_set.config(distinct=True)
    >>> naked_result_set._distinct
    True

but returns a copy of itself:

    >>> returned_result == decorated_result_set
    True

__getitem__()
-------------

The decorated __getitem__ gets the item from the original result set
and decorates the item before returning it:

    >>> print(decorated_result_set[0])
    Dist name is: debian

any()
-----

The decorated any() method calls the original result set's any() method
and decorates the result:

    >>> orig_result = decorated_result_set.result_set.any()
    >>> decorated_result_set.any() == result_decorator(orig_result)
    1 elements in result set
    True

first()
-------

The decorated first() method calls the original result set's first()
method and decorates the result:

    >>> print(decorated_result_set.first())
    1 elements in result set
    Dist name is: debian

pre_iter_hook is not called from methods like first() or one() which return
at most one row:

    >>> empty_result_set = decorated_result_set.copy()
    >>> print(
    ...     empty_result_set.config(offset=empty_result_set.count()).first()
    ... )
    None

last()
------

The decorated last() method calls the original result set's last()
method and decorates the result:

    >>> print(decorated_result_set.last())
    1 elements in result set
    Dist name is: ubuntutest

order_by()
----------

The decorated order_by() method calls the original result set's order_by()
method and decorates the result:

    >>> from storm.expr import Desc
    >>> ordered_results = decorated_result_set.order_by(
    ...     Desc(Distribution.name)
    ... )
    >>> for dist in ordered_results:
    ...     print(dist)
    ...
    7 elements in result set
    Dist name is: ubuntutest
    ...
    Dist name is: debian

one()
-----

The decorated one() method calls the original result set's one()
method and decorates the result:

    >>> print(decorated_result_set.config(offset=2, limit=1).one())
    1 elements in result set
    Dist name is: redhat

    >>> print(result_decorator(decorated_result_set.result_set.one()))
    Dist name is: redhat

splicing
--------

Splicing a decorated resultset returns another decorated resultset:

    >>> isinstance(decorated_result_set[0:3], DecoratedResultSet)
    True

find()
------

DecoratedResultSet.find() returns another DecoratedResultSet containing
a refined query.

    >>> result_set = store.find(Distribution)
    >>> proxied_result_set = ProxyFactory(result_set)
    >>> decorated_result_set = DecoratedResultSet(
    ...     proxied_result_set, result_decorator
    ... )
    >>> ubuntu_distros = removeSecurityProxy(decorated_result_set).find(
    ...     "Distribution.name like 'ubuntu%'"
    ... )
    >>> for dist in ubuntu_distros:
    ...     print(dist)
    ...
    Dist name is: ubuntu
    Dist name is: ubuntutest


get_plain_result_set()
----------------------

DecoratedResultSet.get_plain_result_set() returns the plain Storm result
set.

    >>> decorated_result_set.get_plain_result_set()
    <storm.store.ResultSet object at...

get_plain_result_set() works for nested DecoratedResultSets.

    >>> def embellish(result):
    ...     return result.replace("Dist name", "The distribution name")
    ...
    >>> embellished_result_set = DecoratedResultSet(
    ...     decorated_result_set, embellish
    ... )
    >>> embellished_result_set.get_plain_result_set()
    <storm.store.ResultSet object at...
