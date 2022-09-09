Inline Editing of BugTasks
==========================

On the bug page, the bugtasks are editable inline. This means that
basically the same form is included on the page for each bugtask. Even
so, if a bug has more than one bugtasks, all the ids used in the forms
are unique (except.for the "Email me about changes to this bug report"
option).

For example, bug one has more than one Package field.

    >>> user_browser.open("http://launchpad.test/bugs/1")
    >>> user_browser.getControl("Package")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.AmbiguityError: label ...'Package' matches: ...

Still, the ids of the fields are unique.

    >>> soup = find_main_content(user_browser.contents)
    >>> non_unique_ids = []
    >>> found_ids = set()
    >>> import re
    >>> for tag in soup.find_all(id=re.compile(".+")):
    ...     if tag["id"] in found_ids:
    ...         non_unique_ids.append(tag["id"])
    ...     found_ids.add(tag["id"])
    ...

(The "Email me..." option has the same id everywhere since the
user is not subscribing to the bugtask, but to the bug.)

    >>> for item in non_unique_ids:
    ...     print(item)
    ...
    subscribe
    subscribe

