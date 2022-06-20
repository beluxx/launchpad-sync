Rosetta gives Karma to the users that do some kind of actions.

This test documents when and why Rosetta does it.

Note, that once we commit the transaction, we need to fetch again any
SQLObject we need to use to be sure we have the right information. Seems
like SQLObjects are not persistent between transactions.

    >>> import transaction
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.karma import IKarmaActionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.translations.enums import RosettaImportStatus
    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue)
    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> from lp.translations.model.potemplate import POTemplate

    >>> translation_import_queue = getUtility(ITranslationImportQueue)
    >>> karma_action_set = getUtility(IKarmaActionSet)
    >>> rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts

Setup an event listener to help ensure karma is assigned when it should.

    >>> from lp.testing.karma import KarmaAssignedEventListener
    >>> karma_helper = KarmaAssignedEventListener()
    >>> karma_helper.register_listener()


Uploading a .pot file
=====================

The action of upload a .pot file is rewarded with some karma.
The .pot files are supposed to come always from upstream so the action
of upload it increases the value of our data because we are more up to date
with upstream.

Let's say that we have this .pot file to import:

    >>> potemplate_contents = br'''
    ... msgid ""
    ... msgstr ""
    ... "Content-Type: text/plain; charset=CHARSET\n"
    ...
    ... msgid "foo"
    ... msgstr ""
    ... '''
    >>> potemplate = POTemplate.get(1)

We are going to import it as the Rosetta expert team, like we do with
automatic imports from Ubuntu. In this case, we shouldn't give any kind
of karma to that user.

    >>> uploaded_by_maintainer = True
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     potemplate.path, potemplate_contents, uploaded_by_maintainer,
    ...     rosetta_experts, productseries=potemplate.productseries,
    ...     potemplate=potemplate)

    # Login as a rosetta expert to be able to change the import's status.
    >>> login('carlos@canonical.com')
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> entry_id = entry.id

The file data is stored in the Librarian, so we have to commit the transaction
to make sure it's stored properly.

    >>> transaction.commit()

We tell the PO template to import from the file data it has.  If any karma is
assigned to the team, our karma_helper will print it out here.

    >>> entry = translation_import_queue[entry_id]
    >>> potemplate = POTemplate.get(1)
    >>> (subject, message) = potemplate.importFromQueue(entry)

(Nothing printed means no karma was assigned)

    >>> transaction.commit()

Let's do the same import as the Foo Bar user.

    >>> personset = getUtility(IPersonSet)
    >>> foo_bar = personset.getByEmail('foo.bar@canonical.com')
    >>> login('foo.bar@canonical.com')

Do the import.

    >>> potemplate = POTemplate.get(1)
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     potemplate.path, potemplate_contents, uploaded_by_maintainer,
    ...     foo_bar, productseries=potemplate.productseries,
    ...     potemplate=potemplate)
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> entry_id = entry.id

The file data is stored in the Librarian, so we have to commit the transaction
to make sure it's stored properly.

    >>> transaction.commit()

Tell the PO template to import from the file data it has, and see the karma
being assigned.

    >>> entry = translation_import_queue[entry_id]
    >>> potemplate = POTemplate.get(1)
    >>> (subject, message) = potemplate.importFromQueue(entry)
    Karma added: action=translationtemplateimport, product=evolution
    >>> transaction.commit()


Uploading a .po file
====================

The action of upload a .po file is rewarded with some karma if it comes
from upstream. If it's just a translation update, we don't give karma, for
the upload action, you will get it from the translations you are adding.

Let's say that we have this .po file to import:

    >>> import datetime
    >>> import pytz
    >>> UTC = pytz.timezone('UTC')
    >>> pofile_contents = six.ensure_binary(r'''
    ... msgid ""
    ... msgstr ""
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ... "X-Rosetta-Export-Date: %s\n"
    ...
    ... msgid "foo"
    ... msgstr "bar"
    ... ''' % datetime.datetime.now(UTC).isoformat())
    >>> potemplate = POTemplate.get(1)
    >>> pofile = potemplate.getPOFileByLang('es')

As we can see, we don't have any information in that file about who
did the translations, so we will get that credit to the person that
did the upload.

