# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from collections import (
    deque,
    Iterable,
    )
import warnings
import weakref

from zope.app.security.principalregistry import UnauthenticatedPrincipal
from zope.browser.interfaces import IView
from zope.component import (
    getUtility,
    queryAdapter,
    )
from zope.interface import classProvides
from zope.proxy import removeAllProxies
from zope.publisher.interfaces import IApplicationRequest
from zope.security.checker import CheckerPublic
from zope.security.interfaces import ISecurityPolicy
from zope.security.management import (
    checkPermission as zcheckPermission,
    getInteraction,
    system_user,
    )
from zope.security.permission import (
    checkPermission as check_permission_is_registered,
    )
from zope.security.proxy import removeSecurityProxy
from zope.security.simplepolicies import (
    ParanoidSecurityPolicy,
    PermissiveSecurityPolicy,
    )

from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.readonly import is_read_only
from canonical.launchpad.webapp.interaction import InteractionExtras
from canonical.launchpad.webapp.interfaces import (
    AccessLevel,
    ILaunchpadContainer,
    ILaunchpadPrincipal,
    )
from canonical.launchpad.webapp.metazcml import ILaunchpadPermission
from canonical.lazr.canonicalurl import nearest_adapter
from canonical.lazr.interfaces import IObjectPrivacy
from lp.app.interfaces.security import IAuthorization


LAUNCHPAD_SECURITY_POLICY_CACHE_KEY = 'launchpad.security_policy_cache'


