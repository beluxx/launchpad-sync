POTMsgSet tests
===============

POTMsgSet represents messages to translate that a POTemplate file has.

In this test we'll be committing a lot to let changes replicate to the
standby database.

    >>> import transaction

We need to get a POTMsgSet object to perform this test.

    >>> from zope.component import getUtility
    >>> from lp.translations.model.translationmessage import (
    ...     TranslationMessage)
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> from lp.translations.interfaces.potmsgset import IPOTMsgSet

    >>> potemplate = factory.makePOTemplate()
    >>> potmsgset = factory.makePOTMsgSet(
    ...     potemplate=potemplate,
    ...     singular="bla")

Verify interface.

    >>> from lp.testing import verifyObject
    >>> verifyObject(IPOTMsgSet, potmsgset)
    True

We also need some time and date functions to do translation updates.

    >>> from datetime import datetime
    >>> import pytz


POTMsgSet.is_translation_credit and POTMsgSet.translation_credit_type
---------------------------------------------------------------------

A POTMsgSet can be translation credits. These have special msgids that may
differ for historical reason for the same type of credit. The property
is_translation_credit indicates if the POTMsgSet is translation credits. The
property translation_credit_type contains the type of translation credits.

    >>> print(potmsgset.is_translation_credit)
    False
    >>> print(potmsgset.translation_credits_type.title)
    Not a translation credits message

    >>> credits = factory.makePOTMsgSet(
    ...     potemplate, singular=u'translator-credits')
    >>> print(credits.is_translation_credit)
    True
    >>> print(credits.translation_credits_type.title)
    Gnome credits message


Plural forms
------------

Let's focus on handling of messages with plural forms.

An empty translation does not need to exist in the database.  If not,
a PlaceholderPOFile is used instead.

    >>> evolution = getUtility(IProductSet).getByName('evolution')
    >>> evolution_trunk = evolution.getSeries('trunk')
    >>> evolution_potemplate = evolution_trunk.getPOTemplate('evolution-2.2')
    >>> language_pt_BR = getUtility(
    ...     ILanguageSet).getLanguageByCode('pt_BR')
    >>> pt_BR_placeholderpofile = evolution_potemplate.getPlaceholderPOFile(
    ...     language_pt_BR)

We get a POTMsgSet and verify it's a singular form:

    >>> potmsgset = (
    ...     pt_BR_placeholderpofile.potemplate.getPOTMsgSetByMsgIDText(
    ...         'evolution addressbook'))
    >>> potmsgset.msgid_plural is None
    True

    >>> current = potmsgset.getCurrentTranslation(
    ...     evolution_potemplate, pt_BR_placeholderpofile.language,
    ...     evolution_potemplate.translation_side)
    >>> print(current)
    None
    >>> pt_BR_placeholder_current = (
    ...     potmsgset.getCurrentTranslationMessageOrDummy(
    ...         pt_BR_placeholderpofile))
    >>> pt_BR_placeholder_current.plural_forms
    1
    >>> pt_BR_placeholder_current.translations
    [None]

A TranslationMessage knows what language it is in.

    >>> print(pt_BR_placeholder_current.language.code)
    pt_BR

Using another placeholder pofile we'll get a POTMsgset that's not a singular
form:

    >>> language_apa = getUtility(ILanguageSet).getLanguageByCode('apa')
    >>> apa_placeholderpofile = evolution_potemplate.getPlaceholderPOFile(
    ...     language_apa)
    >>> plural_potmsgset = (
    ...     apa_placeholderpofile.potemplate.getPOTMsgSetByMsgIDText(
    ...         '%d contact', '%d contacts'))
    >>> print(apa_placeholderpofile.language.code)
    apa

We don't know anything about pluralforms for this language, so we fall
back to the most common case:

    >>> print(apa_placeholderpofile.language.pluralforms)
    None
    >>> apa_placeholder_current = (
    ...     plural_potmsgset.getCurrentTranslationMessageOrDummy(
    ...         apa_placeholderpofile))
    >>> apa_placeholder_current.plural_forms
    2
    >>> apa_placeholder_current.translations
    [None, None]

