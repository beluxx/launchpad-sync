Blueprint views
===============

Set Up
------
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

Viewing current blueprints
--------------------------

We should be able to see a "+specs" and a "+portlet-latestspecs" view
on sprint, product, person, project and distribution.

    >>> print(http("""
    ... GET /firefox/+portlet-latestspecs HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /ubuntu/+portlet-latestspecs HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /mozilla/+portlet-latestspecs HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /~carlos/+portlet-latestspecs HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /sprints/ubz/+portlet-latestspecs HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...


    >>> print(http("""
    ... GET /firefox/+specs HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /ubuntu/+specs HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /mozilla/+specs HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /~carlos/+specs HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /sprints/ubz/+specs HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

The other way of sorting blueprints is by assignee:

    >>> print(http("""
    ... GET /firefox/+assignments HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /ubuntu/+assignments HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /mozilla/+assignments HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /~carlos/+assignments HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /sprints/ubz/+assignments HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

Also, we should have "+documentation" views on product, productseries,
project, distro and distroseries.


    >>> print(http("""
    ... GET /firefox/+documentation HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /firefox/1.0/+documentation HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /ubuntu/+documentation HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /ubuntu/hoary/+documentation HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...

    >>> print(http("""
    ... GET /mozilla/+documentation HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...


Some of the listings are supposed to indicate if there is an informational
spec there using a badge:

    >>> print(http("""
    ... GET /kubuntu/+documentation HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    ...Activating Usplash...


Viewing all blueprints
----------------------

From time to time it's useful to review the complete list of all blueprints
associated with a blueprint target, including those blueprints that have
already been implemented.

To demonstrate this, we'll start by creating two blueprints for a
distribution:

    >>> browser = user_browser
    >>> browser.open('http://blueprints.launchpad.test/ubuntu')
    >>> browser.getLink('Register a blueprint').click()
    >>> browser.url
    'http://blueprints.launchpad.test/ubuntu/+addspec'
    >>> browser.getControl('Name').value = 'blueprint-1'
    >>> browser.getControl('Title').value = 'The First Blueprint'
    >>> browser.getControl('Summary').value = 'The first blueprint.'
    >>> browser.getControl('Register').click()
    >>> browser.url
    'http://blueprints.launchpad.test/ubuntu/+spec/blueprint-1'
    >>> browser.open(
    ...     'http://blueprints.launchpad.test/ubuntu/+addspec')
    >>> browser.getControl('Name').value = 'blueprint-2'
    >>> browser.getControl('Title').value = 'The Second Blueprint'
    >>> browser.getControl('Summary').value = 'The second blueprint.'
    >>> browser.getControl('Register').click()
    >>> browser.url
    'http://blueprints.launchpad.test/ubuntu/+spec/blueprint-2'

To begin with, we can see ''both'' blueprints by visiting the distribution's
blueprints page:

    >>> browser.getLink('Blueprints').click()
    >>> browser.url
    'http://blueprints.launchpad.test/ubuntu'
    >>> browser.getLink('blueprint-1')
    <Link...
    >>> browser.getLink('blueprint-2')
    <Link...

Let's mark the ''second'' blueprint as ''implemented'':

    >>> browser.getLink('blueprint-2').click()
    >>> browser.url
    'http://blueprints.launchpad.test/ubuntu/+spec/blueprint-2'
    >>> browser.getLink(url='+status').click()
    >>> browser.url
    'http://blueprints.launchpad.test/ubuntu/+spec/blueprint-2/+status'
    >>> browser.getControl('Implementation Status').value = ['IMPLEMENTED']
    >>> browser.getControl('Change').click()
    >>> browser.url
    'http://blueprints.launchpad.test/ubuntu/+spec/blueprint-2'

By default, implemented blueprints are ''not'' listed on a target's blueprint
listing pages. So now when we visit the distribution's blueprints page, the
second blueprint is no longer visible:

    >>> browser.getLink('Blueprints').click()
    >>> browser.url
    'http://blueprints.launchpad.test/ubuntu'
    >>> browser.getLink('blueprint-1')
    <Link...
    >>> browser.getLink('blueprint-2')
    Traceback (most recent call last):
        ...
    zope.testbrowser.browser.LinkNotFoundError

However, it ''is'' still possible to view the second blueprint by following
the "List all blueprints" link:

    >>> browser.getLink('List all blueprints').click()
    >>> browser.url
    'http://blueprints.launchpad.test/ubuntu/+specs?show=all'
    >>> browser.getLink('blueprint-1')
    <Link...
    >>> browser.getLink('blueprint-2')
    <Link...

It's also possible to access views of all blueprints for the following
blueprint targets:

 * distribution series:

    >>> browser.open('http://blueprints.launchpad.test/ubuntu/hoary')
    >>> browser.getLink('List all blueprints').click()
    >>> browser.url
    'http://blueprints.launchpad.test/ubuntu/hoary/+specs?show=all'

 * project groups:

    >>> browser.open('http://blueprints.launchpad.test/mozilla')
    >>> browser.getLink('List all blueprints').click()
    >>> browser.url
    'http://blueprints.launchpad.test/mozilla/+specs?show=all'

 * products:

    >>> browser.open('http://blueprints.launchpad.test/firefox')
    >>> browser.getLink('List all blueprints').click()
    >>> browser.url
    'http://blueprints.launchpad.test/firefox/+specs?show=all'

 * product series:

    >>> browser.open('http://blueprints.launchpad.test/firefox/1.0')
    >>> browser.getLink('List all blueprints').click()
    >>> browser.url
    'http://blueprints.launchpad.test/firefox/1.0/+specs?show=all'

 * projects:

    >>> browser.open('http://blueprints.launchpad.test/mozilla')
    >>> browser.getLink('List all blueprints').click()
    >>> browser.url
    'http://blueprints.launchpad.test/mozilla/+specs?show=all'
    >>> specs = find_tag_by_id(browser.contents, 'speclisting')
    >>> print(extract_text(specs))
    Priority Blueprint Design Delivery Assignee Project Series
    High     svg-support Approved Beta Available Carlos ... firefox
    Medium   canvas      New Unknown firefox
    Medium   extension-manager-upgrades New Informational Carlos ... firefox
    Medium   mergewin    New Unknown firefox
    Not      e4x Review  Unknown Dafydd Harries firefox

* project series:

  In order to see any blueprints, we must first assign a Mozilla Firefox
  blueprint to a series.

    >>> browser = setupBrowser(auth='Basic foo.bar@canonical.com:test')
    >>> browser.open('http://blueprints.launchpad.test/mozilla')
    >>> browser.getLink('svg-support').click()
    >>> browser.getLink('Propose as goal').click()
    >>> series_goal = browser.getControl('Series Goal')
    >>> series_goal.value = ['2']
    >>> browser.getControl('Continue').click()
    >>> browser.open('http://blueprints.launchpad.test/mozilla/+series/1.0')
    >>> specs = find_tag_by_id(browser.contents, 'speclisting')
    >>> print(extract_text(specs))
    Priority Blueprint Design Delivery Assignee Project Series Milestone
    High svg-support Approved Beta Available Carlos ... firefox 1.0
