# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the sendbranchmail script"""

import os.path

import transaction

from lp.code.enums import (
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
)
from lp.code.model.branchjob import RevisionMailJob, RevisionsAddedJob
from lp.services.config import config
from lp.services.osutils import override_environ
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessAppServerLayer
from lp.testing.script import run_script


class TestSendbranchmail(TestCaseWithFactory):
    layer = ZopelessAppServerLayer

    def createBranch(self):
        branch, tree = self.create_branch_and_tree()
        branch.subscribe(
            branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL,
            branch.registrant,
        )
        transport = tree.controldir.root_transport
        transport.put_bytes("foo", b"bar")
        tree.add("foo")
        # XXX: AaronBentley 2010-08-06 bug=614404: a bzr username is
        # required to generate the revision-id.
        with override_environ(BRZ_EMAIL="me@example.com"):
            tree.commit("Added foo.", rev_id=b"rev1")
        return branch, tree

    def test_sendbranchmail(self):
        """Ensure sendbranchmail runs and sends email."""
        self.useBzrBranches()
        branch, tree = self.createBranch()
        mail_job = RevisionMailJob.create(
            branch, 1, "from@example.org", "body", "foo"
        )
        transaction.commit()
        retcode, stdout, stderr = run_script(
            os.path.join(config.root, "cronscripts", "process-job-source.py"),
            args=["IRevisionMailJobSource"],
        )
        self.assertTextMatchesExpressionIgnoreWhitespace(
            "INFO    "
            "Creating lockfile: /var/lock/launchpad-process-job-source-"
            "IRevisionMailJobSource.lock\n"
            "INFO    Running synchronously.\n"
            "INFO    Running <REVISION_MAIL branch job \\(\\d+\\) for .*?> "
            "\\(ID %d\\) in status Waiting\n"
            "INFO    Ran 1 RevisionMailJob jobs.\n" % mail_job.job.id,
            stderr,
        )
        self.assertEqual("", stdout)
        self.assertEqual(0, retcode)

    def test_revision_added_job(self):
        """RevisionsAddedJobs are run by sendbranchmail."""
        self.useBzrBranches()
        branch, tree = self.createBranch()
        tree.controldir.root_transport.put_bytes("foo", b"baz")
        # XXX: AaronBentley 2010-08-06 bug=614404: a bzr username is
        # required to generate the revision-id.
        with override_environ(BRZ_EMAIL="me@example.com"):
            tree.commit("Added foo.", rev_id=b"rev2")
        job = RevisionsAddedJob.create(
            branch, "rev1", "rev2", "from@example.org"
        )
        transaction.commit()
        retcode, stdout, stderr = run_script(
            os.path.join(config.root, "cronscripts", "process-job-source.py"),
            args=["IRevisionsAddedJobSource"],
        )
        self.assertTextMatchesExpressionIgnoreWhitespace(
            "INFO    "
            "Creating lockfile: /var/lock/launchpad-process-job-source-"
            "IRevisionsAddedJobSource.lock\n"
            "INFO    Running synchronously.\n"
            "INFO    Running <REVISIONS_ADDED_MAIL branch job \\(\\d+\\) "
            "for .*?> \\(ID %d\\) in status Waiting\n"
            "INFO    Ran 1 RevisionsAddedJob jobs.\n" % job.job.id,
            stderr,
        )
        self.assertEqual("", stdout)
        self.assertEqual(0, retcode)
