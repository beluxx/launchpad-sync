Site-wide Search
================

Launchpad features a site-wide search that combines an external search
engine's site-specific search with Launchpad's prominent objects (projects,
bugs, teams, etc.).

    # Our very helpful function for printing all the page results.

    >>> def print_search_results(contents=None):
    ...     if contents is None:
    ...         contents = anon_browser.contents
    ...     tag = find_tag_by_id(contents, 'search-results')
    ...     if tag:
    ...         print(extract_text(tag))

    # Another helper to make searching convenient.

    >>> def search_for(terms, browser=anon_browser):
    ...     try:
    ...         search_form = browser.getForm('globalsearch')
    ...     except LookupError:
    ...         search_form = browser.getForm(name='sitesearch')
    ...     search_text = search_form.getControl(name='field.text')
    ...     search_text.value = terms
    ...     search_form.submit()

The search form is available on almost every Launchpad page.

    >>> anon_browser.open('http://launchpad.test/ubuntu')
    >>> search_for('test1')
    >>> print(anon_browser.url)
    http://launchpad.test/+search?field.text=test1

But the search results page has its own search form, so the global one
is omitted.

    >>> global_search_form = anon_browser.getForm('globalsearch')
    Traceback (most recent call last):
    ...
    LookupError

If by chance someone ends up at /+search with no search parameters, they
get an explanation of the search function.

    >>> anon_browser.open('http://launchpad.test/+search')
    >>> print(anon_browser.title)
    Search Launchpad

    >>> print_search_results()

    >>> print(extract_text(
    ...     find_tag_by_id(anon_browser.contents, 'no-search')))
    Enter a term or many terms to find matching pages...

When the user searches for specific item, such as a project name, they
see a result for that exact match in Launchpad.

    >>> search_for('firefox')
    >>> print(anon_browser.title)
    Pages matching "firefox" in Launchpad

    >>> print_search_results()
    Exact matches
    Mozilla Firefox
    The Mozilla Firefox web browser
    Registered by Sample Person
    on 2004-09-24

Searching for an integer returns the matching bug number as well as the
matching question number, if one exists. Searching for "3", the user
sees that a bug matched.

    >>> search_for('3')
    >>> print(anon_browser.title)
    Pages matching "3" in Launchpad

    >>> print_search_results()
    Exact matches
    Bug #3: Bug Title Test
    ...
    3: Firefox is slow and consumes too much RAM
    ...

An arbitrary search returns a list of the search engine's search results.
The user searches for "bug" and sees a listing of matching pages. The
navigation states that the page is showing 1 through 20 of 25 total results.

    # Use our pre-defined search results for the 'bug' search.

    >>> search_for('bug')
    >>> print(anon_browser.title)
    Pages matching "bug" in Launchpad

    >>> print_search_results()
    1 → 20 of 25 pages matching "bug"...
    Launchpad Bugs...
    Bugs in Ubuntu...
    Bugs related to Sample Person...
    Bug #1 in Mozilla Firefox: ...Firefox does not support SVG...
    ...

They can see there really are only twenty matches in the page.

    >>> first_page_results = list(
    ...     find_tags_by_class(anon_browser.contents, 'pagematch'))
    >>> len(first_page_results)
    20

The user sees the 'Next' link, and uses it to view the next page. It has
5 page matches.

    >>> anon_browser.getLink('Next').click()
    >>> second_page_results = list(
    ...     find_tags_by_class(anon_browser.contents, 'pagematch'))
    >>> len(second_page_results)
    5

    >>> in_both = [match for match in second_page_results
    ...            if match in first_page_results]
    >>> in_both
    []

A search may return exact matches and matching pages. The batch
navigation text changes from "pages matching ..." to "other pages
matching ...".

    # Use our pre-defined search results for the 'launchpad' search.

    >>> search_for('launchpad')
    >>> print(anon_browser.title)
    Pages matching "launchpad" in Launchpad

    >>> print_search_results()
    Exact matches
    Launchpad
    Launchpad is a catalogue of libre software projects and products.
    ...
    Registered by Sample Person  on 2006-11-24
    Launchpad Developers (launchpad)
    Launchpad developers
    Created on 2005-10-13...
    1 → 20 of 25 other pages matching "launchpad"...
    Launchpad Bugs...


Specific searches
-----------------

Searches for specific launchpad items such as bugs, people, questions,
teams, or projects, will return their respective matching item.

The user searches for 'firefox' and sees the Mozilla Firefox product as
the most relevant match.

    >>> search_for('firefox')
    >>> print_search_results()
    Exact matches
    Mozilla Firefox
    The Mozilla Firefox web browser
    Registered by Sample Person
    on 2004-09-24

Project groups can appear too. For example, when the user searches for
'gnome', the GNOME project group is the best match.

    >>> search_for('gnome')
    >>> print_search_results()
    Exact matches
    GNOME
    The GNOME Project is an initiative to ...
    applications to work together in a harmonious desktop-ish way.
    Registered by Sample Person
    on 2004-09-24

Distributions also appear in the 'Exact matches' section. The user
searches for 'ubuntu' and sees it listed..

    >>> search_for('ubuntu')
    >>> print_search_results()
    Exact matches
    Ubuntu
    Ubuntu is a new approach to Linux Distribution that includes ...
    Registered
    by
    Registry Administrators
    on 2006-10-16

