# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0702

"""The Launchpad code hosting file system.

The way Launchpad presents branches is very different from the way it stores
them. Externally, branches are reached using URLs that look like
<schema>://launchpad.net/~owner/product/branch-name. Internally, they are
stored by branch ID. Branch 1 is stored at 00/00/00/01 and branch 10 is stored
at 00/00/00/0A. Further, these branches might not be stored on the same
physical machine.

This means that our services need to translate the external paths into
internal paths.

We also want to let users create new branches on Launchpad simply by pushing
them up. We want Launchpad to detect when a branch has been changed and update
our internal mirror.

This means our services must detect events like "make directory" and "unlock
branch", translate them into Launchpad operations like "create branch" and
"request mirror" and then actually perform those operations.

So, we have a `LaunchpadServer` which implements the core operations --
translate a path, make a branch and request a mirror -- in terms of virtual
paths.

This server does most of its work by delegating to a `LaunchpadBranch` object.
This object can be constructed from a virtual path and then operated on. It in
turn delegates to the "authserver", an internal XML-RPC server that actually
talks to the database. We cache requests to the authserver using
`CachingAuthserverClient`, in order to speed things up a bit.

We hook the `LaunchpadServer` into Bazaar by implementing a
`VirtualTransport`, a `bzrlib.transport.Transport` that wraps all of its
operations so that they are translated by an object that implements
`translateVirtualPath`.

This virtual transport isn't quite enough, since it only does dumb path
translation. We also need to be able to interpret filesystem events in terms
of Launchpad branches. To do this, we provide a `LaunchpadTransport` that
hooks into operations like `mkdir` and ask the `LaunchpadServer` to make a
branch if appropriate.
"""

__metaclass__ = type
__all__ = [
    'LaunchpadServer',
    'LaunchpadTransport',
    'set_up_logging',
    ]

import logging
import os
import xmlrpclib

from bzrlib.errors import (
    BzrError, InProcessTransport, NoSuchFile, PermissionDenied,
    TransportNotPossible)
from bzrlib import trace, urlutils
from bzrlib.transport import (
    get_transport,
    register_transport,
    Server,
    Transport,
    unregister_transport,
    )

from twisted.internet import defer
from twisted.python import failure
from twisted.web.xmlrpc import Fault

from canonical.authserver.interfaces import (
    NOT_FOUND_FAULT_CODE, PERMISSION_DENIED_FAULT_CODE, READ_ONLY)

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.bazaarfs import (
    ALLOWED_DIRECTORIES, FORBIDDEN_DIRECTORY_ERROR, is_lock_directory)
from canonical.config import config
from canonical.twistedsupport.loggingsupport import set_up_oops_reporting


def get_path_segments(path, maximum_segments=-1):
    """Break up the given path into segments.

    If 'path' ends with a trailing slash, then the final empty segment is
    ignored.
    """
    return path.strip('/').split('/', maximum_segments)


class _NotFilter(logging.Filter):
    """A Filter that only allows records that do *not* match.

    A _NotFilter initialized with "A.B" will allow "C", "A.BB" but not allow
    "A.B", "A.B.C" etc.
    """

    def filter(self, record):
        return not logging.Filter.filter(self, record)


def set_up_logging(configure_oops_reporting=False):
    """Set up logging for the smart server.

    This sets up a debugging handler on the 'codehosting' logger, makes sure
    that things logged there won't go to stderr (necessary because of
    bzrlib.trace shenanigans) and then returns the 'codehosting' logger.

    In addition, if configure_oops_reporting is True, install a
    Twisted log observer that ensures unhandled exceptions get
    reported as OOPSes.
    """
    log = logging.getLogger('codehosting')

    if config.codehosting.debug_logfile is not None:
        # Create the directory that contains the debug logfile.
        parent_dir = os.path.dirname(config.codehosting.debug_logfile)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        assert os.path.isdir(parent_dir), (
            "%r should be a directory" % parent_dir)

        # Messages logged to 'codehosting' are stored in the debug_logfile.
        handler = logging.FileHandler(config.codehosting.debug_logfile)
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s %(levelname)-8s %(name)s\t%(message)s'))
        handler.setLevel(logging.DEBUG)
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.CRITICAL)

    # Don't log 'codehosting' messages to stderr.
    if getattr(trace, '_stderr_handler', None) is not None:
        trace._stderr_handler.addFilter(_NotFilter('codehosting'))

    if configure_oops_reporting:
        set_up_oops_reporting('codehosting')

    return log


