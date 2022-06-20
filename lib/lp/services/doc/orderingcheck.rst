OrderingCheck
=============

Often when you iterate over a sequence of items, you assume that they're
in some particular order.  If you're worried that they might not be in
that order sometimes, you may add an assertion to that affect.  But it
adds some ugliness: "if this is not the first item, assert..."  Doesn't
seem worth the trouble.

    >>> from lp.services.orderingcheck import OrderingCheck

    >>> def sort_key(item):
    ...     """Simple sorting key for integers.
    ...
    ...     This could just be the integer itself, but in order to support
    ...     None on Python 3 we need an additional term.
    ...     """
    ...     return (0 if item is None else 1, item)

The OrderingCheck makes it clean and easy.  You create an OrderingCheck
with the same arguments that go into Python's standard sorting
functions.

    >>> checker = OrderingCheck(key=sort_key)

    >>> for number in range(3):
    ...     checker.check(number)


Sorting criteria
----------------

The OrderingCheck accepts all the same sorting options (as keyword args)
as Python's built-in sorting functions.

    >>> checker = OrderingCheck(key=lambda v: v, reverse=True)
    >>> for number in (3, 2, 1):
    ...     checker.check(number)


Unexpected values
-----------------

If any item is out of sequence, the OrderingCheck raises an assertion
error.

    >>> checker = OrderingCheck(key=sort_key)
    >>> checker.check(1)
    >>> checker.check(0)
    Traceback (most recent call last):
    ...
    AssertionError: Unexpected ordering at item 1: 0 should come before 1.


Edge cases
----------

It is safe to use the None value.  sort_key places it below any other
integer.

    >>> checker = OrderingCheck(key=sort_key)
    >>> checker.check(None)
    >>> checker.check(-10000)
    >>> checker.check(0)

Values may also repeat, as long as the ordering is deterministic.

    >>> checker = OrderingCheck(key=sort_key)
    >>> checker.check(1)
    >>> checker.check(1)
    >>> checker.check(2)


Customization
-------------

If raising an assertion error is not the response you want for a bad
ordering, override the "fail" method.

    >>> def alternative_fail(item):
    ...     """Don't raise an error, just print a message."""
    ...     print("Item %s was out of sequence." % item)

    >>> checker = OrderingCheck(key=sort_key)
    >>> checker.fail = alternative_fail

    >>> checker.check(10)
    >>> checker.check(9)
    Item 9 was out of sequence.
    >>> checker.check(8)
    Item 8 was out of sequence.

Because this custom failure handler did not raise an error, execution
continued despite the unexpected values.

Since no exception was raised, the OrderingCheck still accepted that
last value as a comparison base for the next one.

    >>> checker.check(9)

In general though, you'll want the checker to raise an error when things
aren't ordered the way you expect.
