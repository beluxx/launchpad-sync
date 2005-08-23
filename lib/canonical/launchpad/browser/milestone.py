# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Milestone views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IProduct, IDistribution, IMilestoneSet)
from canonical.launchpad.browser.editview import SQLObjectEditView

__all__ = [
    'MilestoneAddView',
    'MilestoneEditView',
    ]

class MilestoneAddView:
    def create(self, name, dateexpected=None):
        """Inject the relevant product or distribution into the kw args."""
        product = None
        distribution = None
        if IProduct.providedBy(self.context):
            product = self.context.id
        elif IDistribution.providedBy(self.context):
            distribution = self.context.id
        return getUtility(IMilestoneSet).new(name, product=product,
            distribution=distribution, dateexpected=dateexpected)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return '.'


class MilestoneEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect('../..')

