PO Template webservices
=======================


Getting the attributes of a POTemplate
--------------------------------------

Anonymous users have read access to PO templates attributes.

    >>> from lazr.restful.testing.webservice import pprint_entry
    >>> potemplate = anon_webservice.get(
    ...     '/ubuntu/hoary/+source/pmount/+pots/pmount').jsonBody()
    >>> pprint_entry(potemplate)
    active: True
    date_last_updated: '2005-05-06T20:09:23.775993+00:00'
    description: None
    exported_in_languagepacks: True
    format: 'PO format'
    id: 2
    language_count: 9
    message_count: 63
    name: 'pmount'
    owner_link: 'http://.../~rosetta-admins'
    path: 'po/template.pot'
    priority: 0
    resource_type_link: 'http://.../#translation_template'
    self_link: 'http://.../ubuntu/hoary/+source/pmount/+pots/pmount'
    translation_domain: 'pmount'
    translation_files_collection_link:
        'http://.../pmount/+pots/pmount/translation_files'
    web_link: 'http://translati.../ubuntu/hoary/+source/pmount/+pots/pmount'

"translation_files" will list all POFiles associated with this template.

    >>> translation_files = anon_webservice.get(
    ...     potemplate['translation_files_collection_link']).jsonBody()
    >>> print(translation_files['total_size'])
    9
    >>> print(translation_files['entries'][0]['resource_type_link'])
    http://.../#translation_file


Getting all potemplates for a distribution series
-------------------------------------------------

All templates associated to a distribution series are available from the
'getTranslationTemplates' GET method.

    >>> from zope.component import getUtility
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> login('admin@canonical.com')
    >>> hoary = getUtility(ILaunchpadCelebrities).ubuntu.getSeries('hoary')
    >>> templates = getUtility(IPOTemplateSet).getSubset(distroseries=hoary)
    >>> db_count = len(list(templates))
    >>> logout()
    >>> all_translation_templates = anon_webservice.named_get(
    ...     '/ubuntu/hoary/', 'getTranslationTemplates').jsonBody()
    >>> api_count = all_translation_templates['total_size']
    >>> api_count == db_count
    True
    >>> print(all_translation_templates['entries'][0]['resource_type_link'])
    http://.../#translation_template


Getting all potemplates for a product series
--------------------------------------------

All translation templates for a product series are available using the
'getTranslationTemplates' GET method.

    >>> login('admin@canonical.com')
    >>> productseries = factory.makeProductSeries()
    >>> productseries_name = productseries.name
    >>> product_name = productseries.product.name
    >>> potemplate_1 = factory.makePOTemplate(productseries=productseries)
    >>> potemplate_2 = factory.makePOTemplate(productseries=productseries)
    >>> potemplate_count = 2
    >>> logout()
    >>> all_translation_templates = anon_webservice.named_get(
    ...     '/%s/%s' % (
    ...         product_name,
    ...         productseries_name),
    ...     'getTranslationTemplates'
    ...     ).jsonBody()
    >>> api_count = all_translation_templates['total_size']
    >>> api_count == potemplate_count
    True
    >>> print(all_translation_templates['entries'][0]['resource_type_link'])
    http://.../#translation_template


Getting all translation templates for a source package
------------------------------------------------------

All translation templates for a source package are available using the
'getTranslationTemplates' GET method.


    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet)
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> login('admin@canonical.com')
    >>> hoary = getUtility(ILaunchpadCelebrities).ubuntu.getSeries('hoary')
    >>> evolution_package = getUtility(ISourcePackageNameSet)['evolution']
    >>> templates = getUtility(
    ...     IPOTemplateSet).getSubset(
    ...         distroseries=hoary,
    ...         sourcepackagename=evolution_package)
    >>> db_count = len(list(templates))
    >>> logout()
    >>> all_translation_templates = anon_webservice.named_get(
    ...     '/ubuntu/hoary/+source/evolution',
    ...     'getTranslationTemplates').jsonBody()
    >>> api_count = all_translation_templates['total_size']
    >>> api_count == db_count
    True
    >>> print(all_translation_templates['entries'][0]['resource_type_link'])
    http://.../#translation_template
