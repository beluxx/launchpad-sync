The translation focus of a product can be explicitly set to a specific series.
When not set, launchpad recommends the development focus to translate.

    >>> from lp.app.enums import ServiceUsage
    >>> login('admin@canonical.com')
    >>> fooproject = factory.makeProduct(name="fooproject")
    >>> fooproject.translations_usage = ServiceUsage.LAUNCHPAD
    >>> fooproject_trunk = fooproject.getSeries("trunk")
    >>> fooproject_url = canonical_url(
    ...     fooproject, rootsite="translations")
    >>> logout()

Only admin users are able to change the translation focus of a product.
Unprivileged users can see the recommended series for translation,
but have no access to the 'Configure translations' menu.

    >>> admin_browser.open(fooproject_url)
    >>> print(extract_text(
    ...     find_tags_by_class(admin_browser.contents,
    ...                        'menu-link-configure_translations')[0]))
    Configure Translations

    >>> browser.open(fooproject_url)
    >>> print(extract_text(
    ...     find_tags_by_class(browser.contents, 'edit sprite')[0]))
    Traceback (most recent call last):
    ...
    IndexError: list index out of range

Setting the translation focus
=============================

    >>> login('admin@canonical.com')
    >>> from zope.security.proxy import removeSecurityProxy
    >>> pot_main = factory.makePOTemplate(
    ...     productseries=fooproject_trunk, name="pot1")
    >>> removeSecurityProxy(pot_main).messagecount = 10
    >>> pofile = factory.makePOFile("pt_BR", potemplate=pot_main)

When the translation focus is not set, Launchpad suggests the
development focus as the current series to be translated.
It needs to be translatable.

    >>> print(fooproject.translation_focus)
    None

    >>> logout()
    >>> browser.open(fooproject_url)
    >>> print(extract_text(
    ...     find_tags_by_class(browser.contents, 'portlet')[0]))
    Translation details...
    Launchpad currently recommends translating... Fooproject trunk series.
    ...

We can set an untranslatable series as the translation focus, but Launchpad
won't consider it because there'll be nothing to translate.

    >>> login('admin@canonical.com')
    >>> fooproject_untranslatableseries = factory.makeProductSeries(
    ...     product=fooproject,
    ...     name="untranslatable-series")
    >>> fooproject.translation_focus = fooproject_untranslatableseries
    >>> print(removeSecurityProxy(fooproject.translation_focus.name))
    untranslatable-series

    >>> logout()
    >>> browser.open(fooproject_url)
    >>> print(extract_text(
    ...     find_tags_by_class(browser.contents, 'portlet')[0]))
    Translation details...
    Launchpad currently recommends translating... Fooproject trunk series.
    ...

We need to create a translatable series so we can set it as translation focus.

    >>> login('admin@canonical.com')
    >>> fooproject_otherseries = factory.makeProductSeries(product=fooproject,
    ...     name="other-series")
    >>> pot_other = factory.makePOTemplate(
    ...     productseries=fooproject_otherseries, name="pot2")
    >>> removeSecurityProxy(pot_other).messagecount = 10
    >>> pofile1 = factory.makePOFile('pt_BR', potemplate=pot_other)

    >>> fooproject.translation_focus = fooproject_otherseries
    >>> logout()

    >>> browser.open(fooproject_url)
    >>> print(extract_text(
    ...     find_tags_by_class(browser.contents, 'portlet')[0]))
    Translation details...
    Launchpad currently recommends translating...
    Fooproject other-series series.
    ...
