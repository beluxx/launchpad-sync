# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import hashlib
import http.client
import io
import os
import re
import socket
import textwrap
import threading
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import transaction
from fixtures import EnvironmentVariable, TempDir
from testtools.testcase import ExpectedException

from lp.services.config import config
from lp.services.daemons.tachandler import TacTestSetup
from lp.services.database.interfaces import IStandbyStore
from lp.services.database.policy import StandbyDatabasePolicy
from lp.services.database.sqlbase import block_implicit_flushes
from lp.services.librarian import client as client_module
from lp.services.librarian.client import (
    LibrarianClient,
    LibrarianServerError,
    RestrictedLibrarianClient,
    _File,
)
from lp.services.librarian.interfaces.client import UploadFailed
from lp.services.librarian.model import LibraryFileAlias
from lp.services.propertycache import cachedproperty
from lp.services.timeout import override_timeout, with_timeout
from lp.testing import TestCase
from lp.testing.layers import (
    DatabaseLayer,
    FunctionalLayer,
    LaunchpadFunctionalLayer,
)
from lp.testing.views import create_webservice_error_view


class PropagatingThread(threading.Thread):
    """Thread class that propagates errors to the parent."""

    # https://stackoverflow.com/a/31614591
    def run(self):
        self.exc = None
        try:
            if hasattr(self, "_Thread__target"):
                # Thread uses name mangling prior to Python 3.
                self.ret = self._Thread__target(
                    *self._Thread__args, **self._Thread__kwargs
                )
            else:
                self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self):
        super().join()
        if self.exc:
            raise self.exc


