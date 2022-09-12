The Distribution Series Bugs Page
---------------------------------

The +bugs page for a distribution series presents some basic information the
bugs, as well as a listing.

    >>> anon_browser.open("http://bugs.launchpad.test/ubuntu/warty/+bugs")
    >>> anon_browser.title
    'Warty (4.10) : Bugs : Ubuntu'

    >>> find_tags_by_class(
    ...     anon_browser.contents, "buglisting-row"
    ... ) is not None
    True

The page has a link to see all open bugs.

    >>> anon_browser.getLink("Open bugs").click()
    >>> anon_browser.url
    'http://bugs.launchpad.test/ubuntu/warty/+bugs'
    >>> find_tags_by_class(
    ...     anon_browser.contents, "buglisting-row"
    ... ) is not None
    True

It also has a link to subscribe to bug mail.

    >>> user_browser.open("http://bugs.launchpad.test/ubuntu/warty")
    >>> user_browser.getLink("Subscribe to bug mail").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/ubuntu/warty/+subscribe


Bugs Fixed Elsewhere
--------------------

The Bugs frontpage includes the number of bugs that are fixed in some
other context.

    >>> anon_browser.open("http://bugs.launchpad.test/ubuntu/warty")
    >>> fixed_elsewhere_link = anon_browser.getLink("Bugs fixed elsewhere")

The link takes you to the list of the bugs fixed elsewhere.

    >>> fixed_elsewhere_link.click()
    >>> anon_browser.url
    'http://.../+bugs?field.status_upstream=resolved_upstream'

    >>> print(find_main_content(anon_browser.contents))
    <...
    <p>There are currently no open bugs.</p>
    ...


Expirable Bugs
--------------

The bugs page displays the number of Incomplete, unattended bugs that
can expire when the project has enabled bug expiration.

    >>> anon_browser.open("http://bugs.launchpad.test/ubuntu/warty")
    >>> expirable_bugs_link = anon_browser.getLink("Incomplete bugs")

The link goes to the expirable bugs page, where the anonymous user can
see which bugs will expire if they are not confirmed.

    >>> expirable_bugs_link.click()
    >>> print(anon_browser.title)
    Expirable bugs : Warty (4.10) : Bugs : Ubuntu

