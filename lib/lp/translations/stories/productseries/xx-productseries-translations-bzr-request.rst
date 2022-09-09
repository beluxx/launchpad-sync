Requesting a one-time import of translation files
=================================================
Product maintainers can request a one-time import of translation files
from the Bazaar branch that is officially linked to the release series
of a product. This function complements the general import settings
found on the "Settings" page.

Getting there
-------------
The maintainer of a product sees a menu option called "Reqeust Bazaar
import" that leads to the page to request such imports.

    >>> browser.addHeader("Authorization", "Basic test@canonical.com:test")
    >>> browser.open("http://translations.launchpad.test/evolution/trunk/")
    >>> browser.getLink("Request an import from bazaar").click()
    >>> print(browser.url)
    http://translations.l...d.test/evolution/trunk/+request-bzr-import

The request page with a branch
------------------------------
The product series must have a branch configured in order to be able
to request an import. The current branch is displayed on the page.

    >>> branch = find_tag_by_id(browser.contents, "branch-display")
    >>> print(extract_text(branch))
    The official Bazaar branch is:
    lp://dev/evolution

If the product series is not configured to import translation files
continuously, the user is reminded of that here.

    >>> settings = find_tag_by_id(browser.contents, "settings-display")
    >>> print(extract_text(settings))
    To enable continuous imports please change the settings here.
    >>> browser.getLink("here").click()
    >>> print(browser.url)
    http://translations.l...d.test/evolution/trunk/+translations-settings

Changing that setting will make that message disappear from the page.

    >>> browser.getControl(
    ...     name="field.translations_autoimport_mode"
    ... ).value = ["IMPORT_TEMPLATES"]
    >>> browser.getControl("Save settings").click()
    >>> browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/"
    ...     "+request-bzr-import"
    ... )
    >>> settings = find_tag_by_id(browser.contents, "settings-display")
    >>> print(settings)
    None

The request is made by clicking on a button labeled
"Request one-time import".

    >>> request_button = find_tag_by_id(
    ...     browser.contents, "field.actions.request_import"
    ... )
    >>> print(request_button)
    <input ...type="submit"...value="Request one-time import"...
    >>> browser.getControl("Request one-time import").click()
    >>> print(browser.url)
    http://translations.launchpad.test/evolution/trunk
    >>> print_feedback_messages(browser.contents)
    The import has been requested.

The request page without a branch
---------------------------------
The official Bazaar branch gets removed from the product series.

    >>> browser.open("http://launchpad.test/evolution/trunk/+setbranch")
    >>> browser.getControl(name="field.branch_location").value = ""
    >>> browser.getControl("Update").click()

Since the product series does not have a branch set now, requesting an
import is pointless. The page points the user to the fact and where to
set the branch.

    >>> browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/"
    ...     "+request-bzr-import"
    ... )
    >>> branch = find_tag_by_id(browser.contents, "no-branch-display")
    >>> print(extract_text(branch))
    This series does not have an official Bazaar branch.
    Please set it first.
    >>> browser.getLink("Please set it first.").click()
    >>> print(browser.url)
    http://launchpad.test/evolution/trunk/+setbranch

The request button is missing completely from the page.

    >>> browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/"
    ...     "+request-bzr-import"
    ... )
    >>> request_button = find_tag_by_id(
    ...     browser.contents, "field.actions.request_import"
    ... )
    >>> print(request_button)
    None
