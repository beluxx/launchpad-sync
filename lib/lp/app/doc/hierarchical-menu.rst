Hierarchical menus
==================

The location bar aids users in navigating the depths of Launchpad.  It
is built from a chain of Breadcrumb objects built up from the URL
generation rules with some manual override.s

A simple object hierarchy
-------------------------

First, we need a hierarchy of objects to build upon:

    >>> from zope.component import getMultiAdapter, provideAdapter
    >>> from zope.interface import Interface, implementer

    >>> class ICookbook(Interface):
    ...     """A cookbook for holding recipes."""

    >>> class IRecipe(Interface):
    ...     """A recipe in a cookbook."""

    >>> class ICooker(Interface):
    ...     """A cooker."""

    >>> from lp.services.webapp.interfaces import ICanonicalUrlData
    >>> from lp.services.webapp.url import urlappend

    >>> @implementer(ICanonicalUrlData)
    ... class BaseContent:
    ...
    ...     def __init__(self, name, parent, path_prefix=None):
    ...         self.name = name
    ...         if path_prefix is not None:
    ...             self.path = urlappend(path_prefix, name)
    ...         else:
    ...             self.path = name
    ...         self.inside = parent
    ...         self.rootsite = None

    >>> class Root(BaseContent):
    ...     """ The site root."""

    >>> @implementer(ICookbook)
    ... class Cookbook(BaseContent):
    ...     pass

    >>> @implementer(IRecipe)
    ... class Recipe(BaseContent):
    ...     pass

    >>> @implementer(ICooker)
    ... class Cooker(BaseContent):
    ...     pass

Today we'll be cooking with Spam!

    >>> root = Root('', None)
    >>> cooker = Cooker('jamie', root, '+cooker')
    >>> cookbook = Cookbook('joy-of-cooking', root)
    >>> recipe = Recipe('spam', cookbook)


Discovering breadcrumbs
-----------------------

The Hierarchy class builds the breadcrumbs by finding the deepest object
in request.traversed_objects that can be adapted to IBreadcrumb, then
building the chain by following IBreadcrumb.inside or
ICanonicalUrlData.inside. Any object in the chain that can be adapted
to IBreadcrumb is added to the breadcrumbs list.

We'll add the objects to the request's list of traversed objects so
the hierarchy will discover them.

    >>> from lp.testing.menu import make_fake_request
    >>> request = make_fake_request(
    ...     'http://launchpad.test/joy-of-cooking/spam',
    ...     [root, cookbook, recipe])

The hierarchy's list of breadcrumbs is empty since none of the objects
have an IBreadcrumb adapter.

    >>> hierarchy = getMultiAdapter((recipe, request), name='+hierarchy')
    >>> hierarchy.items
    []

The ICookbook and IRecipe breadcrumb objects show up in the hierarchy after
IBreadcrumb adapters are registered for them.  The hierarchy builds a list of
breadcrumbs starting with the breadcrumb closest to the hierarchy root.

    >>> from lp.app.browser.launchpad import Hierarchy
    >>> from lp.services.webapp.breadcrumb import Breadcrumb

    # Monkey patch Hierarchy.makeBreadcrumbsForRequestedPage so that we don't
    # have to create fake views and other stuff to test breadcrumbs here. The
    # functionality provided by that method is tested in
    # webapp/tests/test_breadcrumbs.py.
    >>> make_breadcrumb_func = Hierarchy.makeBreadcrumbsForRequestedPage
    >>> Hierarchy.makeBreadcrumbsForRequestedPage = lambda self: []

    # Note that the Hierarchy assigns the breadcrumb's URL, but we need to
    # give it a valid .text attribute.
    >>> class TextualBreadcrumb(Breadcrumb):
    ...     @property
    ...     def text(self):
    ...         return self.context.name.capitalize().replace('-', ' ')

    >>> from lp.services.webapp.interfaces import IBreadcrumb

    >>> provideAdapter(TextualBreadcrumb, [ICookbook], IBreadcrumb)
    >>> provideAdapter(TextualBreadcrumb, [IRecipe], IBreadcrumb)

    >>> hierarchy = getMultiAdapter((recipe, request), name='+hierarchy')
    >>> hierarchy.items
    [<TextualBreadcrumb
        url='http://launchpad.test/joy-of-cooking'
        text='Joy of cooking'>,
     <TextualBreadcrumb
        url='http://launchpad.test/joy-of-cooking/spam'
        text='Spam'>]

The ICooker object contains a path prefix, a segment of the path that
does not correspond to any object, it's only used to split traversal
domains. The `Hierarchy` model copes fine with objects like that.

    >>> cooker_request = make_fake_request(
    ...     'http://launchpad.test/+cooker/jamie',
    ...     [root, cooker])

    >>> provideAdapter(TextualBreadcrumb, [ICooker], IBreadcrumb)

    >>> cooker_hierarchy = getMultiAdapter(
    ...     (cooker, cooker_request), name='+hierarchy')
    >>> cooker_hierarchy.items
    [<TextualBreadcrumb url='.../+cooker/jamie' text='Jamie'>]

