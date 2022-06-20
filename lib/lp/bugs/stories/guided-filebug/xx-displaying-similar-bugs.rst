Displaying Similar Bugs
=======================

Up to 10 similar bugs can be displayed during the guided bug filing
process. For each similar bug found, a relevant bugtask is selected
and used to enrich the presentation and information displayed to the
user, hopefully helping them choose accurately and thus reducing
duplicates.

    >>> def print_similar_bugs(content):
    ...     bugs_list = find_tags_by_class(content, 'similar-bug')
    ...     for node in bugs_list:
    ...         label = node.find_all('label')[0]
    ...         label_class = ' '.join(label['class'])
    ...         text_lines = [line.strip() for line in
    ...                       extract_text(node).splitlines()]
    ...         summary = ' '.join(text_lines[:2]).replace(u'\u200B', u'')
    ...         status = ' '.join(text_lines[2:])
    ...         # All this trouble is worth it when you see ndiff output
    ...         # from a failing test, and it *makes sense* :)
    ...         print('(icon class=%s)\n  %s\n  %s' % (
    ...             label_class, summary, status))


Products
--------

If a user tries to file a bug against a product, and does not go down
the advanced bug filing route, they're shown a list of bugs similar to
the summary entered (assuming some are found).

    >>> user_browser.open("http://bugs.launchpad.test/firefox/+filebug")
    >>> user_browser.getControl("Summary", index=0).value = 'a'
    >>> user_browser.getControl("Continue").click()

All of the similar bugs have relevant bugtasks:

    >>> print_similar_bugs(user_browser.contents)
    (icon class=sprite bug-low)
      #1 Firefox does not support SVG
      New (1 comment) last updated 2006-05-19...
      Firefox needs to support embedded SVG...
    (icon class=sprite bug-medium)
      #4 Reflow problems with complex page layouts
      New (0 comments) last updated 2006-07-14...
      Malone pages that use more complex layouts...
    (icon class=sprite bug-critical)
      #5 Firefox install instructions should be complete
      New (0 comments) last updated 2006-07-14...
      All ways of downloading firefox should provide complete...

However, what if a relevant bugtask can't be found? This is unlikely,
but possible, because a similar bug might actually be a duplicate of a
bug that has no bugtask for the product.

When a similar bug is found that is also a duplicate bug, we display
the duplicated bug instead. If the duplicated bug has no bugtask
relating to the context we're trying to file a bug against (here, a
product), we just show basic non-bugtask information.

Specifically, we do not have a status or importance, so we only show
the generic bug icon and 'Open' or 'Closed' instead of 'New',
'Confirmed', etc.

We shall make bug 4 a duplicate of bug 8, which has no bugtask for
firefox.

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/firefox/+bug/4/+duplicate")
    >>> user_browser.getControl('Duplicate Of').value = '8'
    >>> user_browser.getControl('Set Duplicate').click()

Then, if we match bug 1, only basic details of bug 8 are displayed:

    >>> user_browser.open("http://bugs.launchpad.test/firefox/+filebug")
    >>> user_browser.getControl("Summary", index=0).value = 'reflow'
    >>> user_browser.getControl("Continue").click()

    >>> print_similar_bugs(user_browser.contents)
    (icon class=sprite bug)
      #8 Printing doesn't work
      Closed (0 comments) last updated 2006-05-19...
      When I press print in Firefox...

To help the user verify if a bug is indeed simliar to the problem
being reported, the user's original summary is displayed above
the list of potentially similar bugs.

    >>> query = find_tag_by_id(user_browser.contents, 'filebug-query-heading')
    >>> print(extract_text(query))
    Is "reflow" one of these bugs?


Distributions
-------------

If similar bugs are found they're displayed so that the user might
find that their bug has already been reported.

    >>> user_browser.open("http://launchpad.test/ubuntu/+filebug")
    >>> user_browser.getControl("Summary", index=0).value = 'crashes'
    >>> user_browser.getControl("Continue").click()

    >>> print_similar_bugs(user_browser.contents)
    (icon class=sprite bug-medium)
      #9 Thunderbird crashes
      Confirmed (0 comments) last updated 2006-07-14...
      Every time I start Thunderbird...

Only basic details are shown when no relevant bugtask exists:

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/ubuntu/+source/"
    ...     "thunderbird/+bug/9/+duplicate")
    >>> user_browser.getControl('Duplicate Of').value = '8'
    >>> user_browser.getControl('Set Duplicate').click()

    >>> user_browser.open("http://launchpad.test/ubuntu/+filebug")
    >>> user_browser.getControl("Summary", index=0).value = 'crashes'
    >>> user_browser.getControl("Continue").click()

    >>> print_similar_bugs(user_browser.contents)
    (icon class=sprite bug)
      #8 Printing doesn't work
      Closed (0 comments) last updated 2006-05-19...
      When I press print in Firefox...


Distribution Source Packages
----------------------------

In common with all the other guided bug filing processes, we display a
list of similar bugs when a user tries to file a bug against a source
package.

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/+source/"
    ...     "mozilla-firefox/+filebug")
    >>> user_browser.getControl("Summary", index=0).value = 'a'
    >>> user_browser.getControl("Continue").click()

    >>> print_similar_bugs(user_browser.contents)
    (icon class=sprite bug-medium)
      #1 Firefox does not support SVG
      New (1 comment) last updated 2006-05-19...
      Firefox needs to support embedded SVG...

Only basic details are shown when no relevant bugtask exists:

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/firefox/+bug/1/+duplicate")
    >>> user_browser.getControl('Duplicate Of').value = '8'
    >>> user_browser.getControl('Set Duplicate').click()

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/+source/"
    ...     "mozilla-firefox/+filebug")
    >>> user_browser.getControl("Summary", index=0).value = 'a'
    >>> user_browser.getControl("Continue").click()

    >>> print_similar_bugs(user_browser.contents)
    (icon class=sprite bug)
      #8 Printing doesn't work
      Closed (0 comments) last updated 2006-05-19...
      When I press print in Firefox...
