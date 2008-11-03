# Copyright 2006 Canonical Ltd.  All rights reserved.
"""ftpmaster facilities tests."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces.component import IComponentSet
from canonical.launchpad.interfaces.distribution import IDistributionSet
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.publishing import (
    PackagePublishingPocket, PackagePublishingPriority,
    PackagePublishingStatus)
from canonical.launchpad.interfaces.section import ISectionSet
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.changeoverride import (
    ChangeOverride, ArchiveOverriderError)
from canonical.launchpad.scripts.ftpmasterbase import SoyuzScriptError
from canonical.launchpad.tests.test_publishing import SoyuzTestPublisher
from canonical.testing import LaunchpadZopelessLayer


class LocalLogger(FakeLogger):
    """Local log facility """

    def __init__(self):
        self.logs = []

    def read(self):
        """Return printable log contents and reset current log."""
        content = "\n".join(self.logs)
        self.logs = []
        return content

    def message(self, prefix, *stuff, **kw):
        self.logs.append("%s %s" % (prefix, ' '.join(stuff)))


class TestChangeOverride(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """ """
        self.ubuntu = getUtility(IDistributionSet)['ubuntu']
        self.warty = self.ubuntu.getSeries('warty')
        self.warty_i386 = self.warty['i386']
        self.warty_hppa = self.warty['hppa']

        fake_chroot = getUtility(ILibraryFileAliasSet)[1]
        self.warty_i386.addOrUpdateChroot(fake_chroot)
        self.warty_hppa.addOrUpdateChroot(fake_chroot)

        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.person = getUtility(
            IPersonSet).getByName("name16")

    def getChanger(self, package_name='mozilla-firefox', package_version=None,
                   distribution='ubuntu', suite='warty',
                   arch_tag=None, component=None, section=None, priority=None,
                   source_and_binary=False, binary_and_source=False,
                   source_only=False, confirm_all=True):
        """Return a PackageCopier instance.

        Allow tests to use a set of default options to ChangeOverride.
        """
        test_args = [
            '-s', suite,
            '-d', distribution,
            ]

        if confirm_all:
            test_args.append('-y')

        if source_and_binary:
            test_args.append('-S')

        if binary_and_source:
            test_args.append('-B')

        if source_only:
            test_args.append('-t')

        if package_version is not None:
            test_args.extend(['-e', package_version])

        if arch_tag is not None:
            test_args.extend(['-a', arch_tag])

        if component is not None:
            test_args.extend(['-c', component])

        if section is not None:
            test_args.extend(['-x', section])

        if priority is not None:
            test_args.extend(['-p', priority])

        test_args.extend(package_name.split())

        changer = ChangeOverride(
            name='change-override', test_args=test_args)
        changer.logger = LocalLogger()
        changer.setupLocation()
        return changer

    def test_changeoveride_initialize(self):
        """ChangeOverride initialization process.

        Check if the correct attributes are built after initialization.
        """
        changer = self.getChanger(
            component="main", section="base", priority="extra")

        # Processed location inherited from SoyuzScript.
        self.assertEqual(
            self.ubuntu, changer.location.distribution)
        self.assertEqual(
            self.warty, changer.location.distroseries)
        self.assertEqual(
            PackagePublishingPocket.RELEASE, changer.location.pocket)

        # Resolved override values.
        self.assertEqual(
            getUtility(IComponentSet)['main'], changer.component)
        self.assertEqual(
            getUtility(ISectionSet)['base'], changer.section)
        self.assertEqual(
            PackagePublishingPriority.EXTRA, changer.priority)


    def patchedChanger(self, source_only=False, source_and_binary=False,
                       binary_and_source=False, package_name='foo'):
        """Return a patched `ChangeOverride` object.

        All operations are modified to allow test tracing.
        """
        changer = self.getChanger(
            component="main", section="base", priority="extra",
            source_only=source_only, source_and_binary=source_and_binary,
            binary_and_source=binary_and_source, package_name=package_name)

        # Patched override operations.
        def fakeProcessSourceChange(name):
            changer.logger.info("Source change for '%s'" % name)

        def fakeProcessBinaryChange(name):
            changer.logger.info("Binary change for '%s'" % name)

        def fakeProcessChildrenChange(name):
            changer.logger.info("Children change for '%s'" % name)

        # Patch the override operations.
        changer.processSourceChange = fakeProcessSourceChange
        changer.processBinaryChange = fakeProcessBinaryChange
        changer.processChildrenChange = fakeProcessChildrenChange

        # Consume the initializaton logging.
        changer.logger.read()

        return changer

    def test_changeoverride_mode(self):
        """Check `ChangeOverride` mode.

        Confirm the expected behaviour of the change-override modes:

         * Binary-only: default mode, only override binaries exactly matching
              the given name;
         * Source-only: activated via '-t', override only the matching source;
         * Binary-and-source: activated via '-B', override source and binaries
              exactly matching the given name.
         * Source-and-binaries: activated via '-S', override the source
              matching the given name and the binaries built from it.
        """
        changer = self.patchedChanger()
        changer.mainTask()
        self.assertEqual(
            changer.logger.read(),
            "INFO Binary change for 'foo'")

        changer = self.patchedChanger(source_only=True)
        changer.mainTask()
        self.assertEqual(
            changer.logger.read(),
            "INFO Source change for 'foo'")

        changer = self.patchedChanger(binary_and_source=True)
        changer.mainTask()
        self.assertEqual(
            changer.logger.read(),
            "INFO Source change for 'foo'\n"
            "INFO Binary change for 'foo'")

        changer = self.patchedChanger(source_and_binary=True)
        changer.mainTask()
        self.assertEqual(
            changer.logger.read(),
            "INFO Source change for 'foo'\n"
            "INFO Children change for 'foo'")

    def test_changeoverride_multiple_targets(self):
        """`ChangeOverride` can operate on multiple targets.

        It will perform the defined operation for all given command-line
        arguments.
        """
        changer = self.patchedChanger(package_name='foo bar baz')
        changer.mainTask()
        self.assertEqual(
            changer.logger.read(),
            "INFO Binary change for 'foo'\n"
            "INFO Binary change for 'bar'\n"
            "INFO Binary change for 'baz'")

    def assertCurrentBinary(self, distroarchseries, name, version,
                            component_name, section_name, priority_name):
        """Assert if the current binary publication matches the given data."""
        dasbpr = distroarchseries.getBinaryPackage(name)[version]
        pub = dasbpr.current_publishing_record
        self.assertTrue(pub.status.name in ['PUBLISHED', 'PENDING'])
        self.assertEqual(pub.component.name, component_name)
        self.assertEqual(pub.section.name, section_name)
        self.assertEqual(pub.priority.name, priority_name)

    def assertCurrentSource(self, distroseries, name, version,
                            component_name, section_name):
        """Assert if the current source publication matches the given data."""
        dsspr = distroseries.getSourcePackage(name)[version]
        pub = dsspr.current_published
        self.assertTrue(pub.status.name in ['PUBLISHED', 'PENDING'])
        self.assertEqual(pub.component.name, component_name)
        self.assertEqual(pub.section.name, section_name)

    def _setupOverridePublishingContext(self):
        """Setup publishing context.

        'boingo' source and 'boingo-bin' binaries in warty (i386 & hppa).
        """
        source = self.test_publisher.getPubSource(
            sourcename="boingo", version='1.0', distroseries=self.warty)
        binaries = self.test_publisher.getPubBinaries(
            'boingo-bin', pub_source=source, distroseries=self.warty)

    def test_changeoverride_operations(self):
        """Check if `IArchivePublisher.changeOverride` is wrapped correctly.

        `ChangeOverride` allow three types of override operations:

         * Source-only overrides: `processSourceChange`;
         * Binary-only overrides: `processBinaryChange`;
         * Source-children overrides: `processChildrenChange`;

        This test check the expected behaviour for each of them.
        """
        self._setupOverridePublishingContext()

        changer = self.getChanger(
            component="universe", section="web", priority='extra')
        self.assertEqual(
            changer.logger.read(),
            "INFO Override Component to: 'universe'\n"
            "INFO Override Section to: 'web'\n"
            "INFO Override Priority to: 'EXTRA'")

        # Override the source.
        changer.processSourceChange('boingo')
        self.assertEqual(
            changer.logger.read(),
            "INFO 'boingo - 1.0/main/base' source overridden")
        self.assertCurrentSource(
            self.warty, 'boingo', '1.0', 'universe', 'web')

        # Override the binaries.
        changer.processBinaryChange('boingo-bin')
        self.assertEqual(
            changer.logger.read(),
            "INFO 'boingo-bin-1.0/main/base/STANDARD' binary "
                "overridden in warty/hppa\n"
            "INFO 'boingo-bin-1.0/main/base/STANDARD' binary "
                "overridden in warty/i386")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-bin', '1.0', 'universe', 'web', 'EXTRA')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-bin', '1.0', 'universe', 'web', 'EXTRA')

        # Override the source children.
        changer.processChildrenChange('boingo')
        self.assertEqual(
            changer.logger.read(),
            "INFO 'boingo-bin-1.0/universe/web/EXTRA' remained the same\n"
            "INFO 'boingo-bin-1.0/universe/web/EXTRA' remained the same")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-bin', '1.0', 'universe', 'web', 'EXTRA')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-bin', '1.0', 'universe', 'web', 'EXTRA')

    def test_changeoverride_no_change(self):
        """Override source and/or binary already in the desired state.

        Nothing is done and the event is logged.
        """
        self._setupOverridePublishingContext()

        changer = self.getChanger(
            suite="warty", component="main", section="base",
            priority='standard')

        self.assertEqual(
            changer.logger.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'base'\n"
            "INFO Override Priority to: 'STANDARD'")

        changer.processSourceChange('boingo')
        self.assertEqual(
            changer.logger.read(),
            "INFO 'boingo - 1.0/main/base' remained the same")

        self.assertCurrentSource(
            self.warty, 'boingo', '1.0', 'main', 'base')

        changer.processBinaryChange('boingo-bin')
        self.assertEqual(
            changer.logger.read(),
            "INFO 'boingo-bin-1.0/main/base/STANDARD' remained the same\n"
            "INFO 'boingo-bin-1.0/main/base/STANDARD' remained the same")

        self.assertCurrentBinary(
            self.warty_i386, 'boingo-bin', '1.0', 'main', 'base', 'STANDARD')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-bin', '1.0', 'main', 'base', 'STANDARD')

    def test_overrides_with_changed_archive(self):
        """Overrides resulting in archive changes are not allowed.

        Changing the component to 'partner' will result in the archive
        changing on the publishing record.
        """
        self._setupOverridePublishingContext()

        changer = self.getChanger(
            component="partner", section="base", priority="extra")

        self.assertRaises(
            ArchiveOverriderError, changer.processSourceChange, 'boingo')
        self.assertRaises(
            ArchiveOverriderError, changer.processBinaryChange, 'boingo-bin')
        self.assertRaises(
            ArchiveOverriderError, changer.processChildrenChange, 'boingo')

    def test_target_publication_not_found(self):
        """Raises SoyuzScriptError when a source was not found."""
        changer = self.getChanger(
            component="main", section="base", priority="extra")

        self.assertRaises(
            SoyuzScriptError, changer.processSourceChange, 'foobar')
        self.assertRaises(
            SoyuzScriptError, changer.processBinaryChange, 'biscuit')
        self.assertRaises(
            SoyuzScriptError, changer.processChildrenChange, 'cookie')

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
