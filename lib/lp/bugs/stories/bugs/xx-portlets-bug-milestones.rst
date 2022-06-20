Milestone-targeted bugs portlet
===============================

The milestone-targeted bugs portlet displays the number of bugs that have
been targeted to a specific milestone.

The portlet is also available from a project's bugs home page.  To demonstrate
this, a project has to first have one of its milestones associated with a bug.
If there are no milestones with bugs, then there is no milestone-targeted
portlet.

    >>> anon_browser.open("http://bugs.launchpad.test/firefox")
    >>> portlet = find_portlet(
    ...     anon_browser.contents, "Milestone-targeted bugs")
    >>> print(portlet)
    None

To enable the portlet, a bugtask needs to have a milestone associated with it.
Bug 4 has a Firefox bugtask, which can be used once a milestone is selected.

    >>> login('test@canonical.com')
    >>> from zope.component import getUtility
    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> ff_bugtask = getUtility(IBugTaskSet).get(13)
    >>> print(ff_bugtask.bug.id)
    4

    >>> from lp.registry.interfaces.milestone import IMilestoneSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> ff_milestone = getUtility(IMilestoneSet).getByNameAndProduct(
    ...     "1.0", firefox)
    >>> print(ff_milestone.name)
    1.0

The bugtask milestone is set to the Firefox 1.0 milestone.

    >>> ff_bugtask.milestone = ff_milestone.id
    >>> logout()

Now Firefox has a milestone-targeted bugs portlet on the project's bugs home
page.

    >>> anon_browser.open("http://bugs.launchpad.test/firefox")
    >>> portlet = find_portlet(
    ...     anon_browser.contents, "Milestone-targeted bugs")
    >>> print(extract_text(portlet))
    Milestone-targeted bugs
    1
    1.0

Series pages show the portlet too, when there are series bugs with milestones.
Debian has such. Change debian to track bugs in Launchpad and the portlet
becomes visible.

    >>> from lp.testing.service_usage_helpers import set_service_usage
    >>> set_service_usage('debian', bug_tracking_usage='LAUNCHPAD')

And look at the portlet.

    >>> anon_browser.open("http://bugs.launchpad.test/debian/sarge/+bugs")
    >>> portlet = find_portlet(
    ...     anon_browser.contents, "Milestone-targeted bugs")
    >>> print(extract_text(portlet))
    Milestone-targeted bugs
    1
    3.1

