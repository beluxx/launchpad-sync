Adding new projects
===================

Normal users should not be able to do this:

    >>> user_browser.open("http://launchpad.test/projectgroups/+new")
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

But an admin user should be able to do it:

    >>> admin_browser.open("http://launchpad.test/projectgroups")
    >>> admin_browser.getLink("Register a project group").click()
    >>> admin_browser.url
    'http://launchpad.test/projectgroups/+new'

Testing if the validator is working for the URL field.
Add a new project without the http://

    >>> admin_browser.getControl("Name", index=0).value = "kde"
    >>> admin_browser.getControl(
    ...     "Display Name"
    ... ).value = "K Desktop Environment"
    >>> admin_browser.getControl("Project Group Summary").value = "KDE"
    >>> admin_browser.getControl(
    ...     "Description"
    ... ).value = "K Desktop Environment"
    >>> admin_browser.getControl("Maintainer").value = "cprov"
    >>> admin_browser.getControl("Homepage URL").value = "www.kde.org"
    >>> admin_browser.getControl("Add").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    "www.kde.org" is not a valid URI

Testing if the validator is working for the name field.

    >>> admin_browser.open("http://launchpad.test/projectgroups/+new")
    >>> admin_browser.getControl("Name", index=0).value = "kde!"
    >>> admin_browser.getControl(
    ...     "Display Name"
    ... ).value = "K Desktop Environment"
    >>> admin_browser.getControl("Project Group Summary").value = "KDE"
    >>> admin_browser.getControl(
    ...     "Description"
    ... ).value = "K Desktop Environment"
    >>> admin_browser.getControl("Maintainer").value = "cprov"
    >>> admin_browser.getControl("Homepage URL").value = "http://kde.org/"
    >>> admin_browser.getControl("Add").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    Invalid name 'kde!'. Names must...

    >>> admin_browser.getControl("Name", index=0).value = "apache"
    >>> admin_browser.getControl("Add").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    apache is already used by another project

Now we add a new project.

    >>> admin_browser.getControl("Name", index=0).value = "kde"
    >>> admin_browser.getControl("Add").click()
    >>> admin_browser.url
    'http://launchpad.test/kde'

    >>> anon_browser.open(admin_browser.url)
    >>> print(anon_browser.title)
    K Desktop Environment in Launchpad
