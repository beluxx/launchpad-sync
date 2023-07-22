POTemplateSet
=============

Test that the security setup for IPOTemplateSet is working

    >>> from zope.component import getUtility
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> potemplate_set = getUtility(IPOTemplateSet)


getAllByName
------------

This method will return all IPOTemplate that have a given name.

    >>> evolution_templates = potemplate_set.getAllByName("evolution-2.2")
    >>> titles = [potemplate.title for potemplate in evolution_templates]
    >>> (
    ...     'Template "evolution-2.2" in Ubuntu Hoary package "evolution"'
    ...     in titles
    ... )
    True

    >>> 'Template "evolution-2.2" in Evolution trunk' in titles
    True


getAllOrderByDateLastUpdated
----------------------------

This method will give us all available IPOTemplate sorted by their
modification date.

    >>> templates = list(potemplate_set.getAllOrderByDateLastUpdated())
    >>> len(templates)
    10

    >>> templates[0].date_last_updated >= templates[5].date_last_updated
    True

    >>> templates[1].date_last_updated >= templates[5].date_last_updated
    True

    >>> templates[2].date_last_updated >= templates[5].date_last_updated
    True

    >>> templates[3].date_last_updated >= templates[5].date_last_updated
    True

    >>> templates[4].date_last_updated >= templates[5].date_last_updated
    True

= POTemplateSubset=

A POTemplateSubset describes the subset of all templates that belong to
either one product series, or one source package in one distro series.


new
---

When we create a template, it is initialized with a default header.

    >>> from lp.registry.model.product import ProductSet
    >>> alsa_product = ProductSet().getByName("alsa-utils")
    >>> alsa_trunk = alsa_product.getSeries("trunk")
    >>> alsa_subset = potemplate_set.getSubset(productseries=alsa_trunk)
    >>> from lp.registry.model.person import PersonSet
    >>> user = PersonSet().getByEmail("test@canonical.com")
    >>> new_template = alsa_subset.new(
    ...     "testtemplate", "testing", "po/testing.pot", user
    ... )

    >>> print(new_template.header)
    Project-Id-Version: PACKAGE VERSION
    Report-Msgid-Bugs-To: FULL NAME <EMAIL@ADDRESS>
    POT-Creation-Date: ...
    PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
    Last-Translator: FULL NAME <EMAIL@ADDRESS>
    Language-Team: LANGUAGE <LL@li.org>
    MIME-Version: 1.0
    Content-Type: text/plain; charset=UTF-8
    Content-Transfer-Encoding: 8bit


getPOTemplateByName
-------------------

This method gives us the IPOTemplate that belongs to this subset and its
name is the given one.

    >>> from lp.registry.model.productseries import ProductSeries
    >>> productseries = ProductSeries.get(3)
    >>> potemplatesubset = potemplate_set.getSubset(
    ...     productseries=productseries
    ... )

    >>> potemplate = potemplatesubset.getPOTemplateByName("evolution-2.2")
    >>> print(potemplate.title)
    Template "evolution-2.2" in Evolution trunk


getPOTemplateByPath
-------------------

This method gives us the IPOTemplate that belongs to this subset and its
path in the source code is the given one.

    >>> potemplate = potemplatesubset.getPOTemplateByPath(
    ...     "po/evolution-2.2-test.pot"
    ... )
    >>> print(potemplate.title)
    Template "evolution-2.2-test" in Evolution trunk


getAllOrderByDateLastUpdated
----------------------------

This method will give us all available IPOTemplate for this subset
sorted by their modification date.

    >>> templates = list(potemplatesubset.getAllOrderByDateLastUpdated())
    >>> len(templates)
    2

    >>> templates[0].date_last_updated >= templates[1].date_last_updated
    True


getClosestPOTemplate
--------------------

With this method, we get the IPOTemplate from this Subset that has the
bigger part of the path in common.

To do this test, first we check the evolution product, it has two
potemplates in the same path and thus, this method should not get any
value.

    >>> productseries = ProductSeries.get(3)
    >>> potemplatesubset = potemplate_set.getSubset(
    ...     productseries=productseries
    ... )

    >>> for template in potemplatesubset:
    ...     print(template.path)
    ...
    po/evolution-2.2.pot
    po/evolution-2.2-test.pot

    >>> potemplatesubset.getClosestPOTemplate("po") is None
    True

Now, we move to the NetApplet product, we should detect it.

    >>> productseries = ProductSeries.get(5)
    >>> potemplatesubset = potemplate_set.getSubset(
    ...     productseries=productseries
    ... )

    >>> for template in potemplatesubset:
    ...     print(template.path)
    ...
    po/netapplet.pot

    >>> potemplatesubset.getClosestPOTemplate("po") is None
    False

