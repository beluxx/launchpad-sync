Librarian Access
================

The librarian is a file storage service for launchpad. Conceptually
similar to other file storage API's like S3, it is used to store binary
or large content - bug attachments, package builds, images and so on.

Content in the librarian can be exposed at different urls. To expose
some content use a LibraryFileAlias. Private content is supported as
well - for that tokens are added to permit access for a limited time by
a client - each time a client attempts to dereference a private
LibraryFileAlias a token is emitted.


Deployment notes
================

(These may seem a bit out of place - they are, but they need to be
written down somewhere, and the deployment choices inform the
implementation choices).

The basics are simple: The librarian talks to clients. However
restricted file access makes things a little more complex. As the
librarian itself doesn't do SSL processing, and we want restricted files
to be kept confidential the librarian will need a hint from the SSL
front end that SSL was in fact used. The semi standard header Front-End-
Https can be used for this if we filter it in incoming requests from
clients.


setUp
-----

    >>> from lp.services.database.sqlbase import session_store
    >>> from lp.services.librarian.model import TimeLimitedToken


High Level
----------

    >>> import io
    >>> from lp.services.librarian.interfaces import ILibraryFileAliasSet
    >>> data = b"This is some data"

We can create LibraryFileAliases using the ILibraryFileAliasSet utility.
This name is a mouthful, but is consistent with the rest of our naming.

    >>> lfas = getUtility(ILibraryFileAliasSet)
    >>> from lp.services.librarian.interfaces import NEVER_EXPIRES
    >>> alias = lfas.create(
    ...     "text.txt",
    ...     len(data),
    ...     io.BytesIO(data),
    ...     "text/plain",
    ...     NEVER_EXPIRES,
    ... )
    >>> print(alias.mimetype)
    text/plain

    >>> print(alias.filename)
    text.txt

We may wish to set an expiry timestamp on the file. The NEVER_EXPIRES
constant means the file will never be removed from the Librarian, and
because of this should probably never be used.

    >>> alias.expires == NEVER_EXPIRES
    True

    >>> alias = lfas.create(
    ...     "text.txt", len(data), io.BytesIO(data), "text/plain"
    ... )

The default expiry of None means the file will expire a few days after
it is no longer referenced in the database.

    >>> alias.expires is None
    True

The creation timestamp of the LibraryFileAlias is available in the
date_created attribute.

    >>> alias.date_created
    datetime.datetime(...)

We can retrieve the LibraryFileAlias we just created using its ID or
sha256.

    >>> org_alias_id = alias.id
    >>> alias = lfas[org_alias_id]
    >>> alias.id == org_alias_id
    True

    >>> org_alias_id in [
    ...     a.id for a in lfas.findBySHA256(alias.content.sha256)
    ... ]
    True

We can get its URL too

    >>> from lp.services.config import config
    >>> import re
    >>> re.search(
    ...     r"^%s\d+/text.txt$" % config.librarian.download_url,
    ...     alias.http_url,
    ... ) is not None
    True

Librarian also serves the same file through https, we use this for
branding and similar inline-presented objects which would trigger
security warnings on https pages otherwise.

    >>> re.search(r"^https://.+/\d+/text.txt$", alias.https_url) is not None
    True

And we even have a convenient method which returns either the http URL
or the https one, depending on a config value.

    >>> config.vhosts.use_https
    False

    >>> re.search(
    ...     r"^%s\d+/text.txt$" % config.librarian.download_url,
    ...     alias.getURL(),
    ... ) is not None
    True

    >>> from textwrap import dedent
    >>> test_data = dedent(
    ...     """
    ...     [librarian]
    ...     use_https: true
    ...     """
    ... )
    >>> config.push("test", test_data)
    >>> re.search(r"^https://.+/\d+/text.txt$", alias.https_url) is not None
    True

Reset 'use_https' to its original state.

    >>> test_config_data = config.pop("test")

However, we can't access its contents until we have committed

    >>> alias.open()
    Traceback (most recent call last):
        [...]
    LookupError: ...

Once we commit the transaction, LibraryFileAliases can be accessed like
files.

    >>> import transaction
    >>> transaction.commit()

    >>> alias.open()
    >>> six.ensure_str(alias.read())
    'This is some data'

    >>> alias.close()

We can also read it in chunks.

    >>> alias.open()
    >>> six.ensure_str(alias.read(2))
    'Th'

    >>> six.ensure_str(alias.read(6))
    'is is '

    >>> six.ensure_str(alias.read())
    'some data'

    >>> alias.close()

