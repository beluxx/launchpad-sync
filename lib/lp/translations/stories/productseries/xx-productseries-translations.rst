ProductSeries translations
==========================

This page shows a list of available languages for user to translate to in
a single product series, or instructions on how to set up a series for
translation.

    >>> from lp.app.enums import ServiceUsage
    >>> login("foo.bar@canonical.com")
    >>> frobnicator = factory.makeProduct(
    ...     name="frobnicator", translations_usage=ServiceUsage.LAUNCHPAD
    ... )
    >>> frobnicator_trunk = frobnicator.getSeries("trunk")
    >>> frobnicator_trunk_url = canonical_url(
    ...     frobnicator_trunk, rootsite="translations"
    ... )
    >>> logout()

Listing languages with translations is best checked with a helper method.

    >>> def extract_link_info(container):
    ...     link_tag = container.find("a")
    ...     if link_tag:
    ...         href = extract_link_from_tag(link_tag)
    ...     else:
    ...         href = ""
    ...     return int(extract_text(container)), href
    ...

    >>> def print_language_stats(browser):
    ...     table = find_tag_by_id(browser.contents, "languagestats")
    ...     if table is None:
    ...         print("No translations.")
    ...         return
    ...     language_rows = find_tags_by_class(str(table), "stats")
    ...     print(
    ...         "%-25s %13s %13s" % ("Language", "Untranslated", "Unreviewed")
    ...     )
    ...     for row in language_rows:
    ...         cols = row.find_all("td")
    ...         language = extract_text(cols[0])
    ...         untranslated = extract_link_info(cols[2])
    ...         unreviewed = extract_link_info(cols[3])
    ...         print(
    ...             "%-25s %13d %13d\n"
    ...             % (language, untranslated[0], unreviewed[0])
    ...         )
    ...         print("Untranslated link: %s\n" % untranslated[1])
    ...         print("Unreviewed link: %s\n" % unreviewed[1])
    ...

When there are no translatable templates, series is considered as not
being set up for translation.

    >>> anon_browser.open(frobnicator_trunk_url)
    >>> print(anon_browser.title)
    Series trunk : Translations : Frobnicator

    >>> main_content = find_main_content(anon_browser.contents)
    >>> print(extract_text(main_content.find_all("h1")[0]))
    Translation status by language

    >>> print_language_stats(anon_browser)
    No translations.

Explanation is shown to indicate that there are no translations for
this series.

    >>> print(extract_text(main_content.find_all("p")[0]))
    There are no translations for this release series.

Administrator will also see instructions on how to set up a project for
translation.

    >>> admin_browser.open(frobnicator_trunk_url)
    >>> main_content = find_main_content(admin_browser.contents)
    >>> paragraphs = main_content.find_all("p")
    >>> print(extract_text(main_content.find_all("p")[1]))
    To start translating your project...

With one translatable template (with fake stats for 10 messages), a listing
of existing translations is shown. Since there is only one template, each row
count links to the correctly filtered PO file pages.

    >>> login("foo.bar@canonical.com")
    >>> pot = factory.makePOTemplate(
    ...     productseries=frobnicator_trunk, name="template1"
    ... )
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(pot).messagecount = 10
    >>> pofile = factory.makePOFile("sr", potemplate=pot)
    >>> naked_pofile = removeSecurityProxy(pofile)
    >>> naked_pofile.rosettacount = 4
    >>> naked_pofile.updatescount = 2
    >>> naked_pofile.unreviewed_count = 5
    >>> logout()

    >>> browser.open(frobnicator_trunk_url)
    >>> print_language_stats(browser)  # noqa
    Language                   Untranslated    Unreviewed
    Serbian                               6             5
    Untranslated link: /frobnicator/trunk/+pots/template1/sr/+translate?show=untranslated
    Unreviewed link: /frobnicator/trunk/+pots/template1/sr/+translate?show=new_suggestions

Since there is only one template, language link directly to PO file
pages.

    >>> serbian_row = find_tags_by_class(browser.contents, "language-sr")[0]
    >>> serbian_link = serbian_row.find("a")
    >>> print(serbian_link["href"])
    /frobnicator/trunk/+pots/template1/sr/+translate

A product series can have more than one translatable template.

    >>> login("foo.bar@canonical.com")
    >>> pot = factory.makePOTemplate(
    ...     productseries=frobnicator_trunk, name="template2"
    ... )
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(pot).messagecount = 5
    >>> logout()

Statistics add up for untranslated messages. With more than one template the
aggregated row numbers do not link anywhere.

    >>> browser.open(frobnicator_trunk_url)
    >>> print_language_stats(browser)
    Language                   Untranslated    Unreviewed
    Serbian                              11             5
    Untranslated link:
    Unreviewed link:

