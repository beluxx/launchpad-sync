# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Verify (and refresh) `POFile`s' cached statistics."""

__metaclass__ = type
__all__ = ['VerifyPOFileStatsProcess']


import logging

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.interfaces import IPOFileSet
from canonical.launchpad.utilities.looptuner import LoopTuner

class Verifier:
    """`ITunableLoop` that recomputes & checks all `POFile`s' statistics."""
    implements(ITunableLoop)

    def __init__(self, transaction, logger, start_at_id=0):
        self.transaction = transaction
        self.logger = logger
        self.start_id = start_at_id
        self.pofileset = getUtility(IPOFileSet)

    def isDone(self):
        """See `ITunableLoop`."""
        return self.start_id is None

    def __call__(self, chunk_size):
        """See `ITunableLoop`."""
        pofiles = self.pofileset.getBatch(self.start_id, int(chunk_size))

        self.start_id = None
        for pofile in pofiles:
            self.start_id = pofile.id + 1
            try:
                self._verify(pofile)
            except Exception, error:
                self.logger.warning(
                    "Error %s while recomputing stats for POFile %d: %s"
                    % (type(error), pofile.id, error))

        self.transaction.commit()
        self.transaction.begin()

    def _verify(self, pofile):
        old_stats = pofile.getStatistics()
        new_stats = pofile.updateStatistics()
        if new_stats != old_stats:
            self.logger.warning(
                "POFile %d: cached stats were %s, recomputed as %s"
                % (pofile.id, str(old_stats), str(new_stats)))


class VerifyPOFileStatsProcess:
    """Recompute & verify `POFile` translation statistics."""

    def __init__(self, transaction, logger=None, start_at_id=0):
        self.transaction = transaction
        self.logger = logger
        self.start_at_id = start_at_id
        if logger is None:
            self.logger = logging.getLogger("pofile-stats")

    def run(self):
        self.logger.info("Starting verification of POFile stats at id %d"
            % self.start_at_id)
        loop = Verifier(self.transaction, self.logger, self.start_at_id)
        LoopTuner(loop, 4).run()
        self.logger.info("Done.")

