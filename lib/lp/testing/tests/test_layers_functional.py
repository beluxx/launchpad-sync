# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

""" Test layers

Note that many tests are performed at run time in the layers themselves
to confirm that the environment hasn't been corrupted by tests
"""

import io
import os
import signal
from urllib.error import HTTPError
from urllib.request import urlopen

import amqp
from fixtures import (
    EnvironmentVariableFixture,
    Fixture,
    TestWithFixtures,
    )
import six
from zope.component import getUtility
from zope.interface.interfaces import ComponentLookupError

from lp.services.config import config
from lp.services.librarian.client import (
    LibrarianClient,
    UploadFailed,
    )
from lp.services.librarian.interfaces.client import ILibrarianClient
from lp.services.memcache.client import memcache_client_factory
from lp.services.pidfile import pidfile_path
from lp.testing import TestCase
from lp.testing.layers import (
    AppServerLayer,
    BaseLayer,
    DatabaseLayer,
    FunctionalLayer,
    LaunchpadFunctionalLayer,
    LaunchpadLayer,
    LaunchpadScriptLayer,
    LaunchpadTestSetup,
    LaunchpadZopelessLayer,
    LayerInvariantError,
    LayerIsolationError,
    LayerProcessController,
    LibrarianLayer,
    MemcachedLayer,
    RabbitMQLayer,
    ZopelessLayer,
    )


class BaseLayerIsolator(Fixture):
    """A fixture for isolating BaseLayer.

    This is useful to test interactions with LP_PERSISTENT_TEST_SERVICES
    which makes tests within layers unable to test that easily.
    """

    def __init__(self, with_persistent=False):
        """Create a BaseLayerIsolator.

        :param with_persistent: If True LP_PERSISTENT_TEST_SERVICES will
            be enabled during setUp.
        """
        super().__init__()
        self.with_persistent = with_persistent

    def _setUp(self):
        if self.with_persistent:
            env_value = ''
        else:
            env_value = None
        self.useFixture(EnvironmentVariableFixture(
            'LP_PERSISTENT_TEST_SERVICES', env_value))
        self.useFixture(EnvironmentVariableFixture('LP_TEST_INSTANCE'))


class LayerFixture(Fixture):
    """Adapt a layer to a fixture.

    Note that the layer setup/teardown are called, not the base class ones.

    :ivar layer: The adapted layer.
    """

    def __init__(self, layer):
        """Create a LayerFixture.

        :param layer: The layer to use.
        """
        super().__init__()
        self.layer = layer

    def _setUp(self):
        self.layer.setUp()
        self.addCleanup(self.layer.tearDown)


class TestBaseLayer(TestCase):

    def test_allocates_LP_TEST_INSTANCE(self):
        self.useFixture(BaseLayerIsolator())
        with LayerFixture(BaseLayer):
            pid, suffix = os.environ['LP_TEST_INSTANCE'].split('_', 1)
            self.assertEqual(str(os.getpid()), pid)
            self.assertEqual(24, len(suffix))
        self.assertEqual(None, os.environ.get('LP_TEST_INSTANCE'))

    def test_persist_test_services_disables_LP_TEST_INSTANCE(self):
        self.useFixture(BaseLayerIsolator(with_persistent=True))
        with LayerFixture(BaseLayer):
            self.assertEqual(None, os.environ.get('LP_TEST_INSTANCE'))
        self.assertEqual(None, os.environ.get('LP_TEST_INSTANCE'))

    def test_generates_unique_config(self):
        config.setInstance('testrunner')
        orig_instance = config.instance_name
        self.useFixture(
            EnvironmentVariableFixture('LP_PERSISTENT_TEST_SERVICES'))
        self.useFixture(EnvironmentVariableFixture('LP_TEST_INSTANCE'))
        self.useFixture(EnvironmentVariableFixture('LPCONFIG'))
        with LayerFixture(BaseLayer):
            self.assertEqual(
                'testrunner_%s' % os.environ['LP_TEST_INSTANCE'],
                config.instance_name)
        self.assertEqual(orig_instance, config.instance_name)

    def test_generates_unique_config_dirs(self):
        self.useFixture(
            EnvironmentVariableFixture('LP_PERSISTENT_TEST_SERVICES'))
        self.useFixture(EnvironmentVariableFixture('LP_TEST_INSTANCE'))
        self.useFixture(EnvironmentVariableFixture('LPCONFIG'))
        with LayerFixture(BaseLayer):
            runner_root = 'configs/%s' % config.instance_name
            runner_appserver_root = 'configs/testrunner-appserver_%s' % \
                os.environ['LP_TEST_INSTANCE']
            self.assertTrue(os.path.isfile(
                runner_root + '/launchpad-lazr.conf'))
            self.assertTrue(os.path.isfile(
                runner_appserver_root + '/launchpad-lazr.conf'))
        self.assertFalse(os.path.exists(runner_root))
        self.assertFalse(os.path.exists(runner_appserver_root))


