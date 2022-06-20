POTemplate index page
=====================

Make the test browser look like it's coming from an arbitrary South African
IP address, since we'll use that later.

    >>> anon_browser.addHeader('X_FORWARDED_FOR', '196.36.161.227')


DistoSeries
-----------

The index page for a POTemplate lists all available translations
for a source package. No Privileges Person visits the
evolution-2.2 POTemplate page.

    >>> anon_browser.open("http://translations.launchpad.test/"
    ...     "ubuntu/hoary/+source/evolution/+pots/evolution-2.2/")
    >>> print(anon_browser.title)
    Template ...evolution-2.2... : Hoary (5.04) :
    Translations : evolution package : Ubuntu

The owner of the template is diplayed.

    >>> owner_display = find_tag_by_id(anon_browser.contents,
    ...                                'potemplate-owner')
    >>> print(extract_text(owner_display))
    Owner: Rosetta Administrators

The page lists the status of all the translations. It merges the
No Privileges Person's languages (which are South African) with
the translated languages. English, which is a South African language
is not included because it is not translatable. For each language, we
show the number of messages that are untranslated, the percentage
that represents, when the translation was updated, and by whom.

    >>> content = find_main_content(anon_browser.contents)
    >>> print(extract_text(content.find_all('h1')[0]))
    Translation status

    >>> table = content.find_all('table')[0]
    >>> for row in table.find_all('tr'):
    ...     print(extract_text(row, formatter='html'))
    Language        Status  Untranslated Need review Changed Last    Edited By
    Afrikaans               22           ...         ...     &mdash; &mdash;
    Japanese                21           ...         ...     ...     Carlos...
    Sotho, Southern         22           ...         ...     &mdash; &mdash;
    Spanish                 15           1           1       ...     Valent...
    Xhosa                   22           ...         ...     ...     &mdash;
    Zulu                    22           ...         ...     &mdash; &mdash;


English is not translatable. We do not display English in the list of
languages when the user speaks English or even when English
translations exist. The Mozilla sourcepackage pkgconf-mozilla has
English translations, but they are not displayed to the user.

    >>> anon_browser.open('http://translations.launchpad.test/ubuntu/hoary/'
    ...     '+source/mozilla/+pots/pkgconf-mozilla')
    >>> table = find_tag_by_id(anon_browser.contents, 'language-chart')
    >>> for row in table.find_all('tr')[0:6]:
    ...     print(extract_text(row, formatter='html'))
    Language    Status  Untranslated Need review Changed Last  Edited By
    Afrikaans             9            ...         ...   ...   &mdash;
    Czech                 ...          ...         ...   ...   Miroslav Kure
    Danish                ...          ...         ...   ...   Morten Brix...
    Dutch                 ...          ...         ...   ...   Luk Claes
    Finnish               ...          ...         ...   ...   P&ouml;ll&auml;


Sharing information
-------------------

The template is sharing translations with the template of the same name in
the Ubuntu source package. This information is displayed on the page.

    >>> anon_browser.open('http://translations.launchpad.test/evolution'
    ...     '/trunk/+pots/evolution-2.2')
    >>> sharing_info = find_tag_by_id(
    ...     anon_browser.contents, 'sharing-information')
    >>> print(extract_text(sharing_info))
    Sharing Information
    This template is sharing translations with
    evolution in Ubuntu Hoary template evolution-2.2.
    View sharing details
    >>> print(sharing_info)
    <div...<a href="/ubuntu/hoary/+source/evolution/+pots/evolution-2.2"...

Likewise, the Ubuntu template gives information about how it is sharing
translations with the upstream project.

    >>> anon_browser.open('http://translations.launchpad.test/ubuntu'
    ...     '/hoary/+source/evolution/+pots/evolution-2.2')
    >>> sharing_info = find_tag_by_id(
    ...     anon_browser.contents, 'sharing-information')
    >>> print(extract_text(sharing_info))
    Sharing Information
    This template is sharing translations with
    Evolution trunk series template evolution-2.2.
    View sharing details
    >>> print(sharing_info)
    <div...<a href="/evolution/trunk/+pots/evolution-2.2"...

