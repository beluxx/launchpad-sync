# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'TranslationTemplateItem',
    ]

from zope.interface import implementer

from lp.services.database.sqlbase import SQLBase
from lp.services.database.sqlobject import (
    ForeignKey,
    IntCol,
    )
from lp.translations.interfaces.translationtemplateitem import (
    ITranslationTemplateItem,
    )


@implementer(ITranslationTemplateItem)
class TranslationTemplateItem(SQLBase):
    """See `ITranslationTemplateItem`."""

    _table = 'TranslationTemplateItem'

    potemplate = ForeignKey(
        foreignKey='POTemplate', dbName='potemplate', notNull=True)
    sequence = IntCol(dbName='sequence', notNull=True)
    potmsgset = ForeignKey(
        foreignKey='POTMsgSet', dbName='potmsgset', notNull=True)