class BaseTestCase(TestCase):
    """Both the Base layer tests, as well as the base Test Case
    for all the other Layer tests.
    """
    layer = BaseLayer

    # These flags will be overridden in subclasses to describe the
    # environment they expect to have available.
    want_component_architecture = False
    want_librarian_running = False
    want_launchpad_database = False
    want_functional_flag = False
    want_zopeless_flag = False
    want_memcached = False
    want_rabbitmq = False

    def testBaseIsSetUpFlag(self):
        self.assertEqual(BaseLayer.isSetUp, True)

    def testFunctionalIsSetUp(self):
        self.assertEqual(FunctionalLayer.isSetUp, self.want_functional_flag)

    def testZopelessIsSetUp(self):
        self.assertEqual(ZopelessLayer.isSetUp, self.want_zopeless_flag)

    def testComponentArchitecture(self):
        try:
            getUtility(ILibrarianClient)
        except ComponentLookupError:
            self.assertFalse(
                    self.want_component_architecture,
                    'Component Architecture should be available.'
                    )
        else:
            self.assertTrue(
                    self.want_component_architecture,
                    'Component Architecture should not be available.'
                    )

    def testLibrarianRunning(self):
        # Check that the librarian is running. Note that even if the
        # librarian is running, it may not be able to actually store
        # or retrieve files if, for example, the Launchpad database is
        # not currently available.
        try:
            urlopen(config.librarian.download_url).read()
            self.assertTrue(
                    self.want_librarian_running,
                    'Librarian should not be running.'
                    )
        except OSError:
            self.assertFalse(
                    self.want_librarian_running,
                    'Librarian should be running.'
                    )

    def testLibrarianWorking(self):
        # Check that the librian is actually working. This means at
        # a minimum the Librarian service is running and is connected
        # to the Launchpad database.
        want_librarian_working = (
                self.want_librarian_running and self.want_launchpad_database
                and self.want_component_architecture
                )
        client = LibrarianClient()
        data = b'Whatever'
        try:
            client.addFile(
                    'foo.txt', len(data), io.BytesIO(data), 'text/plain'
                    )
        except UploadFailed:
            self.assertFalse(
                    want_librarian_working,
                    'Librarian should be fully operational'
                    )
        # Since we use IMasterStore that doesn't throw either AttributeError
        # or ComponentLookupError.
        except TypeError:
            self.assertFalse(
                    want_librarian_working,
                    'Librarian not operational as component architecture '
                    'not loaded'
                    )
        else:
            self.assertTrue(
                    want_librarian_working,
                    'Librarian should not be operational'
                    )

    def testLaunchpadDbAvailable(self):
        if not self.want_launchpad_database:
            self.assertEqual(None, DatabaseLayer._db_fixture)
            return
        con = DatabaseLayer.connect()
        cur = con.cursor()
        cur.execute("SELECT id FROM Person LIMIT 1")
        self.assertNotEqual(None, cur.fetchone())

    def xxxtestMemcachedWorking(self):
        # XXX sinzui 2011-12-27 bug=729062: Disabled because lucid_db_lp
        # reports memcached did not die.(self):
        client = MemcachedLayer.client or memcache_client_factory()
        key = "BaseTestCase.testMemcachedWorking"
        is_live = client.set(key, "live")
        if self.want_memcached:
            self.assertEqual(
                is_live, True, "memcached not live when it should be.")
        else:
            self.assertEqual(
                is_live, False, "memcached is live but should not be.")

    def testRabbitWorking(self):
        rabbitmq = config.rabbitmq
        if not self.want_rabbitmq:
            self.assertEqual(None, rabbitmq.host)
        else:
            self.assertNotEqual(None, rabbitmq.host)
            conn = amqp.Connection(
                host=rabbitmq.host,
                userid=rabbitmq.userid,
                password=rabbitmq.password,
                virtual_host=rabbitmq.virtual_host)
            conn.connect()
            conn.close()


