===================
Blueprints Overview
===================

Launchpad makes it easy for users to see the blueprints filed against any
product or distribution. There's a page where users can find the latest
blueprints, and also other pages where users can browse through complete
lists of blueprints for a given product or distribution.

A number of tests in this need a product with blueprints enabled, so we'll
enable them on firefox.

    >>> from zope.component import getUtility
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.registry.interfaces.product import IProductSet
    >>> login('admin@canonical.com')
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> firefox.blueprints_usage = ServiceUsage.LAUNCHPAD
    >>> transaction.commit()
    >>> logout()

Viewing lists of blueprints
===========================

Launchpad provides a dedicated page where users can browse through all the
available blueprints for any product or distribution. Users can reach this
page from any context by following the "Blueprints" tab.


Viewing blueprints targeted to a product
----------------------------------------

Let's use the Mozilla Firefox product as an example. Users can see the list
of blueprints attached to Mozilla Firefox by following the "Blueprints" tab:

    >>> user_browser.open('http://launchpad.test/firefox')
    >>> user_browser.getLink('Blueprints').click()
    >>> main = find_main_content(user_browser.contents)
    >>> print(backslashreplace(extract_text(main)))
    Blueprints for Mozilla Firefox...
    Priority...Blueprint...Design  ...Delivery      ...
    High    ...svg-support  ...Approved...Beta Available...


Viewing blueprints targeted to a product series
-----------------------------------------------

It's possible to narrow down the list of blueprints to show only those
targeted to a given product series. Let's pick the Mozilla Firefox 1.0
series as an example. To begin with, there are no blueprints listed on
the blueprints page for 1.0:

    >>> user_browser.open('http://blueprints.launchpad.test/firefox/1.0')
    >>> main = find_main_content(user_browser.contents)
    >>> print(backslashreplace(extract_text(main)))
    Blueprints for 1.0
    Launchpad lets projects track the features they intend to implement...

Let's target an existing Mozilla Firefox blueprint to the 1.0 series:

    >>> browser = admin_browser
    >>> browser.open('http://launchpad.test/firefox/+specs')
    >>> browser.getLink('svg-support').click()
    >>> print(browser.title)
    Support Native SVG Objects...
    >>> browser.getLink('Propose as goal').click()
    >>> main = find_main_content(browser.contents)
    >>> print(backslashreplace(extract_text(main)))
    Target to a product series
    Support Native SVG Objects
    ...

    >>> series = browser.getControl('Series Goal')
    >>> series.displayValue = ['firefox 1.0']
    >>> browser.getControl('Continue').click()
    >>> main = find_main_content(browser.contents)
    >>> print(extract_text(find_tag_by_id(main, 'series-goal')))
    Series goal: Accepted for 1.0...

We'll also target the blueprint to a milestone.  First we'll create a
milestone:

    >>> browser.open('http://launchpad.test/firefox/1.0')
    >>> browser.getLink('Create milestone').click()
    >>> browser.getControl('Name').value = '1.0.9'
    >>> browser.getControl('Date Targeted').value = '2050-05-05'
    >>> browser.getControl('Summary').value = 'First ever milestone!'
    >>> browser.getControl('Register Milestone').click()

Now we'll target our chosen blueprint to the new milestone:

    >>> browser.open('http://launchpad.test/firefox/+specs')
    >>> browser.getLink('svg-support').click()
    >>> browser.getLink('Target milestone').click()
    >>> main = find_main_content(browser.contents)
    >>> print(backslashreplace(extract_text(main)))
    Target to a milestone
    ...
    Support Native SVG Objects
    Select the milestone of Mozilla Firefox in which you would like
    this feature to be implemented...

    >>> milestones = browser.getControl('Milestone')
    >>> milestones.displayValue = ['Mozilla Firefox 1.0.9']
    >>> browser.getControl('Change').click()
    >>> main = find_main_content(browser.contents)
    >>> print(extract_text(find_tag_by_id(main, 'milestone-target')))
    Milestone target:...1.0.9...

Now the blueprint listing for the 1.0 series includes an entry for our chosen
blueprint. It also lists the milestone to which the blueprint is targeted:

    >>> user_browser.open('http://blueprints.launchpad.test/firefox/1.0')
    >>> main = find_main_content(user_browser.contents)
    >>> print(backslashreplace(extract_text(main)))
    Blueprints for 1.0...
    Priority...Blueprint...Design  ...Delivery...Assignee...Milestone...
    High    ...svg-support  ...Approved...Beta    ...Carlos  ...1.0.9    ...

