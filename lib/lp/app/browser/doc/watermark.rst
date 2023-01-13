=======================
The "watermark" heading
=======================

The watermark is the image and heading used on all the main Launchpad
pages. The image and heading are determined by Hierarchy from the
IRootContext for the context object.


Watermark headings
==================

Hierarchy.heading() is used when you want a heading for the nearest
object that implements IRootContext.

    >>> from lp.app.browser.launchpad import Hierarchy
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> class TrivialView:
    ...     __name__ = "+trivial"
    ...
    ...     def __init__(self, context):
    ...         self.context = context
    ...
    >>> def get_hierarchy(obj, viewcls=TrivialView):
    ...     req = LaunchpadTestRequest()
    ...     view = viewcls(obj)
    ...     req.traversed_objects.append(view.context)
    ...     req.traversed_objects.append(view)
    ...     return Hierarchy(view, req)
    ...

Products directly implement IRootContext.

    >>> widget = factory.makeProduct(displayname="Widget")
    >>> print(get_hierarchy(widget).heading())
    <h...><a...>Widget</a></h...>

A series of the product still show the product watermark.

    >>> dev_focus = widget.development_focus
    >>> print(get_hierarchy(dev_focus).heading())
    <h...><a...>Widget</a></h...>

ProjectGroups also directly implement IRootContext ...

    >>> kde = factory.makeProject(displayname="KDE")
    >>> print(get_hierarchy(kde).heading())
    <h...><a...>KDE</a></h...>

... as do distributions ...

    >>> mint = factory.makeDistribution(displayname="Mint Linux")
    >>> print(get_hierarchy(mint).heading())
    <h...><a...>Mint Linux</a></h...>

... and people ...

    >>> eric = factory.makePerson(displayname="Eric the Viking")
    >>> print(get_hierarchy(eric).heading())
    <h...><a...>Eric the Viking</a></h...>

... and sprints.

    >>> sprint = factory.makeSprint(title="Launchpad Epic")
    >>> print(get_hierarchy(sprint).heading())
    <h...><a...>Launchpad Epic</a></h...>

If there is no root context defined for the object, then the heading is
'Launchpad.net' (differentiating from the Launchpad project within
Launchpad.net).

    >>> machine = factory.makeCodeImportMachine()
    >>> print(get_hierarchy(machine).heading())
    <h...><span...>Launchpad.net</span></h...>

Any HTML in the context title will be escaped to avoid XSS vulnerabilities.

    >>> person = factory.makePerson(
    ...     displayname="Fubar<br/><script>alert('XSS')</script>"
    ... )
    >>> print(get_hierarchy(person).heading())  # noqa
    <h...><a...>Fubar&lt;br/&gt;&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;</a></h...>


Watermark images
================

The image for the watermark is determined effectively by context/image:logo.

    >>> print(get_hierarchy(dev_focus).logo())
    <a href="..."><img ... src="/@@/product-logo" /></a>

    >>> print(get_hierarchy(eric).logo())
    <a...><img ... src="/@@/person-logo" /></a>

If there is no root context, the Launchpad logo is shown.

    >>> print(get_hierarchy(machine).logo())
    <img ... src="/@@/launchpad-logo" />


Heading level
=============

The watermark heading is shown above the application tabs, in either H1 level
or H2 level.  The heading level is determined by the view.  For the index view
of the context, H1 is used.  For all non-index pages, i.e. subpages, H2 is
used.

The choice of heading level is controlled by a marker interface on the view.
Normally, the view class does not implement the marker interface, meaning it
is not the index page of the context.  In this case the heading is rendered in
H2.

    >>> print(get_hierarchy(widget).heading())
    <h2...><a...>Widget</a></h2>

If the view class implements IMajorHeadingView, then this is the index page
for the context and the heading is rendered in H1.

    >>> from zope.interface import implementer
    >>> from lp.app.interfaces.headings import IMajorHeadingView
    >>> @implementer(IMajorHeadingView)
    ... class HeadingView(TrivialView):
    ...     pass
    ...
    >>> print(get_hierarchy(widget, viewcls=HeadingView).heading())
    <h1...><a...>Widget</a></h1>
