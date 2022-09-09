Adding a Product to a ProjectGroup
----------------------------------

A project registrant can add products to a project. Let's add an
Eye of GNOME product to the GNOME project.  There is a link at the
bottom of the project page to add a new product:

    >>> browser.addHeader("Authorization", "Basic test@canonical.com:test")
    >>> browser.open("http://launchpad.test/gnome")
    >>> browser.getLink("Register a project in GNOME").click()
    >>> print(browser.url)
    http://launchpad.test/gnome/+newproduct

Now we'll fill in the product details and add it.  This is a two-step
process.  Fill in the first page and then 'Continue' which will keep
us on the same page.

    >>> browser.getControl(name="field.display_name").value = "Eye of GNOME"
    >>> browser.getControl(name="field.name", index=0).value = "eog"
    >>> browser.getControl(
    ...     name="field.summary"
    ... ).value = "An image viewer for GNOME"
    >>> browser.getControl("Continue").click()
    >>> print(browser.url)
    http://launchpad.test/gnome/+newproduct

    >>> browser.getControl(name="field.description").value = "Blah blah blah"
    >>> browser.getControl(name="field.licenses").value = ["GNU_GPL_V2"]
    >>> browser.getControl("Complete Registration").click()
    >>> print(browser.url)
    http://launchpad.test/eog

Now let's get the page for that product to make sure it's there.  It
is accessible both under "/" and under the project URL:

    >>> anon_browser.open("http://launchpad.test/eog")
    >>> "Eye of GNOME" in anon_browser.contents
    True

    >>> anon_browser.open("http://launchpad.test/gnome/eog")
    >>> "Eye of GNOME" in anon_browser.contents
    True

