Code imports
============

The sample data only contains imports that target Bazaar, but we'll create
another couple that target Git as well before we start.

    >>> from zope.component import getUtility
    >>> from lp.code.enums import TargetRevisionControlSystems
    >>> from lp.code.tests.helpers import GitHostingFixture
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.testing import login, logout

    >>> login("test@canonical.com")
    >>> name12 = getUtility(IPersonSet).getByName("name12")
    >>> with GitHostingFixture():
    ...     _ = factory.makeCodeImport(
    ...         registrant=name12,
    ...         context=getUtility(IProductSet).getByName("gnome-terminal"),
    ...         branch_name="gnome-terminal",
    ...         git_repo_url="git://git.gnome.org/gnome-terminal",
    ...         target_rcs_type=TargetRevisionControlSystems.GIT,
    ...     )
    ...     _ = factory.makeCodeImport(
    ...         registrant=name12,
    ...         context=getUtility(IProductSet).getByName("evolution"),
    ...         branch_name="evolution",
    ...         git_repo_url="https://git.gnome.org/browse/evolution",
    ...         target_rcs_type=TargetRevisionControlSystems.GIT,
    ...     )
    ...
    >>> logout()

The code imports overview page is linked off the main code page.

    >>> browser.open("http://code.launchpad.test")
    >>> browser.getLink("3 imported branches").click()
    >>> print(browser.title)
    Code Imports

Any user can look at the current list of imports.

    >>> anon_browser.open("http://code.launchpad.test/+code-imports")
    >>> print(anon_browser.title)
    Code Imports

There are two CodeImports in the sample data and they both show up in
the page, as well as the two we created above:

    >>> table = find_tag_by_id(browser.contents, "code-import-listing")
    >>> names = [extract_text(tr.td) for tr in table.tbody("tr")]
    >>> for name in names:
    ...     print(name)
    ...
    ~vcs-imports/gnome-terminal/import
    ~vcs-imports/evolution/import
    ~name12/gnome-terminal/+git/gnome-terminal
    ~name12/evolution/+git/evolution

If we click on the code import's name, we go to the associated branch
for that import:

    >>> browser.getLink("~vcs-imports/gnome-terminal/import").click()
    >>> browser.url
    'http://code.launchpad.test/~vcs-imports/gnome-terminal/import'


Filtering the code import list
==============================

The code import listing is filterable, on review status, source type, and
target type.  There are no invalid imports in the sample data, so if we
filter just on them we'll see the "no imports found" message.  It is worth
ensuring that the control for filtering on review status reads "Any" by
default, as the code that ensures this is poking at Zope 3 internals a bit.

    >>> browser.open("http://code.launchpad.test/+code-imports")
    >>> control = browser.getControl(name="field.review_status")
    >>> control.displayValue
    ['Any']
    >>> control.displayValue = ["Invalid"]
    >>> browser.getControl(name="submit").click()
    >>> print(extract_text(find_tag_by_id(browser.contents, "no-imports")))
    No matching code imports found.

Of course selecting the "Any" filtering option ensures that all
imports appear again.

    >>> browser.getControl(name="field.review_status").displayValue = ["Any"]
    >>> browser.getControl(name="submit").click()
    >>> table = find_tag_by_id(browser.contents, "code-import-listing")
    >>> rows = [extract_text(tr) for tr in table("tr")]
    >>> for row in rows:
    ...     print(row)  # noqa
    ...
    Import                                     Created  Source type        Target type Location     Status
    ~vcs-imports/gnome-terminal/import         2007-... Subversion via ... Bazaar      http://sv... Reviewed
    ~vcs-imports/evolution/import              2007-... Concurrent Vers... Bazaar      :pserver:... Pending Review
    ~name12/gnome-terminal/+git/gnome-terminal ...      Git                Git         git://git... Reviewed
    ~name12/evolution/+git/evolution           ...      Git                Git         https://g... Reviewed

We can also filter by source type.

    >>> control = browser.getControl(name="field.rcs_type")
    >>> control.displayValue
    ['Any']
    >>> control.displayValue = ["Concurrent Versions System"]
    >>> browser.getControl(name="submit").click()
    >>> table = find_tag_by_id(browser.contents, "code-import-listing")
    >>> rows = [extract_text(tr) for tr in table("tr")]
    >>> for row in rows:
    ...     print(row)  # noqa
    ...
    Import                        Created  Source type        Target type Location     Status
    ~vcs-imports/evolution/import 2007-... Concurrent Vers... Bazaar      :pserver:... Pending Review

... or by target type.

    >>> browser.getControl(name="field.rcs_type").displayValue = ["Any"]
    >>> control = browser.getControl(name="field.target_rcs_type")
    >>> control.displayValue
    ['Any']
    >>> control.displayValue = ["Git"]
    >>> browser.getControl(name="submit").click()
    >>> table = find_tag_by_id(browser.contents, "code-import-listing")
    >>> rows = [extract_text(tr) for tr in table("tr")]
    >>> for row in rows:
    ...     print(row)  # noqa
    ...
    Import                                     Created  Source type        Target type Location     Status
    ~name12/gnome-terminal/+git/gnome-terminal ...      Git                Git         git://git... Reviewed
    ~name12/evolution/+git/evolution           ...      Git                Git         https://g... Reviewed

If we create a lot of imports, the listing view will be batched.

    >>> login("test@canonical.com")
    >>> for i in range(10):
    ...     new_import = factory.makeCodeImport()
    ...
    >>> logout()

    >>> browser.open("http://code.launchpad.test/+code-imports")
    >>> browser.getLink("Next").click()
    >>> browser.url
    'http://code.launchpad.test/+code-imports/+index?...start=5...'
