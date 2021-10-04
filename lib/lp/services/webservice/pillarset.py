# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A class for the top-level link to the pillar set."""

__all__ = [
    'IPillarSetLink',
    'PillarSetLink',
    ]

from lazr.restful.interfaces import ITopLevelEntryLink
from zope.interface import implementer

from lp.registry.interfaces.pillar import IPillarNameSet
from lp.services.webapp.interfaces import ICanonicalUrlData


class IPillarSetLink(ITopLevelEntryLink, ICanonicalUrlData):
    """A marker interface."""


@implementer(IPillarSetLink)
class PillarSetLink:
    """The top-level link to the pillar set."""

    link_name = 'pillars'
    entry_type = IPillarNameSet

    inside = None
    path = 'pillars'
    rootsite = 'api'
