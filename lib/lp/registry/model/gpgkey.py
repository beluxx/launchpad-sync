# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['GPGKey', 'GPGKeySet']

from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLObjectNotFound,
    StringCol,
    )
from zope.component import getUtility
from zope.interface import implementer

from lp.registry.interfaces.gpg import (
    IGPGKey,
    IGPGKeySet,
    )
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from lp.services.gpg.interfaces import (
    GPGKeyAlgorithm,
    IGPGHandler,
    )


@implementer(IGPGKey)
class GPGKey(SQLBase):

    _table = 'GPGKey'
    _defaultOrder = ['owner', 'keyid']

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    keyid = StringCol(dbName='keyid', notNull=True)
    fingerprint = StringCol(dbName='fingerprint', notNull=True)

    keysize = IntCol(dbName='keysize', notNull=True)

    algorithm = EnumCol(dbName='algorithm', notNull=True,
                        enum=GPGKeyAlgorithm)

    active = BoolCol(dbName='active', notNull=True)

    can_encrypt = BoolCol(dbName='can_encrypt', notNull=False)

    @property
    def keyserverURL(self):
        return getUtility(
            IGPGHandler).getURLForKeyInServer(self.fingerprint, public=True)

    @property
    def displayname(self):
        return '%s%s/%s' % (self.keysize, self.algorithm.title, self.keyid)


@implementer(IGPGKeySet)
class GPGKeySet:

    def new(self, ownerID, keyid, fingerprint, keysize,
            algorithm, active=True, can_encrypt=False):
        """See `IGPGKeySet`"""
        return GPGKey(owner=ownerID, keyid=keyid,
                      fingerprint=fingerprint, keysize=keysize,
                      algorithm=algorithm, active=active,
                      can_encrypt=can_encrypt)

    def activate(self, requester, key, can_encrypt):
        """See `IGPGKeySet`."""
        fingerprint = key.fingerprint
        lp_key = self.getByFingerprint(fingerprint)
        if lp_key:
            # Then the key already exists, so let's reactivate it.
            lp_key.active = True
            lp_key.can_encrypt = can_encrypt
            return lp_key, False
        ownerID = requester.id
        keyid = key.keyid
        keysize = key.keysize
        algorithm = GPGKeyAlgorithm.items[key.algorithm]
        lp_key = self.new(
            ownerID, keyid, fingerprint, keysize, algorithm,
            can_encrypt=can_encrypt)
        return lp_key, True

    def getByFingerprint(self, fingerprint, default=None):
        """See `IGPGKeySet`"""
        result = GPGKey.selectOneBy(fingerprint=fingerprint)
        if result is None:
            return default
        return result

    def getByFingerprints(self, fingerprints):
        """See `IGPGKeySet`"""
        return IStore(GPGKey).find(
            GPGKey, GPGKey.fingerprint.is_in(fingerprints))

    def getGPGKeysForPerson(self, owner, active=True):
        if active is False:
            query = """
                active = false
                AND fingerprint NOT IN
                    (SELECT fingerprint FROM LoginToken
                     WHERE fingerprint IS NOT NULL
                           AND requester = %s
                           AND date_consumed is NULL
                    )
                """ % sqlvalues(owner.id)
        else:
            query = 'active=true'

        query += ' AND owner=%s' % sqlvalues(owner.id)

        return list(GPGKey.select(query, orderBy='id'))