If the user has the right permissions, they are offered to edit the sharing
information.

    >>> admin_browser.open('http://translations.launchpad.test/evolution'
    ...     '/trunk/+pots/evolution-2.2')
    >>> sharing_details = find_tag_by_id(
    ...     admin_browser.contents, 'sharing-details')
    >>> print(extract_text(sharing_details))
    Edit sharing details
    >>> print(sharing_details['href'])
    http://.../ubuntu/hoary/+source/evolution/+sharing-details



Finding related templates
-------------------------

When products have more than one template, the page informs the user
that there are alternates that may be translated.

    >>> anon_browser.open("http://translations.launchpad.test/"
    ...     "evolution/trunk/+pots/evolution-2.2-test")
    >>> alternate_notice = find_tag_by_id(anon_browser.contents,
    ...                                   'potemplate-relatives')
    >>> print(extract_text(alternate_notice))
    Other templates here: evolution-2.2.

The notice links to the alternate template.

    >>> print(alternate_notice)
    <p...>
    <span>Other templates here:</span>
    <a href="/evolution/trunk/+pots/evolution-2.2">evolution-2.2</a>...
    </p>


When the branch or the source package contains less than five templates
they are all displayed on the template page.

A source package with five templates is created.

    >>> from zope.component import getUtility
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities

    >>> login('admin@canonical.com')
    >>> ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    >>> hoary = ubuntu.getSeries('hoary')
    >>> package = factory.makeSourcePackage(distroseries=hoary)
    >>> template = factory.makePOTemplate(
    ...     distroseries=hoary,
    ...     sourcepackagename=package.sourcepackagename, name='first')
    >>> template = factory.makePOTemplate(
    ...     distroseries=hoary,
    ...     sourcepackagename=package.sourcepackagename, name='second')
    >>> template = factory.makePOTemplate(
    ...     distroseries=hoary,
    ...     sourcepackagename=package.sourcepackagename, name='third')
    >>> template = factory.makePOTemplate(
    ...     distroseries=hoary,
    ...     sourcepackagename=package.sourcepackagename, name='forth')
    >>> template = factory.makePOTemplate(
    ...     distroseries=hoary,
    ...     sourcepackagename=package.sourcepackagename, name='fifth')
    >>> logout()

Visiting any template from the same page, the user sees links to the other
templates.

    >>> browser.open(
    ...     ("http://translations.launchpad.test/"
    ...     "ubuntu/hoary/+source/%s/+pots/%s") % (
    ...     package.name, template.name))
    >>> relatives = find_tag_by_id(
    ...     browser.contents, 'potemplate-relatives')
    >>> print(extract_text(relatives))
    Other templates here: first, forth, second, third.

For five templates, the page displays the first four templates in
alphabetical order, and a link to the page listing all templates.

Another template is added to the same source package.

    >>> login('admin@canonical.com')
    >>> template = factory.makePOTemplate(
    ...     distroseries=hoary,
    ...     sourcepackagename=package.sourcepackagename, name='sixth')
    >>> logout()

    >>> browser.open(
    ...     ("http://translations.launchpad.test/"
    ...     "ubuntu/hoary/+source/%s/+pots/%s") % (
    ...     package.name, template.name))
    >>> relatives = find_tag_by_id(
    ...     browser.contents, 'potemplate-relatives')
    >>> print(extract_text(relatives))
    Other templates here: fifth, first, forth, second
    and one other template.

    >>> browser.getLink('one other template').click()

For more than five templates, the page displays the first four templates in
alphabetical order, and a link to the page listing
all templates, stating the number of other templates.

Another template is added to the same source package.

    >>> login('admin@canonical.com')
    >>> template = factory.makePOTemplate(
    ...     distroseries=hoary,
    ...     sourcepackagename=package.sourcepackagename, name='seventh')
    >>> logout()

    >>> browser.open((
    ...     "http://translations.launchpad.test/"
    ...     "ubuntu/hoary/+source/%s/+pots/%s") % (
    ...     package.name, template.name))
    >>> relatives = find_tag_by_id(
    ...     browser.contents, 'potemplate-relatives')
    >>> print(extract_text(relatives))
    Other templates here: fifth, first, forth, second
    and 2 other templates.

    >>> browser.getLink('2 other templates').click()
    >>> browser.url == ((
    ...     'http://translations.launchpad.test/'
    ...     'ubuntu/hoary/+source/%s/+translations') % (
    ...     package.name))
    True