But if we give the empty string or None, we get nothing

    >>> potemplatesubset.getClosestPOTemplate("") is None
    True

    >>> potemplatesubset.getClosestPOTemplate("") is None
    True


POTemplate
==========

POTemplate is an object with all strings that must be translated for a
concrete context.

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.testing import verifyObject
    >>> from lp.translations.interfaces.potemplate import IPOTemplate
    >>> from lp.translations.model.potemplate import POTemplate
    >>> potemplate = IStore(POTemplate).get(POTemplate, 1)

It implements the IPOTemplate interface.

    >>> verifyObject(IPOTemplate, potemplate)
    True


getPOFileByPath
---------------

We can get an IPOFile inside a template based on its path.

    >>> pofile = potemplate.getPOFileByPath("es.po")
    >>> print(pofile.title)
    Spanish (es) translation of evolution-2.2 in Evolution trunk


getPlaceholderPOFile
--------------------

To get an IPOFile object even for languages which don't have a
translation of this template, we use the getPlaceholderPOFile method,
passing in the language.

    >>> xx_language = factory.makeLanguage("xx@test", name="Test language")
    >>> xx_pofile = potemplate.getPlaceholderPOFile(xx_language)
    >>> print(xx_pofile.title)
    Test language (xx@test) translation of evolution-2.2 in Evolution trunk


newPOFile
---------

The Portuguese translation has not been started yet; therefore, when we
call IPOTemplate.newPOFile() a POFile instance will be created.

    >>> pofile = potemplate.newPOFile("pt")

By default, we should get a path for this pofile, that has some
information about its potemplate's filename so we don't have conflicts
with other pofiles.

    >>> print(pofile.path)
    po/evolution-2.2-pt.po

Lets try to access untranslated entries here.

    >>> potmsgsets = list(pofile.getPOTMsgSetUntranslated())
    >>> len(potmsgsets) == potemplate.getPOTMsgSetsCount(current=True)
    True

And there shouldn't be any translated entries

    >>> potmsgsets = list(pofile.getPOTMsgSetTranslated())
    >>> len(potmsgsets)
    0


relatives_by_source
-------------------

This property gives us an iterator of IPOTemplate objects that are in
the same context IProductSeries or IDistroSeries/ISourcePackageName and
are 'current'.

First, we can see the relatives in a IProductSeries context.

    >>> for relative_potemplate in potemplate.relatives_by_source:
    ...     assert relative_potemplate.iscurrent
    ...     print(relative_potemplate.title)
    ...
    Template "evolution-2.2-test" in Evolution trunk

Let's get a new IPOTemplate that belongs to an IDistroSeries:

    >>> potemplate = IStore(POTemplate).get(POTemplate, 4)
    >>> print(potemplate.title)
    Template "evolution-2.2" in Ubuntu Hoary package "evolution"

And this is the list of templates related with this one based on its
context:

    >>> for relative_potemplate in potemplate.relatives_by_source:
    ...     assert relative_potemplate.iscurrent
    ...     print(relative_potemplate.title)
    ...
    Template "man" in Ubuntu Hoary package "evolution"

But we can see that there is a third template in this context:

    >>> not_current_template = IStore(POTemplate).get(POTemplate, 9)
    >>> not_current_template.productseries == potemplate.productseries
    True

    >>> not_current_template.distroseries == potemplate.distroseries
    True

    >>> not_current_template.sourcepackagename == potemplate.sourcepackagename
    True

And this is the explanation of not having it in previous lists, it's not
current.

    >>> not_current_template.iscurrent
    False


export()
--------

