# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
BATCH_SIZE = 40

class DistroArchReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request


class DistroArchReleaseBinariesView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

        # XXX for the moment I'm making FTI searching the only option
        #     MarkShuttleworth 10-03-2005
        self.fti = self.request.get("fti", "")
        self.fti = True

    def binaryPackagesBatchNavigator(self):
        name = self.request.get("name", "")

        if not name:
            binary_packages = []
        else:
            binary_packages = list(self.context.findPackagesByName(name,
                                                                   self.fti))

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE
        batch = Batch(list = binary_packages, start = start,
                      size = batch_size)

        return BatchNavigator(batch = batch, request = self.request)

