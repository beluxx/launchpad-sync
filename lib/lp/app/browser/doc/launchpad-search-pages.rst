Launchpad search page
=====================

Users can search for Launchpad objects and pages from the search form
located on all pages. The search is performed and displayed by the
LaunchpadSearchView.

    >>> from zope.component import getMultiAdapter, getUtility
    >>> from lp.services.webapp.interfaces import ILaunchpadRoot
    >>> from lp.services.webapp.servers import LaunchpadTestRequest

    >>> root = getUtility(ILaunchpadRoot)
    >>> request = LaunchpadTestRequest()
    >>> search_view = getMultiAdapter((root, request), name="+search")
    >>> search_view.initialize()
    >>> search_view
    <....SimpleViewClass from .../templates/launchpad-search.pt ...>


Page title and heading
----------------------

The page title and heading suggest to the user to search launchpad
when there is no search text.

    >>> print(search_view.text)
    None
    >>> search_view.page_title
    'Search Launchpad'
    >>> search_view.page_heading
    'Search Launchpad'

When text is not None, the title indicates what was searched.

    >>> from lp.services.encoding import wsgi_native_string

    >>> def getSearchView(form):
    ...     search_param_list = []
    ...     for name in sorted(form):
    ...         value = form[name]
    ...         search_param_list.append(
    ...             wsgi_native_string(name)
    ...             + wsgi_native_string("=")
    ...             + wsgi_native_string(value)
    ...         )
    ...     query_string = wsgi_native_string("&").join(search_param_list)
    ...     request = LaunchpadTestRequest(
    ...         SERVER_URL="https://launchpad.test/+search",
    ...         QUERY_STRING=query_string,
    ...         form=form,
    ...         PATH_INFO="/+search",
    ...     )
    ...     search_view = getMultiAdapter((root, request), name="+search")
    ...     search_view.initialize()
    ...     return search_view
    ...

    >>> search_view = getSearchView(form={"field.text": "albatross"})

    >>> print(search_view.text)
    albatross
    >>> print(search_view.page_title)
    Pages matching "albatross" in Launchpad
    >>> print(search_view.page_heading)
    Pages matching "albatross" in Launchpad


No matches
----------

There were no matches for 'albatross'.

    >>> search_view.has_matches
    False

When search text is not submitted there are no matches. Search text is
required to perform a search. Note that field.actions.search is not a
required param to call the Search Action. The view always calls the
search action.

    >>> search_view = getSearchView(form={})

    >>> print(search_view.text)
    None
    >>> search_view.has_matches
    False


Bug and Question Searches
-------------------------

When a numeric token can be extracted from the submitted search text,
the view tries to match a bug and question. Bugs and questions are
matched by their id.

    >>> search_view = getSearchView(form={"field.text": "5"})
    >>> print(search_view._getNumericToken(search_view.text))
    5
    >>> search_view.has_matches
    True
    >>> print(search_view.bug.title)
    Firefox install instructions should be complete
    >>> print(search_view.question.title)
    Installation failed

Bugs and questions are matched independent of each other. The number
extracted may only match one kind of object. For example, there are
more bugs than questions.

    >>> search_view = getSearchView(form={"field.text": "15"})
    >>> print(search_view._getNumericToken(search_view.text))
    15
    >>> search_view.has_matches
    True
    >>> print(search_view.bug.title)
    Nonsensical bugs are useless
    >>> print(search_view.question)
    None

Private bugs are not matched if the user does not have permission to
see them. For example, Sample Person can see a private bug that they
created because they are the owner.

    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.app.enums import InformationType

    >>> login("test@canonical.com")
    >>> sample_person = getUtility(ILaunchBag).user
    >>> private_bug = factory.makeBug(
    ...     owner=sample_person, information_type=InformationType.USERDATA
    ... )

    >>> search_view = getSearchView(form={"field.text": str(private_bug.id)})
    >>> search_view.bug.private
    True

But anonymous and unprivileged users cannot see the private bug.

    >>> login(ANONYMOUS)
    >>> search_view = getSearchView(form={"field.text": str(private_bug.id)})
    >>> print(search_view.bug)
    None

The text and punctuation in the search text is ignored, and only the
first group of numbers is matched. For example a user searches for three
questions by number ('Question #15, #7, and 5.'). Only the first number
is used, and it matches a bug, not a question. The second and third
numbers do match questions, but they are not used.

    >>> search_view = getSearchView(
    ...     form={"field.text": "Question #15, #7, and 5."}
    ... )
    >>> print(search_view._getNumericToken(search_view.text))
    15
    >>> search_view.has_matches
    True
    >>> print(search_view.bug.title)
    Nonsensical bugs are useless
    >>> print(search_view.question)
    None