class LaunchpadSecurityPolicy(ParanoidSecurityPolicy):
    classProvides(ISecurityPolicy)

    def __init__(self, *participations):
        ParanoidSecurityPolicy.__init__(self, *participations)
        self.extras = InteractionExtras()

    def _checkRequiredAccessLevel(self, access_level, permission, object):
        """Check that the principal has the level of access required.

        Each permission specifies the level of access it requires (read or
        write) and all LaunchpadPrincipals have an access_level attribute. If
        the principal's access_level is not sufficient for that permission,
        returns False.
        """
        lp_permission = getUtility(ILaunchpadPermission, permission)
        if lp_permission.access_level == "write":
            required_access_level = [
                AccessLevel.WRITE_PUBLIC, AccessLevel.WRITE_PRIVATE,
                AccessLevel.DESKTOP_INTEGRATION]
            if access_level not in required_access_level:
                return False
        elif lp_permission.access_level == "read":
            # All principals have access to read data so there's nothing
            # to do here.
            pass
        else:
            raise AssertionError(
                "Unknown access level: %s" % lp_permission.access_level)
        return True

    def _checkPrivacy(self, access_level, object):
        """If the object is private, check that the principal can access it.

        If the object is private and the principal's access level doesn't give
        access to private objects, return False.  Return True otherwise.
        """
        private_access_levels = [
            AccessLevel.READ_PRIVATE, AccessLevel.WRITE_PRIVATE,
            AccessLevel.DESKTOP_INTEGRATION]
        if access_level in private_access_levels:
            # The user has access to private objects. Return early,
            # before checking whether the object is private, since
            # checking it might be expensive.
            return True
        return not IObjectPrivacy(object).is_private

    def _getPrincipalsAccessLevel(self, principal, object):
        """Get the principal's access level for the given object.

        If the principal's scope is None or the object is within the
        principal's scope, the original access level is returned.  Otherwise
        the access level is READ_PUBLIC.
        """
        if principal.scope is None:
            return principal.access_level
        else:
            container = nearest_adapter(object, ILaunchpadContainer)
            if container.isWithin(principal.scope):
                return principal.access_level
            else:
                return AccessLevel.READ_PUBLIC

    @block_implicit_flushes
    def checkPermission(self, permission, object):
        """Check the permission, object, user against the launchpad
        authorization policy.

        If the object is a view, then consider the object to be the view's
        context.

        If we are running in read-only mode, all permission checks are
        failed except for launchpad.View requests, which are checked
        as normal. All other permissions are used to protect write
        operations.

        Workflow:
        - If the principal is not None and its access level is not what is
          required by the permission, deny.
        - If the object to authorize is private and the principal has no
          access to private objects, deny.
        - If we have zope.Public, allow.  (But we shouldn't ever get this.)
        - If we have launchpad.AnyPerson and the principal is an
          ILaunchpadPrincipal then allow.
        - If the object has an IAuthorization named adapter, named
          after the permission, use that to check the permission.
        - Otherwise, deny.
        """
        # Shortcut in read-only mode. We have to do this now to avoid
        # accidentally using cached results. This will be important when
        # Launchpad automatically fails over to read-only mode when the
        # master database is unavailable.
        if is_read_only():
            lp_permission = getUtility(ILaunchpadPermission, permission)
            if lp_permission.access_level != "read":
                return False

        # If we have a view, get its context and use that to get an
        # authorization adapter.
        if IView.providedBy(object):
            objecttoauthorize = object.context
        else:
            objecttoauthorize = object
        if objecttoauthorize is None:
            # We will not be able to lookup an adapter for this, so we can
            # return False already.
            return False
        # Remove all proxies from object to authorize. The security proxy is
        # removed for obvious reasons but we also need to remove the location
        # proxy (which is used on apidoc.lp.dev) because otherwise we can't
        # create a weak reference to our object in our security policy cache.
        objecttoauthorize = removeAllProxies(objecttoauthorize)

        participations = [
            participation for participation in self.participations
            if participation.principal is not system_user]

        if len(participations) > 1:
            raise RuntimeError("More than one principal participating.")

        # The participation's cache of (object -> permission -> result), or
        # None if the participation does not support caching.
        participation_cache = None
        # A cache of (permission -> result) for objecttoauthorize, or None if
        # the participation does not support caching. This resides as a value
        # of participation_cache.
        object_cache = None

        if len(participations) == 0:
            principal = None
        else:
            participation = participations[0]
            if IApplicationRequest.providedBy(participation):
                participation_cache = participation.annotations.setdefault(
                    LAUNCHPAD_SECURITY_POLICY_CACHE_KEY,
                    weakref.WeakKeyDictionary())
                object_cache = participation_cache.setdefault(
                    objecttoauthorize, {})
                if permission in object_cache:
                    return object_cache[permission]
            principal = removeAllProxies(participation.principal)

        if (principal is not None and
            not isinstance(principal, UnauthenticatedPrincipal)):
            access_level = self._getPrincipalsAccessLevel(
                principal, objecttoauthorize)
            if not self._checkRequiredAccessLevel(
                access_level, permission, objecttoauthorize):
                return False
            if not self._checkPrivacy(access_level, objecttoauthorize):
                return False

        # The following two checks shouldn't be needed, strictly speaking,
        # because zope.Public is CheckerPublic, and the Zope security
        # machinery shortcuts this to always allow it. However, it is here as
        # a "belt and braces". It is also a bit of a lie: if the permission is
        # zope.Public, privacy and access levels (checked above) will be
        # irrelevant!
        if permission == 'zope.Public':
            return True
        if permission is CheckerPublic:
            return True

        if (permission == 'launchpad.AnyPerson' and
            ILaunchpadPrincipal.providedBy(principal)):
            return True

        # If there are delegated authorizations they must *all* be allowed
        # before permission to access objecttoauthorize is granted.
        result = all(
            iter_authorization(
                objecttoauthorize, permission, principal,
                participation_cache, breadth_first=True))

        # Cache the top-level result. Be warned that this result /may/ be
        # based on 10s or 100s of delegated authorization checks, and so even
        # small changes in the model data could invalidate this result.
        if object_cache is not None:
            object_cache[permission] = result

        return result


