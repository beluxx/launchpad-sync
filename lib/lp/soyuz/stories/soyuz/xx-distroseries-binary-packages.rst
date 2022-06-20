Distro series binary package
============================

A binary package for a distro-series displays the package's name,
summary and description:

    >>> browser.open(
    ...     'http://launchpad.test/ubuntu/warty/+package/mozilla-firefox')
    >>> print(browser.title)
    mozilla-firefox : Warty (4.10) : Ubuntu

    >>> main_content = find_main_content(browser.contents)
    >>> print(extract_text(main_content))
    Binary package “mozilla-firefox” in ubuntu warty
    Warty (4.10) mozilla-firefox
    Mozilla Firefox Web Browser
    Mozilla Firefox Web Browser is .....
    Source package
    iceweasel 1.0 source package in Ubuntu
    Published versions
    mozilla-firefox 0.9 in hppa (Release)
    mozilla-firefox 0.9 in i386 (Release)
    mozilla-firefox 1.0 in i386 (Release)

And each publishing history item is a link to the relevant binary
release:

    >>> print(browser.getLink('mozilla-firefox 0.9 in hppa (Release)').url)
    http://launchpad.test/ubuntu/warty/hppa/mozilla-firefox/0.9
    >>> print(browser.getLink('mozilla-firefox 0.9 in i386 (Release)').url)
    http://launchpad.test/ubuntu/warty/i386/mozilla-firefox/0.9
    >>> print(browser.getLink('mozilla-firefox 1.0 in i386 (Release)').url)
    http://launchpad.test/ubuntu/warty/i386/mozilla-firefox/1.0

The page also displays a link to the distro series source package
release:

    >>> browser.getLink(id="source_package").click()
    >>> browser.title
    '1.0 : iceweasel package : Ubuntu'

Some DistroSeriesBinaryPackages are unpublished, in this case there is
no link to any source package:

    >>> browser.open(
    ...     'http://launchpad.test/ubuntu/hoary/+package/mozilla-firefox')
    >>> print(browser.title)
    mozilla-firefox : Hoary (5.04) : Ubuntu

    >>> main_content = find_main_content(browser.contents)
    >>> print(extract_text(main_content))
    Binary package “mozilla-firefox” in ubuntu hoary
    Hoary (5.04) mozilla-firefox
    No summary available for mozilla-firefox in ubuntu hoary.
    No description available for mozilla-firefox in ubuntu hoary.
    Published versions
    Not published at present.