First, we are going to import it as the Rosetta expert team, like we do with
automatic imports from Ubuntu. In this case, we shouldn't give any kind
of karma to that user.

Do the import.

    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, uploaded_by_maintainer,
    ...     rosetta_experts, productseries=potemplate.productseries,
    ...     potemplate=potemplate, pofile=pofile)
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> entry_id = entry.id

The file data is stored in the Librarian, so we have to commit the transaction
to make sure it's stored properly.

    >>> transaction.commit()

Tell the PO template to import from the file data it has.  If any karma is
assigned to the team, our karma_helper will print it out here.

    >>> potemplate = POTemplate.get(1)
    >>> entry = translation_import_queue[entry_id]
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> (subject, message) = pofile.importFromQueue(entry)
    >>> transaction.commit()


We attach the new file as comming from upstream, that means that we
will give karma only for the upload action.

    >>> potemplate = POTemplate.get(1)
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, uploaded_by_maintainer, foo_bar,
    ...     productseries=potemplate.productseries, potemplate=potemplate,
    ...     pofile=pofile)
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> entry_id = entry.id

The file data is stored in the Librarian, so we have to commit the transaction
to make sure it's stored properly.

    >>> transaction.commit()

Tell the PO file to import from the file data it has.

    >>> potemplate = POTemplate.get(1)
    >>> entry = translation_import_queue[entry_id]
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> (subject, message) = pofile.importFromQueue(entry)
    Karma added: action=translationimportupstream, product=evolution

Now, the user is going to upload a local edition of the .po file. In this
case, we will give karma *only* because the translation change.

    >>> pofile_contents = six.ensure_binary(r'''
    ... msgid ""
    ... msgstr ""
    ... "Content-Type: text/plain; charset=UTF-8\n"
    ... "X-Rosetta-Export-Date: %s\n"
    ...
    ... msgid "foo"
    ... msgstr "bars"
    ... ''' % datetime.datetime.now(UTC).isoformat())

We attach the new file as not comming from upstream.

    >>> potemplate = POTemplate.get(1)
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, not uploaded_by_maintainer, foo_bar,
    ...     productseries=potemplate.productseries, potemplate=potemplate,
    ...     pofile=pofile)
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> entry_id = entry.id

The file data is stored in the Librarian, so we have to commit the transaction
to make sure it's stored properly.

    >>> transaction.commit()

Tell the PO file to import from the file data it has.  The user has rights
to edit translations directly, so their suggestion is approved directly.
No karma is awarded for this action.

    >>> potemplate = POTemplate.get(1)
    >>> entry = translation_import_queue[entry_id]
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> (subject, message) = pofile.importFromQueue(entry)
    >>> transaction.commit()

Let's try the case when a file is uploaded, but no translation is changed.
To do this test, we are going to repeat previous import.

We import it again without changes and see that we don't get karma changes.

    >>> potemplate = POTemplate.get(1)
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path, pofile_contents, not uploaded_by_maintainer, foo_bar,
    ...     productseries=potemplate.productseries, potemplate=potemplate,
    ...     pofile=pofile)
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> entry_id = entry.id

The file data is stored in the Librarian, so we have to commit the transaction
to make sure it's stored properly.

    >>> transaction.commit()

Tell the PO file to import from the file data it has and see that no karma is
assigned.  If it was, it'd be printed after the call to importFromQueue().

    >>> potemplate = POTemplate.get(1)
    >>> entry = translation_import_queue[entry_id]
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> (subject, message) = pofile.importFromQueue(entry)
    >>> transaction.commit()


Translating from the web UI
===========================

Translating something using the website UI can give you three kind of karma
actions:

 - translationsuggestionadded: When you add a translation but you are not
   allowed to do modifications directly to those translations.
 - translationsuggestionapproved: When you added a translation that is
   actually used because you have edition rights or because a reviewer
   approved your suggestion.
 - translationreview: When you approve a translation from someone else as a
   valid translation to use.


Let's say that we are a translator that is not an editor for the team that
handles translations for a given pofile.