We can guess the pluralforms for this language through ILanguage.pluralforms:

    >>> language_ru = getUtility(ILanguageSet).getLanguageByCode('ru')
    >>> ru_placeholderpofile = evolution_potemplate.getPlaceholderPOFile(
    ...     language_ru)
    >>> ru_placeholder_current = (
    ...     plural_potmsgset.getCurrentTranslationMessageOrDummy(
    ...     	ru_placeholderpofile))

    >>> print(ru_placeholderpofile.language.pluralforms)
    3
    >>> ru_placeholder_current.plural_forms
    3
    >>> ru_placeholder_current.translations
    [None, None, None]


Missing forms
.............

Even when a message has a singular and a plural in English, a
translation does not have to cover all plural forms available in the
target language.

We call such a message incomplete, and undesirable as it is, it is still
gracefully accepted.

    >>> pofile_es = evolution_potemplate.getPOFileByLang('es')
    >>> plural_potmsgset = pofile_es.potemplate.getPOTMsgSetByMsgIDText(
    ...     u'%d contact', u'%d contacts')
    >>> pofile_es.plural_forms
    2
    >>> foobar = getUtility(IPersonSet).getByName('name16')
    >>> message = factory.makeCurrentTranslationMessage(
    ...     pofile_es, plural_potmsgset, foobar,
    ...     translations={0: u'foo %d', 1: None})
    >>> message.is_complete
    False
    >>> message = factory.makeCurrentTranslationMessage(
    ...     pofile_es, plural_potmsgset, foobar,
    ...     translations={0: None})
    >>> message.is_complete
    False


Extraneous forms
................

It's not normally possible to input more plural forms for a translated
message than the language has.  But that number is configurable, and can
change (particularly when it is first defined).

As an example, let's look at the Zapotec translation for PowerMonger.

    >>> pm_translation = factory.makePOFile('zap')
    >>> zap = pm_translation.language

The number of plural forms in the Zapotec language is not configured,
so for now, the system guesses that it has two.

    >>> print(zap.pluralforms)
    None
    >>> print(pm_translation.plural_forms)
    2

    >>> pm_template = pm_translation.potemplate
    >>> pm_potmsgset = factory.makePOTMsgSet(
    ...     pm_template, singular='%d keyboard', plural='%d keyboards')

The message we're looking at is translated to two plural forms.

    >>> message_with_two_forms = factory.makeCurrentTranslationMessage(
    ...     pm_translation, pm_potmsgset, pm_template.owner,
    ...     translations=['%d fu', '%d fuitl'])

When an otherwise identical translation with three comes along, the
third form is ignored because it falls outside the current 2 forms.
The "new" translation message is the same one we already had.

    >>> message_with_three_forms = factory.makeCurrentTranslationMessage(
    ...     pm_translation, pm_potmsgset, pm_template.owner,
    ...     translations=['%d fu', '%d fuitl', '%d fuitlx'])
    >>> message_with_three_forms == message_with_two_forms
    True

Based on the latest research, it is now decided that Zapotec has three
plural forms.  This time, uploading a three-form translation produces a
new translation message.

Carlos is a privileged translator that will do the updates.

    >>> carlos = getUtility(IPersonSet).getByName('carlos')
    >>> login('carlos@canonical.com')
    >>> zap.pluralforms = 3
    >>> zap.pluralexpression = 'n % 3'

    >>> message_with_three_forms = factory.makeCurrentTranslationMessage(
    ...     pm_translation, pm_potmsgset, pm_template.owner,
    ...     translations=['%d fu', '%d fuitl', '%d fuitlx'])
    >>> message_with_three_forms == message_with_two_forms
    False

Now it is discovered that the very controversial Zapotec really only has
a single form.

    >>> zap.pluralforms = 1

When a new translation is submitted, again identical in the first form,
no new message is created.  Instead, the closest existing match (the
one with two forms) is updated.

    >>> message_with_one_form = factory.makeCurrentTranslationMessage(
    ...     pm_translation, pm_potmsgset, pm_template.owner,
    ...     translations=['%d fu'])

    >>> message_with_one_form == message_with_two_forms
    True