An IBreadcrumb can override ICanonicalUrlData.inside with its inside
attribute.

    >>> class ParentedTextualBreadcrumb(TextualBreadcrumb):
    ...     inside = cookbook
    >>> provideAdapter(ParentedTextualBreadcrumb, [ICooker], IBreadcrumb)
    >>> cooker_hierarchy = getMultiAdapter(
    ...     (cooker, cooker_request), name='+hierarchy')
    >>> cooker_hierarchy.items
    [<TextualBreadcrumb url='.../joy-of-cooking' text='Joy of cooking'>,
     <ParentedTextualBreadcrumb url='.../+cooker/jamie' text='Jamie'>]

    >>> provideAdapter(TextualBreadcrumb, [ICooker], IBreadcrumb)

Displaying breadcrumbs
----------------------

Breadcrumbs are only displayed if there is more than one breadcrumb, as
otherwise the breadcrumb will simply replicate the context.title heading
above it.

    >>> len(hierarchy.items)
    2
    >>> hierarchy.display_breadcrumbs
    True

    >>> cooker_hierarchy = getMultiAdapter(
    ...     (cooker, cooker_request), name='+hierarchy')
    >>> len(cooker_hierarchy.items)
    1
    >>> cooker_hierarchy.display_breadcrumbs
    False

Additionally, if the view implements IMajorHeadingView then the breadcrumbs
will not be displayed.

    >>> ham_recipe = Recipe('ham', cookbook)
    >>> ham_request = make_fake_request(
    ...     'http://launchpad.test/joy-of-cooking/ham',
    ...     [root, cookbook, ham_recipe])

    >>> ham_hierarchy = getMultiAdapter(
    ...     (ham_recipe, ham_request), name='+hierarchy')
    >>> hierarchy.display_breadcrumbs
    True

    >>> from zope.interface import alsoProvides
    >>> from lp.app.interfaces.headings import IMajorHeadingView
    >>> alsoProvides(ham_recipe, IMajorHeadingView)
    >>> ham_hierarchy.display_breadcrumbs
    False


Building IBreadcrumb objects
----------------------------

The construction of breadcrumb objects is handled by an IBreadcrumb adapter,
which adapts a context object and produces an IBreadcrumb object for that
context.  The default adapter provides the url attribute, but the breadcrumb's
text must be overridden in subclasses.

    >>> from zope.interface.verify import verifyObject
    >>> from lp.services.webapp.interfaces import IBreadcrumb
    >>> breadcrumb = Breadcrumb(cookbook)
    >>> verifyObject(IBreadcrumb, breadcrumb)
    True
    >>> print(breadcrumb.text)
    None
    >>> print(breadcrumb.url)
    http://launchpad.test/joy-of-cooking

As said above, the breadcrumb's attributes can be overridden with subclassing
and Python properties.

    >>> class DynamicBreadcrumb(Breadcrumb):
    ...     @property
    ...     def text(self):
    ...         return self.context.name.capitalize().replace('-', ' ')

    >>> breadcrumb = DynamicBreadcrumb(cookbook)
    >>> breadcrumb
    <DynamicBreadcrumb
        url='http://launchpad.test/joy-of-cooking'
        text='Joy of cooking'>


Customizing the hierarchy
-------------------------

We can customize the hierarchy itself by changing the list of objects
and URLs that it uses to construct the breadcrumbs list.

The Hierarchy object should *not* construct the Breadcrumb objects
itself.  It should let the IBreadcrumbBuilder handle it: this ensures
consistency across the site.

    >>> class CustomHierarchy(Hierarchy):
    ...     @property
    ...     def objects(self):
    ...         return [recipe]

    >>> spammy_hierarchy = CustomHierarchy(root, request)
    >>> spammy_hierarchy.items
    [<TextualBreadcrumb
        url='http://launchpad.test/joy-of-cooking/spam'
        text='Spam'>]


Rendering the list
------------------

The Hierarchy object is responsible for rendering the HTML for the
location bar.

    >>> from lp.services.beautifulsoup import BeautifulSoup
    >>> from lp.testing.pages import extract_text

    # Borrowed from lp.testing.pages.print_location()
    >>> def print_hierarchy(html):
    ...     soup = BeautifulSoup(html)
    ...     hierarchy = soup.find(attrs={'class': 'breadcrumbs'}).find_all(
    ...         recursive=False)
    ...     segments = [extract_text(step) for step in hierarchy]
    ...     print('Location:', ' > '.join(segments))

    >>> markup = hierarchy.render()
    >>> print_hierarchy(markup)
    Location: Joy of cooking > Spam

The items in the breadcrumbs are linked, except for the last one which
represents the current location.

    >>> print(markup)
    <ol itemprop="breadcrumb" class="breadcrumbs">
      <li>
        <a href="http://launchpad.test/joy-of-cooking">Joy of cooking</a>
      </li>
      <li>
          Spam
      </li>
    </ol>

The Launchpad Homepage displays no items in its location bar.  We are
considered to be on the home page if there are no breadcrumbs.

    # Simulate a visit to the site root
    >>> request = make_fake_request('http://launchpad.test/', [root])
    >>> homepage_hierarchy = getMultiAdapter(
    ...     (root, request), name='+hierarchy')

    >>> homepage_hierarchy.items
    []

    >>> print(homepage_hierarchy.render().strip())
    <BLANKLINE>


Put the monkey patched method back.

    >>> Hierarchy.makeBreadcrumbsForRequestedPage = make_breadcrumb_func
