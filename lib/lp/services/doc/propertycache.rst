Cached Properties in propertycache
==================================

    >>> from lp.services.propertycache import (
    ...     cachedproperty,
    ...     clear_property_cache,
    ...     get_property_cache,
    ...     IPropertyCache,
    ...     )

Cached properties are for situations where a property is computed once
and then returned each time it is asked for.

    >>> from itertools import count
    >>> counter = count(1)

    >>> class Foo:
    ...     @cachedproperty
    ...     def bar(self):
    ...         return next(counter)

    >>> foo = Foo()

The property cache can be obtained with `get_property_cache()`.

    >>> cache = get_property_cache(foo)

Calling `get_property_cache()` on a cache returns the cache:

    >>> get_property_cache(cache) is cache
    True

Caches provide the `IPropertyCache` interface.

    >>> IPropertyCache.providedBy(cache)
    True

Initially it is empty. Caches can be iterated over to reveal the names
of the values cached within.

    >>> list(cache)
    []

After accessing a cached property the cache is no longer empty.

    >>> foo.bar
    1
    >>> list(cache)
    ['bar']
    >>> cache.bar
    1

Attempting to access an unknown name from the cache is an error.

    >>> cache.baz
    Traceback (most recent call last):
    ...
    AttributeError: 'DefaultPropertyCache' object has no attribute 'baz'

Values in the cache can be deleted.

    >>> del cache.bar
    >>> list(cache)
    []

Accessing the cached property causes its populate function to be
called again.

    >>> foo.bar
    2
    >>> cache.bar
    2

Values in the cache can be set and updated.

    >>> cache.bar = 456
    >>> foo.bar
    456

Caches respond to membership tests.

    >>> "bar" in cache
    True

    >>> del cache.bar

    >>> "bar" in cache
    False

It is safe to delete names from the cache even if there is no value
cached.

    >>> del cache.bar
    >>> del cache.bar

The cache can be cleared with `clear_property_cache()`.

    >>> cache.bar = 123
    >>> cache.baz = 456
    >>> sorted(cache)
    ['bar', 'baz']

    >>> clear_property_cache(cache)
    >>> list(cache)
    []

For convenience, the property cache for an object can also be cleared
by passing the object itself into `clear_property_cache()`.

    >>> cache.bar = 123
    >>> list(cache)
    ['bar']

    >>> clear_property_cache(foo)
    >>> list(cache)
    []


The cachedproperty decorator
----------------------------

A cached property can be declared with or without an explicit name. If
not provided it will be derived from the decorated object. This name
is the name under which values will be cached.

    >>> class Foo:
    ...     @cachedproperty("a_in_cache")
    ...     def a(self):
    ...         return 1234
    ...     @cachedproperty
    ...     def b(self):
    ...         return 5678

    >>> foo = Foo()

`a` was declared with an explicit name of "a_in_cache" so it is known
as "a_in_cache" in the cache.

    >>> from lp.services.propertycache import CachedProperty

    >>> isinstance(Foo.a, CachedProperty)
    True
    >>> print(Foo.a.name)
    a_in_cache
    >>> Foo.a.populate
    <function ...a at 0x...>

    >>> foo.a
    1234
    >>> get_property_cache(foo).a_in_cache
    1234

`b` was defined without an explicit name so it is known as "b" in the
cache too.

    >>> isinstance(Foo.b, CachedProperty)
    True
    >>> Foo.b.name
    'b'
    >>> Foo.b.populate
    <function ...b at 0x...>

    >>> foo.b
    5678
    >>> get_property_cache(foo).b
    5678

Cached properties cannot be set or deleted from the host object.

    >>> foo.a = 4321
    Traceback (most recent call last):
    ...
    AttributeError: a_in_cache cannot be set here; instead set
    explicitly with get_property_cache(object).a_in_cache = 4321

    >>> del foo.a
    Traceback (most recent call last):
    ...
    AttributeError: a_in_cache cannot be deleted here; instead delete
    explicitly with del get_property_cache(object).a_in_cache
