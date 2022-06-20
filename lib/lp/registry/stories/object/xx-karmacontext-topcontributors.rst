Top contributors
================

For products, projects and distributions, we have a portlet which displays
the top 5 overall contributors of that KarmaContext
(product/project/distribution).  Also, the menu contains a link to the
+topcontributors page, where we list the top overall contributors and the
top contributors by category (Bugs, Specs, Translation, etc).


Top contributors of a distribution
----------------------------------

The top contributors page can be reached from the top contributors portlet.

    >>> anon_browser.open('http://launchpad.test/ubuntu/')
    >>> find_tag_by_id(
    ...     anon_browser.contents, 'portlet-top-contributors') is not None
    True

    >>> anon_browser.getLink('More contributors').click()
    >>> print(anon_browser.title)
    Top Ubuntu Contributors...


Top contributors of a product
-----------------------------

The top contributors page can be reached from the top contributors portlet.

    >>> anon_browser.open('http://launchpad.test/firefox')
    >>> find_tag_by_id(
    ...     anon_browser.contents, 'portlet-top-contributors') is not None
    True

    >>> anon_browser.getLink('More contributors').click()
    >>> print(anon_browser.title)
    Top Mozilla Firefox Contributors...


Top contributors of a project group
-----------------------------------

The top contributors page can be reached from the top contributors portlet.

    >>> anon_browser.open('http://launchpad.test/mozilla')
    >>> find_tag_by_id(
    ...     anon_browser.contents, 'portlet-top-contributors') is not None
    True

    >>> anon_browser.getLink('More contributors').click()
    >>> print(anon_browser.title)
    Top The Mozilla Project Contributors...