With more than one template, link points to a product series per-language
translations page.

    >>> serbian_row = find_tags_by_class(browser.contents, "language-sr")[0]
    >>> serbian_link = serbian_row.find("a")
    >>> print(serbian_link["href"])
    /frobnicator/trunk/+lang/sr

Upload page and translations use
--------------------------------

If the product a series belongs to is not configured to use Launchpad
for Translations, the distroseries translations upload page will say so.
Otherwise, people may keep trying to upload their files rather than
finding and throwing the switch.

    >>> owner_browser = setupBrowser("Basic test@canonical.com:test")

Evolution is set up to use Launchpad Translations, so the notice does
not appear there.

    >>> owner_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "evolution/trunk/+translations-upload"
    ... )
    >>> print(
    ...     find_tag_by_id(
    ...         owner_browser.contents, "not-translated-in-launchpad"
    ...     )
    ... )
    None

Nor does it appear on the template upload pages.

    >>> owner_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "evolution/trunk/+pots/evolution-2.2/+upload"
    ... )
    >>> print(
    ...     find_tag_by_id(
    ...         owner_browser.contents, "not-translated-in-launchpad"
    ...     )
    ... )
    None

Now this is changed: Evolution's owner configures it not to use
Launchpad Translations.

    # Use the raw DB object to bypass the security proxy.
    >>> from lp.registry.model.product import Product
    >>> product = Product.byName("bazaar")
    >>> product.translations_usage = ServiceUsage.NOT_APPLICABLE

When the owner now visits the upload page for trunk, there's a notice.

    >>> owner_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "bazaar/trunk/+translations-upload"
    ... )
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             owner_browser.contents, "not-translated-in-launchpad"
    ...         )
    ...     )
    ... )
    trunk does not translate its messages.
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             owner_browser.contents, "translations-explanation"
    ...         )
    ...     )
    ... )
    Launchpad allows communities to translate projects using
    imports or a branch.
    Getting started with translating your project in Launchpad
    Configure Translations

The notice links to the page for configuring translations on the project.

    >>> owner_browser.getLink("Translations", index=1).click()
    >>> print(owner_browser.url)
    http://.../bazaar/+configure-translations

An administrator also sees the notice.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "bazaar/trunk/+translations-upload"
    ... )
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             admin_browser.contents, "not-translated-in-launchpad"
    ...         )
    ...     )
    ... )
    trunk does not translate its messages.
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             admin_browser.contents, "translations-explanation"
    ...         )
    ...     )
    ... )
    Launchpad allows communities to translate projects using
    imports or a branch.
    Getting started with translating your project in Launchpad
    Configure Translations

A Translations admin who is neither a Launchpad admin nor the project
owner (and so won't be able to change the project's settings) sees the
notice but not the link to the project's settings.

    >>> from zope.component import getUtility
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.teammembership import (
    ...     ITeamMembershipSet,
    ...     TeamMembershipStatus,
    ... )

    # Log in so as to be able to create objects
    >>> admin_email = "foo.bar@canonical.com"
    >>> login(admin_email)
    >>> admin_user = getUtility(IPersonSet).getByEmail(admin_email)

    >>> jtv = factory.makePerson(email="jtv-sample@canonical.com")
    >>> celebs = getUtility(ILaunchpadCelebrities)
    >>> membership = getUtility(ITeamMembershipSet).new(
    ...     jtv,
    ...     celebs.rosetta_experts,
    ...     TeamMembershipStatus.APPROVED,
    ...     admin_user,
    ... )
    >>> from storm.store import Store
    >>> Store.of(membership).flush()
    >>> logout()

    >>> jtv_browser = setupBrowser("Basic jtv-sample@canonical.com:test")
    >>> jtv_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "bazaar/trunk/+translations-upload"
    ... )

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             jtv_browser.contents, "not-translated-in-launchpad"
    ...         )
    ...     )
    ... )
    trunk does not translate its messages.

Branch synchronization options
------------------------------

When no imports or exports have been set up, the page indicates that

    >>> browser.open(frobnicator_trunk_url)
    >>> sync_settings = first_tag_by_class(
    ...     browser.contents, "automatic-synchronization"
    ... )
    >>> print(extract_text(sync_settings))
    Automatic synchronization
    This project is currently not using any synchronization
    with bazaar branches.