class BranchNotFound(BzrError):
    """Raised when on translating a virtual path for a non-existent branch."""

    _fmt = ("Could not find id for branch ~%(owner)s/%(product)s/%(name)s.")


class NotABranchPath(BzrError):
    """Raised when we cannot translate a virtual path to a branch.

    In particular, this is raised when there is some intrinsic deficiency in
    the path itself.
    """

    _fmt = ("Could not translate %(virtual_path)r to branch. %(reason)s")


class NotEnoughInformation(NotABranchPath):
    """Raised when there's not enough information in the path."""

    def __init__(self, virtual_path):
        NotABranchPath.__init__(
            self, virtual_path=virtual_path, reason="Not enough information.")


class InvalidOwnerDirectory(NotABranchPath):
    """Raised when the owner directory is invalid.

    This generally means that it doesn't start with a tilde (~).
    """

    def __init__(self, virtual_path):
        NotABranchPath.__init__(
            self, virtual_path=virtual_path,
            reason="Path must start with a user or team directory.")


class CachingAuthserverClient:
    """Wrapper for the authserver that caches responses for a particular user.

    This only wraps the methods that are used for serving branches via a
    Bazaar transport: createBranch, getBranchInformation and requestMirror.

    In the normal course of operation, our Bazaar transport translates from
    "virtual branch identifier" (currently '~owner/product/name') to a branch
    ID. It does this many, many times for a single Bazaar operation. Thus, it
    makes sense to cache results from the authserver.
    """

    def __init__(self, authserver, user_id):
        """Construct a caching authserver.

        :param authserver: A blocking XML-RPC proxy, usually an instance of
            `xmlrpclib.ServerProxy`
        :param user_id: The database ID of the user who will be making these
            requests. An integer.
        """
        self._authserver = authserver
        self._branch_info_cache = {}
        self._user_id = user_id

    def createBranch(self, owner, product, branch):
        """Create a branch on the authserver.

        This raises any Faults that might be raised by the authserver's
        `createBranch` method, so for more information see
        `IHostedBranchStorage.createBranch`.

        :param owner: The owner of the branch. A string that is the name of a
            Launchpad `IPerson`.
        :param product: The project that the branch belongs to. A string that
            is either '+junk' or the name of a Launchpad `IProduct`.
        :param branch: The name of the branch to create.

        :return: The ID of the created branch.
        """
        deferred = defer.maybeDeferred(
            self._authserver.createBranch, self._user_id, owner, product,
            branch)

        def cb(branch_id):
            # Clear the cache for this branch. We *could* populate it with
            # (branch_id, 'w'), but then we'd be building in more assumptions
            # about the authserver.
            self._branch_info_cache[(owner, product, branch)] = None
            # XXX: JonathanLange 2008-04-23: This logic should be moved to the
            # authserver. test_make_product_directory_for_nonexistent_product
            # and test_mkdir_not_team_member_error (in test_filesystem) both
            # fail without this check. Those tests should be moved (or copied)
            # to the authserver level at the same time that this check is.
            if branch_id == '':
                raise xmlrpclib.Fault(
                    PERMISSION_DENIED_FAULT_CODE,
                    'Cannot create branch: ~%s/%s/%s'
                    % (owner, product, branch))
            return branch_id

        return deferred.addCallback(cb)

    def getBranchInformation(self, owner, product, branch):
        """Get branch information from the authserver.

        :param owner: The owner of the branch. A string that is the name of a
            Launchpad `IPerson`.
        :param product: The project that the branch belongs to. A string that
            is either '+junk' or the name of a Launchpad `IProduct`.
        :param branch: The name of the branch that we are interested in.

        :return: (branch_id, permissions), where 'permissions' is WRITABLE if
            the current user can write to the branch, and READ_ONLY if
            they cannot. If the branch doesn't exist, return ('', ''). The
            "current user" is the user ID passed to the constructor.
        """
        branch_info = self._branch_info_cache.get((owner, product, branch))
        if branch_info is not None:
            deferred = defer.succeed(branch_info)
        else:
            deferred = defer.maybeDeferred(
                self._authserver.getBranchInformation, self._user_id, owner,
                product, branch)
            def add_to_cache(branch_info):
                self._branch_info_cache[
                    (owner, product, branch)] = branch_info
                return branch_info
            deferred.addCallback(add_to_cache)
        return deferred

    def requestMirror(self, branch_id):
        """Mark a branch as needing to be mirrored.

        :param branch_id: The database ID of the branch.
        """
        return defer.maybeDeferred(
            self._authserver.requestMirror, self._user_id, branch_id)


