Finding the nearest adapter
===========================

The nearest_adapter() and nearest_context_with_adapter() will search the
navigation hierarchy for a content-type that supplies the requested
adaptation.


A sample hierarchy
------------------

First, we'll construct an example object hierarchy.

    >>> from zope.interface import implementer, Interface
    >>> from lp.services.webapp.interfaces import ICanonicalUrlData

    >>> class ICookbook(Interface):
    ...     pass

    >>> class IRecipe(Interface):
    ...     pass

    >>> @implementer(ICanonicalUrlData)
    ... class BaseContent:
    ...     def __init__(self, name, parent):
    ...         self.name = name
    ...         self.path = name
    ...         self.inside = parent
    ...         self.rootsite = None

    >>> class Root(BaseContent):
    ...     pass

    >>> @implementer(ICookbook)
    ... class Cookbook(BaseContent):
    ...     pass

    >>> @implementer(IRecipe)
    ... class Recipe(BaseContent):
    ...     pass

Here is the structure of our hierarchy:

    >>> root = BaseContent('', None)
    >>> cookbook = Cookbook('joy-of-cooking', root)
    >>> recipe = Recipe('fried-spam', cookbook)


Using nearest_adapter
---------------------

We'll try adapting our objects to a made-up interface, ICookingDirections.

    >>> class ICookingDirections(Interface):
    ...     """Something that tells us how to cook."""

    >>> @implementer(ICookingDirections)
    ... class CookingDirections:
    ...     def __init__(self, context):
    ...         self.context = context

Right now, none of our example objects can be turned into cooking
directions.

    >>> from lp.services.webapp.canonicalurl import (nearest_adapter,
    ...     nearest_context_with_adapter)

    >>> print(nearest_adapter(root, ICookingDirections))
    None
    >>> print(nearest_adapter(cookbook, ICookingDirections))
    None
    >>> print(nearest_adapter(recipe, ICookingDirections))
    None

The same holds true for nearest_context_with_adapter():

    >>> nearest_context_with_adapter(root, ICookingDirections)
    (None, None)

We'll make the "cookbook" object adaptable to ICookingDirections.

    >>> from zope.component import provideAdapter
    >>> provideAdapter(CookingDirections, [ICookbook], ICookingDirections)

    >>> ICookingDirections(cookbook)
    <...CookingDirections ...>

The nearest_adapter() function will look up the hierarchy for an object
that has the requested adaptation.

"recipe" does not provide ICookingDirections, but "cookbook" does, so
cookbook's adapter will be returned.

    >>> print(nearest_adapter(recipe, ICookingDirections))
    <...CookingDirections ...>

We can verify that the adapter is actually for the Cookbook using
nearest_adapter_with_context().

    >>> print(nearest_context_with_adapter(recipe, ICookingDirections))
    (<...Cookbook ...>, <...CookingDirections ...>)

Calling nearest_adapter() on "cookbook" itself will return the
CookingDirections:

    >>> print(nearest_adapter(cookbook, ICookingDirections))
    <...CookingDirections ...>

Calling nearest_adapter() on the hierarchy root returns nothing:
the root does not have the requested adaptation, and there are no higher
objects to search.

    >>> print(nearest_adapter(root, ICookingDirections))
    None


Named lookups with nearest_adapter()
....................................

nearest_adapter() also supports named adapter lookups.

First we need a named adapter to use:

    >>> from zope.component import queryAdapter

    >>> class ILabelledCookbook(Interface):
    ...     """ A recipe with a name."""

    >>> @implementer(ILabelledCookbook)
    ... class LabelledCookbook:
    ...     def __init__(self, context):
    ...         self.context = context

    >>> provideAdapter(LabelledCookbook, [ICookbook], ILabelledCookbook,
    ...     name='foo')

    >>> print(queryAdapter(cookbook, ILabelledCookbook))
    None
    >>> queryAdapter(cookbook, ILabelledCookbook, name='foo')
    <...LabelledCookbook ...>

nearest_adapter() behaves as it would with a regular adapter.  The named
adapter for the next highest object in the canonical URL is returned.
For a recipe, this is the adapter for the cookbook:

    >>> nearest_adapter(recipe, ILabelledCookbook, name='foo')
    <...LabelledCookbook ...>

We can verify that the adapter is for the Cookbook using
nearest_context_with_adapter():

    >>> print(nearest_context_with_adapter(
    ...     recipe, ILabelledCookbook, name='foo'))
    (<...Cookbook ...>, <...LabelledCookbook ...>)

And we can see that the adapter is not returned if we omit the 'name'
keyword argument:

    >>> print(nearest_adapter(recipe, ILabelledCookbook))
    None

If we search for the adapter on the cookbook object, the lookup works as
expected:

    >>> nearest_adapter(cookbook, ILabelledCookbook, name='foo')
    <...LabelledCookbook ...>

And searching for the adapter on the root object returns nothing:

    >>> print(nearest_adapter(root, ILabelledCookbook, name='foo'))
    None
