POFileTranslateView
===================

On this section, we are going to test the view class for an IPOFile.

First, we need some imports.

    >>> import io
    >>> from zope.publisher.browser import FileUpload
    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> from lp.translations.model.translationmessage import (
    ...     TranslationMessage, DummyTranslationMessage)
    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue)
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet)
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet

All the tests will be submitted as coming from the No Privilege person.

    >>> login('no-priv@canonical.com')

Now it's time to test the initialization of the view class.

    >>> sourcepackagenameset = getUtility(ISourcePackageNameSet)
    >>> sourcepackagename = sourcepackagenameset['evolution']
    >>> distributionset = getUtility(IDistributionSet)
    >>> distribution = distributionset['ubuntu']
    >>> series = distribution['hoary']
    >>> potemplateset = getUtility(IPOTemplateSet)
    >>> potemplatesubset = potemplateset.getSubset(
    ...     distroseries=series, sourcepackagename=sourcepackagename)
    >>> potemplate = potemplatesubset['evolution-2.2']
    >>> pofile_es = potemplate.getPOFileByLang('es')
    >>> form = {'show': 'all' }
    >>> pofile_view = create_view(pofile_es, '+translate', form=form)
    >>> pofile_view.initialize()

An IPOFile knows (or sometimes has to guess) its number of pluralforms.  In
this case it's 2, the most common number.

    >>> pofile_es.language.pluralforms
    2

Thus the view class also knows about the plural forms information.

    >>> pofile_view.has_plural_form_information
    True

We know that we want all messages.

    >>> print(pofile_view.show)
    all

This time, we are going to see what happens if we get an IPOFile without
the plural form information.

    >>> language_tlh = getUtility(ILanguageSet).getLanguageByCode('tlh')
    >>> pofile_tlh = potemplate.getDummyPOFile(language_tlh)
    >>> form = {'show': 'all' }
    >>> pofile_view = create_view(pofile_tlh, '+translate', form=form)
    >>> pofile_view.initialize()

Here we can see that it's lacking that information.

    >>> pofile_tlh.language.pluralforms is None
    True

And the view class detects it correctly.

    >>> pofile_view.has_plural_form_information
    False

Check the argument to filter messagesets.

    >>> form = {'show': 'translated'}
    >>> pofile_view = create_view(pofile_es, '+translate', form=form)
    >>> pofile_view.initialize()

Yeah, it detects it correctly and stores the attribute as it should be.

    >>> print(pofile_view.show)
    translated

Let's move to the navigation URLS testing.

We get a request without any argument.

    >>> form = {'show': 'all' }
    >>> pofile_view = create_view(pofile_es, '+translate', form=form)
    >>> pofile_view.initialize()

It's time to test that we get the right message sets from the submitted form.

    >>> form = {'show': 'all' }
    >>> pofile_view = create_view(pofile_es, '+translate', form=form)
    >>> pofile_view.initialize()

We get the first entry that should be in the form, the one with id == 130.

    >>> for potmsgset in pofile_view._getSelectedPOTMsgSets():
    ...     if potmsgset.id == 130:
    ...         break

The id for this message set is the one we expected.

    >>> potmsgset.id
    130

And as it's the first entry, its sequence number is also the right one.

    >>> potmsgset.getSequence(pofile_es.potemplate)
    1

Test that the associated text to translate is the one we want. We initialize
a view for it, which will be the last in the pofile_view's list.

    >>> len(pofile_view.translationmessage_views)
    10
    >>> pofile_view._buildTranslationMessageViews([potmsgset])
    >>> len(pofile_view.translationmessage_views)
    11
    >>> translationmessage_view = pofile_view.translationmessage_views[-1]
    >>> translationmessage_view.initialize()
    >>> print(translationmessage_view.singular_text)
    evolution addressbook

It does not have a plural form.

    >>> translationmessage_view.plural_text is None
    True

And thus, it only has one translation.

    >>> translationmessage_view.pluralform_indices
    [0]

Which is the one we wanted.

    >>> for translation in translationmessage_view.context.translations:
    ...     print(translation)
    libreta de direcciones de Evolution

To help the JavaScript key navigation the view is exposing the autofocus
field and a list of all translation fields ordered by the way they are
listed in the page.

    >>> for translationmessage_view in (
    ...     pofile_view.translationmessage_views):
    ...     translationmessage_view.initialize()
    >>> print(pofile_view.autofocus_html_id)
    msgset_130_es_translation_0_new
    >>> print(pofile_view.translations_order)
    msgset_130_es_translation_0_new msgset_131_es_translation_0_new
    msgset_132_es_translation_0_new msgset_133_es_translation_0_new
    msgset_134_es_translation_0_new msgset_135_es_translation_0_new
    msgset_136_es_translation_0_new msgset_137_es_translation_0_new
    msgset_138_es_translation_0_new msgset_139_es_translation_0_new
    msgset_130_es_translation_0_new

It's time to check the submission of translations and the IPOFile statistics
update.

But first, let's see current values.

    >>> stats = pofile_es.updateStatistics()
    >>> pofile_es.updatesCount()
    0
    >>> pofile_es.rosettaCount()
    7

