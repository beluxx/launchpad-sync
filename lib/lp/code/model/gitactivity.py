# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository activity logs."""

__all__ = [
    'GitActivity',
    ]

import pytz
from storm.locals import (
    DateTime,
    Int,
    JSON,
    Reference,
    )
from zope.interface import implementer

from lp.code.enums import GitActivityType
from lp.code.interfaces.gitactivity import (
    IGitActivity,
    IGitActivitySet,
    )
from lp.registry.interfaces.person import (
    validate_person,
    validate_public_person,
    )
from lp.services.database.constants import DEFAULT
from lp.services.database.enumcol import DBEnum
from lp.services.database.stormbase import StormBase


@implementer(IGitActivity)
class GitActivity(StormBase):
    """See IGitActivity`."""

    __storm_table__ = 'GitActivity'

    id = Int(primary=True)

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    date_changed = DateTime(
        name='date_changed', tzinfo=pytz.UTC, allow_none=False)

    changer_id = Int(
        name='changer', allow_none=False, validator=validate_public_person)
    changer = Reference(changer_id, 'Person.id')

    changee_id = Int(
        name='changee', allow_none=True, validator=validate_person)
    changee = Reference(changee_id, 'Person.id')

    what_changed = DBEnum(
        name='what_changed', enum=GitActivityType, allow_none=False)

    old_value = JSON(name='old_value', allow_none=True)
    new_value = JSON(name='new_value', allow_none=True)

    def __init__(self, repository, changer, what_changed, changee=None,
                 old_value=None, new_value=None, date_changed=DEFAULT):
        super().__init__()
        self.repository = repository
        self.date_changed = date_changed
        self.changer = changer
        self.changee = changee
        self.what_changed = what_changed
        self.old_value = old_value
        self.new_value = new_value

    @property
    def changee_description(self):
        if self.changee is not None:
            return "~" + self.changee.name
        elif self.new_value is not None and "changee_type" in self.new_value:
            return self.new_value["changee_type"].lower()
        elif self.old_value is not None and "changee_type" in self.old_value:
            return self.old_value["changee_type"].lower()
        else:
            return None


def _make_rule_value(rule, position=None):
    return {
        "ref_pattern": rule.ref_pattern,
        "position": position if position is not None else rule.position,
        }


def _make_grant_value(grant):
    return {
        # If the grantee is a person, then we store that in
        # GitActivity.changee; this makes it visible to person merges and so
        # on.
        "changee_type": grant.grantee_type.title,
        "ref_pattern": grant.rule.ref_pattern,
        "can_create": grant.can_create,
        "can_push": grant.can_push,
        "can_force_push": grant.can_force_push,
        }


@implementer(IGitActivitySet)
class GitActivitySet:

    def logRuleAdded(self, rule, user):
        """See `IGitActivitySet`."""
        return GitActivity(
            rule.repository, user, GitActivityType.RULE_ADDED,
            new_value=_make_rule_value(rule))

    def logRuleChanged(self, old_rule, new_rule, user):
        """See `IGitActivitySet`."""
        return GitActivity(
            new_rule.repository, user, GitActivityType.RULE_CHANGED,
            old_value=_make_rule_value(old_rule),
            new_value=_make_rule_value(new_rule))

    def logRuleRemoved(self, rule, user):
        """See `IGitActivitySet`."""
        return GitActivity(
            rule.repository, user, GitActivityType.RULE_REMOVED,
            old_value=_make_rule_value(rule))

    def logRuleMoved(self, rule, old_position, new_position, user):
        """See `IGitActivitySet`."""
        return GitActivity(
            rule.repository, user, GitActivityType.RULE_MOVED,
            old_value=_make_rule_value(rule, position=old_position),
            new_value=_make_rule_value(rule, position=new_position))

    def logGrantAdded(self, grant, user):
        """See `IGitActivitySet`."""
        return GitActivity(
            grant.repository, user, GitActivityType.GRANT_ADDED,
            changee=grant.grantee,
            new_value=_make_grant_value(grant))

    def logGrantChanged(self, old_grant, new_grant, user):
        """See `IGitActivitySet`."""
        return GitActivity(
            new_grant.repository, user, GitActivityType.GRANT_CHANGED,
            changee=new_grant.grantee,
            old_value=_make_grant_value(old_grant),
            new_value=_make_grant_value(new_grant))

    def logGrantRemoved(self, grant, user):
        """See `IGitActivitySet`."""
        return GitActivity(
            grant.repository, user, GitActivityType.GRANT_REMOVED,
            changee=grant.grantee,
            old_value=_make_grant_value(grant))