Templates can be exported to its native format.

    >>> for line in potemplate.export().decode("ASCII").split("\n"):
    ...     if "X-Launchpad-Export-Date" in line:
    ...         # Avoid a time bomb in our tests and ignore this field.
    ...         continue
    ...     print(line)  # noqa
    ...
    #, fuzzy
    msgid ""
    msgstr ""
    "Project-Id-Version: PACKAGE VERSION\n"
    "Report-Msgid-Bugs-To: \n"
    "POT-Creation-Date: 2005-04-07 14:10+0200\n"
    "PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
    "Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
    "Language-Team: LANGUAGE <LL@li.org>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: text/plain; charset=ASCII\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n"
    "X-Generator: Launchpad (build ...)\n"
    <BLANKLINE>
    #: a11y/addressbook/ea-addressbook-view.c:94
    #: a11y/addressbook/ea-addressbook-view.c:103
    #: a11y/addressbook/ea-minicard-view.c:119
    msgid "evolution addressbook"
    msgstr ""
    <BLANKLINE>
    #: a11y/addressbook/ea-minicard-view.c:101
    msgid "current addressbook folder"
    msgstr ""
    <BLANKLINE>
    #: a11y/addressbook/ea-minicard-view.c:102
    msgid "have "
    msgstr ""
    <BLANKLINE>
    #: a11y/addressbook/ea-minicard-view.c:102
    msgid "has "
    msgstr ""
    <BLANKLINE>
    #: a11y/addressbook/ea-minicard-view.c:104
    msgid " cards"
    msgstr ""
    <BLANKLINE>
    #: a11y/addressbook/ea-minicard-view.c:104
    msgid " card"
    msgstr ""
    <BLANKLINE>
    #: a11y/addressbook/ea-minicard-view.c:105
    msgid "contact's header: "
    msgstr ""
    <BLANKLINE>
    #: a11y/addressbook/ea-minicard.c:166
    msgid "evolution minicard"
    msgstr ""
    <BLANKLINE>
    #. addressbook:ldap-init primary
    #: addressbook/addressbook-errors.xml.h:2
    msgid "This addressbook could not be opened."
    msgstr ""
    <BLANKLINE>
    #. addressbook:ldap-init secondary
    #: addressbook/addressbook-errors.xml.h:4
    msgid ""
    "This addressbook server might unreachable or the server name may be "
    "misspelled or your network connection could be down."
    msgstr ""
    <BLANKLINE>
    #. addressbook:ldap-auth primary
    #: addressbook/addressbook-errors.xml.h:6
    msgid "Failed to authenticate with LDAP server."
    msgstr ""
    <BLANKLINE>
    #. addressbook:ldap-auth secondary
    #: addressbook/addressbook-errors.xml.h:8
    msgid ""
    "Check to make sure your password is spelled correctly and that you are using "
    "a supported login method. Remember that many passwords are case sensitive; "
    "your caps lock might be on."
    msgstr ""
    <BLANKLINE>
    #: addressbook/gui/component/addressbook-migrate.c:124
    #: calendar/gui/migration.c:188 mail/em-migrate.c:1201
    #, c-format
    msgid "Migrating `%s':"
    msgstr ""
    <BLANKLINE>
    #: addressbook/gui/component/addressbook-migrate.c:1123
    msgid ""
    "The location and hierarchy of the Evolution contact folders has changed "
    "since Evolution 1.x.\n"
    "\n"
    "Please be patient while Evolution migrates your folders..."
    msgstr ""
    <BLANKLINE>
    #: addressbook/gui/widgets/e-addressbook-model.c:151
    #, c-format
    msgid "%d contact"
    msgid_plural "%d contacts"
    msgstr[0] ""
    msgstr[1] ""
    <BLANKLINE>
    #: addressbook/gui/widgets/eab-gui-util.c:275
    #, c-format
    msgid ""
    "Opening %d contact will open %d new window as well.\n"
    "Do you really want to display this contact?"
    msgid_plural ""
    "Opening %d contacts will open %d new windows as well.\n"
    "Do you really want to display all of these contacts?"
    msgstr[0] ""
    msgstr[1] ""
    <BLANKLINE>
    #: addressbook/gui/widgets/foo.c:345
    #, c-format
    msgid "%d foo"
    msgid_plural "%d bars"
    msgstr[0] ""
    msgstr[1] ""
    <BLANKLINE>
    # start po-group: common
    #. xgroup(common)
    #: encfs/FileUtils.cpp:1044
    msgid "EncFS Password: "
    msgstr ""
    <BLANKLINE>
    #. xgroup(usage)
    #: encfs/main.cpp:340
    msgid ""
    "When specifying daemon mode, you must use absolute paths (beginning with '/')"
    msgstr ""
    <BLANKLINE>
    #. xgroup(setup)
    #: encfs/FileUtils.cpp:535
    #, c-format
    msgid ""
    "Please select a key size in bits.  The cipher you have chosen\n"
    "supports sizes from %i to %i bits in increments of %i bits.\n"
    "For example: "
    msgstr ""
    <BLANKLINE>
    #: encfs/encfsctl.cpp:346
    #, c-format
    msgid "Found %i invalid file."
    msgid_plural "Found %i invalid files."
    msgstr[0] ""
    msgstr[1] ""
    <BLANKLINE>
    #: modules/aggregator.module:15
    msgid ""
    "\n"
    "      <p>Thousands of sites (particularly news sites and weblogs) publish "
    "their latest headlines and/or stories in a machine-readable format so that "
    "other sites can easily link to them. This content is usually in the form of "
    "an <a href=\"http://blogs.law.harvard.edu/tech/rss\">RSS</a> feed (which is "
    "an XML-based syndication standard).</p>\n"
    "      <p>You can read aggregated content from many sites using RSS feed "
    "readers, such as <a "
    "href=\"http://www.disobey.com/amphetadesk/\">Amphetadesk</a>.</p>\n"
    "      <p>Drupal provides the means to aggregate feeds from many sites and "
    "display these aggregated feeds to your site's visitors. To do this, enable "
    "the aggregator module in site administration and then go to the aggregator "
    "configuration page, where you can subscribe to feeds and set up other "
    "options.</p>\n"
    "      <h3>How do I find RSS feeds to aggregate?</h3>\n"
    "      <p>Many web sites (especially weblogs) display small XML icons or "
    "other obvious links on their home page. You can follow these to obtain the "
    "web address for the RSS feed. Common extensions for RSS feeds are .rss, .xml "
    "and .rdf. For example: <a href=\"http://slashdot.org/slashdot.rdf\">Slashdot "
    "RSS</a>.</p>\n"
    "      <p>If you can't find a feed for a site, or you want to find several "
    "feeds on a given topic, try an RSS syndication directory such as <a "
    "href=\"http://www.syndic8.com/\">Syndic8</a>.</p>\n"
    "      <p>To learn more about RSS, read Mark Pilgrim's <a "
    "href=\"http://www.xml.com/pub/a/2002/12/18/dive-into-xml.html\">What is "
    "RSS</a> and WebReference.com's <a "
    "href=\"http://www.webreference.com/authoring/languages/xml/rss/1/\">The "
    "Evolution of RSS</a> articles.</p>\n"
    "      <p>NOTE: Enable your site's XML syndication button by turning on the "
    "Syndicate block in block management.</p>\n"
    "      <h3>How do I add a news feed?</h3>\n"
    "      <p>To subscribe to an RSS feed on another site, use the <a href=\"% "
    "admin-news\">aggregation page</a>.</p>\n"
    "      <p>Once there, click the <a href=\"%new-feed\">new feed</a> tab. "
    "Drupal will then ask for the following:</p>\n"
    "      <ul>\n"
    "       <li><strong>Title</strong> -- The text entered here will be used in "
    "your news aggregator, within the administration configuration section, and "
    "as a title for the news feed block. As a general rule, use the web site name "
    "from which the feed originates.</li>\n"
    "       <li><strong>URL</strong> -- Here you'll enter the fully-qualified web "
    "address for the feed you wish to subscribe to.</li>\n"
    "       <li><strong>Update interval</strong> -- This is how often Drupal will "
    "scan the feed for new content. This defaults to every hour. Checking a feed "
    "more frequently that this is typically a waste of bandwidth and is "
    "considered somewhat impolite. For automatic updates to work, cron.php must "
    "be called regularly. If it is not, you'll have to manually update the feeds "
    "one at a time within the news aggregation administration page by using <a "
    "href=\"%update-items\">update items</a>.</li>\n"
    "       <li><strong>Latest items block</strong> -- The number of items "
    "selected here will determine how many of the latest items from the feed will "
    "appear in a block which may be enabled and placed in the <a "
    "href=\"%block\">blocks</a> administration page.</li>\n"
    "       <li><strong>Automatically file items</strong> -- As items are "
    "received from a feed they will be put in any categories you have selected "
    "here.</li>\n"
    "      </ul>\n"
    "      <p>Once you have submitted the new feed, check to make sure it is "
    "working properly by selecting <a href=\"%update-items\">update items</a> on "
    "the <a href=\"%admin-news\">aggregation page</a>. If you do not see any "
    "items listed for that feed, edit the feed and make sure that the URL was "
    "entered correctly.</p>\n"
    "      <h3>Adding categories</h3>\n"
    "      <p>News items can be filed into categories. To create a category, "
    "start at the <a href=\"%admin-news\">aggregation page</a>.</p>\n"
    "      <p>Once there, select <a href=\"%new-category\">new category</a> from "
    "the menu. Drupal will then ask for the following:</p>\n"
    "      <ul>\n"
    "       <li><strong>Title</strong> -- The title will be used in the <em>news "
    "by topics</em> listing in your news aggregator and for the block created for "
    "the bundle.</li>\n"
    "       <li><strong>Description</strong> -- A short description of the "
    "category to tell users more details about what news items they might find in "
    "the category.</li>\n"
    "       <li><strong>Latest items block</strong> -- The number of items "
    "selected here will determine how many of the latest items from the category "
    "will appear in a block which may be enabled and placed in the <a "
    "href=\"%block\">blocks</a> administration page.</li>\n"
    "      </ul>\n"
    "      <h3>Using the news aggregator</h3>\n"
    "      <p>The news aggregator has a number of ways that it displays your "
    "subscribed content:</p>\n"
    "      <ul>\n"
    "       <li><strong><a href=\"%news-aggregator\">News aggregator</a></strong> "
    "(latest news) -- Displays all incoming items in the order in which they were "
    "received.</li>\n"
    "       <li><strong><a href=\"%sources\">Sources</a></strong> -- Organizes "
    "incoming content by feed, displaying feed titles (each of which links to a "
    "page with the latest items from that feed) and item titles (which link to "
    "that item's actual story/article).</li>\n"
    "       <li><strong><a href=\"%categories\">Categories</a></strong> -- "
    "Organizes incoming content by category, displaying category titles (each of "
    "which links to a page with the latest items from that category) and item "
    "titles (which link to that item's actual story/article).</li>\n"
    "      </ul>\n"
    "      <p>Pages that display items (for sources, categories, etc.) display "
    "the following for each item:\n"
    "      <ul>\n"
    "       <li>The title of the item (its headline).</li>\n"
    "       <li>The categories that the item belongs to, each of which links to "
    "that particular category page as detailed above.</li>\n"
    "       <li>A description containing the first few paragraphs or a summary of "
    "the item (if available).</li>\n"
    "       <li>The name of the feed, which links to the individual feed's page, "
    "listing information about that feed and items for that feed only. This is "
    "not shown on feed pages (they would link to the page you're currently "
    "on).</li>\n"
    "      </ul>\n"
    "      <p>Additionally, users with the <em>administer news feeds "
    "permission</em> will see a link to categorize the news items. Clicking this "
    "will allow them to select which category(s) each news item is in.</p>\n"
    "      <h3>Technical details</h3>\n"
    "      <p>Drupal automatically generates an OPML feed file that is available "
    "by selecting the XML icon on the News Sources page.</p>\n"
    "      <p>When fetching feeds Drupal supports conditional GETs, this reduces "
    "the bandwidth usage for feeds that have not been updated since the last "
    "check.</p>\n"
    "      <p>If a feed is permanently moved to a new location Drupal will "
    "automatically update the feed URL to the new address.</p>"
    msgstr ""


