First, let's make sure the sample user (name12) can't view the page to
add a milestone to the Ubuntu/hoary distroseries, which is owned by the Ubuntu
Team (ubuntu-team).

    >>> name12_browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> name12_browser.open(
    ...     "http://launchpad.test/ubuntu/hoary/+addmilestone"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Let's make the sample user the owner of Ubuntu for this test. The owner
of the distribution should be able to add milestones for it, of course!

    >>> admin_browser.open("http://launchpad.test/ubuntu/+reassign")
    >>> admin_browser.getControl(name="field.owner").value = "name12"
    >>> admin_browser.getControl("Change").click()

Now let's go back and try the add milestone page again. It works:

    >>> name12_browser.open(
    ...     "http://launchpad.test/ubuntu/hoary/+addmilestone"
    ... )

Now, if we post to that form, we should see a success, and the page should
redirect to the Ubuntu Hoary page showing the milestone we added.

    >>> name12_browser.getControl("Name").value = "sounder01"
    >>> name12_browser.getControl("Register Milestone").click()
    >>> name12_browser.url
    'http://launchpad.test/ubuntu/hoary'
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(name12_browser.contents, "series-hoary")
    ...     )
    ... )
    Version ...
    sounder01 ...

Try to target a distribution bug to this milestone.  The form uses the
database ID for the milestone, so we find the ID:

    >>> from lp.registry.model.distribution import Distribution
    >>> from lp.services.database.interfaces import IStore
    >>> ubuntu = IStore(Distribution).find(Distribution, name="ubuntu").one()
    >>> for milestone in ubuntu.milestones:
    ...     if milestone.name == "sounder01":
    ...         break
    ... else:
    ...     assert False, "Milestone not found"
    ...

    >>> name12_browser.open(
    ...     "http://launchpad.test/ubuntu/+source/mozilla-firefox/+bug/1/"
    ...     "+editstatus"
    ... )
    >>> milestone_control = name12_browser.getControl(
    ...     name="ubuntu_mozilla-firefox.milestone"
    ... )
    >>> milestone_control.value = [str(milestone.id)]
    >>> name12_browser.getControl("Save Changes").click()
