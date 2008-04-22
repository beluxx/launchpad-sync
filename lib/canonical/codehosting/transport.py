# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0702

"""Bazaar transport for the Launchpad code hosting file system."""

__metaclass__ = type
__all__ = [
    'LaunchpadServer',
    'LaunchpadTransport',
    'set_up_logging',
    'UntranslatablePath',
    ]

import logging
import os

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

from twisted.web.xmlrpc import Fault
from twisted.python import log as tplog

from canonical.authserver.interfaces import (
    NOT_FOUND_FAULT_CODE, PERMISSION_DENIED_FAULT_CODE, READ_ONLY)

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.bazaarfs import (
    ALLOWED_DIRECTORIES, FORBIDDEN_DIRECTORY_ERROR, is_lock_directory)
from canonical.config import config
from canonical.launchpad.webapp import errorlog
from canonical.twistedsupport.loggingsupport import OOPSLoggingObserver


def split_with_padding(a_string, splitter, num_fields, padding=None):
    """Split the given string into exactly num_fields.

    If the given string doesn't have enough tokens to split into num_fields
    fields, then the resulting list of tokens is padded with 'padding'.
    """
    tokens = a_string.split(splitter, num_fields - 1)
    tokens.extend([padding] * max(0, num_fields - len(tokens)))
    return tokens


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

    # Don't log 'codehosting' messages to stderr.
    if getattr(trace, '_stderr_handler', None) is not None:
        trace._stderr_handler.addFilter(_NotFilter('codehosting'))

    log.setLevel(logging.DEBUG)

    if configure_oops_reporting:
        errorlog.globalErrorUtility.configure('codehosting')
        tplog.addObserver(OOPSLoggingObserver('codehosting').emit)

    return log


class UntranslatablePath(BzrError):

    _fmt = ("Could not translate %(path)s onto backing transport for "
            "user %(user)r")


class BranchNotFound(BzrError):

    _fmt = ("Could not find id for branch ~%(owner)s/%(product)s/%(name)s.")


class CachingAuthserverClient:

    def __init__(self, authserver, user_id):
        self._authserver = authserver
        self._branch_info_cache = {}
        self._user_id = user_id

    def createBranch(self, owner, product, branch):
        """Create a branch on the authserver."""
        branch_id = self._authserver.createBranch(
            self._user_id, owner, product, branch)
        # Clear the cache for this branch. We *could* populate it with
        # (branch_id, 'w'), but then we'd be building in more assumptions
        # about the authserver.
        self._branch_info_cache[(owner, product, branch)] = None
        return branch_id

    def getBranchInformation(self, owner, product, branch):
        """Get branch information from the authserver."""
        branch_info = self._branch_info_cache.get((owner, product, branch))
        if branch_info is None:
            branch_info = self._authserver.getBranchInformation(
                self._user_id, owner, product, branch)
            self._branch_info_cache[(owner, product, branch)] = branch_info
        return branch_info

    def requestMirror(self, branch_id):
        return self._authserver.requestMirror(self._user_id, branch_id)


class BranchPath:

    @classmethod
    def from_virtual_path(cls, authserver, virtual_path):
        segments = get_path_segments(virtual_path, 3)
        # If we don't have at least an owner, product and name, then we don't
        # have enough information for a branch.
        if len(segments) < 3:
            raise NoSuchFile(virtual_path)
        # If we have only an owner, product, name tuple, append an empty path.
        if len(segments) == 3:
            segments.append('')
        user_dir, product, name, path = segments
        # The Bazaar client will look for a .bzr directory in the owner and
        # product directories to see if there's a shared repository. There
        # won't be, but if we raise a PermissionDenied, Bazaar will prompt the
        # user to retry the command with --create-prefix, which is unhelpful.
        # Instead, we raise NoSuchFile, which should avoid this.
        if '.bzr' in (user_dir, product, name):
            raise NoSuchFile(virtual_path)
        if not user_dir.startswith('~'):
            raise NoSuchFile(virtual_path)
        return cls(authserver, user_dir[1:], product, name), path

    def __init__(self, authserver, owner, product, name):
        self._authserver = authserver
        self._owner = owner
        self._product = product
        self._name = name

    def checkPath(self, path_on_branch):
        """Raise an error if `path_on_branch` is not valid."""
        if path_on_branch == '':
            return
        segments = get_path_segments(path_on_branch)
        if segments[0] not in ALLOWED_DIRECTORIES:
            raise PermissionDenied(
                FORBIDDEN_DIRECTORY_ERROR % (segments[0],))

    def ensureUnderlyingPath(self, transport):
        """Ensure that the directory for the branch exists on the transport.
        """
        try:
            ensure_base(transport.clone(self.getRealPath('')))
        except BranchNotFound:
            # The branch doesn't exist so we don't need to create the
            # underlying directory.
            pass

    def getRealPath(self, path_on_branch):
        self.checkPath(path_on_branch)
        branch_id = self.getID()
        path = '/'.join([branch_id_to_path(branch_id), path_on_branch])
        return path

    def getID(self):
        return self.getInfo()[0]

    def getPermissions(self):
        return self.getInfo()[1]

    def getInfo(self):
        branch_id, permissions = self._authserver.getBranchInformation(
            self._owner, self._product, self._name)
        if branch_id == '':
            raise BranchNotFound(
                owner=self._owner, product=self._product, name=self._name)
        return branch_id, permissions

    def requestMirror(self):
        branch_id = self.getID()
        self._authserver.requestMirror(branch_id)