The user enters the number 1, and they see a bug and a question in the
"Exact matches" section.

    >>> search_for('1')
    >>> print_search_results()
    Exact matches
    Bug #1: Firefox does not support SVG
    in Mozilla Firefox, Ubuntu, Debian, reported on ...
    1: Firefox cannot render Bank Site
    posted on ... by Steve Alexander in Mozilla Firefox

The user searches for the rosetta admins team and it is listed.

    >>> search_for('rosetta admins')
    >>> print_search_results()
    Exact matches
    Rosetta Administrators (rosetta-admins)
    Rosetta Administrators
    Created on 2005-06-06

Search for a user's launchpad name, a user will find the user in the
"Exact matches" section.

    >>> search_for('mark')
    >>> print_search_results()
    Exact matches
    Mark Shuttleworth (mark)
    joined on 2005-06-06, with 130 karma

The exact matches section will contain information about Shipit when the
searches looks like the user is looking to get CDs sent from shipit.

    >>> search_for('ubuntu cds')
    >>> print_search_results()
    Exact matches
    Shipit Questions | ubuntu
    Ubuntu is available free of charge and we can send you a CD
    of the latest version with no extra cost, but the delivery
    may take up to ten weeks, so you should consider downloading
    the CD image if you have a fast Internet connection.

    >>> anon_browser.getLink('Shipit Questions | ubuntu').url
    'http://www.ubuntu.com/getubuntu/shipit-faq'


Searches with no results
------------------------

Searches that don't return any results display a explanation message to
the user. The text field is focused so that the user can try another
search.

    >>> search_for('fnord')
    >>> print(extract_text(
    ...     find_main_content(anon_browser.contents), skip_tags=[]))
    Pages matching "fnord" in Launchpad
    <!-- setFocusByName('field.text'); // -->
    Your search for “fnord” did not return any results.


Searches when there is no page service
--------------------------------------

The search provider may not be available when the search is performed.
This is often caused by temporary connectivity problems. A message is
displayed that explains that the search can be performed again to find
matching pages.

    >>> search_for('gnomebaker')
    >>> print(find_tag_by_id(anon_browser.contents, 'no-page-service'))
    <p id="no-page-service">
    The page search service was not available when this search was
    performed.
    <a href="http://launchpad.test/+search?field.text=gnomebaker">Search
    again</a> to see the matching pages.
    </p>


Searches for the empty string
-----------------------------

If the user submits the form without entering a term in the search
field, the page does not contain any results. The user can see that the
page is identical to the page visited without performing a search.

    >>> search_for('')
    >>> print(anon_browser.title)
    Search Launchpad

    >>> print_search_results()


Search limits
-------------

The Google Custom Search Engine restricts the search to 10 terms and
they cannot exceed 2048 characters. Testing revealed that 29 terms were
actually honored by Google. Phrases are not terms; each word in the
phrase was a term. Launchpad does not impose a restriction on the number
of terms since sending more terms does not represent an error. Launchpad
imposes an artificial limit to 250 characters.

The user cannot enter more than 250 characters to in the search field.

    >>> too_many_characters = '12345 7890' * 25 + 'n'
    >>> search_for(too_many_characters)
    >>> print_feedback_messages(anon_browser.contents)
    There is 1 error.
    The search text cannot exceed 250 characters.


Searching from any page
-----------------------

Most pages have the global search form in them. Any user can enter terms
in the page they are viewing and submit the form to see the results.

    >>> anon_browser.open('http://bugs.launchpad.test/firefox')
    >>> print(anon_browser.title)
    Bugs : Mozilla Firefox

    >>> print(anon_browser.url)
    http://bugs.launchpad.test/firefox

    >>> search_for('mozilla')
    >>> print(anon_browser.title)
    Pages matching "mozilla" in Launchpad

    >>> print(anon_browser.url)
    http://launchpad.test/+search?...

    >>> print_search_results()
    Exact matches
    The Mozilla Project
    The Mozilla Project is the largest open source web browser collaborati...
    browser technology.
    Registered by Sample Person
    on 2004-09-24


Searching for private data
--------------------------

When a search matches a private object those objects are only shown if
the logged in users has the permission to see it.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet, PersonVisibility
    >>> login('foo.bar@canonical.com')
    >>> salgado = getUtility(IPersonSet).getByName('salgado')
    >>> priv_team = factory.makeTeam(
    ...     owner=salgado, name="private-benjamin",
    ...     displayname="Private Benjamin",
    ...     visibility=PersonVisibility.PRIVATE)
    >>> logout()
    >>> browser = setupBrowser(auth='Basic salgado@ubuntu.com:test')
    >>> browser.open('http://launchpad.test/+search')
    >>> search_for('Private Benjamin', browser=browser)
    >>> print_search_results(browser.contents)
    Exact matches
    Private Benjamin
    (private-benjamin)
    ...

A user who is not in the private team will not see the team listed in
the results.

    >>> user_browser.open('http://launchpad.test/+search')
    >>> search_for('Private Benjamin', browser=user_browser)
    >>> print_search_results(user_browser.contents)