This avoids the creation of redundant translation messages where
possible.


isTranslationNewerThan
----------------------

This method tells us whether the active translation was reviewed after
the given timestamp.

    >>> translationmessage = TranslationMessage.get(2)
    >>> potmsgset = translationmessage.potmsgset
    >>> from lp.translations.model.pofile import POFile
    >>> pofile = POFile.get(1)
    >>> translationmessage.date_reviewed.isoformat()
    '2005-04-07T13:19:17.601068+00:00'
    >>> potmsgset.isTranslationNewerThan(pofile,
    ...     datetime(2004, 11, 30, 7, 0, 0, tzinfo=pytz.UTC))
    True
    >>> potmsgset.isTranslationNewerThan(pofile,
    ...     datetime(2006, 11, 30, 7, 0, 0, tzinfo=pytz.UTC))
    False


External translation suggestions
--------------------------------

External translation suggestions are current, imported or suggested
translation for exactly the same English string, but in a different
translation template.

    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet

Suggestions between modules depend also on whether the other translation
template is available to all users or should be ignored because
either the product or distribution where it's attached is not using
translations anymore or the translation template is not current anymore.

We will use this helper function to print all suggestions found:

    >>> def print_suggestions(suggestions):
    ...     """Print IPOFile title, translation and where is it used."""
    ...     lines = []
    ...     for suggestion in suggestions:
    ...         usage = []
    ...         if suggestion.is_current_ubuntu:
    ...             usage.append('Launchpad')
    ...         if suggestion.is_current_upstream:
    ...             usage.append('Upstream')
    ...         if not usage:
    ...             usage.append('None')
    ...         pofile = suggestion.getOnePOFile()
    ...         lines.append('%s: %s (%s)' % (
    ...             pofile.title,
    ...             suggestion.translations[0],
    ...             ' & '.join(usage)))
    ...     for line in sorted(lines):
    ...         print(line)


POTMsgSet.getExternallyUsedTranslationMessages
----------------------------------------------

 On one side, we have a translation template for the evolution product.

    >>> evo_product_template = evolution_potemplate
    >>> print(evo_product_template.title)
    Template "evolution-2.2" in Evolution trunk

On the other, we have a translation template for the evolution package in
Ubuntu Hoary distribution.

    >>> templateset = getUtility(IPOTemplateSet)
    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> ubuntu_hoary = ubuntu.getSeries('hoary')
    >>> evo_hoary_package = ubuntu_hoary.getSourcePackage('evolution')
    >>> evo_distro_template = templateset.getSubset(
    ...     sourcepackagename=evo_hoary_package.sourcepackagename,
    ...     distroseries=ubuntu_hoary).getPOTemplateByName('evolution-2.2')
    >>> print(evo_distro_template.title)
    Template "evolution-2.2" in Ubuntu Hoary package "evolution"

Both, product and distribution use Launchpad Translations.

    >>> evolution.translations_usage.name
    'LAUNCHPAD'
    >>> ubuntu.translations_usage.name
    'LAUNCHPAD'

And both translation templates are current

    >>> evo_product_template.iscurrent
    True
    >>> evo_distro_template.iscurrent
    True

The "suggestive templates" cache is up to date.

    >>> def refresh_suggestive_templates_cache():
    ...     """Update the `SuggestivePOTemplate` cache."""
    ...     templateset.wipeSuggestivePOTemplatesCache()
    ...     templateset.populateSuggestivePOTemplatesCache()

    >>> refresh_suggestive_templates_cache()
    >>> transaction.commit()

