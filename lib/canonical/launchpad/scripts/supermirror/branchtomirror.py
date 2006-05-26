# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import httplib
import os
import shutil
import socket
import urllib2

import bzrlib.branch
import bzrlib.errors


__all__ = ['BranchToMirror']

def identical_formats(branch_one, branch_two):
    """Check if two branches have the same bzrdir, repo, and branch formats."""
    # XXX AndrewBennetts 2006-05-18: comparing format objects is ugly.
    # See bug 45277.
    b1, b2 = branch_one, branch_two
    return (
        b1.bzrdir._format.__class__ == b2.bzrdir._format.__class__ and 
        b1.repository._format.__class__ == b2.repository._format.__class__ and
        b1._format.__class__ == b2._format.__class__
    )


class BranchToMirror:
    """This class represents a single branch that needs mirroring.

    It has a source URL, a destination URL, a database id and a 
    status client which is used to report on the mirror progress.
    """

    def __init__(self, src, dest, branch_status_client, branch_id):
        self.source = src
        self.dest = dest
        self.branch_status_client = branch_status_client
        self.branch_id = branch_id
        self._source_branch = None
        self._dest_branch = None
        assert self.dest is not None
        assert self.source is not None

    def _openSourceBranch(self):
        """Open the branch to pull from, useful to override in tests."""
        self._source_branch = bzrlib.branch.Branch.open(self.source)

    def _openDestBranch(self):
        """Open the branch to pull to, creating a new one if necessary.
        
        Useful to override in tests.
        """
        try:
            branch = bzrlib.bzrdir.BzrDir.open(self.dest).open_branch()
        except bzrlib.errors.NotBranchError:
            # XXX Andrew Bennetts 2006-05-17: 
            #    Unfortunately, we cannot use BzrDir.create_branch_convenience,
            #    because it doesn't let us control the branch or repository
            #    format.
            # Make a new branch in the same format as the source branch.
            branch = self._createDestBranch()
        else:
            # Check that destination branch is in the same format as the source.
            # If it isn't, we'll delete it and mirror from scratch.
            if not identical_formats(self._source_branch, branch):
                shutil.rmtree(self.dest)
                branch = self._createDestBranch()
        self._dest_branch = branch

    def _createDestBranch(self):
        """Create the branch to pull to."""
        os.makedirs(self.dest) 
        bzrdir_format = self._source_branch.bzrdir._format
        bzrdir = bzrdir_format.initialize(self.dest)
        repo_format = self._source_branch.repository._format
        repo = repo_format.initialize(bzrdir)
        branch_format = self._source_branch._format
        branch = branch_format.initialize(bzrdir)
        return branch

    def _pullSourceToDest(self):
        """Pull the contents of self._source_branch into self._dest_branch."""
        assert self._source_branch is not None
        assert self._dest_branch is not None
        self._dest_branch.pull(self._source_branch, overwrite=True)

    def _mirrorFailed(self, error_msg):
        """Log that the mirroring of this branch failed."""
        self.branch_status_client.mirrorFailed(self.branch_id, str(error_msg))

    def mirror(self):
        """Open source and destination branches and pull source into
        destination.
        """
        self.branch_status_client.startMirroring(self.branch_id)

        try: 
            self._openSourceBranch()
            self._openDestBranch()
            self._pullSourceToDest()
        # add further encountered errors from the production runs here
        # ------ HERE ---------
        #
        except urllib2.HTTPError, e:
            msg = str(e)
            if int(e.code) == httplib.UNAUTHORIZED:
                # Maybe this will be caugnt in bzrlib one day, and then we'll
                # be able to get rid of this.
                # https://launchpad.net/products/bzr/+bug/42383
                msg = 'Private branch; required authentication'
            self._mirrorFailed(msg)

        except socket.error, e:
            msg = 'A socket error occurred: %s' % str(e)
            self._mirrorFailed(msg)

        except bzrlib.errors.UnsupportedFormatError, e:
            msg = ("The supermirror does not support branches from before "
                   "bzr 0.7. Please upgrade the branch using bzr upgrade.")
            self._mirrorFailed(msg)

        except bzrlib.errors.UnknownFormatError, e:
            if e.args[0].count('\n') >= 2:
                msg = 'Not a branch'
            else:
                msg = 'Unknown branch format: %s' % e.args[0]
            self._mirrorFailed(msg)

        except bzrlib.errors.ParamikoNotPresent, e:
            msg = ("The supermirror does not support mirroring branches "
                   "from SFTP URLs. Please register a HTTP location for "
                   "this branch.")
            self._mirrorFailed(msg)

        except bzrlib.errors.NotBranchError, e:
            self._mirrorFailed(e)

        except bzrlib.errors.BzrError, e:
            self._mirrorFailed(e)

        else:
            self.branch_status_client.mirrorComplete(self.branch_id)

    def __eq__(self, other):
        return self.source == other.source and self.dest == other.dest

    def __repr__(self):
        return ("<BranchToMirror source=%s dest=%s at %x>" % 
                (self.source, self.dest, id(self)))

