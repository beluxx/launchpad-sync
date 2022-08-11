# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the person_sort_key stored procedure."""

from zope.component import getUtility
from zope.interface.verify import verifyObject

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.nameblacklist import (
    INameBlacklist,
    INameBlacklistSet,
)
from lp.services.database.interfaces import IStore
from lp.services.webapp.authorization import check_permission
from lp.testing import ANONYMOUS, TestCaseWithFactory, login, login_celebrity
from lp.testing.layers import DatabaseFunctionalLayer, ZopelessDatabaseLayer


class TestNameBlacklist(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def setUp(self):
        super().setUp()
        self.name_blacklist_set = getUtility(INameBlacklistSet)
        self.caret_foo_exp = self.name_blacklist_set.create("^foo")
        self.foo_exp = self.name_blacklist_set.create("foo")
        self.verbose_exp = self.name_blacklist_set.create("v e r b o s e")
        team = self.factory.makeTeam()
        self.admin_exp = self.name_blacklist_set.create("fnord", admin=team)
        self.store = IStore(self.foo_exp)
        self.store.flush()

    def name_blacklist_match(self, name, user_id=None):
        """Return the result of the name_blacklist_match stored procedure."""
        user_id = user_id or 0
        result = self.store.execute(
            "SELECT name_blacklist_match(%s, %s)", (name, user_id)
        )
        return result.get_one()[0]

    def is_blacklisted_name(self, name, user_id=None):
        """Return the result of the is_blacklisted_name stored procedure."""
        user_id = user_id or 0
        result = self.store.execute(
            "SELECT is_blacklisted_name(%s, %s)", (name, user_id)
        )
        blacklisted = result.get_one()[0]
        self.assertIsNotNone(blacklisted, "is_blacklisted_name returned NULL")
        return bool(blacklisted)

    def test_name_blacklist_match(self):

        # A name that is not blacklisted returns NULL/None
        self.assertIsNone(self.name_blacklist_match("bar"))

        # A name that is blacklisted returns the id of the row in the
        # NameBlacklist table that matched. Rows are tried in order, and the
        # first match is returned.
        self.assertEqual(
            self.name_blacklist_match("foobar"), self.caret_foo_exp.id
        )
        self.assertEqual(self.name_blacklist_match("barfoo"), self.foo_exp.id)

    def test_name_blacklist_match_admin_does_not_match(self):
        # A user in the expresssion's admin team is exempt from the
        # backlisted name restriction.
        user = self.admin_exp.admin.teamowner
        self.assertEqual(None, self.name_blacklist_match("fnord", user.id))

    def test_name_blacklist_match_launchpad_admin_can_change(self):
        # A Launchpad admin is exempt from any backlisted name restriction
        # that has an admin.
        user = self.factory.makePerson()
        admins = getUtility(ILaunchpadCelebrities).admin
        admins.addMember(user, user)
        self.assertEqual(None, self.name_blacklist_match("fnord", user.id))

    def test_name_blacklist_match_launchpad_admin_cannot_change(self):
        # A Launchpad admin cannot override backlisted names without admins.
        user = self.factory.makePerson()
        admins = getUtility(ILaunchpadCelebrities).admin
        admins.addMember(user, user)
        self.assertEqual(
            self.foo_exp.id, self.name_blacklist_match("barfoo", user.id)
        )

    def test_name_blacklist_match_cache(self):
        # If the blacklist is changed in the DB, these changes are noticed.
        # This test is needed because the stored procedure keeps a cache
        # of the compiled regular expressions.
        self.assertEqual(
            self.name_blacklist_match("foobar"), self.caret_foo_exp.id
        )
        self.caret_foo_exp.regexp = "nomatch"
        self.assertEqual(self.name_blacklist_match("foobar"), self.foo_exp.id)
        self.foo_exp.regexp = "nomatch2"
        self.assertIsNone(self.name_blacklist_match("foobar"))

    def test_is_blacklisted_name(self):
        # is_blacklisted_name() is just a wrapper around name_blacklist_match
        # that is friendlier to use in a boolean context.
        self.assertFalse(self.is_blacklisted_name("bar"))
        self.assertTrue(self.is_blacklisted_name("foo"))
        self.caret_foo_exp.regexp = "bar"
        self.foo_exp.regexp = "bar2"
        self.assertFalse(self.is_blacklisted_name("foo"))

    def test_is_blacklisted_name_admin_false(self):
        # Users in the expression's admin team are will return False.
        user = self.admin_exp.admin.teamowner
        self.assertFalse(self.is_blacklisted_name("fnord", user.id))

    def test_case_insensitive(self):
        self.assertTrue(self.is_blacklisted_name("Foo"))

    def test_verbose(self):
        # Testing the VERBOSE flag is used when compiling the regexp
        self.assertTrue(self.is_blacklisted_name("verbose"))


class TestNameBlacklistSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        login_celebrity("registry_experts")
        self.name_blacklist_set = getUtility(INameBlacklistSet)

    def test_create_with_one_arg(self):
        # Test NameBlacklistSet.create(regexp).
        name_blacklist = self.name_blacklist_set.create("foo")
        self.assertTrue(verifyObject(INameBlacklist, name_blacklist))
        self.assertEqual("foo", name_blacklist.regexp)
        self.assertIs(None, name_blacklist.comment)

    def test_create_with_two_args(self):
        # Test NameBlacklistSet.create(regexp, comment).
        name_blacklist = self.name_blacklist_set.create("foo", "bar")
        self.assertTrue(verifyObject(INameBlacklist, name_blacklist))
        self.assertEqual("foo", name_blacklist.regexp)
        self.assertEqual("bar", name_blacklist.comment)

    def test_create_with_three_args(self):
        # Test NameBlacklistSet.create(regexp, comment, admin).
        team = self.factory.makeTeam()
        name_blacklist = self.name_blacklist_set.create("foo", "bar", team)
        self.assertTrue(verifyObject(INameBlacklist, name_blacklist))
        self.assertEqual("foo", name_blacklist.regexp)
        self.assertEqual("bar", name_blacklist.comment)
        self.assertEqual(team, name_blacklist.admin)

    def test_get_int(self):
        # Test NameBlacklistSet.get() with int id.
        name_blacklist = self.name_blacklist_set.create("foo", "bar")
        store = IStore(name_blacklist)
        store.flush()
        retrieved = self.name_blacklist_set.get(name_blacklist.id)
        self.assertEqual(name_blacklist, retrieved)

    def test_get_string(self):
        # Test NameBlacklistSet.get() with string id.
        name_blacklist = self.name_blacklist_set.create("foo", "bar")
        store = IStore(name_blacklist)
        store.flush()
        retrieved = self.name_blacklist_set.get(str(name_blacklist.id))
        self.assertEqual(name_blacklist, retrieved)

    def test_get_returns_None_instead_of_ValueError(self):
        # Test that NameBlacklistSet.get() will return None instead of
        # raising a ValueError when it tries to cast the id to an int,
        # so that traversing an invalid url causes a Not Found error
        # instead of an error that is recorded as an oops.
        self.assertIs(None, self.name_blacklist_set.get("asdf"))

    def test_getAll(self):
        # Test NameBlacklistSet.getAll().
        result = [
            (item.regexp, item.comment)
            for item in self.name_blacklist_set.getAll()
        ]
        expected = [
            ("^admin", None),
            ("blacklist", "For testing purposes"),
        ]
        self.assertEqual(expected, result)

    def test_NameBlacklistSet_permissions(self):
        # Verify that non-registry-experts do not have permission to
        # access the NameBlacklistSet.
        self.assertTrue(
            check_permission("launchpad.View", self.name_blacklist_set)
        )
        self.assertTrue(
            check_permission("launchpad.Edit", self.name_blacklist_set)
        )
        login(ANONYMOUS)
        self.assertFalse(
            check_permission("launchpad.View", self.name_blacklist_set)
        )
        self.assertFalse(
            check_permission("launchpad.Edit", self.name_blacklist_set)
        )

    def test_NameBlacklist_permissions(self):
        # Verify that non-registry-experts do not have permission to
        # access the NameBlacklist.
        name_blacklist = self.name_blacklist_set.create("foo")
        self.assertTrue(check_permission("launchpad.View", name_blacklist))
        self.assertTrue(check_permission("launchpad.Edit", name_blacklist))
        login(ANONYMOUS)
        self.assertFalse(check_permission("launchpad.View", name_blacklist))
        self.assertFalse(check_permission("launchpad.Edit", name_blacklist))
