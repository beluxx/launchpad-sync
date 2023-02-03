# Copyright 2011-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""BugSummary Storm database classes."""

__all__ = [
    "BugSummary",
    "CombineBugSummaryConstraint",
    "get_bugsummary_filter_for_user",
]

from storm.expr import SQL, And, Or, Select
from storm.properties import Bool, Int, Unicode
from storm.references import Reference
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.bugs.interfaces.bugsummary import IBugSummary, IBugSummaryDimension
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    BugTaskStatusSearch,
)
from lp.registry.interfaces.role import IPersonRoles
from lp.registry.model.accesspolicy import AccessPolicy, AccessPolicyGrant
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.milestone import Milestone
from lp.registry.model.person import Person
from lp.registry.model.product import Product
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase
from lp.services.database.stormexpr import WithMaterialized


@implementer(IBugSummary)
class BugSummary(StormBase):
    """BugSummary Storm database class."""

    __storm_table__ = "combinedbugsummary"

    id = Int(primary=True)
    count = Int()

    product_id = Int(name="product")
    product = Reference(product_id, Product.id)

    productseries_id = Int(name="productseries")
    productseries = Reference(productseries_id, ProductSeries.id)

    distribution_id = Int(name="distribution")
    distribution = Reference(distribution_id, Distribution.id)

    distroseries_id = Int(name="distroseries")
    distroseries = Reference(distroseries_id, DistroSeries.id)

    sourcepackagename_id = Int(name="sourcepackagename")
    sourcepackagename = Reference(sourcepackagename_id, SourcePackageName.id)

    ociproject_id = Int(name="ociproject")
    ociproject = Reference(ociproject_id, "OCIProject.id")

    milestone_id = Int(name="milestone")
    milestone = Reference(milestone_id, Milestone.id)

    status = DBEnum(name="status", enum=(BugTaskStatus, BugTaskStatusSearch))

    importance = DBEnum(name="importance", enum=BugTaskImportance)

    tag = Unicode()

    viewed_by_id = Int(name="viewed_by")
    viewed_by = Reference(viewed_by_id, Person.id)
    access_policy_id = Int(name="access_policy")
    access_policy = Reference(access_policy_id, AccessPolicy.id)

    has_patch = Bool()


@implementer(IBugSummaryDimension)
class CombineBugSummaryConstraint:
    """A class to combine two separate bug summary constraints.

    This is useful for querying on multiple related dimensions (e.g. milestone
    + sourcepackage) - and essential when a dimension is not unique to a
    context.
    """

    def __init__(self, *dimensions):
        self.dimensions = map(
            lambda x: removeSecurityProxy(x.getBugSummaryContextWhereClause()),
            dimensions,
        )

    def getBugSummaryContextWhereClause(self):
        """See `IBugSummaryDimension`."""
        return And(*self.dimensions)


def get_bugsummary_filter_for_user(user):
    """Build a Storm expression to filter BugSummary by visibility.

    :param user: The user for which visible rows should be calculated.
    :return: (with_clauses, where_clauses)
    """
    # Admins get to see every bug, everyone else only sees bugs
    # viewable by them-or-their-teams.
    # Note that because admins can see every bug regardless of
    # subscription they will see rather inflated counts. Admins get to
    # deal.
    public_filter = And(
        BugSummary.viewed_by_id == None, BugSummary.access_policy_id == None
    )
    if user is None:
        return [], [public_filter]
    elif IPersonRoles(user).in_admin:
        return [], []
    else:
        store = IStore(TeamParticipation)
        with_clauses = [
            WithMaterialized(
                "teams",
                store,
                Select(
                    TeamParticipation.teamID,
                    tables=[TeamParticipation],
                    where=(TeamParticipation.personID == user.id),
                ),
            ),
            WithMaterialized(
                "policies",
                store,
                Select(
                    AccessPolicyGrant.policy_id,
                    tables=[AccessPolicyGrant],
                    where=(
                        AccessPolicyGrant.grantee_id.is_in(
                            SQL("SELECT team FROM teams")
                        )
                    ),
                ),
            ),
        ]
        where_clauses = [
            Or(
                public_filter,
                BugSummary.viewed_by_id.is_in(SQL("SELECT team FROM teams")),
                BugSummary.access_policy_id.is_in(
                    SQL("SELECT policy FROM policies")
                ),
            )
        ]
        return with_clauses, where_clauses
