On the bug listings page there is a portlet which shows all tags that
have been used for bugs in this context. The content of this portlet is loaded
using Javascript after page load.

    >>> anon_browser.open("http://launchpad.test/ubuntu/+bugs")
    >>> anon_browser.getLink(id="tags-content-link").click()
    >>> print(anon_browser.url)
    http://launchpad.test/ubuntu/+bugtarget-portlet-tags-content
    >>> tags_portlet = find_tags_by_class(anon_browser.contents, "data-list")[
    ...     0
    ... ]
    >>> for a_tag in tags_portlet("a"):
    ...     print(a_tag.decode_contents())
    ...
    crash
    dataloss
    pebcak

If we click on a tag, only bugs with that tag are displayed:

    >>> anon_browser.getLink(url="crash").click()
    >>> anon_browser.url
    'http://launchpad.test/ubuntu/+bugs?field.tag=crash'

    >>> from lp.bugs.tests.bug import print_bugtasks
    >>> print_bugtasks(anon_browser.contents)
    9 Thunderbird crashes
      thunderbird (Ubuntu) Medium Confirmed
    10 another test bug
       linux-source-2.6.15 (Ubuntu) Medium New

Clicking on a tags shows only bugs that have that specific tag, so if
we click on another tag, the bugs that were shown previously won't be
shown.

    >>> anon_browser.open(
    ...     "http://launchpad.test/ubuntu/+bugtarget-portlet-tags-content"
    ... )
    >>> anon_browser.getLink("dataloss").click()
    >>> anon_browser.url
    'http://launchpad.test/ubuntu/+bugs?field.tag=dataloss'
    >>> print_bugtasks(anon_browser.contents)
    2 Blackhole Trash folder
      Ubuntu Medium New

We update bug #2's status to Invalid to demonstrate that the portlet body is
not available when no tags are relevant:

    >>> admin_browser.open("http://bugs.launchpad.test/tomcat/+bug/2")
    >>> admin_browser.getControl("Status", index=0).value = ["Invalid"]
    >>> admin_browser.getControl("Save Changes", index=0).click()

    >>> anon_browser.open(
    ...     "http://launchpad.test/tomcat/+bugtarget-portlet-tags-content"
    ... )
    >>> print(extract_text(anon_browser.contents))
    Tags
