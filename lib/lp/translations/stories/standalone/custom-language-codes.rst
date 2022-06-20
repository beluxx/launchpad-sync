Custom Language Codes
---------------------

Some projects insist on using nonstandard language codes, such as es_ES
for standard Spanish or pt-BR instead of pt_BR.  Custom language codes
are a feature that helps deal with this during translation import.  A
custom language code maps a language code as the project (or package)
uses it to a language, regardless of whether the code is for an existing
language or not.

Custom language codes are attached to either a product or a source
package.

    >>> from zope.component import getUtility
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.app.enums import ServiceUsage

    >>> def find_custom_language_codes_link(browser):
    ...     """Find reference to custom language codes on a page."""
    ...     return find_tag_by_id(browser.contents, 'custom-language-codes')

    >>> login(ANONYMOUS)
    >>> owner = factory.makePerson(email='o@example.com')
    >>> rosetta_admin = factory.makePerson(email='r@example.com')
    >>> removeSecurityProxy(rosetta_admin).join(
    ...     getUtility(ILaunchpadCelebrities).rosetta_experts)
    >>> product = factory.makeProduct(displayname="Foo", owner=owner)
    >>> trunk = product.getSeries('trunk')
    >>> naked_product = removeSecurityProxy(product)
    >>> naked_product.translations_usage = ServiceUsage.LAUNCHPAD
    >>> template = factory.makePOTemplate(productseries=trunk)
    >>> product_page = canonical_url(product, rootsite='translations')
    >>> logout()

    >>> owner_browser = setupBrowser("Basic o@example.com:test")
    >>> rosetta_admin_browser = setupRosettaExpertBrowser()

The project's owner sees the link to the custom language codes on a project's
main translations page.

    >>> owner_browser.open(product_page)
    >>> tag = find_custom_language_codes_link(owner_browser)
    >>> print(extract_text(tag.decode_contents()))
    If necessary, you may
    define custom language codes
    for this project.

Translation admins also have access to this link.

    >>> rosetta_admin_browser.open(product_page)
    >>> tag = find_custom_language_codes_link(rosetta_admin_browser)
    >>> print(extract_text(tag.decode_contents()))
    If necessary, you may
    define custom language codes
    for this project.

The link goes to the custom language codes management page.

    >>> owner_browser.getLink("define custom language codes").click()
    >>> custom_language_codes_page = owner_browser.url

Other users don't see this link.

    >>> user_browser.open(product_page)
    >>> print(find_custom_language_codes_link(user_browser))
    None

Initially the page shows no custom language codes for the project.

    >>> tag = find_tag_by_id(owner_browser.contents, 'empty')
    >>> print(extract_text(tag.decode_contents()))
    No custom language codes have been defined.

There is a link to add a custom language code.

    >>> owner_browser.getLink("Add a custom language code").click()
    >>> add_page = owner_browser.url

    >>> owner_browser.getControl("Language code:").value = 'no'
    >>> owner_browser.getControl("Language:").value = ['nn']
    >>> owner_browser.getControl("Add").click()

This leads back to the custom language codes overview, where the new
code is now shown.

    >>> owner_browser.url == custom_language_codes_page
    True

    >>> tag = find_tag_by_id(owner_browser.contents, 'nonempty')
    >>> print(extract_text(tag.decode_contents()))
    Foo uses the following custom language codes:
    Code...     ...maps to language
    no          Norwegian Nynorsk

There is an overview page for the custom code, though there's not much
to see there.

    >>> owner_browser.getLink("no").click()
    >>> main = find_main_content(owner_browser.contents)
    >>> print(extract_text(main.decode_contents()))
    Custom language code  ...no... for Foo
    For Foo, uploads with the language code
    “no”
    are associated with the language
    Norwegian Nynorsk.
    remove custom language code
    custom language codes overview

The overview page leads back to the custom language codes overview.

    >>> code_page = owner_browser.url
    >>> owner_browser.getLink(
    ...     "custom language codes overview").click()
    >>> owner_browser.url == custom_language_codes_page
    True

    >>> owner_browser.open(code_page)

There is also a link for removing codes.  The owner follows the link and
removes the "no" custom language code.

    >>> owner_browser.getLink("remove custom language code").click()
    >>> remove_page = owner_browser.url
    >>> owner_browser.getControl("Remove").click()

This leads back to the overview page.

    >>> owner_browser.url == custom_language_codes_page
    True

    >>> tag = find_tag_by_id(owner_browser.contents, 'empty')
    >>> print(extract_text(tag.decode_contents()))
    No custom language codes have been defined.


Unprivileged access
===================

A unprivileged user can see the page, actually, if they know the URL.
This can be convenient for debugging.

    >>> user_browser.open(custom_language_codes_page)

    >>> tag = find_tag_by_id(user_browser.contents, 'empty')
    >>> print(extract_text(tag.decode_contents()))
    No custom language codes have been defined.

