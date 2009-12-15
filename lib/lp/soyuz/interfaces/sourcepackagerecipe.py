# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = []

from lazr.restful.fields import Reference

from zope.interface import Interface

from zope.schema import Datetime, TextLine

from canonical.launchpad import _
from canonical.launchpad.validators.name import name_validator

from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.sourcepackagename import ISourcePackageName


class ISourcePackageRecipe(Interface):
    """ XXX """

    date_created = Datetime(required=True, readonly=True)
    date_last_modified = Datetime(required=True, readonly=True)

    registrant = Reference(IPerson, title=_("XXX"), readonly=True)
    owner = Reference(IPerson, title=_("XXX"))
    distroseries = Reference(IDistroSeries, title=_("XXX"))
    sourcepackagename = Reference(ISourcePackageName, title=_("XXX"))

    name = TextLine(
            title=_("Name"), required=True,
            constraint=name_validator,
            description=_("The name of this recipe."))

class ISourcePackageRecipeSource(Interface):
    """ XXX """

    def new(registrant, owner, distroseries, sourcepackagename, name, recipe):
        """ XXX """
