TranslationImportQueueEntry Edit View
=====================================

On this section, we are going to test the edit view class for an
ITranslationImportQueueEntry object.

    >>> from zope.component import getUtility
    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue)
    >>> from lp.translations.browser.translationimportqueue import (
    ...     TranslationImportQueueEntryView)

This view is only accessible for administrators.

    >>> login('foo.bar@canonical.com')

In real life, entries in the import queue have been uploaded by a person.
We will create the entry by hand but need a person to be named as importer.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> importer = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
    >>> print(importer.displayname)
    Foo Bar

A real entry would have been uploaded in the context of productseries or a
sourcepackage within a distroseries. So we need to get a productseries for
our entry.

    >>> from lp.registry.interfaces.productseries import (
    ...     IProductSeriesSet)
    >>> productseries = getUtility(IProductSeriesSet).get(3)
    >>> print(productseries.name)
    trunk
    >>> print(productseries.summary)
    The primary "trunk" of development for this product...

Now we create the entry in the queue.

    >>> queue = getUtility(ITranslationImportQueue)
    >>> pot_entry = queue.addOrUpdateEntry(
    ...     'demo.pot', b'# foo', False,
    ...     importer, productseries=productseries)
    >>> print(pot_entry.path)
    demo.pot

The view is named "+index" and it is found on the TranslationsLayer. We want
to get it new for each subsequent test.

    >>> from lp.testing.views import create_initialized_view
    >>> view = create_initialized_view(pot_entry, '+index')
    >>> isinstance(view, TranslationImportQueueEntryView)
    True

Upon initialization the view sets the file type.

    >>> print(view.initial_values['file_type'])
    Template

Validating correct data should not produce an error.

    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     TranslationFileType)
    >>> data = {
    ...     'file_type': TranslationFileType.POT,
    ...     'path': 'demo.pot',
    ...     'name': 'demo-name',
    ...     'translation_domain': 'demo-domain'}
    >>> def validate(view, data):
    ...     view.validate(data)
    ...     for err in view.errors:
    ...         print(err)
    >>> validate(view, data)

But declaring a different file type would require different data, so we get
some errors.

    >>> view = create_initialized_view(pot_entry, '+index')
    >>> data = {
    ...     'file_type': TranslationFileType.PO,
    ...     'path': 'demo.pot',
    ...     'name': 'demo-name',
    ...     'translation_domain': 'demo-domain'}
    >>> validate(view, data)
    This filename is not appropriate for a translation.
    Please choose a template.

Also, the filename must be given and the template name must be a valid name.

    >>> view = create_initialized_view(pot_entry, '+index')
    >>> data = {
    ...     'file_type': TranslationFileType.POT,
    ...     'path': None,
    ...     'name': '.-demo-name',
    ...     'translation_domain': 'demo-domain'}
    >>> validate(view, data)
    The file name is missing.
    Please specify a valid name for the template...

Specifying po file data for po templates is not a good idea either.

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> language = getUtility(ILanguageSet).getLanguageByCode('eo')
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> potemplate = getUtility(IPOTemplateSet).getPOTemplateByPathAndOrigin(
    ...     'po/evolution-2.2.pot', productseries)
    >>> view = create_initialized_view(pot_entry, '+index')
    >>> data = {
    ...     'file_type': TranslationFileType.POT,
    ...     'path': 'demo.po',
    ...     'potemplate': potemplate,
    ...     'language': language }
    >>> validate(view, data)
    This filename is not appropriate for a template.
    Please specify a name for the template.
    Please specify a translation domain for the template.

But if it works if you decide that the file in question really is a po file.

    >>> view = create_initialized_view(pot_entry, '+index')
    >>> data = {
    ...     'file_type': TranslationFileType.PO,
    ...     'path': 'demo.po',
    ...     'potemplate': potemplate,
    ...     'language': language }
    >>> validate(view, data)

After submitting the entry, the status is set to "Approved".
The potemplate entry for the new template is also created.

    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     RosettaImportStatus)
    >>> view = create_initialized_view(pot_entry, '+index')
    >>> view.context.potemplate == None
    True
    >>> data = {
    ...     'file_type': TranslationFileType.POT,
    ...     'path': 'demo.pot',
    ...     'name': 'demo-name',
    ...     'translation_domain': 'demo-domain'}
    >>> view.validate(data)
    >>> view._change_action(data)
    >>> pot_entry.status == RosettaImportStatus.APPROVED
    True
    >>> pot_entry.potemplate != None
    True

The Ubuntu distribution gets special treatment for the language pack flag.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    >>> ubuntuseries = factory.makeDistroSeries(ubuntu)
    >>> packagename = factory.makeSourcePackageName()

We can upload to a sourcepackagename in the Ubuntu series.

    >>> ubuntu_entry = queue.addOrUpdateEntry(
    ...     'demo.pot', b'# foo', True,
    ...     importer, distroseries=ubuntuseries,
    ...     sourcepackagename=packagename)
    >>> ubuntu_view = create_initialized_view(ubuntu_entry, '+index')

The form now has a field for languagepacks. The value of the field defaults
to "True" as no potemplate has been set yet.

    >>> ubuntu_view.context.potemplate == None
    True
    >>> 'languagepack' in ubuntu_view.field_names
    True
    >>> ubuntu_view.initial_values['languagepack'] == True
    True

Submitting this form will set the languagepack flag in the newly created
potemplate.

    >>> data = {
    ...     'file_type': TranslationFileType.POT,
    ...     'path': 'demo.pot',
    ...     'name': 'demo-name',
    ...     'translation_domain': 'demo-domain',
    ...     'languagepack': True}
    >>> ubuntu_view.validate(data)
    >>> ubuntu_view._change_action(data)
    >>> ubuntu_entry.potemplate.languagepack == True
    True

Once the template has been set, the view will display its languagepack value
as the default value.

    >>> ubuntu_entry.potemplate.languagepack = False
    >>> ubuntu_view = create_initialized_view(ubuntu_entry, '+index')
    >>> ubuntu_view.initial_values['languagepack'] == False
    True

For a product template, languagepack is not displayed.

    >>> other_series = factory.makeProductSeries()
    >>> other_entry = queue.addOrUpdateEntry(
    ...     'demo.pot', b'# foo', True,
    ...     importer, productseries=other_series)
    >>> other_view = create_initialized_view(other_entry, '+index')
    >>> 'languagepack' in other_view.field_names
    False

When importing po files, only the relevant templates should be made
available for selection.

    >>> po_entry = queue.addOrUpdateEntry(
    ...     'demo.po', b'# foo', False,
    ...     importer, productseries=productseries)
    >>> print(po_entry.path)
    demo.po

The drop-down list is fed from a vocabulary.

    >>> from lp.translations.vocabularies import TranslationTemplateVocabulary
    >>> vocab = TranslationTemplateVocabulary(po_entry)
    >>> for term in vocab:
    ...     print(term.title)
    demo-name
    evolution-2.2
    evolution-2.2-test

But templates may be obsoleted by setting "iscurrent" to False.

    >>> pot_entry.potemplate.iscurrent = False

Only templates marked as "iscurrent" are available in the view when
importing po files.

    >>> vocab = TranslationTemplateVocabulary(po_entry)
    >>> for term in vocab:
    ...     print(term.title)
    evolution-2.2
    evolution-2.2-test
