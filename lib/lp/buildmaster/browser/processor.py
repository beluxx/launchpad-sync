# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Navigation views for processors."""

__all__ = [
    "ProcessorSetNavigation",
]


from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.services.webapp import Navigation


class ProcessorSetNavigation(Navigation):
    """IProcessorSet navigation."""

    usedfor = IProcessorSet

    def traverse(self, name):
        return self.context.getByName(name)
