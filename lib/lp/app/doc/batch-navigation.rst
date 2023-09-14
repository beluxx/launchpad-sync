================
Batch Navigation
================

Most of the test for this behaviour is in the lazr.batchnavigation package.

This documents and tests the Launchpad-specific elements of its usage.

Note that our use of the batching code relies on the registration of
lp.services.webapp.batching.FiniteSequenceAdapter for
storm.zope.interfaces.IResultSet and
storm.zope.interfaces.ISQLObjectResultSet.

Batch navigation provides a way to navigate batch results in a web
page by providing URL links to the next, previous and numbered pages
of results.

It uses two arguments to control the batching:

  - start: The first item we should show in current batch.
  - batch: Controls the amount of items we are showing per batch. It will only
           appear if it's different from the default value set when the batch
           is created.

Imports:

    >>> from lp.services.webapp.batching import BatchNavigator
    >>> from lp.services.webapp.servers import LaunchpadTestRequest

    >>> def build_request(query_string_args=None, method="GET"):
    ...     if query_string_args is None:
    ...         query_string_args = {}
    ...     query_string = "&".join(
    ...         "%s=%s" % (k, v) for k, v in query_string_args.items()
    ...     )
    ...     request = LaunchpadTestRequest(
    ...         SERVER_URL="http://www.example.com/foo",
    ...         method=method,
    ...         environ={"QUERY_STRING": query_string},
    ...     )
    ...     request.processInputs()
    ...     return request
    ...

A dummy request object:

Some sample data.

    >>> reindeer = [
    ...     "Dasher",
    ...     "Dancer",
    ...     "Prancer",
    ...     "Vixen",
    ...     "Comet",
    ...     "Cupid",
    ...     "Donner",
    ...     "Blitzen",
    ...     "Rudolph",
    ... ]


Multiple pages
==============

The batch navigator tells us whether multiple pages will be used.

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.services.identity.model.emailaddress import EmailAddress
    >>> select_results = (
    ...     IStore(EmailAddress).find(EmailAddress).order_by("id")
    ... )
    >>> batch_nav = BatchNavigator(select_results, build_request(), size=50)
    >>> batch_nav.has_multiple_pages
    True

    >>> one_page_nav = BatchNavigator(
    ...     select_results, build_request(), size=200
    ... )
    >>> one_page_nav.has_multiple_pages
    False

Maximum batch size
==================

Since the batch size is exposed in the URL, it's possible for users to
tweak the batch parameter to retrieve more results. Since that may
potentially exhaust server resources, an upper limit is put on the batch
size. If the requested batch parameter is higher than this, an
InvalidBatchSizeError is raised.

    >>> from lp.services.config import config
    >>> from textwrap import dedent
    >>> config.push(
    ...     "max-batch-size",
    ...     dedent(
    ...         """\
    ...     [launchpad]
    ...     max_batch_size: 5
    ...     """
    ...     ),
    ... )
    >>> request = build_request({"start": "0", "batch": "20"})
    >>> BatchNavigator(reindeer, request=request)
    Traceback (most recent call last):
      ...
    lazr.batchnavigator.interfaces.InvalidBatchSizeError:
    Maximum for "batch" parameter is 5.

    >>> ignored = config.pop("max-batch-size")


Batch views
===========

A view is often used with a BatchNavigator to determine when to
display the current batch.

If the current batch is empty, nothing is rendered for the
upper and lower navigation link views.

    >>> from zope.component import getMultiAdapter

    >>> request = build_request({"start": "0", "batch": "10"})
    >>> navigator = BatchNavigator([], request=request)
    >>> upper_view = getMultiAdapter(
    ...     (navigator, request), name="+navigation-links-upper"
    ... )
    >>> print(upper_view.render())
    <BLANKLINE>

    >>> lower_view = getMultiAdapter(
    ...     (navigator, request), name="+navigation-links-lower"
    ... )
    >>> print(lower_view.render())
    <BLANKLINE>

When there is a current batch, but there are no previous or next
batches, both the upper and lower navigation links view will render.

    >>> navigator = BatchNavigator(reindeer, request=request)
    >>> upper_view = getMultiAdapter(
    ...     (navigator, request), name="+navigation-links-upper"
    ... )
    >>> print(upper_view.render())
    <table...
    ...<strong>1</strong>...&rarr;...<strong>9</strong>...of 9 results...
    ...<span class="first inactive">...First...
    ...<span class="previous inactive">...Previous...
    ...<span class="next inactive">...Next...
    ...<span class="last inactive">...Last...

    >>> lower_view = getMultiAdapter(
    ...     (navigator, request), name="+navigation-links-lower"
    ... )
    >>> print(lower_view.render())
    <table...
    ...<strong>1</strong>...&rarr;...<strong>9</strong>...of 9 results...
    ...<span class="first inactive">...First...
    ...<span class="previous inactive">...Previous...
    ...<span class="next inactive">...Next...
    ...<span class="last inactive">...Last...
