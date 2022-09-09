
We want to test the interface that allows us to mark one specification as
superseded by another. It should allow us to select the superseded
specification, select its successor, and then update the database.

First, we need to be able to see this page, we will go in as Carlos, the
approver of the specification. Not only will we test the existence of the
page, we will also test that the spec is currently in the New status (i.e.
not already superseded).

    >>> browser.addHeader("Authorization", "Basic carlos@canonical.com:test")
    >>> browser.open(
    ...     "http://blueprints.launchpad.test/firefox/+spec/"
    ...     + "extension-manager-upgrades"
    ... )
    >>> "New" in browser.contents
    True

Make sure Bug 4116 stays fixed

    >>> browser.open(
    ...     "http://blueprints.launchpad.test/firefox/+spec/"
    ...     + "extension-manager-upgrades/+supersede"
    ... )

The page contains a link back to the blueprint, in case we change our
mind.

    >>> back_link = browser.getLink("Extension Manager Upgrades")
    >>> back_link.url  # noqa
    'http://blueprints.launchpad.test/firefox/+spec/extension-manager-upgrades'
    >>> browser.getLink("Cancel").url  # noqa
    'http://blueprints.launchpad.test/firefox/+spec/extension-manager-upgrades'

Next, we will POST to that form, setting the spec which supersedes this one:

    >>> browser.getControl("Superseded by").value = "svg-support"
    >>> browser.getControl("Continue").click()

Now, on the spec page we should see an alert that the spec has been
superseded. The spec status should also have changed to superseded.

    >>> "This blueprint has been superseded." in browser.contents
    True
    >>> "Superseded" in browser.contents
    True

And finally, we want to clear the superseding spec data and reset the
status to New. If we POST back to the form, with Superseded by empty,
then it should automatically do this:

    >>> browser.getLink("Mark superseded").click()
    >>> browser.getControl("Superseded by").value
    'svg-support'
    >>> browser.getControl("Superseded by").value = ""
    >>> browser.getControl("Continue").click()

Let's confirm the status change:

    >>> "New" in browser.contents
    True
