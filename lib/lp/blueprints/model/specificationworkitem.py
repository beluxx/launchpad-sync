# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "SpecificationWorkItem",
]

from datetime import timezone

from storm.locals import Bool, DateTime, Int, Reference, Unicode
from storm.store import Store
from zope.interface import implementer

from lp.blueprints.enums import SpecificationWorkItemStatus
from lp.blueprints.interfaces.specificationworkitem import (
    ISpecificationWorkItem,
    ISpecificationWorkItemSet,
)
from lp.registry.interfaces.person import validate_public_person
from lp.services.database.constants import DEFAULT
from lp.services.database.enumcol import DBEnum
from lp.services.database.stormbase import StormBase
from lp.services.helpers import backslashreplace


@implementer(ISpecificationWorkItem)
class SpecificationWorkItem(StormBase):
    __storm_table__ = "SpecificationWorkItem"
    __storm_order__ = "id"

    id = Int(primary=True)
    title = Unicode(allow_none=False)
    specification_id = Int(name="specification")
    specification = Reference(specification_id, "Specification.id")
    assignee_id = Int(name="assignee", validator=validate_public_person)
    assignee = Reference(assignee_id, "Person.id")
    milestone_id = Int(name="milestone")
    milestone = Reference(milestone_id, "Milestone.id")
    status = DBEnum(
        enum=SpecificationWorkItemStatus,
        allow_none=False,
        default=SpecificationWorkItemStatus.TODO,
    )
    date_created = DateTime(
        allow_none=False, default=DEFAULT, tzinfo=timezone.utc
    )
    sequence = Int(allow_none=False)
    deleted = Bool(allow_none=False, default=False)

    def __repr__(self):
        title = backslashreplace(self.title)
        assignee = getattr(self.assignee, "name", None)
        return "<SpecificationWorkItem [%s] %s: %s of %s>" % (
            assignee,
            title,
            self.status.name,
            self.specification,
        )

    def __init__(
        self, title, status, specification, assignee, milestone, sequence
    ):
        self.title = title
        self.status = status
        self.specification = specification
        self.assignee = assignee
        self.milestone = milestone
        self.sequence = sequence

    @property
    def is_complete(self):
        """See `ISpecificationWorkItem`."""
        return self.status == SpecificationWorkItemStatus.DONE


@implementer(ISpecificationWorkItemSet)
class SpecificationWorkItemSet:
    def unlinkMilestone(self, milestone):
        """See `ISpecificationWorkItemSet`."""
        Store.of(milestone).find(
            SpecificationWorkItem, milestone_id=milestone.id
        ).set(milestone_id=None)
