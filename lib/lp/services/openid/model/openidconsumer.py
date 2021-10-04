# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OpenID Consumer related database classes."""

__all__ = ['OpenIDConsumerNonce']

from zope.interface import implementer

from lp.services.openid.interfaces.openidconsumer import IOpenIDConsumerStore
from lp.services.openid.model.baseopenidstore import (
    BaseStormOpenIDAssociation,
    BaseStormOpenIDNonce,
    BaseStormOpenIDStore,
    )


class OpenIDConsumerAssociation(BaseStormOpenIDAssociation):
    __storm_table__ = 'OpenIDConsumerAssociation'


class OpenIDConsumerNonce(BaseStormOpenIDNonce):
    __storm_table__ = 'OpenIDConsumerNonce'


@implementer(IOpenIDConsumerStore)
class OpenIDConsumerStore(BaseStormOpenIDStore):
    """An OpenID association and nonce store for Launchpad."""

    Association = OpenIDConsumerAssociation
    Nonce = OpenIDConsumerNonce