class LaunchpadServer(Server):
    """Bazaar Server for Launchpad branches.

    See LaunchpadTransport for more information.
    """

    def __init__(self, authserver, user_id, hosting_transport,
                 mirror_transport):
        """
        Construct a LaunchpadServer.

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

        # Cache for authserver responses to getBranchInformation(). This maps
        # from (user, product, branch) tuples to whatever
        # getBranchInformation() returns. To clear an individual tuple, set
        # its value in the cache to None, or delete it from the cache.
        user_dict = authserver.getUser(user_id)
        user_id = user_dict['id']
        user_name = user_dict['name']
        self.authserver = CachingAuthserverClient(authserver, user_id)
        self.backing_transport = hosting_transport
        self.mirror_transport = get_transport(
            'readonly+' + mirror_transport.base)
        self._is_set_up = False
        self.logger = logging.getLogger('codehosting.lpserve.%s' % user_name)

    def _getBranch(self, virtual_path):
        return BranchPath.from_virtual_path(self.authserver, virtual_path)

    def createBranch(self, virtual_path):
        """Make a new directory for the given virtual path.

        If the request is to make a user or a product directory, fail
        with PermissionDenied error. If the request is to make a
        branch directory, create the branch in the database then
        create a matching directory on the backing transport.
        """
        self.logger.info('mkdir(%r)', virtual_path)
        try:
            # XXX: the tests seem to expect that we should raise a
            # PermissionDenied here. Hmm. Find out why.
            branch, ignored = self._getBranch(virtual_path)
        except NoSuchFile:
            raise PermissionDenied(virtual_path)

        branch_id = self._make_branch(branch)
        # XXX: This logic should be moved to the authserver!
        if branch_id == '':
            raise PermissionDenied(
                'Cannot create branch: %s' % (virtual_path,))
        branch.ensureUnderlyingPath(self.backing_transport)

    def requestMirror(self, virtual_path):
        """Request that the branch that owns 'virtual_path' be mirrored."""
        branch, ignored = self._getBranch(virtual_path)
        branch.requestMirror()

    def translateVirtualPath(self, virtual_path):
        """Translate 'virtual_path' into a transport and sub-path.

        :raise UntranslatablePath: If path is untranslatable. This could be
            because the path is too short (doesn't include user, product and
            branch), or because the user, product or branch in the path don't
            exist.

        :raise TransportNotPossible: If the path is necessarily invalid. Most
            likely because it didn't begin with a tilde ('~').

        :return: (transport, path_on_transport)
        """
        self.logger.debug('translate_virtual_path(%r)', virtual_path)
        branch, path = self._getBranch(virtual_path)

        try:
            real_path = branch.getRealPath(path)
        except BranchNotFound:
            if path == '':
                # We are trying to translate a branch path that doesn't exist.
                raise
            else:
                # We are trying to translate a path within a branch that
                # doesn't exist.
                raise NoSuchFile(virtual_path)

        permissions = branch.getPermissions()
        if permissions == READ_ONLY:
            transport = self.mirror_transport
        else:
            transport = self.backing_transport
            branch.ensureUnderlyingPath(transport)
        return transport, real_path

    def _make_branch(self, branch):
        """Create a branch in the database for the given user and product.

        :param user: The loginID of the user who owns the new branch.
        :param product: The name of the product to which the new branch
            belongs.
        :param branch: The name of the new branch.

        :raise PermissionDenied: If 'user' does not begin with a '~' or if
            'product' is not the name of an existing product.
        :return: The database ID of the new branch.
        """
        try:
            return self.authserver.createBranch(
                branch._owner, branch._product, branch._name)
        except Fault, f:
            if f.faultCode == NOT_FOUND_FAULT_CODE:
                # One might think that it would make sense to raise
                # NoSuchFile here, but that makes the client do "clever"
                # things like say "Parent directory of
                # bzr+ssh://bazaar.launchpad.dev/~noone/firefox/branch
                # does not exist.  You may supply --create-prefix to
                # create all leading parent directories."  Which is just
                # misleading.
                raise TransportNotPossible(f.faultString)
            elif f.faultCode == PERMISSION_DENIED_FAULT_CODE:
                raise PermissionDenied(f.faultString)
            else:
                raise

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


class LaunchpadTransport(Transport):
    """Transport to map from ~user/product/branch paths to codehosting paths.

    Launchpad serves its branches from URLs that look like
    bzr+ssh://launchpad/~user/product/branch. On the filesystem, the branches
    are stored by their id.

    This transport maps from the external, 'virtual' paths to the internal
    filesystem paths. The internal filesystem is represented by a backing
    transport.
    """

    def __init__(self, server, url):
        self.server = server
        Transport.__init__(self, url)

    def external_url(self):
        # There's no real external URL to this transport. It's heavily
        # dependent on the process.
        raise InProcessTransport(self)

    def _abspath(self, relpath):
        """Return the absolute path to `relpath` without the schema."""
        return urlutils.joinpath(self.base[len(self.server.scheme)-1:],
                                 relpath)

    def _call(self, methodname, relpath, *args, **kwargs):
        """Call a method on the backing transport, translating relative,
        virtual paths to filesystem paths.

        If 'relpath' translates to a path that we only have read-access to,
        then the method will be called on the backing transport decorated with
        'readonly+'.

        :raise NoSuchFile: If the path cannot be translated.
        :raise TransportNotPossible: If trying to do a write operation on a
            read-only path.
        """
        transport, path = self.server.translateVirtualPath(
            self._abspath(relpath))
        method = getattr(transport, methodname)
        return method(path, *args, **kwargs)

    # Transport methods
    def abspath(self, relpath):
        self.server.logger.debug('abspath(%s)', relpath)
        return urlutils.join(self.server.scheme, relpath)

    def append_file(self, relpath, f, mode=None):
        return self._call('append_file', relpath, f, mode)

    def clone(self, relpath=None):
        self.server.logger.debug('clone(%s)', relpath)
        if relpath is None:
            return LaunchpadTransport(self.server, self.base)
        else:
            return LaunchpadTransport(
                self.server, urlutils.join(self.base, relpath))

    def delete(self, relpath):
        return self._call('delete', relpath)

    def delete_tree(self, relpath):
        return self._call('delete_tree', relpath)

    def get(self, relpath):
        return self._call('get', relpath)

    def has(self, relpath):
        return self._call('has', relpath)

    def iter_files_recursive(self):
        self.server.logger.debug('iter_files_recursive()')
        transport, path = self.server.translateVirtualPath(self._abspath('.'))
        return transport.clone(path).iter_files_recursive()

    def listable(self):
        self.server.logger.debug('listable()')
        transport, path = self.server.translateVirtualPath(self._abspath('.'))
        return transport.listable()

    def list_dir(self, relpath):
        return self._call('list_dir', relpath)

    def lock_read(self, relpath):
        return self._call('lock_read', relpath)

    def lock_write(self, relpath):
        return self._call('lock_write', relpath)

    def mkdir(self, relpath, mode=None):
        # If we can't translate the path, then perhaps we are being asked to
        # create a new branch directory. Delegate to the server, as it knows
        # how to deal with absolute virtual paths.
        try:
            return self._call('mkdir', relpath, mode)
        except BranchNotFound:
            # Looks like we are trying to make a branch.
            return self.server.createBranch(self._abspath(relpath))
        except NoSuchFile, e:
            # The relpath is invalid for some reason. In that case tell the
            # user we cannot make it.
            raise PermissionDenied(relpath)

    def put_file(self, relpath, f, mode=None):
        return self._call('put_file', relpath, f, mode)

    def rename(self, rel_from, rel_to):
        abs_to = self._abspath(rel_to)
        transport, path = self.server.translateVirtualPath(abs_to)
        # This is a horrible lie. What we should check is that the transport
        # of rel_to is the same as the transport of rel_from.
        if transport.is_readonly():
            raise TransportNotPossible('readonly transport')
        abs_from = self._abspath(rel_from)
        if is_lock_directory(abs_from):
            self.server.requestMirror(abs_from)
        return self._call('rename', rel_from, path)

    def rmdir(self, relpath):
        virtual_path = self._abspath(relpath)
        path_segments = path = virtual_path.lstrip('/').split('/')
        if len(path_segments) <= 3:
            raise PermissionDenied(virtual_path)
        return self._call('rmdir', relpath)

    def stat(self, relpath):
        return self._call('stat', relpath)
