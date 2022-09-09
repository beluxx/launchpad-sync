Changing Milestones of Bugtasks
===============================

Bugtasks associated with products, productseries, distributions and
distroseries can be targeted to milestones.

Sample Person is the owner of the Firefox product. They decide to plan
when bugs should be fixed by setting up some milestones.

    >>> owner_browser = setupBrowser("Basic test@canonical.com:test")
    >>> owner_browser.open("http://launchpad.test/firefox/+bug/1")

Bug 1 affects the Firefox project. The 1.0 milestone is available for
use, but the bug is not yet targeted to that milestone.

    >>> table = find_tag_by_id(owner_browser.contents, "affected-software")
    >>> print(extract_text(table))
    Affects             Status  Importance  Assigned to        Milestone
    ... Mozilla Firefox ... New     Low     Mark Shuttleworth
    ...

    >>> milestone_control = owner_browser.getControl(
    ...     name="firefox.milestone", index=0
    ... )
    >>> milestone_control.displayValue
    ['(nothing selected)']
    >>> milestone_control.displayOptions
    ['(nothing selected)', 'Mozilla Firefox 1.0']

Sample Person targets the bug to 1.0 for Firefox. This shows up in the
Affects table, and in the selected value of the Milestone menu.

    >>> milestone_control.displayValue = ["Mozilla Firefox 1.0"]
    >>> owner_browser.getControl("Save Changes", index=0).click()
    >>> table = find_tag_by_id(owner_browser.contents, "affected-software")
    >>> print(extract_text(table))
    Affects             Status  Importance  Assigned to           Milestone
    ... Mozilla Firefox ... New     Low     Mark Shuttleworth ... 1.0
    ...
    >>> milestone_control = owner_browser.getControl(
    ...     name="firefox.milestone", index=0
    ... )
    >>> milestone_control.displayValue
    ['Mozilla Firefox 1.0']

Sample Person defines milestone 1.0.1 for firefox series 1.0...

    >>> owner_browser.open("http://launchpad.test/firefox/1.0/+addmilestone")
    >>> name_field = owner_browser.getControl("Name:")
    >>> name_field.value = "1.0.1"
    >>> owner_browser.getControl("Register Milestone").click()
    >>> print_errors(owner_browser.contents)

...and then they approve the nomination of bug #1 for the firefox series 1.0.

    >>> owner_browser.open("http://launchpad.test/firefox/+bug/1")
    >>> owner_browser.getControl("Approve", index=0).click()

Sample Person assigns the firefox series 1.0 bugtask for bug 1 to
to the milestone 1.0.0. Note that milestones defined for the product itself
are listed too.

    >>> milestone_control = owner_browser.getControl(
    ...     name="firefox_1.0.milestone"
    ... )
    >>> milestone_control.displayValue
    ['(nothing selected)']
    >>> milestone_control.displayOptions
    ['(nothing selected)', 'Mozilla Firefox 1.0.1', 'Mozilla Firefox 1.0']
    >>> milestone_control.displayValue = ["Mozilla Firefox 1.0.1"]
    >>> owner_browser.getControl("Save Changes", index=1).click()
    >>> milestone_control = owner_browser.getControl(
    ...     name="firefox_1.0.milestone"
    ... )
    >>> milestone_control.displayValue
    ['Mozilla Firefox 1.0.1']

Foo Bar is a member of the Ubuntu team that owns the Ubuntu
distribution. They decide to assign some bug to some milestones.
First they register a new milestone.

    >>> admin_browser.open("http://launchpad.test/ubuntu/hoary/+addmilestone")
    >>> name_field = admin_browser.getControl("Name:")
    >>> name_field.value = "5.04.rc1"
    >>> admin_browser.getControl("Register Milestone").click()

They target bug #1 to milestone 5.04-rc1 for Ubuntu.

    >>> admin_browser.open("http://launchpad.test/firefox/+bug/1")
    >>> table = find_tag_by_id(admin_browser.contents, "affected-software")
    >>> print(extract_text(table))  # noqa
    Affects                      Status  Importance  Assigned to           Milestone
    ... Mozilla Firefox          ... New     Low     Mark Shuttleworth ... 1.0
    ...
    ... mozilla-firefox (Ubuntu) ... New     Medium
    ...
    >>> milestone_control = admin_browser.getControl(
    ...     name="ubuntu_mozilla-firefox.milestone"
    ... )
    >>> milestone_control.displayValue
    ['(nothing selected)']
    >>> milestone_control.displayOptions
    ['(nothing selected)', 'Ubuntu 5.04.rc1']
    >>> milestone_control.displayValue = ["Ubuntu 5.04.rc1"]
    >>> admin_browser.getControl("Save Changes", index=3).click()
    >>> table = find_tag_by_id(admin_browser.contents, "affected-software")
    >>> print(extract_text(table))  # noqa
    Affects                      Status  Importance  Assigned to           Milestone
    ... Mozilla Firefox      ... New     Low         Mark Shuttleworth ... 1.0
    ...
    ... mozilla-firefox (Ubuntu) ... New Medium ...                        5.04.rc1
    ...
    >>> milestone_control = admin_browser.getControl(
    ...     name="ubuntu_mozilla-firefox.milestone"
    ... )
    >>> milestone_control.displayValue
    ['Ubuntu 5.04.rc1']

Bug #1 is already nominated for Hoary, so they can create another bugtask
by clicking on the "approve" button for this nomination.

    >>> admin_browser.getControl("Approve").click()

Now they can set the milestone for the bug in Hoary. Note that the
milestone assigned for Ubuntu has been "carried over", so they
remove the milestone now.

    >>> milestone_control = admin_browser.getControl(
    ...     name="ubuntu_hoary_mozilla-firefox.milestone"
    ... )
    >>> milestone_control.displayValue
    ['Ubuntu 5.04.rc1']

    >>> milestone_control.displayOptions
    ['(nothing selected)', 'Ubuntu 5.04.rc1']
    >>> milestone_control.displayValue = ["(nothing selected)"]
    >>> admin_browser.getControl("Save Changes", index=3).click()
    >>> milestone_control = admin_browser.getControl(
    ...     name="ubuntu_hoary_mozilla-firefox.milestone"
    ... )
    >>> milestone_control.displayValue
    ['(nothing selected)']
