# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "PackagesetGroup",
]

import pytz
from storm.locals import DateTime, Int, Reference, Storm
from zope.interface import implementer

from lp.soyuz.interfaces.packagesetgroup import IPackagesetGroup


@implementer(IPackagesetGroup)
class PackagesetGroup(Storm):
    """See `IPackageset`."""

    __storm_table__ = "PackagesetGroup"
    id = Int(primary=True)

    date_created = DateTime(
        name="date_created", allow_none=False, tzinfo=pytz.UTC
    )

    owner_id = Int(name="owner", allow_none=False)
    owner = Reference(owner_id, "Person.id")
