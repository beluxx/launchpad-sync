# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test our mechanisms for locating which config file to use."""

__all__ = []

import os
import shutil
from tempfile import NamedTemporaryFile, mkdtemp

from lp.services import config
from lp.testing import TestCase


class TestConfigLookup(TestCase):
    def setUp(self):
        super().setUp()
        self.temp_lookup_file = None
        self.original_CONFIG_LOOKUP_FILES = config.CONFIG_LOOKUP_FILES
        self.original_LPCONFIG = os.environ["LPCONFIG"]

    def tearDown(self):
        del self.temp_lookup_file
        config.CONFIG_LOOKUP_FILES = self.original_CONFIG_LOOKUP_FILES
        os.environ["LPCONFIG"] = self.original_LPCONFIG
        super().tearDown()

    def makeLookupFile(self):
        self.temp_lookup_file = NamedTemporaryFile()
        self.temp_lookup_file.write(b"\nfrom_disk \n")
        self.temp_lookup_file.flush()
        config.CONFIG_LOOKUP_FILES = [
            NamedTemporaryFile().name,
            self.temp_lookup_file.name,
        ]

    def testByEnvironment(self):
        # Create the lookup file to demonstrate it is overridden.
        self.makeLookupFile()

        os.environ["LPCONFIG"] = "from_env"

        self.assertEqual(config.find_instance_name(), "from_env")

    def testByFile(self):
        # Create the lookup file.
        self.makeLookupFile()

        # Trash the environment variable so it doesn't override.
        del os.environ["LPCONFIG"]

        self.assertEqual(config.find_instance_name(), "from_disk")

    def testByDefault(self):
        # Trash the environment variable so it doesn't override.
        del os.environ["LPCONFIG"]

        self.assertEqual(config.find_instance_name(), config.DEFAULT_CONFIG)


class ConfigTestCase(TestCase):
    """Base test case that provides fixtures for testing configuration."""

    def setUpConfigRoots(self):
        """Create an alternate config roots."""
        if hasattr(self, "temp_config_root_dir"):
            return
        self.temp_config_root_dir = mkdtemp("configs")
        self.original_root_dirs = config.CONFIG_ROOT_DIRS
        config.CONFIG_ROOT_DIRS = [self.temp_config_root_dir]
        self.addCleanup(self.tearDownConfigRoots)

    def tearDownConfigRoots(self):
        """Remove the work down by setUpConfigRoots()."""
        shutil.rmtree(self.temp_config_root_dir)
        config.CONFIG_ROOT_DIRS = self.original_root_dirs

    def setUpInstanceConfig(self, instance_name):
        """Create an instance directory with empty config files.

        The path to the instance config directory is returned.
        """
        self.setUpConfigRoots()
        instance_config_dir = os.path.join(
            self.temp_config_root_dir, instance_name
        )
        os.mkdir(instance_config_dir)

        # Create an empty config file.
        open(
            os.path.join(instance_config_dir, "launchpad-lazr.conf"), "w"
        ).close()
        return instance_config_dir


class TestInstanceConfigDirLookup(ConfigTestCase):
    """Test where instance config directories are looked up."""

    def setUp(self):
        super().setUp()
        self.setUpConfigRoots()

    def test_find_config_dir_raises_ValueError(self):
        self.assertRaises(ValueError, config.find_config_dir, "no_instance")

    def test_find_config_dir(self):
        instance_config_dir = self.setUpInstanceConfig("an_instance")
        self.assertEqual(
            instance_config_dir, config.find_config_dir("an_instance")
        )

    def test_Config_uses_find_config_dir(self):
        instance_config_dir = self.setUpInstanceConfig("an_instance")
        # Create a very simple config file.
        cfg = config.LaunchpadConfig("an_instance")
        config_file = open(
            os.path.join(instance_config_dir, "launchpad-lazr.conf"), "w"
        )
        config_file.write("[launchpad]\ndefault_batch_size=2323")
        config_file.close()

        self.assertEqual(2323, cfg.launchpad.default_batch_size)
