Propose a branch for merging
============================

    >>> login(ANONYMOUS)
    >>> from lp.code.tests.helpers import make_erics_fooix_project
    >>> locals().update(make_erics_fooix_project(factory))
    >>> branch = factory.makeProductBranch(product=fooix)
    >>> url = canonical_url(branch)
    >>> logout()

The Propose for merging link should be there even if there is no logged in
user.

    >>> browser = setupBrowser()
    >>> browser.open(url)
    >>> browser.getLink('Propose for merging')
    <Link text='Propose for merging' ...

When proposing a branch for merging, the minimum that is needed is a target
branch.

    >>> browser = setupBrowser(auth='Basic fred@example.com:test')
    >>> browser.open(url)
    >>> browser.getLink('Propose for merging').click()

    >>> def print_radio_buttons(browser):
    ...     main = find_main_content(browser.contents)
    ...     for button in main.find_all('input', attrs={'type': 'radio'}):
    ...         try:
    ...             if button['checked']:
    ...                 checked = '(*)'
    ...             else:
    ...                 checked = '( )'
    ...         except KeyError:
    ...             checked = '( )'
    ...         print(checked, button['value'])

    >>> print_radio_buttons(browser)
    (*) ~eric/fooix/trunk
    ( ) other
    >>> browser.getControl('Propose Merge').click()
    >>> print_tag_with_id(browser.contents, 'proposal-summary')
    Status: Needs review
    Proposed branch: ...
    Merge into: lp://dev/fooix
    To merge this branch: bzr merge ...


Work in progress
----------------

Sometimes a proposal is wanted for the diff against the target, but the code
is not yet ready for review.  In these situations the user can uncheck the
needs review checkbox in the extra options.

    >>> login(ANONYMOUS)
    >>> branch = factory.makeProductBranch(product=fooix)
    >>> url = canonical_url(branch)
    >>> logout()

    >>> browser.open(url)
    >>> browser.getLink('Propose for merging').click()
    >>> browser.getControl('Needs review').click()
    >>> browser.getControl('Propose Merge').click()
    >>> print_tag_with_id(browser.contents, 'proposal-summary')
    Status: Work in progress
    Proposed branch: ...
    Merge into: lp://dev/fooix
    To merge this branch: bzr merge ...