We have the same message in both templates but with different
translations in Spanish:

    >>> from zope.security.proxy import removeSecurityProxy

    >>> spanish = pofile_es.language
    >>> evo_product_message = evo_product_template.getPOTMsgSetByMsgIDText(
    ...     ' cards')
    >>> evo_product_translation = (
    ...     evo_product_message.getCurrentTranslation(
    ...         evo_product_template, spanish,
    ...         evo_product_template.translation_side))
    >>> print(pretty(removeSecurityProxy(
    ...     evo_product_translation.translations)))
    [' tarjetas']
    >>> evo_distro_message = evo_distro_template.getPOTMsgSetByMsgIDText(
    ...     ' cards')
    >>> evo_distro_translation = (
    ...     evo_distro_message.getCurrentTranslation(
    ...         evo_distro_template, spanish,
    ...         evo_distro_template.translation_side))
    >>> print(pretty(removeSecurityProxy(
    ...     evo_distro_translation.translations)))
    [' caratas']

    >>> suggestions = (
    ...     evo_product_message.getExternallyUsedTranslationMessages(spanish))
    >>> print_suggestions(suggestions)
    Spanish (es) translation of evolution-2.2 in Ubuntu Hoary package
    "evolution":  caratas (Launchpad)
    Spanish (es) translation of evolution-2.2 in Ubuntu Hoary package
    "evolution":  tarjetas (Upstream)

    >>> suggestions = evo_distro_message.getExternallyUsedTranslationMessages(
    ...    spanish)
    >>> print_suggestions(suggestions)
    Spanish (es) translation of evolution-2.2 in Evolution trunk:
    tarjetas (Launchpad & Upstream)

We need to be logged in as an admin to do some special attribute
changes:

    >>> login('carlos@canonical.com')

When a translation template is set as not current, those translations
are not available as suggestions anymore:

    >>> evo_distro_template.iscurrent = False
    >>> refresh_suggestive_templates_cache()
    >>> transaction.commit()
    >>> suggestions = (
    ...     evo_product_message.getExternallyUsedTranslationMessages(spanish))
    >>> len(suggestions)
    0

The same happens if the distribution is not officially using
translations.

    >>> from lp.app.enums import ServiceUsage

    >>> ubuntu.translations_usage = ServiceUsage.NOT_APPLICABLE

    # We set the template as current again so we are sure that we don't show
    # suggestions just due to the change to the translations_usage flag.
    >>> evo_distro_template.iscurrent = True
    >>> transaction.commit()
    >>> suggestions = (
    ...     evo_product_message.getExternallyUsedTranslationMessages(spanish))
    >>> len(suggestions)
    0

And products not using translations officially have the same behaviour.

    >>> evolution.translations_usage = ServiceUsage.NOT_APPLICABLE
    >>> refresh_suggestive_templates_cache()
    >>> transaction.commit()
    >>> suggestions = evo_distro_message.getExternallyUsedTranslationMessages(
    ...    spanish)
    >>> len(suggestions)
    0

Let's restore the flags for next section.

    >>> ubuntu.translations_usage = ServiceUsage.LAUNCHPAD
    >>> evolution.translations_usage = ServiceUsage.LAUNCHPAD
    >>> refresh_suggestive_templates_cache()
    >>> transaction.commit()


POTMsgSet.getExternallySuggestedTranslationMessages
---------------------------------------------------

This method returns a set of submissions that have suggested translations
for the same msgid as the given POTMsgSet across the whole system.

We are going to work with the 'man' template in evolution package for
Ubuntu Hoary distribution.

    >>> evo_man_template = getUtility(IPOTemplateSet).getSubset(
    ...     sourcepackagename=evo_hoary_package.sourcepackagename,
    ...     distroseries=ubuntu_hoary).getPOTemplateByName('man')

Let's take a message 'test man page' that is translated into Spanish.

    >>> potmsgset_translated = evo_man_template.getPOTMsgSetByMsgIDText(
    ...     'test man page')
    >>> pofile = evo_man_template.getPOFileByLang('es')
    >>> print(pofile.title)
    Spanish (es) translation of man in Ubuntu Hoary package "evolution"
    >>> current = potmsgset_translated.getCurrentTranslation(
    ...     evo_man_template, pofile.language,
    ...     evo_man_template.translation_side)
    >>> print(pretty(removeSecurityProxy(current.translations)))
    ['just a translation']