class MemcachedTestCase(BaseTestCase):
    layer = MemcachedLayer
    want_memcached = True


class LibrarianTestCase(BaseTestCase):
    layer = LibrarianLayer

    want_launchpad_database = True
    want_librarian_running = True

    def testUploadsSucceed(self):
        # This layer is able to be used on its own as it depends on
        # DatabaseLayer.
        # We can test this using remoteAddFile (it does not need the CA
        # loaded)
        client = LibrarianClient()
        data = b'This is a test'
        client.remoteAddFile(
            'foo.txt', len(data), io.BytesIO(data), 'text/plain')


class LibrarianLayerTest(TestCase, TestWithFixtures):

    def test_makes_unique_instance(self):
        # Capture the original settings
        default_root = config.librarian_server.root
        download_port = config.librarian.download_port
        restricted_download_port = config.librarian.restricted_download_port
        self.useFixture(BaseLayerIsolator())
        with LayerFixture(BaseLayer), LayerFixture(DatabaseLayer):
            with LayerFixture(LibrarianLayer):
                active_root = config.librarian_server.root
                # The config settings have changed:
                self.assertNotEqual(default_root, active_root)
                self.assertNotEqual(
                    download_port, config.librarian.download_port)
                self.assertNotEqual(
                    restricted_download_port,
                    config.librarian.restricted_download_port)
                self.assertTrue(os.path.exists(active_root))
            # This needs more sophistication in the config system (tearDown on
            # the layer needs to pop the config fragment off of disk - and
            # perhaps notify other processes that its done this. So for now we
            # leave the new config in place).
            # self.assertEqual(default_root, config.librarian_server.root)
            # The working dir has to have been deleted.
            self.assertFalse(os.path.exists(active_root))


class LibrarianResetTestCase(TestCase):
    """Our page tests need to run multple tests without destroying
    the librarian database in between.
    """
    layer = LibrarianLayer

    sample_data = b'This is a test'

    def test_librarian_is_reset(self):
        # Add a file. We use remoteAddFile because it does not need the CA
        # loaded to work.
        client = LibrarianClient()
        LibrarianTestCase.url = client.remoteAddFile(
            six.ensure_str(self.sample_data), len(self.sample_data),
            io.BytesIO(self.sample_data), 'text/plain'
            )
        self.assertEqual(
            urlopen(LibrarianTestCase.url).read(), self.sample_data
            )
        # Perform the librarian specific between-test code:
        LibrarianLayer.testTearDown()
        LibrarianLayer.testSetUp()
        # Which should have nuked the old file.
        self.assertRaises(HTTPError, urlopen, LibrarianTestCase.url)


class LibrarianHideTestCase(TestCase):
    layer = LaunchpadLayer

    def testHideLibrarian(self):
        # First perform a successful upload:
        client = LibrarianClient()
        data = b'foo'
        client.remoteAddFile(
            'foo', len(data), io.BytesIO(data), 'text/plain')
        # The database was committed to, but not by this process, so we need
        # to ensure that it is fully torn down and recreated.
        DatabaseLayer.force_dirty_database()

        # Hide the librarian, and show that the upload fails:
        LibrarianLayer.hide()
        self.assertRaises(UploadFailed, client.remoteAddFile,
                          b'foo', len(data), io.BytesIO(data), 'text/plain')

        # Reveal the librarian again, allowing uploads:
        LibrarianLayer.reveal()
        client.remoteAddFile(
            b'foo', len(data), io.BytesIO(data), 'text/plain')


class RabbitMQTestCase(BaseTestCase):
    layer = RabbitMQLayer
    want_rabbitmq = True


class DatabaseTestCase(BaseTestCase):
    layer = DatabaseLayer

    want_launchpad_database = True

    def testConnect(self):
        DatabaseLayer.connect()

    def getWikinameCount(self, con):
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM Wikiname")
        num = cur.fetchone()[0]
        return num

    def test_db_is_reset(self):
        con = DatabaseLayer.connect()
        cur = con.cursor()
        cur.execute("DELETE FROM Wikiname")
        self.assertEqual(self.getWikinameCount(con), 0)
        con.commit()
        # Run the per-test code for the Database layer.
        DatabaseLayer.testTearDown()
        DatabaseLayer.testSetUp()
        # Wikiname table should have been restored.
        con = DatabaseLayer.connect()
        self.assertNotEqual(0, self.getWikinameCount(con))


