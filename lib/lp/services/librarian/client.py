# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "FileDownloadClient",
    "FileUploadClient",
    "get_libraryfilealias_download_path",
    "LibrarianClient",
    "RestrictedLibrarianClient",
    "url_path_quote",
]


import hashlib
import http.client
import select
import socket
import threading
import time
from socket import AF_INET, SOCK_STREAM
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse, urlunparse
from urllib.request import urlopen

import six
from lazr.restful.utils import get_current_browser_request
from storm.store import Store
from zope.interface import implementer

from lp.services.config import config, dbconfig
from lp.services.database.interfaces import IPrimaryStore
from lp.services.database.postgresql import ConnectionString
from lp.services.database.sqlobject import SQLObjectNotFound
from lp.services.librarian.interfaces.client import (
    LIBRARIAN_SERVER_DEFAULT_TIMEOUT,
    DownloadFailed,
    ILibrarianClient,
    IRestrictedLibrarianClient,
    LibrarianServerError,
    UploadFailed,
)
from lp.services.timeline.requesttimeline import get_request_timeline


def url_path_quote(filename):
    """Quote `filename` for use in a URL."""
    # RFC 3986 says ~ should not be generated escaped, but urllib.parse.quote
    # predates it. Additionally, + is safe to use unescaped in paths and is
    # frequently used in Debian versions, so leave it alone.
    #
    # This needs to match Library.getAlias' TimeLimitedToken handling.
    return quote(filename, safe="/~+")


def get_libraryfilealias_download_path(aliasID, filename):
    """Download path for a given `LibraryFileAlias` id and filename."""
    return "/%d/%s" % (int(aliasID), url_path_quote(filename))


def compose_url(base_url, alias_path):
    """Compose a URL for a library file alias."""
    if alias_path is None:
        return None
    else:
        return urljoin(base_url, alias_path)


