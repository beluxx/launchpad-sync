Products with translations
==========================

We have to do a little set up.

    >>> from zope.component import getUtility
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.testing import (
    ...     login,
    ...     logout,
    ... )
    >>> login("admin@canonical.com")
    >>> evolution = getUtility(IProductSet).getByName("evolution")
    >>> alsa = getUtility(IProductSet).getByName("alsa-utils")
    >>> evolution.translations_usage = ServiceUsage.LAUNCHPAD
    >>> alsa.translations_usage = ServiceUsage.LAUNCHPAD
    >>> transaction.commit()
    >>> logout()

The +products-with-translations page lists all translatable products in
Launchpad.

    >>> browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "translations/+products-with-translations"
    ... )

    >>> print(find_main_content(browser.contents).decode_contents())
    <...>
    ... of 2 results
    ...Evolution...
    ...alsa-utils...