class LaunchpadBranch:
    """A branch on Launchpad.

    This abstractly represents a branch on Launchpad without exposing details
    of the naming of Launchpad branches. It contains and maintains the
    knowledge of how a virtual path, such as '~owner/product/branch' is
    translated into the underlying storage systems.

    It also exposes operations on Launchpad branches that we in turn expose
    via the codehosting system. Namely, creating a branch and requesting that
    a branch be mirrored.
    """

    @classmethod
    def from_virtual_path(cls, authserver, virtual_path):
        """Construct a LaunchpadBranch from a virtual path.

        :param authserver: An XML-RPC client to the Launchpad authserver.
            This is used to get information about the branch and to perform
            database operations on the branch.
        :param virtual_path: A public path to a branch, or to a file or
            directory within a branch.

        :raise NotABranchPath: If `virtual_path` cannot be translated into a
            (potential) path to a branch. See also `NotEnoughInformation`
            and `InvalidOwnerDirectory`.

        :return: (launchpad_branch, rest_of_path), where `launchpad_branch`
            is an instance of LaunchpadBranch that represents the branch at
            the virtual path, and `rest_of_path` is a path within that branch.
        """
        segments = get_path_segments(virtual_path, 3)
        # If we don't have at least an owner, product and name, then we don't
        # have enough information for a branch.
        if len(segments) < 3:
            raise NotEnoughInformation(virtual_path)
        # If we have only an owner, product, name tuple, append an empty path.
        if len(segments) == 3:
            segments.append('')
        user_dir, product, name, path = segments
        # The Bazaar client will look for a .bzr directory in the owner and
        # product directories to see if there's a shared repository. There
        # won't be, so we should treat this case the same as trying to access
        # a branch without enough information.
        if '.bzr' in (user_dir, product, name):
            raise NotEnoughInformation(virtual_path)
        if not user_dir.startswith('~'):
            raise InvalidOwnerDirectory(virtual_path)
        return cls(authserver, user_dir[1:], product, name), path

    def __init__(self, authserver, owner, product, name):
        """Construct a LaunchpadBranch object.

        In general, don't call this directly, use
        `LaunchpadBranch.from_virtual_path` instead. This prevents assumptions
        about branch naming spreading throughout the code.

        :param authserver: An XML-RPC client to the Launchpad authserver.
            This is used to get information about the branch and to perform
            database operations on the branch.
        :param owner: The owner of the branch. A string that is the name of a
            Launchpad `IPerson`.
        :param product: The project that the branch belongs to. A string that
            is either '+junk' or the name of a Launchpad `IProduct`.
        :param branch: The name of the branch.
        """
        self._authserver = authserver
        self._owner = owner
        self._product = product
        self._name = name

    def checkPath(self, path_on_branch):
        """Raise an error if `path_on_branch` is not valid.

        This allows us to enforce a certain level of policy about what goes
        into a branch directory on Launchpad. Specifically, we do not allow
        arbitrary files at the top-level, we only allow Bazaar control
        directories, and backups of same.

        :raise PermissionDenied: if `path_on_branch` is forbidden.
        """
        if path_on_branch == '':
            return
        segments = get_path_segments(path_on_branch)
        if segments[0] not in ALLOWED_DIRECTORIES:
            raise PermissionDenied(
                FORBIDDEN_DIRECTORY_ERROR % (segments[0],))

    def create(self):
        """Create a branch in the database.

        :raise TransportNotPossible: If the branch owner or product does not
            exist.
        :raise PermissionDenied: If the branch cannot be created in the
            database. This might indicate that the branch already exists, or
            that its creation is forbidden by a policy.
        """
        deferred = self._authserver.createBranch(
            self._owner, self._product, self._name)

        def convert_fault(failure):
            failure.trap(Fault)
            fault = failure.value
            if fault.faultCode == NOT_FOUND_FAULT_CODE:
                # One might think that it would make sense to raise
                # NoSuchFile here, but that makes the client do "clever"
                # things like say "Parent directory of
                # bzr+ssh://bazaar.launchpad.dev/~noone/firefox/branch
                # does not exist.  You may supply --create-prefix to
                # create all leading parent directories."  Which is just
                # misleading.
                raise TransportNotPossible(fault.faultString)
            elif fault.faultCode == PERMISSION_DENIED_FAULT_CODE:
                raise PermissionDenied(fault.faultString)
            else:
                raise

        return deferred.addErrback(convert_fault)

    def ensureUnderlyingPath(self, transport):
        """Ensure that the directory for the branch exists on the transport.
        """
        deferred = self.getRealPath('')
        deferred.addErrback(lambda failure: failure.trap(BranchNotFound))
        deferred.addCallback(
            lambda real_path: ensure_base(transport.clone(real_path)))
        return deferred

    def getRealPath(self, path_on_branch):
        """Return the 'real' path to a path within this branch.

        :param path_on_branch: A path within this branch.

        :raise BranchNotFound: if the branch does not exist.
        :raise PermissionDenied: if `path_on_branch` is forbidden.

        :return: A path relative to the base directory where all branches
            are stored. This path will look like '00/AB/02/43/.bzr/foo', where
            'AB0243' is the database ID of the branch expressed in hex and
            '.bzr/foo' is `path_on_branch`.
        """
        try:
            self.checkPath(path_on_branch)
        except PermissionDenied:
            return defer.fail(failure.Failure())
        deferred = self.getID()
        return deferred.addCallback(
            lambda branch_id: '/'.join(
                [branch_id_to_path(branch_id), path_on_branch]))

    def getID(self):
        """Return the database ID of this branch.

        :raise BranchNotFound: if the branch does not exist.
        :return: the database ID of the branch, an integer.
        """
        return self._getInfo().addCallback(lambda branch_info: branch_info[0])

    def getPermissions(self):
        """Return the permissions that the current user has for this branch.

        :raise BranchNotFound: if the branch does not exist.
        :return: WRITABLE if the user can write to the branch, READ_ONLY
            otherwise.
        """
        return self._getInfo().addCallback(lambda branch_info: branch_info[1])

    def _getInfo(self):
        deferred = self._authserver.getBranchInformation(
            self._owner, self._product, self._name)
        def check_branch_id(branch_info):
            (branch_id, permissions) = branch_info
            if branch_id == '':
                raise BranchNotFound(
                    owner=self._owner, product=self._product, name=self._name)
            return branch_info
        return deferred.addCallback(check_branch_id)

    def requestMirror(self):
        """Request that the branch be mirrored as soon as possible.

        :raise BranchNotFound: if the branch does not exist.
        """
        deferred = self.getID()
        deferred.addCallback(self._authserver.requestMirror)
        return deferred


