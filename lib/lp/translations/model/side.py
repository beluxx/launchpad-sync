# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`TranslationSideTraits` implementations."""

__all__ = [
    'TranslationSideTraits',
    'TranslationSideTraitsSet',
    ]

from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.translations.interfaces.side import (
    ITranslationSideTraits,
    ITranslationSideTraitsSet,
    TranslationSide,
    )


@implementer(ITranslationSideTraits)
class TranslationSideTraits:
    """See `ITranslationSideTraits`."""

    def __init__(self, side, flag_name, displayname):
        self.side = side
        self.other_side_traits = None
        self.flag_name = flag_name
        self.displayname = displayname

    def getFlag(self, translationmessage):
        """See `ITranslationSideTraits`."""
        return getattr(translationmessage, self.flag_name)

    def getCurrentMessage(self, potmsgset, potemplate, language):
        """See `ITranslationSideTraits`."""
        return potmsgset.getCurrentTranslation(
            potemplate, language, self.side)

    def setFlag(self, translationmessage, value):
        """See `ITranslationSideTraits`."""
        naked_tm = removeSecurityProxy(translationmessage)
        setattr(naked_tm, self.flag_name, value)


@implementer(ITranslationSideTraitsSet)
class TranslationSideTraitsSet:
    """See `ITranslationSideTraitsSet`."""

    def __init__(self):
        upstream = TranslationSideTraits(
            TranslationSide.UPSTREAM, 'is_current_upstream', "upstream")
        ubuntu = TranslationSideTraits(
            TranslationSide.UBUNTU, 'is_current_ubuntu', "Ubuntu")
        ubuntu.other_side_traits = upstream
        upstream.other_side_traits = ubuntu
        self.traits = dict(
            (traits.side, traits)
            for traits in [ubuntu, upstream])

    def getTraits(self, side):
        """See `ITranslationSideTraitsSet`."""
        return self.traits[side]

    def getForTemplate(self, potemplate):
        """See `ITranslationSideTraitsSet`."""
        return self.getTraits(potemplate.translation_side)

    def getAllTraits(self):
        """See `ITranslationSideTraitsSet`."""
        return self.traits
