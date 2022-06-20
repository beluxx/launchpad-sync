
Now, we are going to show that it is possible to retarget specs, to a
different product or distribution.

First, load the svg-support spec on Firefox:

    >>> admin_browser.open("http://launchpad.test/firefox/+spec/svg-support")

Now, let's make sure we can see the retargeting page for it, as the Foo Bar
administrator:

    >>> admin_browser.getLink("Re-target blueprint").click()

The page contains a link back to the blueprint, in case we change our
mind.

    >>> back_link = admin_browser.getLink('Support Native SVG Objects')
    >>> back_link.url
    'http://blueprints.launchpad.test/firefox/+spec/svg-support'
    >>> admin_browser.getLink('Cancel').url
    'http://blueprints.launchpad.test/firefox/+spec/svg-support'

We can move the blueprint to Evolution.

    >>> admin_browser.getControl("For").value = "evolution"
    >>> admin_browser.getControl("Retarget Blueprint").click()
    >>> admin_browser.url
    'http://blueprints.launchpad.test/evolution/+spec/svg-support'

OK. Now, it follows that we should be able to retarget it immediately from
evolution, to a distribution. Let's try redhat.

    >>> admin_browser.getLink("Re-target blueprint").click()
    >>> admin_browser.getControl("For").value = "redhat"
    >>> admin_browser.getControl("Retarget Blueprint").click()
    >>> admin_browser.url
    'http://blueprints.launchpad.test/redhat/+spec/svg-support'

And similarly, this should now be on Red Hat, and we should be able to send
it straight back to firefox. This means that the data set should finish this
test in the same state that it was when we started.

    >>> admin_browser.getLink("Re-target blueprint").click()
    >>> admin_browser.getControl("For").value = "firefox"
    >>> admin_browser.getControl("Retarget Blueprint").click()
    >>> admin_browser.url
    'http://blueprints.launchpad.test/firefox/+spec/svg-support'

If we try to reassign the spec to a target which doesn't exist, we don't
blow up:

    >>> admin_browser.getLink("Re-target blueprint").click()
    >>> admin_browser.getControl("For").value = "foo bar"
    >>> admin_browser.getControl("Retarget Blueprint").click()

We stay on the same page and get an error message printed out:

    >>> admin_browser.url
    'http://blueprints.launchpad.test/firefox/+spec/svg-support/+retarget'

    >>> for tag in find_tags_by_class(admin_browser.contents, 'message'):
    ...     print(tag.decode_contents())
    There is 1 error.
    <BLANKLINE>
    There is no project with the name 'foo bar'. Please check that name and
    try again.
