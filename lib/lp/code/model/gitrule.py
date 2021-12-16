# Copyright 2018-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository access rules."""

__all__ = [
    'GitRule',
    'GitRuleGrant',
    ]

from collections import (
    defaultdict,
    OrderedDict,
    )

from lazr.enum import DBItem
from lazr.restful.interfaces import (
    IFieldMarshaller,
    IJSONPublishable,
    )
from lazr.restful.utils import get_current_browser_request
import pytz
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Store,
    Unicode,
    )
from zope.component import (
    adapter,
    getMultiAdapter,
    getUtility,
    )
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.code.enums import (
    GitGranteeType,
    GitPermissionType,
    )
from lp.code.interfaces.gitactivity import IGitActivitySet
from lp.code.interfaces.gitrule import (
    describe_git_permissions,
    IGitNascentRule,
    IGitNascentRuleGrant,
    IGitRule,
    IGitRuleGrant,
    )
from lp.registry.interfaces.person import (
    IPerson,
    validate_person,
    validate_public_person,
    )
from lp.registry.model.person import Person
from lp.services.database.bulk import (
    load_referencing,
    load_related,
    )
from lp.services.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from lp.services.database.enumcol import DBEnum
from lp.services.database.stormbase import StormBase
from lp.services.fields import InlineObject
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.services.webapp.snapshot import notify_modified


def git_rule_modified(rule, event):
    """Update date_last_modified when a GitRule is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on Git repository rules.
    """
    if event.edited_fields:
        user = IPerson(event.user)
        getUtility(IGitActivitySet).logRuleChanged(
            event.object_before_modification, rule, user)
        removeSecurityProxy(rule).date_last_modified = UTC_NOW


