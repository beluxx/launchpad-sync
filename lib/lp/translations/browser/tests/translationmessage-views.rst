TranslationMessage View
=======================

On this section, we are going to test the view class for an
ITranslationMessage object.

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.translations.model.pofile import POFile
    >>> from lp.translations.model.translationmessage import (
    ...     TranslationMessage,
    ... )
    >>> from lp.services.webapp import canonical_url
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet

All the tests will be submitted as coming from Kurem, an editor for the
POFile that we are going to edit.

    >>> login("kurem@debian.cz")


No plural forms
---------------

We are going to see what happens if we get an entry for a language
without the plural form information.

    >>> translationmessage = TranslationMessage.get(1)
    >>> pofile = POFile.get(1)
    >>> language_tlh = getUtility(ILanguageSet).getLanguageByCode("tlh")
    >>> pofile_tlh = pofile.potemplate.getPlaceholderPOFile(language_tlh)
    >>> potmsgset = pofile_tlh.potemplate.getPOTMsgSetByMsgIDText(
    ...     "evolution addressbook"
    ... )
    >>> current_translationmessage = (
    ...     potmsgset.getCurrentTranslationMessageOrPlaceholder(pofile_tlh)
    ... )
    >>> translationmessage_page_view = create_view(
    ...     current_translationmessage, "+translate"
    ... )
    >>> translationmessage_page_view.initialize()

Here we can see that it's lacking that information.

    >>> print(translationmessage_page_view.context.language.pluralforms)
    None

And the view class detects it correctly.

    >>> translationmessage_page_view.has_plural_form_information
    False


Basic checks
------------

Now, we will use objects that we have in our database, instead of
placeholder ones.

    >>> server_url = "/".join(
    ...     [canonical_url(current_translationmessage), "+translate"]
    ... )
    >>> translationmessage.setPOFile(pofile)
    >>> translationmessage_page_view = create_view(
    ...     translationmessage, "+translate", server_url=server_url
    ... )
    >>> translationmessage_page_view.initialize()

We have the plural form information for this language.

    >>> print(translationmessage_page_view.context.language.pluralforms)
    2

And thus, the view class should know that it doesn't lacks the plural forms
information.

    >>> translationmessage_page_view.has_plural_form_information
    True

Also, we should get the timestamp when we started so we can detect changes
done when we started this request. We cannot check for its concrete value
or we could introduce a time bomb in the system so we check that it's not
None.

    >>> translationmessage_page_view.lock_timestamp is None
    False


The subview: TranslationMessageView
-----------------------------------

For the next tests, we grab the subview which is what holds information
that pertains to the POMsgSet rendering itself:

    >>> subview = translationmessage_page_view.translationmessage_view
    >>> subview.initialize()

The request didn't get any argument, and because that, we should get the
default values for the alternative language.

    >>> subview.sec_lang is None
    True

We are at the beginning because this subview is being used for the first
item.

    >>> subview.context.potmsgset.getSequence(pofile.potemplate)
    1

It does not have a plural message

    >>> subview.plural_text is None
    True

And thus, it only has one translation.

    >>> subview.pluralform_indices
    [0]

Which is the one we wanted.

    >>> print(subview.getCurrentTranslation(0))
    libreta de direcciones de Evolution

As we didn't submit the form, the getSubmittedTranslation method will
return None.

    >>> print(subview.getSubmittedTranslation(0))
    None

If we request a plural form that is not valid, we get an AssertionError.

    >>> subview.getCurrentTranslation(1)
    Traceback (most recent call last):
    ...
    AssertionError: There is no plural form #1 for Spanish (es) language

    >>> subview.getSubmittedTranslation(1)
    Traceback (most recent call last):
    ...
    AssertionError: There is no plural form #1 for Spanish (es) language

The translation on the other side is defined and same as the active one.

    >>> print(subview.getOtherTranslation(0))
    libreta de direcciones de Evolution

