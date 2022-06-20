Hide bug comments
=================

Comments that have had their visible attribute set to False
will not show up when browsing the comment list for a bug.
All comments are set visible by default.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/jokosher/+bug/11')
    >>> user_browser.getControl(name='field.comment').value = (
    ...     'This comment will not be visible when the test completes.')
    >>> user_browser.getControl('Post Comment', index=-1).click()
    >>> main_content = find_main_content(user_browser.contents)
    >>> new_comment = main_content('div', 'boardCommentBody')[-1]
    >>> new_comment_text = extract_text(new_comment.div)
    >>> print(new_comment_text)
    This comment will not be visible when the test completes.

Admin users can set a message's visible attribute to False.
In this case, the last message in the list, the one just added,
is now set to be hidden.

    >>> from zope.component import getUtility
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.bugmessage import IBugMessageSet
    >>> login('foo.bar@canonical.com')
    >>> bug_11 = getUtility(IBugSet).get(11)
    >>> message = bug_11.messages[-1]
    >>> print(message.text_contents)
    This comment will not be visible when the test completes.
    >>> bug_message = getUtility(IBugMessageSet).getByBugAndMessage(
    ...     bug_11, message)
    >>> bug_message.message.visible = False
    >>> transaction.commit()
    >>> logout()

For ordinary users, the newly created message no longer appears
in the list once visible has been set False.

    >>> test_browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> test_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/jokosher/+bug/11')
    >>> main_content = find_main_content(test_browser.contents)
    >>> last_comment = main_content('div', 'boardCommentBody')[-1]
    >>> last_comment_text = extract_text(last_comment.div)
    >>> print(last_comment_text)
    This title, however, is the same as the bug title and so it will
    be suppressed in the UI.

Ordinary users also cannot reach the message via direct link.

    >>> comments = find_tags_by_class(
    ...     test_browser.contents, 'boardComment')
    >>> for comment in comments:
    ...     number_node = comment.find(None, 'bug-comment-index')
    ...     latest_index = extract_text(number_node)
    >>> test_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/jokosher/+bug/11/comments/%d' % (int(latest_index[1:]) + 1))
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...

For admin users, the message is still visible in the bug page.

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/jokosher/+bug/11')
    >>> main_content = find_main_content(admin_browser.contents)
    >>> last_comment = main_content('div', 'boardCommentBody')[-1]
    >>> last_comment_text = extract_text(last_comment.div)
    >>> print(last_comment_text)
    This comment will not be visible when the test completes.

Admin users will see the hidden message highlighted with an
'adminHiddenComment' style.

    >>> print(' '.join(last_comment.parent['class']))
    boardComment editable-message adminHiddenComment

Admin users can also reach the message via direct link, and it is
highlighted with the 'adminHiddenComment style there too.

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/jokosher/+bug/11/comments/%d' % (int(latest_index[1:]) + 1))
    >>> contents = extract_text(admin_browser.contents)
    >>> print(contents)
    Comment #7 : Bug #11 ...
    This comment will not be visible when the test completes.
    ...
    >>> main_content = find_main_content(admin_browser.contents)
    >>> last_comment = main_content('div', 'boardCommentBody')[-1]
    >>> last_comment_text = extract_text(last_comment.div)
    >>> print(' '.join(last_comment.parent['class']))
    boardComment editable-message adminHiddenComment

Also for the owner of comment the message is still visible in the bug page.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/jokosher/+bug/11')
    >>> main_content = find_main_content(user_browser.contents)
    >>> last_comment = main_content('div', 'boardCommentBody')[-1]
    >>> last_comment_text = extract_text(last_comment.div)
    >>> print(last_comment_text)
    This comment will not be visible when the test completes.

Owner of the comment will see the hidden message highlighted with an
'adminHiddenComment' style.

    >>> print(' '.join(last_comment.parent['class']))
    boardComment editable-message adminHiddenComment

Owner of the comment can also reach the message via direct link, and it is
highlighted with the 'adminHiddenComment style there too.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/jokosher/+bug/11/comments/%d' % (int(latest_index[1:]) + 1))
    >>> contents = extract_text(user_browser.contents)
    >>> print(contents)
    Comment #7 : Bug #11 ...
    This comment will not be visible when the test completes.
    ...
    >>> main_content = find_main_content(user_browser.contents)
    >>> last_comment = main_content('div', 'boardCommentBody')[-1]
    >>> last_comment_text = extract_text(last_comment.div)
    >>> print(' '.join(last_comment.parent['class']))
    boardComment editable-message adminHiddenComment
