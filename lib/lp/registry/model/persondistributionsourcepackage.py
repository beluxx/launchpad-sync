# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A person's view on a source package in a distribution."""

__all__ = [
    'PersonDistributionSourcePackage',
    ]

from zope.interface import (
    implementer,
    provider,
    )

from lp.registry.interfaces.persondistributionsourcepackage import (
    IPersonDistributionSourcePackage,
    IPersonDistributionSourcePackageFactory,
    )


@implementer(IPersonDistributionSourcePackage)
@provider(IPersonDistributionSourcePackageFactory)
class PersonDistributionSourcePackage:

    def __init__(self, person, distro_source_package):
        self.person = person
        self.distro_source_package = distro_source_package

    @staticmethod
    def create(person, distro_source_package):
        return PersonDistributionSourcePackage(person, distro_source_package)

    @property
    def display_name(self):
        return '%s in %s' % (
            self.person.displayname, self.distro_source_package.displayname)

    displayname = display_name

    def __eq__(self, other):
        return (
            IPersonDistributionSourcePackage.providedBy(other) and
            self.person == other.person and
            self.distro_source_package == other.distro_source_package)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.person, self.distro_source_package))
