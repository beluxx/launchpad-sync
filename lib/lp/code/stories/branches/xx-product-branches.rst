================
Product Branches
================

    >>> from lp.code.tests.branch_helper import reset_all_branch_last_modified
    >>> reset_all_branch_last_modified()


Product branch summaries
========================

Branch listings for products now have a summary shown at the top of
the page before the listing table itself.

What is shown depends on the how many branches are in the project,
who they are owned by, whether or not the branch officially uses
Launchpad code, whether or not there is a development focus branch,
whether or not there are any download files specified for the product.


No branches
===========

If there are no branches a message offering options is shown.

The default page for the code rootsite on a product is the code
overview page.

    >>> browser.open("http://code.launchpad.test/applets")
    >>> print(browser.title)
    Code : Gnome Applets

If there are not any branches, a helpful message is shown.

    >>> def get_summary(browser):
    ...     return find_tag_by_id(browser.contents, "branch-summary")
    ...
    >>> summary = get_summary(browser)
    >>> print(extract_text(summary))
    Launchpad does not know where Gnome Applets
    hosts its code.
    There are no branches for Gnome Applets
    in Launchpad.
    Getting started
    with code hosting in Launchpad.

    If there are Bazaar branches of Gnome Applets in a publicly
      accessible location, Launchpad can act as a mirror of the branch
      by registering a Mirrored branch. Read more.
    Launchpad can also act as a primary location for Bazaar branches of
      Gnome Applets. Read more.
    Launchpad can import code from CVS, Subversion or Git
      into Bazaar branches. Read more...

The 'Help' links go to the help wiki.

    >>> for anchor in summary.find_all("a"):
    ...     print(anchor["href"])
    ...
    https://help.launchpad.net/Code


Link to the product downloads
=============================

It is possible that a new person coming to the code tab would be interested
in downloads that may have been added for the product.

    >>> browser.open("http://code.launchpad.test/netapplet")
    >>> print(extract_text(get_summary(browser)))
    Launchpad does not know where NetApplet hosts its code...
    There are no branches for NetApplet in Launchpad.
    ...
    There are download files available for NetApplet.
    >>> browser.getLink("download files")
    <Link...url='http://launchpad.test/netapplet/+download'>



Development focus branches
==========================

If a development focus branch is set and browsable, the user is shown
a link to browse the code and a simple command line to get the branch.
If the branch is not browsable (in this case, it has no revisions but
it could be private or remote), only the command to get the branch is
shown.

    >>> browser.open("http://code.launchpad.test/evolution")
    >>> summary = get_summary(browser)
    >>> print(extract_text(get_summary(browser)))
    Evolution hosts its code externally.
    You can learn more at the project's web page.
    Launchpad imports the master branch and you can create branches from
    it.
    You can
    get a copy of the development focus branch
    using the command:
    bzr branch lp://dev/evolution

    >>> links = summary.find_all("a")

Both active reviews and approved merges are links allowing the user to
go to listing views.


Initial branch listing
======================

The initial branch listing has the following branches in order:
 * The current development focus branch
 * Other series branches (as long as not Merged or Abandoned)
 * Other non-series branches ordered by most recently modified

If a branch is associated with more than one series, it is only shown
once, but both series are shown in the listing.

    >>> admin_browser.open("http://launchpad.test/firefox/trunk/+setbranch")
    >>> admin_browser.getControl("Branch:").value = "~name12/firefox/main"
    >>> admin_browser.getControl("Update").click()
    >>> admin_browser.open("http://launchpad.test/firefox/1.0/+setbranch")
    >>> admin_browser.getControl("Branch:").value = "~name12/firefox/main"
    >>> admin_browser.getControl("Update").click()

    >>> browser.open("http://code.launchpad.test/firefox")
    >>> table = find_tag_by_id(browser.contents, "branchtable")
    >>> for row in table.tbody.find_all("tr")[0:2]:
    ...     print(extract_text(row))
    lp://dev/firefox
      Series: trunk, 1.0                     Development ...
    lp://dev/~mark/firefox/release--0.9.1  Development ...

Firstly lets associate release--0.9.1 with the 1.0 series.

    >>> admin_browser.open("http://launchpad.test/firefox/1.0/+setbranch")
    >>> admin_browser.getControl(
    ...     "Branch:"
    ... ).value = "~mark/firefox/release--0.9.1"
    >>> admin_browser.getControl("Update").click()

    >>> browser.open("http://code.launchpad.test/firefox")
    >>> table = find_tag_by_id(browser.contents, "branchtable")
    >>> for row in table.tbody.find_all("tr")[0:2]:
    ...     print(extract_text(row))
    lp://dev/firefox
      Series: trunk                 Development ...
    lp://dev/firefox/1.0
      Series: 1.0                   Development ...

If series branches are marked as Abandoned they will not show up on the
default listings.

    >>> admin_browser.open(
    ...     "http://code.launchpad.test/~name12/firefox/main/+edit"
    ... )
    >>> admin_browser.getControl("Abandoned").click()
    >>> admin_browser.getControl("Change Branch").click()
    >>> admin_browser.open(
    ...     "http://code.launchpad.test/~mark/firefox/release--0.9.1/+edit"
    ... )
    >>> admin_browser.getControl("Abandoned").click()
    >>> admin_browser.getControl("Change Branch").click()

    >>> browser.open("http://code.launchpad.test/firefox")
    >>> table = find_tag_by_id(browser.contents, "branchtable")
    >>> for row in table.tbody.find_all("tr")[0:2]:
    ...     print(extract_text(row))
    lp://dev/~mark/firefox/release-0.8     Development ...


