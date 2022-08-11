The class LimitedList implements a mutable sequence that takes not more
than a given number of elements.

The constructor requires a parameter that specifies the maximum
number of elements.

    >>> from lp.services.limitedlist import LimitedList
    >>> LimitedList(1)
    <LimitedList(1, [])>

The property max_length stores the maximum allowed length of the list.

    >>> LimitedList(2).max_length
    2

    >>> LimitedList()
    Traceback (most recent call last):
    ...
    TypeError: __new__() ...

We can optionally specify the initial content of the sequence. Note that
only the last N elements of the second parameter are stored, where N is
the given maximum size of the LimitedList.

    >>> LimitedList(3, (0, 'one', 2, 3))
    <LimitedList(3, ['one', 2, 3])>

If the initial content has more elements than the given maximum length,
the first elements are dropped.

    >>> LimitedList(2, [1, 2, 3])
    <LimitedList(2, [2, 3])>

If we add two LimitedLists, the result is a LimitedList too, its maximum
length is the same as the maximum length of the left operand. If the
concatenated lists have more elements than left_operand.max_length, only
the last elements are stored.

    >>> new_list = LimitedList(3, [1, 2]) + LimitedList(10, [3, 4])
    >>> new_list
    <LimitedList(3, [2, 3, 4])>

If we add a LimitedList and a regular list, the result is a LimitedList.

    >>> new_list = LimitedList(3, [1, 2]) + [3, 4]
    >>> new_list
    <LimitedList(3, [2, 3, 4])>

    >>> new_list = [1, 2] + LimitedList(3, [3, 4])
    >>> new_list
    <LimitedList(3, [2, 3, 4])>

Inline addition is also possible.

    >>> list_one = LimitedList(3, [1, 2])
    >>> list_one += [3]
    >>> list_one
    <LimitedList(3, [1, 2, 3])>
    >>> list_one += [4]
    >>> list_one
    <LimitedList(3, [2, 3, 4])>

We can multiply lists by integers. Again, if the length of the result
exceeds the maximum number of allowed lements, the first elements
are dropped.

    >>> LimitedList(5, [4, 5, 6]) * 2
    <LimitedList(5, [5, 6, 4, 5, 6])>

    >>> 2 * LimitedList(5, [4, 5, 6])
    <LimitedList(5, [5, 6, 4, 5, 6])>

Inline multiplication works the same.

    >>> list_two = LimitedList(5, [4, 5, 6])
    >>> list_two *= 2
    >>> list_two
    <LimitedList(5, [5, 6, 4, 5, 6])>

    >>> morphing_number = 2
    >>> morphing_number *= LimitedList(5, [4, 5, 6])
    >>> morphing_number
    <LimitedList(5, [5, 6, 4, 5, 6])>

We can change slices of a LimitedList. If the new value exceeds the
maximum length, the first elements are removed.

    >>> list_three = LimitedList(3, [1, 2, 3])
    >>> list_three[1:2] = [42, 43]
    >>> list_three
    <LimitedList(3, [42, 43, 3])>

When we append() elements to a LimitedList, it does not exceed its
length limit.

    >>> list_four = LimitedList(3, [1, 2])
    >>> list_four.append(3)
    >>> list_four
    <LimitedList(3, [1, 2, 3])>
    >>> list_four.append(4)
    >>> list_four
    <LimitedList(3, [2, 3, 4])>

Similary, a LimitedList does not exceed it length limit, when we extend()
it.

    >>> list_five = LimitedList(3, [1])
    >>> list_five.extend([2, 3])
    >>> list_five
    <LimitedList(3, [1, 2, 3])>
    >>> list_five.extend([4, 5])
    >>> list_five
    <LimitedList(3, [3, 4, 5])>

And when insert elements into a limited list, the maximum length is
also not exceeded.

    >>> list_six = LimitedList(3, [1, 2])
    >>> list_six.insert(1, 3)
    >>> list_six
    <LimitedList(3, [1, 3, 2])>
    >>> list_six.insert(1, 4)
    >>> list_six
    <LimitedList(3, [4, 3, 2])>