class LaunchpadServer(Server):
    """Bazaar Server for Launchpad branches."""

    def __init__(self, authserver, user_id, hosting_transport,
                 mirror_transport):
        """Construct a LaunchpadServer.

        :param authserver: An xmlrpclib.ServerProxy that points to the
            authserver.
        :param user_id: A login ID for the user who is accessing branches.
        :param hosting_transport: A Transport pointing to the root of where
            the branches are actually stored.
        :param mirror_transport: A Transport pointing to the root of where
            branches are mirrored to.
        """
        # bzrlib's Server class does not have a constructor, so we cannot
        # safely upcall it.
        # pylint: disable-msg=W0231
        user_id = authserver.getUser(user_id)['id']
        self._authserver = CachingAuthserverClient(authserver, user_id)
        self._backing_transport = hosting_transport
        self._mirror_transport = get_transport(
            'readonly+' + mirror_transport.base)
        self._is_set_up = False

    def _getBranch(self, virtual_path):
        return LaunchpadBranch.from_virtual_path(
            self._authserver, virtual_path)

    def createBranch(self, virtual_path):
        """Make a new directory for the given virtual path.

        If `virtual_path` is a branch directory, create the branch in the
        database, then create a matching directory on the backing transport.

        :param virtual_path: A virtual path to be translated.

        :raise NotABranchPath: If `virtual_path` does not have at least a
            valid path to a branch.
        :raise TransportNotPossible: If the branch owner or product does not
            exist.
        :raise PermissionDenied: If the branch cannot be created in the
            database. This might indicate that the branch already exists, or
            that its creation is forbidden by a policy.
        """
        branch, ignored = self._getBranch(virtual_path)
        deferred = branch.create()

        def ensure_path(branch_id):
            deferred = branch.ensureUnderlyingPath(self._backing_transport)
            return deferred.addCallback(lambda ignored: branch_id)
        return deferred.addCallback(ensure_path)

    def requestMirror(self, virtual_path):
        """Request that the branch that owns 'virtual_path' be mirrored.

        :param virtual_path: A virtual path to be translated.

        :raise NotABranchPath: If `virtual_path` does not have at least a
            valid path to a branch.
        """
        branch, ignored = self._getBranch(virtual_path)
        branch.requestMirror()

    def translateVirtualPath(self, virtual_path):
        """Translate 'virtual_path' into a transport and sub-path.

        :param virtual_path: A virtual path to be translated.

        :raise NotABranchPath: If `virtual_path` does not have at least a
            valid path to a branch.
        :raise BranchNotFound: If `virtual_path` looks like a path to a
            branch, but there is no branch in the database that matches.
        :raise NoSuchFile: If `virtual_path` is *inside* a non-existing
            branch.
        :raise PermissionDenied: if the path on the branch is forbidden.

        :return: (transport, path_on_transport)
        """
        branch, path = self._getBranch(virtual_path)

        deferred = branch.getRealPath(path)

        def branch_not_found(failure):
            failure.trap(BranchNotFound)
            if path == '':
                # We are trying to translate a branch path that doesn't exist.
                return failure
            else:
                # We are trying to translate a path within a branch that
                # doesn't exist.
                raise NoSuchFile(virtual_path)

        deferred.addErrback(branch_not_found)

        def get_transport(real_path):
            deferred = branch.getPermissions()
            def got_permissions(permissions):
                if permissions == READ_ONLY:
                    return self._mirror_transport
                else:
                    transport = self._backing_transport
                    deferred = branch.ensureUnderlyingPath(transport)
                    deferred.addCallback(lambda ignored: transport)
                    return deferred
            deferred.addCallback(got_permissions)
            deferred.addCallback(lambda transport: (transport, real_path))
            return deferred

        return deferred.addCallback(get_transport)

    def _factory(self, url):
        """Construct a transport for the given URL. Used by the registry."""
        assert url.startswith(self.scheme)
        return LaunchpadTransport(self, url)

    def get_url(self):
        """Return the URL of this server.

        The URL is of the form 'lp-<object_id>:///', where 'object_id' is
        id(self). This ensures that we can have LaunchpadServer objects for
        different users, different backing transports and, theoretically,
        different authservers.

        See Server.get_url.
        """
        return self.scheme

    def setUp(self):
        """See Server.setUp."""
        self.scheme = 'lp-%d:///' % id(self)
        register_transport(self.scheme, self._factory)
        self._is_set_up = True

    def tearDown(self):
        """See Server.tearDown."""
        if not self._is_set_up:
            return
        self._is_set_up = False
        unregister_transport(self.scheme, self._factory)