It is not an error to search for a non-existent bug or question.

    >>> search_view = getSearchView(form={"field.text": "55555"})
    >>> print(search_view._getNumericToken(search_view.text))
    55555
    >>> search_view.has_matches
    False
    >>> print(search_view.bug)
    None
    >>> print(search_view.question)
    None

There is no error if a number cannot be extracted from the search text.

    >>> search_view = getSearchView(form={"field.text": "fifteen"})
    >>> print(search_view._getNumericToken(search_view.text))
    None
    >>> search_view.has_matches
    False
    >>> print(search_view.bug)
    None
    >>> print(search_view.question)
    None

Bugs and questions are only returned for the first page of search,
when the start param is 0.

    >>> search_view = getSearchView(form={"field.text": "5", "start": "20"})
    >>> search_view.has_matches
    False
    >>> print(search_view.bug)
    None
    >>> print(search_view.question)
    None



Projects and Persons and Teams searches
---------------------------------------

When a Launchpad name can be made from the search text, the view tries
to match the name to a pillar or person. a pillar is a distribution,
product, or project group. A person is a person or a team.

    >>> search_view = getSearchView(form={"field.text": "launchpad"})
    >>> print(search_view._getNameToken(search_view.text))
    launchpad
    >>> search_view.has_matches
    True
    >>> print(search_view.pillar.displayname)
    Launchpad
    >>> print(search_view.person_or_team.displayname)
    Launchpad Developers

A launchpad name is constructed from the search text. The letters are
converted to lowercase. groups of spaces and punctuation are replaced
with a hyphen.

    >>> search_view = getSearchView(form={"field.text": "Gnome Terminal"})
    >>> print(search_view._getNameToken(search_view.text))
    gnome-terminal
    >>> search_view.has_matches
    True
    >>> print(search_view.pillar.displayname)
    GNOME Terminal
    >>> print(search_view.person_or_team)
    None

Since our pillars can have aliases, it's also possible to look up a pillar
by any of its aliases.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet)["firefox"]
    >>> login("foo.bar@canonical.com")
    >>> firefox.setAliases(["iceweasel"])
    >>> login(ANONYMOUS)
    >>> search_view = getSearchView(form={"field.text": "iceweasel"})
    >>> print(search_view._getNameToken(search_view.text))
    iceweasel
    >>> search_view.has_matches
    True
    >>> print(search_view.pillar.displayname)
    Mozilla Firefox

This is a harder example that illustrates that text that is clearly not
the name of a pillar will none-the-less be tried. See the `Page searches`
section for how this kind of search can return matches.

    >>> search_view = getSearchView(
    ...     form={"field.text": "YAHOO! webservice's Python API."}
    ... )
    >>> print(search_view._getNameToken(search_view.text))
    yahoo-webservices-python-api.
    >>> search_view.has_matches
    False
    >>> print(search_view.pillar)
    None
    >>> print(search_view.person_or_team)
    None

Leading and trailing punctuation and whitespace are stripped.

    >>> search_view = getSearchView(form={"field.text": "~name12"})
    >>> print(search_view._getNameToken(search_view.text))
    name12
    >>> search_view.has_matches
    True
    >>> print(search_view.pillar)
    None
    >>> print(search_view.person_or_team.displayname)
    Sample Person

Pillars, persons and teams are only returned for the first page of
search, when the start param is 0.

    >>> search_view = getSearchView(
    ...     form={"field.text": "launchpad", "start": "20"}
    ... )
    >>> search_view.has_matches
    True
    >>> print(search_view.bug)
    None
    >>> print(search_view.question)
    None
    >>> print(search_view.pillar)
    None

Deactivated pillars and non-valid persons and teams cannot be exact
matches. For example, the python-gnome2-dev product will not match a
pillar, nor will nsv match Nicolas Velin's unclaimed account.

    >>> from lp.registry.interfaces.person import IPersonSet

    >>> python_gnome2 = getUtility(IProductSet).getByName("python-gnome2-dev")
    >>> python_gnome2.active
    False

    >>> search_view = getSearchView(
    ...     form={"field.text": "python-gnome2-dev", "start": "0"}
    ... )
    >>> print(search_view._getNameToken(search_view.text))
    python-gnome2-dev
    >>> print(search_view.pillar)
    None

    >>> nsv = getUtility(IPersonSet).getByName("nsv")
    >>> print(nsv.displayname)
    Nicolas Velin
    >>> nsv.is_valid_person_or_team
    False

    >>> search_view = getSearchView(form={"field.text": "nsv", "start": "0"})
    >>> print(search_view._getNameToken(search_view.text))
    nsv
    >>> print(search_view.person_or_team)
    None