However, if we ask for incorrect plural form, we get an AssertionError.

    >>> subview.getOtherTranslation(1)
    Traceback (most recent call last):
    ...
    AssertionError: There is no plural form #1 for Spanish (es) language


Web presentation
----------------

Some characters are presented specially in the Web interface, and there are
functions to determine whether to advise translators about their presence.

We will use this helper function to simplify the test:

    # This is just an easy way to get different messages for all
    # available options to test.
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.app.errors import NotFoundError
    >>> from lp.services.propertycache import get_property_cache
    >>> from lp.translations.model.pomsgid import POMsgID
    >>> def changeMsgID(new_msgid):
    ...     potmsgset = removeSecurityProxy(subview.context.potmsgset)
    ...     try:
    ...         msgid = POMsgID.getByMsgid(new_msgid)
    ...     except NotFoundError:
    ...         msgid = POMsgID.new(new_msgid)
    ...     potmsgset.msgid_singular = msgid
    ...     del get_property_cache(potmsgset).singular_text
    ...     flush_database_updates()
    ...

First, text_has_tab() determines whether a message set contains any tabs.

    >>> subview.text_has_tab
    False

When we change the set to include a tab character, the function detects it.

    >>> changeMsgID("Foo\tBar")
    >>> subview.text_has_tab
    True

Similarly, text_has_newline() determines whether a message contains newlines.

    >>> changeMsgID("Foo Bar")
    >>> subview.text_has_newline
    False

    >>> changeMsgID("Foo\nBar")
    >>> subview.text_has_newline
    True

And text_has_leading_or_trailing_space() determines ... well, you can guess.

    >>> changeMsgID("Foo Bar")
    >>> subview.text_has_leading_or_trailing_space
    False

    >>> changeMsgID(" Leading space")
    >>> subview.text_has_leading_or_trailing_space
    True

    >>> changeMsgID("  Leading space")
    >>> subview.text_has_leading_or_trailing_space
    True

    >>> changeMsgID("Trailing space ")
    >>> subview.text_has_leading_or_trailing_space
    True

    >>> changeMsgID("Trailing space  ")
    >>> subview.text_has_leading_or_trailing_space
    True

    >>> changeMsgID("Leading\n Space  ")
    >>> subview.text_has_leading_or_trailing_space
    True

    >>> changeMsgID("Trailing \nSpace  ")
    >>> subview.text_has_leading_or_trailing_space
    True

    >>> changeMsgID("Trailing \r\nspace")
    >>> subview.text_has_leading_or_trailing_space
    True

    >>> import transaction
    >>> transaction.commit()


Submitting translations
-----------------------

A new translation is submitted through the view.

    >>> form = {
    ...     "lock_timestamp": "2006-11-28T13:00:00+00:00",
    ...     "alt": None,
    ...     "msgset_1": None,
    ...     "msgset_1_es_translation_0_radiobutton": (
    ...         "msgset_1_es_translation_0_new"
    ...     ),
    ...     "msgset_1_es_translation_0_new": "Foo",
    ...     "submit_translations": "Save &amp; Continue",
    ... }
    >>> translationmessage_page_view = create_view(
    ...     translationmessage, "+translate", form=form, server_url=server_url
    ... )
    >>> translationmessage_page_view.request.method = "POST"
    >>> translationmessage_page_view.initialize()
    >>> transaction.commit()

Now, let's see how the system prevents a submission that has a timestamp older
than when last current translation was submitted.

    >>> from zope import datetime as zope_datetime
    >>> old_timestamp_text = "2006-11-28T12:30:00+00:00"
    >>> old_timestamp = zope_datetime.parseDatetimetz(old_timestamp_text)

We can see here that translation in pomsgset is newer than old_timestamp.

    >>> potmsgset.isTranslationNewerThan(pofile, old_timestamp)
    True

