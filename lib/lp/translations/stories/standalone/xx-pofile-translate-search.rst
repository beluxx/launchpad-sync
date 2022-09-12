Searching through PO files
==========================

While doing translations, one can also search for messages containing
a certain substring (whether in original English string or in
a translation).

No Privileges Person visits the evolution-2.2 package in Ubuntu Hoary
can see the search box on the translate page:

    >>> user_browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/"
    ...     "+source/evolution/+pots/evolution-2.2/es/+translate"
    ... )
    >>> user_browser.getControl("Search", index=0).value = "contact"
    >>> user_browser.getForm(id="search_form").submit()
    >>> user_browser.url
    'http://.../evolution-2.2/es/+translate?batch=10&show=all&search=contact'

All 4 results are still shown.

    >>> print_batch_header(find_main_content(user_browser.contents))
    1 ... 4  of 4 results

Searching for a single-letter string fails.

    >>> user_browser.getControl("Search", index=0).value = "a"
    >>> user_browser.getForm(id="search_form").submit()
    >>> user_browser.url
    'http://.../evolution-2.2/es/+translate?batch=10&show=all&search=a'

A warning is displayed.

    >>> tags = find_tags_by_class(user_browser.contents, "warning message")
    >>> print(extract_text(tags[0]))
    Please try searching for a longer string.

And no filtering is applied: all messages are shown.

    >>> print_batch_header(find_main_content(user_browser.contents))
    1 ... 10  of 22 results