It doesn't return other submissions done in the given IPOMsgSet because
the 'wiki' space is for any submission done outside that IPOMsgSet.

    # There is no other message with the same msgid in our system that has a
    # non active submission.
    >>> wiki_submissions = (
    ...     potmsgset_translated.getExternallySuggestedTranslationMessages(
    ...         pofile.language))
    >>> len(wiki_submissions)
    0

Now, we get a dummy message that has the same msgid as the previous one.
A dummy message is one that is not yet stored in our database, we use
them to be able to render those messages in our UI, once we get a
submission with a value for it, it's created in our database so it's not
dummy anymore.

    >>> pmount_hoary_package = ubuntu_hoary.getSourcePackage('pmount')
    >>> pmount_man_template = getUtility(IPOTemplateSet).getSubset(
    ...     sourcepackagename=pmount_hoary_package.sourcepackagename,
    ...     distroseries=ubuntu_hoary).getPOTemplateByName('man')
    >>> potmsgset_untranslated = pmount_man_template.getPOTMsgSetByMsgIDText(
    ...     'test man page')
    >>> language_es = getUtility(ILanguageSet).getLanguageByCode('es')
    >>> pofile = pmount_man_template.getPlaceholderPOFile(language_es)
    >>> print(pofile.title)
    Spanish (es) translation of man in Ubuntu Hoary package "pmount"

Given that it doesn't exist in our database, is impossible to have a
submission already for it.

    >>> current = potmsgset_untranslated.getCurrentTranslation(
    ...     pmount_man_template, pofile.language,
    ...     pmount_man_template.translation_side)
    >>> print(current)
    None
    >>> imported = potmsgset_untranslated.getOtherTranslation(
    ...     pofile.language, pmount_man_template.translation_side)
    >>> print(imported)
    None

This other dummy IPOMsgSet though, will get all submissions done in
pomsgset_translated (except ones with the same translation that is already
active) as it's another context.

    >>> wiki_submissions = (
    ...     potmsgset_untranslated.getExternallySuggestedTranslationMessages(
    ...         pofile.language))
    >>> print_suggestions(wiki_submissions)
    Spanish (es) translation of man in Ubuntu Hoary package "evolution":
    blah, blah, blah (None)
    Spanish (es) translation of man in Ubuntu Hoary package "evolution":
    lalalala (None)

However, if the hoary template version is not current and thus hidden,
we get no suggestions.

    >>> evo_man_template.iscurrent = False
    >>> refresh_suggestive_templates_cache()
    >>> transaction.commit()

    >>> wiki_submissions = (
    ...     potmsgset_untranslated.getExternallySuggestedTranslationMessages(
    ...         pofile.language))
    >>> len(wiki_submissions)
    0


Nor do we get any suggestions if the Ubuntu distribution is not using
Launchpad for translations.

    # We set the template as current again so we are sure that we don't show
    # suggestions just due to the change to the translations_usage flag.
    >>> evo_man_template.iscurrent = True
    >>> ubuntu.translations_usage = ServiceUsage.NOT_APPLICABLE
    >>> refresh_suggestive_templates_cache()
    >>> transaction.commit()

    >>> wiki_submissions = (
    ...     potmsgset_untranslated.getExternallyUsedTranslationMessages(
    ...         pofile.language))
    >>> len(wiki_submissions)
    0

POTMsgSet.getExternallySuggestedOrUsedTranslationMessages
---------------------------------------------------------

This helper combines both getExternallyUsedTranslationMessages and
getExternallySuggestedTranslationMessages into one call for more efficient
database access. It is intended for use whenever both
getExternallyUsedTranslationMessages and
getExternallySuggestedTranslationMessages will be used on the same potmsgset.

If we go back to the external translations available before, we can see we get
the same result for suggestions and used messages.

    >>> suggestions, used = (
    ...     potmsgset_untranslated
    ...       .getExternallySuggestedOrUsedTranslationMessages(
    ...         suggested_languages=[pofile.language],
    ...         used_languages=[pofile.language]))[pofile.language]
    >>> wiki_suggestions = (
    ...     potmsgset_untranslated.getExternallySuggestedTranslationMessages(
    ...         pofile.language))
    >>> wiki_used = (
    ...     potmsgset_untranslated.getExternallyUsedTranslationMessages(
    ...         pofile.language))
    >>> wiki_submissions == suggestions
    True
    >>> wiki_used == used
    True


