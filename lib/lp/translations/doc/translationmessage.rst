TranslationMessage
==================

Let's do some imports we will need to test this class.

    >>> from zope.component import getUtility
    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> from lp.translations.interfaces.translationmessage import (
    ...     ITranslationMessage)
    >>> from lp.translations.interfaces.translator import ITranslatorSet
    >>> from lp.translations.model.pofile import DummyPOFile

    >>> login('carlos@canonical.com')
    >>> pofile_es = factory.makePOFile(language_code='es')
    >>> potemplate = pofile_es.potemplate
    >>> potmsgset = factory.makePOTMsgSet(potemplate=potemplate)

This class links the translations submitted by a translator with the
associated POFile and POTMsgSet.  TranslationMessage and
DummyTranslationMessage both implement ITranslationMessage:

    >>> translationmessage = factory.makeCurrentTranslationMessage(
    ...     potmsgset=potmsgset, pofile=pofile_es)
    >>> verifyObject(ITranslationMessage, translationmessage)
    True

    >>> dummy_message = potmsgset.getCurrentTranslationMessageOrDummy(
    ...     factory.makePOFile('xh'))
    >>> verifyObject(ITranslationMessage, dummy_message)
    True


plural_forms
------------

This property returns a number of plural forms needed for a
TranslationMessage to be 'complete', i.e. contain all the necessary
translations.

We can look at a POTMsgSet with no plural forms:

    >>> print(potmsgset.plural_text)
    None

Any TranslationMessage for such a POTMsgSet returns a single plural form in
the translation, no matter the number of plural forms defined for the
language:

    >>> serbian = getUtility(ILanguageSet)['sr']
    >>> serbian.pluralforms
    3
    >>> current_sr = potmsgset.getCurrentTranslationMessageOrDummy(
    ...     DummyPOFile(potemplate, serbian))
    >>> current_sr.plural_forms
    1

    >>> divehi = getUtility(ILanguageSet)['dv']
    >>> print(divehi.pluralforms)
    None
    >>> current_dv = potmsgset.getCurrentTranslationMessageOrDummy(
    ...     DummyPOFile(potemplate, divehi))
    >>> current_dv.plural_forms
    1

For any POTMsgSet using plural forms, we get a defined number of plural
forms per language (3 for Serbian, as specified in the language).

    >>> potmsgset_plural = factory.makePOTMsgSet(
    ...     potemplate=potemplate, singular=u"singular", plural=u"plural")

    >>> print(potmsgset_plural.plural_text)
    plural
    >>> serbian.pluralforms
    3
    >>> current_sr = potmsgset_plural.getCurrentTranslationMessageOrDummy(
    ...     DummyPOFile(potemplate, serbian))
    >>> current_sr.plural_forms
    3

In case the language doesn't have number of plural forms defined, we return
a default of 2, which is the most common number of plural forms:

    >>> print(divehi.pluralforms)
    None
    >>> current_dv = potmsgset_plural.getCurrentTranslationMessageOrDummy(
    ...     DummyPOFile(potemplate, divehi))
    >>> current_dv.plural_forms
    2


isHidden
--------

This method tells if a TranslationMessage is actually shown in the
web translation interface or not.

We have to commit transaction for every message update so we end up
with different timestamps on messages.

    >>> import transaction

We are working with a product with translations being restricted to
a single translation group.

    >>> productseries = potemplate.productseries
    >>> product = productseries.product
    >>> product.translationgroup = factory.makeTranslationGroup(product.owner)

    >>> from lp.translations.enums import TranslationPermission
    >>> product.translationpermission = TranslationPermission.STRUCTURED

The only Serbian reviewer in this translation group is 'name16' user.

    >>> foobar = getUtility(IPersonSet).getByName('name16')
    >>> sr_translation_reviewer = getUtility(ITranslatorSet).new(
    ...     product.translationgroup, serbian, foobar)

No Privileges Person is going to work on Serbian (sr) translation, with
the new PO file.

    >>> pofile_sr = potemplate.newPOFile('sr')
    >>> potmsgset = factory.makePOTMsgSet(potemplate=potemplate,
    ...     singular=u'evolution addressbook')

No Privileges Person can only submit a suggestion, which will not be
hidden.

    >>> nopriv = getUtility(IPersonSet).getByName('no-priv')
    >>> login('no-priv@canonical.com')

    >>> new_suggestion = potmsgset.submitSuggestion(
    ...     pofile_sr, nopriv, {0: u'suggestion'})
    >>> transaction.commit()
    >>> new_suggestion.isHidden(pofile_sr)
    False

'foobar' is a privileged translator that will do the updates.

    >>> login('foo.bar@canonical.com')

An imported translation is not hidden when submitted.

    >>> imported_translation = factory.makeCurrentTranslationMessage(
    ...     pofile_sr, potmsgset, foobar, current_other=True,
    ...     translations={ 0: 'imported' })
    >>> transaction.commit()
    >>> imported_translation.isHidden(pofile_sr)
    False