Involvement portlet
===================

There are two links in the side portlet:
'Import a branch' and 'Configure code hosting'
The links are only shown if the user has permission to perform the task.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.testing import celebrity_logged_in
    >>> from lp.testing.factory import LaunchpadObjectFactory
    >>> factory = LaunchpadObjectFactory()
    >>> login(ANONYMOUS)
    >>> product = getUtility(IProductSet).getByName("firefox")
    >>> owner = product.owner
    >>> old_branch = product.development_focus.branch
    >>> ignored = login_person(product.owner)
    >>> product.development_focus.branch = None
    >>> def print_links(browser):
    ...     links = find_tag_by_id(browser.contents, "involvement")
    ...     if links is None:
    ...         print("None")
    ...         return
    ...     for link in links.find_all("a"):
    ...         print(extract_text(link))
    ...

    >>> def setup_code_hosting(productname):
    ...     with celebrity_logged_in("admin"):
    ...         product = getUtility(IProductSet).getByName(productname)
    ...         branch = factory.makeProductBranch(product=product)
    ...         product.development_focus.branch = branch
    ...

The involvement portlet is not shown if the product does not have code
hosting configured or if it is not using Launchpad.

    >>> print(product.codehosting_usage.name)
    UNKNOWN
    >>> logout()
    >>> admin_browser.open("http://code.launchpad.test/firefox")
    >>> print_links(admin_browser)
    None

    >>> setup_code_hosting("firefox")
    >>> login(ANONYMOUS)
    >>> print(product.codehosting_usage.name)
    LAUNCHPAD
    >>> logout()
    >>> admin_browser.open("http://code.launchpad.test/firefox")
    >>> print_links(admin_browser)
    Import a branch
    Configure Code

The owner of the project sees the links for the activities they can
perform, everything except defining branch visibility.

    >>> owner_browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> owner_browser.open("http://code.launchpad.test/firefox")
    >>> print_links(owner_browser)
    Import a branch
    Configure Code

And a regular user can only register and import branches.

    >>> user_browser.open("http://code.launchpad.test/firefox")
    >>> print_links(user_browser)
    Import a branch

If the product specifies that it officially uses Launchpad code, then
the 'Import a branch' button is still shown.

    >>> ignored = login_person(owner)
    >>> product.development_focus.branch = old_branch
    >>> logout()
    >>> browser.open("http://code.launchpad.test/firefox")
    >>> print_links(browser)
    Import a branch


The statistics portlet
======================

The text that is shown giving a summary of the number of branches
shows correct singular and plural forms.

    >>> from lp.testing import normalize_whitespace
    >>> def get_stats_portlet(browser):
    ...     return find_tag_by_id(
    ...         browser.contents, "portlet-product-branchstatistics"
    ...     )
    ...
    >>> def print_portlet(product):
    ...     browser.open("http://code.launchpad.test/%s" % product)
    ...     portlet = get_stats_portlet(browser)
    ...     if portlet is None:
    ...         print("None")
    ...     else:
    ...         print(normalize_whitespace(extract_text(portlet)))
    ...

    >>> setup_code_hosting("gnome-terminal")
    >>> print_portlet("gnome-terminal")
    See all merge proposals.
    GNOME Terminal has 9 active branches owned by 2 people and 2 teams.
    There were 0 commits in the last month.

    >>> from lp.testing import ANONYMOUS, login, logout
    >>> login(ANONYMOUS)
    >>> fooix = factory.makeProduct("fooix")
    >>> ignored = factory.makeProductBranch(fooix)
    >>> logout()
    >>> setup_code_hosting("fooix")
    >>> print_portlet("fooix")
    See all merge proposals.
    Fooix has 2 active branches owned by 2 people.
    There were 0 commits in the last month.

    >>> print_portlet("evolution")
    See all merge proposals.
    Evolution has 3 active branches owned by 1 person and 1 team.
    There were 0 commits in the last month.

    >>> login(ANONYMOUS)
    >>> dinky = factory.makeProduct("dinky")
    >>> logout()
    >>> setup_code_hosting("dinky")
    >>> print_portlet("dinky")
    See all merge proposals.
    Dinky has 1 active branch owned by 1 person.
    There were 0 commits in the last month.


Product has Branches, but none initially visible
================================================

It is a bit of an edge case, but if there are branches for a product but all
of them are either merged or abandoned and there is no development focus
branch, then they will not appear on the initial branch listing and
the portlets will not be shown.

    >>> admin_browser.open(
    ...     "http://code.launchpad.test/~carlos/iso-codes/0.35"
    ... )
    >>> admin_browser.getLink("Change branch details").click()
    >>> admin_browser.getControl("Abandoned").click()
    >>> admin_browser.getControl("Change Branch").click()

    >>> print_portlet("iso-codes")
    None

    >>> message = find_tag_by_id(browser.contents, "no-branch-message")
    >>> print(extract_text(message))
    There are branches registered for iso-codes but none of them match the
    current filter criteria for this page. Try filtering on "Any Status".


Getting to the branch listing for a product
===========================================

If there are branches, but they do not fit with the appropriate filter
we are given a different message.

    >>> browser.open(
    ...     "http://code.launchpad.test/firefox/+branches"
    ...     "?field.lifecycle=Mature"
    ... )
    >>> message = find_tag_by_id(browser.contents, "no-branch-message")
    >>> print(extract_text(message))
    There are branches registered for Mozilla Firefox but none of them match
    the current filter criteria for this page. Try filtering on "Any Status".