Private pillars are not matched if the user does not have permission to see
them. For example, Sample Person can see a private project that they created
because they are the owner.

    >>> from lp.registry.interfaces.product import License

    >>> login("test@canonical.com")
    >>> private_product = factory.makeProduct(
    ...     owner=sample_person,
    ...     information_type=InformationType.PROPRIETARY,
    ...     licenses=[License.OTHER_PROPRIETARY],
    ... )
    >>> private_product_name = private_product.name

    >>> search_view = getSearchView(form={"field.text": private_product_name})
    >>> search_view.pillar.private
    True

But anonymous and unprivileged users cannot see the private project.

    >>> login(ANONYMOUS)
    >>> search_view = getSearchView(form={"field.text": private_product_name})
    >>> print(search_view.pillar)
    None


Shipit CD searches
------------------

The has_shipit property will be True when the search looks like the user
is searching for Shipit CDs. There is no correct object in Launchpad to
display. The page template decides how to handle when has_shipit is
True.

The match is based on an intersection to the words in the search text
and the shipit_keywords. The comparison is case-insensitive, has_shipit
is True when 2 or more words match.

    >>> sorted(search_view.shipit_keywords)
    ['cd', 'cds', 'disc', 'dvd', 'dvds', 'edubuntu', 'free', 'get', 'kubuntu',
     'mail', 'send', 'ship', 'shipit', 'ubuntu']
    >>> search_view = getSearchView(
    ...     form={"field.text": "ubuntu CDs", "start": "0"}
    ... )
    >>> search_view.has_shipit
    True

    >>> search_view = getSearchView(
    ...     form={"field.text": "shipit", "start": "0"}
    ... )
    >>> search_view.has_shipit
    False

    >>> search_view = getSearchView(
    ...     form={"field.text": "get Kubuntu cds", "start": "0"}
    ... )
    >>> search_view.has_shipit
    True

There are shipit_anti_keywords too, words that indicate the search is
not for free CDs from Shipit. Search that have any of these word will
set has_shipit to False.

    >>> sorted(search_view.shipit_anti_keywords)
    ['burn', 'burning', 'enable', 'error', 'errors', 'image', 'iso',
     'read', 'rip', 'write']

    >>> search_view = getSearchView(
    ...     form={"field.text": "ubuntu CD write", "start": "0"}
    ... )
    >>> search_view.has_shipit
    False

    >>> search_view = getSearchView(
    ...     form={"field.text": "shipit error", "start": "0"}
    ... )
    >>> search_view.has_shipit
    False


The shipit FAQ URL is provides by the view for the template to use.

    >>> search_view.shipit_faq_url
    'http://www.ubuntu.com/getubuntu/shipit-faq'


Page searches
-------------

The view uses the Search Service to locate pages that match the
search terms.

    >>> search_view = getSearchView(form={"field.text": " bug"})
    >>> print(search_view.text)
    bug
    >>> search_view.has_matches
    True
    >>> search_view.pages
    <...SiteSearchBatchNavigator ...>

The Search Service may not be available due to connectivity problems.
The view's has_page_service attribute reports when the search was performed
with the Search Service page matches.

    >>> search_view.has_page_service
    True

The batch navigation heading is created by the view. The heading
property returns a 2-tuple of singular and plural heading. There
is a heading when there are only Search Service page matches...

    >>> search_view.has_exact_matches
    False
    >>> for heading in search_view.batch_heading:
    ...     print(heading)
    ...
    page matching "bug"
    pages matching "bug"

...and a heading for when there are exact matches and Search Service page
matches.

    >>> search_view = getSearchView(form={"field.text": " launchpad"})
    >>> search_view.has_exact_matches
    True
    >>> for heading in search_view.batch_heading:
    ...     print(heading)
    ...
    other page matching "launchpad"
    other pages matching "launchpad"

