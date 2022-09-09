Users can see bugs tags on the bug page.

    >>> user_browser.open("http://bugs.launchpad.test/firefox/+bug/1")
    >>> user_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'
    >>> print(extract_text(find_tag_by_id(user_browser.contents, "bug-tags")))
    Add tags  Tag help

Let's specify some tags:

    >>> user_browser.getLink("Add tags").click()
    >>> tags = user_browser.getControl("Tags")
    >>> tags.value
    ''

If we enter an invalid tag name, we'll get an error.

    >>> tags.value = "!!invalid!! foo"
    >>> user_browser.getControl("Change").click()

    >>> for tag in find_tags_by_class(user_browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There is 1 error.
    '!!invalid!!' isn't a valid tag name. Tags must start with a letter
    or number and be lowercase. The characters "+", "-" and "." are also
    allowed after the first character.

Let's specify two valid tags.

    >>> tags = user_browser.getControl("Tags")
    >>> tags.value = "bar foo"
    >>> user_browser.getControl("Change").click()


Now the tags will be displayed on the bug page:

    >>> "Tags:" in user_browser.contents
    True
    >>> "foo" in user_browser.contents
    True
    >>> "bar" in user_browser.contents
    True

Simply changing the ordering of the bug tags won't cause anything to
happen.

    >>> user_browser.open("http://bugs.launchpad.test/firefox/+bug/1/+edit")
    >>> tags = user_browser.getControl("Tags")
    >>> tags.value
    'bar foo'

    >>> tags.value = "foo bar"
    >>> user_browser.getControl("Change").click()
    >>> user_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'

Let's delete the tags we added.

    >>> user_browser.open("http://bugs.launchpad.test/firefox/+bug/1/+edit")
    >>> user_browser.getControl("Tags").value
    'bar foo'
    >>> user_browser.getControl("Tags").value = ""
    >>> user_browser.getControl("Change").click()
    >>> user_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'

If we look at a bug having tags, the displayed tags are links, linking
to the list of all bugs having that tag in this context.

    >>> anon_browser.open("http://bugs.launchpad.test/ubuntu/+bug/2")
    >>> anon_browser.url
    'http://bugs.launchpad.test/ubuntu/+bug/2'

    >>> anon_browser.getLink("dataloss").click()
    >>> anon_browser.url
    'http://bugs.launchpad.test/ubuntu/+bugs?field.tag=dataloss'

    >>> from lp.bugs.tests.bug import print_bugtasks
    >>> print_bugtasks(anon_browser.contents)
    2 Blackhole Trash folder Ubuntu Medium New
