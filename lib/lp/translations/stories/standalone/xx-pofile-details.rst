POFile Details Page
===================

Each translation file has an overview page which shows the list of
contributors.

    >>> from lp.testing.sampledata import ADMIN_EMAIL
    >>> anon_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/es/+details"
    ... )
    >>> print(
    ...     backslashreplace(
    ...         extract_text(find_main_content(anon_browser.contents))
    ...     )
    ... )
    Details for Spanish translation
    ...
    Latest contributor:
    Carlos...
    Contributors to this translation
    The following people have made some contribution to this specific
    translation:
    Carlos... (filter)
    Mark Shuttleworth (filter)
    No Privileges Person (filter)

User can filter any contributions done by Carlos (the first person
appearing among contributors), by choosing the 'filter' link:

    >>> anon_browser.getLink("filter").click()
    >>> print(anon_browser.title)
    Translations by Carlos ... in ...

To display all the translations submitted by Carlos, and allow easier
debugging and problem catching when changes are introduced, we define
a separate method to pretty-print all the translations.

    >>> def print_shown_translations(browser):
    ...     # Extract a class from any of the contained <td> elements,
    ...     # returning the first one actually defined.
    ...     def get_first_defined_class(cells):
    ...         for cell in cells:
    ...             type = dict(cell.attrs).get("class")
    ...             if type:
    ...                 return " ".join(type)
    ...         return None
    ...
    ...     # Get contents of all the `cells`, and join them with spaces.
    ...     def get_columns(cells):
    ...         contents = []
    ...         for cell in cells:
    ...             text = extract_text(cell).replace("\n", "\\n")
    ...             if text:
    ...                 contents.append(text)
    ...         return " ".join(contents)
    ...
    ...     table = find_tags_by_class(browser.contents, "listing")[0]
    ...     rows = table.find_all("tr")
    ...     for row in rows:
    ...         cells = row.find_all("td")
    ...         type = get_first_defined_class(cells)
    ...         types = {
    ...             "englishstring": "english",
    ...             "usedtranslation": " used",
    ...             "hiddentranslation": " old",
    ...             "suggestedtranslation": " unused",
    ...         }
    ...         contents = get_columns(cells)
    ...         if len(contents) > 50:
    ...             contents = contents[:47] + "..."
    ...         print("%-10s %s" % (types[type], contents))
    ...

A user can see all the submissions Carlos has made to this POFile.
Note that 'english' in the first column indicates a msgid, and 'used',
'old' or 'unused' indicate type of a translation ('used' if it is
is_current_ubuntu, 'unused' if not current but unreviewed, and 'old' if it
was reviewed and rejected).

    >>> print_shown_translations(anon_browser)
    english    1. evolution addressbook
     used      2005-04-07 libreta de direcciones de Evolution
    english    2. current addressbook folder
     used      2005-04-07 carpeta de libretas de direcciones a...
    english    3. have
     old       2006-12-22 lalalala
     used      2005-04-07 tiene
    english    5. cards
     used      2005-04-07 tarjetas
    english    14. The location and hierarchy of the Evolution...
     used      2005-04-07 La ubicaci...
    english    15. %d contact\n%d contacts
     used      2005-04-07 %d contacto\n%d contactos
    english    16. Opening %d contact will open %d new window ...
     used      2005-04-07 Abrir %d contacto abrir...
    english    18. EncFS Password:
     used      2005-04-07 Contrase...

Looking at the same page filtered by 'no-priv' person, the user is shown
only a single unused suggestion instead:

    >>> anon_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/"
    ...     "+pots/evolution-2.2/es/+filter?person=no-priv"
    ... )
    >>> print_shown_translations(anon_browser)
    english    14. The location and hierarchy of the Evolution...
     unused    2005-08-29 This is a suggestion added by a non-...

A POTMsgSet sequence number is also a link to edit a translation.

    >>> anon_browser.getLink("14.").click()
    >>> print(anon_browser.url)
    http://.../evolution/trunk/+pots/evolution-2.2/es/14/+translate
    >>> print(anon_browser.title)
    Browsing Spanish translation...


Invalid input
-------------

Manually filtering by non-existent user warns the user of the problem.

    >>> anon_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/"
    ...     "+pots/evolution-2.2/es/+filter?person=danilo"
    ... )
    >>> print_feedback_messages(anon_browser.contents)
    Requested person not found.
    This person has made no contributions to this file.

If a person to filter by is not specified, user is notified of that.

    >>> anon_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/"
    ...     "+pots/evolution-2.2/es/+filter"
    ... )
    >>> print_feedback_messages(anon_browser.contents)
    No person to filter by specified.
    This person has made no contributions to this file.


Merged accounts
---------------

On the overview page of each translation pofile, users will not see merged
accounts.

We'll create two new accounts to demonstrate this.

    >>> from zope.component import getUtility
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities

    >>> login(ADMIN_EMAIL)
    >>> ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    >>> hoary = ubuntu.getSeries("hoary")
    >>> translator = factory.makePerson(displayname="Poly Glot")
    >>> merged_translator = factory.makePerson(displayname="Mere Pere")
    >>> package = factory.makeSourcePackage(distroseries=hoary)
    >>> template = factory.makePOTemplate(
    ...     distroseries=hoary,
    ...     sourcepackagename=package.sourcepackagename,
    ...     name="first",
    ... )
    >>> language_code = "es"
    >>> pofile = factory.makePOFile(language_code, potemplate=template)
    >>> potmsgset = factory.makePOTMsgSet(template)
    >>> translation = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile, translator=merged_translator, potmsgset=potmsgset
    ... )
    >>> translation = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile, translator=translator, potmsgset=potmsgset
    ... )
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(merged_translator).merged = translator
    >>> logout()

    >>> browser.open(
    ...     (
    ...         "http://translations.launchpad.test/"
    ...         "ubuntu/hoary/+source/%s/+pots/%s/%s/+details"
    ...     )
    ...     % (package.name, template.name, language_code)
    ... )
    >>> main_text = extract_text(find_main_content(browser.contents))
    >>> print(main_text)
    Details for ...
    Contributors to this translation
    The following people have made some contribution to this specific
    translation:
    Poly Glot (filter)

    >>> "Mere Pere" in main_text
    False


Statistics
----------

A POFile's details page shows translation statistics.

    >>> login(ADMIN_EMAIL)
    >>> naked_pofile = removeSecurityProxy(factory.makePOFile())
    >>> naked_pofile.potemplate.messagecount = 10
    >>> naked_pofile.untranslated = 3
    >>> naked_pofile.currentcount = 4
    >>> naked_pofile.updatescount = 2
    >>> naked_pofile.rosettacount = 1 + naked_pofile.updatescount
    >>> pofile_url = canonical_url(naked_pofile) + "/+details"
    >>> logout()

    >>> browser.open(pofile_url)
    >>> stats_portlet = find_tag_by_id(browser.contents, "portlet-stats")
    >>> print(extract_text(stats_portlet))
    Statistics
    Messages: 10
    Translated: 7 (70.0%)
    Untranslated: 3 (30.0%)
    Shared between Ubuntu and upstream: 4 (40.0%)
    Translated differently between Ubuntu and upstream: 2 (20.0%)
    Only translated on this side: 1 (10.0%)
