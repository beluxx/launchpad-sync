# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from testtools.matchers import (
    Equals,
    Is,
    KeysEqual,
    LessThan,
    Not,
    )
from zope.interface import (
    implementer,
    Interface,
    )
from zope.interface.exceptions import BrokenImplementation
from zope.interface.verify import verifyObject
from zope.security.checker import NamesChecker
from zope.security.proxy import ProxyFactory

from lp.testing import (
    RequestTimelineCollector,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import (
    BrowsesWithQueryLimit,
    Contains,
    DoesNotContain,
    DoesNotCorrectlyProvide,
    DoesNotProvide,
    EqualsIgnoringWhitespace,
    HasQueryCount,
    IsNotProxied,
    IsProxied,
    Provides,
    ProvidesAndIsProxied,
    )


class ITestInterface(Interface):
    """A dummy interface for testing."""

    def doFoo():
        """Dummy method for interface compliance testing."""


@implementer(ITestInterface)
class Implementor:
    """Dummy class that implements ITestInterface for testing."""

    def doFoo(self):
        pass


class DoesNotProvideTests(TestCase):

    def test_describe(self):
        obj = object()
        mismatch = DoesNotProvide(obj, ITestInterface)
        self.assertEqual(
            "%r does not provide %r." % (obj, ITestInterface),
            mismatch.describe())


class DoesNotCorrectlyProvideMismatchTests(TestCase):

    def test_describe(self):
        obj = object()
        mismatch = DoesNotCorrectlyProvide(obj, ITestInterface)
        self.assertEqual(
            "%r claims to provide %r, but does not do so correctly."
                % (obj, ITestInterface),
            mismatch.describe())

    def test_describe_with_extra(self):
        obj = object()
        mismatch = DoesNotCorrectlyProvide(
            obj, ITestInterface, extra="foo")
        self.assertEqual(
            "%r claims to provide %r, but does not do so correctly: foo"
                % (obj, ITestInterface),
            mismatch.describe())


class ProvidesTests(TestCase):

    def test_str(self):
        matcher = Provides(ITestInterface)
        self.assertEqual("provides %r." % ITestInterface, str(matcher))

    def test_matches(self):
        matcher = Provides(ITestInterface)
        self.assertEqual(None, matcher.match(Implementor()))

    def match_does_not_provide(self):
        obj = object()
        matcher = Provides(ITestInterface)
        return obj, matcher.match(obj)

    def test_mismatches_not_implements(self):
        obj, mismatch = self.match_does_not_provide()
        self.assertIsInstance(mismatch, DoesNotProvide)

    def test_does_not_provide_sets_object(self):
        obj, mismatch = self.match_does_not_provide()
        self.assertEqual(obj, mismatch.obj)

    def test_does_not_provide_sets_interface(self):
        obj, mismatch = self.match_does_not_provide()
        self.assertEqual(ITestInterface, mismatch.interface)

    def match_does_not_verify(self):

        @implementer(ITestInterface)
        class BadlyImplementedClass:
            pass

        obj = BadlyImplementedClass()
        matcher = Provides(ITestInterface)
        return obj, matcher.match(obj)

    def test_mismatch_does_not_verify(self):
        obj, mismatch = self.match_does_not_verify()
        self.assertIsInstance(mismatch, DoesNotCorrectlyProvide)

    def test_does_not_verify_sets_object(self):
        obj, mismatch = self.match_does_not_verify()
        self.assertEqual(obj, mismatch.obj)

    def test_does_not_verify_sets_interface(self):
        obj, mismatch = self.match_does_not_verify()
        self.assertEqual(ITestInterface, mismatch.interface)

    def test_does_not_verify_sets_extra(self):
        obj, mismatch = self.match_does_not_verify()
        try:
            verifyObject(ITestInterface, obj)
            self.assertTrue("verifyObject did not raise an exception.")
        except BrokenImplementation as e:
            extra = str(e)
        self.assertEqual(extra, mismatch.extra)


class IsNotProxiedTests(TestCase):

    def test_describe(self):
        obj = object()
        mismatch = IsNotProxied(obj)
        self.assertEqual("%r is not proxied." % obj, mismatch.describe())


class IsProxiedTests(TestCase):

    def test_str(self):
        matcher = IsProxied()
        self.assertEqual("Is proxied.", str(matcher))

    def test_match(self):
        obj = ProxyFactory(object(), checker=NamesChecker())
        self.assertEqual(None, IsProxied().match(obj))

    def test_mismatch(self):
        obj = object()
        self.assertIsInstance(IsProxied().match(obj), IsNotProxied)

    def test_mismatch_sets_object(self):
        obj = object()
        mismatch = IsProxied().match(obj)
        self.assertEqual(obj, mismatch.obj)


class ProvidesAndIsProxiedTests(TestCase):

    def test_str(self):
        matcher = ProvidesAndIsProxied(ITestInterface)
        self.assertEqual(
            "Provides %r and is proxied." % ITestInterface,
            str(matcher))

    def test_match(self):
        obj = ProxyFactory(
            Implementor(), checker=NamesChecker(names=("doFoo", )))
        matcher = ProvidesAndIsProxied(ITestInterface)
        self.assertThat(obj, matcher)
        self.assertEqual(None, matcher.match(obj))

    def test_mismatch_unproxied(self):
        obj = Implementor()
        matcher = ProvidesAndIsProxied(ITestInterface)
        self.assertIsInstance(matcher.match(obj), IsNotProxied)

    def test_mismatch_does_not_implement(self):
        obj = ProxyFactory(object(), checker=NamesChecker())
        matcher = ProvidesAndIsProxied(ITestInterface)
        self.assertIsInstance(matcher.match(obj), DoesNotProvide)


class TestQueryMatching(TestCase):
    """Query matching is a work in progress and can be factored out more.

    For now its pretty hard coded to the initial use case and overlaps some
    unwritten hypothetical testtools infrastructure - e.g. permitting use of
    attrgetter and the like.
    """

    def test_match(self):
        matcher = HasQueryCount(Is(3))
        collector = RequestTimelineCollector()
        collector.count = 3
        # not inspected
        del collector.queries
        self.assertThat(matcher.match(collector), Is(None))

    def test_mismatch(self):
        matcher = HasQueryCount(LessThan(2))
        collector = RequestTimelineCollector()
        collector.count = 2
        collector.queries = [
            (0, 1, "SQL-main-slave", "SELECT 1 FROM Person", None),
            (2, 3, "SQL-main-slave", "SELECT 1 FROM Product", None),
            ]
        mismatch = matcher.match(collector)
        self.assertThat(mismatch, Not(Is(None)))
        details = mismatch.get_details()
        lines = []
        for name, content in details.items():
            self.assertEqual("queries", name)
            self.assertEqual("text", content.content_type.type)
            lines.append(''.join(content.iter_text()))
        separator = "-" * 70
        expected_lines = [
            "0-1@SQL-main-slave SELECT 1 FROM Person\n" + separator + "\n" +
            "2-3@SQL-main-slave SELECT 1 FROM Product\n" + separator,
            ]
        self.assertEqual(expected_lines, lines)
        self.assertEqual(
            "queries do not match: %s" % (LessThan(2).match(2).describe(),),
            mismatch.describe())

    def test_with_backtrace(self):
        matcher = HasQueryCount(LessThan(2))
        collector = RequestTimelineCollector()
        collector.count = 2
        collector.queries = [
            (0, 1, "SQL-main-slave", "SELECT 1 FROM Person",
             '  File "example", line 2, in <module>\n'
             '    Store.of(Person).one()\n'),
            (2, 3, "SQL-main-slave", "SELECT 1 FROM Product",
             '  File "example", line 3, in <module>\n'
             '    Store.of(Product).one()\n'),
            ]
        mismatch = matcher.match(collector)
        self.assertThat(mismatch, Not(Is(None)))
        details = mismatch.get_details()
        lines = []
        for name, content in details.items():
            self.assertEqual("queries", name)
            self.assertEqual("text", content.content_type.type)
            lines.append(''.join(content.iter_text()))
        separator = "-" * 70
        backtrace_separator = "." * 70
        expected_lines = [
            '0-1@SQL-main-slave SELECT 1 FROM Person\n' + separator + '\n' +
            '  File "example", line 2, in <module>\n' +
            '    Store.of(Person).one()\n' + backtrace_separator + '\n' +
            '2-3@SQL-main-slave SELECT 1 FROM Product\n' + separator + '\n' +
            '  File "example", line 3, in <module>\n' +
            '    Store.of(Product).one()\n' + backtrace_separator,
            ]
        self.assertEqual(expected_lines, lines)
        self.assertEqual(
            "queries do not match: %s" % (LessThan(2).match(2).describe(),),
            mismatch.describe())

    def test_byEquality(self):
        old_collector = RequestTimelineCollector()
        old_collector.count = 2
        old_collector.queries = [
            (0, 1, "SQL-main-slave", "SELECT 1 FROM Person", None),
            (2, 3, "SQL-main-slave", "SELECT 1 FROM Product", None),
            ]
        new_collector = RequestTimelineCollector()
        new_collector.count = 3
        new_collector.queries = [
            (0, 1, "SQL-main-slave", "SELECT 1 FROM Person", None),
            (2, 3, "SQL-main-slave", "SELECT 1 FROM Product", None),
            (4, 5, "SQL-main-slave", "SELECT 1 FROM Distribution", None),
            ]
        matcher = HasQueryCount.byEquality(old_collector)
        mismatch = matcher.match(new_collector)
        self.assertThat(mismatch, Not(Is(None)))
        details = mismatch.get_details()
        old_lines = []
        new_lines = []
        self.assertThat(details, KeysEqual("queries", "other_queries"))
        self.assertEqual("text", details["other_queries"].content_type.type)
        old_lines.append("".join(details["other_queries"].iter_text()))
        self.assertEqual("text", details["queries"].content_type.type)
        new_lines.append("".join(details["queries"].iter_text()))
        separator = "-" * 70
        expected_old_lines = [
            "0-1@SQL-main-slave SELECT 1 FROM Person\n" + separator + "\n" +
            "2-3@SQL-main-slave SELECT 1 FROM Product\n" + separator,
            ]
        expected_new_lines = [
            "0-1@SQL-main-slave SELECT 1 FROM Person\n" + separator + "\n" +
            "2-3@SQL-main-slave SELECT 1 FROM Product\n" + separator + "\n" +
            "4-5@SQL-main-slave SELECT 1 FROM Distribution\n" + separator,
            ]
        self.assertEqual(expected_old_lines, old_lines)
        self.assertEqual(expected_new_lines, new_lines)
        self.assertEqual(
            "queries do not match: %s" % (Equals(2).match(3).describe(),),
            mismatch.describe())


class TestBrowserQueryMatching(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_smoke(self):
        person = self.factory.makePerson()
        matcher = BrowsesWithQueryLimit(100, person)
        self.assertThat(person, matcher)
        matcher = Not(BrowsesWithQueryLimit(1, person))
        self.assertThat(person, matcher)


class DoesNotContainTests(TestCase):

    def test_describe(self):
        mismatch = DoesNotContain("foo", "bar")
        self.assertEqual(
            "'foo' does not contain 'bar'.", mismatch.describe())


class ContainsTests(TestCase):

    def test_str(self):
        matcher = Contains("bar")
        self.assertEqual("Contains 'bar'.", str(matcher))

    def test_match(self):
        matcher = Contains("bar")
        self.assertIs(None, matcher.match("foo bar baz"))

    def test_mismatch_returns_does_not_start_with(self):
        matcher = Contains("bar")
        self.assertIsInstance(matcher.match("foo"), DoesNotContain)

    def test_mismatch_sets_matchee(self):
        matcher = Contains("bar")
        mismatch = matcher.match("foo")
        self.assertEqual("foo", mismatch.matchee)

    def test_mismatch_sets_expected(self):
        matcher = Contains("bar")
        mismatch = matcher.match("foo")
        self.assertEqual("bar", mismatch.expected)


class EqualsIgnoringWhitespaceTests(TestCase):

    def test_bytes(self):
        matcher = EqualsIgnoringWhitespace(b"abc")
        self.assertEqual("EqualsIgnoringWhitespace(%r)" % b"abc", str(matcher))

    def test_match_bytes(self):
        matcher = EqualsIgnoringWhitespace(b"one \t two \n three")
        self.assertIs(None, matcher.match(b" one \r two     three "))

    def test_mismatch_bytes(self):
        matcher = EqualsIgnoringWhitespace(b"one \t two \n three")
        mismatch = matcher.match(b" one \r three ")
        self.assertEqual(
            "%r != %r" % (b"one three", b"one two three"),
            mismatch.describe())

    def test_match_unicode(self):
        matcher = EqualsIgnoringWhitespace(u"one \t two \n \u1234  ")
        self.assertIs(None, matcher.match(u" one \r two     \u1234 "))

    def test_mismatch_unicode(self):
        matcher = EqualsIgnoringWhitespace(u"one \t two \n \u1234  ")
        mismatch = matcher.match(u" one \r \u1234 ")
        self.assertEqual(
            u"%r != %r" % (u"one \u1234", u"one two \u1234"),
            mismatch.describe())

    def test_match_non_string(self):
        matcher = EqualsIgnoringWhitespace(1234)
        self.assertIs(None, matcher.match(1234))
