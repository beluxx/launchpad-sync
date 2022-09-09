Check if the merge proposal badge is shown
==========================================

    >>> def branchSummary(browser):
    ...     table = find_tag_by_id(browser.contents, "branchtable")
    ...     for row in table.tbody.find_all("tr"):
    ...         cells = row.find_all("td")
    ...         first_cell = cells[0]
    ...         anchors = first_cell.find_all("a")
    ...         print(anchors[0].get("href"))
    ...         # Badges in the next cell
    ...         for img in cells[1].find_all("img"):
    ...             print(img["title"])
    ...


    >>> login("foo.bar@canonical.com")
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.product import IProductSet
    >>> bob = factory.makePerson(name="bob")
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> target = factory.makeProductBranch(
    ...     product=firefox, owner=bob, name="target"
    ... )
    >>> source = factory.makeProductBranch(
    ...     owner=bob, product=firefox, name="review"
    ... )
    >>> proposal = source.addLandingTarget(bob, target)
    >>> logout()

    >>> browser.open("http://code.launchpad.test/firefox/+branches")
    >>> branchSummary(browser)
    /~bob/firefox/review
    Has a merge proposal
    /~bob/firefox/target
    /~mark/firefox/release-0.8
    /~mark/firefox/release-0.9
    /~mark/firefox/release--0.9.1
    /~mark/firefox/release-0.9.2
    Linked to a bug