It's possible to navigate to the milestone directly:

    >>> user_browser.getLink('1.0.9').click()
    >>> print(user_browser.title)
    1.0.9 : Mozilla Firefox


Viewing blueprints targeted to a distribution
---------------------------------------------

Let's use the Ubuntu distribution as an example. Users can see the list of
blueprints attached to Ubuntu Linux by following the "Blueprints" tab:

    >>> user_browser.open('http://launchpad.test/ubuntu')
    >>> user_browser.getLink('Blueprints').click()
    >>> main = find_main_content(user_browser.contents)
    >>> print(backslashreplace(extract_text(main)))
    Blueprints for Ubuntu...
    Priority ...Blueprint        ...Design    ...Delivery...
    Undefined...media-integrity-check...Discussion...Unknown...


Viewing blueprints targeted to a distribution series
----------------------------------------------------

As before, it's possible to narrow down the list of blueprints to show only
those targeted to a given distribution series. Let's pick the Grumpy Groundhog
series as an example. To begin with, there are no blueprints listed on the
blueprints page for Grumpy:

    >>> user_browser.open('http://blueprints.launchpad.test/ubuntu/grumpy')
    >>> main = find_main_content(user_browser.contents)
    >>> print(backslashreplace(extract_text(main)))
    Blueprints for Grumpy
    Launchpad lets projects track the features they intend to implement...

Let's target an existing Ubuntu blueprint to the Grumpy series:

    >>> browser = admin_browser
    >>> browser.open('http://launchpad.test/ubuntu/+specs')
    >>> browser.getLink('media-integrity-check').click()
    >>> main = find_main_content(browser.contents)
    >>> print(browser.title)
    CD Media Integrity Check...
    >>> browser.getLink('Propose as goal').click()
    >>> main = find_main_content(browser.contents)
    >>> print(backslashreplace(extract_text(main)))
    Target to a distribution series
    CD Media Integrity Check
    ...
    >>> series = browser.getControl('Series Goal')
    >>> series.displayValue = ['ubuntu grumpy']
    >>> browser.getControl('Continue').click()
    >>> main = find_main_content(browser.contents)
    >>> print(extract_text(find_tag_by_id(browser.contents, 'series-goal')))
    Series goal: Accepted for grumpy...

We'll also target the blueprint to a milestone.  First we'll create a
milestone:

    >>> browser.open('http://launchpad.test/ubuntu/grumpy/')
    >>> browser.getLink('Create milestone').click()
    >>> browser.getControl('Name').value = 'drift-1'
    >>> browser.getControl('Date Targeted').value = '2050-05-05'
    >>> browser.getControl('Summary').value = 'First drift of groundhogs!'
    >>> browser.getControl('Register Milestone').click()

Now we'll target our chosen blueprint to the new milestone:

    >>> browser.open('http://launchpad.test/ubuntu/+specs')
    >>> browser.getLink('media-integrity-check').click()
    >>> browser.getLink('Target milestone').click()
    >>> print(extract_text(find_main_content(browser.contents)))
    Target to a milestone
    ...
    CD Media Integrity Check
    Select the milestone of Ubuntu in which you would like this feature
    to be implemented...

    >>> milestones = browser.getControl('Milestone')
    >>> milestones.displayValue = ['Ubuntu drift-1']
    >>> browser.getControl('Change').click()
    >>> print(extract_text(
    ...     find_tag_by_id(browser.contents, 'milestone-target')))
    Milestone target: drift-1

Finally, the blueprint listing for Grumpy includes an entry for our chosen
blueprint. It also lists the milestone to which the blueprint is targeted:

    >>> user_browser.open('http://blueprints.launchpad.test/ubuntu/grumpy')
    >>> main = find_main_content(user_browser.contents)
    >>> print(backslashreplace(extract_text(main)))
    Blueprints for Grumpy...
    Priority ...Blueprint        ...Design    ...Delivery...Milestone...
    Undefined...media-integrity-check...Discussion...Unknown ...drift-1  ...

It's possible to navigate to the milestone directly:

    >>> user_browser.getLink('drift-1').click()
    >>> print(user_browser.title)
    drift-1 : Ubuntu
