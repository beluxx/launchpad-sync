Bug tracker information
=======================

If a product doesn't use Launchpad to track its bugs, there's
information about the product's bug tracker when adding an upstream
task.

    >>> user_browser.open(
    ...    'http://launchpad.test/firefox/+bug/1/+choose-affected-product')
    >>> user_browser.getControl('Project').value = 'gnome-terminal'
    >>> user_browser.getControl('Continue').click()
    >>> print(user_browser.contents)
    <...GNOME Terminal uses
    <a href="http://bugzilla.gnome.org/bugs">GnomeGBug GTracker</a>
    to track its bugs...

    >>> from lp.bugs.tests.bug import print_upstream_linking_form
    >>> print_upstream_linking_form(user_browser)
    (*) I have the URL for the upstream bug:
        [          ]
    ( ) I have already emailed an upstream bug contact:
        [          ]
    ( ) I want to add this upstream project to the bug report, but someone
        must find or report this bug in the upstream bug tracker.

If a product doesn't use Launchpad, and doesn't have a bug tracker
specified, it will simply say that it doesn't use Launchpad to track
its bugs and prompt for a URL or an email address.

    >>> user_browser.open(
    ...    'http://launchpad.test/firefox/+bug/1/+choose-affected-product')
    >>> user_browser.getControl('Project').value = 'thunderbird'
    >>> user_browser.getControl('Continue').click()
    >>> print(user_browser.contents)
    <...Mozilla Thunderbird doesn't use Launchpad to track its bugs...

    >>> print_upstream_linking_form(user_browser)
    (*) I have the URL for the upstream bug:
        [          ]
    ( ) I have already emailed an upstream bug contact:
        [          ]
    ( ) I want to add this upstream project to the bug report, but someone
        must find or report this bug in the upstream bug tracker.

For products using Launchpad, the linking upstream widgets won't even
appear.

    >>> user_browser.open(
    ...    'http://launchpad.test/firefox/+bug/1/+choose-affected-product')
    >>> user_browser.getControl('Project').value = 'evolution'
    >>> user_browser.getControl('Continue').click()

    >>> print_upstream_linking_form(user_browser)
    Traceback (most recent call last):
    ...
    LookupError: name 'field.link_upstream_how'
    ...
