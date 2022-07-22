# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the LibraryFileAlias."""

import io
import unittest

import transaction
from zope.component import getUtility

from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.testing import ANONYMOUS, login, logout
from lp.testing.layers import LaunchpadFunctionalLayer


class TestLibraryFileAlias(unittest.TestCase):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)
        self.text_content = b"This is content\non two lines."
        self.file_alias = getUtility(ILibraryFileAliasSet).create(
            "content.txt",
            len(self.text_content),
            io.BytesIO(self.text_content),
            "text/plain",
        )
        # Make it possible to retrieve the content from the Librarian.
        transaction.commit()

    def tearDown(self):
        logout()

    def test_file_is_closed_at_the_end_of_transaction(self):
        """Non-DB instance state should be reset on transaction boundaries."""
        self.file_alias.open()
        self.assertEqual(self.text_content[0:4], self.file_alias.read(4))
        # This should reset the file pointer.
        transaction.commit()
        # If the file pointer isn't reset, the next call to read() will return
        # the remaining content. If it's reset, the file will be auto-opened
        # and its whole content will be returned.
        self.assertEqual(self.text_content, self.file_alias.read())
