# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `BugTargetTraversalMixin`."""

from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy

from lp.services.webapp.publisher import canonical_url
from lp.testing import TestCaseWithFactory, login_person
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.publication import test_traverse


class TestBugTaskTraversal(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_traversal_to_nonexistent_bugtask(self):
        # Test that a traversing to a non-existent bugtask redirects to the
        # bug's default bugtask.
        bug = self.factory.makeBug()
        bugtask = self.factory.makeBugTask(bug=bug)
        bugtask_url = canonical_url(bugtask, rootsite="bugs")
        login_person(bugtask.owner)
        bugtask.delete()
        obj, view, request = test_traverse(bugtask_url)
        view()
        naked_view = removeSecurityProxy(view)
        self.assertEqual(301, request.response.getStatus())
        self.assertEqual(
            naked_view.target,
            canonical_url(bug.default_bugtask, rootsite="bugs"),
        )

    def test_traversal_to_bugtask_delete_url(self):
        # Test that a traversing to the delete URL of a non-existent bugtask
        # raises a NotFound error.
        bug = self.factory.makeBug()
        bugtask = self.factory.makeBugTask(bug=bug)
        bugtask_delete_url = canonical_url(
            bugtask, rootsite="bugs", view_name="+delete"
        )
        login_person(bugtask.owner)
        bugtask.delete()
        self.assertRaises(NotFound, test_traverse, bugtask_delete_url)

    def test_traversal_to_nonexistent_bugtask_on_api(self):
        # Traversing to a non-existent bugtask on the API redirects to
        # the default bugtask, but also on the API.
        bug = self.factory.makeBug()
        product = self.factory.makeProduct()
        obj, view, request = test_traverse(
            "http://api.launchpad.test/1.0/%s/+bug/%d"
            % (product.name, bug.default_bugtask.bug.id)
        )
        self.assertEqual(
            removeSecurityProxy(view).target,
            "http://api.launchpad.test/1.0/%s/+bug/%d"
            % (bug.default_bugtask.target.name, bug.default_bugtask.bug.id),
        )