class FileUploadClient:
    """Simple blocking client for uploading to the librarian."""

    s_poll_timeout = 0

    def __init__(self):
        # This class is registered as a utility, which means an instance of
        # it will be shared between threads. The easiest way of making this
        # class thread safe is by storing all state in a thread local.
        self.state = threading.local()

    def _connect(self):
        """Connect this client.

        The host and port default to what is specified in the configuration
        """
        try:
            self.state.s = socket.socket(AF_INET, SOCK_STREAM)
            if config.librarian.client_socket_timeout is not None:
                self.state.s.settimeout(config.librarian.client_socket_timeout)
            self.state.s.connect((self.upload_host, self.upload_port))
            self.state.f = self.state.s.makefile("rwb", 0)

            # Register epoll for the socket.
            self.state.s_poll = select.epoll()
            self.state.s_poll.register(self.state.s.fileno(), select.EPOLLIN)
        except OSError as x:
            raise UploadFailed(
                "[%s:%s]: %s" % (self.upload_host, self.upload_port, x)
            )

    def _close(self):
        """Close connection"""
        if hasattr(self.state, "s_poll"):
            self.state.s_poll.unregister(self.state.s.fileno())
            self.state.s_poll.close()
            del self.state.s_poll
        if hasattr(self.state, "s"):
            self.state.s.close()
            del self.state.s
        if hasattr(self.state, "f"):
            self.state.f.close()
            del self.state.f

    def _checkError(self):
        poll_result = self.state.s_poll.poll(self.s_poll_timeout)
        if poll_result:
            fileno, event = poll_result[0]
            # Accepts any event that contains input data. Even if we
            # only subscribed to EPOLLIN, when connection is closed right
            # after sending data, we will receive [EPOLLHUP | EPOLLERR |
            # EPOLLIN] == 25, for example). EPOLLIN is the first bit,
            # so we should check just that for incoming data.
            if fileno != self.state.s.fileno() or not (event & select.EPOLLIN):
                return
            response = six.ensure_str(
                self.state.f.readline().strip(), errors="replace"
            )
            raise UploadFailed("Server said early: " + response)

    def _sendLine(self, line, check_for_error_responses=True):
        self.state.f.write(line + b"\r\n")
        if check_for_error_responses:
            self._checkError()

    def _sendHeader(self, name, value):
        self._sendLine(six.ensure_binary("%s: %s" % (name, value)))

    def addFile(
        self,
        name,
        size,
        file,
        contentType,
        expires=None,
        debugID=None,
        allow_zero_length=False,
    ):
        """Add a file to the librarian.

        :param name: Name to store the file as
        :param size: Size of the file
        :param file: File-like object with the content in it
        :param contentType: mime-type, e.g. text/plain
        :param expires: Expiry time of file. See LibrarianGarbageCollection.
            Set to None to only expire when it is no longer referenced.
        :param debugID: Optional.  If set, causes extra logging for this
            request on the server, which will be marked with the value
            given.
        :param allow_zero_length: If True permit zero length files.
        :returns: aliasID as an integer
        :raises UploadFailed: If the server rejects the upload for some
            reason.
        """
        if file is None:
            raise TypeError("Bad File Descriptor: %s" % repr(file))
        if allow_zero_length:
            min_size = -1
        else:
            min_size = 0
        if size <= min_size:
            raise UploadFailed("Invalid length: %d" % size)

        name = six.ensure_binary(name)

        # Import in this method to avoid a circular import
        from lp.services.librarian.model import (
            LibraryFileAlias,
            LibraryFileContent,
        )

        try:
            self._connect()

            # Get the name of the database the client is using, so that
            # the server can check that the client is using the same
            # database as the server.
            store = IPrimaryStore(LibraryFileAlias)
            databaseName = self._getDatabaseName(store)

            # Generate new content and alias IDs.
            # (we'll create rows with these IDs later, but not yet)
            contentID = store.execute(
                "SELECT nextval('libraryfilecontent_id_seq')"
            ).get_one()[0]
            aliasID = store.execute(
                "SELECT nextval('libraryfilealias_id_seq')"
            ).get_one()[0]

            # Send command
            self._sendLine(b"STORE %d %s" % (size, name))

            # Send headers
            self._sendHeader("Database-Name", databaseName)
            self._sendHeader("File-Content-ID", contentID)
            self._sendHeader("File-Alias-ID", aliasID)

            if debugID is not None:
                self._sendHeader("Debug-ID", debugID)

            # Send blank line. Do not check for a response from the
            # server when no data will be sent. Otherwise
            # _checkError() might consume the "200" response which
            # is supposed to be read below in this method.
            self._sendLine(b"", check_for_error_responses=(size > 0))

            # Prepare to the upload the file
            md5_digester = hashlib.md5()
            sha1_digester = hashlib.sha1()
            sha256_digester = hashlib.sha256()
            bytesWritten = 0

            # Read in and upload the file 64kb at a time, by using the two-arg
            # form of iter (see
            # /usr/share/doc/python/html/library/functions.html#iter).
            for chunk in iter(lambda: file.read(1024 * 64), b""):
                self.state.f.write(chunk)
                bytesWritten += len(chunk)
                md5_digester.update(chunk)
                sha1_digester.update(chunk)
                sha256_digester.update(chunk)

            assert (
                bytesWritten == size
            ), "size is %d, but %d were read from the file" % (
                size,
                bytesWritten,
            )
            self.state.f.flush()

            # Read response
            response = six.ensure_str(
                self.state.f.readline().strip(), errors="replace"
            )
            if response != "200":
                raise UploadFailed("Server said: " + response)

            # Add rows to DB
            content = LibraryFileContent(
                id=contentID,
                filesize=size,
                sha256=sha256_digester.hexdigest(),
                sha1=sha1_digester.hexdigest(),
                md5=md5_digester.hexdigest(),
            )
            LibraryFileAlias(
                id=aliasID,
                content=content,
                filename=name.decode("UTF-8"),
                mimetype=contentType,
                expires=expires,
                restricted=self.restricted,
            )

            Store.of(content).flush()

            assert isinstance(aliasID, int), "aliasID %r not an integer" % (
                aliasID,
            )
            return aliasID
        except socket.timeout:
            timeout = config.librarian.client_socket_timeout
            raise UploadFailed("Server timed out after %s second(s)" % timeout)
        finally:
            self._close()

    def _getDatabaseName(self, store):
        return store.execute("SELECT current_database();").get_one()[0]

    def remoteAddFile(self, name, size, file, contentType, expires=None):
        """See `IFileUploadClient`."""
        if file is None:
            raise TypeError("No data")
        if size <= 0:
            raise UploadFailed("No data")
        name = six.ensure_binary(name)
        self._connect()
        try:
            database_name = ConnectionString(dbconfig.main_primary).dbname
            self._sendLine(b"STORE %d %s" % (size, name))
            self._sendHeader("Database-Name", database_name)
            self._sendHeader("Content-Type", str(contentType))
            if expires is not None:
                epoch = time.mktime(expires.utctimetuple())
                self._sendHeader("File-Expires", str(int(epoch)))

            # Send blank line
            self._sendLine(b"")

            # Prepare to the upload the file
            bytesWritten = 0

            # Read in and upload the file 64kb at a time, by using the two-arg
            # form of iter (see
            # /usr/share/doc/python/html/library/functions.html#iter).
            for chunk in iter(lambda: file.read(1024 * 64), b""):
                self.state.f.write(chunk)
                bytesWritten += len(chunk)

            assert (
                bytesWritten == size
            ), "size is %d, but %d were read from the file" % (
                size,
                bytesWritten,
            )
            self.state.f.flush()

            # Read response
            response = six.ensure_str(
                self.state.f.readline().strip(), errors="replace"
            )
            if not response.startswith("200"):
                raise UploadFailed(
                    "Could not upload %s. Server said: %s" % (name, response)
                )

            status, ids = response.split()
            contentID, aliasID = ids.split("/", 1)

            path = get_libraryfilealias_download_path(aliasID, name)
            return urljoin(self.download_url, path)
        finally:
            self._close()


