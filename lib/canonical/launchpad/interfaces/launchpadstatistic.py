# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Launchpad statistic storage interfaces."""

__metaclass__ = type

__all__ = [
    'ILaunchpadStatistic',
    'ILaunchpadStatisticSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Int, TextLine
from canonical.launchpad import _


class ILaunchpadStatistic(Interface):
    """A single stored statistic or value in the Launchpad system.

    Each statistic is a name/value pair. Names are text, unique, and values
    are integers.
    """

    name = TextLine(title=_('Field Name'), required=True, readonly=True)
    value = Int(title=_('Value'), required=True, readonly=True)
    dateupdated = Attribute("The date this statistic was updated.")


class ILaunchpadStatisticSet(Interface):
    """The set of all ILaunchpadStatistics."""

    def __iter__():
        """Return an iterator over the whole set of statistics."""

    def update(name, value):
        """Update the field given in name to the value passed as value.
        Also, update the dateupdated to reflect the current datetime.
        """

    def dateupdated(name):
        """Return the date and time the given statistic name was last
        updated.
        """

    def value(name):
        """Return the current value of the requested statistic."""

    def updateStatistics(ztm):
        """Update the statistics in the system."""

