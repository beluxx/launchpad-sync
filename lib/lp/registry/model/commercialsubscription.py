# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation classes for a CommercialSubscription."""

__all__ = ['CommercialSubscription']

import datetime

import pytz
from storm.locals import (
    DateTime,
    Int,
    Reference,
    Store,
    Unicode,
    )
from zope.interface import implementer

from lp.registry.errors import CannotDeleteCommercialSubscription
from lp.registry.interfaces.commercialsubscription import (
    ICommercialSubscription,
    )
from lp.registry.interfaces.person import validate_public_person
from lp.services.database.constants import UTC_NOW
from lp.services.database.stormbase import StormBase


@implementer(ICommercialSubscription)
class CommercialSubscription(StormBase):

    __storm_table__ = 'CommercialSubscription'

    id = Int(primary=True)

    product_id = Int(name='product', allow_none=False)
    product = Reference(product_id, 'Product.id')

    date_created = DateTime(tzinfo=pytz.UTC, allow_none=False, default=UTC_NOW)
    date_last_modified = DateTime(
        tzinfo=pytz.UTC, allow_none=False, default=UTC_NOW)
    date_starts = DateTime(tzinfo=pytz.UTC, allow_none=False, default=UTC_NOW)
    date_expires = DateTime(tzinfo=pytz.UTC, allow_none=False, default=UTC_NOW)

    registrant_id = Int(
        name='registrant', allow_none=False, validator=validate_public_person)
    registrant = Reference(registrant_id, 'Person.id')

    purchaser_id = Int(
        name='purchaser', allow_none=False, validator=validate_public_person)
    purchaser = Reference(purchaser_id, 'Person.id')

    sales_system_id = Unicode(allow_none=False)
    whiteboard = Unicode(default=None)

    def __init__(self, product, date_starts, date_expires, registrant,
                 purchaser, sales_system_id, whiteboard):
        super().__init__()
        self.product = product
        self.date_starts = date_starts
        self.date_expires = date_expires
        self.registrant = registrant
        self.purchaser = purchaser
        self.sales_system_id = sales_system_id
        self.whiteboard = whiteboard

    @property
    def is_active(self):
        """See `ICommercialSubscription`"""
        now = datetime.datetime.now(pytz.timezone('UTC'))
        return self.date_starts < now < self.date_expires

    def delete(self):
        """See `ICommercialSubscription`"""
        if self.is_active:
            raise CannotDeleteCommercialSubscription(
                "This CommercialSubscription is still active.")
        Store.of(self).remove(self)
