# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Client code for the branch filesystem endpoint.

This code talks to the internal XML-RPC server for the branch filesystem.
"""

__metaclass__ = type
__all__ = [
    'BlockingProxy',
    'BranchFileSystemClient',
    'NotInCache',
    'trap_fault',
    ]

from twisted.internet import defer
from twisted.web.xmlrpc import Fault


class BlockingProxy:

    def __init__(self, proxy):
        self._proxy = proxy

    def callRemote(self, method_name, *args):
        return getattr(self._proxy, method_name)(*args)


class NotInCache(Exception):
    """Raised when we try to get a path from the cache that's not present."""


class BranchFileSystemClient:
    """Wrapper for the authserver that caches responses for a particular user.

    This only wraps the methods that are used for serving branches via a
    Bazaar transport: createBranch, requestMirror and translatePath.

    In the normal course of operation, our Bazaar transport translates from
    "virtual branch identifier" (currently '~owner/product/name') to a branch
    ID. It does this many, many times for a single Bazaar operation. Thus, it
    makes sense to cache results from the authserver.
    """

    def __init__(self, authserver, user_id):
        """Construct a caching authserver.

        :param authserver: An XML-RPC proxy that implements callRemote.
        :param user_id: The database ID of the user who will be making these
            requests. An integer.
        """
        self._authserver = authserver
        self._cache = {}
        self._user_id = user_id

    def _getMatchedPart(self, path, transport_tuple):
        """Return the part of 'path' that the endpoint actually matched."""
        trailing_length = len(transport_tuple[2])
        if trailing_length == 0:
            matched_part = path
        else:
            matched_part = path[:-trailing_length]
        return matched_part.rstrip('/')

    def _addToCache(self, transport_tuple, path):
        (transport_type, data, trailing_path) = transport_tuple
        matched_part = self._getMatchedPart(path, transport_tuple)
        self._cache[matched_part] = (transport_type, data)
        return transport_tuple

    def _getFromCache(self, path):
        for object_path, (transport_type, data) in self._cache.iteritems():
            if path.startswith(object_path):
                trailing_path = path[len(object_path):].lstrip('/')
                return (transport_type, data, trailing_path)
        raise NotInCache(path)

    def createBranch(self, branch_path):
        """Create a branch on the authserver.

        This raises any Faults that might be raised by the authserver's
        `createBranch` method, so for more information see
        `IHostedBranchStorage.createBranch`.

        :param owner: The owner of the branch. A string that is the name of a
            Launchpad `IPerson`.
        :param product: The project that the branch belongs to. A string that
            is either '+junk' or the name of a Launchpad `IProduct`.
        :param branch: The name of the branch to create.

        :return: A `Deferred` that fires the ID of the created branch.
        """
        return defer.maybeDeferred(
            self._authserver.callRemote, 'createBranch', self._user_id,
            branch_path)

    def requestMirror(self, branch_id):
        """Mark a branch as needing to be mirrored.

        :param branch_id: The database ID of the branch.
        """
        return defer.maybeDeferred(
            self._authserver.callRemote, 'requestMirror', self._user_id,
            branch_id)

    def translatePath(self, path):
        """Translate 'path'."""
        try:
            return defer.succeed(self._getFromCache(path))
        except NotInCache:
            deferred = defer.maybeDeferred(
                self._authserver.callRemote, 'translatePath', self._user_id,
                path)
            deferred.addCallback(self._addToCache, path)
            return deferred



def trap_fault(failure, *fault_codes):
    """Trap a fault, based on fault code.

    :param failure: A Twisted L{Failure}.
    :param *fault_codes: XML-RPC fault codes.
    :raise Failure: if 'failure' is not a Fault failure, or if the fault code
        does not match the given codes.
    :return: The Fault if it matches one of the codes.
    """
    failure.trap(Fault)
    fault = failure.value
    if fault.faultCode in fault_codes:
        return fault
    raise failure
