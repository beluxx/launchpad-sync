Demo and launchpad.net
======================

Launchpad can brand instances as 'demo' instances to make it obvious to
users that they are working in a playpen and changes they make do not
affect the launchpad.net database.

This is controlled by a pair of config variables.

    >>> from lp.services.config import config
    >>> config.launchpad.is_demo
    False
    >>> config.launchpad.site_message
    ''

(We could hard-code database names rather than using config variables.
But using config variables future-proofs us against changes such as
using multiple launchpad databases. It also makes testing and examining
instance-specific customizations much easier.)

When you are on a demo site, the is_demo setting is advertised by both
the page background, and the text "demo site" in the page footer.

Note: during the transition to 3.0 we test a non-3-0 page as well as
a 3-0 page to ensure that both display the correct demo/lp-net
information and styles.

    # Set config to pretend we're on a demo site:
    >>> from lp.testing.fixture import DemoMode
    >>> demo_mode_fixture = DemoMode()
    >>> demo_mode_fixture.setUp()
    >>> print(config.launchpad.is_demo)
    True

The demo style is applied and the site_message is also included as part
of the header. The site-message is structured so that any links will not
be escaped.

For a 3-0 page:

    >>> browser.open('http://launchpad.test/ubuntu')
    >>> print(browser.contents)
    <...
    <style...url(/@@/demo)...</style>
    ...
    >>> print(extract_text(find_tag_by_id(browser.contents, 'lp-version')))
    • r... devmode demo site (Get the code!)

    >>> print(extract_text(find_tags_by_class(
    ...     browser.contents, 'sitemessage')[0]))
    This is a demo site mmk. File a bug.
    >>> print(browser.getLink(url="http://example.com").text)
    File a bug

When you are not on a demo site, the text no longer appears.

    >>> demo_mode_fixture.cleanUp()
    >>> print(config.launchpad.is_demo)
    False

First for a 3-0 page:

    >>> browser.open('http://launchpad.test/ubuntu')
    >>> print(extract_text(find_tag_by_id(browser.contents, 'lp-version')))
    • r... devmode (Get the code!)
    >>> len(find_tags_by_class(browser.contents, 'sitemessage'))
    0
