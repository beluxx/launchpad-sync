# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functions used with the repack Git repositories script."""

__metaclass__ = type

from psycopg2.extensions import TransactionRollbackError
import six
from storm.expr import (
    And,
    Or,
    )
import transaction

from lp.code.enums import GitRepositoryStatus
from lp.code.errors import CannotRepackRepository
from lp.code.model.gitrepository import GitRepository
from lp.services.config import config
from lp.services.database.interfaces import IStore
from lp.services.looptuner import (
    LoopTuner,
    TunableLoop,
    )


class RepackTunableLoop(TunableLoop):
    tuner_class = LoopTuner
    maximum_chunk_size = 5

    def __init__(self, log, dry_run, abort_time=None):
        super(RepackTunableLoop, self).__init__(log, abort_time)
        self.dry_run = dry_run
        self.start_at = 0
        self.logger = log
        self.store = IStore(GitRepository)

    def findRepackCandidates(self):
        repos = self.store.find(
            GitRepository,
            (Or(
                GitRepository.loose_object_count >=
                config.codehosting.loose_objects_threshold,
                GitRepository.status == GitRepositoryStatus.AVAILABLE,
                GitRepository.pack_count >=
                config.codehosting.packs_threshold
                ),
             And(GitRepository.id > self.start_at))).order_by(GitRepository.id)
        return repos

    def isDone(self):
        return self.findRepackCandidates().is_empty()

    def __call__(self, chunk_size):
        repackable_repos = list(self.findRepackCandidates()[:chunk_size])
        counter = 0
        for repo in repackable_repos:
            try:
                if self.dry_run:
                    print ('Would repack %s' % repo.identity)
                else:
                    self.logger.info(
                        'Requesting automatic git repository repack for %s.'
                        % repo.identity)
                    repo.repackRepository()
                    counter += 1
            except CannotRepackRepository as e:
                self.logger.error(
                    'An error occurred while requesting repository repack %s'
                    % e.args[0])
                continue
            except TransactionRollbackError as error:
                self.logger.error(
                    'An error occurred while requesting repository repack %s'
                    % six.text_type(error))
                if transaction is not None:
                    transaction.abort()
                continue

        if self.dry_run:
            print(
                'Reporting %d automatic git repository repacks '
                'would have been requested as part of this run '
                'out of the %d qualifying for repack.'
                % (counter, len(repackable_repos)))
        else:
            self.logger.info(
                'Requested %d automatic git repository repacks '
                'out of the %d qualifying for repack.'
                % (counter, len(repackable_repos)))

        self.start_at = repackable_repos[-1].id

        if not self.dry_run:
            transaction.commit()
        else:
            transaction.abort()