class VirtualTransport(Transport):
    """A transport for a virtual file system.

    Assumes that it has a 'server' which implements 'translateVirtualPath'.
    This method is expected to take an absolute virtual path and translate it
    into a real transport and a path on that transport.
    """

    def __init__(self, server, url):
        self.server = server
        Transport.__init__(self, url)

    def _extractResult(self, deferred):
        failures = []
        successes = []
        deferred.addCallbacks(successes.append, failures.append)
        if len(failures) == 1:
            failures[0].raiseException()
        elif len(successes) == 1:
            return successes[0]
        else:
            raise AssertionError("%r has not fired yet." % (deferred,))

    def external_url(self):
        # There's no real external URL to this transport. It's heavily
        # dependent on the process.
        raise InProcessTransport(self)

    def _abspath(self, relpath):
        """Return the absolute path to `relpath` without the schema."""
        return urlutils.joinpath(
            self.base[len(self.server.scheme)-1:], relpath)

    def _getUnderylingTransportAndPath(self, relpath):
        """Return the underlying transport and path for `relpath`."""
        virtual_path = self._abspath(relpath)
        return self.server.translateVirtualPath(virtual_path)

    def _call(self, method_name, relpath, *args, **kwargs):
        """Call a method on the backing transport, translating relative,
        virtual paths to filesystem paths.

        If 'relpath' translates to a path that we only have read-access to,
        then the method will be called on the backing transport decorated with
        'readonly+'.
        """
        def call_method((transport, path)):
            method = getattr(transport, method_name)
            return method(path, *args, **kwargs)

        deferred = self._getUnderylingTransportAndPath(relpath)
        deferred.addCallback(call_method)
        return self._extractResult(deferred)

    # Transport methods
    def abspath(self, relpath):
        return urlutils.join(self.base, relpath)

    def append_file(self, relpath, f, mode=None):
        return self._call('append_file', relpath, f, mode)

    def clone(self, relpath=None):
        if relpath is None:
            return self.__class__(self.server, self.base)
        else:
            return self.__class__(
                self.server, urlutils.join(self.base, relpath))

    def delete(self, relpath):
        return self._call('delete', relpath)

    def delete_tree(self, relpath):
        return self._call('delete_tree', relpath)

    def get(self, relpath):
        return self._call('get', relpath)

    def get_bytes(self, relpath):
        return self._call('get_bytes', relpath)

    def has(self, relpath):
        return self._call('has', relpath)

    def iter_files_recursive(self):
        deferred = self._getUnderylingTransportAndPath('.')
        def iter_files((transport, path)):
            return transport.clone(path).iter_files_recursive()
        deferred.addCallback(iter_files)
        return self._extractResult(deferred)

    def listable(self):
        deferred = self._getUnderylingTransportAndPath('.')
        def listable((transport, path)):
            return transport.listable()
        deferred.addCallback(listable)
        return self._extractResult(deferred)

    def list_dir(self, relpath):
        return self._call('list_dir', relpath)

    def lock_read(self, relpath):
        return self._call('lock_read', relpath)

    def lock_write(self, relpath):
        return self._call('lock_write', relpath)

    def mkdir(self, relpath, mode=None):
        return self._call('mkdir', relpath, mode)

    def put_file(self, relpath, f, mode=None):
        return self._call('put_file', relpath, f, mode)

    def local_realPath(self, relpath):
        # This method should return an absolute path (not URL) that points to
        # `relpath` and dereferences any symlinks. The absolute path should be
        # on this transport.
        #
        # Here, we assume that the underlying transport has no symlinks
        # (Bazaar transports cannot create symlinks). This means that we can
        # just return the absolute path.
        return self._abspath(relpath)

    def rename(self, rel_from, rel_to):
        to_deferred = self._getUnderylingTransportAndPath(rel_to)
        from_deferred = self._getUnderylingTransportAndPath(rel_from)
        deferred = defer.gatherResults([to_deferred, from_deferred])

        def do_rename(((to_transport, to_path), (from_transport, from_path))):
            if to_transport is not from_transport:
                raise TransportNotPossible(
                    'cannot move between underlying transports')
            return getattr(from_transport, 'rename')(from_path, to_path)

        deferred.addCallback(do_rename)
        return self._extractResult(deferred)

    def rmdir(self, relpath):
        return self._call('rmdir', relpath)

    def stat(self, relpath):
        return self._call('stat', relpath)

    def writeChunk(self, relpath, offset, data):
        return self._call('writeChunk', relpath, offset, data)


