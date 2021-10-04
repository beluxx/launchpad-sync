# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of `ISuiteSourcePackage`."""

__all__ = [
    'SuiteSourcePackage',
    ]

from zope.interface import implementer

from lp.registry.interfaces.suitesourcepackage import ISuiteSourcePackage


@implementer(ISuiteSourcePackage)
class SuiteSourcePackage:
    """Implementation of `ISuiteSourcePackage`."""

    def __init__(self, distroseries, pocket, sourcepackagename):
        self.distroseries = distroseries
        self.pocket = pocket
        self.sourcepackagename = sourcepackagename

    def __eq__(self, other):
        try:
            other = ISuiteSourcePackage(other)
        except TypeError:
            return NotImplemented
        return (
            self.sourcepackage == other.sourcepackage
            and self.pocket == other.pocket)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.sourcepackage, self.pocket))

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.path)

    @property
    def displayname(self):
        """See `ISuiteSourcePackage`."""
        return "%s in %s" % (self.sourcepackagename.name, self.suite)

    @property
    def distribution(self):
        """See `ISuiteSourcePackage`."""
        return self.distroseries.distribution

    @property
    def path(self):
        """See `ISuiteSourcePackage`."""
        return '/'.join([
            self.distribution.name,
            self.suite,
            self.sourcepackagename.name])

    @property
    def sourcepackage(self):
        """See `ISuiteSourcePackage`."""
        return self.distroseries.getSourcePackage(self.sourcepackagename)

    @property
    def suite(self):
        """See `ISuiteSourcePackage`."""
        return self.distroseries.getSuite(self.pocket)