The SiteSearchBatchNavigator behaves like most BatchNavigators, except that
its batch size is always 20. The size restriction conforms to Google's
maximum number of results that can be returned per request.

    >>> search_view.start
    0
    >>> search_view.pages.currentBatch().size
    20
    >>> pages = list(search_view.pages.currentBatch())
    >>> len(pages)
    20
    >>> for page in pages[0:5]:
    ...     print("'%s'" % page.title)
    'Launchpad Bugs'
    'Bugs in Ubuntu Linux'
    'Bugs related to Sample Person'
    '...Bug... #1 in Mozilla Firefox: ...Firefox does not support SVG...'
    'Bugs in Source Package ...thunderbird... in Ubuntu Linux'

The batch navigator provides access to the other batches. There are two
batches of pages that match the search text 'bugs'. The navigator
provides a link to the next batch, which also happens to be the last
batch.

    >>> search_view.pages.nextBatchURL()
    '...start=20'
    >>> search_view.pages.lastBatchURL()
    '...start=20'

The second batch has only five matches in it, even though the batch size
is 20. That is because there were only 25 matching pages.

    >>> search_view = getSearchView(form={"field.text": "bug", "start": "20"})
    >>> search_view.start
    20
    >>> print(search_view.text)
    bug
    >>> search_view.has_matches
    True

    >>> search_view.pages.currentBatch().size
    20
    >>> pages = list(search_view.pages.currentBatch())
    >>> len(pages)
    5
    >>> for page in pages:
    ...     print("'%s'" % page.title)
    ...
    '...Bug... #2 in Ubuntu Hoary: “Blackhole Trash folder”'
    '...Bug... #2 in mozilla-firefox (Debian): ...Blackhole Trash folder...'
    '...Bug... #3 in mozilla-firefox (Debian): “Bug Title Test”'
    '...Bug... trackers registered in Launchpad'
    '...Bug... tracker “Debian Bug tracker”'

    >>> search_view.pages.nextBatchURL()
    ''
    >>> search_view.pages.lastBatchURL()
    ''

The PageMatch object has a title, url, and summary. The title and url
are used for making links to the pages. The summary contains markup
showing the matching terms in context of the page text.

    >>> page = pages[0]
    >>> page
    <...PageMatch ...>
    >>> print("'%s'" % page.title)
    '...Bug... #2 in Ubuntu Hoary: “Blackhole Trash folder”'
    >>> page.url
    'http://bugs.launchpad.test/ubuntu/hoary/+bug/2'
    >>> print("'%s'" % page.summary)
    '...Launchpad’s ...bug... tracker allows collaboration...'


No page matches
---------------

When an empty PageMatches object is returned by the Search Service to
the view, there are no matches to show.

    >>> search_view = getSearchView(form={"field.text": "no-meaningful"})
    >>> search_view.has_matches
    False


Unintelligible searches
-----------------------

When a user searches for a malformed string, we don't OOPS, but show an
error. Also disable warnings, since we are tossing around malformed Unicode.

    >>> import warnings
    >>> with warnings.catch_warnings():
    ...     warnings.simplefilter("ignore")
    ...     search_view = getSearchView(
    ...         form={"field.text": b"\xfe\xfckr\xfc"}
    ...     )
    ...
    >>> html = search_view()
    >>> "Can not convert your search term" in html
    True


Bad site search response handling
----------------------------

Connectivity problems can cause missing or incomplete responses from
the site search engine. The LaunchpadSearchView will display the other
searches and show a message explaining that the user can search again to
find matching pages.

    >>> search_view = getSearchView(form={"field.text": "gnomebaker"})
    >>> search_view.has_matches
    True
    >>> print(search_view.pillar.displayname)
    gnomebaker
    >>> search_view.has_page_service
    False

The view provides the requested URL so that the template can make a
link to try the search again

    >>> print(search_view.url)
    https://launchpad.test/+search?field.text=gnomebaker


SearchFormView and SearchFormPrimaryView
----------------------------------------

Two companion views are used to help render the global search form.
They define the required attributes to render the form in the
correct state.

The LaunchpadSearchFormView provides the minimum information to display
the form, but cannot handled the submitted data. It appends a suffix
('-secondary') to the id= and name= of the form and inputs, to prevent
them from conflicting with the other form. The search text is not the
default value of the text field; 'bug' was submitted above, but is not
present in the rendered form.

    >>> search_form_view = getMultiAdapter(
    ...     (search_view, request), name="+search-form"
    ... )
    >>> search_form_view.initialize()
    >>> search_form_view.id_suffix
    '-secondary'
    >>> print(search_form_view.render())
    <form action="http://launchpad.test/+search" method="get"
      accept-charset="UTF-8" id="sitesearch-secondary"
      name="sitesearch-secondary">
      <div>
        <input class="textType" type="text" size="36"
          id="field.text-secondary" name="field.text" />
        <input class="button" type="submit" value="Search"
          id="field.text-secondary" name="field.actions.search-secondary" />
      </div>
    </form>

