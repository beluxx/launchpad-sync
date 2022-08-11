Person's translation activity
=============================

A person's translation activity page displays the translations that the
person has contributed to.

Here the person whose activity we're going to look at is Carlos.

    >>> anon_browser.open(
    ...     "http://translations.launchpad.test/people/carlos/+activity")

The user can see in the page navigation that Carlos has so far worked
on six files, five of which are shown on this page.

    >>> print(extract_text(find_tag_by_id(
    ...     anon_browser.contents, 'top-navigation')))
    1...5...of...6...results...

The user sees a table with four columns with headings, with five POFiles
listed which Carlos has contributed to.

    # Prints a heading and formatted list of POFiles and latest submissions.
    >>> def print_activity_list(listing):
    ...     for row in listing.find_all('tr'):
    ...         print(extract_text(row))

    >>> listing = find_tag_by_id(anon_browser.contents, 'activity-table')
    >>> print_activity_list(listing)
    2007-07-12
    English (en) translation of pkgconf-mozilla in Ubuntu Hoary package
    "mozilla"
    2007-04-07
    Spanish (es) translation of alsa-utils in alsa-utils trunk
    2007-01-24
    Spanish (es) translation of man in Ubuntu Hoary package "evolution"
    2006-12-22
    Spanish (es) translation of evolution-2.2 in Evolution trunk
    2005-10-11
    Japanese (ja) translation of evolution-2.2 in Ubuntu Hoary package
    "evolution"

Clicking one of the entries takes you to a page listing all of Carlos'
contributions to the selected translation.

    >>> alsa_utils_link = (
    ...     'Spanish (es) translation of alsa-utils in alsa-utils trunk')
    >>> anon_browser.getLink(alsa_utils_link).click()
    >>> print(anon_browser.title)
    Translations by ...Spanish (es)...


URL-escaped user names
----------------------

Since the user's name is included in the URL, and user names can contain
some slightly weird characters, it is escaped especially for this usage.

For instance, here's a user called a+b.

    >>> login('carlos@canonical.com')
    >>> ab = factory.makePerson(name='a+b')
    >>> sr_pofile = factory.makePOFile('sr')
    >>> message = factory.makeCurrentTranslationMessage(
    ...     pofile=sr_pofile, translator=ab)
    >>> person_url = canonical_url(ab, rootsite='translations')
    >>> logout()

When a+b goes to see the translations they have done, they see a correctly
encoded link to a filtered PO file page.

    >>> user_browser.open(person_url + '/+activity')
    >>> table = find_tag_by_id(user_browser.contents, 'activity-table')
    >>> link = table.find('a')
    >>> url = link['href']
    >>> print(url.split('/')[-1])
    +filter?person=a%2Bb

Because of this, the link actually works.

    >>> user_browser.open(url)
    >>> print(user_browser.title)
    Translations by A+b in...Serbian (sr) translation...