@implementer(IGitRule, IJSONPublishable)
class GitRule(StormBase):
    """See `IGitRule`."""

    __storm_table__ = 'GitRule'

    id = Int(primary=True)

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    position = Int(name='position', allow_none=False)

    ref_pattern = Unicode(name='ref_pattern', allow_none=False)

    creator_id = Int(
        name='creator', allow_none=False, validator=validate_public_person)
    creator = Reference(creator_id, 'Person.id')

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name='date_last_modified', tzinfo=pytz.UTC, allow_none=False)

    def __init__(self, repository, position, ref_pattern, creator,
                 date_created):
        super().__init__()
        self.repository = repository
        self.position = position
        self.ref_pattern = ref_pattern
        self.creator = creator
        self.date_created = date_created
        self.date_last_modified = date_created
        get_property_cache(self).grants = []

    def __repr__(self):
        return "<GitRule '%s' for %s>" % (
            self.ref_pattern, self.repository.unique_name)

    def toDataForJSON(self, media_type):
        """See `IJSONPublishable`."""
        if media_type != "application/json":
            raise ValueError("Unhandled media type %s" % media_type)
        request = get_current_browser_request()
        field = InlineObject(schema=IGitNascentRule).bind(self)
        marshaller = getMultiAdapter((field, request), IFieldMarshaller)
        return marshaller.unmarshall(None, self)

    @cachedproperty
    def grants(self):
        """See `IGitRule`."""
        return list(Store.of(self).find(
            GitRuleGrant, GitRuleGrant.rule_id == self.id))

    def addGrant(self, grantee, grantor, can_create=False, can_push=False,
                 can_force_push=False, permissions=None):
        """See `IGitRule`."""
        if permissions is not None:
            if can_create or can_push or can_force_push:
                raise AssertionError(
                    "GitRule.addGrant takes either "
                    "can_create/can_push/can_force_push or permissions, not "
                    "both")
            can_create = GitPermissionType.CAN_CREATE in permissions
            can_push = GitPermissionType.CAN_PUSH in permissions
            can_force_push = GitPermissionType.CAN_FORCE_PUSH in permissions
        grant = GitRuleGrant(
            rule=self, grantee=grantee, can_create=can_create,
            can_push=can_push, can_force_push=can_force_push, grantor=grantor,
            date_created=DEFAULT)
        getUtility(IGitActivitySet).logGrantAdded(grant, grantor)
        del get_property_cache(self).grants
        return grant

    def _validateGrants(self, grants):
        """Validate a new iterable of access grants."""
        for grant in grants:
            if grant.grantee_type == GitGranteeType.PERSON:
                if grant.grantee is None:
                    raise ValueError(
                        "Permission grant for %s has grantee_type 'Person' "
                        "but no grantee" % self.ref_pattern)
            else:
                if grant.grantee is not None:
                    raise ValueError(
                        "Permission grant for %s has grantee_type '%s', "
                        "contradicting grantee ~%s" %
                        (self.ref_pattern, grant.grantee_type,
                         grant.grantee.name))

    def setGrants(self, grants, user):
        """See `IGitRule`."""
        self._validateGrants(grants)
        existing_grants = {
            (grant.grantee_type, grant.grantee): grant
            for grant in self.grants}
        new_grants = OrderedDict(
            ((grant.grantee_type, grant.grantee), grant)
            for grant in grants)

        for grant_key, grant in existing_grants.items():
            if grant_key not in new_grants:
                grant.destroySelf(user)

        for grant_key, new_grant in new_grants.items():
            grant = existing_grants.get(grant_key)
            if grant is None:
                new_grantee = (
                    new_grant.grantee
                    if new_grant.grantee_type == GitGranteeType.PERSON
                    else new_grant.grantee_type)
                grant = self.addGrant(
                    new_grantee, user, can_create=new_grant.can_create,
                    can_push=new_grant.can_push,
                    can_force_push=new_grant.can_force_push)
            else:
                edited_fields = []
                with notify_modified(grant, edited_fields):
                    for field in ("can_create", "can_push", "can_force_push"):
                        if getattr(grant, field) != getattr(new_grant, field):
                            setattr(grant, field, getattr(new_grant, field))
                            edited_fields.append(field)

    @staticmethod
    def preloadGrantsForRules(rules):
        """Preload the access grants related to an iterable of rules."""
        grants = load_referencing(GitRuleGrant, rules, ["rule_id"])
        grants_map = defaultdict(list)
        for grant in grants:
            grants_map[grant.rule_id].append(grant)
        for rule in rules:
            get_property_cache(rule).grants = grants_map[rule.id]
        load_related(Person, grants, ["grantee_id"])

    def destroySelf(self, user):
        """See `IGitRule`."""
        getUtility(IGitActivitySet).logRuleRemoved(self, user)
        for grant in self.grants:
            grant.destroySelf()
        rules = list(self.repository.rules)
        Store.of(self).remove(self)
        rules.remove(self)
        removeSecurityProxy(self.repository)._syncRulePositions(rules)


def git_rule_grant_modified(grant, event):
    """Update date_last_modified when a GitRuleGrant is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on Git repository grants.
    """
    if event.edited_fields:
        user = IPerson(event.user)
        getUtility(IGitActivitySet).logGrantChanged(
            event.object_before_modification, grant, user)
        removeSecurityProxy(grant).date_last_modified = UTC_NOW


class GitRuleGrantMixin:
    """Properties common to GitRuleGrant and GitNascentRuleGrant."""

    @property
    def permissions(self):
        permissions = set()
        if self.can_create:
            permissions.add(GitPermissionType.CAN_CREATE)
        if self.can_push:
            permissions.add(GitPermissionType.CAN_PUSH)
        if self.can_force_push:
            permissions.add(GitPermissionType.CAN_FORCE_PUSH)
        return frozenset(permissions)

    @permissions.setter
    def permissions(self, value):
        self.can_create = GitPermissionType.CAN_CREATE in value
        self.can_push = GitPermissionType.CAN_PUSH in value
        self.can_force_push = GitPermissionType.CAN_FORCE_PUSH in value