If you don't want to read the file in chunks you can neglect to call
open() and close().

    >>> six.ensure_str(alias.read())
    'This is some data'

Each alias also has an expiry date associated with it, the default of
None meaning the file will expire a few days after nothing references it
any more:

    >>> alias.expires is None
    True

Closing an alias repeatedly and/or without opening it beforehand is
tolerated and will not result in exceptions being raised.

    >>> alias.close()
    >>> alias.close()


Low Level
---------

We can also use the ILibrarianClient Utility directly to store and
access files in the Librarian.

    >>> from lp.services.librarian.interfaces.client import ILibrarianClient
    >>> client = getUtility(ILibrarianClient)
    >>> aid = client.addFile(
    ...     "text.txt",
    ...     len(data),
    ...     io.BytesIO(data),
    ...     "text/plain",
    ...     NEVER_EXPIRES,
    ... )
    >>> transaction.commit()
    >>> f = client.getFileByAlias(aid)
    >>> six.ensure_str(f.read())
    'This is some data'

    >>> url = client.getURLForAlias(aid)
    >>> re.search(
    ...     r"^%s\d+/text.txt$" % config.librarian.download_url, url
    ... ) is not None
    True

When secure=True, the returned url has the id as part of the domain name
and the protocol is https:

    >>> expected = r"^https://i%d\..+:\d+/%d/text.txt$" % (aid, aid)
    >>> found = client.getURLForAlias(aid, secure=True)
    >>> re.search(expected, found) is not None
    True

Librarian reads are logged in the request timeline.

    >>> from lazr.restful.utils import get_current_browser_request
    >>> from lp.services.timeline.requesttimeline import get_request_timeline
    >>> request = get_current_browser_request()
    >>> timeline = get_request_timeline(request)
    >>> f = client.getFileByAlias(aid)
    >>> action = timeline.actions[-1]
    >>> action.category
    'librarian-connection'

    >>> action.detail.endswith("/text.txt")
    True

    >>> _unused = f.read()
    >>> action = timeline.actions[-1]
    >>> action.category
    'librarian-read'

    >>> action.detail.endswith("/text.txt")
    True

At this level we can also reverse the transactional semantics by using
the remoteAddFile instead of the addFile method. In this case, the
database rows are added by the Librarian, which means that the file is
downloadable immediately and will exist even if the client transaction
rolls back. However, the records in the database will not be visible to
the client until it begins a new transaction.

    >>> url = client.remoteAddFile(
    ...     "text.txt", len(data), io.BytesIO(data), "text/plain"
    ... )
    >>> print(url)
    http://.../text.txt

    >>> from urllib.request import urlopen
    >>> six.ensure_str(urlopen(url).read())
    'This is some data'

If we abort the transaction, it is still in there

    >>> transaction.abort()
    >>> six.ensure_str(urlopen(url).read())
    'This is some data'

