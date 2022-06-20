Displaying an Unknown importance after switching to using Launchpad Bugs
========================================================================

XXX: This test should be restructured into a more general "Switching to
     Launchpad Bugs" use case. -- Bjorn Tillenius, 2007-04-24

When project doesn't use Launchpad as its official bugtracker, it's
possible for its bugs to have an Unknown importance.

    >>> admin_browser.open('http://launchpad.test/debian/+edit')
    >>> admin_browser.getControl(
    ...     'Bugs in this project are tracked in Launchpad').selected
    False
    >>> user_browser.open(
    ...     'http://launchpad.test/debian'
    ...     '/+source/evolution/+bug/7/+editstatus')
    >>> main = find_main_content(user_browser.contents)
    >>> read_only_icon = main.find('span', {'class': 'sprite read-only'})
    >>> print(extract_text(read_only_icon.parent))
    Unknown

If the project switches to use Launchpad as its bug tracker, the
importance will still have an Unknown value.

    >>> admin_browser.open('http://launchpad.test/debian/+edit')
    >>> admin_browser.getControl(
    ...     'Bugs in this project are tracked in Launchpad').selected = True
    >>> admin_browser.getControl('Change', index=3).click()
    >>> admin_browser.title
    'Debian in Launchpad'

    >>> user_browser.open(
    ...     'http://launchpad.test'
    ...     '/debian/+source/evolution/+bug/7/+editstatus')
    >>> main = find_main_content(user_browser.contents)
    >>> read_only_icon = main.find('span', {'class': 'sprite read-only'})
    >>> print(extract_text(read_only_icon.parent))
    Unknown
