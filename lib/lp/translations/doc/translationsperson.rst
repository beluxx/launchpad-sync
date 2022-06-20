TranslationsPerson
==================

Adapting IPerson to an ITranslationsPerson yields a TranslationsPerson
object which provides translatable languages and translation history.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> personset = getUtility(IPersonSet)
    >>> from lp.translations.interfaces.translationsperson import (
    ...     ITranslationsPerson)

ITranslationsPerson.translatable_languages yields the same list, except it
leaves out US English and languages marked as non-visible such as 'zh' or
'de_DE'.

    >>> daf = personset.getByName('daf')
    >>> translations_daf = ITranslationsPerson(daf)
    >>> for language in translations_daf.translatable_languages:
    ...     print(language.code, language.englishname)
    en_GB  English (United Kingdom)
    ja     Japanese
    cy     Welsh

    >>> carlos = personset.getByName('carlos')
    >>> translations_carlos = ITranslationsPerson(carlos)
    >>> for language in translations_carlos.translatable_languages:
    ...     print(language.code, language.englishname)
    ca     Catalan
    es     Spanish

The IPerson interface offers a way of returning POFileTranslator records
for a Person:

    >>> for pt in translations_carlos.translation_history:
    ...     print(pt.pofile.title)
    English (en) trans... of pkgconf-mozilla in Ubuntu Hoary package "mozilla"
    Spanish (es) translation of alsa-utils in alsa-utils trunk
    Spanish (es) translation of man in Ubuntu Hoary package "evolution"
    Spanish (es) translation of evolution-2.2 in Evolution trunk
    Japanese (ja) tran... of evolution-2.2 in Ubuntu Hoary package "evolution"
    Spanish (es) trans... of evolution-2.2 in Ubuntu Hoary package "evolution"