You can also set the expiry date on the file this way too:

    >>> from datetime import date, datetime, timezone
    >>> url = client.remoteAddFile(
    ...     "text.txt",
    ...     len(data),
    ...     io.BytesIO(data),
    ...     "text/plain",
    ...     expires=datetime(2005, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
    ... )
    >>> transaction.abort()

To check the expiry is set, we need to extract the alias id from the
URL. remoteAddFile deliberately returns the URL instead of the alias id
because, except for test cases, the URL is the only thing useful
(because the client can't see the database records yet).

    >>> import re
    >>> match = re.search(r"/(\d+)/", url)
    >>> alias_id = int(match.group(1))
    >>> alias = lfas[alias_id]
    >>> print(alias.expires.isoformat())
    2005-09-01T12:00:00+00:00


Restricted Librarian
--------------------

Some files should not be generally available publicly. If you know the
URL, any file can be retrieved directly from the librarian. For this
reason, there is a restricted librarian to which access is restricted
(at the system-level). This means that only Launchpad has direct access
to the host. You use the IRestrictedLibrarianClient to access this
librarian.

    >>> from zope.interface.verify import verifyObject
    >>> from lp.services.librarian.interfaces.client import (
    ...     IRestrictedLibrarianClient,
    ... )
    >>> restricted_client = getUtility(IRestrictedLibrarianClient)
    >>> verifyObject(IRestrictedLibrarianClient, restricted_client)
    True

File alias uploaded through the restricted librarian have the restricted
attribute set.

    >>> private_content = b"This is private data."
    >>> private_file_id = restricted_client.addFile(
    ...     "private.txt",
    ...     len(private_content),
    ...     io.BytesIO(private_content),
    ...     "text/plain",
    ... )
    >>> file_alias = getUtility(ILibraryFileAliasSet)[private_file_id]
    >>> file_alias.restricted
    True

    >>> transaction.commit()
    >>> file_alias.open()
    >>> print(six.ensure_str(file_alias.read()))
    This is private data.

    >>> file_alias.close()

Restricted files are accessible with HTTP on a private domain.

    >>> print(file_alias.http_url)
    http://.../private.txt

    >>> file_alias.http_url.startswith(
    ...     config.librarian.restricted_download_url
    ... )
    True

They can also be accessed externally using a time-limited token appended
to their private_url. Possession of a token is sufficient to grant
access to a file, regardless of who is logged in. getURL can be asked to
provide such a token.

    >>> import hashlib
    >>> token_url = file_alias.getURL(include_token=True)
    >>> print(token_url)
    https://i...restricted.../private.txt?token=...

    >>> token_url.startswith("https://i%d.restricted." % file_alias.id)
    True

    >>> private_path = TimeLimitedToken.url_to_token_path(
    ...     file_alias.private_url
    ... )
    >>> url_token = token_url.split("=")[1].encode("ASCII")
    >>> hashlib.sha256(url_token).hexdigest() == session_store().find(
    ...     TimeLimitedToken, path=private_path
    ... ).any().token
    True

LibraryFileAliasView doesn't work on restricted files. This is a
temporary measure until we're sure no restricted files leak into the
traversal hierarchy.

    >>> from zope.component import getMultiAdapter
    >>> view = getMultiAdapter((file_alias, request), name="+index")
    >>> view.initialize()
    Traceback (most recent call last):
    ...
    AssertionError

If you try to retrieve this file through the standard ILibrarianClient,
you'll get a DownloadFailed error.

    >>> client.getFileByAlias(private_file_id)
    Traceback (most recent call last):
      ...
    lp.services.librarian.interfaces.client.DownloadFailed:
    Alias ... cannot be downloaded from this client.

    >>> client.getURLForAlias(private_file_id)
    Traceback (most recent call last):
      ...
    lp.services.librarian.interfaces.client.DownloadFailed:
    Alias ... cannot be downloaded from this client.

But using the restricted librarian will work:

    >>> restricted_client.getFileByAlias(private_file_id)
    <lp.services.librarian.client._File...>

    >>> file_url = restricted_client.getURLForAlias(private_file_id)
    >>> print(file_url)
    http://.../private.txt

Trying to access that file directly on the normal librarian will fail
(by switching the port)

    >>> sneaky_url = file_url.replace(
    ...     config.librarian.restricted_download_url,
    ...     config.librarian.download_url,
    ... )
    >>> urlopen(sneaky_url).read()
    Traceback (most recent call last):
      ...
    urllib.error.HTTPError: HTTP Error 404: Not Found

But downloading it from the restricted host, will work.

    >>> print(six.ensure_str(urlopen(file_url).read()))
    This is private data.

Trying to retrieve a non-restricted file from the restricted librarian
also fails:

    >>> public_content = b"This is public data."
    >>> public_file_id = getUtility(ILibrarianClient).addFile(
    ...     "public.txt",
    ...     len(public_content),
    ...     io.BytesIO(public_content),
    ...     "text/plain",
    ... )
    >>> file_alias = getUtility(ILibraryFileAliasSet)[public_file_id]
    >>> file_alias.restricted
    False

    >>> transaction.commit()

    >>> restricted_client.getURLForAlias(public_file_id)
    Traceback (most recent call last):
      ...
    lp.services.librarian.interfaces.client.DownloadFailed: ...

    >>> restricted_client.getFileByAlias(public_file_id)
    Traceback (most recent call last):
      ...
    lp.services.librarian.interfaces.client.DownloadFailed: ...

The remoteAddFile() on the restricted client, also creates a restricted
file:

    >>> url = restricted_client.remoteAddFile(
    ...     "another-private.txt",
    ...     len(private_content),
    ...     io.BytesIO(private_content),
    ...     "text/plain",
    ... )
    >>> print(url)
    http://.../another-private.txt

    >>> url.startswith(config.librarian.restricted_download_url)
    True

The file can then immediately be retrieved:

    >>> print(six.ensure_str(urlopen(url).read()))
    This is private data.

Another way to create a restricted file is by using the restricted
parameter to ILibraryFileAliasSet:

    >>> restricted_file = getUtility(ILibraryFileAliasSet).create(
    ...     "yet-another-private.txt",
    ...     len(private_content),
    ...     io.BytesIO(private_content),
    ...     "text/plain",
    ...     restricted=True,
    ... )
    >>> restricted_file.restricted
    True

Even if one has the SHA1 of the file, searching the librarian for it
will only return the file if it was in the same restriction space.

So searching for the private content on the public librarian will fail:

    >>> transaction.commit()
    >>> search_query = "search?digest=%s" % restricted_file.content.sha1
    >>> print(
    ...     six.ensure_str(
    ...         urlopen(config.librarian.download_url + search_query).read()
    ...     )
    ... )
    0

But on the restricted server, this will work:

    >>> result = six.ensure_str(
    ...     urlopen(
    ...         config.librarian.restricted_download_url + search_query
    ...     ).read()
    ... )
    >>> result = result.splitlines()
    >>> print(result[0])
    3

    >>> sorted(file_path.split("/")[1] for file_path in result[1:])
    ['another-private.txt', 'private.txt', 'yet-another-private.txt']


Odds and Sods
-------------

An UploadFailed will be raised if you try to create a file with no
content

    >>> client.addFile("test.txt", 0, io.BytesIO(b"hello"), "text/plain")
    Traceback (most recent call last):
        [...]
    lp.services.librarian.interfaces.client.UploadFailed: Invalid length: 0

If you really want a zero length file you can do it:

    >>> aid = client.addFile(
    ...     "test.txt", 0, io.BytesIO(), "text/plain", allow_zero_length=True
    ... )
    >>> transaction.commit()
    >>> f = client.getFileByAlias(aid)
    >>> six.ensure_str(f.read())
    ''

An AssertionError will be raised if the number of bytes that could be
read from the file don't match the declared size.

    >>> client.addFile("test.txt", 42, io.BytesIO(), "text/plain")
    Traceback (most recent call last):
        [...]
    AssertionError: size is 42, but 0 were read from the file

Filenames with spaces in them work.

    >>> aid = client.addFile(
    ...     "hot dog", len(data), io.BytesIO(data), "text/plain"
    ... )
    >>> transaction.commit()
    >>> f = client.getFileByAlias(aid)
    >>> six.ensure_str(f.read())
    'This is some data'

    >>> url = client.getURLForAlias(aid)
    >>> re.search(r"/\d+/hot%20dog$", url) is not None
    True

Unicode file names work.  Note that the filename in the resulting URL is
encoded as UTF-8.

    >>> aid = client.addFile(
    ...     "Yow\N{INTERROBANG}", len(data), io.BytesIO(data), "text/plain"
    ... )
    >>> transaction.commit()
    >>> f = client.getFileByAlias(aid)
    >>> six.ensure_str(f.read())
    'This is some data'

    >>> url = client.getURLForAlias(aid)
    >>> re.search(r"/\d+/Yow%E2%80%BD$", url) is not None
    True

Files will get garbage collected on production systems as per
LibrarianGarbageCollection. If you request the URL of a deleted file,
you will be given None

    >>> alias = lfas[36]
    >>> alias.deleted
    True

    >>> alias.http_url is None
    True

    >>> alias.https_url is None
    True

    >>> alias.getURL() is None
    True

    >>> client.getURLForAlias(alias.id) is None
    True


Default View
------------

A librarian file has a default view that should redirect to the download
URL.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> req = LaunchpadTestRequest()
    >>> alias = lfas.create(
    ...     "text2.txt",
    ...     len(data),
    ...     io.BytesIO(data),
    ...     "text/plain",
    ...     NEVER_EXPIRES,
    ... )
    >>> transaction.commit()
    >>> lfa_view = getMultiAdapter((alias, req), name="+index")
    >>> lfa_view.initialize()
    >>> req.response.getHeader("Location") == alias.getURL()
    True


File views setup
----------------

We need some files to test different ways of accessing them.

    >>> filename = "public.txt"
    >>> content = b"PUBLIC"
    >>> public_file = getUtility(ILibraryFileAliasSet).create(
    ...     filename,
    ...     len(content),
    ...     io.BytesIO(content),
    ...     "text/plain",
    ...     NEVER_EXPIRES,
    ...     restricted=False,
    ... )

    >>> filename = "restricted.txt"
    >>> content = b"RESTRICTED"
    >>> restricted_file = getUtility(ILibraryFileAliasSet).create(
    ...     filename,
    ...     len(content),
    ...     io.BytesIO(content),
    ...     "text/plain",
    ...     NEVER_EXPIRES,
    ...     restricted=True,
    ... )

    # Create a new LibraryFileAlias not referencing any LibraryFileContent
    # record. Such records are considered as being deleted.

    >>> from lp.services.librarian.model import LibraryFileAlias
    >>> from lp.services.database.interfaces import IPrimaryStore

    >>> deleted_file = LibraryFileAlias(
    ...     content=None, filename="deleted.txt", mimetype="text/plain"
    ... )
    >>> ignore = IPrimaryStore(LibraryFileAlias).add(deleted_file)

Commit the just-created files.

    >>> transaction.commit()

    >>> deleted_file = getUtility(ILibraryFileAliasSet)[deleted_file.id]
    >>> print(deleted_file.deleted)
    True

Clear out existing tokens.

    >>> _ = session_store().find(TimeLimitedToken).remove()


LibraryFileAliasMD5View
-----------------------

The MD5 summary for a file can be downloaded. The text file contains the
hash and file name.

    >>> view = create_view(public_file, "+md5")
    >>> print(view.render())
    cd0c6092d6a6874f379fe4827ed1db8b public.txt

    >>> print(view.request.response.getHeader("Content-type"))
    text/plain


Download counts
---------------

The download counts for librarian files are stored in the
LibraryFileDownloadCount table, broken down by day and country, but
there's also a 'hits' attribute on ILibraryFileAlias, which holds the
total number of times that file has been downloaded.

The count starts at 0, and cannot be changed directly.

    >>> public_file.hits
    0

    >>> public_file.hits = 10
    Traceback (most recent call last):
    ...
    zope.security.interfaces.ForbiddenAttribute: ...

To change that, we have to use the updateDownloadCount() method, which
takes care of creating/updating the necessary LibraryFileDownloadCount
entries.

    >>> from lp.services.worlddata.interfaces.country import ICountrySet
    >>> country_set = getUtility(ICountrySet)
    >>> november_1st_2006 = date(2006, 11, 1)
    >>> brazil = country_set["BR"]
    >>> public_file.updateDownloadCount(november_1st_2006, brazil, count=1)
    >>> public_file.hits
    1

This was the first hit for that file from Brazil on 2006 November first,
so a new LibraryFileDownloadCount was created.

    >>> from lp.services.librarian.model import LibraryFileDownloadCount
    >>> from storm.locals import Store
    >>> store = Store.of(public_file)
    >>> brazil_entry = store.find(
    ...     LibraryFileDownloadCount,
    ...     libraryfilealias=public_file,
    ...     country=brazil,
    ...     day=november_1st_2006,
    ... ).one()
    >>> brazil_entry.count
    1

Below we simulate a hit from Japan on that same day, which will also
create a new LibraryFileDownloadCount.

    >>> japan = country_set["JP"]
    >>> public_file.updateDownloadCount(november_1st_2006, japan, count=3)
    >>> public_file.hits
    4

    >>> japan_entry = store.find(
    ...     LibraryFileDownloadCount,
    ...     libraryfilealias=public_file,
    ...     country=japan,
    ...     day=november_1st_2006,
    ... ).one()
    >>> japan_entry.count
    3

If there's another hit from Brazil on the same day, the existing entry
will be updated.

    >>> public_file.updateDownloadCount(november_1st_2006, brazil, count=2)
    >>> public_file.hits
    6

    >>> brazil_entry.count
    3

If the hit happened on a different day, a separate entry would be
created.

    >>> november_2nd_2006 = date(2006, 11, 2)
    >>> public_file.updateDownloadCount(november_2nd_2006, brazil, count=10)
    >>> public_file.hits
    16

    >>> brazil_entry2 = store.find(
    ...     LibraryFileDownloadCount,
    ...     libraryfilealias=public_file,
    ...     country=brazil,
    ...     day=november_2nd_2006,
    ... ).one()
    >>> brazil_entry2.count
    10

    >>> last_downloaded_date = november_2nd_2006


Time to last download
---------------------

The .last_downloaded property gives us the time delta from today to the
day that file was last downloaded, or None if it's never been
downloaded.

    >>> today = datetime.now(timezone.utc).date()
    >>> public_file.last_downloaded == today - last_downloaded_date
    True

    >>> content = b"something"
    >>> brand_new_file = getUtility(ILibraryFileAliasSet).create(
    ...     "new.txt",
    ...     len(content),
    ...     io.BytesIO(content),
    ...     "text/plain",
    ...     NEVER_EXPIRES,
    ...     restricted=False,
    ... )
    >>> print(brand_new_file.last_downloaded)
    None
