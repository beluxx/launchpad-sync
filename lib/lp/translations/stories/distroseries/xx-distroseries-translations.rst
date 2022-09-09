Distribution series translations
================================

This page shows a list of PO templates contained within all source
packages in a particular distibution series.

In this case, we're asking for the translation overview for Hoary.

    >>> anon_browser.open("http://translations.launchpad.test/ubuntu/hoary")

The system is not showing non visible languages:

    >>> anon_browser.getLink("Spanish (Spain)")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

The system will not show English because it is not translatable:

    >>> anon_browser.getLink("English")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

But it shows the ones not hidden:

    >>> print(anon_browser.getLink("Spanish").url)
    http://translations.launchpad.test/ubuntu/hoary/+lang/es

Launchpad has an option to hide all of the translations for a distribution
series.  The link to hide translations is not available to anonymous users:

    >>> anon_browser.getLink("Change settings")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

And the page is not available either:

    >>> anon_browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/"
    ...     "+translations-admin"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

... but the link is available to administrators:

    >>> dtc_browser = setupDTCBrowser()
    >>> dtc_browser.open("http://translations.launchpad.test/ubuntu/hoary")
    >>> dtc_browser.getLink("Change settings").click()

Once the administrator hides all translations...

    >>> dtc_browser.getControl(
    ...     "Hide translations for this release"
    ... ).selected = True
    >>> dtc_browser.getControl("Change").click()
    >>> print(dtc_browser.url)
    http://translations.launchpad.test/ubuntu/hoary

...a notice about the fact shows up on the overview page.

    >>> notices = find_tags_by_class(
    ...     dtc_browser.contents, "visibility-notice"
    ... )
    >>> for notice in notices:
    ...     print(extract_text(notice))
    ...
    Translations for this series are currently hidden.

Now, the translation status page will no longer display any languages to
regular users.

    >>> user_browser.open("http://translations.launchpad.test/ubuntu/hoary")
    Traceback (most recent call last):
    ...
    lp.app.errors.TranslationUnavailable: ...

Also, if the user tries to navigate directly to launchpad pages,
the system tells them that they're not allowed to see those pages.

    >>> user_browser.handleErrors = True
    >>> user_browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/+lang/es"
    ... )
    Traceback (most recent call last):
    ...
    urllib.error.HTTPError: HTTP Error 503: Service Unavailable
    >>> main_content = find_main_content(user_browser.contents)
    >>> print(main_content.find_next("p").decode_contents())
    Translations for this release series are not available yet.

    >>> user_browser.handleErrors = False

Translations administrator have access series with hidden translations.

    >>> dtc_browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/+lang/es"
    ... )

Non existing languages are not viewable. English is a special case
in that we store the translatable messages as English, so it cannot
should not viewed

    >>> user_browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/+lang/notexists"
    ... )
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...

    >>> user_browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/+lang/en"
    ... )
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...

Translation pages for source packages are also unavailable to
non-administrative users.

    >>> user_browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/"
    ...     "+sources/evolution/+pots/evolution-2.2"
    ... )
    Traceback (most recent call last):
    ...
    lp.app.errors.TranslationUnavailable: ...

However, source package translations are still available to the
administrators.

    >>> dtc_browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/"
    ...     "+sources/evolution/+pots/evolution-2.2"
    ... )

There is also an option to set/unset whether translation imports for a
distribution should be deferred. That option is set also from the same
form where we hide all translations and an admin is able to change it:

    >>> dtc_browser.open("http://translations.launchpad.test/ubuntu/hoary")
    >>> dtc_browser.getLink("Change settings").click()
    >>> dtc_browser.getControl("Defer translation imports").selected
    False
    >>> dtc_browser.getControl("Defer translation imports").selected = True
    >>> dtc_browser.getControl("Change").click()
    >>> print(dtc_browser.url)
    http://translations.launchpad.test/ubuntu/hoary

Once the system accepts the submission, we can see such change applied.

    >>> dtc_browser.getLink("Change settings").click()
    >>> dtc_browser.getControl("Defer translation imports").selected
    True

There are no visible user interface changes once this flag is changed. It
just prevents that the translation import script, which is executed by cron,
handle translation imports for this distro series.
