# Copyright 2006 Canonical Ltd.  All rights reserved.

import os
import socket

from canonical.config import config
from contrib.glock import GlobalLock, LockAlreadyAcquired
from canonical.launchpad.scripts.supermirror.branchtargeter import branchtarget
from canonical.launchpad.scripts.supermirror.branchtomirror import (
    BranchToMirror)


class JobManager:
    """Schedule and manage the mirroring of branches.

    The jobmanager is responsible for organizing the mirroring of all
    branches.
    """

    name = 'branch-puller'

    def __init__(self):
        self.branches_to_mirror = []
        self.actualLock = None
        self.lockfilename = None

    def add(self, branch_to_mirror):
        """Add a branch to mirror to the JobManager."""
        self.branches_to_mirror.append(branch_to_mirror)

    def run(self, logger):
        """Run all branches_to_mirror registered with the JobManager"""
        logger.info('%d branches to mirror', len(self.branches_to_mirror))
        while self.branches_to_mirror:
            self.branches_to_mirror.pop(0).mirror(logger)
        logger.info('Mirroring complete')

    def _getBranchToMirror(self, branch_status_client, branch_id, branch_src,
                           unique_name):
        destination = config.supermirror.branchesdest
        branch_src = branch_src.strip()
        path = branchtarget(branch_id)
        branch_dest = os.path.join(destination, path)
        return BranchToMirror(
            branch_src, branch_dest, branch_status_client, branch_id,
            unique_name)
        
    def addBranches(self, branch_status_client):
        """Queue branches from the list given by the branch status client."""
        branches_to_pull = branch_status_client.getBranchPullQueue()
        for branch_id, branch_src, unique_name in branches_to_pull:
            branch = self._getBranchToMirror(
                branch_status_client, branch_id, branch_src, unique_name)
            self.add(branch)

    def lock(self):
        self.actualLock = GlobalLock(self.lockfilename)
        try:
            self.actualLock.acquire()
        except LockAlreadyAcquired:
            raise LockError(self.lockfilename)

    def unlock(self):
        self.actualLock.release()

    def recordActivity(self, branch_status_client,
                       date_started, date_completed):
        """Record successful completion of the script."""
        branch_status_client.recordSuccess(
            self.name, socket.gethostname(), date_started, date_completed)


class UploadJobManager(JobManager):
    """Manage mirroring of upload branches.

    UploadJobManager is responsible for the mirroring of branches that were
    uploaded to the bazaar.launchpad.net SFTP server.
    """

    name = 'branch-puller-upload'

    def __init__(self):
        JobManager.__init__(self)
        self.lockfilename = '/var/lock/launchpad-branch-puller-upload.lock'

    def addBranches(self, branch_status_client):
        """Queue branches from the list given by the branch status client."""
        branches_to_pull = branch_status_client.getBranchPullQueue()
        for branch_id, branch_src, unique_name in branches_to_pull:
            branch = self._getBranchToMirror(
                branch_status_client, branch_id, branch_src, unique_name)
            self.add(branch)

    def add(self, branch_to_mirror):
        """Add a branch to mirror, only if it is an upload branch."""
        if branch_to_mirror.isUploadBranch():
            JobManager.add(self, branch_to_mirror)


class ImportJobManager(JobManager):
    """Manage mirroring of import branches.

    ImportJobManager is responsible for the mirroring of branches produced by
    the VCS imports system.
    """

    name = 'branch-puller-import'

    def __init__(self):
        JobManager.__init__(self)
        self.lockfilename = '/var/lock/launchpad-branch-puller-import.lock'

    def addBranches(self, branch_status_client):
        """Queue branches from the list given by the branch status client."""
        branches_to_pull = branch_status_client.getBranchPullQueue()
        for branch_id, branch_src, unique_name in branches_to_pull:
            branch = self._getBranchToMirror(
                branch_status_client, branch_id, branch_src, unique_name)
            self.add(branch)

    def add(self, branch_to_mirror):
        """Add a branch to mirror, only if it is an import branch."""
        if branch_to_mirror.isImportBranch():
            JobManager.add(self, branch_to_mirror)


class MirrorJobManager(JobManager):
    """Manage mirroring of external branches.

    MirrorJobManager is responsible for the mirroring of branches hosted on the
    internet.
    """

    name = 'branch-puller-mirror'

    def __init__(self):
        JobManager.__init__(self)
        self.lockfilename = '/var/lock/launchpad-branch-puller-mirror.lock'

    def addBranches(self, branch_status_client):
        """Queue branches from the list given by the branch status client."""
        branches_to_pull = branch_status_client.getBranchPullQueue()
        for branch_id, branch_src, unique_name in branches_to_pull:
            branch = self._getBranchToMirror(
                branch_status_client, branch_id, branch_src, unique_name)
            self.add(branch)

    def add(self, branch_to_mirror):
        """Add a branch to mirror, only if it is an external branch."""
        if branch_to_mirror.isMirrorBranch():
            JobManager.add(self, branch_to_mirror)


class LockError(StandardError):

    def __init__(self, lockfilename):
        self.lockfilename = lockfilename

    def __str__(self):
        return 'Jobmanager unable to get master lock: %s' % self.lockfilename

