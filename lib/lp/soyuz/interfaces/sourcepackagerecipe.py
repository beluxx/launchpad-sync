# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface of the `SourcePackageRecipe` content type."""

__metaclass__ = type
__all__ = ['ISourcePackageRecipe']

from lazr.restful.fields import Reference

from zope.interface import Interface

from zope.schema import Datetime, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.validators.name import name_validator

from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.role import IHasOwner
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.sourcepackagename import ISourcePackageName


class ISourcePackageRecipe(IHasOwner):
    """An ISourcePackageRecipe describes how to build a source package.

    More precisely, it describes how to combine a number of branches into a
    debianized source tree.
    """

    date_created = Datetime(required=True, readonly=True)
    date_last_modified = Datetime(required=True, readonly=True)

    registrant = Reference(
        IPerson, title=_("The person who created this recipe"), readonly=True)
    owner = Reference(
        IPerson, title=_("The person or team who can edit this recipe"),
        readonly=False)
    distroseries = Reference(
        IDistroSeries, title=_("The distroseries this recipe will build a "
                               "source package for"),
        readonly=True)
    sourcepackagename = Reference(
        ISourcePackageName, title=_("The name of the source package this "
                                    "recipe will build a source package"),
        readonly=True)

    name = TextLine(
            title=_("Name"), required=True,
            constraint=name_validator,
            description=_("The name of this recipe."))

    recipe_text = Text(
        title=_("The text of the recipe."), required=True, readonly=False)

    def getReferencedBranches():
        """An iterator of the branches referenced by this recipe."""


class ISourcePackageRecipeSource(Interface):
    """A utility of this interface can be used to create and access recipes.
    """

    def new(registrant, owner, distroseries, sourcepackagename, name, builder_recipe):
        """Create an `ISourcePackageRecipe`."""
