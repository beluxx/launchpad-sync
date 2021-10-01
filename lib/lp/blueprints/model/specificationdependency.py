# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ['SpecificationDependency']

from sqlobject import ForeignKey
from zope.interface import implementer

from lp.blueprints.interfaces.specificationdependency import (
    ISpecificationDependency,
    )
from lp.services.database.sqlbase import SQLBase


@implementer(ISpecificationDependency)
class SpecificationDependency(SQLBase):
    """A link between a spec and a bug."""

    _table = 'SpecificationDependency'
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)
    dependency = ForeignKey(dbName='dependency',
        foreignKey='Specification', notNull=True)
