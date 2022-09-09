Translations policy settings
============================

A product owner, Rosetta expert, and Ubuntu translations coordinator
browser is created.

    >>> from lp.app.enums import ServiceUsage

    >>> login("admin@canonical.com")
    >>> product_owner = factory.makePerson(email="po@ex.com")
    >>> chestii = factory.makeProduct(
    ...     name="chestii",
    ...     owner=product_owner,
    ...     translations_usage=ServiceUsage.LAUNCHPAD,
    ... )
    >>> logout()
    >>> dtc_browser = setupDTCBrowser()
    >>> re_browser = setupRosettaExpertBrowser()
    >>> po_browser = setupBrowser("Basic po@ex.com:test")

Visiting the main products translations page, product owners and Rosetta
administrators sees the "Configure translations" link, leading to the
translations settings page.

    >>> re_browser.open("http://translations.launchpad.test/chestii")
    >>> re_browser.getLink("Configure Translations").click()
    >>> print(re_browser.url)
    http://translations.launchpad.test/chestii/+configure-translations

    >>> po_browser.open("http://translations.launchpad.test/chestii")
    >>> po_browser.getLink("Configure Translations").click()
    >>> print(po_browser.url)
    http://translations.launchpad.test/chestii/+configure-translations

From the settings page, translations group and translation permissions
can be changed.

    >>> hint = find_tag_by_id(re_browser.contents, "form_extra_info")
    >>> print(extract_text(hint))
    Select the translation group that will be managing...

    >>> re_browser.getControl("Translation group").value = [
    ...     "ubuntu-translators"
    ... ]
    >>> re_browser.getControl("Translation permissions policy").value = [
    ...     "CLOSED"
    ... ]
    >>> re_browser.getControl("Change").click()
    >>> print(re_browser.url)
    http://translations.launchpad.test/chestii
    >>> permissions = find_tag_by_id(
    ...     re_browser.contents, "translation-permissions"
    ... )
    >>> print(extract_text(permissions))
    Chestii is translated by Ubuntu Translators with Closed permissions.

Other persons, including the translation group owners, will not see the link
to translations policy page.

    >>> dtc_browser.open("http://translations.launchpad.test/chestii")
    >>> dtc_browser.getLink("Configure Translations")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

An attempt to access the translations policy url will not be authorized.

    >>> browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "chestii/+configure-translations"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...


Translations policy for distributions
-------------------------------------

Ubuntu translation coordinators will have access to translations policy page
for Ubuntu and will be able to change it.

    >>> dtc_browser.open("http://translations.launchpad.test/ubuntu")
    >>> dtc_browser.getLink("Configure translations").click()
    >>> print(dtc_browser.url)
    http://translations.launchpad.test/ubuntu/+configure-translations

    >>> dtc_browser.getControl("Translation group").value = [
    ...     "ubuntu-translators"
    ... ]
    >>> dtc_browser.getControl("Translation permissions policy").value = [
    ...     "CLOSED"
    ... ]
    >>> dtc_browser.getControl("Change").click()
    >>> print(dtc_browser.url)
    http://translations.launchpad.test/ubuntu
    >>> permissions = find_tag_by_id(
    ...     dtc_browser.contents, "translation-permissions"
    ... )
    >>> print(extract_text(permissions))
    Ubuntu is translated by Ubuntu Translators with Closed permissions.