Now we do a submission with new translations:

 - msgset_*_new are the translations we are adding.
 - msgset_*_new_checkbox are the flags to tell us whether the translation
   submitted in its corresponding msgset_*_new variable should be taken in
   consideration (if True) or just ignored (False).

    >>> form = {
    ...     'batch': '10',
    ...     'start': '0',
    ...     'show': 'all',
    ...     'lock_timestamp': '2006-11-28 13:00:00 UTC',
    ...     'msgset_130': None,
    ...     'msgset_130_es_translation_0_radiobutton':
    ...         'msgset_130_es_translation_0_new',
    ...     'msgset_130_es_translation_0_new': 'Foo',
    ...     'msgset_138': None,
    ...     'msgset_138_es_translation_0_radiobutton':
    ...         'msgset_138_es_translation_0_new',
    ...     'msgset_138_es_translation_0_new': 'Bar',
    ...     'submit_translations': 'Save &amp; Continue'}
    >>> pofile_view = create_view(pofile_es, '+translate', form=form)
    >>> pofile_view.request.method = 'POST'
    >>> pofile_view.initialize()

And check again.

    >>> stats = pofile_es.updateStatistics()
    >>> pofile_es.updatesCount()
    1
    >>> pofile_es.rosettaCount()
    8

The messages displayed on the +translate page are always in ascending order of
their POTMsgSets' sequence numbers.

    >>> for potmsgset in pofile_view._getSelectedPOTMsgSets():
    ...     print(potmsgset.getSequence(pofile_es.potemplate))
    1
    2
    3
    4
    5
    6
    7
    8
    9
    10
    11
    12
    13
    14
    15
    16
    17
    18
    19
    20
    21
    22

Also, we get redirected to the next batch.

    >>> pofile_view.request.response.getHeader('Location')
    'http://127.0.0.1?memo=10&start=10'

The message's sequence is the position of that message in latest imported
template. We are going to test now what happens when we submit a potmsgset
that has a sequence == 0. It means that that msgset is disabled and we don't
serve such messages in our translation form, but we could get it in some
situations, like when this set of actions happen:

 - A user gets a translation form for the template X.
 - A new template X is imported into the system that removes some messages
   from the previous import.
 - Previous user, submits the translation form they got for the old template
   X.

The problem here is that some of the messages on that form are disabled so
their sequence is 0.

    >>> from lp.translations.model.potmsgset import POTMsgSet
    >>> potmsgset = POTMsgSet.get(161)
    >>> item = potmsgset.setSequence(pofile_es.potemplate, 0)
    >>> potmsgset.getSequence(pofile_es.potemplate)
    0
    >>> form = {
    ...     'batch': '10',
    ...     'start': '0',
    ...     'show': 'untranslated',
    ...     'lock_timestamp': '2006-11-28 13:00:00 UTC',
    ...     'msgset_161': None,
    ...     'msgset_161_es_translation_0_radiobutton':
    ...         'msgset_161_es_translation_0_new',
    ...     'msgset_161_es_translation_0_new': 'Foo',
    ...     'submit_translations': 'Save &amp; Continue'}
    >>> pofile_view = create_view(pofile_es, '+translate', form=form)
    >>> pofile_view.request.method = 'POST'
    >>> pofile_view.initialize()
    >>> flush_database_caches()

And we can see that we didn't get errors.

    >>> translationmessage = potmsgset.getCurrentTranslation(
    ...     pofile_es.potemplate, pofile_es.language,
    ...     pofile_es.potemplate.translation_side)
    >>> for translation in translationmessage.translations:
    ...     print(translation)
    Foo
    >>> pofile_view.errors
    {}

The view pre-populates the internal "relevant submissions" caches of the
POMsgSets it shows.  We pick one with a nice list of POSubmissions and see
what's inside.

#    >>> pomsgset = POMsgSet.get(604)
#    >>> pomsgset._hasSubmissionsCaches()
#    True
#    >>> pomsgset.id
#    604
#    >>> pomsgset.potmsgset.id
#    144
#    >>> for text in pomsgset.active_texts:
#    ...     print(text)
#    %d contacto
#    %d contactos
#    >>> for text in pomsgset.published_texts:
#    ...     print(text)
#    %d contacto
#    %d contactos
#    >>> list(pomsgset.getNewSubmissions(0))
#    []
#    >>> list(pomsgset.getNewSubmissions(1))
#    []
#    >>> for submission in pomsgset.getCurrentSubmissions(0):
#    ...     print(submission.datecreated.isoformat())
#    2005-04-07T...
#    >>> for submission in pomsgset.getCurrentSubmissions(1):
#    ...     print(submission.datecreated.isoformat())
#    2005-04-07T...

The POMsgSet we're looking at had its submissions cache pre-populated by the
view object, which is faster because it can fetch all its information from the
database in bulk.  If we force the POMsgSet to fill its own caches, using its
own logic to fetch just its own submissions from the database, we get the
exact same results.

