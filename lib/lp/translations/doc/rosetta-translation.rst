
Rosetta Translation Objects
===========================

This test demonstrates the complete hierarchy of Rosetta translation objects,
from POTemplate down to POTranslation.

Get a PO template.

    >>> from lp.translations.model.potemplate import POTemplate
    >>> template = POTemplate.get(1)
    >>> template.name == 'evolution-2.2'
    True

Check that the PO template has a certain message ID.

    >>> from lp.translations.model.pomsgid import POMsgID
    >>> pomsgid = POMsgID.getByMsgid('evolution addressbook')
    >>> template.hasMessageID(pomsgid, None)
    True

Get a Spanish PO file for this PO template

    >>> pofile = template.getPOFileByLang('es')

Get a translation for a particular message and check it has a translation.

    >>> potmsgset = factory.makePOTMsgSet(template)
    >>> spanish = pofile.language
    >>> translations = factory.makeTranslationsDict()
    >>> message = factory.makeCurrentTranslationMessage(
    ...     pofile, potmsgset, translations=translations)
    >>> translationmessage = potmsgset.getCurrentTranslation(
    ...     template, spanish, template.translation_side)
    >>> len(translationmessage.translations)
    1
    >>> translationmessage.is_current_upstream
    True

Get a person to create a translation with.

    >>> from lp.registry.model.person import Person
    >>> person = Person.get(1)
    >>> pofile.canEditTranslations(person)
    True

Add a translation.

    >>> import pytz
    >>> UTC = pytz.timezone('UTC')
    >>> message = factory.makeCurrentTranslationMessage(
    ...     pofile, potmsgset, translations=translations, current_other=True)
    >>> message.is_current_ubuntu
    True
    >>> message.is_current_upstream
    True
    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> flush_database_caches()

Check that this submission is now the active one for this msgset/pluralform

    >>> current = potmsgset.getCurrentTranslation(
    ...     template, spanish, template.translation_side)
    >>> current == message
    True
    >>> message.is_current_upstream
    True
    >>> message.msgstr0.translation == translations[0]
    True

Check that this submission is the upstream one

    >>> potmsgset.getOtherTranslation(
    ...     spanish, template.translation_side) == message
    True
    >>> message.is_current_upstream
    True

Test the origin enum column.

    >>> from lp.translations.interfaces.translationmessage import (
    ...     RosettaTranslationOrigin)
    >>> message.origin == RosettaTranslationOrigin.ROSETTAWEB
    True

Get a list of the translations again to check the new one has been added.

    >>> message.translations[0] == translations[0]
    True

Now we want to test the interaction of the "upstream" translations with the
"active translations". There are several things we want to be able to test.
First, let's setup some useful variables.

    >>> Pa = Person.get(50)
    >>> Pb = Person.get(46)
    >>> Pc = Person.get(16)

Pa, Pb and Pc are three useful Person's.

Let's pretend we've seen a new translation in the upstream PO files for
this project from Pa.

    >>> translations = { 0: u'bar' }
    >>> upstream_message = factory.makeCurrentTranslationMessage(
    ...     pofile, potmsgset=potmsgset, translator=Pa,
    ...     translations=translations, current_other=True)
    >>> flush_database_caches()

Make sure that the new submission is in fact from Pa.

    >>> upstream_message.submitter == Pa
    True

This is marked as current in both Ubuntu and upstream.

    >>> upstream_message.msgstr0.translation == u'bar'
    True

    >>> potmsgset.getCurrentTranslation(
    ...     template, spanish, template.translation_side) == upstream_message
    True

Excellent. This shows that activating a new upstream translation upon
detection works.

Now, let's add a translation from Pb, through the web.

    >>> translations = { 0: u'baz' }
    >>> message = factory.makeCurrentTranslationMessage(
    ...     pofile, potmsgset, translator=Pb, translations=translations)
    >>> flush_database_caches()
    >>> web_submission = potmsgset.getCurrentTranslation(
    ...     template, spanish, template.translation_side)

Make sure the new submission is from Pb.

    >>> web_submission.submitter == Pb
    True

This submission should now be active, but not from upstream. When we get a new
translation through the web, this updates the active selection but not the
upstream selection.

    >>> web_submission.msgstr0.translation == u'baz'
    True

    >>> potmsgset.getOtherTranslation(
    ...     spanish, template.translation_side) == web_submission
    False

In fact, the upstream submission should still be the original one, from Pa:

    >>> potmsgset.getOtherTranslation(
    ...     spanish, template.translation_side) == upstream_message
    True

And the lasttranslator for this pofile should be the one who submitted the
current translation.

    >>> pofile.lasttranslator == Pb
    True
