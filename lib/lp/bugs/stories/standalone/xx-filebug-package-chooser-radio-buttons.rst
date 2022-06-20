The +filebug pages for a distribution and distribution package present a
simple package selection widget, where you can either select the package
in which you think the bug occurrs, or say "I don't know".

The default on the distribution +filebug page is "I don't know". We
will use the advanced filebug form to skip searching for dupes.

    >>> user_browser.open("http://launchpad.test/ubuntu/+filebug")
    >>> user_browser.getControl('Summary', index=0).value = 'Bug Summary'
    >>> user_browser.getControl('Continue').click()

    >>> print(user_browser.getControl(name="packagename_option").value)
    ['none']

("I don't know" remains selected.)

    >>> print(user_browser.getControl(name="packagename_option").value)
    ['none']

If you enter a package name that doesn't exist in the distribution,
you're returned to the page, with the "choose" radio button selected.

    >>> user_browser.getControl(name="field.packagename").value = (
    ...     "nosuchpackage")
    >>> user_browser.getControl("Submit Bug Report").click()

    >>> user_browser.url
    'http://launchpad.test/ubuntu/+filebug'

    >>> print(user_browser.getControl(name="packagename_option").value)
    ['choose']

On the package +filebug page, the package name is populated by default.

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/+source/mozilla-firefox/+filebug")
    >>> user_browser.getControl('Summary', index=0).value = 'Bug Summary'
    >>> user_browser.getControl('Continue').click()

    >>> print(user_browser.getControl(name="packagename_option").value)
    ['choose']

    >>> print(user_browser.getControl(name="field.packagename").value)
    mozilla-firefox
