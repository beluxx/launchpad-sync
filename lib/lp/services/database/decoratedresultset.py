# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'DecoratedResultSet',
    ]

from lazr.delegates import delegate_to
from storm import Undef
from storm.zope.interfaces import IResultSet
from zope.security.proxy import (
    isinstance as zope_isinstance,
    ProxyFactory,
    removeSecurityProxy,
    )


@delegate_to(IResultSet, context='result_set')
class DecoratedResultSet:
    """A decorated Storm ResultSet for 'Magic' (presenter) classes.

    Because `DistroSeriesBinaryPackage` doesn't actually exist in the
    database, the `DistroSeries`.searchPackages method uses the
    `DistroSeriesPackageCache` object to search for packages within a
    `DistroSeries`.

    Nonetheless, the users of the searchPackages method (such as the
    `DistroSeriesView`) expect a result set of DSBPs. Rather than executing
    the query prematurely and doing a list comprehension on the complete
    result set (which could be very large) to convert all the results (even
    though batching may mean only a window of 10 results is required), this
    adapted result set converts the results only when they are needed.

    This behaviour is required for other classes as well (Distribution,
    DistroArchSeries), hence a generalised solution.
    """

    def __init__(self, result_set, result_decorator=None, pre_iter_hook=None,
                 bulk_decorator=None, slice_info=False, return_both=False):
        """
        Wrap `result_set` in a decorator.

        The decorator will act as a result set where a result row `self[x]`
        is really `result_decorator(result_set[x])`.

        :param result_set: The original result set to be decorated.
        :param result_decorator: A transformation function that individual
            results will be passed through. Mutually exclusive with
            bulk_decorator.
        :param pre_iter_hook: The method to be called (with the 'result_set')
            immediately before iteration starts. The return value of the hook
            is ignored.
        :param bulk_decorator: A transformation function that chunks of
            results will be passed through. Mutually exclusive with
            result_decorator.
        :param slice_info: If True pass information about the slice parameters
            to the result_decorator and pre_iter_hook. any() and similar
            methods will cause None to be supplied.
        :param return_both: If True return both the plain and decorated
            values as a tuple.
        """
        if (bulk_decorator is not None and
            (result_decorator is not None or pre_iter_hook is not None)):
            raise TypeError(
                "bulk_decorator cannot be used with result_decorator or "
                "pre_iter_hook")
        self.result_set = result_set
        self.result_decorator = result_decorator
        self.pre_iter_hook = pre_iter_hook
        self.bulk_decorator = bulk_decorator
        self.slice_info = slice_info
        self.config(return_both=return_both)

    def _extract_plain_and_result(self, results):
        """Extract the plain and normal results from a sub-result.

        This gets slightly complicated when there are nested
        DecoratedResultSets, as we have to propogate the plain result
        all the way up.
        """
        if not results:
            return [], []
        elif (zope_isinstance(self.result_set, DecoratedResultSet)
              and self.return_both):
            assert (
                removeSecurityProxy(self.result_set).return_both
                    == self.return_both)
            return tuple(zip(*results))
        else:
            return results, results

    def decorate_single(self, result, row_index=None):
        """Decorate a result or return None if the result is itself None"""
        # If we have a nested DecoratedResultSet we need to propogate
        # the plain result.
        ([plain], [result]) = self._extract_plain_and_result([result])

        if result is None:
            decorated = None
        else:
            if self.result_decorator is not None:
                if self.slice_info:
                    decorated = self.result_decorator(result, row_index)
                else:
                    decorated = self.result_decorator(result)
            elif self.bulk_decorator is not None:
                if self.slice_info:
                    [decorated] = self.bulk_decorator(
                        [result], slice(row_index, row_index + 1))
                else:
                    [decorated] = self.bulk_decorator([result])
            else:
                decorated = result
        if self.return_both:
            return (plain, decorated)
        else:
            return decorated

    def copy(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned result set.
        """
        new_result_set = self.result_set.copy(*args, **kwargs)
        return DecoratedResultSet(
            new_result_set, self.result_decorator, self.pre_iter_hook,
            self.bulk_decorator, self.slice_info, self.return_both)

    def config(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated result set.after updating the config.
        """
        return_both = kwargs.pop('return_both', None)
        if return_both is not None:
            self.return_both = return_both
            if zope_isinstance(self.result_set, DecoratedResultSet):
                self.result_set.config(return_both=return_both)

        self.result_set.config(*args, **kwargs)
        return self

    def __iter__(self, *args, **kwargs):
        """See `IResultSet`.

        Yield a decorated version of the returned value.
        """
        # Execute/evaluate the result set query.
        results = list(self.result_set.__iter__(*args, **kwargs))
        if self.slice_info:
            # Calculate slice data
            start = self.result_set._offset
            if start is Undef:
                start = 0
            stop = start + len(results)
            result_slice = slice(start, stop)
        if self.bulk_decorator is not None:
            pre_iter_rows = self._extract_plain_and_result(results)[1]
            if self.slice_info:
                results = self.bulk_decorator(pre_iter_rows, result_slice)
            else:
                results = self.bulk_decorator(pre_iter_rows)
            for value in results:
                yield value
        else:
            if self.pre_iter_hook is not None:
                pre_iter_rows = self._extract_plain_and_result(results)[1]
                if self.slice_info:
                    self.pre_iter_hook(pre_iter_rows, result_slice)
                else:
                    self.pre_iter_hook(pre_iter_rows)
            if self.slice_info:
                start = result_slice.start
                for offset, value in enumerate(results):
                    yield self.decorate_single(value, offset + start)
            else:
                for value in results:
                    yield self.decorate_single(value)

    def __getitem__(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned value.
        """
        # Can be a value or result set...
        value = self.result_set.__getitem__(*args, **kwargs)
        naked_value = removeSecurityProxy(value)
        if IResultSet.providedBy(naked_value):
            return DecoratedResultSet(
                value, self.result_decorator, self.pre_iter_hook,
                self.bulk_decorator, self.slice_info)
        else:
            return self.decorate_single(value)

    def iterhook_one_elem(self, value):
        if value is not None and self.pre_iter_hook is not None:
            self.pre_iter_hook([value])

    def any(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned value.
        """
        value = self.result_set.any(*args, **kwargs)
        self.iterhook_one_elem(value)
        return self.decorate_single(value)

    def first(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned value.
        """
        value = self.result_set.first(*args, **kwargs)
        self.iterhook_one_elem(value)
        return self.decorate_single(value)

    def last(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned value.
        """
        value = self.result_set.last(*args, **kwargs)
        self.iterhook_one_elem(value)
        return self.decorate_single(value)

    def one(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned value.
        """
        value = self.result_set.one(*args, **kwargs)
        self.iterhook_one_elem(value)
        return self.decorate_single(value)

    def order_by(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned result set.
        """
        new_result_set = self.result_set.order_by(*args, **kwargs)
        return DecoratedResultSet(
            new_result_set, self.result_decorator, self.pre_iter_hook,
            self.bulk_decorator, self.slice_info, self.return_both)

    def get_plain_result_set(self):
        """Return the plain Storm result set."""
        if zope_isinstance(self.result_set, DecoratedResultSet):
            return self.result_set.get_plain_result_set()
        else:
            return self.result_set

    def find(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned result set.
        """
        naked_result_set = removeSecurityProxy(self.result_set)
        if naked_result_set is not self.result_set:
            naked_new_result_set = naked_result_set.find(*args, **kwargs)
            new_result_set = ProxyFactory(naked_new_result_set)
        else:
            new_result_set = self.result_set.find(*args, **kwargs)
        return DecoratedResultSet(
            new_result_set, self.result_decorator, self.pre_iter_hook,
            self.bulk_decorator, self.slice_info, self.return_both)
