404 pages
=========

If you follow a link from another page to a Launchpad page that doesn't
exist, the 404 page includes a link back to the referring page.

(We can't test the 404 page using testbrowser, because it won't show us
the contents of any error page. So we use http() instead.)

    >>> page_with_referer = str(http(r"""
    ... GET /+fhqwhgads HTTP/1.1
    ... Referer: http://launchpad.test/+about
    ... """))
    >>> print(page_with_referer)
    HTTP/1.1 404 Not Found
    ...href="http://launchpad.test/+about"...

It also contains instructions specific to broken links.

    >>> main_content = find_main_content(page_with_referer)
    >>> for paragraph in main_content('p'):
    ...     print(extract_text(paragraph))
    This page does not exist, or you may not have permission to see it.
    If you have been to this page before, it is possible it has been removed.
    If you got here from a link elsewhere on Launchpad...
    Otherwise, complain to the maintainers of the page that linked here.
    If this is blocking your work...

If you go to a non-existent page directly, without sending a Referer:
header, the 404 page does not try to link to the referring page.
And the advice about broken links is gone, replaced with advice about
things like mistyped URLs.

    >>> page_with_no_referer = str(http(r"""
    ... GET /+fhqwhgads HTTP/1.1
    ... """))
    >>> print(page_with_no_referer)
    HTTP/1.1 404 Not Found
    ...
    >>> main_content = find_main_content(page_with_no_referer)
    >>> for paragraph in main_content('p'):
    ...     print(extract_text(paragraph))
    This page does not exist, or you may not have permission to see it.
    If you have been to this page before, it is possible it has been removed.
    Check that you are logged in with the correct account, or that you
    entered the address correctly, or search for it:
    ...
