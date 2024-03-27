# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.testing.breadcrumbs import BaseBreadcrumbTestCase


class TestCodeImportMachineBreadcrumb(BaseBreadcrumbTestCase):
    """Test breadcrumbs for an `ICodeImportMachine`."""

    def test_machine(self):
        machine = self.factory.makeCodeImportMachine(hostname="apollo")
        expected = [
            ("Code Import System", "http://code.launchpad.test/+code-imports"),
            ("Machines", "http://code.launchpad.test/+code-imports/+machines"),
            (
                "apollo",
                "http://code.launchpad.test/+code-imports/+machines/apollo",
            ),
        ]
        self.assertBreadcrumbs(expected, machine)
