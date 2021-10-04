# Copyright 2009-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for runlaunchpad.py"""

__all__ = [
    'CommandLineArgumentProcessing',
    'ServersToStart',
    ]

import shutil
import tempfile

from lp.scripts.runlaunchpad import (
    get_services_to_run,
    process_config_arguments,
    SERVICES,
    split_out_runlaunchpad_arguments,
    )
import lp.services.config
from lp.services.config import config
from lp.testing import TestCase


class CommandLineArgumentProcessing(TestCase):
    """runlaunchpad.py's command line arguments fall into two parts. The first
    part specifies which services to run, then second part is passed directly
    on to the Zope webserver start up.
    """

    def test_no_parameter(self):
        """Given no arguments, return no services and no Zope arguments."""
        self.assertEqual(([], []), split_out_runlaunchpad_arguments([]))

    def test_run_options(self):
        """Services to run are specified with an optional `-r` option.

        If a service is specified, it should appear as the first value in the
        returned tuple.
        """
        self.assertEqual(
            (['foo'], []), split_out_runlaunchpad_arguments(['-r', 'foo']))

    def test_run_lots_of_things(self):
        """The `-r` option can be used to specify multiple services.

        Multiple services are separated with commas. e.g. `-r foo,bar`.
        """
        self.assertEqual(
            (['foo', 'bar'], []),
            split_out_runlaunchpad_arguments(['-r', 'foo,bar']))

    def test_run_with_zope_params(self):
        """Any arguments after the initial `-r` option should be passed
        straight through to Zope.
        """
        self.assertEqual(
            (['foo', 'bar'], ['-o', 'foo', '--bar=baz']),
            split_out_runlaunchpad_arguments(['-r', 'foo,bar', '-o', 'foo',
                                              '--bar=baz']))

    def test_run_with_only_zope_params(self):
        """Pass all the options to zope when the `-r` option is not given."""
        self.assertEqual(
            ([], ['-o', 'foo', '--bar=baz']),
            split_out_runlaunchpad_arguments(['-o', 'foo', '--bar=baz']))


class TestDefaultConfigArgument(TestCase):
    """Tests for the processing of config arguments."""

    def setUp(self):
        super(TestDefaultConfigArgument, self).setUp()
        self.config_root = tempfile.mkdtemp('configs')
        self.saved_instance = config.instance_name
        self.saved_config_roots = lp.services.config.CONFIG_ROOT_DIRS
        lp.services.config.CONFIG_ROOT_DIRS = [self.config_root]
        self.addCleanup(self.cleanUp)

    def cleanUp(self):
        shutil.rmtree(self.config_root)
        lp.services.config.CONFIG_ROOT_DIRS = self.saved_config_roots
        config.setInstance(self.saved_instance)

    def test_i_sets_the_instance(self):
        """The -i parameter will set the config instance name."""
        self.assertEqual(
            ['-o', 'foo'],
            process_config_arguments(['-i', 'test', '-o', 'foo']))
        self.assertEqual('test', config.instance_name)


class ServersToStart(TestCase):
    """Test server startup control."""

    def setUp(self):
        """Make sure that only the Librarian is configured to launch."""
        super(ServersToStart, self).setUp()
        launch_data = """
            [librarian_server]
            launch: True
            [codehosting]
            launch: False
            [launchpad]
            launch: False
            """
        config.push('launch_data', launch_data)
        self.addCleanup(config.pop, 'launch_data')

    def test_nothing_explicitly_requested(self):
        """Implicitly start services based on the config.*.launch property.
        """
        services = get_services_to_run([])
        expected = [SERVICES['librarian']]

        # The search test services may or may not be asked to run.
        if config.bing_test_service.launch:
            expected.append(SERVICES['bing-webservice'])

        # RabbitMQ may or may not be asked to run.
        if config.rabbitmq.launch:
            expected.append(SERVICES['rabbitmq'])

        self.assertContentEqual(expected, services)

    def test_explicit_request_overrides(self):
        """Only start those services which are explicitly requested,
        ignoring the configuration properties.
        """
        services = get_services_to_run(['sftp'])
        self.assertEqual([SERVICES['sftp']], services)

    def test_launchpad_systems_red(self):
        self.assertFalse(config.launchpad.launch)
