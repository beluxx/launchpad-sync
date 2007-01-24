#!/usr/bin/env python
# Copyright (c) 2005-2006 Canonical Ltd.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

import datetime
import os
import random
import time
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.revision import NULL_REVISION
from bzrlib.uncommit import uncommit
import pytz
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.database import (
    Revision, RevisionNumber, RevisionParent, RevisionAuthor)
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.launchpad.interfaces import IBranchSet
from canonical.launchpad.scripts.bzrsync import BzrSync, RevisionModifiedError
from canonical.launchpad.scripts.tests.webserver_helper import WebserverHelper
from canonical.testing import ZopelessLayer


class BzrSyncTestCase(unittest.TestCase):
    """Common base for BzrSync test cases."""

    layer = ZopelessLayer

    AUTHOR = "Revision Author <author@example.com>"
    LOG = "Log message"

    def setUp(self):
        self.webserver_helper = WebserverHelper()
        self.webserver_helper.setUp()
        self.zopeless_helper = LaunchpadZopelessTestSetup(
            dbuser=config.branchscanner.dbuser)
        self.zopeless_helper.setUp()
        self.txn = self.zopeless_helper.txn
        self.setUpBzrBranch()
        self.setUpDBBranch()
        self.setUpAuthor()

    def tearDown(self):
        self.zopeless_helper.tearDown()
        self.webserver_helper.tearDown()

    def join(self, name):
        return self.webserver_helper.join(name)

    def url(self, name):
        return self.webserver_helper.get_remote_url(name)

    def setUpBzrBranch(self):
        self.bzr_branch_relpath = "bzr_branch"
        self.bzr_branch_abspath = self.join(self.bzr_branch_relpath)
        self.bzr_branch_url = self.url(self.bzr_branch_relpath)
        os.mkdir(self.bzr_branch_abspath)
        self.bzr_tree = BzrDir.create_standalone_workingtree(
            self.bzr_branch_abspath)
        self.bzr_branch = self.bzr_tree.branch

    def setUpDBBranch(self):
        self.txn.begin()
        arbitraryownerid = 1
        self.db_branch = getUtility(IBranchSet).new(
            name="test",
            owner=arbitraryownerid,
            product=None,
            url=self.bzr_branch_url,
            title="Test branch",
            summary="Branch for testing")
        self.txn.commit()

    def setUpAuthor(self):
        self.db_author = RevisionAuthor.selectOneBy(name=self.AUTHOR)
        if not self.db_author:
            self.txn.begin()
            self.db_author = RevisionAuthor(name=self.AUTHOR)
            self.txn.commit()

    def getCounts(self):
        return (Revision.select().count(),
                RevisionNumber.select().count(),
                RevisionParent.select().count(),
                RevisionAuthor.select().count())

    def assertCounts(self, counts, new_revisions=0, new_numbers=0,
                     new_parents=0, new_authors=0):
        (old_revision_count,
         old_revisionnumber_count,
         old_revisionparent_count,
         old_revisionauthor_count) = counts
        (new_revision_count,
         new_revisionnumber_count,
         new_revisionparent_count,
         new_revisionauthor_count) = self.getCounts()
        revision_pair = (old_revision_count+new_revisions,
                         new_revision_count)
        revisionnumber_pair = (old_revisionnumber_count+new_numbers,
                               new_revisionnumber_count)
        revisionparent_pair = (old_revisionparent_count+new_parents,
                               new_revisionparent_count)
        revisionauthor_pair = (old_revisionauthor_count+new_authors,
                               new_revisionauthor_count)
        self.assertEqual(revision_pair[0], revision_pair[1],
                         "Wrong Revision count (should be %d, not %d)"
                         % revision_pair)
        self.assertEqual(revisionnumber_pair[0], revisionnumber_pair[1],
                         "Wrong RevisionNumber count (should be %d, not %d)"
                         % revisionnumber_pair)
        self.assertEqual(revisionparent_pair[0], revisionparent_pair[1],
                         "Wrong RevisionParent count (should be %d, not %d)"
                         % revisionparent_pair)
        self.assertEqual(revisionauthor_pair[0], revisionauthor_pair[1],
                         "Wrong RevisionAuthor count (should be %d, not %d)"
                         % revisionauthor_pair)


