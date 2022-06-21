
We also have the special Launchpad Statistics summary page. This is only
acessible to launchpad Admins:

    >>> user_browser.open('http://launchpad.test/+statistics')
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...


When we login as an admin, we can see all the stats listed:

    >>> admin_browser.open('http://launchpad.test/+statistics/')
    >>> print(admin_browser.title)
    Launchpad statistics
    >>> 'answered_question_count' in admin_browser.contents
    True
    >>> 'products_with_blueprints' in admin_browser.contents
    True
    >>> 'solved_question_count' in admin_browser.contents
    True
