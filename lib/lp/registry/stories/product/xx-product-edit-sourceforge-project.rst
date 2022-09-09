Editing the SourceForge project
-------------------------------

The setting of the SourceForge project is constrained.

    >>> def set_sourceforge_project(name):
    ...     admin_browser.open("http://launchpad.test/firefox/+edit")
    ...     admin_browser.getControl("Sourceforge Project").value = name
    ...     admin_browser.getControl("Change").click()
    ...     print(admin_browser.url)
    ...     print_feedback_messages(admin_browser.contents)
    ...

    >>> set_sourceforge_project("1234")
    http://launchpad.test/firefox/+edit
    There is 1 error.
    SourceForge project names must begin with a letter (A
    to Z; case does not matter), followed by zero or more
    letters, numbers, or hyphens, then end with a letter
    or number. In total it must not be more than 63
    characters in length.

    >>> set_sourceforge_project("x" * 64)
    http://launchpad.test/firefox/+edit
    There is 1 error.
    SourceForge project names must begin with a letter (A
    to Z; case does not matter), followed by zero or more
    letters, numbers, or hyphens, then end with a letter
    or number. In total it must not be more than 63
    characters in length.

    >>> set_sourceforge_project("")
    http://launchpad.test/firefox

    >>> set_sourceforge_project("firefox")
    http://launchpad.test/firefox