And current value

    >>> for translation in potmsgset.getCurrentTranslation(
    ...     pofile.potemplate,
    ...     pofile.language,
    ...     pofile.potemplate.translation_side,
    ... ).translations:
    ...     print(translation)
    Foo

We do the submission with that lock_timestamp.

    >>> server_url = "/".join(
    ...     [canonical_url(translationmessage), "+translate"]
    ... )
    >>> form = {
    ...     "lock_timestamp": old_timestamp_text,
    ...     "alt": None,
    ...     "msgset_1": None,
    ...     "msgset_1_es_translation_0_radiobutton": (
    ...         "msgset_1_es_translation_0_new"
    ...     ),
    ...     "msgset_1_es_translation_0_new": "Foos",
    ...     "submit_translations": "Save &amp; Continue",
    ... }
    >>> translationmessage_page_view = create_view(
    ...     translationmessage, "+translate", form=form, server_url=server_url
    ... )
    >>> translationmessage_page_view.request.method = "POST"
    >>> translationmessage_page_view.initialize()
    >>> for (
    ...     notification
    ... ) in translationmessage_page_view.request.notifications:
    ...     print(notification.message)
    There is an error in the translation you provided. Please correct it
    before continuing.
    >>> print(translationmessage_page_view.error)
    This translation has changed since you last saw it.  To avoid
    accidentally reverting work done by others, we added your
    translations as suggestions.  Please review the current values.
    >>> transaction.commit()

This submission is not saved because there is another modification, this
means that timestamps remain unchanged.

    >>> potmsgset.isTranslationNewerThan(pofile, old_timestamp)
    True

And active text too

    >>> for translation in potmsgset.getCurrentTranslation(
    ...     pofile.potemplate,
    ...     pofile.language,
    ...     pofile.potemplate.translation_side,
    ... ).translations:
    ...     print(translation)
    Foo


Bogus translation submission
----------------------------

What would happen if we get a submit for another msgset that isn't being
considered?

    >>> server_url = "/".join(
    ...     [canonical_url(translationmessage), "+translate"]
    ... )
    >>> form = {
    ...     "lock_timestamp": "2006-11-28 13:00:00 UTC",
    ...     "alt": None,
    ...     "msgset_2": None,
    ...     "msgset_2_es_translation_0_new": "Foo",
    ...     "msgset_2_es_translation_0_new_checkbox": True,
    ...     "submit_translations": "Save &amp; Continue",
    ... }
    >>> translationmessage_page_view = create_view(
    ...     translationmessage, "+translate", form=form, server_url=server_url
    ... )
    >>> translationmessage_page_view.request.method = "POST"
    >>> translationmessage_page_view.initialize()

The list of translations parsed will be empty because the submission is
ignored:

    >>> translationmessage_page_view.form_posted_translations
    {}

And since this was a POST, we don't even build the subview:

    >>> translationmessage_page_view.translationmessage_view is None
    True


TranslationMessageSuggestions
-----------------------------

This class keeps all suggestions available for a concrete
ITranslationMessage.

    >>> from zope.component import getUtility
    >>> from lp.translations.browser.translationmessage import (
    ...     TranslationMessageSuggestions,
    ... )
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet

We are going to work with Evolution's evolution-2.2 template.

    >>> potemplate_set = getUtility(IPOTemplateSet)
    >>> potemplates = potemplate_set.getAllByName("evolution-2.2")
    >>> potemplate_trunk = potemplates[0]
    >>> potemplate_hoary = potemplates[1]
    >>> print(potemplate_trunk.title)
    Template "evolution-2.2" in Evolution trunk
    >>> print(potemplate_hoary.title)
    Template "evolution-2.2" in Ubuntu Hoary package "evolution"

For alternative suggestions we need two languages, the one being
translated and other one providing suggestions. We will use Japanese
as the language to get suggestions for because it has less plural forms
than the other chosen language, Spanish.

    # Japanese translation for this template doesn't exist yet in our
    # database, we need to create it first.
    >>> pofile_ja = potemplate_trunk.newPOFile("ja")
    >>> pofile_ja.language.pluralforms
    1
    >>> pofile_es = potemplate_trunk.getPOFileByLang("es")
    >>> pofile_es.language.pluralforms
    2

