=================
Profiling support
=================

..  ReST Comment: this is intended to be a true DOC test, with an emphasis on
    documentation.  Of the three sections, the last two have been adjusted for
    this goal.

Launchpad supports three modes of profiling.

Profiling requests in pagetests
===============================

Our testing framework has support for profiling requests made in
pagetests.  When the PROFILE_PAGETESTS_REQUESTS environment variable is
set, it will save profiling information in the file specified in that
variable.

The pagetests profiler is created by the layer during its setUp.

    >>> from lp.testing.layers import PageTestLayer

(Save the existing configuration.)

    >>> import os
    >>> import tempfile

    >>> old_profile_environ = os.environ.get(
    ...     'PROFILE_PAGETESTS_REQUESTS', '')

    >>> pagetests_profile_dir = tempfile.mkdtemp(prefix='pagetests_profile')
    >>> pagetests_profile = os.path.join(
    ...     pagetests_profile_dir, 'pagetests.prof')
    >>> os.environ['PROFILE_PAGETESTS_REQUESTS'] = pagetests_profile

    >>> PageTestLayer.setUp()
    >>> PageTestLayer.profiler
    <...Profile...>
    >>> len(PageTestLayer.profiler.getstats())
    0

The layer also adds WSGI middleware that takes care of profiling (among
other things).

    >>> from lp.testing.pages import http

    # We need to close the default interaction.
    >>> logout()

    >>> response = http('GET / HTTP/1.0')
    >>> profile_count = len(PageTestLayer.profiler.getstats())
    >>> profile_count > 0
    True

Requests made with a testbrowser will also be profiled.

    >>> from zope.testbrowser.wsgi import Browser
    >>> browser = Browser()
    >>> browser.open('http://launchpad.test/')
    >>> len(PageTestLayer.profiler.getstats()) > profile_count
    True

Once the layer finishes, it saves the profile data in the requested file.

    >>> PageTestLayer.tearDown()
    >>> import pstats
    >>> stats = pstats.Stats(pagetests_profile)
    >>> os.remove(pagetests_profile)

When the environment isn't set, no profile is created.

    >>> del os.environ['PROFILE_PAGETESTS_REQUESTS']

    >>> PageTestLayer.setUp()
    >>> print(PageTestLayer.profiler)
    None

And no stats file is written when the layer is torn down.

    >>> PageTestLayer.tearDown()
    >>> os.path.exists(pagetests_profile)
    False


Profiling request in the app server
===================================

It is also possible to get a profile of requests served by the app
server.

*Important*: This is not blessed for production, primarily because of
the typical cost of employing a profiling hook.  Also, profiled requests
are forced to run in serial.  This is also a concern for production
usage, since some of our requests can take much longer than others.

It might be fine to occasionally turn on in staging; that is more
negotiable, at least.  LOSAs will need to vet the feature to see if they are
concerned about it giving too much information about our staging system.

The feature has two modes.

-   It can be configured to optionally profile requests.  To turn this on, in
    ``launchpad-lazr.conf`` (e.g.,
    ``configs/development/launchpad-lazr.conf``) , in the ``[profiling]``
    section, set ``profiling_allowed: True``.  As of this writing, this
    is the default value for development.

    Once it is turned on, you can insert /++profile++/ in the URL to get
    basic instructions on how to use the feature.  You use the
    ``launchpad-lazr.conf`` ``profile_dir`` setting to determine what
    directory will receive written profiles.

..  This ReST comment tests the assertion above that profiling_allowed is
    True by default for tests and development.

    >>> from lp.services.config import config
    >>> config.profiling.profiling_allowed
    True

    Similarly, this tests that, in a fully set-up environment, the
    profiling machinery that is coded and unit-tested in
    lp/services/profile is hooked up properly.  This is intended to be a
    smoke test.  The unit tests verify further functionality.

    >>> response = http('GET /++profile++ HTTP/1.0')
    >>> b'<h1>Profiling Information</h1>' in response.getBody()
    True

-   It can be configured to profile all requests, indiscriminately.  To turn
    this on, use the ``profiling_allowed`` setting described in option 1
    above and also set ``profile_all_requests: True`` in the
    ``[profiling]`` section of ``launchpad-lazr.conf``.  This is turned
    off by default.  As with the first option, you use the
    ``profile_dir`` setting to determine what directory will receive the
    profiles.

    Once it is turned on, every request will create a profiling log usable
    with KCacheGrind.  The browser will include information on the file
    created for that request.

..  This ReST comment tests the assertion above that profile_all_requests is
    False by default for tests and development.

    >>> from lp.services.config import config
    >>> config.profiling.profile_all_requests
    False

Profile files are named based on the time of the request start, the
pageid, and the thread that processed it.

Together with the profiling information, an informational OOPS report is
usually also created.

If the request actually resulted in an OOPS, the logged OOPS will have
the real exception information, instead of being an informational
ProfilingOops.

In either case, the OOPS id is referenced in the profiling log's
filename.

Memory profiling
================

It is possible to keep a log of the memory profile of the application. That's
useful to try to figure out what requests are causing the memory usage of the
server to increase.

This is not blessed for production use at this time: the implementation relies
on lib/lp/services/profile/mem.py, which as of this writing warns in its
docstring that "[n]one of this should be in day-to-day use."  We should
document the source of these concerns and evaluate them before using it in
production.  Staging may be more acceptable.

Note that the data collected will be polluted by parallel requests: if
memory increases in one request while another is also running in a different
thread, both requests will show the increase.

It also will probably be polluted by simultaneous use of the profiling
options described above (`Profiling request in the app server`_).

To turn this on, use the ``profiling_allowed`` setting described in the
previous profiling section, and also set the ``memory_profile_log`` in
the ``[profiling]`` section of ``launchpad-lazr.conf`` to a path to a
log file.

..  This ReST comment tests the assertion above that memory_profile_log is
    the way to turn on memory profiling.  It is intended to be a smoke test.
    The real tests are in the lp/services/profile package.

    >>> profile_dir = tempfile.mkdtemp(prefix='profile')
    >>> memory_profile_log = os.path.join(profile_dir, 'memory.log')
    >>> from textwrap import dedent
    >>> config.push('memory_profile', dedent("""
    ...     [profiling]
    ...     profile_request: False
    ...     memory_profile_log: %s""" % memory_profile_log))
    >>> response = http('GET / HTTP/1.0')
    >>> with open(memory_profile_log) as memory_profile_fh:
    ...     (timestamp, page_id, oops_id, duration,
    ...      start_vss, start_rss, end_vss, end_rss) = (
    ...         memory_profile_fh.readline().split())
    >>> print(timestamp)
    20...
    >>> print(oops_id)
    -
    >>> print(page_id)
    RootObject:index.html

..  ReST comment: this is clean up for the work done above.

    >>> import shutil
    >>> os.environ['PROFILE_PAGETESTS_REQUESTS'] = old_profile_environ
    >>> shutil.rmtree(pagetests_profile_dir)
    >>> shutil.rmtree(profile_dir)
    >>> old_config = config.pop('memory_profile')
