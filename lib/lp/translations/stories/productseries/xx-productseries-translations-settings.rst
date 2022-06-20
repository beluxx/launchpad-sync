Changing the Bazaar import settings for a product series
========================================================

Product maintainers can request a one-time import of translation files
from the Bazaar branch that is officially linked to the release series
of a product. This function complements the general import settings
found on the "Settings" page.

Getting there
-------------

The maintainer of a product sees a menu option called "Settings" that
leads to the settings page.

    >>> browser.addHeader('Authorization',
    ...                   'Basic test@canonical.com:test')
    >>> browser.open(
    ...     'http://translations.launchpad.test/evolution/trunk/')
    >>> browser.getLink('Set up branch synchronization').click()
    >>> print(browser.url)
    http://translations.l...d.test/evolution/trunk/+translations-settings

The branch display
------------------

An official Bazaar branch is linked to this product settings. It is
displayed on the page.

    >>> branch = find_tag_by_id(browser.contents, 'branch-display')
    >>> print(extract_text(branch))
    The official Bazaar branch is:
    lp://dev/evolution

When the official Bazaar branch gets removed from the product series,
a message indicating so is displayed instead of the branch. The
message also directs to the page where the branch can be set.

    >>> browser.open('http://launchpad.test/evolution/trunk/+setbranch')
    >>> browser.getControl(name='field.branch_location').value = ''
    >>> browser.getControl('Update').click()

    >>> browser.open(
    ...     'http://translations.launchpad.test/evolution/trunk/'
    ...     '+translations-settings')
    >>> branch = find_tag_by_id(browser.contents, 'no-branch-display')
    >>> print(extract_text(branch))
    This series does not have an official Bazaar branch.
    Set it now!
    >>> browser.getLink('Set it now!').click()
    >>> print(browser.url)
    http://launchpad.test/evolution/trunk/+setbranch

Pointer to one-time import
--------------------------

The user is also reminded that a one-time import of translation files
can be requested and a link to that page is provided.

    >>> browser.open(
    ...     'http://translations.launchpad.test/evolution/trunk/'
    ...     '+translations-settings')
    >>> settings = find_tag_by_id(browser.contents, 'bzr-request-display')
    >>> print(extract_text(settings))
    You can request a one-time import.
    >>> browser.getLink('request a one-time import').click()
    >>> print(browser.url)
    http://translations.l...d.test/evolution/trunk/+request-bzr-import

Changing the setting
--------------------

The setting is changed by selecting the desired mode with the radio
buttons in the form.

    >>> browser.open('http://translations.launchpad.test/evolution/trunk/')
    >>> browser.getLink('Set up branch synchronization').click()
    >>> print_radio_button_field(browser.contents,
    ...                          'translations_autoimport_mode')
    (*) None
    ( ) Import template files
    ( ) Import template and translation files
    >>> browser.getControl(
    ...     name='field.translations_autoimport_mode').value = (
    ...         ['IMPORT_TEMPLATES'])
    >>> browser.getControl('Save settings').click()

The user is automatically redirected to the page they came from.

    >>> print(browser.url)
    http://translations.launchpad.test/evolution/trunk/
    >>> print_feedback_messages(browser.contents)
    The settings have been updated.

If they look at the synchonization settings page again, they see that
the changes have been saved.

    >>> browser.getLink('Set up branch synchronization').click()
    >>> print_radio_button_field(browser.contents,
    ...                          'translations_autoimport_mode')
    ( ) None
    (*) Import template files
    ( ) Import template and translation files
