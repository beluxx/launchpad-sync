POTemplate View
===============

On this section, we are going to test the view class for an IPOTemplate.

First, we need some imports.

    >>> import io
    >>> from zope.publisher.browser import FileUpload
    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue)
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet)

All the tests will be submitted as comming from the No Privilege person.

    >>> login('no-priv@canonical.com')

Let's got some needed objects.

    >>> sourcepackagenameset = getUtility(ISourcePackageNameSet)
    >>> sourcepackagename = sourcepackagenameset['evolution']
    >>> distributionset = getUtility(IDistributionSet)
    >>> distribution = distributionset['ubuntu']
    >>> series = distribution['hoary']
    >>> potemplateset = getUtility(IPOTemplateSet)
    >>> potemplatesubset = potemplateset.getSubset(
    ...     distroseries=series, sourcepackagename=sourcepackagename)
    >>> potemplate = potemplatesubset['evolution-2.2']

It's time to check that the upload form sets the right fields.

To be sure that we are using the right entry from the import queue,
we check that it only has two items from sample data.

    >>> translationimportqueue = getUtility(ITranslationImportQueue)
    >>> translationimportqueue.countEntries()
    2

The FileUpload class needs a class with the attributes: filename, file and
headers.

XXX cjwatson 2018-06-02: FileUploadArgument.filename can become a native
string again once we're on zope.publisher >= 4.0.0a1.

    >>> class FileUploadArgument:
    ...     filename=b'po/foo.pot'
    ...     file=io.BytesIO(b'foos')
    ...     headers=''

Now, we do the upload.

    >>> form = {
    ...     'file': FileUpload(FileUploadArgument()),
    ...     'UPLOAD': 'Upload'}
    >>> potemplate_view = create_view(potemplate, '+upload', form=form)
    >>> potemplate_view.request.method = 'POST'
    >>> potemplate_view.initialize()

As we can see, we have now three entries in our queue.

    >>> translationimportqueue.countEntries()
    3

Get it and check that some attributes are set as they should. For instance,
the entry should be linked with the IPOTemplate we are using.

    >>> from lp.translations.enums import RosettaImportStatus
    >>> entry = translationimportqueue.getAllEntries(
    ...     import_status=RosettaImportStatus.NEEDS_REVIEW).last()
    >>> entry.potemplate == potemplate
    True

From the IPOTemplate upload form, we can also upload .po files. Let's check
that feature...

XXX cjwatson 2018-06-02: FileUploadArgument.filename can become a native
string again once we're on zope.publisher >= 4.0.0a1.

    >>> class FileUploadArgument:
    ...     filename=b'po/es.po'
    ...     file=io.BytesIO(b'foos')
    ...     headers=''

We do the upload...

    >>> form = {
    ...     'file': FileUpload(FileUploadArgument()),
    ...     'UPLOAD': 'Upload'}
    >>> potemplate_view = create_view(potemplate, '+upload', form=form)
    >>> potemplate_view.request.method = 'POST'
    >>> potemplate_view.initialize()

As we can see, we have now another entry in our queue.

    >>> translationimportqueue.countEntries()
    4

Get it and check that some attributes are set as they should. For instance,
the entry should be linked with the IPOTemplate we are using.

    >>> entry = translationimportqueue.getAllEntries(
    ...     import_status=RosettaImportStatus.NEEDS_REVIEW).last()
    >>> entry.potemplate == potemplate
    True

And for the path, we are going to use the filename we got from the upload form
because it's a .po file instead of a .pot file and we need that information
to differenciate different .po files associated with the context.

    >>> print(entry.path)
    po/es.po

And that's all, folks!