class _File:
    """A File wrapper which uses the timeline and has security assertions."""

    def __init__(self, file, url):
        self.file = file
        self.url = url
        headers = file.info()
        chunked = headers.get("Transfer-Encoding") == "chunked"
        if not chunked and "Content-Length" in headers:
            try:
                self.length = int(headers["Content-Length"])
            except ValueError:
                self.length = None
            else:
                if self.length < 0:
                    self.length = None
        else:
            self.length = None

    def read(self, chunksize=None):
        request = get_current_browser_request()
        timeline = get_request_timeline(request)
        action = timeline.start("librarian-read", self.url)
        try:
            if chunksize is None:
                s = self.file.read()
            else:
                if self.length is not None:
                    chunksize = min(chunksize, self.length)
                s = self.file.read(chunksize)
            if self.length is not None:
                self.length -= len(s)
                # httplib doesn't quite do all the checking we need: in
                # particular, it won't fail on a short bounded-size read
                # from a non-chunked-transfer-coding resource.  Check this
                # manually.
                if not s and chunksize != 0 and self.length:
                    raise http.client.IncompleteRead(s, expected=self.length)
            return s
        finally:
            action.finish()

    def close(self):
        return self.file.close()


class FileDownloadClient:
    """A simple client to download files from the librarian"""

    # If anything is using this, it should be exposed as a public method
    # in the interface. Note that there is no need to contact the Librarian
    # to do this if you have a database connection available.
    #
    # def _findByDigest(self, hexdigest):
    #     """Return a list of relative paths to aliases"""
    #     host = config.librarian.download_host
    #     port = config.librarian.download_port
    #     url = ('http://%s:%d/search?digest=%s' % (
    #         host, port, hexdigest)
    #         )
    #     results = urlopen(url).read()
    #     lines = results.split('\n')
    #     count, paths = lines[0], lines[1:]
    #     if int(count) != len(paths):
    #         raise DownloadFailed('Incomplete response')
    #     return paths

    def _getAlias(self, aliasID, secure=False):
        """Retrieve the `LibraryFileAlias` with the given id.

        :param aliasID: A unique ID for the alias.
        :param secure: Controls the behaviour when looking up restricted
            files.  If False restricted files are only permitted when
            self.restricted is True.  See `getURLForAlias`.
        :returns: A `LibraryFileAlias`.
        :raises: `DownloadFailed` if the alias is invalid or
            inaccessible.
        """
        from lp.services.librarian.model import LibraryFileAlias

        try:
            lfa = LibraryFileAlias.get(aliasID)
        except SQLObjectNotFound:
            lfa = None

        if lfa is None:
            raise DownloadFailed("Alias %d not found" % aliasID)
        self._checkAliasAccess(lfa, secure=secure)

        return lfa

    def _checkAliasAccess(self, alias, secure=False):
        """Verify that `alias` can be accessed.

        :param alias: A `LibraryFileAlias`.
        :param secure: Controls the behaviour when looking up restricted
            files.  If False restricted files are only permitted when
            self.restricted is True.  See `getURLForAlias`.
        :raises: `DownloadFailed` if access is not allowed.
        """
        if not secure and alias.restricted != self.restricted:
            raise DownloadFailed(
                "Alias %d cannot be downloaded from this client." % alias.id
            )

    def _getPathForAlias(self, aliasID, secure=False):
        """Returns the path inside the librarian to talk about the given
        alias.

        :param aliasID: A unique ID for the alias
        :param secure: Controls the behaviour when looking up restricted
            files.  If False restricted files are only permitted when
            self.restricted is True.  See `getURLForAlias`.
        :returns: String path, url-escaped.  Unicode is UTF-8 encoded before
            url-escaping, as described in section 2.2.5 of RFC 2718.
            None if the file has been deleted.

        :raises: DownloadFailed if the alias is invalid
        """
        return self._getPathForAliasObject(
            self._getAlias(int(aliasID), secure=secure)
        )

    def _getPathForAliasObject(self, alias):
        """Returns the Librarian path for a `LibraryFileAlias`."""
        if alias.deleted:
            return None
        return get_libraryfilealias_download_path(
            alias.id, alias.filename.encode("utf-8")
        )

    def _getBaseURL(self, alias, secure=False):
        """Get the base URL to use for `alias`.

        :param secure: If true generate https urls on unique domains for
            security.
        """
        if not secure:
            return self.download_url

        # Secure url generation is the same for both restricted and
        # unrestricted files aliases : it is used to give web clients (not
        # appservers) a url to use to access a file which is either
        # restricted (and so they will also need a TimeLimitedToken) or
        # is suspected hostile (and so it should be isolated on its own
        # domain). Note that only the former is currently used in LP.
        # The algorithm is:
        # parse the url
        download_url = config.librarian.download_url
        parsed = list(urlparse(download_url))
        # Force the scheme to https
        parsed[0] = "https"
        # Insert the alias id (which is a unique key, thus unique) in the
        # netloc
        parsed[1] = ("i%d.restricted." % alias.id) + parsed[1]
        return urlunparse(parsed)

    def getURLForAlias(self, aliasID, secure=False):
        """Returns the url for talking to the librarian about the given
        alias.

        :param aliasID: A unique ID for the alias
        :param secure: If true generate https urls on unique domains for
            security.
        :returns: String URL, or None if the file has expired and been
            deleted.
        """
        alias = self._getAlias(aliasID, secure=secure)
        return self.getURLForAliasObject(alias, secure=secure)

    def getURLForAliasObject(self, alias, secure=False):
        """Return the download URL for a `LibraryFileAlias`.

        There is a separate `getURLForAlias` that takes an alias ID.  If
        you're not sure whether it's safe for the client to access your
        `alias`, use `getURLForAlias` which will retrieve its own copy.

        :param alias: A `LibraryFileAlias` whose URL you want.
        :param secure: If true generate https urls on unique domains for
            security.
        :returns: String URL, or None if the file has expired and been
            deleted.
        """
        # Note that the path is the same for both secure and insecure
        # URLs.  This is deliberate: the server doesn't need to know
        # about the original Host the client provides, and testing is
        # easier as we don't need wildcard https environments on dev
        # machines.
        self._checkAliasAccess(alias, secure=secure)
        base = self._getBaseURL(alias, secure=secure)
        path = self._getPathForAliasObject(alias)
        return compose_url(base, path)

    def _getURLForDownload(self, aliasID):
        """Returns the internal librarian URL for the alias.

        :param aliasID: A unique ID for the alias

        :returns: String URL, or None if the file has expired and been
            deleted.
        """
        return compose_url(
            self._internal_download_url, self._getPathForAlias(aliasID)
        )

    def getFileByAlias(
        self, aliasID, timeout=LIBRARIAN_SERVER_DEFAULT_TIMEOUT
    ):
        """See `IFileDownloadClient`."""
        url = self._getURLForDownload(aliasID)
        if url is None:
            # File has been deleted
            return None
        try_until = time.time() + timeout
        request = get_current_browser_request()
        timeline = get_request_timeline(request)
        action = timeline.start("librarian-connection", url)
        try:
            return self._connect_read(url, try_until, aliasID)
        finally:
            action.finish()

    def _connect_read(self, url, try_until, aliasID):
        """Helper for getFileByAlias."""
        while 1:
            try:
                return _File(urlopen(url), url)
            except URLError as error:
                # 404 errors indicate a data inconsistency: more than one
                # attempt to open the file is pointless.
                #
                # Note that URLError is a base class of HTTPError.
                if isinstance(error, HTTPError) and error.code == 404:
                    raise LookupError(aliasID)
                # HTTPErrors with a 5xx error code ("server problem")
                # are a reason to retry the access again, as well as
                # generic, non-HTTP, URLErrors like "connection refused".
                if (
                    isinstance(error, HTTPError)
                    and 500 <= error.code <= 599
                    or isinstance(error, URLError)
                    and not isinstance(error, HTTPError)
                ):
                    if time.time() <= try_until:
                        time.sleep(1)
                    else:
                        # There's a test (in
                        # lib/c/l/browser/tests/test_librarian.py) which
                        # simulates a librarian server error by raising this
                        # exception, so if you change the exception raised
                        # here, make sure you update the test.
                        raise LibrarianServerError(str(error))
                else:
                    raise


@implementer(ILibrarianClient)
class LibrarianClient(FileUploadClient, FileDownloadClient):
    """See `ILibrarianClient`."""

    restricted = False

    @property
    def upload_host(self):
        return config.librarian.upload_host

    @property
    def upload_port(self):
        return config.librarian.upload_port

    @property
    def download_url(self):
        return config.librarian.download_url

    @property
    def _internal_download_url(self):
        """Used by `_getURLForDownload`."""
        return "http://%s:%s/" % (
            config.librarian.download_host,
            config.librarian.download_port,
        )


@implementer(IRestrictedLibrarianClient)
class RestrictedLibrarianClient(LibrarianClient):
    """See `IRestrictedLibrarianClient`."""

    restricted = True

    @property
    def upload_host(self):
        return config.librarian.restricted_upload_host

    @property
    def upload_port(self):
        return config.librarian.restricted_upload_port

    @property
    def download_url(self):
        return config.librarian.restricted_download_url

    @property
    def _internal_download_url(self):
        """Used by `_getURLForDownload`."""
        return "http://%s:%s/" % (
            config.librarian.restricted_download_host,
            config.librarian.restricted_download_port,
        )
