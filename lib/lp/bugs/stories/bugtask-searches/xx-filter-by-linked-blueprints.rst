Searching for bugs with linked blueprints
-----------------------------------------

Using the "advanced search" form, we can limit a bug task search to
bugs that are linked to blueprints or to bugs that are not linked to
any blueprints. Normally, both options are turned on.

    >>> advanced_search_url = (
    ...     'http://bugs.launchpad.test/firefox/+bugs?advanced=1')
    >>> anon_browser.open(advanced_search_url)
    >>> anon_browser.getControl(
    ...     'Show bugs with linked blueprints').selected
    True
    >>> anon_browser.getControl(
    ...     'Show bugs without linked blueprints').selected
    True

In this case all bugs are returned.

    >>> from lp.bugs.tests.bug import print_bugtasks
    >>> anon_browser.getControl('Search', index=1).click()
    >>> print_bugtasks(anon_browser.contents)
    5 Firefox install instructions should be complete
     Mozilla Firefox Critical New
    4 Reflow problems with complex page layouts
     Mozilla Firefox Medium New
    1 Firefox does not support SVG
     Mozilla Firefox Low New

When we uncheck 'Show bugs without linked blueprints', only bugs with
linked blueprints are returned.

    >>> anon_browser.open(advanced_search_url)
    >>> without_blueprints = anon_browser.getControl(
    ...     'Show bugs without linked blueprints')
    >>> without_blueprints.selected = False
    >>> anon_browser.getControl('Search', index=1).click()
    >>> print_bugtasks(anon_browser.contents)
    1 Firefox does not support SVG
     Mozilla Firefox Low New

Similary, we can search for blueprints that don't have linked
blueprints, if we uncheck 'Show bugs with linked blueprints'.

    >>> anon_browser.open(advanced_search_url)
    >>> with_blueprints = anon_browser.getControl(
    ...     'Show bugs with linked blueprints')
    >>> with_blueprints.selected = False
    >>> anon_browser.getControl('Search', index=1).click()
    >>> print_bugtasks(anon_browser.contents)
    5 Firefox install instructions should be complete
     Mozilla Firefox Critical New
    4 Reflow problems with complex page layouts
     Mozilla Firefox Medium New

If we uncheck both fields, all bugs are returned.

    >>> anon_browser.open(advanced_search_url)
    >>> with_blueprints = anon_browser.getControl(
    ...     'Show bugs with linked blueprints')
    >>> with_blueprints.selected = False
    >>> without_blueprints = anon_browser.getControl(
    ...     'Show bugs without linked blueprints')
    >>> without_blueprints.selected = False
    >>> anon_browser.getControl('Search', index=1).click()
    >>> print_bugtasks(anon_browser.contents)
    5 Firefox install instructions should be complete
     Mozilla Firefox Critical New
    4 Reflow problems with complex page layouts
     Mozilla Firefox Medium New
    1 Firefox does not support SVG
     Mozilla Firefox Low New