class TestBzrSync(BzrSyncTestCase):

    def syncAndCount(self, new_revisions=0, new_numbers=0,
                     new_parents=0, new_authors=0):
        counts = self.getCounts()
        BzrSync(self.txn, self.db_branch).syncHistoryAndClose()
        self.assertCounts(
            counts, new_revisions=new_revisions, new_numbers=new_numbers,
            new_parents=new_parents, new_authors=new_authors)

    def commitRevision(self, message=None, committer=None,
                       extra_parents=None, rev_id=None,
                       timestamp=None, timezone=None,
                       filename="file", contents=None):
        file = open(os.path.join(self.bzr_branch_abspath, filename), "w")
        if contents is None:
            file.write(str(time.time()+random.random()))
        else:
            file.write(contents)
        file.close()
        inventory = self.bzr_tree.read_working_inventory()
        if not inventory.has_filename(filename):
            self.bzr_tree.add(filename)
        if message is None:
            message = self.LOG
        if committer is None:
            committer = self.AUTHOR
        if extra_parents is not None:
            self.bzr_tree.add_pending_merge(*extra_parents)
        self.bzr_tree.commit(message, committer=committer, rev_id=rev_id,
                             timestamp=timestamp, timezone=timezone)

    def uncommitRevision(self):
        self.bzr_tree = self.bzr_branch.bzrdir.open_workingtree()
        branch = self.bzr_tree.branch
        uncommit(branch, tree=self.bzr_tree)

    def test_empty_branch(self):
        # Importing an empty branch does nothing.
        self.syncAndCount()
        self.assertEqual(self.db_branch.revision_count, 0)

    def test_import_revision(self):
        # Importing a revision in history adds one revision and number.
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.assertEqual(self.db_branch.revision_count, 1)

    def test_import_uncommit(self):
        # Second import honours uncommit.
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.uncommitRevision()
        self.syncAndCount(new_numbers=-1)
        self.assertEqual(self.db_branch.revision_count, 0)

    def test_import_recommit(self):
        # Second import honours uncommit followed by commit.
        self.commitRevision('first')
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.assertEqual(self.db_branch.revision_count, 1)
        self.uncommitRevision()
        self.commitRevision('second')
        self.syncAndCount(new_revisions=1)
        self.assertEqual(self.db_branch.revision_count, 1)
        [revno] = self.db_branch.revision_history
        self.assertEqual(revno.revision.log_body, 'second')

    def test_import_revision_with_url(self):
        # Importing a revision passing the url parameter works.
        self.commitRevision()
        counts = self.getCounts()
        bzrsync = BzrSync(self.txn, self.db_branch, self.bzr_branch_url)
        bzrsync.syncHistoryAndClose()
        self.assertCounts(counts, new_revisions=1, new_numbers=1)

    def test_new_author(self):
        # Importing a different committer adds it as an author.
        author = "Another Author <another@example.com>"
        self.commitRevision(committer=author)
        self.syncAndCount(new_revisions=1, new_numbers=1, new_authors=1)
        db_author = RevisionAuthor.selectOneBy(name=author)
        self.assertTrue(db_author)
        self.assertEquals(db_author.name, author)

    def test_new_parent(self):
        # Importing two revisions should import a new parent.
        self.commitRevision()
        self.commitRevision()
        self.syncAndCount(new_revisions=2, new_numbers=2, new_parents=1)

    def test_shorten_history(self):
        # commit some revisions with two paths to the head revision
        self.commitRevision()
        merge_rev_id = self.bzr_branch.last_revision()
        self.commitRevision()
        self.commitRevision(extra_parents=[merge_rev_id])
        self.syncAndCount(new_revisions=3, new_numbers=3, new_parents=3)
        self.assertEqual(self.db_branch.revision_count, 3)

        # now do a sync with a the shorter history.
        old_revision_history = self.bzr_branch.revision_history()
        new_revision_history = (old_revision_history[:-2] +
                                old_revision_history[-1:])

        counts = self.getCounts()
        bzrsync = BzrSync(self.txn, self.db_branch)
        bzrsync.bzr_history = new_revision_history
        bzrsync.syncHistoryAndClose()
        # the new history is one revision shorter:
        self.assertCounts(
            counts, new_revisions=0, new_numbers=-1,
            new_parents=0, new_authors=0)
        self.assertEqual(self.db_branch.revision_count, 2)

    def test_last_scanned_id_recorded(self):
        # test that the last scanned revision ID is recorded
        self.syncAndCount()
        self.assertEquals(NULL_REVISION, self.db_branch.last_scanned_id)
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.assertEquals(self.bzr_branch.last_revision(),
                          self.db_branch.last_scanned_id)

    def test_timestamp_parsing(self):
        # Test that the timezone selected does not affect the
        # timestamp recorded in the database.
        self.commitRevision(rev_id='rev-1',
                            timestamp=1000000000.0,
                            timezone=0)
        self.commitRevision(rev_id='rev-2',
                            timestamp=1000000000.0,
                            timezone=28800)
        self.syncAndCount(new_revisions=2, new_numbers=2, new_parents=1)
        rev_1 = Revision.selectOneBy(revision_id='rev-1')
        rev_2 = Revision.selectOneBy(revision_id='rev-2')
        UTC = pytz.timezone('UTC')
        dt = datetime.datetime.fromtimestamp(1000000000.0, UTC)
        self.assertEqual(rev_1.revision_date, dt)
        self.assertEqual(rev_2.revision_date, dt)

    def assertTextEqual(self, text1, text2):
        if text1 != text2:
            # find the first point of difference
            for pos in xrange(len(text1)):
                if text1[pos] != text2[pos]:
                    raise AssertionError("Text differs at position %d\n"
                                         "  text1[%d:]: %s\n"
                                         "  text2[%d:]: %s\n"
                                         % (pos, pos, repr(text1[pos:]),
                                            pos, repr(text2[pos:])))

    def test_email_format(self):
        first_revision = 'rev-1'
        self.commitRevision(rev_id=first_revision,
                            message="Log message",
                            committer="Joe Bloggs <joe@example.com>",
                            filename="hello.txt",
                            contents="Hello World\n",
                            timestamp=1000000000.0,
                            timezone=0)
        second_revision = 'rev-2'
        self.commitRevision(rev_id=second_revision,
                            message="Extended contents",
                            committer="Joe Bloggs <joe@example.com>",
                            filename="hello.txt",
                            contents="Hello World\n\nFoo Bar\n",
                            timestamp=1000100000.0,
                            timezone=0)
        
        sync = BzrSync(self.txn, self.db_branch)
        try:
            revision = sync.bzr_branch.repository.get_revision(first_revision)
            diff_lines = sync.get_diff_lines(revision)

            expected = ("=== added file 'hello.txt'\n"
                        "--- a/hello.txt\t1970-01-01 00:00:00 +0000\n"
                        "+++ b/hello.txt\t2001-09-09 01:46:40 +0000\n@@ -0,0 +1,1 @@\n"
                        "+Hello World\n\n")
            self.assertTextEqual('\n'.join(diff_lines), expected)
                             
            expected = (u"-"*60 + "\n"
                        "revno: 1\n"
                        "committer: Joe Bloggs <joe@example.com>\n"
                        "branch nick: bzr_branch\n"
                        "timestamp: Sun 2001-09-09 01:46:40 +0000\n"
                        "message:\n"
                        "  Log message\n"
                        "added:\n"
                        "  hello.txt\n")
            self.assertTextEqual(sync.get_revision_message(revision), expected)


            revision = sync.bzr_branch.repository.get_revision(second_revision)
            diff_lines = sync.get_diff_lines(revision)

            expected = ("=== modified file 'hello.txt'\n"
                        "--- a/hello.txt\t2001-09-09 01:46:40 +0000\n"
                        "+++ b/hello.txt\t2001-09-10 05:33:20 +0000\n"
                        "@@ -1,1 +1,3 @@\n"
                        " Hello World\n"
                        "+\n"
                        "+Foo Bar\n\n")
            self.assertTextEqual('\n'.join(diff_lines), expected)
                             
            expected = (u"-"*60 + "\n"
                        "revno: 2\n"
                        "committer: Joe Bloggs <joe@example.com>\n"
                        "branch nick: bzr_branch\n"
                        "timestamp: Mon 2001-09-10 05:33:20 +0000\n"
                        "message:\n"
                        "  Extended contents\n"
                        "modified:\n"
                        "  hello.txt\n")
            self.assertTextEqual(sync.get_revision_message(revision), expected)

        finally:
            sync.close()

