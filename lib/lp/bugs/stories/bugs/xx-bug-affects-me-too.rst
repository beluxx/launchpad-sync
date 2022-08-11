Marking a bug as affecting the user
===================================

Users can mark bugs as affecting them. Let's create a sample bug to
try this out.

    >>> login(ANONYMOUS)
    >>> from lp.services.webapp import canonical_url
    >>> test_bug = factory.makeBug()
    >>> test_bug_url = canonical_url(test_bug)
    >>> logout()

The user goes to the bug's index page, and finds a statement that the
bug affects one other person (in this instance, the person who filed
the bug).

    >>> user_browser.open(test_bug_url)
    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents, 'affectsmetoo').find(
    ...         None, 'static')))
    This bug affects 1 person. Does this bug affect you?

Next to the statement is a link containing an edit icon.

    >>> edit_link = find_tag_by_id(
    ...     user_browser.contents, 'affectsmetoo').a
    >>> print(edit_link['href'])
    +affectsmetoo
    >>> print(edit_link.img['src'])
    /@@/edit

The user is affected by this bug, so clicks the link.

    >>> user_browser.getLink(url='+affectsmetoo').click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/.../+bug/.../+affectsmetoo
    >>> user_browser.getControl(name='field.affects').value
    ['YES']

The form defaults to 'Yes', and the user submits the form.

    >>> user_browser.getControl('Change').click()

The bug page loads again, and now the text is changed, to make it
clear to the user that they have marked this bug as affecting them.

    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents, 'affectsmetoo').find(
    ...         None, 'static')))
    This bug affects you and 1 other person

On second thoughts, the user realises that this bug does not affect
them, so they click on the edit link once more.

    >>> user_browser.getLink(url='+affectsmetoo').click()

The user changes their selection to 'No' and submits the form.

    >>> user_browser.getControl(name='field.affects').value = ['NO']
    >>> user_browser.getControl('Change').click()

Back at the bug page, the text changes once again.

    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents, 'affectsmetoo').find(
    ...         None, 'static')))
    This bug affects 1 person, but not you


Anonymous users
---------------

Anonymous users just see the number of affected users.

    >>> anon_browser.open(test_bug_url)
    >>> print(extract_text(find_tag_by_id(
    ...     anon_browser.contents, 'affectsmetoo')))
    This bug affects 1 person

If no one is marked as affected by the bug, the message does not
appear at all to anonymous users.

    >>> login('test@canonical.com')
    >>> test_bug.markUserAffected(test_bug.owner, False)
    >>> logout()

    >>> anon_browser.open(test_bug_url)
    >>> print(find_tag_by_id(anon_browser.contents, 'affectsmetoo'))
    None


Static and dynamic support
--------------------------

A bug page contains markup to support both static (no Javascript) and
dynamic (Javascript enabled) scenarios.

    >>> def class_filter(css_class):
    ...     def test(node):
    ...         return css_class in node.get('class', [])
    ...     return test

    >>> static_content = find_tag_by_id(
    ...     user_browser.contents, 'affectsmetoo').find(
    ...         class_filter('static'))

    >>> static_content is not None
    True

    >>> dynamic_content = find_tag_by_id(
    ...     user_browser.contents, 'affectsmetoo').find(
    ...         class_filter('dynamic'))

    >>> dynamic_content is not None
    True

The dynamic content is hidden by the presence of the "hidden" CSS
class.

    >>> print(' '.join(static_content.get('class')))
    static

    >>> print(' '.join(dynamic_content.get('class')))
    dynamic hidden

It is the responsibility of Javascript running in the page to unhide
the dynamic content and hide the static content.
