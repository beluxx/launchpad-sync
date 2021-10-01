# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for linking Specifications and Branches."""

__all__ = [
    "ISpecificationBranch",
    "ISpecificationBranchSet",
    ]

from lazr.restful.declarations import (
    export_operation_as,
    export_write_operation,
    exported,
    exported_as_webservice_entry,
    operation_for_version,
    )
from lazr.restful.fields import (
    Reference,
    ReferenceChoice,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import Int

from lp import _
from lp.blueprints.interfaces.specification import ISpecification
from lp.code.interfaces.branch import IBranch
from lp.registry.interfaces.person import IPerson


@exported_as_webservice_entry(as_of="beta")
class ISpecificationBranch(Interface):
    """A branch linked to a specification."""

    id = Int(title=_("Specification Branch #"))
    specification = exported(
        ReferenceChoice(
            title=_("Blueprint"), vocabulary="Specification",
            required=True,
            readonly=True, schema=ISpecification), as_of="beta")
    branch = exported(
        ReferenceChoice(
            title=_("Branch"),
            vocabulary="Branch",
            required=True,
            schema=IBranch), as_of="beta")

    datecreated = Attribute("The date on which I was created.")
    registrant = exported(
        Reference(
            schema=IPerson, readonly=True, required=True,
            title=_("The person who linked the bug to the branch")),
        as_of="beta")

    @export_operation_as('delete')
    @export_write_operation()
    @operation_for_version('beta')
    def destroySelf():
        """Destroy this specification branch link"""


class ISpecificationBranchSet(Interface):
    """Methods that work on the set of all specification branch links."""

    def getSpecificationBranchesForBranches(branches, user):
        """Return a sequence of ISpecificationBranch instances associated with
        the given branches.

        Only return instances that are visible to the user.
        """
