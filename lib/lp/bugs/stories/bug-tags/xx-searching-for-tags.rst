Searching for bug tags
======================

On the advanced search page it's possible to search for a specific tag.

    >>> anon_browser.open("http://launchpad.test/ubuntu/+bugs?advanced=1")
    >>> anon_browser.getControl("Tags").value = "crash"
    >>> anon_browser.getControl("Search", index=0).click()

    >>> from lp.bugs.tests.bug import print_bugtasks
    >>> print_bugtasks(anon_browser.contents)
    9 Thunderbird crashes thunderbird (Ubuntu) Medium Confirmed
    10 another test bug linux-source-2.6.15 (Ubuntu) Medium New

If more than one tag is entered, bugs with any those tags will be
shown.

    >>> anon_browser.open("http://launchpad.test/ubuntu/+bugs?advanced=1")
    >>> anon_browser.getControl("Tags").value = "crash dataloss"
    >>> anon_browser.getControl("Search", index=0).click()
    >>> print_bugtasks(anon_browser.contents)
    9 Thunderbird crashes thunderbird (Ubuntu) Medium Confirmed
    10 another test bug linux-source-2.6.15 (Ubuntu) Medium New
    2 Blackhole Trash folder Ubuntu Medium New

If an invalid tag name is entered, an error message will be displayed.

    >>> anon_browser.open("http://launchpad.test/ubuntu/+bugs?advanced=1")
    >>> anon_browser.getControl("Tags").value = "!!invalid!!"
    >>> anon_browser.getControl("Search", index=0).click()

    >>> for tag in find_tags_by_class(anon_browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    '!!invalid!!' isn't a valid tag name. Tags must start with a letter
    or number and be lowercase. The characters "+", "-" and "." are also
    allowed after the first character.


Cross-Site Scripting, or XSS
----------------------------

The tags field and its related messages are properly escaped in order
to prevent XSS.

    >>> anon_browser.open("http://launchpad.test/ubuntu/+bugs?advanced=1")
    >>> anon_browser.getControl("Tags").value = (
    ...     '<script>alert("cheezburger");</script>'
    ... )
    >>> anon_browser.getControl("Search", index=0).click()

The value can be obtained correctly, which indicates that the markup
is parse-able:

    >>> anon_browser.getControl("Tags").value
    '<script>alert("cheezburger");</script>'

Indeed, the markup is valid and correctly escaped:

    >>> print(find_tag_by_id(anon_browser.contents, "field.tag").prettify())
    <input class="textType" id="field.tag"
           name="field.tag" size="20" type="text"
           value='&lt;script&gt;alert("cheezburger");&lt;/script&gt;'/>

The error message is also valid and correctly escaped:

    >>> for tag in find_tags_by_class(anon_browser.contents, "message"):
    ...     print(tag.prettify())
    ...
    <div class="message">
    '&lt;script&gt;alert("cheezburger");&lt;/script&gt;' isn't ...
    </div>

The script we tried to inject is not present, unescaped, anywhere in
the page:

    >>> '<script>alert("cheezburger");</script>' in anon_browser.contents
    False
