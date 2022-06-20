Translation Relicensing Agreement
=================================

Translators who have previously submitted any translations through
Launchpad can decide whether they want their translations relicensed
under BSD or not.

    >>> from zope.component import getUtility
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.testing import verifyObject
    >>> from lp.translations.model.translationrelicensingagreement \
    ...     import TranslationRelicensingAgreement
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.translations.interfaces.translationsperson import (
    ...     ITranslationsPerson)
    >>> from lp.translations.interfaces.translationrelicensingagreement \
    ...     import ITranslationRelicensingAgreement
    >>> login('karl@canonical.com')
    >>> person = getUtility(IPersonSet).getByName('karl')
    >>> translations_person = ITranslationsPerson(person)
    >>> verifyObject(ITranslationsPerson, translations_person)
    True

When Karl has not made his selection yet, it is marked as None.

    >>> print(translations_person.translations_relicensing_agreement)
    None
    >>> choice = IStore(TranslationRelicensingAgreement).find(
    ...     TranslationRelicensingAgreement, person=person).one()
    >>> print(choice)
    None

Setting a value will create a new TranslationRelicensingAgreement
object.

    >>> translations_person.translations_relicensing_agreement = True
    >>> print(translations_person.translations_relicensing_agreement)
    True
    >>> choice = IStore(TranslationRelicensingAgreement).find(
    ...     TranslationRelicensingAgreement, person=person).one()
    >>> print(choice.allow_relicensing)
    True

A `choice` implements ITranslationRelicensingAgreement interface:

    >>> verifyObject(ITranslationRelicensingAgreement, choice)
    True

A translator can also change their mind later.

    >>> translations_person.translations_relicensing_agreement = False
    >>> print(translations_person.translations_relicensing_agreement)
    False
    >>> choice = IStore(TranslationRelicensingAgreement).find(
    ...     TranslationRelicensingAgreement, person=person).one()
    >>> print(choice.allow_relicensing)
    False
