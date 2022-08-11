Bugs with lots of comments
==========================

When a bug has a very large number of comments, only some of them are
displayed. A notice is added at the end of the comment list to tell
the user about this.

Bug 11 has quite a few comments. Note that the "Add comment" text area also
has the comment-text CSS class, increasing all the find_tags_by_class counts
below by one.

    >>> user_browser.open('http://launchpad.test/bugs/11')
    >>> comments = find_tags_by_class(user_browser.contents, 'comment-text')
    >>> len(comments)
    7

Let's briefly override the configuration to push bug 11 over the
threshold.

    >>> from lp.services.config import config
    >>> config.push('malone', '''
    ... [malone]
    ... comments_list_max_length: 5
    ... comments_list_truncate_oldest_to: 1
    ... comments_list_truncate_newest_to: 2
    ... ''')

Now only 3 comments will be displayed; the oldest and the 2 newest.

    >>> user_browser.open('http://launchpad.test/bugs/11')
    >>> comments = find_tags_by_class(user_browser.contents, 'comment-text')
    >>> len(comments)
    4

With a warning telling the user where the comments have gone:

    >>> print(extract_text(first_tag_by_class(
    ...     user_browser.contents, 'informational message')))
    Displaying first 1
    and last 2
    comments.
    View all 6
    comments or add a comment.

The add comment box is present but hidden so people don't accidentally
reply to the wrong message.

    >>> print(find_tag_by_id(
    ...     user_browser.contents, 'add-comment-form-container'))
    <div class="hidden" id="add-comment-form-container">...
    <div id="add-comment-form">...</div>...
    </div>

In amongst that message are two links that will let us see all the
comments and the add comment box.

    >>> user_browser.getLink('View all 6 comments').url
    'http://.../jokosher/+bug/11?comments=all'

    >>> user_browser.getLink('add a comment').url
    'http://.../jokosher/+bug/11?comments=all'

    >>> user_browser.getLink('View all 6 comments').click()
    >>> comments = find_tags_by_class(user_browser.contents, 'comment-text')
    >>> len(comments)
    7

    >>> print(find_tag_by_id(user_browser.contents, 'add-comment-form').name)
    div

Anonymous users have a slightly different experience. If the comment
list is truncated, the usual "to post a comment you must log in" note
is also removed.

    >>> anon_browser.open('http://launchpad.test/bugs/11')
    >>> print(find_tag_by_id(
    ...     anon_browser.contents, 'add-comment-login-first'))
    None

When an anonymous user views all comments, the "you must log in" note
returns.

    >>> anon_browser.getLink('View all 6 comments').click()
    >>> add_comment_link = find_tag_by_id(
    ...     anon_browser.contents, 'add-comment-login-first')
    >>> print(extract_text(add_comment_link))
    To post a comment you must log in.
    >>> print(add_comment_link.a.get('href'))
    +login?comments=all

Restore the configuration to its previous setting.

    >>> config.pop('malone')
    (...)
