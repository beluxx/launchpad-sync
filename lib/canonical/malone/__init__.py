# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# This is the canonical.malone python package.

__metaclass__ = type

from zope.interface import implements
from zope.app.container.interfaces import IContained

from canonical.malone.interfaces import IMaloneApplication, IUsesAddForm
from canonical.publication import rootObject

class MaloneApplication(object):
    implements(IMaloneApplication, IContained, IUsesAddForm)

    __parent__ = rootObject

    def add(self, ob):
        return ob

    def nextURL(self):
        return '.'