class LaunchpadTransport(VirtualTransport):
    """Virtual transport to implement the Launchpad VFS for branches.

    This implements a few hooks to translate filesystem operations (such as
    making a certain kind of directory) into Launchpad operations (such as
    creating a branch in the database).

    It also converts the Launchpad-specific translation errors (such as 'not a
    valid branch path') into Bazaar errors (such as 'no such file').
    """

    def _getUnderylingTransportAndPath(self, relpath):
        try:
            return VirtualTransport._getUnderylingTransportAndPath(
                self, relpath)
        except NotABranchPath, e:
            # If a virtual path doesn't point to a branch, then we cannot
            # translate it to an underlying transport. For almost all
            # purposes, this is as good as not existing at all.
            return defer.fail(NoSuchFile(e.virtual_path, e.reason))

    def mkdir(self, relpath, mode=None):
        # We hook into mkdir so that we can request the creation of a branch
        # and so that we can provide useful errors in the special case where
        # the user tries to make a directory like "~foo/bar". That is, a
        # directory that has too little information to be translated into a
        # Launchpad branch.
        deferred = VirtualTransport._getUnderylingTransportAndPath(
            self, relpath)
        def maybe_make_branch_in_db(failure):
            # Looks like we are trying to make a branch.
            failure.trap(BranchNotFound)
            return self.server.createBranch(self._abspath(relpath))
        def check_permission_denied(failure):
            # You can't ever create a directory that's not even a valid branch
            # name. That's strictly forbidden.
            failure.trap(NotABranchPath)
            exc_object = failure.value
            raise PermissionDenied(exc_object.virtual_path, exc_object.reason)
        def mkdir((transport, path)):
            return getattr(transport, 'mkdir')(path, mode)

        deferred.addCallback(mkdir)
        deferred.addErrback(maybe_make_branch_in_db)
        deferred.addErrback(check_permission_denied)
        return self._extractResult(deferred)

    def rename(self, rel_from, rel_to):
        # We hook into rename to catch the "unlock branch" event, so that we
        # can request a mirror once a branch is unlocked.
        abs_from = self._abspath(rel_from)
        if is_lock_directory(abs_from):
            self.server.requestMirror(abs_from)
        return VirtualTransport.rename(self, rel_from, rel_to)

    def rmdir(self, relpath):
        # We hook into rmdir in order to prevent users from deleting branches,
        # products and people from the VFS.
        virtual_path = self._abspath(relpath)
        path_segments = path = virtual_path.lstrip('/').split('/')
        if len(path_segments) <= 3:
            raise PermissionDenied(virtual_path)
        return VirtualTransport.rmdir(self, relpath)


class AsyncLaunchpadTransport(LaunchpadTransport):

    def _extractResult(self, deferred):
        return deferred
