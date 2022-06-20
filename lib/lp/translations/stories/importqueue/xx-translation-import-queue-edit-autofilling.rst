This test is going to test the form prefill so we speedup the productivity
of the Translation import queue reviewers.

First, we need to feed the import queue.

    >>> import lp.translations
    >>> import os.path
    >>> test_file_name = os.path.join(
    ...     os.path.dirname(lp.translations.__file__),
    ...     'stories/importqueue/'
    ...     'xx-translation-import-queue-edit-autofilling.tar.gz')
    >>> tarball = open(test_file_name, 'rb')

    >>> browser = setupBrowser(auth='Basic carlos@canonical.com:test')
    >>> browser.open(
    ...     'http://translations.launchpad.test/alsa-utils/trunk/'
    ...     '+translations-upload')
    >>> file_ctrl = browser.getControl('File:')
    >>> file_ctrl.add_file(
    ...     tarball, 'application/x-gzip', 'test-autofilling.tar.gz')
    >>> browser.getControl('Upload').click()
    >>> browser.url
    'http://translations.launchpad.test/alsa-utils/trunk/+translations-upload'
    >>> for tag in find_tags_by_class(browser.contents, 'message'):
    ...     print(tag)
    <div...Thank you for your upload. 2 files from the tarball...

Let's check the values we get by default from the .pot file. The name field
and the translation domain field are pre-filled from the name of the file.

    >>> login(ANONYMOUS)
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.product import IProductSet
    >>> series = getUtility(IProductSet).getByName('alsa-utils').getSeries(
    ...     'trunk')
    >>> pot_qid = series.getTranslationImportQueueEntries(
    ...     file_extension='pot')[0].id
    >>> po_qid = series.getTranslationImportQueueEntries(
    ...     file_extension='po')[0].id
    >>> logout()

    >>> browser.open(
    ...     'http://translations.launchpad.test/+imports/%d' % pot_qid)
    >>> browser.getControl(name='field.name').value
    'test'
    >>> browser.getControl(name='field.translation_domain').value
    'test'

But the path field has been preloaded with the value from the tar ball and
the file type has been determined correctly from it.

    >>> browser.getControl(name='field.path').value
    'test/test.pot'
    >>> browser.getControl(name='field.file_type').value
    ['POT']

Let's fill in the information.

    >>> browser.getControl('Name').value = 'alsa-utils'
    >>> browser.getControl('Translation domain').value = 'alsa-utils'
    >>> browser.getControl('Approve').click()
    >>> browser.url
    'http://translations.launchpad.test/+imports'

Now, as we already know the name, a new form load should
give us that field with information.

    >>> browser.open(
    ...     'http://translations.launchpad.test/+imports/%d' % pot_qid)
    >>> browser.getControl(name='field.name').value
    'alsa-utils'

Let's move to the .po file. The language is guessed from the file name
and the user sees a warning so they check that it's ok.

    >>> browser.open(
    ...     'http://translations.launchpad.test/+imports/%d' % po_qid)
    >>> browser.getControl(name='field.file_type').value
    ['PO']
    >>> browser.getControl(name='field.path').value
    'test/es.po'
    >>> browser.getControl(name='field.potemplate').value
    ['']
    >>> browser.getControl(name='field.language').value
    ['es']

Rosetta experts should be able to override the path in the source tree from
where this entry comes. To be sure that the path changed but that it's still
the same entry, previous_url holds current value.

    >>> browser.getControl(name='field.path').value = 'po/es.po'
    >>> browser.getControl(name='field.potemplate').value = ['10']
    >>> browser.getControl('Approve').click()
    >>> browser.url
    'http://translations.launchpad.test/+imports'

Reloading the form shows all the submitted information applied.

    >>> browser.open(
    ...     'http://translations.launchpad.test/+imports/%d' % po_qid)
    >>> browser.getControl(name='field.path').value
    'po/es.po'
    >>> browser.getControl(name='field.potemplate').value
    ['10']
    >>> browser.getControl(name='field.language').value
    ['es']
