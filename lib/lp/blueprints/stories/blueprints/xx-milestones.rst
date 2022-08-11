Specifications and Milestones
=============================

Let's target a blueprint to the 1.0 milestone of Mozilla. Before we do this,
the milestone page lists one feature targeted already, and no bugs:

    >>> admin_browser.open('http://launchpad.test/firefox/+milestone/1.0')
    >>> tag = find_tag_by_id(admin_browser.contents, 'specification-count')
    >>> print(extract_text(tag))
    1 blueprint

We'll target the "canvas" blueprint. Each blueprint has a separate page for
milestone targeting.

    >>> admin_browser.open(
    ...     'http://blueprints.launchpad.test/firefox/+spec/canvas')
    >>> admin_browser.getLink('Target milestone').click()
    >>> print(admin_browser.title)
    Target to a milestone : Support <canvas> Objects :
    Blueprints : Mozilla Firefox
    >>> back_link = admin_browser.getLink('Support <canvas> Objects')
    >>> back_link.url
    'http://blueprints.launchpad.test/firefox/+spec/canvas'

Now, we choose a milestone from the list.

    >>> admin_browser.getControl('Milestone').displayOptions
    ['(nothing selected)', 'Mozilla Firefox 1.0']
    >>> admin_browser.getControl('Milestone').value = ['1']
    >>> admin_browser.getControl('Status Whiteboard').value = 'foo'
    >>> admin_browser.getControl('Change').click()

We expect to be redirected to the spec home page.

    >>> admin_browser.url
    'http://blueprints.launchpad.test/firefox/+spec/canvas'

And on that page, we expect to see that the spec is targeted to the 1.0
milestone.

    >>> print(find_main_content(admin_browser.contents))
    <...Milestone target:...
    <.../firefox/+milestone/1.0...

    >>> print(admin_browser.getLink('1.0').url)
    http://launchpad.test/firefox/+milestone/1.0

    >>> admin_browser.getLink('1.0').click()
    >>> print(admin_browser.getLink('Support <canvas> Objects').url)
    http://blueprints.launchpad.test/firefox/+spec/canvas

The count of targeted features has also updated.

    >>> content = find_main_content(admin_browser.contents)
    >>> tag = find_tag_by_id(admin_browser.contents, 'specification-count')
    >>> print(extract_text(tag))
    2 blueprints