However all they get is a read-only version of the page.

    >>> user_browser.getLink("Add a custom language code").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

The page for adding custom language codes is not accessible to them.

    >>> user_browser.open(add_page)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

And naturally, if the owner creates a custom language code again, an
unprivileged user can't remove it.

    >>> owner_browser.open(add_page)
    >>> owner_browser.getControl("Language code:").value = 'no'
    >>> owner_browser.getControl("Language:").value = ['nn']
    >>> owner_browser.getControl("Add").click()

    >>> user_browser.open(custom_language_codes_page)
    >>> tag = find_tag_by_id(user_browser.contents, 'nonempty')
    >>> print(extract_text(tag.decode_contents()))
    Foo uses the following custom language codes:
    Code...     ...maps to language
    no          Norwegian Nynorsk

    >>> user_browser.getLink("no").click()
    >>> user_browser.getLink("remove custom language code")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> user_browser.open(remove_page)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...


Source packages
===============

The story for source packages is very similar to that for products.  In
this case, the custom language code is tied to the distribution source
package--i.e. the combination of a distribution and a source package
name.  However, since there is no Translations page for that type of
object (and we'd probably never go there if there were), the link is
shown on the source package page. For distributions, the owner of the
distribution's translation group is a translations administrator.

    >>> login(ANONYMOUS)
    >>> from lp.registry.model.sourcepackage import SourcePackage
    >>> from lp.registry.model.sourcepackagename import SourcePackageName

    >>> distro = factory.makeDistribution('distro')
    >>> distroseries = factory.makeDistroSeries(distribution=distro)
    >>> sourcepackagename = SourcePackageName(name='bar')
    >>> package = factory.makeSourcePackage(
    ...     sourcepackagename=sourcepackagename, distroseries=distroseries)
    >>> naked_distro = removeSecurityProxy(distro)
    >>> naked_distro.translations_usage = ServiceUsage.LAUNCHPAD
    >>> other_series = factory.makeDistroSeries(distribution=distro)
    >>> template = factory.makePOTemplate(
    ...     distroseries=package.distroseries,
    ...     sourcepackagename=package.sourcepackagename)
    >>> package_page = canonical_url(package, rootsite="translations")
    >>> page_in_other_series = canonical_url(SourcePackage(
    ...     distroseries=other_series,
    ...     sourcepackagename=package.sourcepackagename),
    ...     rootsite="translations")
    >>> translations_admin = factory.makePerson(email='ta@example.com')
    >>> translationgroup = factory.makeTranslationGroup(
    ...     owner=translations_admin)
    >>> removeSecurityProxy(distro).translationgroup = translationgroup
    >>> logout()

    >>> translations_browser = setupBrowser("Basic ta@example.com:test")
    >>> translations_browser.open(package_page)

Of course in this case, the notice about there being no custom language
codes talks about a package, not a project.

    >>> tag = find_custom_language_codes_link(translations_browser)
    >>> print(extract_text(tag.decode_contents()))
    If necessary, you may
    define custom language codes
    for this package.

    >>> translations_browser.getLink("define custom language codes").click()
    >>> custom_language_codes_page = translations_browser.url

    >>> tag = find_tag_by_id(translations_browser.contents, 'empty')
    >>> print(extract_text(tag.decode_contents()))
    No custom language codes have been defined.

A translations admin can add a language code.

    >>> translations_browser.getLink("Add a custom language code").click()
    >>> add_page = translations_browser.url

    >>> translations_browser.getControl("Language code:").value = 'pt-br'
    >>> translations_browser.getControl("Language:").value = ['pt_BR']
    >>> translations_browser.getControl("Add").click()

The language code is displayed.

    >>> tag = find_tag_by_id(translations_browser.contents, 'nonempty')
    >>> print(extract_text(tag.decode_contents()))
    bar in Distro uses the following custom language codes:
    Code...     ...maps to language
    pt-br       Portuguese (Brazil)

It's also displayed identically on the same package but in another
release series of the same distribution.

    >>> translations_browser.open(page_in_other_series)
    >>> tag = find_custom_language_codes_link(translations_browser)
    >>> print(extract_text(tag.decode_contents()))
    If necessary, you may
    define custom language codes
    for this package.

    >>> translations_browser.getLink("define custom language codes").click()
    >>> tag = find_tag_by_id(translations_browser.contents, 'nonempty')
    >>> print(extract_text(tag.decode_contents()))
    bar in Distro uses the following custom language codes:
    Code...     ...maps to language
    pt-br       Portuguese (Brazil)


The new code has a link there...

    >>> translations_browser.getLink("pt-br").click()

...and can be deleted.

    >>> translations_browser.getLink("remove custom language code").click()
    >>> translations_browser.getControl("Remove").click()

    >>> tag = find_tag_by_id(translations_browser.contents, 'empty')
    >>> print(extract_text(tag.decode_contents()))
    No custom language codes have been defined.