We are going to work with a plural form message.

    >>> potmsgset = potemplate_trunk.getPOTMsgSetByMsgIDText(
    ...     "%d contact", "%d contacts"
    ... )
    >>> potmsgset.msgid_plural is None
    False

Also, we are going to create a new translation for the Japanese
language that will be used as the suggestion.

    >>> carlos = getUtility(IPersonSet).getByName("carlos")
    >>> login("carlos@canonical.com")
    >>> translation_message_ja = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile_ja,
    ...     potmsgset=potmsgset,
    ...     translator=carlos,
    ...     reviewer=carlos,
    ...     translations={0: "Foo %d"},
    ... )
    >>> for translation in translation_message_ja.translations:
    ...     print(translation)
    ...
    Foo %d

Let's get current message in Spanish.

# XXX JeroenVermeulen 2010-11-19: Hard-coding the wrong translation side
# here to make the test pass.  Once we update the is_current_* flags in
# the sample data, this should start to fail and then we can update it
# to use pofile_es.potemplate.translation_side instead.
    >>> from lp.translations.interfaces.side import TranslationSide
    >>> translation_message_es = potmsgset.getCurrentTranslation(
    ...     pofile_es.potemplate, pofile_es.language, TranslationSide.UBUNTU
    ... )

And we prepare the ITranslationMessageSuggestions object for the higher
Spanish plural form.

    >>> suggestions = TranslationMessageSuggestions(
    ...     title="Testing",
    ...     translation=translation_message_es,
    ...     submissions=[translation_message_ja],
    ...     user_is_official_translator=True,
    ...     form_is_writeable=True,
    ...     plural_form=(pofile_es.language.pluralforms - 1),
    ... )

Which produces no suggestions, because Japanese only has one form but
Spanish has two.

    >>> print(suggestions.submissions)
    []

However, when we use the first plural form, which exists in both
languages...

    >>> suggestions = TranslationMessageSuggestions(
    ...     title="Testing",
    ...     translation=translation_message_es,
    ...     submissions=[translation_message_ja],
    ...     user_is_official_translator=True,
    ...     form_is_writeable=True,
    ...     plural_form=0,
    ... )

... we get suggestions.

    >>> len(suggestions.submissions)
    1
    >>> submission = suggestions.submissions[0]
    >>> for attr in sorted(dir(submission)):
    ...     if not attr.startswith("_"):
    ...         print("%s: %s" % (attr, getattr(submission, attr)))
    ...
    date_created: ...
    id: ...
    is_empty: False
    is_local_to_pofile: False
    is_traversable: ...
    language: ...
    legal_warning: False
    origin_html_id: msgset_15_ja_suggestion_..._0_origin
    person: ...
    plural_index: 0
    pofile: ...
    potmsgset: ...
    row_html_id:
    suggestion_dismissable_class: msgset_15_dismissable_button
    suggestion_html_id: msgset_15_ja_suggestion_..._0
    suggestion_text: Foo <code>%d</code>
    translation_html_id: msgset_15_es_translation_0
    translationmessage: ...

Another reason why a suggestion might not have translations for all
plural forms is that it was submitted as a translation for an English
message that didn't have a plural.

Here, an identical message is added to the two Evolution templates: the
"trunk" one and the one in Ubuntu Hoary.  But one of the English strings
is in a single form only, whereas the other has a singular and a plural.

    >>> singular_id = "This message has %d form."
    >>> plural_id = "This message has %d forms."
    >>> pofile_simple = potemplate_trunk.getPOFileByLang("es")
    >>> pofile_plural = potemplate_hoary.getPOFileByLang("es")
    >>> potmsgset_simple = potemplate_trunk.createMessageSetFromText(
    ...     singular_id, None
    ... )
    >>> potmsgset_plural = potemplate_hoary.createMessageSetFromText(
    ...     singular_id, plural_id
    ... )

