# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Launchpad IDatabaseInteractionPolicy.

The policy connects our Storm stores to either master or replica
databases based on the type of request or if read only mode is in operation.
"""

__metaclass__ = type
__all__ = [
        'LaunchpadDatabasePolicy',
        ]

from storm.zope.interfaces import IZStorm

from zope.component import getUtility
from zope.interface import implements

import canonical.launchpad.webapp.adapter as da
from canonical.launchpad.webapp.interfaces import IDatabasePolicy

class LaunchpadDatabasePolicy:

    implements(IDatabasePolicy)

    def __init__(self, request):
        self.request = request

    def beforeTraversal(self):
        """Install the database policy.

        This method is invoked by
        LaunchpadBrowserPublication.beforeTraversal()
        
        The policy connects our Storm stores to either master or replica
        databases based on the type of request or if read only mode is in
        operation.
        """
        self.read_only = self.request.method in ['GET', 'HEAD']

        # Tell our custom database adapter that the request has started.
        da.set_request_started()

        # Select the default Store.
        if self.read_only:
            da.StoreSelector.setDefaultFlavor(da.StoreSelector.SLAVE)
        else:
            da.StoreSelector.setDefaultFlavor(da.StoreSelector.MASTER)

        # And if we need write access or not. This isn't required for
        # production, but simulates a read only slave in the development
        # environment.
        main_store = da.StoreSelector.get(
                da.StoreSelector.MAIN, da.StoreSelector.DEFAULT)
        if self.read_only:
            main_store.execute("SET transaction_read_only TO TRUE")
        else:
            main_store.execute("SET transaction_read_only TO FALSE")
        
    def endRequest(self):
        """Cleanup.
        
        This method is invoked by LaunchpadBrowserPublication.endRequest.
        """
        da.clear_request_started()

