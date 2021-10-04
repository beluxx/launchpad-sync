# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OpenID adapters and helpers."""

__all__ = [
    'CurrentOpenIDEndPoint',
    'OpenIDPersistentIdentity',
    ]

import six
from zope.component import adapter
from zope.interface import implementer

from lp.registry.interfaces.person import IPerson
from lp.services.config import config
from lp.services.database.interfaces import IStore
from lp.services.identity.interfaces.account import IAccount
from lp.services.openid.interfaces.openid import IOpenIDPersistentIdentity
from lp.services.openid.model.openididentifier import OpenIdIdentifier


class CurrentOpenIDEndPoint:
    """A utility for working with multiple OpenID End Points."""

    @staticmethod
    def getServiceURL():
        """The OpenID server URL (/+openid) for the current request."""
        return config.launchpad.openid_provider_root + '+openid'

    @staticmethod
    def getAllRootURLs():
        """All configured OpenID provider root URLs."""
        yield config.launchpad.openid_provider_root
        alternate_roots = config.launchpad.openid_alternate_provider_roots
        if alternate_roots:
            for root in [r.strip() for r in alternate_roots.split(',')]:
                if root:
                    yield root


@adapter(IAccount)
@implementer(IOpenIDPersistentIdentity)
class OpenIDPersistentIdentity:
    """A persistent OpenID identifier for a user."""

    def __init__(self, account):
        self.account = account

    @property
    def openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        openid_identifier = self.openid_identifier
        if openid_identifier is None:
            return None
        return (
            six.ensure_text(config.launchpad.openid_provider_root) +
            openid_identifier)

    @property
    def openid_identifier(self):
        """See `IOpenIDPersistentIdentity`."""
        # We might have multiple OpenID identifiers linked to an
        # account. We just use the first one which is good enough
        # for our purposes.
        identifier = IStore(OpenIdIdentifier).find(
            OpenIdIdentifier, account=self.account).order_by(
                OpenIdIdentifier.date_created).first()
        if identifier is None:
            return None
        else:
            return '+id/' + identifier.identifier


@adapter(IPerson)
@implementer(IOpenIDPersistentIdentity)
def person_to_openidpersistentidentity(person):
    """Adapts an `IPerson` into an `IOpenIDPersistentIdentity`."""
    return OpenIDPersistentIdentity(person.account)
