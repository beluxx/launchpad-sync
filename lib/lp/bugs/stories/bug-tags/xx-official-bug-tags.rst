fficial Bug Tags
=================

Project admins can manage the official bug tags by following a link
from the main bug page.

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/firefox')
    >>> admin_browser.getLink('Edit official tags').click()
    >>> print(admin_browser.url)
    http://bugs.launchpad.test/firefox/+manage-official-tags

Tags are entered into a textarea as a list of white-spaces separated
words.

    >>> admin_browser.getControl('Official Bug Tags').value = 'foo bar'
    >>> admin_browser.getControl('Save').click()
    >>> print(admin_browser.url)
    http://bugs.launchpad.test/firefox
    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/firefox/+manage-official-tags')
    >>> print(admin_browser.getControl('Official Bug Tags').value)
    bar foo

The link as well as the edit form is only available for products and
distributions but not for other bug targets.

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/firefox/1.0')
    >>> print(admin_browser.getLink('Edit official tags'))
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/firefox/1.0/+manage-official-tags')
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...

The link as well as the edit form is only available for project
administrators but not for ordinary users.

    >>> browser.open('http://bugs.launchpad.test/firefox')
    >>> print(browser.getLink('Edit official tags'))
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> browser.open(
    ...     'http://bugs.launchpad.test/firefox/+manage-official-tags')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

The link is also available for the bug supervisor.

    >>> from lp.testing.sampledata import ADMIN_EMAIL
    >>> from lp.testing import login, logout
    >>> login(ADMIN_EMAIL)
    >>> supervisor = factory.makePerson()
    >>> youbuntu = factory.makeProduct(name='youbuntu',
    ...     bug_supervisor=supervisor,
    ...     official_malone=True)
    >>> bug_super_browser = setupBrowser(
    ...     auth='Basic %s:test' % supervisor.preferredemail.email)
    >>> logout()
    >>> bug_super_browser.open(
    ...     'http://bugs.launchpad.test/youbuntu')
    >>> bug_super_browser.getLink('Edit official tags').click()
    >>> print(bug_super_browser.url)
    http://bugs.launchpad.test/youbuntu/+manage-official-tags

The bug supervisor can also set the tags for the product.

    >>> bug_super_browser.getControl('Official Bug Tags').value = 'foo bar'
    >>> bug_super_browser.getControl('Save').click()
    >>> print(bug_super_browser.url)
    http://bugs.launchpad.test/youbuntu
    >>> bug_super_browser.open(
    ...     'http://bugs.launchpad.test/youbuntu/+manage-official-tags')
    >>> print(bug_super_browser.getControl('Official Bug Tags').value)
    bar foo

Official Tags on Bug Pages
--------------------------

Official tags are displayed using a different style from unofficial ones.
They are grouped together at the beginning of the list.

    >>> from lp.services.webapp import canonical_url
    >>> from lp.bugs.tests.bug import print_bug_tag_anchors
    >>> import transaction
    >>> login('foo.bar@canonical.com')
    >>> gfoobar = factory.makeProduct(name='gfoobar')
    >>> gfoobar.official_bug_tags = [u'alpha', u'charlie']
    >>> gfoobar_bug = factory.makeBug(target=gfoobar)
    >>> gfoobar_bug.tags = [u'alpha', u'bravo', u'charlie', u'delta']
    >>> gfoobar_bug_url = canonical_url(gfoobar_bug)
    >>> transaction.commit()
    >>> logout()

    >>> browser.open(gfoobar_bug_url)
    >>> tags_div = find_tag_by_id(browser.contents, 'bug-tags')
    >>> print_bug_tag_anchors(tags_div.find_all('a'))
    official-tag alpha
    official-tag charlie
    unofficial-tag bravo
    unofficial-tag delta


Entering Official Tags
----------------------

Available Official Tags in Javascript
.....................................

The list of available official tags is present on the page as a Javascript
variable. This list is used to initialize the tag entry widget. The list
comprises of the official tags of all targets for which the bug has a task.

    >>> login('foo.bar@canonical.com')
    >>> product1 = factory.makeProduct()
    >>> product2 = factory.makeProduct()
    >>> product1.official_bug_tags = [u'eenie', u'meenie']
    >>> product2.official_bug_tags = [u'miney', u'moe']
    >>> bug = factory.makeBug(target=product1)
    >>> bug.addTask(target=product2, owner=factory.makePerson())
    <BugTask ...>
    >>> bug_url = canonical_url(bug)
    >>> transaction.commit()
    >>> logout()

    >>> browser.open(bug_url)
    >>> js = find_tag_by_id(browser.contents, 'available-official-tags-js')
    >>> print(js)
    <script...>var available_official_tags =
    ["eenie", "meenie", "miney", "moe"];</script>
