# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Factory used to get named services."""

__all__ = [
    'ServiceFactory',
    ]

from zope.component import getUtility
from zope.interface import implementer

from lp.app.interfaces.services import (
    IService,
    IServiceFactory,
    )
from lp.services.webapp.publisher import Navigation


@implementer(IServiceFactory)
class ServiceFactory(Navigation):
    """Creates a named service.

    Services are traversed via urls of the form /services/<name>
    Implementation classes are registered as named zope utilities.
    """

    def __init__(self):
        super().__init__(None)

    def traverse(self, name):
        return self.getService(name)

    def getService(self, service_name):
        return getUtility(IService, service_name)
