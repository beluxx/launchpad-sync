Searching by tags
=================

The advanced bug search allows searching for bugs by the tags they are
tagged with. It is possible to search either inclusively (for bugs
tagged with any of the specified tags), or exclusively (only for bugs
tagged with all the specified tags).

First, we create some bugs.

    >>> from zope.component import getUtility
    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.testing import login, logout

    >>> login("no-priv@canonical.com")
    >>> firefox = getUtility(IProductSet).get(4)
    >>> foobar = getUtility(IPersonSet).getByName("name16")

The first bug is tagged with both 'test-tag-1' and 'test-tag-2'.

    >>> params = CreateBugParams(
    ...     title="test bug a", comment="test bug a", owner=foobar
    ... )
    >>> test_bug_a = firefox.createBug(params)
    >>> test_bug_a.tags = ["test-tag-1", "test-tag-2"]

The second bug is tagged with only 'test-tag-1'.

    >>> params = CreateBugParams(
    ...     title="test bug b", comment="test bug b", owner=foobar
    ... )
    >>> test_bug_b = firefox.createBug(params)
    >>> test_bug_b.tags = ["test-tag-1"]

    >>> logout()

We go to the global bug search page and search for bugs with all the tags.
Only 'test bug a' is returned.

    >>> anon_browser.open("http://bugs.launchpad.test/bugs/+bugs?advanced=1")
    >>> anon_browser.getControl(
    ...     name="field.tag"
    ... ).value = "test-tag-1 test-tag-2"
    >>> anon_browser.getControl(name="field.tags_combinator").value = ["ALL"]
    >>> anon_browser.getControl("Search", index=1).click()
    >>> "test bug a" in anon_browser.contents
    True
    >>> "test bug b" in anon_browser.contents
    False

We go to the bug search page and search for bugs with any of the tags.
Both bugs are returned.

    >>> anon_browser.open("http://launchpad.test/firefox/+bugs?advanced=1")
    >>> anon_browser.getControl(
    ...     name="field.tag"
    ... ).value = "test-tag-1 test-tag-2"
    >>> anon_browser.getControl(name="field.tags_combinator").value = ["ANY"]
    >>> anon_browser.getControl("Search", index=1).click()
    >>> "test bug a" in anon_browser.contents
    True
    >>> "test bug b" in anon_browser.contents
    True

Same works for user related bugs:

    >>> anon_browser.open("http://launchpad.test/~name16/+bugs?advanced=1")
    >>> anon_browser.getControl(
    ...     name="field.tag"
    ... ).value = "test-tag-1 test-tag-2"
    >>> anon_browser.getControl(name="field.tags_combinator").value = ["ANY"]
    >>> anon_browser.getControl("Search", index=1).click()
    >>> "test bug a" in anon_browser.contents
    True
    >>> "test bug b" in anon_browser.contents
    True

When we search for bugs with all the tags, though, only the first bug is
returned, since it's the only bug with both tags.

    >>> anon_browser.open("http://launchpad.test/firefox/+bugs?advanced=1")
    >>> anon_browser.getControl(
    ...     name="field.tag"
    ... ).value = "test-tag-1 test-tag-2"
    >>> anon_browser.getControl(name="field.tags_combinator").value = ["ALL"]
    >>> anon_browser.getControl("Search", index=1).click()
    >>> "test bug a" in anon_browser.contents
    True
    >>> "test bug b" in anon_browser.contents
    False

And also for user related bugs:

    >>> anon_browser.open("http://launchpad.test/~name16/+bugs?advanced=1")
    >>> anon_browser.getControl(
    ...     name="field.tag"
    ... ).value = "test-tag-1 test-tag-2"
    >>> anon_browser.getControl(name="field.tags_combinator").value = ["ALL"]
    >>> anon_browser.getControl("Search", index=1).click()
    >>> "test bug a" in anon_browser.contents
    True
    >>> "test bug b" in anon_browser.contents
    False