#    >>> pomsgset._invalidateSubmissionsCaches()
#    >>> pomsgset._hasSubmissionsCaches()
#    False
#    >>> pomsgset.initializeSubmissionsCaches()
#    >>> pomsgset.id
#    604
#    >>> pomsgset.potmsgset.id
#    144
#    >>> for text in pomsgset.active_texts:
#    ...     print(text)
#    %d contacto
#    %d contactos
#    >>> for text in pomsgset.published_texts:
#    ...     print(text)
#    %d contacto
#    %d contactos
#    >>> list(pomsgset.getNewSubmissions(0))
#    []
#    >>> list(pomsgset.getNewSubmissions(1))
#    []
#    >>> for submission in pomsgset.getCurrentSubmissions(0):
#    ...     print(submission.datecreated.isoformat())
#    2005-04-07T...
#    >>> for submission in pomsgset.getCurrentSubmissions(1):
#    ...     print(submission.datecreated.isoformat())
#    2005-04-07T...

Now, we are going to check the alternative language submission.

#    >>> form = {
#    ...     'show': 'all',
#    ...     'batch': '10',
#    ...     'start': '10',
#    ...     'field.alternative_language': 'fr',
#    ...     'select_alternate_language': 'Change'}
#    >>> pofile_view = create_view(pofile_es, '+translate', form=form)
#    >>> pofile_view.initialize()
#    >>> pofile_view.second_lang_code
#    'fr'

POFileUploadView
================

Let's check that the upload form sets the right fields.

To be sure that we are using the right entry from the import queue,
we check that it contains only sample data entries.

    >>> translationimportqueue = getUtility(ITranslationImportQueue)
    >>> translationimportqueue.countEntries()
    2
    >>> for entry in translationimportqueue.getAllEntries():
    ...     print(entry.id, entry.content.filename)
    1 evolution-2.2-test.pot
    2 pt_BR.po

The FileUpload class needs a class with the attributes: filename, file and
headers.

XXX cjwatson 2018-06-02: FileUploadArgument.filename can become a native
string again once we're on zope.publisher >= 4.0.0a1.

    >>> class FileUploadArgument:
    ...     filename=b'po/es.po'
    ...     file=io.BytesIO(b'foos')
    ...     headers=''

Now, we do the upload.

    >>> form = {
    ...     'file': FileUpload(FileUploadArgument()),
    ...     'upload_type': 'upstream',
    ...     'pofile_upload': 'Upload'}
    >>> pofile_view = create_view(pofile_es, '+upload', form=form)
    >>> pofile_view.request.method = 'POST'
    >>> pofile_view.initialize()

As we can see, we have now one entry added to our queue.

    >>> translationimportqueue.countEntries()
    3

Get it and check that some attributes are set as they should.

    >>> from lp.translations.enums import RosettaImportStatus
    >>> entry = translationimportqueue.getAllEntries(
    ...     import_status=RosettaImportStatus.NEEDS_REVIEW).last()
    >>> entry.pofile == pofile_es
    True

And for the path, we are going to use the one we already have for the
given POFile instead of the one given with the submit.

    >>> entry.path == pofile_es.path
    True
    >>> print(pofile_es.path)
    es.po

    >>> transaction.commit()

POFileNavigation
================

This class is used to traverse from IPOFile objects to ITranslationMessage
ones.

    >>> from zope.security.proxy import isinstance
    >>> from lp.translations.browser.pofile import POFileNavigation

First, what happens if we get any method that is not supported?

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> request = LaunchpadTestRequest(form={'show': 'all' })
    >>> request.method = 'PUT'
    >>> navigation = POFileNavigation(pofile_es, request)
    >>> navigation.traverse('1')
    Traceback (most recent call last):
    ...
    AssertionError: We only know about GET, HEAD, and POST

The traversal value should be an integer.

    >>> request.method = 'GET'
    >>> navigation.traverse('foo')
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...

Also, translation message sequence numbers are always >= 1.

    >>> navigation.traverse('0')
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...

The given sequence number, we also need that is part of the available ones,
if we use a high one, we should detect it.

    >>> navigation.traverse('30')
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...

But if we have a right sequence number, we will get a valid translation
message.

    >>> isinstance(navigation.traverse('1'), TranslationMessage)
    True

Now, we are going to select a translation message that doesn't exist
yet in our database.

    >>> isinstance(navigation.traverse('22'), DummyTranslationMessage)
    True

But if we do a POST, instead of getting a DummyTranslationMessage
object, we will get a TranslationMessage.

#    >>> request.method = 'POST'
#    >>> isinstance(navigation.traverse('22'), TranslationMessage)
#    True


POExportView
============

POExportView class is used to handle download requests from the web
site.

Once a download request is registered, we redirect to the IPOFile's
index page.

    >>> potemplate = potemplatesubset['evolution-2.2']
    >>> pofile_es = potemplate.getPOFileByLang('es')

    # Request the download.
    >>> form = {'format': 'PO' }
    >>> pofile_view = create_view(pofile_es, '+export', form=form)
    >>> pofile_view.request.method = 'POST'
    >>> pofile_view.initialize()

And we are redirected to the index page, as expected:

    >>> print(pofile_view.request.response.getHeader('Location'))
    http://trans.../ubuntu/hoary/+source/evolution/+pots/evolution-2.2/es