The "other templates" link for product series templates is leading to a
page showing all templates for that product series.

A product series with 7 templates is created.

    >>> from lp.app.enums import ServiceUsage
    >>> login('admin@canonical.com')
    >>> product = factory.makeProduct(name="fusa",
    ...     translations_usage=ServiceUsage.LAUNCHPAD)
    >>> product_trunk = product.getSeries('trunk')
    >>> template = factory.makePOTemplate(
    ...     productseries=product_trunk, name='first')
    >>> template = factory.makePOTemplate(
    ...     productseries=product_trunk, name='second')
    >>> template = factory.makePOTemplate(
    ...     productseries=product_trunk, name='third')
    >>> template = factory.makePOTemplate(
    ...     productseries=product_trunk, name='forth')
    >>> template = factory.makePOTemplate(
    ...     productseries=product_trunk, name='fifth')
    >>> template = factory.makePOTemplate(
    ...     productseries=product_trunk, name='sixth')
    >>> template = factory.makePOTemplate(
    ...     productseries=product_trunk, name='seventh')
    >>> logout()

    >>> browser.open((
    ...     "http://translations.launchpad.test/"
    ...     "fusa/trunk/+pots/%s") % template.name)
    >>> relatives = find_tag_by_id(
    ...     browser.contents, 'potemplate-relatives')
    >>> print(extract_text(relatives))
    Other templates here: fifth, first, forth, second
    and 2 other templates.

    >>> browser.getLink('2 other templates').click()
    >>> browser.url == (
    ...     'http://translations.launchpad.test/'
    ...     'fusa/trunk/+templates')
    True


Administering templates
-----------------------

Anonymous visitors see only a list of all existing templates, with no
administration or download/upload links.

    >>> anon_browser.open(
    ...     'http://translations.launchpad.test/'
    ...     'ubuntu/hoary/+source/evolution/+pots/evolution-2.2')
    >>> anon_browser.getLink('upload')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> anon_browser.getLink('download').click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

As an authenticated user, you should see the download link,
but not the one for uploading file to this potemplate.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/'
    ...     'ubuntu/hoary/+source/evolution/+pots/evolution-2.2')
    >>> user_browser.getLink('upload')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> user_browser.getLink('download').click()
    >>> print(user_browser.url)
    http://trans.../ubuntu/hoary/+source/evolution/+pots/evolution-2.2/+export

Translation administrators will see both download and upload links.
Beside administering this template, "Change permissions"
and "Change details" should be also accessible.

    >>> admin_browser.open(
    ...     'http://translations.launchpad.test/'
    ...     'ubuntu/hoary/+source/evolution/+pots/evolution-2.2')
    >>> admin_browser.getLink('upload').click()
    >>> print(admin_browser.url)
    http://trans.../ubuntu/hoary/+source/evolution/+pots/evolution-2.2/+upload

    >>> admin_browser.open(
    ...     'http://translations.launchpad.test/'
    ...     'ubuntu/hoary/+source/evolution/+pots/evolution-2.2')
    >>> admin_browser.getLink('download').click()
    >>> print(admin_browser.url)
    http://trans.../ubuntu/hoary/+source/evolution/+pots/evolution-2.2/+export

    >>> admin_browser.open(
    ...     'http://translations.launchpad.test/'
    ...     'ubuntu/hoary/+source/evolution/+pots/evolution-2.2')
    >>> admin_browser.getLink('Administer this template').click()
    >>> print(admin_browser.url)
    http://trans.../ubuntu/hoary/+source/evolution/+pots/evolution-2.2/+admin

    >>> admin_browser.open(
    ...     'http://translations.launchpad.test/'
    ...     'ubuntu/hoary/+source/evolution/+pots/evolution-2.2')
    >>> admin_browser.getLink('Change details').click()
    >>> print(admin_browser.url)
    http://trans.../ubuntu/hoary/+source/evolution/+pots/evolution-2.2/+edit
