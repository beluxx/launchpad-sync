# Copyright 2012-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.archiveuploader.dscfile import SignableTagFile
from lp.archiveuploader.nascentuploadfile import UploadError
from lp.registry.interfaces.person import PersonVisibility
from lp.testing import TestCaseWithFactory, celebrity_logged_in
from lp.testing.layers import DatabaseFunctionalLayer


class TestPrivateMaintainers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_private_team_maintainer(self):
        # Maintainers can not be private teams.
        with celebrity_logged_in("admin"):
            self.factory.makeTeam(
                email="foo@bar.com", visibility=PersonVisibility.PRIVATE
            )
        sigfile = SignableTagFile()
        self.assertRaisesWithContent(
            UploadError,
            "Invalid Maintainer.",
            sigfile.parseAddress,
            "foo@bar.com",
        )
