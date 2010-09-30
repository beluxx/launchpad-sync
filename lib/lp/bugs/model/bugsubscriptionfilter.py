# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscriptionFilter']

from storm.base import Storm
from storm.locals import (
    Bool,
    Int,
    Reference,
    Unicode,
    )

from canonical.launchpad.interfaces.lpstorm import IStore
from lp.bugs.model.bugsubscriptionfilterstatus import (
    BugSubscriptionFilterStatus,
    )


class BugSubscriptionFilter(Storm):
    """A filter to specialize a *structural* subscription."""

    __storm_table__ = "BugSubscriptionFilter"

    id = Int(primary=True)

    structural_subscription_id = Int(
        "structuralsubscription", allow_none=False)
    structural_subscription = Reference(
        structural_subscription_id, "StructuralSubscription.id")

    find_all_tags = Bool(allow_none=False, default=False)
    include_any_tags = Bool(allow_none=False, default=False)
    exclude_any_tags = Bool(allow_none=False, default=False)

    other_parameters = Unicode()

    description = Unicode()

    def _get_statuses(self):
        """Return a frozenset of statuses to filter on."""
        return frozenset(
            IStore(BugSubscriptionFilterStatus).find(
                BugSubscriptionFilterStatus,
                BugSubscriptionFilterStatus.filter == self).values(
                BugSubscriptionFilterStatus.status))

    def _set_statuses(self, statuses):
        """Update the statuses to filter on.

        The statuses must be from the `BugTaskStatus` enum, but can be
        bundled in any iterable.
        """
        statuses = frozenset(statuses)
        current_statuses = self.statuses
        store = IStore(BugSubscriptionFilterStatus)
        # Add additional statuses.
        for status in statuses.difference(current_statuses):
            status_filter = BugSubscriptionFilterStatus()
            status_filter.filter = self
            status_filter.status = status
            store.add(status_filter)
        # Delete unused ones.
        store.find(
            BugSubscriptionFilterStatus,
            BugSubscriptionFilterStatus.filter == self,
            BugSubscriptionFilterStatus.status.is_in(
                current_statuses.difference(statuses))).remove()

    statuses = property(
        _get_statuses, _set_statuses, doc=(
            "A frozenset of statuses filtered on."))
