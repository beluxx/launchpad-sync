Advanced personal subscriptions
-------------------------------

When a user visits the +subscribe page of a bug they are given the option to
subscribe to the bug at a given BugNotificationLevel.

    >>> from lp.services.webapp import canonical_url
    >>> from lp.testing.sampledata import USER_EMAIL
    >>> login(USER_EMAIL)
    >>> bug = factory.makeBug()
    >>> task = bug.default_bugtask
    >>> url = canonical_url(task, view_name='+subscribe')
    >>> logout()
    >>> user_browser.open(url)
    >>> bug_notification_level_control = user_browser.getControl(
    ...     name='field.bug_notification_level')
    >>> for control in bug_notification_level_control.controls:
    ...     print(control.optionValue)
    Discussion
    Details
    Lifecycle

The user can subscribe to the bug at any of the given notification levels. In
this case, they want to subscribe to just metadata updates:

    >>> bug_notification_level_control.getControl(
    ...     'any change is made to this bug, other than a new comment '
    ...     'being added').click()
    >>> user_browser.getControl('Continue').click()

    >>> for message in find_tags_by_class(user_browser.contents, 'message'):
    ...     print(extract_text(message))
    You have subscribed to this bug report.
