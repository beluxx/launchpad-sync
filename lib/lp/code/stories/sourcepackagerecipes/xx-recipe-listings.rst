====================
Recipe Listing Pages
====================

Pages that want to display lists of recipes use the recipe-listing
page template, and views derived from RecipeListingView.

    >>> def print_recipe_listing_head(browser):
    ...     table = find_tag_by_id(browser.contents, 'recipetable')
    ...     for row in table.thead.find_all('tr'):
    ...         print(extract_text(row))

    >>> def print_recipe_listing_contents(browser):
    ...     table = find_tag_by_id(browser.contents, 'recipetable')
    ...     for row in table.tbody.find_all('tr'):
    ...         print(extract_text(row))


Branch Recipe Listings
======================

Create a sample branch.

    >>> login('foo.bar@canonical.com')
    >>> recipeless_branch = factory.makeBranch()
    >>> recipeless_branch_url = canonical_url(recipeless_branch)
    >>> logout()
    >>> nopriv_browser = setupBrowser(
    ...     auth='Basic nopriv@canonical.com:test')

Create a new sample branch, but this time create some source package branches
to go along with them.

    >>> login('foo.bar@canonical.com')
    >>> branch = factory.makeBranch()
    >>> recipe1 = factory.makeSourcePackageRecipe(branches=[branch])
    >>> recipe2 = factory.makeSourcePackageRecipe(branches=[branch])
    >>> recipe3 = factory.makeSourcePackageRecipe(branches=[branch])

Keep these urls, including the product url.  We'll use these later.

    >>> branch_url = canonical_url(branch)
    >>> product_url = canonical_url(branch.product)

    >>> logout()

Since there are 3 recipes associated with this branch now, the link should now
read "3 recipes." Let's click through.

    >>> nopriv_browser.open(branch_url)
    >>> nopriv_browser.getLink('3 recipes').click()
    >>> print(nopriv_browser.url)  # noqa
    http://code.launchpad.test/~person-name.../product-name.../branch.../+recipes

The "Base Source" column should not be shown.

    >>> print_recipe_listing_head(nopriv_browser)
    Name
    Owner
    Registered

The recipe listing page should have a list of all the recipes the branch is
a base for.

    >>> print_recipe_listing_contents(nopriv_browser)
    spr-name... Person-name...
    spr-name... Person-name...
    spr-name... Person-name...


Git Recipe Listings
===================

Create a new sample repository, some branches in it, and some source package
recipes to go along with them.

    >>> login('foo.bar@canonical.com')
    >>> repository = factory.makeGitRepository()
    >>> ref1, ref2, ref3 = factory.makeGitRefs(
    ...     repository=repository,
    ...     paths=[u"refs/heads/a", u"refs/heads/b", u"refs/heads/c"])
    >>> recipe1a = factory.makeSourcePackageRecipe(branches=[ref1])
    >>> recipe1b = factory.makeSourcePackageRecipe(branches=[ref1])
    >>> recipe2 = factory.makeSourcePackageRecipe(branches=[ref2])
    >>> recipe3 = factory.makeSourcePackageRecipe(branches=[ref3])

Keep these urls, including the target url.  We'll use these later.

    >>> repository_url = canonical_url(repository)
    >>> ref1_url = canonical_url(ref1)
    >>> target_url = canonical_url(repository.target)

    >>> logout()

Since there are 4 recipes associated with this repository now, the link
should now read "4 recipes."  Let's click through.

    >>> nopriv_browser.open(repository_url)
    >>> nopriv_browser.getLink('4 recipes').click()
    >>> print(nopriv_browser.url)  # noqa
    http://code.launchpad.test/~person-name.../product-name.../+git/gitrepository.../+recipes

The "Base Source" column should not be shown.

    >>> print_recipe_listing_head(nopriv_browser)
    Name
    Owner
    Registered

The recipe listing page should have a list of all the recipes the repository
is a base for.

    >>> print_recipe_listing_contents(nopriv_browser)
    spr-name... Person-name...
    spr-name... Person-name...
    spr-name... Person-name...
    spr-name... Person-name...

If we start from one of the branches instead, then only two recipes are
listed.

    >>> from lp.code.tests.helpers import GitHostingFixture

    >>> with GitHostingFixture():
    ...     nopriv_browser.open(ref1_url)
    >>> nopriv_browser.getLink('2 recipes').click()
    >>> print(nopriv_browser.url)  # noqa
    http://code.launchpad.test/~person-name.../product-name.../+git/gitrepository.../+ref/a/+recipes

    >>> print_recipe_listing_head(nopriv_browser)
    Name
    Owner
    Registered

    >>> print_recipe_listing_contents(nopriv_browser)
    spr-name... Person-name...
    spr-name... Person-name...


Product Recipe Listings
=======================

Let's use the product from the former branch test.

    >>> nopriv_browser.open(product_url)
    >>> nopriv_browser.getLink('View source package recipes').click()
    >>> print(nopriv_browser.url)
    http://code.launchpad.test/product-name.../+recipes

    >>> print_recipe_listing_head(nopriv_browser)
    Name
    Owner
    Base Source
    Registered

The listings should now show all recipes whose base branch is a branch from
this product.

    >>> print_recipe_listing_contents(nopriv_browser)
    spr-name... Person-name... lp://dev/... ...
    spr-name... Person-name... lp://dev/... ...
    spr-name... Person-name... lp://dev/... ...

The same thing works for the target of the former Git repository test.

    >>> nopriv_browser.open(target_url)
    >>> nopriv_browser.getLink('View source package recipes').click()
    >>> print(nopriv_browser.url)
    http://code.launchpad.test/product-name.../+recipes

    >>> print_recipe_listing_head(nopriv_browser)
    Name
    Owner
    Base Source
    Registered

    >>> print_recipe_listing_contents(nopriv_browser)
    spr-name... Person-name... lp:~.../+git/... ...
    spr-name... Person-name... lp:~.../+git/... ...
    spr-name... Person-name... lp:~.../+git/... ...
    spr-name... Person-name... lp:~.../+git/... ...


Person Recipe Listings
======================

Create a person, make some recipes for that person.

    >>> login('foo.bar@canonical.com')
    >>> person = factory.makePerson()
    >>> person_url = canonical_url(person)
    >>> recipe1 = factory.makeSourcePackageRecipe(owner=person)
    >>> recipe2 = factory.makeSourcePackageRecipe(owner=person)
    >>> recipe3 = factory.makeSourcePackageRecipe(owner=person)
    >>> logout()

    >>> nopriv_browser.open(person_url)
    >>> nopriv_browser.getLink('View source package recipes').click()
    >>> print(nopriv_browser.url)
    http://code.launchpad.test/~person-name.../+recipes

The "Owner" section should be missing.

    >>> print_recipe_listing_head(nopriv_browser)
    Name
    Base Source
    Registered

The listings should now show all recipes whose base branch is a branch from
this product.

    >>> print_recipe_listing_contents(nopriv_browser)
    spr-name... lp://dev/... ...
    spr-name... lp://dev/... ...
    spr-name... lp://dev/... ...
