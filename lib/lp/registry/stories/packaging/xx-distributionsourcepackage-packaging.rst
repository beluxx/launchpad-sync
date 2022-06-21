Distribution Packaging
======================

The packaging records for a source package in a given distribution are
displayed on the page of the distribution source package.

Any user can see the summary of the binaries built from the current version
of the package.

    >>> anon_browser.open('http://launchpad.test/ubuntu/+source/pmount')
    >>> print(extract_text(find_tag_by_id(anon_browser.contents, 'summary')))
    pmount: pmount shortdesc

This page includes a table that lists all the releases of this source
package in this distribution, and the packaging associations for this
source package in each series of this distribution.

    >>> anon_browser.open('http://launchpad.test/ubuntu/+source/alsa-utils')
    >>> content = anon_browser.contents
    >>> print(extract_text(find_tag_by_id(content, 'packages_list')))
    The Hoary Hedgehog Release (active development)     Set upstream link
      1.0.9a-4ubuntu1 release (main) 2005-09-15
    The Warty Warthog Release (current stable release) alsa-utils trunk series
      1.0.9a-4        release (main) 2005-09-16
      1.0.8-1ubuntu1  release (main) 2005-09-15


Delete Link Button
------------------

A button is displayed to authenticated users to delete existing
packaging links.

    >>> user_browser = setupBrowser(auth='Basic test@canonical.com:test')
    >>> user_browser.open('http://launchpad.test/ubuntu/+source/alsa-utils')
    >>> link = user_browser.getLink(
    ...     url='/ubuntu/warty/+source/alsa-utils/+remove-packaging')
    >>> print(link)
    <Link text='Remove upstream link'...

This button is not displayed to anonymous users.

    >>> anon_browser.open('http://launchpad.test/ubuntu/+source/alsa-utils')
    >>> anon_browser.getForm("delete_warty_alsa-utils_trunk")
    Traceback (most recent call last):
    ...
    LookupError

Clicking this button deletes the corresponding packaging association.

    >>> link = user_browser.getLink(
    ...     url='/ubuntu/warty/+source/alsa-utils/+remove-packaging')
    >>> link.click()
    >>> user_browser.getControl('Unlink').click()
    >>> content = user_browser.contents
    >>> for tag in find_tags_by_class(content, 'error'):
    ...     print(extract_text(tag))
    >>> for tag in find_tags_by_class(content, 'informational'):
    ...     print(extract_text(tag))
    Removed upstream association between alsa-utils trunk series and Warty.
    >>> print(extract_text(find_tag_by_id(content, 'packages_list')))
    The Hoary Hedgehog Release (active development)     Set upstream link
      1.0.9a-4ubuntu1 release (main) 2005-09-15
    The Warty Warthog Release (current stable release)  Set upstream link
      1.0.9a-4        release (main) 2005-09-16
      1.0.8-1ubuntu1  release (main) 2005-09-15
