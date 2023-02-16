ZCML Directives
===============

We have a bunch of custom zcml directives in Launchpad.

Canonical URLs
--------------

See canonical_url.rst for information and tests of the lp:url directive.


A zcml context for zcml directive unittests
-------------------------------------------

This is a context that collects actions and has a __repr__ for use in
tests that shows a pretty-printed representation of the actions.

We have to add the 'kw' arg for the EditFormDirective tests, but it isn't
important, so we just discard it.


    >>> import re, pprint
    >>> atre = re.compile(" at [0-9a-fA-Fx]+")
    >>> class Context:
    ...     actions = ()
    ...
    ...     def action(self, discriminator, callable, args, kw=None):
    ...         self.actions += ((discriminator, callable, args),)
    ...
    ...     def __repr__(self):
    ...         stream = StringIO()
    ...         pprinter = pprint.PrettyPrinter(stream=stream, width=60)
    ...         pprinter.pprint(self.actions)
    ...         r = stream.getvalue()
    ...         return ("".join(atre.split(r))).strip()
    ...

The code to this is actually repeated all through the Zope 3 unit tests for
zcml directives. :-(


Setting up some interfaces and objects to test with
---------------------------------------------------

We'll put an interface in lp.testing.IFoo, and set the
default view for the IFooLayer layer.

    >>> from zope.component import queryMultiAdapter
    >>> import lp.testing
    >>> from zope.interface import Interface, implementer
    >>> class IFoo(Interface):
    ...     pass
    ...
    >>> class IFooLayer(Interface):
    ...     pass
    ...
    >>> lp.testing.IFoo = IFoo
    >>> lp.testing.IFooLayer = IFooLayer

    >>> @implementer(IFoo)
    ... class FooObject:
    ...     pass
    ...
    >>> fooobject = FooObject()
    >>> @implementer(IFooLayer)
    ... class Request:
    ...     pass
    ...
    >>> request = Request()

    >>> class FooView:
    ...     def __call__(self):
    ...         return "FooView was called"
    ...
    >>> lp.testing.FooView = FooView


Overriding the browser:page directive
-------------------------------------

We override browser:page to allow us to specify the facet that the
page is associated with.

First, a unit test of the overridden directive.

    >>> from lp.services.webapp.metazcml import page
    >>> context = Context()
    >>> context.info = "INFO"

Name some variables to mirror the names used as arguments.

    >>> name = "NAME"
    >>> permission = "PERMISSION"
    >>> for_ = "FOR_"
    >>> facet = "FACET"
    >>> page(context, name, permission, for_, facet=facet)

Look for the SimpleLaunchpadViewClass in the data structure above, and check
its __launchpad_facetname__ attribute.

    >>> from zope.security.proxy import isinstance
    >>> def get_simplelaunchpadviewclass(actions_tuple):
    ...     for o in actions_tuple:
    ...         if isinstance(o, tuple):
    ...             o = get_simplelaunchpadviewclass(o)
    ...         if (
    ...             hasattr(o, "__name__")
    ...             and o.__name__ == "SimpleLaunchpadViewClass"
    ...         ):
    ...             return o
    ...     return None
    ...
    >>> cls = get_simplelaunchpadviewclass(context.actions)
    >>> cls
    <class 'zope.browserpage.metaconfigure.SimpleLaunchpadViewClass'>
    >>> print(cls.__launchpad_facetname__)
    FACET

Next, a functional/integration test of the overridden directive.

    >>> print(queryMultiAdapter((fooobject, request), name="+whatever"))
    None
    >>> print(queryMultiAdapter((fooobject, request), name="+mandrill"))
    None

    >>> from zope.configuration import xmlconfig
    >>> zcmlcontext = xmlconfig.string(
    ...     """
    ... <configure xmlns:browser="http://namespaces.zope.org/browser"
    ...     package="lp.services">
    ...   <include file="webapp/meta-overrides.zcml" />
    ...   <browser:page
    ...     for="lp.testing.IFoo"
    ...     name="+whatever"
    ...     permission="zope.Public"
    ...     class="lp.testing.FooView"
    ...     attribute="__call__"
    ...     facet="the_evil_facet"
    ...     layer="lp.testing.IFooLayer"
    ...     />
    ...   <browser:page
    ...     for="lp.testing.IFoo"
    ...     name="+mandrill"
    ...     permission="zope.Public"
    ...     template="../../lp/app/templates/base-layout.pt"
    ...     facet="another-mister-lizard"
    ...     layer="lp.testing.IFooLayer"
    ...     />
    ... </configure>
    ... """
    ... )

    >>> whatever_view = queryMultiAdapter(
    ...     (fooobject, request), name="+whatever"
    ... )

    >>> print(whatever_view.__class__.__name__)
    FooView
    >>> print(whatever_view.__launchpad_facetname__)
    the_evil_facet
    >>> mandrill_view = queryMultiAdapter(
    ...     (fooobject, request), name="+mandrill"
    ... )

    >>> print(mandrill_view.__class__.__name__)
    SimpleViewClass from ...base-layout.pt
    >>> print(mandrill_view.__launchpad_facetname__)
    another-mister-lizard


Overriding the browser:pages directive
--------------------------------------

We override browser:pages to allow us to specify the facet that each
page is associated with.

First, a unit test of the overridden directive.

    >>> from lp.services.webapp.metazcml import pages
    >>> context = Context()
    >>> context.info = "INFO"

Name some variables to mirror the names used as arguments.

    >>> for_ = "FOR_"
    >>> permission = "PERMISSION"

    >>> name = "NAME"
    >>> facet = "FACET"

The facet specified for the outer pages element will be used only when a
facet is not specified for the inner page.

    >>> P = pages(context, permission, for_, facet="OUTERFACET")
    >>> P.page(context, name, facet=facet)
    >>> P.page(context, "OTHER NAME")

Look for the SimpleLaunchpadViewClass in the data structure above, and check
its __launchpad_facetname__ attribute.

    >>> cls = get_simplelaunchpadviewclass(context.actions)
    >>> cls
    <class 'zope.browserpage.metaconfigure.SimpleLaunchpadViewClass'>
    >>> print(cls.__launchpad_facetname__)
    FACET
    >>> cls2 = context.actions[3][2][1]
    >>> cls2
    <class 'zope.browserpage.metaconfigure.SimpleLaunchpadViewClass'>
    >>> print(cls2.__launchpad_facetname__)
    OUTERFACET

Next, a functional/integration test of the overridden directive.

    >>> print(queryMultiAdapter((fooobject, request), name="+whatever2"))
    None

    >>> zcmlcontext = xmlconfig.string(
    ...     """
    ... <configure xmlns:browser="http://namespaces.zope.org/browser"
    ...     package="lp.services">
    ...   <include file="webapp/meta-overrides.zcml" />
    ...   <browser:pages
    ...     for="lp.testing.IFoo"
    ...     layer="lp.testing.IFooLayer"
    ...     class="lp.testing.FooView"
    ...     facet="outerspace"
    ...     permission="zope.Public">
    ...     <browser:page
    ...         name="+whatever2"
    ...         attribute="__call__"
    ...         facet="another_evil_facet"
    ...         />
    ...     <browser:page
    ...         name="+whatever3"
    ...         attribute="__call__"
    ...         />
    ...   </browser:pages>
    ... </configure>
    ... """
    ... )

    >>> whatever2_view = queryMultiAdapter(
    ...     (fooobject, request), name="+whatever2"
    ... )
    >>> print(whatever2_view.__class__.__name__)
    FooView
    >>> print(whatever2_view.__launchpad_facetname__)
    another_evil_facet

    >>> whatever3_view = queryMultiAdapter(
    ...     (fooobject, request), name="+whatever3"
    ... )
    >>> print(whatever3_view.__class__.__name__)
    FooView
    >>> print(whatever3_view.__launchpad_facetname__)
    outerspace


Overriding zope:configure to add a facet attribute
--------------------------------------------------

We override the grouping directive zope:configure to add a 'facet' attribute
that can be inherited by all of the directives it contains.

    >>> from lp.services.webapp.metazcml import GroupingFacet
    >>> context = Context()

Name some variables to mirror the names used as arguments.

    >>> facet = "whole-file-facet"

    >>> gc = GroupingFacet(context, facet=facet)
    >>> print(gc.facet)
    whole-file-facet

Next, a functional/integration test of the overridden directive.

    >>> print(queryMultiAdapter((fooobject, request), name="+impliedfacet"))
    None

    >>> zcmlcontext = xmlconfig.string(
    ...     """
    ... <configure xmlns="http://namespaces.zope.org/zope"
    ...            xmlns:browser="http://namespaces.zope.org/browser"
    ...            xmlns:lp="http://namespaces.canonical.com/lp"
    ...            package="lp.services">
    ...   <include file="webapp/meta.zcml" />
    ...   <include file="webapp/meta-overrides.zcml" />
    ...   <lp:facet facet="whole-facet">
    ...     <browser:page
    ...       for="lp.testing.IFoo"
    ...       name="+impliedfacet"
    ...       permission="zope.Public"
    ...       class="lp.testing.FooView"
    ...       attribute="__call__"
    ...       layer="lp.testing.IFooLayer"
    ...       />
    ...   </lp:facet>
    ... </configure>
    ... """
    ... )

    >>> impliedfacet_view = queryMultiAdapter(
    ...     (fooobject, request), name="+impliedfacet"
    ... )
    >>> print(impliedfacet_view.__class__.__name__)
    FooView
    >>> print(impliedfacet_view.__launchpad_facetname__)
    whole-facet


Overriding zope:permission
--------------------------

The permissions used in Launchpad must also specify the level of access
they require ('read' or 'write'), so our zope:permission directive will
register an ILaunchpadPermission with the given access_level instead of
an IPermission.

    >>> zcmlcontext = xmlconfig.string(
    ...     """
    ... <configure xmlns="http://namespaces.zope.org/zope"
    ...     i18n_domain="canonical">
    ...   <include file="lib/lp/services/webapp/meta-overrides.zcml" />
    ...   <permission id="foo.bar" title="Foo Bar" access_level="read" />
    ... </configure>
    ... """
    ... )
    >>> from lp.services.webapp.metazcml import ILaunchpadPermission
    >>> from lp.testing import verifyObject
    >>> permission = getUtility(ILaunchpadPermission, "foo.bar")
    >>> verifyObject(ILaunchpadPermission, permission)
    True
    >>> print(permission.access_level)
    read


Cleaning up the interfaces and objects to test with
---------------------------------------------------

Clean up the interfaces we created for testing with.

    >>> del lp.testing.IFoo
    >>> del lp.testing.IFooLayer
    >>> del lp.testing.FooView
