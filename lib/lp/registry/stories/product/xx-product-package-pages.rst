Product Packaging
=================

Launchpad can show you a product's packages by distribution, with links to
each.

    >>> anon_browser.open("http://launchpad.test/evolution/+packages")
    >>> print(anon_browser.title)
    Linked packages ...
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(anon_browser.contents, "distribution-series")
    ...     )
    ... )
    Distribution series  Source package        Version  Project series
    Warty (4.10)         evolution  Evolution           trunk series ...

    >>> anon_browser.getLink(url="/ubuntu/warty/+source/evolution").click()
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(anon_browser.contents, "maincontent").h1
    ...     )
    ... )
    evolution source package in Warty

It can also show the packages by product series. And if you have permission
(for example, you're the owner of the product), Launchpad lets you register
packages for each series. In this case, mark@example.com is the owner of
Evolution.

    >>> evo_owner = setupBrowser(auth="Basic mark@example.com:test")
    >>> evo_owner.open("http://launchpad.test/evolution/+packages")
    >>> print(evo_owner.title)
    Linked packages ...
    >>> print(
    ...     extract_text(find_tag_by_id(evo_owner.contents, "packages-trunk"))
    ... )
    Distribution  Distribution series  Source package  Version
    Ubuntu        Warty (4.10)         evolution                Remove...
    Ubuntu        Hoary (5.04)         evolution       1.0      Remove...

    >>> evo_owner.getLink(url="/ubuntu/hoary/+source/evolution") is not None
    True

Any logged in users can still see the links to create a packaging link.

    >>> user_browser.open("http://launchpad.test/evolution/+packages")
    >>> print(user_browser.getLink(url="/evolution/trunk/+ubuntupkg").url)
    http://launchpad.test/evolution/trunk/+ubuntupkg

    >>> anon_browser.open("http://launchpad.test/evolution/+packages")
    >>> anon_browser.getLink(url="/evolution/trunk/+ubuntupkg")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError


Deleting packaging links
------------------------

Packaging links can be deleted if they were created in error.

    >>> evo_owner.getLink(
    ...     url="/ubuntu/warty/+source/evolution/+remove-packaging"
    ... ).click()
    >>> print(evo_owner.title)
    Unlink an upstream project...
    >>> evo_owner.getControl("Unlink").click()
    >>> print(evo_owner.title)
    Linked packages...

    >>> print_feedback_messages(evo_owner.contents)
    Removed upstream association between Evolution trunk series and Warty.

    >>> print(
    ...     extract_text(find_tag_by_id(evo_owner.contents, "packages-trunk"))
    ... )
    Distribution  Distribution series  Source package  Version
    Ubuntu        Hoary (5.04)         evolution       1.0     Remove...
