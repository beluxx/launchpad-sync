Product Translations
====================

Each product in Launchpad has a Translations page.

    >>> anon_browser.open('http://translations.launchpad.test/evolution')
    >>> print(anon_browser.title)
    Translations : Evolution
    >>> print(extract_text(find_main_content(anon_browser.contents)))
    Translation overview
    ...

A helper method to print out language chart.

    >>> def print_language_stats(browser):
    ...     table = find_tag_by_id(browser.contents, 'languagestats')
    ...     if table is None:
    ...         print("No translations.")
    ...         return
    ...     language_rows = find_tags_by_class(str(table), 'stats')
    ...     print("%-25s %13s %13s" % (
    ...         "Language", "Untranslated", "Unreviewed"))
    ...     for row in language_rows:
    ...         cols = row.find_all('td')
    ...         language = extract_text(cols[0])
    ...         untranslated = extract_text(cols[2])
    ...         unreviewed = extract_text(cols[3])
    ...         print("%-25s %13d %13d" % (
    ...             language, int(untranslated), int(unreviewed)))

We even have a language chart table.

    >>> print_language_stats(anon_browser)
    Language                   Untranslated    Unreviewed
    Portuguese (Brazil)                  25             0
    Spanish                              22             2

If a product is not set up for translations in Launchpad, and you are its
registrant or an admin, the Translations page suggests that you set it up for
translation, or link the product to a translatable package.

    >>> registrant = setupBrowser(auth='Basic mark@example.com:test')
    >>> registrant.open(
    ...     'http://translations.launchpad.test/gnomebaker')
    >>> print(extract_text(
    ...     find_tag_by_id(
    ...         registrant.contents, 'not-translated-in-launchpad')))
    Launchpad does not know where gnomebaker translates its messages.

    >>> print(extract_text(
    ...     find_tag_by_id(
    ...         registrant.contents, 'translations-explanation')))
    Launchpad allows communities to translate projects using imports or a
    branch.
    Getting started with translating your project in Launchpad
    Configure Translations

    >>> registrant.getLink(
    ...     url=('/gnomebaker/trunk/'
    ...          '+translations-upload')) is not None
    True

The instructions for the registrant link to the translations
configuration page, where they can configure the project to use
Launchpad for translations if desired.

    >>> registrant.getLink('Translations').click()
    >>> print(registrant.url)
    http://.../gnomebaker/+configure-translations

(The template upload process is tested in xx-translation-import-queue.rst.)


If you're logged in as someone else, it only tells you that the translations
are not being used, and provides access to help.

    >>> unprivileged = setupBrowser(auth='Basic no-priv@canonical.com:test')
    >>> unprivileged.open('http://translations.launchpad.test/gnomebaker')
    >>> print(extract_text(find_main_content(unprivileged.contents)))
    Translation overview
    Help for translations
    Launchpad does not know where
    gnomebaker translates its messages.

It omits the registrant-only links ...

    >>> unprivileged.getLink(url='/gnomebaker/trunk/+translations-upload')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> unprivileged.getLink(url='/gnomebaker/+packages')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

... because you can't do those things.

    >>> unprivileged.open(
    ...     'http://translations.launchpad.test/gnomebaker/trunk/'
    ...     '+translations-upload')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...


If you're not logged in at all, you aren't shown the registrant
options, either.

    >>> anon_browser.open('http://translations.launchpad.test/gnomebaker')
    >>> print(extract_text(find_main_content(anon_browser.contents)))
    Translation overview
    Help for translations
    Launchpad does not know where
    gnomebaker translates its messages.

Finally, if a product states that is not officially using Launchpad
Translations it doesn't show any translation template:

    >>> anon_browser.open('http://launchpad.test/netapplet')
    >>> anon_browser.getLink('Translations').click()
    >>> print(anon_browser.title)
    Translations : NetApplet
    >>> print(find_main_content(anon_browser.contents))
    <...
    ...Translation overview...

And since the Network Applet isn't currently using Launchpad for
Translations, there is no language chart shown.

    >>> print(find_tag_by_id(anon_browser.contents, 'language-chart'))
    None

If the netapplet project is updated to use Launchpad for translations...

    >>> admin_browser.open('http://launchpad.test/netapplet')
    >>> admin_browser.getLink('Translations', index=1).click()
    >>> print_radio_button_field(admin_browser.contents, "translations_usage")
    (*) Unknown
    ( ) Launchpad
    ( ) External
    ( ) Not Applicable
    >>> admin_browser.getControl('Launchpad').click()
    >>> admin_browser.getControl('Change').click()

...there are no longer any obsolete entries.

    >>> admin_browser.getLink('Translations', index=1).click()
    >>> print(admin_browser.title)
    Configure translations : Translations : NetApplet
    >>> print(find_tag_by_id(admin_browser.contents,
    ...                'portlet-obsolete-translatable-series'))
    None

Also, we will get some translation status for network applet.

    >>> anon_browser.open('http://translations.launchpad.test/netapplet')
    >>> print(find_main_content(anon_browser.contents))
    <...
    ...Translation overview...
    >>> print_language_stats(anon_browser)
    Language                   Untranslated    Unreviewed


Translation recommendation
==========================

The page mentions which product series should be translated.

    >>> def find_translation_recommendation(browser):
    ...     """Find the text recommending to translate."""
    ...     tag = find_tag_by_id(
    ...         browser.contents, 'translation-recommendation')
    ...     if tag is None:
    ...         return None
    ...     return extract_text(tag.decode_contents())

    >>> product_url = 'http://translations.launchpad.test/evolution'

That's all an anonymous user will see.

    >>> anon_browser.open(product_url)
    >>> print(find_translation_recommendation(anon_browser))
    Launchpad currently recommends translating Evolution trunk series.

A logged-in user is also invited to download translations.

    >>> user_browser.open(product_url)
    >>> print(find_translation_recommendation(user_browser))
    Launchpad currently recommends translating Evolution trunk series.
    You can also download translations for trunk.

A user with upload rights sees the invitation not just to download but
to upload as well.

    >>> admin_browser.open(product_url)
    >>> print(find_translation_recommendation(admin_browser))
    Launchpad currently recommends translating Evolution trunk series.
    You can also download or upload translations for trunk.

If there is no translatable series, no such recommendation is displayed.
A series is not translatable if all templates are disabled. We need to jump
through some hoops to create that situation.

    >>> login('foo.bar@canonical.com')
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.product import IProductSet
    >>> evotrunk = getUtility(IProductSet).getByName(
    ...     'evolution').getSeries('trunk')
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> potemplates = getUtility(IPOTemplateSet).getSubset(
    ...     productseries=evotrunk, iscurrent=True)
    >>> for potemplate in potemplates:
    ...     potemplate.iscurrent = False
    >>> logout()
    >>> admin_browser.open(product_url)
    >>> print(find_translation_recommendation(admin_browser))
    None

At the moment, translatable source packages are not recommended, although
the product is linked to one.

    >>> source_package = find_tag_by_id(
    ...     admin_browser.contents, 'portlet-translatable-packages')
    >>> print(extract_text(source_package))
    All translatable distribution packages
    evolution source package in Hoary

Instead a notice is displayed that the product has no translations.

    >>> notice = first_tag_by_class(admin_browser.contents, 'notice')
    >>> print(extract_text(notice))
    Getting started with translating your project in Launchpad
    Configure Translations
    There are no translations for this project.
