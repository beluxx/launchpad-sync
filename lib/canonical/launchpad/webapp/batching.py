# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import urllib

from zope.interface import implements

from canonical.config import config
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.z3batching.batch import _Batch
from canonical.launchpad.webapp.interfaces import (
    IBatchNavigator, ITableBatchNavigator, InvalidBatchSizeError
    )


class UpperBatchNavigationView(LaunchpadView):
    """Only render navigation links if there is a batch."""

    def render(self):
        if self.context.currentBatch():
            return LaunchpadView.render(self)
        return u""


class LowerBatchNavigationView(UpperBatchNavigationView):
    """Only render bottom navigation links if there are multiple batches."""

    def render(self):
        if (self.context.currentBatch() and
            (self.context.nextBatchURL() or
            self.context.prevBatchURL())):
            return LaunchpadView.render(self)
        return u""


class BatchNavigator:

    implements(IBatchNavigator)

    start_variable_name = 'start'
    batch_variable_name = 'batch'

    # We want subclasses to be able to hide the 'Last' link from
    # users.  They may want to do this for really large result sets;
    # for example, batches with over a hundred thousand items.
    show_last_link = True

    # The default heading describing the kind of objects in the batch.
    # Sub-classes can override this to be more specific.
    default_singular_heading = 'result'
    default_plural_heading = 'results'

    transient_parameters = None

    def __init__(self, results, request, start=0, size=None, callback=None,
                 transient_parameters=None):
        """Constructs a BatchNavigator instance.

        :param results: is an iterable of results.

        :param request: will be inspected for a start variable; if set,
            it indicates which point we are currently displaying at. It
            will also be inspected for a batch variable; if set, it will
            be used instead of the size supplied in the callsite.

        :param size: is the default batch size, to fall back to if the
            request does not specify one.  If no size can be determined
            from arguments or request, the launchpad.default_batch_size
            config option is used.

        :param callback: is called, if defined, at the end of object
            construction with the defined batch as determined by the
            start and request parameters.

        :param transient_parameters: optional sequence of parameter
            names that should not be passed on in links generated by
            the batch navigator.  Use this for parameters that had
            meaning when this page was requested, but should not be kept
            around for other page requests in the batch.

        :raises InvalidBatchSizeError: if the requested batch size is higher
            than the maximum allowed.
        """
        # We grab the request variables directly from the requests
        # query_string_parameters so that they will be recognized
        # even during post operations.
        batch_params_source = request.query_string_params

        # For backwards compatibility (as in the past a work-around has been
        # to include the url batch params in hidden fields within posted
        # forms), if the request is a POST request, and either the 'start'
        # or 'batch' params are included then revert to the default behaviour
        # of using the request (which automatically gets the params from the
        # request.form dict).
        if request.method == 'POST' and (
            self.start_variable_name in request.form or
            self.batch_variable_name in request.form):
            batch_params_source = request

        # In this code we ignore invalid request variables since it
        # probably means the user finger-fumbled it in the request. We
        # could raise UnexpectedFormData, but is there a good reason?
        request_start = batch_params_source.get(
            self.start_variable_name, None)
        if request_start is None:
            self.start = start
        else:
            try:
                self.start = int(request_start)
            except (ValueError, TypeError):
                self.start = start

        self.default_size = size

        request_size = batch_params_source.get(self.batch_variable_name, None)
        if request_size:
            try:
                size = int(request_size)
            except (ValueError, TypeError):
                pass
            if size > config.launchpad.max_batch_size:
                raise InvalidBatchSizeError(
                    'Maximum for "%s" parameter is %d.' %
                    (self.batch_variable_name,
                     config.launchpad.max_batch_size))

        if size is None:
            size = config.launchpad.default_batch_size

        self.transient_parameters = set([
            self.start_variable_name,
            self.batch_variable_name,
            ])
        if transient_parameters is not None:
            self.transient_parameters.update(transient_parameters)

        self.batch = _Batch(results, start=self.start, size=size)
        self.request = request
        if callback is not None:
            callback(self, self.batch)
        self.setHeadings(
            self.default_singular_heading, self.default_plural_heading)

    @property
    def heading(self):
        """See `IBatchNavigator`"""
        if self.batch.total() == 1:
            return self._singular_heading
        return self._plural_heading

    def setHeadings(self, singular, plural):
        """See `IBatchNavigator`"""
        self._singular_heading = singular
        self._plural_heading = plural

    def getCleanQueryString(self, params=None):
        """Removes start and batch params if present and returns a query
        string.

        If ``params`` is None, uses the current request.query_string_params.
        """
        if params is None:
            params = self.request.query_string_params
        return urllib.urlencode(
            [(key, value) for (key, value) in sorted(params.items())
             if key not in self.transient_parameters])

    def generateBatchURL(self, batch):
        url = ""
        if not batch:
            return url

        qs = self.getCleanQueryString()
        if qs:
            qs += "&"

        start = batch.startNumber() - 1
        size = batch.size
        base_url = str(self.request.URL)
        url = "%s?%s%s=%d" % (base_url, qs, self.start_variable_name, start)
        if size != self.default_size:
            # The current batch size should only be part of the URL if it's
            # different from the default batch size.
            url = "%s&%s=%d" % (url, self.batch_variable_name, size)
        return url

    def getBatches(self):
        batch = self.batch.firstBatch()
        batches = [batch]
        while 1:
            batch = batch.nextBatch()
            if not batch:
                break
            batches.append(batch)
        return batches

    def firstBatchURL(self):
        batch = self.batch.firstBatch()
        if self.start == 0:
            # We are already on the first batch.
            batch = None
        return self.generateBatchURL(batch)

    def prevBatchURL(self):
        return self.generateBatchURL(self.batch.prevBatch())

    def nextBatchURL(self):
        return self.generateBatchURL(self.batch.nextBatch())

    def lastBatchURL(self):
        batch = self.batch.lastBatch()
        if self.start == batch.start:
            # We are already on the last batch.
            batch = None
        return self.generateBatchURL(batch)

    def batchPageURLs(self):
        batches = self.getBatches()
        urls = []
        size = len(batches)

        nextb = self.batch.nextBatch()

        # Find the current page
        if nextb:
            current = nextb.start/nextb.size
        else:
            current = size

        self.current = current
        # Find the start page to show
        if (current - 5) > 0:
            start = current-5
        else:
            start = 0

        # Find the last page to show
        if (start + 10) < size:
            stop = start + 10
        else:
            stop = size

        initial = start
        while start < stop:
            this_batch = batches[start]
            url = self.generateBatchURL(this_batch)
            if (start+1) == current:
                urls.append({'['+str(start + 1)+']' : url})
            else:
                urls.append({start + 1 : url})
            start += 1

        if current != 1:
            url = self.generateBatchURL(batches[0])
            urls.insert(0, {'_first_' : url})
        if current != size:
            url = self.generateBatchURL(batches[size-1])
            urls.append({'_last_':url})

        return urls

    def currentBatch(self):
        return self.batch


class TableBatchNavigator(BatchNavigator):
    """See canonical.launchpad.interfaces.ITableBatchNavigator."""
    implements(ITableBatchNavigator)

    def __init__(self, results, request, start=0, size=None,
                 columns_to_show=None, callback=None):
        BatchNavigator.__init__(self, results, request, start, size, callback)

        self.show_column = {}
        if columns_to_show:
            for column_to_show in columns_to_show:
                self.show_column[column_to_show] = True