No Privileges Person is a translator that fits this requirement.

    >>> potemplate = POTemplate.get(1)
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> no_priv = personset.getByEmail('no-priv@canonical.com')
    >>> pofile.canEditTranslations(no_priv)
    False

We are going to add a suggestion that already exists from other user,
that should not add any kind of karma to this user.

    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText(u'foo')
    >>> new_translations = {0: 'bar'}
    >>> fuzzy = False
    >>> by_maintainer = False

And we can see as they won't get any karma activity from that, otherwise
it'd be printed after the call to set current translation.

    >>> translationmessage = factory.makeCurrentTranslationMessage(
    ...     pofile, potmsgset, no_priv, translations=new_translations,
    ...     current_other=by_maintainer)
    >>> flush_database_caches()

But now, they will provide a new suggestion.

    >>> new_translations = {0: u'somethingelse'}

At this moment, karma is assigned and thus is printed here.

    >>> no_priv = personset.getByEmail('no-priv@canonical.com')
    >>> potemplate = POTemplate.get(1)
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText(u'foo')
    >>> translationmessage = potmsgset.submitSuggestion(
    ...     pofile, no_priv, new_translations)
    Karma added: action=translationsuggestionadded, product=evolution
    >>> transaction.commit()

Now, a reviewer for the Spanish team is going to review that translation and
do other translations.

    >>> kurem = personset.getByEmail('kurem@debian.cz')

Now, they will approve a suggestion.  This will give them karma for
reviewing the suggestion and will also give karma to the user who made the
suggestion for it being approved.

    >>> potemplate = POTemplate.get(1)
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText(u'foo')
    >>> new_translations = {0: u'somethingelse'}
    >>> translationmessage = potmsgset.findTranslationMessage(
    ...     pofile, new_translations)
    >>> translationmessage.approve(pofile, kurem)
    Karma added: action=translationsuggestionapproved, product=evolution
    Karma added: action=translationreview, product=evolution
    >>> transaction.commit()

Finally, this reviewer, is going to add a new translation directly. They
should get karma for their translation, but not for a review.

    >>> kurem = personset.getByEmail('kurem@debian.cz')
    >>> potemplate = POTemplate.get(1)
    >>> pofile = potemplate.getPOFileByLang('es')
    >>> potmsgset = potemplate.getPOTMsgSetByMsgIDText(u'foo')
    >>> new_translations = {0: u'changed again'}
    >>> translationmessage = potmsgset.submitSuggestion(
    ...     pofile, kurem, new_translations)
    Karma added: action=translationsuggestionadded, product=evolution
    >>> translationmessage.approve(pofile, kurem)
    >>> transaction.commit()


IPOTemplate description change
==============================

When someone adds a description for an IPOTemplate, we give them some karma
because they are giving more information to our users about the usage of
that template.

We are going to use Sample Person for this test as they're the owner of the
product from where the IPOTemplate is and they have rights to change the
description.

    >>> sample_person = personset.getByEmail('test@canonical.com')
    >>> login('test@canonical.com')
    >>> form = {
    ...     u'field.owner': u'test@canonical.com',
    ...     u'field.name': u'test',
    ...     u'field.priority': u'0',
    ...     u'field.description': u'This is a new description',
    ...     u'field.actions.change': u'Change'}
    >>> potemplate_view = create_view(potemplate, '+edit', form=form)
    >>> potemplate_view.request.method = 'POST'

Let's see the description we have atm:

    >>> print(potemplate.description)
    Template for evolution in hoary

We do the update and see the karma being assigned.

    >>> status = potemplate_view.initialize()
    Karma added:
    action=translationtemplatedescriptionchanged, product=evolution

And the new one is:

    >>> print(potemplate.description)
    This is a new description

Now, let's ensure that we've covered every one of Rosetta's karma
actions.

    >>> from lp.registry.model.karma import KarmaCategory
    >>> translation_category = KarmaCategory.byName('translations')
    >>> for karma_action in translation_category.karmaactions:
    ...     assert karma_action in karma_helper.added_karma_actions, (
    ...         '%s was not test!' % karma_action.name)

Unregister the event listener to make sure we won't interfere in other tests.

    >>> karma_helper.unregister_listener()

