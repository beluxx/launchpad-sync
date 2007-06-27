# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Broswer views for CodeImports."""

__metaclass__ = type

__all__ = [
    'CodeImportSetNavigation',
    'CodeImportSetView',
    'CodeImportView',
    ]


from canonical.launchpad.interfaces import ICodeImportSet
from canonical.launchpad.webapp import LaunchpadView, Navigation
from canonical.launchpad.webapp.batching import BatchNavigator


class CodeImportSetNavigation(Navigation):

    usedfor = ICodeImportSet

    def breadcrumb(self):
        return "Code Imports"

    def traverse(self, id):
        try:
            return self.context.get(id)
        except LookupError:
            return None

class CodeImportSetView(LaunchpadView):
    def initialize(self):
        self.batchnav = BatchNavigator(
            self.context.getAll(), self.request, size=50)

class CodeImportView(LaunchpadView):
    def initialize(self):
        self.title = "Code Import for %s"%(self.context.product.name,)
