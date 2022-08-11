Entry details
=============

The translation import queue entry page shows various details about an
entry and its target that may be helpful in queue review.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.translations.model.translationimportqueue import (
    ...     TranslationImportQueue)

    >>> filename = 'po/foo.pot'

    >>> login(ANONYMOUS)
    >>> queue = TranslationImportQueue()
    >>> product = factory.makeProduct(
    ...     translations_usage=ServiceUsage.LAUNCHPAD)
    >>> product_displayname = product.displayname
    >>> trunk = product.getSeries('trunk')
    >>> uploader = factory.makePerson()
    >>> entry = queue.addOrUpdateEntry(
    ...     filename, b'# empty', False, uploader, productseries=trunk)
    >>> entry_url = canonical_url(entry, rootsite='translations')
    >>> logout()

    >>> admin_browser.open(entry_url)
    >>> details = find_tag_by_id(admin_browser.contents, 'portlet-details')
    >>> details_text = extract_text(details)
    >>> print(details_text)
    Upload attached to ... trunk series.
    This project...s licence is open source.
    Release series has no templates.
    Project has no translatable series.
    File po/foo.pot uploaded by ...

The details include the project the entry is for, and who uploaded it.

    >>> product_displayname in details_text
    True

    # Must remove the security proxy because IPerson.displayname is protected.
    >>> removeSecurityProxy(uploader).displayname in details_text
    True

There's also a link to the file's contents.

    >>> print(admin_browser.getLink(filename).text)
    po/foo.pot
    >>> print(admin_browser.getLink(filename).url)
    http://...foo.pot


Existing templates
------------------

If there are translatable templates in the series, this will be stated
and there will be a link to the templates list.

    >>> login(ANONYMOUS)
    >>> template = factory.makePOTemplate(productseries=trunk)
    >>> logout()

    >>> admin_browser.open(entry_url)
    >>> details = find_tag_by_id(admin_browser.contents, 'portlet-details')
    >>> details_text = extract_text(details)
    >>> print(details_text)
    Upload attached to
    ...
    Release series has 1 template.
    ...

    >>> print(admin_browser.getLink('1 template').url)
    http...://translations.launchpad.test/.../trunk/+templates

    >>> admin_browser.getLink('1 template').click()
    >>> print(admin_browser.title)
    All templates : Series trunk : Translations : ...

In that case, the product is also shown to have translatable series.

    >>> print(details_text)
    Upload attached to
    ...
    Project has translatable series: trunk.
    ...


Source packages
---------------

The portlet shows different (well, less) information for uploads
attached to distribution packages.

    >>> from lp.registry.model.distribution import DistributionSet

    >>> login(ANONYMOUS)
    >>> distro = DistributionSet().getByName('ubuntu')
    >>> distroseries = distro.getSeries('hoary')
    >>> packagename = factory.makeSourcePackageName(name='xpad')
    >>> entry = queue.addOrUpdateEntry(
    ...     filename, b'# nothing', True, uploader, distroseries=distroseries,
    ...     sourcepackagename=packagename)
    >>> entry_url = canonical_url(entry, rootsite='translations')
    >>> logout()

This only shows the source package and the file.

    >>> admin_browser.open(entry_url)
    >>> details = find_tag_by_id(admin_browser.contents, 'portlet-details')
    >>> details_text = extract_text(details)
    >>> print(details_text)
    Upload attached to xpad in Ubuntu Hoary.
    File po/foo.pot uploaded by ...
