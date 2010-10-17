# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from testtools.matchers import (
    Is,
    LessThan,
    Not,
    )
from zope.interface import (
    implements,
    Interface,
    )
from zope.interface.exceptions import BrokenImplementation
from zope.interface.verify import verifyObject
from zope.security.checker import NamesChecker
from zope.security.proxy import ProxyFactory

from lp.testing import TestCase
from lp.testing._webservice import QueryCollector
from lp.testing.matchers import (
    DoesNotCorrectlyProvide,
    DoesNotProvide,
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


class Implementor:
    """Dummy class that implements ITestInterface for testing."""

    implements(ITestInterface)

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

        class BadlyImplementedClass:
            implements(ITestInterface)

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
            self.assert_("verifyObject did not raise an exception.")
        except BrokenImplementation, e:
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
        collector = QueryCollector()
        collector.count = 3
        # not inspected
        del collector.queries
        self.assertThat(matcher.match(collector), Is(None))

    def test_mismatch(self):
        matcher = HasQueryCount(LessThan(2))
        collector = QueryCollector()
        collector.count = 2
        collector.queries = [("foo", "bar"), ("baaz", "quux")]
        mismatch = matcher.match(collector)
        self.assertThat(mismatch, Not(Is(None)))
        details = mismatch.get_details()
        lines = []
        for name, content in details.items():
            self.assertEqual("queries", name)
            self.assertEqual("text", content.content_type.type)
            lines.append(''.join(content.iter_text()))
        self.assertEqual(["('foo', 'bar')\n('baaz', 'quux')"],
            lines)
        self.assertEqual(
            "queries do not match: %s" % (LessThan(2).match(2).describe(),),
            mismatch.describe())
