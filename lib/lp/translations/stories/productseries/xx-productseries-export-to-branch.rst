ProductSeries Translations Branch
=================================

If a ProductSeries has its translations_branch set, Launchpad will
periodically commit snapshots of the series' translations to that
branch.

    >>> from lp.app.enums import ServiceUsage

    >>> login(ANONYMOUS)
    >>> owner = factory.makePerson(email="x@example.com")
    >>> product = factory.makeProduct(
    ...     owner=owner, translations_usage=ServiceUsage.LAUNCHPAD
    ... )
    >>> productseries = product.getSeries("trunk")
    >>> branch = factory.makeBranch(product=product, owner=owner)
    >>> branch_name = branch.name
    >>> foreign_branch = factory.makeBranch(product=product)
    >>> foreign_name = foreign_branch.name

    >>> def set_translations_branch(browser, branch_name):
    ...     """Set translations branch.
    ...
    ...     The browser must point at the translations-branch linking
    ...     page.  Afterwards, it will point at the translations
    ...     settings page.
    ...     """
    ...     branch_widget = browser.getControl("Translations export branch")
    ...     branch_widget.value = branch_name
    ...     update_widget = browser.getControl("Update")
    ...     update_widget.click()
    ...

    >>> def get_translations_branch_paragraph(browser):
    ...     """Return text for current translations branch.
    ...
    ...     The browser must be pointing at the settings page.
    ...     """
    ...     tag = find_tag_by_id(browser.contents, "translations-branch")
    ...     return tag.decode_contents()
    ...

A project owner sets a translations branch from the series' translations
settings page.

    >>> productseries_url = str(
    ...     "http://translations.launchpad.test/%s/trunk"
    ...     % productseries.product.name
    ... )
    >>> settings_page = productseries_url + "/+translations-settings"
    >>> link_page = productseries_url + "/+link-translations-branch"
    >>> logout()

    >>> owner_browser = setupBrowser(auth="Basic x@example.com:test")
    >>> owner_browser.open(settings_page)

The settings page currently shows that no branch has been selected.

    >>> print(extract_text(get_translations_branch_paragraph(owner_browser)))
    Currently not exporting translations to a branch.
    Choose a target branch.

The notice links to a page where a translations branch can be selected.

    >>> owner_browser.getLink("Choose a target branch").click()
    >>> print(owner_browser.url)
    http://translations.launchpad.test/.../trunk/+link-translations-branch

    >>> set_translations_branch(owner_browser, branch_name)

After setting the branch, the form returns to the settings page.

    >>> print(owner_browser.url)
    http://translations.launchpad.test/.../trunk/+translations-settings

It shows the changed setting.

    >>> print(extract_text(get_translations_branch_paragraph(owner_browser)))
    Exporting translations to branch: lp:...

The notice links to the branch, and to the page where the setting can be
changed.

    >>> edit_link = owner_browser.getLink(id="translations-branch-edit-link")
    >>> print(edit_link.url)
    http://translations.launchpad.test/.../trunk/+link-translations-branch

    >>> branch_link = owner_browser.getLink(url=branch_name)
    >>> print(branch_link.url)
    http://code.launchpad.test/~.../.../...

    >>> branch_link.click()

    >>> branch_page = owner_browser.url

    >>> back_reference = find_tag_by_id(
    ...     owner_browser.contents, "translations-sources"
    ... )
    >>> print(back_reference)
    <div ...>
    <h2>Automatic translations commits</h2>
    <ul>
    <li><a href=".../trunk">... trunk series</a></li>
    </ul>
    </div>


Disabling exports
-----------------

The field can also be cleared in order to disable the exports.

    >>> owner_browser.open(link_page)
    >>> set_translations_branch(owner_browser, "")

    >>> print(owner_browser.url)
    http://translations.launchpad.test/.../trunk/+translations-settings

The settings page then goes back to showing the original message.

    >>> print(extract_text(get_translations_branch_paragraph(owner_browser)))
    Currently not exporting translations to a branch.
    Choose a target branch.

Of course the product series will no longer show up on the branch
overview as a translations source.

    >>> owner_browser.open(branch_page)
    >>> back_reference = find_tag_by_id(
    ...     owner_browser.contents, "translations-sources"
    ... )
    >>> print(back_reference)
    None


Security
--------

You can only set the translations_branch to a branch that you own.
Otherwise you'd be giving Launchpad a blanket licence to commit
translations to someone else's branch.

    >>> owner_browser.open(link_page)
    >>> set_translations_branch(owner_browser, foreign_name)

This leaves the translations_branch unchanged.

    >>> owner_browser.open(settings_page)
    >>> print(extract_text(get_translations_branch_paragraph(owner_browser)))
    Currently not exporting translations to a branch.
    Choose a target branch.

And of course, setting the translations branch requires edit privileges
on the release series.

    >>> user_browser.open(link_page)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...
