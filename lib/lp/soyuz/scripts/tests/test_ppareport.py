# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Tests for `PPAReportScript.` """

__metaclass__ = type

import os
from StringIO import StringIO
import shutil
import tempfile
import unittest

from canonical.config import config
from canonical.launchpad.scripts import BufferLogger
from canonical.testing import LaunchpadZopelessLayer
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.soyuz.scripts.ppareport import PPAReportScript


class TestPPAReport(unittest.TestCase):
    """Test the PPAReportScript class."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Reset the PPA repository root."""
        ppa_root = config.personalpackagearchive.root
        if os.path.exists(ppa_root):
            shutil.rmtree(ppa_root)
        os.makedirs(ppa_root)

    def getReporter(self, ppa_owner=None, gen_over_quota=False,
                    gen_user_emails=False, gen_orphan_repos=False,
                    gen_missing_repos=False, output=None,
                    quota_threshould=None):
        """Return a `PPAReportScript` instance.

        When the 'output' command-line options is not set it overrides the
        script setup to store output in a `StringIO` object so it can be
        verified later.
        """
        test_args = []

        if ppa_owner is not None:
            test_args.extend(['-p', ppa_owner])

        if output is not None:
            test_args.extend(['-o', output])

        if quota_threshould is not None:
            test_args.extend(['-t', quota_threshould])

        if gen_over_quota:
            test_args.append('--gen-over-quota')

        if gen_user_emails:
            test_args.append('--gen-user-emails')

        if gen_orphan_repos:
            test_args.append('--gen-orphan-repos')

        if gen_missing_repos:
            test_args.append('--gen-missing-repos')

        reporter = PPAReportScript(name='ppa-report', test_args=test_args)
        reporter.logger = BufferLogger()

        # Override the output handlers if no 'output' option was passed
        # via command-line.
        def set_test_output():
            reporter.output = StringIO()

        def close_test_output():
            pass

        if output is None:
            reporter.setOutput = set_test_output
            reporter.closeOutput = close_test_output

        return reporter

    def testDeniedOptionCombination(self):
        denied_combinations = (
            {'gen_over_quota': True, 'gen_user_emails': True},
            {'gen_orphan_repos': True, 'gen_user_emails': True},
            {'gen_missing_repos': True, 'gen_user_emails': True},
            {'gen_orphan_repos': True, 'ppa_owner': 'foo'},
            {'gen_missing_repos': True, 'ppa_owner': 'foo'},
            )

        for kwargs in denied_combinations:
            reporter = self.getReporter(**kwargs)
            self.assertRaises(
                LaunchpadScriptFailure, reporter.checkOptions)

    def testGetActivePPAs(self):
        # `PPAReportScript.getActivePPAs` returns a list of `IArchive`
        # objects representing the PPAs with active publications.
        # Supports filtering by a specific PPA owner name.
        reporter = self.getReporter()
        self.assertEquals(
            [ppa.owner.name for ppa in reporter.getActivePPAs()],
            ['cprov', 'sabdfl'])

        reporter = self.getReporter(ppa_owner='cprov')
        self.assertEquals(
            [ppa.owner.name for ppa in reporter.getActivePPAs()],
            ['cprov'])

        reporter = self.getReporter(ppa_owner='foobar')
        self.assertEquals(
            [ppa.owner.name for ppa in reporter.getActivePPAs()],
            [])

    def testOverQuota(self):
        # OverQuota report lists PPA urls, quota and current size values
        # one by line in a CSV format.

        # Quota threshould defaults to 80%
        reporter = self.getReporter()
        ppas = reporter.getActivePPAs()
        reporter.setOutput()
        reporter.reportOverQuota(ppas)
        self.assertEquals(
            reporter.output.getvalue().splitlines(), [
                '',
                '= PPAs over 80.00% of their quota =',
                ]
            )

        # Quota threshould can be specified.
        reporter = self.getReporter(quota_threshould=.01)
        reporter.setOutput()
        reporter.reportOverQuota(ppas)
        self.assertEquals(
            reporter.output.getvalue().splitlines(), [
                '',
                '= PPAs over 0.01% of their quota =',
                'http://launchpad.dev/~cprov/+archive/ppa | 1024 | 9',
                'http://launchpad.dev/~sabdfl/+archive/ppa | 1024 | 9',
                ]
            )

    def testUserEmails(self):
        # UserEmails report lists user name, user displayname and user
        # preferred emails address one by line in a CSV format for users
        # involed with the given PPAs.
        reporter = self.getReporter()
        ppas = reporter.getActivePPAs()
        reporter.setOutput()
        reporter.reportUserEmails(ppas)
        self.assertEquals(
            reporter.output.getvalue().splitlines(), [
                '',
                '= PPA user emails =',
                'cprov | Celso Providelo | celso.providelo@canonical.com',
                'sabdfl | Mark Shuttleworth | mark@hbd.com',
                ]
            )

        # UserEmails report can be generated for a single PPA.
        reporter = self.getReporter(ppa_owner='cprov')
        ppas = reporter.getActivePPAs()
        reporter.setOutput()
        reporter.reportUserEmails(ppas)
        self.assertEquals(
            reporter.output.getvalue().splitlines(), [
                '',
                '= PPA user emails =',
                'cprov | Celso Providelo | celso.providelo@canonical.com',
                ]
            )

    def testOrphanRepos(self):
        # OrphanRepos report lists all directories in the PPA root that
        # do not correspond to a existing active PPA. Since the test
        # setup resets PPA root, there is nothing to report.
        reporter = self.getReporter(ppa_owner='cprov')
        ppas = reporter.getActivePPAs()
        reporter.setOutput()
        reporter.reportOrphanRepos(ppas)
        self.assertEquals(
            reporter.output.getvalue().splitlines(), [
                '',
                '= Orphan PPA repositories =',
                ]
            )
        # We create a 'orphan' repository.
        orphan_repo = os.path.join(
            config.personalpackagearchive.root, 'orphan')
        os.mkdir(orphan_repo)

        # It gets listed in the OrphanRepos reports.
        reporter.setOutput()
        reporter.reportOrphanRepos(ppas)
        self.assertEquals(
            reporter.output.getvalue().splitlines(), [
                '',
                '= Orphan PPA repositories =',
                '/var/tmp/ppa.test/orphan',
                ]
            )
        # Remove the orphan directory.
        shutil.rmtree(orphan_repo)

    def testMissingRepos(self):
        # MissingRepos report lists all repositories that should exist
        # in the PPA root that in other to satisfy the active PPAs in DB.
        reporter = self.getReporter()
        ppas = reporter.getActivePPAs()

        # Since setup resets PPA root, both active PPAs are listed.
        reporter.setOutput()
        reporter.reportMissingRepos(ppas)
        self.assertEquals(
            reporter.output.getvalue().splitlines(), [
                '',
                '= Missing PPA repositories =',
                '/var/tmp/ppa.test/cprov',
                '/var/tmp/ppa.test/sabdfl',
                ]
            )
        # We create both active PPA repositories.
        owner_names = [ppa.owner.name for ppa in ppas]
        created_repos = []
        for owner_name in owner_names:
            repo_path = os.path.join(
                config.personalpackagearchive.root, owner_name)
            os.mkdir(repo_path)
            created_repos.append(repo_path)

        # They are not listed in the MissingRepos report anymore.
        reporter.setOutput()
        reporter.reportMissingRepos(ppas)
        self.assertEquals(
            reporter.output.getvalue().splitlines(), [
                '',
                '= Missing PPA repositories =',
                ]
            )

        # Remove the created repositories.
        for repo_path in created_repos:
            shutil.rmtree(repo_path)

    def testOutput(self):
        # When requested in the command-line the report output is
        # stored correctly in the specified file.
        tmp_path = tempfile.mktemp()
        reporter = self.getReporter(
            gen_missing_repos=True, output=tmp_path)
        reporter.main()
        self.assertEquals(
            open(tmp_path).read().splitlines(),[
                '',
                '= Missing PPA repositories =',
                '/var/tmp/ppa.test/cprov',
                '/var/tmp/ppa.test/sabdfl',
                ]
            )
        # Remove the report file.
        os.remove(tmp_path)

    def testRunMain(self):
        # Run the main() script function with the full report options
        # and check if the testing output is what it promises.
        reporter = self.getReporter(
            gen_over_quota=True, gen_orphan_repos=True,
            gen_missing_repos=True)
        reporter.main()
        self.assertEquals(
            reporter.output.getvalue().splitlines(), [
                '',
                '= PPAs over 80.00% of their quota =',
                '',
                '= Orphan PPA repositories =',
                '',
                '= Missing PPA repositories =',
                '/var/tmp/ppa.test/cprov',
                '/var/tmp/ppa.test/sabdfl',
                ]
            )
        # Another run for generating user emails report
        reporter = self.getReporter(gen_user_emails=True)
        reporter.main()
        self.assertEquals(
            reporter.output.getvalue().splitlines(), [
                '',
                '= PPA user emails =',
                'cprov | Celso Providelo | celso.providelo@canonical.com',
                'sabdfl | Mark Shuttleworth | mark@hbd.com',
                ]
            )


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
