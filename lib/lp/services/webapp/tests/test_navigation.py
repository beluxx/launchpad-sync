# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from zope.component import getMultiAdapter
from zope.configuration import xmlconfig
from zope.interface import (
    implementer,
    Interface,
    )
from zope.interface.interfaces import ComponentLookupError
from zope.publisher.interfaces.browser import (
    IBrowserPublisher,
    IDefaultBrowserLayer,
    )
from zope.testing.cleanup import cleanUp

from lp.services.webapp import Navigation
from lp.testing import TestCase


class TestNavigationDirective(TestCase):

    def test_default_layer(self):
        # By default all navigation classes are registered for
        # IDefaultBrowserLayer.
        directive = """
            <browser:navigation
                module="%(this)s" classes="ThingNavigation"/>
            """ % dict(this=this)
        xmlconfig.string(zcml_configure % directive)
        navigation = getMultiAdapter(
            (Thing(), DefaultBrowserLayer()), IBrowserPublisher, name='')
        self.assertIsInstance(navigation, ThingNavigation)

    def test_specific_layer(self):
        # If we specify a layer when registering a navigation class, it will
        # only be available on that layer.
        directive = """
            <browser:navigation
                module="%(this)s" classes="OtherThingNavigation"
                layer="%(this)s.IOtherLayer" />
            """ % dict(this=this)
        xmlconfig.string(zcml_configure % directive)
        self.assertRaises(
            ComponentLookupError,
            getMultiAdapter,
            (Thing(), DefaultBrowserLayer()), IBrowserPublisher, name='')

        navigation = getMultiAdapter(
            (Thing(), OtherLayer()), IBrowserPublisher, name='')
        self.assertIsInstance(navigation, OtherThingNavigation)

    def test_multiple_navigations_for_single_context(self):
        # It is possible to have multiple navigation classes for a given
        # context class as long as they are registered for different layers.
        directive = """
            <browser:navigation
                module="%(this)s" classes="ThingNavigation"/>
            <browser:navigation
                module="%(this)s" classes="OtherThingNavigation"
                layer="%(this)s.IOtherLayer" />
            """ % dict(this=this)
        xmlconfig.string(zcml_configure % directive)

        navigation = getMultiAdapter(
            (Thing(), DefaultBrowserLayer()), IBrowserPublisher, name='')
        other_navigation = getMultiAdapter(
            (Thing(), OtherLayer()), IBrowserPublisher, name='')
        self.assertNotEqual(navigation, other_navigation)

    def tearDown(self):
        TestCase.tearDown(self)
        cleanUp()


@implementer(IDefaultBrowserLayer)
class DefaultBrowserLayer:
    pass


class IThing(Interface):
    pass


@implementer(IThing)
class Thing(object):
    pass


class ThingNavigation(Navigation):
    usedfor = IThing


class OtherThingNavigation(Navigation):
    usedfor = IThing


class IOtherLayer(Interface):
    pass


@implementer(IOtherLayer)
class OtherLayer:
    pass


this = "lp.services.webapp.tests.test_navigation"
zcml_configure = """
    <configure xmlns:browser="http://namespaces.zope.org/browser">
      <include package="lp.services.webapp" file="meta.zcml" />
      %s
    </configure>
    """
