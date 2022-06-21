
Person Views of Spec Lists
==========================

There are a couple of views of the specs related to a person.

The Features link shows an overview of all the specifications
involving that person.

    >>> browser.open('http://blueprints.launchpad.test/~name16')
    >>> print(browser.title)
    Blueprints : Foo Bar
    >>> soup = find_main_content(browser.contents)
    >>> soup('h1')
    [<h1>Blueprints involving Foo Bar</h1>]

In the left-side menu, there are menu items that allow to select a
subset of these specifications. The 'Approver' link selects the specs
that the user is supposed to approve.

    >>> browser.getLink('Approver').click()
    >>> browser.url
    '.../~name16/+specs?role=approver'
    >>> soup = find_main_content(browser.contents)
    >>> print(soup.find('p', 'informational message'))
    <p class="informational message">
    No feature specifications match your criteria.
    </p>

The 'Assignee' link displays a page showing the specifications assigned
to the person.

    >>> browser.getLink('Assignee').click()
    >>> browser.url
    '.../~name16/+specs?role=assignee'
    >>> soup = find_main_content(browser.contents)
    >>> print(soup.find('p', 'informational message'))
    <p class="informational message">
    No feature specifications match your criteria.
    </p>

The 'Subscriber' link displays a page showing the specifications to
which the person subscribed.

    >>> browser.getLink('Subscriber').click()
    >>> browser.url
    '.../~name16/+specs?role=subscriber'
    >>> browser.getLink('svg-support').attrs['title']
    'Support Native SVG Objects'

The 'Drafter' link displays a page showing the specifications that the
person drafted.

    >>> browser.getLink('Drafter').click()
    >>> browser.url
    '.../~name16/+specs?role=drafter'
    >>> soup = find_main_content(browser.contents)
    >>> print(soup.find('p', 'informational message'))
    <p class="informational message">
    No feature specifications match your criteria.
    </p>

The 'Workload' link displays a page showing the specifications that are
in the workload of that person.

    >>> browser.getLink('Workload').click()
    >>> browser.url
    '.../~name16/+specworkload'
    >>> print(browser.title)
    Blueprint workload...

For a team, the 'Workload' link first shows the specifications that
are part of the workload for the team.  It then shows the workloads
for each member of the team, using batching.

    >>> from lp.services.helpers import backslashreplace
    >>> browser.open('http://blueprints.launchpad.test/~admins')
    >>> print(backslashreplace(browser.title))
    Blueprints : \u201cLaunchpad Administrators\u201d team
    >>> browser.getLink('Workload').click()
    >>> browser.url
    '.../~admins/+specworkload'
    >>> print(browser.title)
    Blueprint workload...
    >>> print(extract_text(find_main_content(browser.contents)))
    Blueprint workload...
    Team member workload...
    Andrew Bennetts's specifications:...
    Daniel Silverstone has no outstanding specifications...
