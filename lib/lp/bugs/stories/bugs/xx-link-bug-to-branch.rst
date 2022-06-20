Linking a bug to a branch
=========================

The main page of a bug has a link to another page where users can
link a branch to a bug.

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/firefox/+bug/1")
    >>> user_browser.getLink('Link a related branch').click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/firefox/+bug/1/+addbranch
    >>> print(extract_text(find_tag_by_id(
    ...    user_browser.contents, 'maincontent')))
    Add a branch to bug #1...
    Linking a Bazaar branch to a bug allows you to notify others of
    work to fix this bug.
    ...

In the form of this page we can specify in a branch name that will be
linked to the bug.

    >>> branch_field = user_browser.getControl(name='field.branch')
    >>> branch_field.value = '~name12/firefox/main'
    >>> user_browser.getControl('Continue').click()

This takes us back to the main page where this branch is now listed as
a related branch.

    >>> print(user_browser.url)
    http://bugs.launchpad.test/firefox/+bug/1
    >>> print(extract_text(user_browser.contents))
    Bug #1...
    Successfully registered branch main for this bug.
    ...
    Related branches
    lp://dev/~name12/firefox/main
    ...

We can delete existing links between a bug and a branch.

    >>> delete_branch_link_url = (
    ...     'http://code.launchpad.test/~name12/firefox/main/+bug/1/+delete')
    >>> link = user_browser.getLink(url=delete_branch_link_url)
    >>> link.click()
    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents, 'maincontent')))
    Remove bug branch link...
    Are you sure you want to remove the link between Bug #1: Firefox does
    not support SVG and the branch lp://dev/~name12/firefox/main?
    ...

    >>> user_browser.getControl('Remove link').click()