Carlos translates both.  The single-form one is simple; for the other he
provides a complete translation including both the singular and the
plural form.

    >>> translation_message_simple = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile_simple,
    ...     potmsgset=potmsgset_simple,
    ...     translator=carlos,
    ...     reviewer=carlos,
    ...     translations={0: "%d forma"},
    ... )
    >>> translation_message_plural = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile_plural,
    ...     potmsgset=potmsgset_plural,
    ...     translator=carlos,
    ...     reviewer=carlos,
    ...     translations={0: "%d forma", 1: "%d formas"},
    ... )

The single-form translation shows up as a suggestion for the singular
translation of the two-form message.

    >>> suggestions = TranslationMessageSuggestions(
    ...     title="Testing",
    ...     translation=translation_message_plural,
    ...     submissions=[translation_message_simple],
    ...     user_is_official_translator=True,
    ...     form_is_writeable=True,
    ...     plural_form=0,
    ... )
    >>> len(suggestions.submissions)
    1

For the plural translation of the same message, however, that
translation provides no text and so is ignored.

    >>> suggestions = TranslationMessageSuggestions(
    ...     title="Testing",
    ...     translation=translation_message_plural,
    ...     submissions=[translation_message_simple],
    ...     user_is_official_translator=True,
    ...     form_is_writeable=True,
    ...     plural_form=1,
    ... )
    >>> len(suggestions.submissions)
    0


Sharing and diverging messages
------------------------------

When there is an existing shared translation, one gets an option
to diverge it when on a zoomed-in view (when looking that particular
message).

    >>> pofile = factory.makePOFile("sr")
    >>> potemplate = pofile.potemplate
    >>> potmsgset = factory.makePOTMsgSet(potemplate, sequence=1)
    >>> translationmessage = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile,
    ...     potmsgset=potmsgset,
    ...     translations=["shared translation"],
    ... )
    >>> translationmessage.setPOFile(pofile)
    >>> server_url = "/".join(
    ...     [canonical_url(translationmessage), "+translate"]
    ... )
    >>> translationmessage_page_view = create_view(
    ...     translationmessage, "+translate", server_url=server_url
    ... )
    >>> translationmessage_page_view.initialize()
    >>> subview = translationmessage_page_view.translationmessage_view
    >>> subview.initialize()
    >>> subview.zoomed_in_view
    True
    >>> subview.allow_diverging
    True

A shared translation is not explicitly shown, since the current one is
the shared translation.

    >>> print(subview.shared_translationmessage)
    None

When looking at the entire POFile, diverging is not allowed.

    >>> server_url = "/".join([canonical_url(pofile), "+translate"])
    >>> pofile_view = create_view(pofile, "+translate", server_url=server_url)
    >>> pofile_view.initialize()
    >>> subview = pofile_view.translationmessage_views[0]
    >>> subview.initialize()
    >>> subview.zoomed_in_view
    False
    >>> subview.allow_diverging
    False

With a diverged translation, the shared translation is explicitly offered
among one of the suggestions, and we are not offered to diverge the
translation further, since it's already diverged.

    >>> diverged_message = factory.makeDivergedTranslationMessage(
    ...     pofile=pofile,
    ...     potmsgset=potmsgset,
    ...     translations=["diverged translation"],
    ... )
    >>> diverged_message.setPOFile(pofile)
    >>> translationmessage_page_view = create_view(
    ...     diverged_message, "+translate", server_url=server_url
    ... )
    >>> translationmessage_page_view.initialize()
    >>> subview = translationmessage_page_view.translationmessage_view
    >>> subview.initialize()
    >>> subview.zoomed_in_view
    True
    >>> subview.allow_diverging
    False
    >>> subview.shared_translationmessage == translationmessage
    True
