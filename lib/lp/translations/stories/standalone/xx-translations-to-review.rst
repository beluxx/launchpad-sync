Translations to Review
----------------------

When a translations reviewer visits their own homepage, it shows a list
of translations that they could or should be reviewing.

    >>> from zope.component import getUtility
    >>> from zope.security.proxy import removeSecurityProxy

    >>> from lp.services.beautifulsoup import BeautifulSoup
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> from lp.translations.interfaces.translator import ITranslatorSet

We'll be following this list as it applies to a new user, xowxz.

    >>> login(ANONYMOUS)

    >>> user = factory.makePerson(name='xowxz', email='xowxz@example.com')

Xowxz is a Khmer reviewer.

    >>> translationgroup = factory.makeTranslationGroup(
    ...     owner=factory.makePerson())
    >>> khmer = getUtility(ILanguageSet).getLanguageByCode('km')
    >>> entry = getUtility(ITranslatorSet).new(
    ...     translationgroup=translationgroup, language=khmer,
    ...     translator=user)

    >>> logout()

    >>> browser = setupBrowser(auth='Basic xowxz@example.com:test')
    >>> homepage = 'http://translations.launchpad.test/~xowxz'

    >>> def add_unreviewed_pofile(translationgroup):
    ...     """Create a POFile managed by `translationgroup`."""
    ...     pofile = removeSecurityProxy(
    ...         factory.makePOFile(language_code=khmer.code))
    ...     product = pofile.potemplate.productseries.product
    ...     product.translationgroup = translationgroup
    ...     pofile.unreviewed_count = 1
    ...     return pofile

    >>> def work_on(user, pofile):
    ...     """Let `user` add a suggestion to `pofile`."""
    ...     potmsgset = factory.makePOTMsgSet(
    ...         potemplate=pofile.potemplate, singular='x', sequence=1)
    ...     factory.makeCurrentTranslationMessage(
    ...         potmsgset=potmsgset, pofile=pofile, translator=user,
    ...         translations=['y'])

    >>> def list_reviewables(browser):
    ...     """List the table of reviewable translations seen in browser."""
    ...     soup = BeautifulSoup(browser.contents)
    ...     listing = soup.find(id="translations-to-review-table")
    ...     if listing:
    ...         count = 0
    ...         for tr in listing.find_all('tr'):
    ...             tds = [td.decode_contents() for td in tr.find_all('td')]
    ...             print('    '.join(tds))
    ...             count += 1
    ...         print("Listing contains %d translation(s)." % count)
    ...     else:
    ...         print("No listing found.")

    >>> def show_reviewables_link(browser):
    ...     """Show the "view all n unreviewed translations" link."""
    ...     soup = BeautifulSoup(browser.contents)
    ...     link = soup.find(id="translations-to-review-link")
    ...     if link:
    ...         print(link.decode_contents())
    ...     else:
    ...         print("No link.")

There are no translations for xowxz to review, so the listing does not
show up.

    >>> browser.open(homepage)
    >>> list_reviewables(browser)
    Listing contains 0 translation(s).

Now some POFiles managed by the xowxz's translation group receive
suggestions that xowxz could review.

    >>> login(ANONYMOUS)
    >>> pofile1 = add_unreviewed_pofile(translationgroup)
    >>> pofile2 = add_unreviewed_pofile(translationgroup)
    >>> logout()

These are translations that xowxz has not worked on.  They are not ones
that xowxz absolutely has to review.

    >>> show_reviewables_link(browser)
    No link.


Full listing
------------

If there are POFiles waiting for review that xowxz has worked on, a link
to the full list shows up.

    >>> login(ANONYMOUS)
    >>> work_on(user, pofile1)
    >>> work_on(user, pofile2)
    >>> logout()

    >>> browser.open(homepage)
    >>> show_reviewables_link(browser)
    See all 2 unreviewed translations

The link leads to a full listing of translations that xowxz seems to be
the appropriate reviewer for.

    >>> browser.getLink(id='translations-to-review-link').click()
    >>> list_reviewables(browser)
    <...
    Listing contains 2 translation(s).

Other translations that xowxz could review but hasn't worked on do not
show up in this full listing.

    >>> login(ANONYMOUS)
    >>> pofile3 = add_unreviewed_pofile(translationgroup)
    >>> logout()

    >>> browser.open(homepage)
    >>> show_reviewables_link(browser)
    See all 2 unreviewed translations

    >>> browser.getLink(id='translations-to-review-link').click()
    >>> list_reviewables(browser)
    <...
    Listing contains 2 translation(s).

Unlike the listing on the main page, the full listing does not cut off
at 10 entries.

    >>> login(ANONYMOUS)
    >>> for count in range(9):
    ...     pofile = add_unreviewed_pofile(translationgroup)
    ...     work_on(user, pofile)
    >>> logout()

    >>> browser.open(homepage)
    >>> list_reviewables(browser)
    <...
    Listing contains 9 translation(s).

    >>> show_reviewables_link(browser)
    See all 11 unreviewed translations

    >>> browser.getLink(id='translations-to-review-link').click()
    >>> list_reviewables(browser)
    <...
    Listing contains 11 translation(s).


Other users
-----------

Others do not see the listing on xowxz's personal translations page.

    >>> user_browser.open(homepage)
    >>> list_reviewables(user_browser)
    No listing found.