def iter_authorization(objecttoauthorize, permission, principal, cache,
                       breadth_first=True):
    """Work through `IAuthorization` adapters for `objecttoauthorize`.

    Adapters are permitted to delegate checks to other adapters, and this
    manages that delegation such that the minimum number of checks are made,
    subject to a breadth-first check of delegations.

    This also updates `cache` as it goes along, though `cache` can be `None`
    if no caching is desired. Only leaf values are cached; the results of a
    delegated authorization are not cached.
    """
    # Check if this calculation has already been done.
    if cache is not None and objecttoauthorize in cache:
        if permission in cache[objecttoauthorize]:
            # Result cached => yield and return.
            yield cache[objecttoauthorize][permission]
            return

    # Create a check_auth function to call checkAccountAuthenticated or
    # checkUnauthenticated as appropriate.
    if ILaunchpadPrincipal.providedBy(principal):
        account = principal.account
        check_auth = lambda authorization: (
            authorization.checkAccountAuthenticated(account))
    else:
        check_auth = lambda authorization: (
            authorization.checkUnauthenticated())

    # Each entry in queue should be an iterable of (object, permission)
    # tuples, upon which permission checks will be performed.
    queue = deque()
    enqueue = (queue.append if breadth_first else queue.appendleft)

    # Enqueue the starting object and permission.
    enqueue(((objecttoauthorize, permission),))

    while len(queue) != 0:
        for obj, permission in queue.popleft():
            # Unwrap object; see checkPermission for why.
            obj = removeAllProxies(obj)
            # First, check the cache.
            if cache is not None:
                if obj in cache and permission in cache[obj]:
                    # Result cached => yield and skip to the next.
                    yield cache[obj][permission]
                    continue
            # Get an IAuthorization for (obj, permission).
            authorization = queryAdapter(obj, IAuthorization, permission)
            if authorization is None:
                # No authorization adapter => denied.
                yield False
                continue
            # We have an authorization adapter, so check it. This is one of
            # the possibly-expensive bits that a cache can help with.
            result = check_auth(authorization)
            # Is the authorization adapter delegating to other objects?
            if isinstance(result, Iterable):
                enqueue(result)
                continue
            # We have a non-delegated result.
            if result is not True and result is not False:
                warnings.warn(
                    '%r returned %r (%r)' % (
                        authorization, result, type(result)))
                result = bool(result)
            # Update the cache if one has been provided.
            if cache is not None:
                if obj in cache:
                    cache[obj][permission] = result
                else:
                    cache[obj] = {permission: result}
            # Let the world know.
            yield result


def precache_permission_for_objects(participation, permission_name, objects):
    """Precaches the permission for the objects into the policy cache."""
    permission_cache = participation.annotations.setdefault(
        LAUNCHPAD_SECURITY_POLICY_CACHE_KEY,
        weakref.WeakKeyDictionary())
    for obj in objects:
        naked_obj = removeSecurityProxy(obj)
        obj_permission_cache = permission_cache.setdefault(naked_obj, {})
        obj_permission_cache[permission_name] = True


def check_permission(permission_name, context):
    """Like zope.security.management.checkPermission, but also ensures that
    permission_name is real permission.

    Raises ValueError if the permission doesn't exist.
    """
    # This will raise ValueError if the permission doesn't exist.
    check_permission_is_registered(context, permission_name)

    # Now call Zope's checkPermission.
    return zcheckPermission(permission_name, context)


def clear_cache():
    """clear current interaction's IApplicationRequests' authorization caches.
    """
    for p in getInteraction().participations:
        if IApplicationRequest.providedBy(p):
            # LaunchpadBrowserRequest provides a ``clearSecurityPolicyCache``
            # method, but it is not in an interface, and not implemented by
            # all classes that implement IApplicationRequest.
            if LAUNCHPAD_SECURITY_POLICY_CACHE_KEY in p.annotations:
                del p.annotations[LAUNCHPAD_SECURITY_POLICY_CACHE_KEY]


class LaunchpadPermissiveSecurityPolicy(PermissiveSecurityPolicy):

    def __init__(self, *participations):
        PermissiveSecurityPolicy.__init__(self, *participations)
        self.extras = InteractionExtras()
