# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Personal access tokens."""

__all__ = [
    "AccessToken",
    "AccessTokenTargetMixin",
    ]

from datetime import (
    datetime,
    timedelta,
    )
import hashlib

import pytz
from storm.databases.postgres import JSON
from storm.expr import (
    And,
    Cast,
    Or,
    Select,
    SQL,
    Update,
    )
from storm.locals import (
    DateTime,
    Int,
    Reference,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.code.interfaces.gitcollection import IAllGitRepositories
from lp.code.interfaces.gitrepository import IGitRepository
from lp.registry.model.teammembership import TeamParticipation
from lp.services.auth.enums import AccessTokenScope
from lp.services.auth.interfaces import (
    IAccessToken,
    IAccessTokenSet,
    )
from lp.services.database.constants import UTC_NOW
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.stormbase import StormBase


@implementer(IAccessToken)
class AccessToken(StormBase):
    """See `IAccessToken`."""

    __storm_table__ = "AccessToken"

    id = Int(primary=True)

    date_created = DateTime(
        name="date_created", tzinfo=pytz.UTC, allow_none=False)

    _token_sha256 = Unicode(name="token_sha256", allow_none=False)

    owner_id = Int(name="owner", allow_none=False)
    owner = Reference(owner_id, "Person.id")

    description = Unicode(name="description", allow_none=False)

    git_repository_id = Int(name="git_repository", allow_none=False)
    git_repository = Reference(git_repository_id, "GitRepository.id")

    _scopes = JSON(name="scopes", allow_none=False)

    date_last_used = DateTime(
        name="date_last_used", tzinfo=pytz.UTC, allow_none=True)
    date_expires = DateTime(
        name="date_expires", tzinfo=pytz.UTC, allow_none=True)

    revoked_by_id = Int(name="revoked_by", allow_none=True)
    revoked_by = Reference(revoked_by_id, "Person.id")

    resolution = timedelta(minutes=10)

    def __init__(self, secret, owner, description, target, scopes,
                 date_expires=None):
        """Construct an `AccessToken`."""
        self._token_sha256 = hashlib.sha256(secret.encode()).hexdigest()
        self.owner = owner
        self.description = description
        if IGitRepository.providedBy(target):
            self.git_repository = target
        else:
            raise TypeError("Unsupported target: {!r}".format(target))
        self.scopes = scopes
        self.date_created = UTC_NOW
        self.date_expires = date_expires

    @property
    def target(self):
        """See `IAccessToken`."""
        return self.git_repository

    @property
    def scopes(self):
        """See `IAccessToken`."""
        return [
            AccessTokenScope.getTermByToken(scope).value
            for scope in self._scopes]

    @scopes.setter
    def scopes(self, scopes):
        """See `IAccessToken`."""
        self._scopes = [scope.title for scope in scopes]

    def updateLastUsed(self):
        """See `IAccessToken`."""
        store = IMasterStore(AccessToken)
        store.execute(Update(
            {AccessToken.date_last_used: UTC_NOW},
            where=And(
                # Skip the update if the AccessToken row is already locked,
                # for example by a concurrent request using the same token.
                AccessToken.id.is_in(SQL(
                    "SELECT id FROM AccessToken WHERE id = ? "
                    "FOR UPDATE SKIP LOCKED", params=(self.id,))),
                # Only update the last-used date every so often, to avoid
                # bloat.
                Or(
                    AccessToken.date_last_used == None,
                    AccessToken.date_last_used <
                        UTC_NOW - Cast(self.resolution, 'interval'))),
            table=AccessToken))
        store.invalidate(self)

    @property
    def is_expired(self):
        now = datetime.now(pytz.UTC)
        return self.date_expires is not None and self.date_expires <= now

    def revoke(self, revoked_by):
        """See `IAccessToken`."""
        self.date_expires = UTC_NOW
        self.revoked_by = revoked_by


@implementer(IAccessTokenSet)
class AccessTokenSet:

    def new(self, secret, owner, description, target, scopes,
            date_expires=None):
        """See `IAccessTokenSet`."""
        store = IStore(AccessToken)
        token = AccessToken(
            secret, owner, description, target, scopes,
            date_expires=date_expires)
        store.add(token)
        return token

    def getBySecret(self, secret):
        """See `IAccessTokenSet`."""
        return IStore(AccessToken).find(
            AccessToken,
            _token_sha256=hashlib.sha256(secret.encode()).hexdigest()).one()

    def findByOwner(self, owner):
        """See `IAccessTokenSet`."""
        return IStore(AccessToken).find(AccessToken, owner=owner)

    def findByTarget(self, target, visible_by_user=None):
        """See `IAccessTokenSet`."""
        clauses = []
        if IGitRepository.providedBy(target):
            clauses.append(AccessToken.git_repository == target)
            if visible_by_user is not None:
                collection = getUtility(IAllGitRepositories).visibleByUser(
                    visible_by_user).ownedByTeamMember(visible_by_user)
                ids = collection.getRepositoryIds()
                clauses.append(Or(
                    AccessToken.owner_id.is_in(Select(
                        TeamParticipation.teamID,
                        where=TeamParticipation.person == visible_by_user.id)),
                    AccessToken.git_repository_id.is_in(
                        removeSecurityProxy(ids)._get_select())))
        else:
            raise TypeError("Unsupported target: {!r}".format(target))
        clauses.append(Or(
            AccessToken.date_expires == None,
            AccessToken.date_expires > UTC_NOW))
        return IStore(AccessToken).find(AccessToken, *clauses).order_by(
            AccessToken.date_created)

    def getByTargetAndID(self, target, token_id, visible_by_user=None):
        """See `IAccessTokenSet`."""
        return self.findByTarget(target, visible_by_user=visible_by_user).find(
            id=token_id).one()


class AccessTokenTargetMixin:
    """Mix this into classes that implement `IAccessTokenTarget`."""

    def getAccessTokens(self, visible_by_user=None):
        """See `IAccessTokenTarget`."""
        return getUtility(IAccessTokenSet).findByTarget(
            self, visible_by_user=visible_by_user)