A previous suggestion is now hidden.

    >>> new_suggestion.isHidden(pofile_sr)
    True

A newly submitted non-imported translation is not hidden either.

    >>> current_translation = factory.makeCurrentTranslationMessage(
    ...     pofile_sr, potmsgset, foobar, current_other=False,
    ...     translations={ 0: 'current' })
    >>> transaction.commit()
    >>> current_translation.isHidden(pofile_sr)
    False

However, previous imported translation is not hidden yet.

    >>> imported_translation.isHidden(pofile_sr)
    False

If a new current translation is submitted, the old one is hidden.

    >>> new_current_translation = factory.makeCurrentTranslationMessage(
    ...     pofile_sr, potmsgset, foobar, current_other=False,
    ...     translations={ 0 : 'new' })
    >>> transaction.commit()
    >>> new_current_translation.isHidden(pofile_sr)
    False
    >>> current_translation.isHidden(pofile_sr)
    True

    >>> new_current_translation.isHidden(pofile_sr)
    False
    >>> imported_translation.isHidden(pofile_sr)
    False

If a non-privileged user submits another suggestion, it's not hidden,
and last current translation is not hidden either.

    >>> nopriv = getUtility(IPersonSet).getByName('no-priv')
    >>> login('no-priv@canonical.com')

    >>> another_suggestion = potmsgset.submitSuggestion(
    ...     pofile_sr, nopriv, {0: u'another suggestion'})
    >>> transaction.commit()
    >>> another_suggestion.isHidden(pofile_sr)
    False
    >>> new_current_translation.isHidden(pofile_sr)
    False


translations & all_msgstrs
--------------------------

The translations attribute is a list containing all translation strings
for the message, up to and including the last plural form it can have.

For a regular single-form message, that's always one.

    >>> login('foo.bar@canonical.com')
    >>> message = potmsgset.getCurrentTranslation(
    ...     potemplate, serbian, potemplate.translation_side)
    >>> for translation in message.translations:
    ...     print(translation)
    new

If the message has no actual translation, the translations attribute
contains just a None.

    >>> empty_message = potmsgset.submitSuggestion(
    ...     pofile_sr, foobar, {})
    >>> empty_message.translations
    [None]

For a message with plurals, it's the POFile's number of plural forms.

    >>> spanish = getUtility(ILanguageSet)['es']
    >>> plural_potmsgset = factory.makePOTMsgSet(potemplate=potemplate,
    ...                                          singular=u"%d contact",
    ...                                          plural=u"%d contacts")
    >>> plural_message = factory.makeCurrentTranslationMessage(
    ...     potmsgset=plural_potmsgset, pofile=pofile_es,
    ...     translations=[u'%d contacto', u'%d contactos'])
    >>> for translation in plural_message.translations:
    ...     print(translation)
    %d contacto
    %d contactos

If the message does not translate all those forms, we get None entries
in the list.

    >>> empty_message = plural_potmsgset.submitSuggestion(
    ...     pofile_sr, foobar, {})
    >>> empty_message.translations
    [None, None, None]

The all_msgstrs attribute is simpler.  It gives us the full list of
translations for all supported plural forms, even if they are None.
These are POTranslation references, not strings.

    >>> for translation in message.all_msgstrs:
    ...     if translation is None:
    ...         print('None')
    ...     else:
    ...         print(translation.translation)
    new
    None
    None
    None
    None
    None


Composing SQL involving plural forms
------------------------------------

SQL Queries involving the TranslationMessage.msgstr* attributes often
get repetitive.  We have some helper functions to make it easier on the
eyes.

    >>> from lp.translations.model.translationmessage import (
    ...     make_plurals_fragment, make_plurals_sql_fragment)

The helper function make_plurals_fragment repeats a fragment of text
for the number of plural forms we support (starting at zero).

    >>> print(make_plurals_fragment("x%(form)dx", ", "))
    x0x,
    x1x,
    x2x,
    x3x,
    x4x,
    x5x

Composing text like this happens most in WHERE clauses of SQL queries.
The make_plurals_sql_fragment helper adds some parentheses and spaces
where you might otherwise forget them--or want to.

    >>> print(make_plurals_sql_fragment("msgstr%(form)d IS NOT NULL"))
    (msgstr0 IS NOT NULL) AND
    (msgstr1 IS NOT NULL) AND
    (msgstr2 IS NOT NULL) AND
    (msgstr3 IS NOT NULL) AND
    (msgstr4 IS NOT NULL) AND
    (msgstr5 IS NOT NULL)

The sub-clauses don't have to be tied together with AND:

    >>> print(make_plurals_sql_fragment("msgstr%(form)d IS NULL", "OR"))
    (msgstr0 IS NULL) OR
    (msgstr1 IS NULL) OR
    (msgstr2 IS NULL) OR
    (msgstr3 IS NULL) OR
    (msgstr4 IS NULL) OR
    (msgstr5 IS NULL)

