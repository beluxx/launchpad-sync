Distribution translations
=========================

This page shows a list of PO templates contained within all source
packages for the distroseries that is the translation focus for a
given distribution.

Make the test browser look like it's coming from an arbitrary South African
IP address, since we'll use that later.

    >>> browser.addHeader('X_FORWARDED_FOR', '196.36.161.227')

We can reach it from the main distribution page:

    >>> browser.open('http://launchpad.test/ubuntu')
    >>> browser.getLink('Translations').click()
    >>> print(browser.title)
    Translations : Ubuntu

Check that there aren't disabled languages shown here:

    >>> table = find_tag_by_id(browser.contents, 'languagestats')
    >>> language_stats = extract_text(table)
    >>> 'Spanish (Spain)' not in language_stats
    True
    >>> 'Italian (Italy)' not in language_stats
    True

English is a special case in that it is not a translatable language
even though it is visible.

    >>> 'English' not in language_stats
    True

But we show the other languages:

    >>> 'Spanish' in language_stats
    True
    >>> 'Italian' in language_stats
    True

Portuguese (Brazil) is a country specific language but it should not
be disabled and appear in our list.

    >>> 'Portuguese (Brazil)' in language_stats
    True

Now, we are going to check that the language list we got is pointing
to the right translation focus.

    >>> print(browser.getLink('Spanish').url)
    http://translations.launchpad.test/ubuntu/hoary/+lang/es
    >>> print(browser.getLink('Italian').url)
    http://translations.launchpad.test/ubuntu/hoary/+lang/it
    >>> print(browser.getLink('Portuguese (Brazil)').url)
    http://translations.launchpad.test/ubuntu/hoary/+lang/pt_BR

And the other Ubuntu distributions should be there too.

    >>> content = find_main_content(browser.contents)
    >>> print(extract_text(content.find_all('h2')[1]))
    Other versions of Ubuntu

    >>> print(extract_text(content.find(id='distroseries-list')))
    Breezy Badger Autotest (6.6.6)
    Grumpy (5.10)
    Warty (4.10)

We are not showing its translation status here, so we should have
links to their particular translation status.

    >>> print(browser.getLink('Breezy Badger Autotest (6.6.6)').url)
    http://translations.launchpad.test/ubuntu/breezy-autotest
    >>> print(browser.getLink('Grumpy (5.10)').url)
    http://translations.launchpad.test/ubuntu/grumpy
    >>> print(browser.getLink('Warty (4.10)').url)
    http://translations.launchpad.test/ubuntu/warty

But we are already showing the status for the translation focus one,
we should not have a link to it.

    >>> browser.getLink('5.04 The Hoary Hedgehog Release')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

Let's try now a distribution that lacks a translation focus. Debian is
a good example, if enable translations for it.

    >>> from zope.component import getUtility
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> login('admin@canonical.com')
    >>> debian = getUtility(IDistributionSet).getByName('debian')
    >>> debian.translations_usage = ServiceUsage.LAUNCHPAD
    >>> transaction.commit()
    >>> logout()

We should get latest release as the translation focus.

    >>> browser.open('http://translations.launchpad.test/debian')
    >>> browser.url
    'http://translations.launchpad.test/debian'

It doesn't have any translation, so we will get the default GeoIP
languages pointing to the latest release, Hoary.

    >>> print(browser.getLink('Zulu').url)
    http://translations.launchpad.test/debian/sarge/+lang/zu

And the other Ubuntu distributions should be there too.

    >>> content = find_main_content(browser.contents)
    >>> print(extract_text(content.find_all('h2')[1]))
    Other versions of Debian

    >>> print(extract_text(content.find(id='distroseries-list')))
    Sid (3.2)
    Woody (3.0)

We are not showing its translation status here, so we should have
links to their particular translation status.

    >>> print(browser.getLink('Sid (3.2)').url)
    http://translations.launchpad.test/debian/sid
    >>> print(browser.getLink('Woody (3.0)').url)
    http://translations.launchpad.test/debian/woody

But we are already showing the status for the translation focus one,
we should not have a link to it.

    >>> browser.getLink('3.1 Sarge')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

Administrator can change the translation focus for a distribution.

    >>> editor_browser = setupBrowser(
    ...     auth='Basic jeff.waugh@ubuntulinux.com:test')
    >>> editor_browser.open('http://launchpad.test/ubuntu')
    >>> editor_browser.getLink('Change details').click()
    >>> editor_browser.getControl('Translation focus').displayValue
    ['ubuntu hoary']
    >>> editor_browser.getControl('Translation focus').displayValue = [
    ...     'ubuntu grumpy']
    >>> editor_browser.getControl('Change', index=3).click()
    >>> editor_browser.getLink('Change details').click()
    >>> editor_browser.getControl('Translation focus').displayValue
    ['ubuntu grumpy']
