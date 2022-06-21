*******************************
Using launchpadlib in pagetests
*******************************

As an alternative to crafting HTTP requests with the 'webservice'
object, you can write pagetests using launchpadlib.

    >>> from fixtures import (
    ...     EnvironmentVariable,
    ...     TempDir,
    ...     )
    >>> tempdir_fixture = TempDir()
    >>> tempdir_fixture.setUp()
    >>> home_fixture = EnvironmentVariable('HOME', tempdir_fixture.path)
    >>> home_fixture.setUp()

Two helper functions make it easy to set up Launchpad objects that
can access the web service. With launchpadlib_for() you can set up a
Launchpad object for a given user with a single call.

    >>> launchpad = launchpadlib_for(
    ...     u'launchpadlib test', 'salgado', 'WRITE_PUBLIC')
    >>> print(launchpad.me.name)
    salgado

    # XXX leonardr 2010-03-31 bug=552732
    # launchpadlib doesn't work with a credential scoped to a context
    # like 'firefox', because the service root resource is considered
    # out of scope. This test should pass, but it doesn't.
    #
    # When you fix this, be sure to show that an attempt to access
    # something that really is out of scope (like launchpad.me.name)
    # yields a 401 error.
    #
    #>>> launchpad = launchpadlib_for(
    #...     u'launchpadlib test', 'no-priv', 'READ_PRIVATE', 'firefox',
    #...     version="devel")
    #>>> print(launchpad.projects['firefox'].name)
    #firefox

With launchpadlib_credentials_for() you can get a launchpadlib
Credentials object.

    >>> from lp.testing import launchpadlib_credentials_for
    >>> credentials = launchpadlib_credentials_for(
    ...     u'launchpadlib test', 'no-priv', 'READ_PUBLIC')
    >>> credentials
    <launchpadlib.credentials.Credentials object ...>

    >>> print(credentials.consumer.key)
    launchpadlib test
    >>> print(credentials.access_token)
    oauth_token_secret=...&oauth_token=...

This can be used to create your own Launchpad object.  Note you cannot
use launchpadlib.uris.DEV_SERVICE_ROOT as the URL as it uses the https
scheme which does not work in the test environment.

    >>> from launchpadlib.launchpad import Launchpad
    >>> launchpad = Launchpad(
    ...     credentials, None, None, 'http://api.launchpad.test/')
    >>> print(launchpad.me.name)
    no-priv

Anonymous access
================

    >>> lp_anon = Launchpad.login_anonymously('launchpadlib test',
    ...                                       'http://api.launchpad.test/')

The Launchpad object for the anonymous user can be used to access
public information.

    >>> apache_results = lp_anon.project_groups.search(text="Apache")
    >>> print(apache_results[0].name)
    apache

But trying to access information that requires a logged in user
results in an error.

    >>> print(lp_anon.me.name)
    Traceback (most recent call last):
      ...
    lazr.restfulclient.errors.Unauthorized: HTTP Error 401: Unauthorized...


Caching
=======

Let's make sure Launchpad serves caching-related headers that make
launchpadlib work correctly. First, we set up a temporary directory to
store the cache.

    >>> import tempfile
    >>> cache = tempfile.mkdtemp()

Then we make it possible to view the HTTP traffic between launchpadlib
and Launchpad.

    >>> import httplib2
    >>> old_debug_level = httplib2.debuglevel
    >>> httplib2.debuglevel = 1

Now create a Launchpad object and observe how it populates the cache.

    >>> launchpad = Launchpad(
    ...     credentials, None, None, 'http://api.launchpad.test/',
    ...     cache=cache)
    send: ...'GET /1.0/ ...accept: application/vnd.sun.wadl+xml...'
    reply: 'HTTP/1.0 200 Ok\n'
    ...
    send: ...'GET /1.0/ ...accept: application/json...'
    reply: 'HTTP/1.0 200 Ok\n'
    ...

Create a second Launchpad object, and the cached documents will be
used instead of new HTTP requests being used.

    >>> launchpad = Launchpad(
    ...     credentials, None, None, 'http://api.launchpad.test/',
    ...     cache=cache)

Cleanup.

    >>> import shutil
    >>> shutil.rmtree(cache)
    >>> httplib2.debuglevel = old_debug_level

Cache location
--------------

The cache location for Launchpad objects created via launchpadlib_for are a
temp directory.

    >>> launchpad = launchpadlib_for(
    ...     u'launchpadlib test', 'salgado', 'WRITE_PUBLIC')

    >>> launchpad._browser._connection.cache._cache_dir
    '/.../launchpadlib-cache-...'

If we create another Launchpad object, it'll get its own cache directory.

    >>> launchpad_2 = launchpadlib_for(
    ...     u'launchpadlib test', 'salgado', 'WRITE_PUBLIC')

    >>> cache_dir_1 = launchpad._browser._connection.cache._cache_dir
    >>> cache_dir_2 = launchpad_2._browser._connection.cache._cache_dir

    >>> cache_dir_2 != cache_dir_1
    True

We use zope.testing.cleanup to manage cleaning up of the cache directories,
therefore we can peek inside its registry of clean-up actions and see the
clean-up functions biding their time.

    >>> import zope.testing.cleanup
    >>> zope.testing.cleanup._cleanups
    [...(<function _clean_up_cache...>, ('/.../launchpadlib-cache-...'...)...]

    >>> home_fixture.cleanUp()
    >>> tempdir_fixture.cleanUp()