class InstrumentedLibrarianClient(LibrarianClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.check_error_calls = 0

    sentDatabaseName = False

    def _sendHeader(self, name, value):
        if name == "Database-Name":
            self.sentDatabaseName = True
        return LibrarianClient._sendHeader(self, name, value)

    called_getURLForDownload = False

    def _getURLForDownload(self, aliasID):
        self.called_getURLForDownload = True
        return LibrarianClient._getURLForDownload(self, aliasID)

    def _checkError(self):
        self.check_error_calls += 1
        super()._checkError()


def make_mock_file(error, max_raise):
    """Return a surrogate for client._File.

    The surrogate function raises error when called for the first
    max_raise times.
    """

    file_status = {
        "error": error,
        "max_raise": max_raise,
        "num_calls": 0,
    }

    def mock_file(url_file, url):
        if file_status["num_calls"] < file_status["max_raise"]:
            file_status["num_calls"] += 1
            raise file_status["error"]
        return "This is a fake file object"

    return mock_file


class FakeServerTestSetup(TacTestSetup):
    def setUp(self):
        self.port = None
        super().setUp()

    def setUpRoot(self):
        pass

    @cachedproperty
    def root(self):
        return self.useFixture(TempDir()).path

    @property
    def tacfile(self):
        return os.path.join(os.path.dirname(__file__), "fakeserver.tac")

    @property
    def pidfile(self):
        return os.path.join(self.root, "fakeserver.pid")

    @property
    def logfile(self):
        return os.path.join(self.root, "fakeserver.log")

    def removeLog(self):
        pass

    def _hasDaemonStarted(self):
        if super()._hasDaemonStarted():
            with open(self.logfile) as logfile:
                self.port = int(
                    re.search(r"Site starting on (\d+)", logfile.read()).group(
                        1
                    )
                )
            return True
        else:
            return False


class LibrarianFileWrapperTestCase(TestCase):
    """Test behaviour of the _File wrapper used by the librarian client."""

    def makeFile(self, extra_content_length=None):
        extra_content_length_str = (
            str(extra_content_length)
            if extra_content_length is not None
            else None
        )
        self.useFixture(
            EnvironmentVariable(
                "LP_EXTRA_CONTENT_LENGTH", extra_content_length_str
            )
        )
        port = self.useFixture(FakeServerTestSetup()).port
        url = "http://localhost:%d/" % port
        return _File(urlopen(url), url)

    def test_unbounded_read_correct_length(self):
        file = self.makeFile()
        self.assertEqual(b"abcdef", file.read())
        self.assertEqual(b"", file.read())

    def test_unbounded_read_incorrect_length(self):
        file = self.makeFile(extra_content_length=1)
        with ExpectedException(http.client.IncompleteRead):
            # Python 3 notices the short response on the first read.
            self.assertEqual(b"abcdef", file.read())
            # Python 2 only notices the short response on the next read.
            file.read()

    def test_bounded_read_correct_length(self):
        file = self.makeFile()
        self.assertEqual(b"abcd", file.read(chunksize=4))
        self.assertEqual(b"ef", file.read(chunksize=4))
        self.assertEqual(b"", file.read(chunksize=4))

    def test_bounded_read_incorrect_length(self):
        file = self.makeFile(extra_content_length=1)
        self.assertEqual(b"abcd", file.read(chunksize=4))
        self.assertEqual(b"ef", file.read(chunksize=4))
        self.assertRaises(http.client.IncompleteRead, file.read, chunksize=4)


class EchoServer(threading.Thread):
    """Fake TCP server that only replies back the data sent to it.

    This is used to test librarian server early replies with error messages
    during the upload process.
    """

    def __init__(self):
        super().__init__()
        self.should_stop = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(1)
        self.socket.bind(("localhost", 0))
        self.socket.listen(1)
        self.connections = []

    def join(self, *args, **kwargs):
        self.should_stop = True
        super().join(*args, **kwargs)

    def run(self):
        while not self.should_stop:
            try:
                conn, addr = self.socket.accept()
                self.connections.append(conn)
                data = conn.recv(1024)
                conn.sendall(data)
            except socket.timeout:
                # We use the timeout to control how much time we will wait
                # to check again if self.should_stop was set, and the thread
                # will join.
                pass
        for conn in self.connections:
            conn.close()
        self.connections = []
        self.socket.close()


class TimingOutServer(EchoServer):
    """Fake TCP server that never sends a reply."""

    def run(self):
        while not self.should_stop:
            try:
                conn, addr = self.socket.accept()
                self.connections.append(conn)
            except socket.timeout:
                pass
        for conn in self.connections:
            conn.close()
        self.connections = []
        self.socket.close()


class LibrarianClientTestCase(TestCase):
    layer = LaunchpadFunctionalLayer

    def test_addFileSendsDatabaseName(self):
        # addFile should send the Database-Name header.
        client = InstrumentedLibrarianClient()
        client.addFile("sample.txt", 6, io.BytesIO(b"sample"), "text/plain")
        self.assertTrue(
            client.sentDatabaseName, "Database-Name header not sent by addFile"
        )

    def test_remoteAddFileDoesntSendDatabaseName(self):
        # remoteAddFile should send the Database-Name header as well.
        client = InstrumentedLibrarianClient()
        # Because the remoteAddFile call commits to the database in a
        # different process, we need to explicitly tell the DatabaseLayer to
        # fully tear down and set up the database.
        DatabaseLayer.force_dirty_database()
        client.remoteAddFile(
            "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
        )
        self.assertTrue(
            client.sentDatabaseName,
            "Database-Name header not sent by remoteAddFile",
        )

    def test_clientWrongDatabase(self):
        # If the client is using the wrong database, the server should refuse
        # the upload, causing LibrarianClient to raise UploadFailed.
        client = LibrarianClient()
        # Force the client to mis-report its database
        client._getDatabaseName = lambda cur: "wrong_database"
        try:
            client.addFile(
                "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
            )
        except UploadFailed as e:
            msg = e.args[0]
            self.assertTrue(
                msg.startswith("Server said: 400 Wrong database"),
                "Unexpected UploadFailed error: " + msg,
            )
        else:
            self.fail("UploadFailed not raised")

    def test_addFile_fails_when_server_returns_error_msg_on_socket(self):
        server = EchoServer()
        server.start()
        self.addCleanup(server.join)

        upload_host, upload_port = server.socket.getsockname()
        self.pushConfig(
            "librarian", upload_host=upload_host, upload_port=upload_port
        )

        client = LibrarianClient()
        # Artificially increases timeout to avoid race condition.
        # The fake server is running in another thread, and we are sure it
        # will (eventually) reply with an error message. So, let's just wait
        # until that message arrives.
        client.s_poll_timeout = 120

        # Please, note the mismatch between file size (7) and its actual size
        # of the content (6). This is intentional, to make sure we are raising
        # the error coming from the fake server (and not the local check
        # right after, while uploading the file).
        self.assertRaisesRegex(
            UploadFailed,
            "Server said early: STORE 7 sample.txt",
            client.addFile,
            "sample.txt",
            7,
            io.BytesIO(b"sample"),
            "text/plain",
        )

    def test_addFile_fails_when_server_times_out(self):
        server = TimingOutServer()
        server.start()
        self.addCleanup(server.join)

        upload_host, upload_port = server.socket.getsockname()
        self.pushConfig(
            "librarian",
            upload_host=upload_host,
            upload_port=upload_port,
            client_socket_timeout=1,
        )

        client = LibrarianClient()

        @with_timeout()
        def add_file():
            self.assertRaisesWithContent(
                UploadFailed,
                "Server timed out after 1 second",
                client.addFile,
                "sample.txt",
                6,
                io.BytesIO(b"sample"),
                "text/plain",
            )

        with override_timeout(3600):
            add_file()

    def test_addFile_uses_primary(self):
        # addFile is a write operation, so it should always use the
        # primary store, even if the standby is the default. Close the
        # standby store and try to add a file, verifying that the primary
        # is used.
        client = LibrarianClient()
        IStandbyStore(LibraryFileAlias).close()
        with StandbyDatabasePolicy():
            alias_id = client.addFile(
                "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
            )
        transaction.commit()
        f = client.getFileByAlias(alias_id)
        self.assertEqual(f.read(), b"sample")

    def test_addFile_no_response_check_at_end_headers_for_empty_file(self):
        # When addFile() sends the request header, it checks if the
        # server responded with an error response after sending each
        # header line. It does _not_ do this check when it sends the
        # empty line following the headers.
        client = InstrumentedLibrarianClient()
        client.addFile(
            "sample.txt",
            0,
            io.BytesIO(b""),
            "text/plain",
            allow_zero_length=True,
        )
        # addFile() calls _sendHeader() three times and _sendLine()
        # twice, but it does not check if the server responded
        # in the second call.
        self.assertEqual(4, client.check_error_calls)

    def test_addFile_response_check_at_end_headers_for_non_empty_file(self):
        # When addFile() sends the request header, it checks if the
        # server responded with an error response after sending each
        # header line. It does _not_ do this check when it sends the
        # empty line following the headers.
        client = InstrumentedLibrarianClient()
        client.addFile("sample.txt", 4, io.BytesIO(b"1234"), "text/plain")
        # addFile() calls _sendHeader() three times and _sendLine()
        # twice.
        self.assertEqual(5, client.check_error_calls)

    def test_addFile_hashes(self):
        # addFile() sets the MD5, SHA-1 and SHA-256 hashes on the
        # LibraryFileContent record.
        data = b"i am some data"
        md5 = hashlib.md5(data).hexdigest()
        sha1 = hashlib.sha1(data).hexdigest()
        sha256 = hashlib.sha256(data).hexdigest()

        client = LibrarianClient()
        lfa = LibraryFileAlias.get(
            client.addFile("file", len(data), io.BytesIO(data), "text/plain")
        )

        self.assertEqual(md5, lfa.content.md5)
        self.assertEqual(sha1, lfa.content.sha1)
        self.assertEqual(sha256, lfa.content.sha256)

    def test__getURLForDownload(self):
        # This protected method is used by getFileByAlias. It is supposed to
        # use the internal host and port rather than the external, proxied
        # host and port. This is to provide relief for our own issues with the
        # problems reported in bug 317482.
        #
        # (Set up:)
        client = LibrarianClient()
        alias_id = client.addFile(
            "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
        )
        config.push(
            "test config",
            textwrap.dedent(
                """\
                [librarian]
                download_host: example.org
                download_port: 1234
                """
            ),
        )
        try:
            # (Test:)
            # The LibrarianClient should use the download_host and
            # download_port.
            expected_host = "http://example.org:1234/"
            download_url = client._getURLForDownload(alias_id)
            self.assertTrue(
                download_url.startswith(expected_host),
                "expected %s to start with %s" % (download_url, expected_host),
            )
            # If the alias has been deleted, _getURLForDownload returns None.
            lfa = LibraryFileAlias.get(alias_id)
            lfa.content = None
            call = block_implicit_flushes(  # Prevent a ProgrammingError
                LibrarianClient._getURLForDownload
            )
            self.assertEqual(call(client, alias_id), None)
        finally:
            # (Tear down:)
            config.pop("test config")

    def test_restricted_getURLForDownload(self):
        # The RestrictedLibrarianClient should use the
        # restricted_download_host and restricted_download_port, but is
        # otherwise identical to the behaviour of the LibrarianClient discussed
        # and demonstrated above.
        #
        # (Set up:)
        client = RestrictedLibrarianClient()
        alias_id = client.addFile(
            "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
        )
        config.push(
            "test config",
            textwrap.dedent(
                """\
                [librarian]
                restricted_download_host: example.com
                restricted_download_port: 5678
                """
            ),
        )
        try:
            # (Test:)
            # The LibrarianClient should use the download_host and
            # download_port.
            expected_host = "http://example.com:5678/"
            download_url = client._getURLForDownload(alias_id)
            self.assertTrue(
                download_url.startswith(expected_host),
                "expected %s to start with %s" % (download_url, expected_host),
            )
            # If the alias has been deleted, _getURLForDownload returns None.
            lfa = LibraryFileAlias.get(alias_id)
            lfa.content = None
            call = block_implicit_flushes(  # Prevent a ProgrammingError
                RestrictedLibrarianClient._getURLForDownload
            )
            self.assertEqual(call(client, alias_id), None)
        finally:
            # (Tear down:)
            config.pop("test config")

    def test_getFileByAlias(self):
        # This method should use _getURLForDownload to download the file.
        # We use the InstrumentedLibrarianClient to show that it is consulted.
        #
        # (Set up:)
        client = InstrumentedLibrarianClient()
        alias_id = client.addFile(
            "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
        )
        transaction.commit()  # Make sure the file is in the "remote" database.
        self.assertFalse(client.called_getURLForDownload)
        # (Test:)
        f = client.getFileByAlias(alias_id)
        self.assertEqual(f.read(), b"sample")
        self.assertTrue(client.called_getURLForDownload)

    def test_getFileByAliasLookupError(self):
        # The Librarian server can return a 404 HTTPError;
        # LibrarienClient.getFileByAlias() returns a LookupError in
        # this case.
        _File = client_module._File
        client_module._File = make_mock_file(
            HTTPError("http://fake.url/", 404, "Forced error", None, None), 1
        )

        client = InstrumentedLibrarianClient()
        alias_id = client.addFile(
            "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
        )
        transaction.commit()
        self.assertRaises(LookupError, client.getFileByAlias, alias_id)

        client_module._File = _File

    def test_getFileByAliasLibrarianLongServerError(self):
        # The Librarian server can return a 500 HTTPError.
        # LibrarienClient.getFileByAlias() returns a LibrarianServerError
        # if the server returns this error for a longer time than given
        # by the parameter timeout.
        _File = client_module._File

        client_module._File = make_mock_file(
            HTTPError("http://fake.url/", 500, "Forced error", None, None), 2
        )
        client = InstrumentedLibrarianClient()
        alias_id = client.addFile(
            "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
        )
        transaction.commit()
        self.assertRaises(
            LibrarianServerError, client.getFileByAlias, alias_id, 1
        )

        client_module._File = make_mock_file(URLError("Connection refused"), 2)
        client = InstrumentedLibrarianClient()
        alias_id = client.addFile(
            "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
        )
        transaction.commit()
        self.assertRaises(
            LibrarianServerError, client.getFileByAlias, alias_id, 1
        )

        client_module._File = _File

    def test_getFileByAliasLibrarianShortServerError(self):
        # The Librarian server can return a 500 HTTPError;
        # LibrarienClient.getFileByAlias() returns a LibrarianServerError
        # in this case.
        _File = client_module._File

        client_module._File = make_mock_file(
            HTTPError("http://fake.url/", 500, "Forced error", None, None), 1
        )
        client = InstrumentedLibrarianClient()
        alias_id = client.addFile(
            "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
        )
        transaction.commit()
        self.assertEqual(
            client.getFileByAlias(alias_id), "This is a fake file object", 3
        )

        client_module._File = make_mock_file(URLError("Connection refused"), 1)
        client = InstrumentedLibrarianClient()
        alias_id = client.addFile(
            "sample.txt", 6, io.BytesIO(b"sample"), "text/plain"
        )
        transaction.commit()
        self.assertEqual(
            client.getFileByAlias(alias_id), "This is a fake file object", 3
        )

        client_module._File = _File

    def test_thread_state_FileUploadClient(self):
        client = InstrumentedLibrarianClient()
        th = PropagatingThread(
            target=client.addFile,
            args=("sample.txt", 6, io.BytesIO(b"sample"), "text/plain"),
        )
        th.start()
        th.join()
        self.assertEqual(5, client.check_error_calls)


class TestWebServiceErrors(unittest.TestCase):
    """Test that errors are correctly mapped to HTTP status codes."""

    layer = FunctionalLayer

    def test_LibrarianServerError_timeout(self):
        error_view = create_webservice_error_view(LibrarianServerError())
        self.assertEqual(http.client.REQUEST_TIMEOUT, error_view.status)
