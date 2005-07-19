# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Components related to bug tasks."""

__metaclass__ = type

from zope.interface import implements
from zope.component import getUtility

from sqlobject import SQLObjectNotFound

from canonical.launchpad.interfaces import (
    IProduct, IDistribution, IDistroRelease, IBugTaskSubset, IBugSet,
    IBugTaskSet, IBugTaskDelta)

class ContextToBugTaskSubsetAdapter:
    """Adapt a context to an IBugTaskSubset."""
    implements(IBugTaskSubset)

    def __init__(self, context):
        self.context = context
        self.title = context.title

    def __getitem__(self, item):
        """See canonical.launchpad.interfaces.IBugTaskSubset."""
        if item.isdigit():
            bugset = getUtility(IBugSet)
            bugtaskset = getUtility(IBugTaskSet)

            try:
                bug = bugset.get(item)
            except SQLObjectNotFound:
                raise KeyError(item)

            context_filter_param = self._get_context_search_param()
            tasks = bugtaskset.search(bug = bug, **context_filter_param)

            try:
                return tasks[0]
            except IndexError:
                raise KeyError(item)
        else:
            raise KeyError(item)

    def search(self, bug=None, searchtext=None, status=None, priority=None,
               severity=None, milestone=None, assignee=None, owner=None,
               orderby=None, statusexplanation=None):
        """See canonical.launchpad.interfaces.IBugTaskSubset."""
        context_filter_param = self._get_context_search_param()
        return getUtility(IBugTaskSet).search(
            bug=bug, searchtext=searchtext, status=status, priority=priority,
            severity=severity, milestone=milestone, assignee=assignee,
            owner=owner, orderby=orderby,
            statusexplanation=statusexplanation, **context_filter_param)

    def _get_context_search_param(self):
        """Return a query param to filter the IBugTasks for this context.

        Returns a dict, e.g. {'distribution' : ...}.
        """
        search_param = {}

        if IProduct.providedBy(self.context):
            search_param["product"] = self.context
        elif IDistribution.providedBy(self.context):
            search_param["distribution"] = self.context
        elif IDistroRelease.providedBy(self.context):
            search_param["distrorelease"] = self.context
        else:
            raise TypeError("Unknown search context: %s" % repr(self.context))

        return search_param


class BugTaskDelta:
    """See canonical.launchpad.interfaces.IBugTaskDelta."""
    implements(IBugTaskDelta)
    def __init__(self, bugtask, product=None, sourcepackagename=None,
                 binarypackagename=None, status=None, severity=None,
                 priority=None, assignee=None, milestone=None,
                 statusexplanation=None):
        self.bugtask = bugtask
        self.product = product
        self.sourcepackagename = sourcepackagename
        self.binarypackagename = binarypackagename
        self.status = status
        self.severity = severity
        self.priority = priority
        self.assignee = assignee
        self.target = milestone
        self.statusexplanation = statusexplanation