LaunchpadPrimarySearchFormView can handle submitted form by deferring to
its context (the LaunchpadSearchView) for the needed information. The
view does not append a suffix to the form and input ids. The search
field's value is 'bug', as was submitted above.

    >>> search_form_view = getMultiAdapter(
    ...     (search_view, request), name="+primary-search-form"
    ... )
    >>> search_form_view.initialize()
    >>> search_form_view.id_suffix
    ''
    >>> print(search_form_view.render())
    <form action="http://launchpad.test/+search" method="get"
      accept-charset="UTF-8" id="sitesearch"
      name="sitesearch">
      <div>
        <input class="textType" type="text" size="36"
          id="field.text" value="gnomebaker" name="field.text" />
        <input class="button" type="submit" value="Search"
          id="field.text" name="field.actions.search" />
      </div>
    </form>

WindowedList and SiteSearchBatchNavigator
-------------------------------------

The LaunchpadSearchView uses two helper classes to work with
PageMatches.

The PageMatches object returned by the Search Service contains 20
or fewer PageMatches of what could be thousands of matches. Google
requires client's to make repeats request to step though the batches of
matches. The Windowed list is a list that contains only a subset of its
reported size. It is used to make batches in the SiteSearchBatchNavigator.

For example, the last batch of the 'bug' search contained 5 of the 25
matching pages. The WindowList claims to be 25 items in length, but
the first 20 items are None. Only the last 5 items are PageMatches.

    >>> from lp.app.browser.root import WindowedList
    >>> from lp.services.sitesearch.interfaces import active_search_service
    >>> from zope.security.proxy import removeSecurityProxy

    >>> site_search = active_search_service()
    >>> naked_site_search = removeSecurityProxy(site_search)
    >>> page_matches = naked_site_search.search(terms="bug", start=20)
    >>> results = WindowedList(
    ...     page_matches, page_matches.start, page_matches.total
    ... )
    >>> len(results)
    25
    >>> print(results[0])
    None
    >>> print("'%s'" % results[24].title)
    '...Bug... tracker “Debian Bug tracker”'
    >>> results[18, 22]
    [None, None, <...PageMatch ...>, <...PageMatch ...>]

The SiteSearchBatchNavigator restricts the batch size to 20. the 'batch'
parameter that comes from the URL is ignored. For example, setting
the 'batch' parameter to 100 has no affect upon the site search
or on the navigator object.

    >>> from lp.app.browser.root import SiteSearchBatchNavigator

    >>> SiteSearchBatchNavigator.batch_variable_name
    'batch'

    >>> search_view = getSearchView(
    ...     form={
    ...         "field.text": "bug",
    ...         "start": "0",
    ...         "batch": "100",
    ...     }
    ... )

    >>> navigator = search_view.pages
    >>> navigator.currentBatch().size
    20
    >>> len(navigator.currentBatch())
    20
    >>> navigator.nextBatchURL()
    '...start=20'

Even if the PageMatch object to have an impossibly large size, the
navigator conforms to Google's maximum size of 20.

    >>> matches = list(range(0, 100))
    >>> page_matches._matches = matches
    >>> page_matches.start = 0
    >>> page_matches.total = 100
    >>> navigator = SiteSearchBatchNavigator(
    ...     page_matches, search_view.request, page_matches.start, size=100
    ... )
    >>> navigator.currentBatch().size
    20
    >>> len(navigator.currentBatch())
    20
    >>> navigator.nextBatchURL()
    '...start=20'

The PageMatches object can be smaller than 20, for instance, pages
without titles are skipped when parsing the search engine response. The size
of the batch is still 20, but when the items in the batch are iterated,
the true size can be seen. For example there could be only 3 matches in
the PageMatches object, so only 3 are yielded. The start of the next
batch is 20, which is the start of the next batch from Google.

    >>> matches = list(range(0, 3))
    >>> page_matches._matches = matches
    >>> navigator = SiteSearchBatchNavigator(
    ...     page_matches, search_view.request, page_matches.start, size=100
    ... )
    >>> batch = navigator.currentBatch()
    >>> batch.size
    20
    >>> len(batch)
    20
    >>> batch.endNumber()
    3
    >>> for item in batch:
    ...     print(item)
    ...
    0
    1
    2
    >>> navigator.nextBatchURL()
    '...start=20'
