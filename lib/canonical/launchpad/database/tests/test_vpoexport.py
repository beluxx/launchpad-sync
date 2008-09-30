# Copyright 2008 Canonical Ltd.  All rights reserved.
"""PO file export view tests."""

__metaclass__ = type

import unittest
import transaction
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IVPOExportSet)
from canonical.launchpad.testing import (
    LaunchpadObjectFactory)
from canonical.testing import LaunchpadZopelessLayer

# The sequence number 0 is put at the beginning of the data to verify that
# it really gets sorted to the end.
TEST_MESSAGES = [
    {'msgid':'computer', 'string':'komputilo', 'sequence':0},
    {'msgid':'Thank You', 'string':'Dankon', 'sequence':1},
]

class VPOExportSetTestCase(unittest.TestCase):
    """Class test for PO file export view"""
    layer = LaunchpadZopelessLayer

    def _createMessageSet(self, testmsg):
        # Create a message set from the test data
        msgset = self.potemplate.createMessageSetFromText(
            testmsg['msgid'], None)
        msgset.setSequence(self.potemplate, testmsg['sequence'])
        msgset.updateTranslation(
            self.pofile, self.submitter_person,
            {0:testmsg['string'],},
            True, None, force_edition_rights=True)
 
    def setUp(self):
        factory = LaunchpadObjectFactory()

        # Create a PO file and fill with test data
        self.potemplate = factory.makePOTemplate()
        self.pofile = factory.makePOFile('eo', self.potemplate)
        self.submitter_person = factory.makePerson()
        self.msgsets = [
            self._createMessageSet(msg) for msg in TEST_MESSAGES ]

        transaction.commit()

    def test_get_pofile_rows_sequence(self):
        # Test for correct sorting of obsolete messages (where sequence=0)
        vpoexportset = getUtility(IVPOExportSet)
        rows = [ row for row in vpoexportset.get_pofile_rows(self.pofile) ]
        self.failUnlessEqual(rows[-1].sequence, 0,
            "VPOExportSet does not sort obsolete messages (sequence=0) "
            "to the end of the file.")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(VPOExportSetTestCase))
    return suite