class TestBzrSyncModified(BzrSyncTestCase):

    def setUp(self):
        BzrSyncTestCase.setUp(self)
        self.bzrsync = BzrSync(self.txn, self.db_branch)

    def tearDown(self):
        self.bzrsync.close()
        BzrSyncTestCase.tearDown(self)

    def test_revision_modified(self):
        # test that modifications to the list of parents get caught.
        class FakeRevision:
            revision_id = 'rev42'
            parent_ids = ['rev1', 'rev2']
            committer = self.AUTHOR
            message = self.LOG
            timestamp = 1000000000.0
            timezone = 0
        # synchronise the fake revision:
        counts = self.getCounts()
        self.bzrsync.syncRevision(FakeRevision)
        self.assertCounts(
            counts, new_revisions=1, new_numbers=0,
            new_parents=2, new_authors=0)

        # verify that synchronising the revision twice passes and does
        # not create a second revision object:
        counts = self.getCounts()
        self.bzrsync.syncRevision(FakeRevision)
        self.assertCounts(
            counts, new_revisions=0, new_numbers=0,
            new_parents=0, new_authors=0)

        # verify that adding a parent gets caught:
        FakeRevision.parent_ids.append('rev3')
        self.assertRaises(RevisionModifiedError,
                          self.bzrsync.syncRevision, FakeRevision)

        # verify that removing a parent gets caught:
        FakeRevision.parent_ids = ['rev1']
        self.assertRaises(RevisionModifiedError,
                          self.bzrsync.syncRevision, FakeRevision)

        # verify that reordering the parents gets caught:
        FakeRevision.parent_ids = ['rev2', 'rev1']
        self.assertRaises(RevisionModifiedError,
                          self.bzrsync.syncRevision, FakeRevision)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