class LaunchpadTestCase(BaseTestCase):
    layer = LaunchpadLayer

    want_launchpad_database = True
    want_librarian_running = True
    want_memcached = True
    want_rabbitmq = True


class FunctionalTestCase(BaseTestCase):
    layer = FunctionalLayer

    want_component_architecture = True
    want_functional_flag = True


class ZopelessTestCase(BaseTestCase):
    layer = ZopelessLayer

    want_component_architecture = True
    want_launchpad_database = False
    want_librarian_running = False
    want_zopeless_flag = True


class LaunchpadFunctionalTestCase(BaseTestCase):
    layer = LaunchpadFunctionalLayer

    want_component_architecture = True
    want_launchpad_database = True
    want_librarian_running = True
    want_functional_flag = True
    want_memcached = True
    want_rabbitmq = True


class LaunchpadZopelessTestCase(BaseTestCase):
    layer = LaunchpadZopelessLayer

    want_component_architecture = True
    want_launchpad_database = True
    want_librarian_running = True
    want_zopeless_flag = True
    want_memcached = True
    want_rabbitmq = True


class LaunchpadScriptTestCase(BaseTestCase):
    layer = LaunchpadScriptLayer

    want_component_architecture = True
    want_launchpad_database = True
    want_librarian_running = True
    want_zopeless_flag = True
    want_memcached = True
    want_rabbitmq = True


class LayerProcessControllerInvariantsTestCase(BaseTestCase):
    layer = AppServerLayer

    want_component_architecture = True
    want_launchpad_database = True
    want_librarian_running = True
    want_functional_flag = True
    want_zopeless_flag = False
    want_memcached = True
    want_rabbitmq = True

    def testAppServerIsAvailable(self):
        # Test that the app server is up and running.
        mainsite = LayerProcessController.appserver_config.vhost.mainsite
        home_page = six.ensure_text(urlopen(mainsite.rooturl).read())
        self.assertIn(
            'Is your project registered yet?', home_page,
            "Home page couldn't be retrieved:\n%s" % home_page)

    def testStartingAppServerTwiceRaisesInvariantError(self):
        # Starting the appserver twice should raise an exception.
        self.assertRaises(LayerInvariantError,
                          LayerProcessController.startAppServer)


class LayerProcessControllerTestCase(TestCase):
    """Tests for the `LayerProcessController`."""
    # We need the database to be set up, no more.
    layer = DatabaseLayer

    def tearDown(self):
        super().tearDown()
        # Stop the app server.  It's okay if it isn't running.
        LayerProcessController.stopAppServer()

    def test_stopAppServer(self):
        # Test that stopping the app server kills the process and remove the
        # PID file.
        LayerProcessController.setConfig()
        LayerProcessController.startAppServer()
        pid = LayerProcessController.appserver.pid
        pid_file = pidfile_path('launchpad',
                                LayerProcessController.appserver_config)
        LayerProcessController.stopAppServer()
        self.assertRaises(OSError, os.kill, pid, 0)
        self.assertFalse(os.path.exists(pid_file), "PID file wasn't removed")
        self.assertIsNone(
            LayerProcessController.appserver,
            "appserver class attribute wasn't reset")

    def test_postTestInvariants(self):
        # A LayerIsolationError should be raised if the app server dies in the
        # middle of a test.
        LayerProcessController.setConfig()
        LayerProcessController.startAppServer()
        pid = LayerProcessController.appserver.pid
        os.kill(pid, signal.SIGTERM)
        LayerProcessController.appserver.wait()
        self.assertRaises(LayerIsolationError,
                          LayerProcessController.postTestInvariants)

    def test_postTestInvariants_dbIsReset(self):
        # The database should be reset by the test invariants.
        LayerProcessController.setConfig()
        LayerProcessController.startAppServer()
        LayerProcessController.postTestInvariants()
        # XXX: Robert Collins 2010-10-17 bug=661967 - this isn't a reset, its
        # a flag that it *needs* a reset, which is actually quite different;
        # the lack of a teardown will leak databases.
        self.assertEqual(True, LaunchpadTestSetup()._reset_db)


class TestNameTestCase(TestCase):
    layer = BaseLayer

    def testTestName(self):
        self.assertEqual(
            BaseLayer.test_name,
            "lp.testing.tests.test_layers_functional.TestNameTestCase."
            "testTestName")