exportWithTranslations()
------------------------

We can also get a template export that includes all translations inside.
The file format we will get depends on the default template file format.

In this case, we are going to see how a PO template is exported with
translations.

    >>> print(potemplate.source_file_format.name)
    PO

    >>> exported_translation_file = potemplate.exportWithTranslations()

PO file format doesn't have a native way to export template +
translations, instead, we get a tarball with all those files.

    >>> print(exported_translation_file.content_type)
    application/x-gtar

Inspecting the tarball content, we have the list of entries exported.
This includes the 'pt' POFile that was created earlier on the
'evolution' product as this is sharing translations with the source
package that this potemplate is from.

    >>> from lp.services.helpers import bytes_to_tarfile
    >>> tarfile_bytes = exported_translation_file.read()
    >>> tarfile = bytes_to_tarfile(tarfile_bytes)

    >>> sorted(tarfile.getnames())
    ['evolution-2.2', 'evolution-2.2/evolution-2.2-es.po',
     'evolution-2.2/evolution-2.2-ja.po', 'evolution-2.2/evolution-2.2-xh.po',
     'po', 'po/evolution-2.2-pt.po', 'po/evolution-2.2.pot']

The *-es.po file is indeed the Spanish translation...

    >>> file_content = tarfile.extractfile(
    ...     "evolution-2.2/evolution-2.2-es.po"
    ... )
    >>> print(file_content.readline().decode())
    # traducción de es.po al Spanish

And GNU tar can cope with it.

    >>> from lp.services.helpers import simple_popen2
    >>> contents = simple_popen2(["tar", "ztf", "-"], tarfile_bytes)
    >>> for line in sorted(contents.splitlines()):
    ...     print(line.decode())
    ...
    evolution-2.2/
    evolution-2.2/evolution-2.2-es.po
    evolution-2.2/evolution-2.2-ja.po
    evolution-2.2/evolution-2.2-xh.po
    po/
    po/evolution-2.2-pt.po
    po/evolution-2.2.pot

    >>> pofile = simple_popen2(
    ...     ["tar", "zxfO", "-", "evolution-2.2/evolution-2.2-es.po"],
    ...     tarfile_bytes,
    ... )
    >>> print(pofile.decode().split("\n")[0])
    # traducción de es.po al Spanish
