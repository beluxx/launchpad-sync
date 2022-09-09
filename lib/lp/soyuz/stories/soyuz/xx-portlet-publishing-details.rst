The Publishing Details Portlet
==============================

This portlet conveys information about the latest version of a
package for each distroseries in which it is published.

    >>> browser.open(
    ...     "http://launchpad.test/ubuntu/+source/alsa-utils/"
    ...     "+portlet-publishing-details"
    ... )

For each distroseries there is a line containing the distroseries name,
the current version, the published component and the published section.
These latter two come specifically from the publishing records, so take
into account any overrides applied since the package was uploaded.

    >>> print(extract_text(browser.contents))
    "alsa-utils" versions published in Ubuntu
    Warty (1.0.9a-4): main/base
    Hoary (1.0.9a-4ubuntu1): main/base
    Warty (1.0.8-1ubuntu1): main/base

Series and versions are linkified.

    >>> print(browser.getLink("Hoary").url)
    http://bugs.launchpad.test/ubuntu/hoary/+source/alsa-utils
    >>> print(browser.getLink("1.0.9a-4").url)
    http://launchpad.test/ubuntu/+source/alsa-utils/1.0.9a-4

When a source package has never been published, the portlet will say so.

    >>> browser.open(
    ...     "http://launchpad.test/ubuntu/+source/a52dec/"
    ...     "+portlet-publishing-details"
    ... )

    >>> print(extract_text(browser.contents))
    "a52dec" versions published in Ubuntu
    This source is not published in Ubuntu

The portlet will only show the versions of packages published in active
distroseries.  "cdrkit" is published in Warty and Breezy-autotest, but
only Warty is active.

    >>> browser.open(
    ...     "http://launchpad.test/ubuntu/+source/cdrkit/"
    ...     "+portlet-publishing-details"
    ... )

    >>> print(extract_text(browser.contents))
    "cdrkit" versions published in Ubuntu
    Warty (1.0): main/editors
