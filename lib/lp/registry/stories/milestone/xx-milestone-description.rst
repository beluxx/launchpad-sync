Milestone Summary
=================

Distribution and Product milestones have an optional summary text.

Let's make the sample user the owner of Ubuntu and alsa-utils for this test.

    >>> admin_browser.open("http://launchpad.test/ubuntu/+reassign")
    >>> admin_browser.getControl(name="field.owner").value = "name12"
    >>> admin_browser.getControl("Change").click()

    >>> admin_browser.open("http://launchpad.test/alsa-utils/+edit-people")
    >>> admin_browser.getControl(name="field.owner").value = "name12"
    >>> admin_browser.getControl("Save changes").click()

    >>> test_browser = setupBrowser(auth="Basic test@canonical.com:test")

Distribution Milestone Summary
------------------------------

We can set the summary while creating a milestone for a Distribution.

    >>> test_browser.open("http://launchpad.test/ubuntu/hoary/+addmilestone")
    >>> test_browser.getControl("Name").value = "milestone1"
    >>> test_browser.getControl(
    ...     "Summary"
    ... ).value = "Summary of first Ubuntu milestone."
    >>> test_browser.getControl("Register Milestone").click()

The summary appears on the milestone index page.

    >>> test_browser.open(
    ...     "http://launchpad.test/ubuntu/+milestone/milestone1"
    ... )
    >>> tag = find_tag_by_id(test_browser.contents, "description")
    >>> print(extract_text(tag))
    Summary of first Ubuntu milestone.

We can edit the summary after creating the milestone.

    >>> test_browser.open(
    ...     "http://launchpad.test/ubuntu/+milestone/milestone1/+edit"
    ... )
    >>> test_browser.getControl(
    ...     "Summary"
    ... ).value = "Modified summary of first Ubuntu milestone."
    >>> test_browser.getControl("Update").click()

And see that it is indeed modified on the milestone page.

    >>> test_browser.open(
    ...     "http://launchpad.test/ubuntu/+milestone/milestone1"
    ... )
    >>> tag = find_tag_by_id(test_browser.contents, "description")
    >>> print(extract_text(tag))
    Modified summary of first Ubuntu milestone.


Product Milestone Summary
-------------------------

We can set the summary while creating a milestone for a Product.

    >>> test_browser.open(
    ...     "http://launchpad.test/alsa-utils/trunk/+addmilestone"
    ... )
    >>> test_browser.getControl("Name").value = "milestone1"
    >>> test_browser.getControl(
    ...     "Summary"
    ... ).value = "Summary of first alsa-utils milestone."
    >>> test_browser.getControl("Register Milestone").click()

The summary appears on the milestone index page.

    >>> test_browser.open(
    ...     "http://launchpad.test/alsa-utils/+milestone/milestone1"
    ... )
    >>> tag = find_tag_by_id(test_browser.contents, "description")
    >>> print(extract_text(tag))
    Summary of first alsa-utils milestone.

We can edit the summary after creating the milestone.

    >>> test_browser.open(
    ...     "http://launchpad.test/alsa-utils/+milestone/milestone1/+edit"
    ... )
    >>> test_browser.getControl(
    ...     "Summary"
    ... ).value = "Modified summary of first alsa-utils milestone."
    >>> test_browser.getControl("Update").click()

And see that it is indeed modified on the milestone page.

    >>> test_browser.open(
    ...     "http://launchpad.test/alsa-utils/+milestone/milestone1"
    ... )
    >>> tag = find_tag_by_id(test_browser.contents, "description")
    >>> print(extract_text(tag))
    Modified summary of first alsa-utils milestone.