If a translation branch is set we indicate that exports are happening.
Imports are not mentioned until a series branch has been set.

    >>> login("foo.bar@canonical.com")
    >>> from lp.translations.interfaces.translations import (
    ...     TranslationsBranchImportMode,
    ... )
    >>> branch = factory.makeBranch(product=frobnicator)
    >>> frobnicator_trunk.branch = None
    >>> frobnicator_trunk.translations_autoimport_mode = (
    ...     TranslationsBranchImportMode.IMPORT_TEMPLATES
    ... )
    >>> frobnicator_trunk.translations_branch = branch
    >>> logout()

    >>> browser.open(frobnicator_trunk_url)
    >>> sync_settings = first_tag_by_class(
    ...     browser.contents, "automatic-synchronization"
    ... )
    >>> print(extract_text(sync_settings))
    Automatic synchronization
    Translations are exported daily to branch
    lp://dev/~person-name.../frobnicator/branch....

If the branch is private, though the page pretends to non-privileged users
that no synchronization has been set up.

    >>> from lp.app.enums import InformationType
    >>> login("foo.bar@canonical.com")
    >>> private_branch = factory.makeBranch(
    ...     product=frobnicator, information_type=InformationType.USERDATA
    ... )
    >>> frobnicator_trunk.translations_branch = private_branch
    >>> logout()

    >>> browser.open(frobnicator_trunk_url)
    >>> sync_settings = first_tag_by_class(
    ...     browser.contents, "automatic-synchronization"
    ... )
    >>> print(extract_text(sync_settings))
    Automatic synchronization
    This project is currently not using any synchronization
    with bazaar branches.

Imports are indicated in likewise manner once a series branch has been set.

    >>> login("foo.bar@canonical.com")
    >>> frobnicator_trunk.branch = branch
    >>> logout()

    >>> browser.open(frobnicator_trunk_url)
    >>> sync_settings = first_tag_by_class(
    ...     browser.contents, "automatic-synchronization"
    ... )
    >>> print(extract_text(sync_settings))
    Automatic synchronization
    Translations are imported with every update from branch
    lp://dev/frobnicator.


Translation focus
-----------------

If translation focus is not set, there is no recommendation of what
release series should be translated.

    >>> login("admin@canonical.com")
    >>> distribution = factory.makeDistribution(name="earthian")
    >>> distroseries = factory.makeDistroSeries(
    ...     name="1.4", distribution=distribution
    ... )
    >>> print(distribution.translation_focus)
    None
    >>> logout()
    >>> admin_browser.open("http://translations.launchpad.test/earthian/1.4")
    >>> print(find_tag_by_id(admin_browser.contents, "translation-focus"))
    None

If focus is set, nice explanatory text is displayed.

    >>> login("admin@canonical.com")
    >>> focus_series = factory.makeDistroSeries(
    ...     name="1.6", distribution=distribution
    ... )
    >>> distribution.translation_focus = focus_series
    >>> logout()
    >>> admin_browser.open("http://translations.launchpad.test/earthian/1.4")
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(admin_browser.contents, "translation-focus")
    ...     )
    ... )
    Launchpad currently recommends translating 1.6.


Setting up translations for series
----------------------------------

When visiting product translations main page, project developers sees
status for current series configured for translations.
Beside the "All translatable series" section, they will find the
"Set up translations for a series" section with links to other series
that can be configured for translations.

When projects have only one active series, and it is already configured,
project admin does not see the link for configuring other branches.

    >>> admin_browser.open("http://translations.launchpad.test/evolution")
    >>> untranslatable = find_tag_by_id(
    ...     admin_browser.contents, "portlet-untranslatable-branches"
    ... )
    >>> untranslatable is None
    True

A new series is added.

    >>> from lp.registry.interfaces.series import SeriesStatus
    >>> from lp.registry.model.product import Product
    >>> login("foo.bar@canonical.com")
    >>> evolution = Product.byName("evolution")
    >>> series = factory.makeProductSeries(product=evolution, name="evo-new")
    >>> series.status = SeriesStatus.EXPERIMENTAL
    >>> logout()

Project administrator will see links to configuring translations for
the new series.

    >>> admin_browser.open("http://translations.launchpad.test/evolution")
    >>> untranslatable = find_tag_by_id(
    ...     admin_browser.contents, "portlet-untranslatable-branches"
    ... )
    >>> print(extract_text(untranslatable))
    Set up translations for a series...
    evo-new series — manual or automatic...

For each series there is a link for accessing the series translations
page together with link for uploading a template from that series
(manual) and setting automatic imports.

    >>> print(admin_browser.getLink("Evolution evo-new series").url)
    http://translations.launchpad.test/evolution/evo-new/+translations

    >>> print(
    ...     admin_browser.getLink(
    ...         "manual", url="/evolution/evo-new/+translations-upload"
    ...     ).url
    ... )
    http://translations.launchpad.test/evolution/evo-new/+translations-upload

    >>> print(
    ...     admin_browser.getLink(
    ...         "automatic", url="/evolution/evo-new/+translations-settings"
    ...     ).url
    ... )
    ... # noqa
    http://translations.launchpad.test/evolution/evo-new/+translations-settings
