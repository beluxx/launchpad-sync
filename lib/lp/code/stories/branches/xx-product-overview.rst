Latest branches
---------------

On the product overview page there is a portlet to show recently
registered branches.

    >>> def show_latest_branches(url):
    ...     """Show the latest branches portlet at `url`."""
    ...     browser.open(url)
    ...     branches = find_portlet(browser.contents, "Latest branches")
    ...     if branches is None:
    ...         print("No 'Latest branches' portlet found at %s" % (url,))
    ...         return
    ...     for list_item in branches.find_all("li"):
    ...         print(extract_text(list_item))
    ...

    >>> def make_branch_on_product(product, branch_name, person_name):
    ...     """Make a branch on `product`.
    ...
    ...     The name of the branch is `branch_name` and the display
    ...     name of the owner is `person_name`.
    ...     """
    ...     owner = factory.makePerson(displayname=person_name)
    ...     factory.makeProductBranch(
    ...         product=product, owner=owner, name=branch_name
    ...     )
    ...

First we make a product that has three branches registered on it.

    >>> login("no-priv@canonical.com")
    >>> product = factory.makeProduct()
    >>> make_branch_on_product(product, "apple", "Joe Bloggs")
    >>> make_branch_on_product(product, "bear", "Jane Doe")
    >>> make_branch_on_product(product, "cabbage", "Neil Armstrong")
    >>> logout()