Suggestions for translator credits
----------------------------------

Messages with translator credits are translated automatically by
Launchpad, so we should not get any suggestions for them.

To put 'external' suggestions in database, let's translate the
'translation-credits' message in alsa-utils template to Spanish.

    >>> alsa = getUtility(IProductSet).getByName('alsa-utils')
    >>> alsa_trunk = alsa.getSeries('trunk')
    >>> alsa_potemplate = alsa_trunk.getPOTemplate('alsa-utils')
    >>> translator_credits = alsa_potemplate.getPOTMsgSetByMsgIDText(
    ...     u'translation-credits')

    >>> spanish_pofile = alsa_potemplate.getPOFileByLang('es')
    >>> spanish = spanish_pofile.language

    >>> new_translation = factory.makeCurrentTranslationMessage(
    ...     spanish_pofile, translator_credits, carlos,
    ...     translations={0: u'Some Translator'})

    >>> current = translator_credits.getCurrentTranslation(
    ...     alsa_potemplate, spanish, alsa_potemplate.translation_side)
    >>> print(pretty(removeSecurityProxy(current.translations)))
    ['Some Translator']

Now, let's add 'translation-credits' message to a different POTemplate:

    >>> new_credits = evolution_potemplate.createMessageSetFromText(
    ...     singular_text=u'translation-credits', plural_text=None)

However, this one doesn't show up as external suggestion for Spanish.

    >>> new_credits.getExternallyUsedTranslationMessages(spanish)
    []
    >>> new_credits.getExternallySuggestedTranslationMessages(spanish)
    []

POTMsgSet.setSequence
---------------------

Finally, the new `IPOTMsgSet` should have an entry in the
`TranslationTemplateItem` table once we assign a sequence number.

First, we need a helper function to check whether the potmsgset exists
in the table or not.

    >>> def is_potmsgset_in_potemplate(potmsgset, potemplate):
    ...     items = {
    ...         potmsgset.id
    ...         for potmsgset in potemplate.getPOTMsgSets(prefetch=False)
    ...         }
    ...     return potmsgset.id in items

Let's create a new potmsgset object.

    >>> potmsgset = potemplate.createMessageSetFromText(
    ...     u'This is just a test', None)

If we assign the sequence == 0, the POTMsgSet object doesn't have an
entry in the TranslationTemplateItems:

    >>> item = potmsgset.setSequence(potemplate, 0)
    >>> is_potmsgset_in_potemplate(potmsgset, potemplate)
    False
    >>> potmsgset.getSequence(potemplate)
    0

The used number doesn't matter as long as it's higher than zero.

    >>> item = potmsgset.setSequence(potemplate, 99)
    >>> is_potmsgset_in_potemplate(potmsgset, potemplate)
    True
    >>> potmsgset.getSequence(potemplate)
    99

If we change it back to zero, it's removed from the table:

    >>> item = potmsgset.setSequence(potemplate, 0)
    >>> is_potmsgset_in_potemplate(potmsgset, potemplate)
    False
    >>> potmsgset.getSequence(potemplate)
    0


POTMsgSet.flags
---------------

The gettext format can associate flags with a POTMsgSet, such as "this
is a fuzzily matched message" or "this message follows C format-string
rules."  These flags are set in a comment starting with a comma, and
flags are separated by further commas.

    >>> from lp.translations.model.potmsgset import POTMsgSet
    >>> flagged_potmsgset = POTMsgSet(flagscomment=", fuzzy, c-format")

The flags property produces these as a neat list of flags.

    >>> def print_flags(potmsgset):
    ...     for flag in sorted(potmsgset.flags):
    ...         print('"%s"' % flag)
    ...     print('.')

    >>> print_flags(flagged_potmsgset)
    "c-format"
    "fuzzy"
    .

If the message has no flags, that list is empty.

    >>> print_flags(POTMsgSet())
    .