@implementer(IGitRuleGrant, IJSONPublishable)
class GitRuleGrant(StormBase, GitRuleGrantMixin):
    """See `IGitRuleGrant`."""

    __storm_table__ = 'GitRuleGrant'

    id = Int(primary=True)

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    rule_id = Int(name='rule', allow_none=False)
    rule = Reference(rule_id, 'GitRule.id')

    grantee_type = DBEnum(
        name='grantee_type', enum=GitGranteeType, allow_none=False)

    grantee_id = Int(
        name='grantee', allow_none=True, validator=validate_person)
    grantee = Reference(grantee_id, 'Person.id')

    can_create = Bool(name='can_create', allow_none=False)
    can_push = Bool(name='can_push', allow_none=False)
    can_force_push = Bool(name='can_force_push', allow_none=False)

    grantor_id = Int(
        name='grantor', allow_none=False, validator=validate_public_person)
    grantor = Reference(grantor_id, 'Person.id')

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name='date_last_modified', tzinfo=pytz.UTC, allow_none=False)

    def __init__(self, rule, grantee, can_create, can_push, can_force_push,
                 grantor, date_created):
        if isinstance(grantee, DBItem) and grantee.enum == GitGranteeType:
            if grantee == GitGranteeType.PERSON:
                raise ValueError(
                    "grantee may not be GitGranteeType.PERSON; pass a person "
                    "object instead")
            grantee_type = grantee
            grantee = None
        else:
            grantee_type = GitGranteeType.PERSON

        self.repository = rule.repository
        self.rule = rule
        self.grantee_type = grantee_type
        self.grantee = grantee
        self.can_create = can_create
        self.can_push = can_push
        self.can_force_push = can_force_push
        self.grantor = grantor
        self.date_created = date_created
        self.date_last_modified = date_created

    @property
    def combined_grantee(self):
        if self.grantee_type == GitGranteeType.PERSON:
            return self.grantee
        else:
            return self.grantee_type

    def __repr__(self):
        if self.grantee_type == GitGranteeType.PERSON:
            grantee_name = "~%s" % self.grantee.name
        else:
            grantee_name = self.grantee_type.title.lower()
        return "<GitRuleGrant [%s] to %s for %s:%s>" % (
            ", ".join(describe_git_permissions(self.permissions)),
            grantee_name, self.repository.unique_name, self.rule.ref_pattern)

    def toDataForJSON(self, media_type):
        """See `IJSONPublishable`."""
        if media_type != "application/json":
            raise ValueError("Unhandled media type %s" % media_type)
        request = get_current_browser_request()
        field = InlineObject(schema=IGitNascentRuleGrant).bind(self)
        marshaller = getMultiAdapter((field, request), IFieldMarshaller)
        return marshaller.unmarshall(None, self)

    def destroySelf(self, user=None):
        """See `IGitRuleGrant`."""
        if user is not None:
            getUtility(IGitActivitySet).logGrantRemoved(self, user)
        del get_property_cache(self.rule).grants
        Store.of(self).remove(self)


@implementer(IGitNascentRule)
class GitNascentRule:

    def __init__(self, ref_pattern, grants):
        self.ref_pattern = ref_pattern
        self.grants = grants

    def __repr__(self):
        return "<GitNascentRule '%s'>" % self.ref_pattern


@adapter(dict)
@implementer(IGitNascentRule)
def nascent_rule_from_dict(template):
    return GitNascentRule(**template)


@implementer(IGitNascentRuleGrant)
class GitNascentRuleGrant(GitRuleGrantMixin):

    def __init__(self, grantee_type, grantee=None, can_create=False,
                 can_push=False, can_force_push=False):
        self.grantee_type = grantee_type
        self.grantee = grantee
        self.can_create = can_create
        self.can_push = can_push
        self.can_force_push = can_force_push

    def __repr__(self):
        if self.grantee_type == GitGranteeType.PERSON:
            grantee_name = "~%s" % self.grantee.name
        else:
            grantee_name = self.grantee_type.title.lower()
        return "<GitNascentRuleGrant [%s] to %s>" % (
            ", ".join(describe_git_permissions(self.permissions)),
            grantee_name)


@adapter(dict)
@implementer(IGitNascentRuleGrant)
def nascent_rule_grant_from_dict(template):
    return GitNascentRuleGrant(**template)
