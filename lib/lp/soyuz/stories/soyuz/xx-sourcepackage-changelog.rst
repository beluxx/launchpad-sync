Source package changelog
------------------------

Browse the changelog of a sourcepackage..

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/hoary/+source/pmount/+changelog"
    ... )
    >>> print_location(user_browser.contents)
    Hierarchy: Ubuntu > ...pmount... package > Hoary (5.04) > Change log
    Tabs:
    * Overview (selected) - http://launchpad.test/ubuntu/+source/pmount
    * Code - http://code.launchpad.test/ubuntu/+source/pmount
    * Bugs - http://bugs.launchpad.test/ubuntu/+source/pmount
    * Blueprints - not linked
    * Translations - http://translations.launchpad.test/ubuntu/+source/pmount
    * Answers - http://answers.launchpad.test/ubuntu/+source/pmount
    Main heading: Change logs for ...pmount... in Hoary

    >>> print(
    ...     extract_text(find_tag_by_id(user_browser.contents, "changelogs"))
    ... )
    This is a placeholder changelog for pmount 0.1-2
    pmount (0.1-1) hoary; urgency=low
    * Fix description (Malone #1)
    * Fix debian (Debian #2000)
    * Fix warty (Warty Ubuntu #1)
    -- Sample Person &lt;test@canonical.com&gt; Tue, 7 Feb 2006 12:10:08 +0300

.. and another one:

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/hoary/+source/alsa-utils/"
    ...     "+changelog"
    ... )
    >>> print(
    ...     extract_text(find_tag_by_id(user_browser.contents, "changelogs"))
    ... )
    alsa-utils (1.0.9a-4ubuntu1) hoary; urgency=low
    * Placeholder
    LP: #10
    LP: #999
    LP: #badid
    LP: #7, #8,
    #11
    -- Sample Person &lt;test@canonical.com&gt; Tue, 7 Feb 2006 12:10:08 +0300
    alsa-utils (1.0.9a-4) warty; urgency=low
    * Placeholder
    -- Sample Person &lt;test@canonical.com&gt; Tue, 7 Feb 2006 12:10:08 +0300

The LP: #<number> entries are also linkified:

    >>> user_browser.getLink("#10").url
    'http://launchpad.test/bugs/10'

    >>> user_browser.getLink("#999").url
    'http://launchpad.test/bugs/999'

    >>> user_browser.getLink("#badid").url
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> user_browser.getLink("#7").url
    'http://launchpad.test/bugs/7'

    >>> user_browser.getLink("#8").url
    'http://launchpad.test/bugs/8'

    >>> user_browser.getLink("#11").url
    'http://launchpad.test/bugs/11'

The output above shows email addresses, however any email addresses in
the changelog are obfuscated when the user is not logged in (this stops
bots from picking them up):

    >>> anon_browser.open(
    ...     "http://launchpad.test/ubuntu/hoary/+source/alsa-utils/"
    ...     "+changelog"
    ... )
    >>> print(extract_text(find_main_content(anon_browser.contents)))  # noqa
    Change logs for ...alsa-utils... in Hoary
    ...
    -- Sample Person &lt;email address hidden&gt; Tue, 7 Feb 2006 12:10:08 +0300
    alsa-utils (1.0.9a-4) warty; urgency=low
    * Placeholder
    -- Sample Person &lt;email address hidden&gt; Tue, 7 Feb 2006 12:10:08 +0300

If the email address is recognised as one registered in Launchpad, the
address is linkified to point to the person's profile page.  Here,
'commercialpackage' has a known email address in its changelog:

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/breezy-autotest/+source/"
    ...     "commercialpackage/+changelog"
    ... )
    >>> changelog = find_tag_by_id(
    ...     user_browser.contents, "commercialpackage_1.0-1"
    ... )
    >>> print(extract_text(changelog.find("a")))
    foo.bar@canonical.com

Browsing the individual sourcepackage changelog.

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/+source/alsa-utils/1.0.9a-4ubuntu1"
    ... )

The changelog is still linkified here so that the bug links work,
although the version link will point to the same page we're already on.

    >>> print(
    ...     find_tag_by_id(
    ...         user_browser.contents, "alsa-utils_1.0.9a-4ubuntu1"
    ...     )
    ... )
    <pre ... id="alsa-utils_1.0.9a-4ubuntu1">alsa-utils (1.0.9a-4ubuntu1) ...
    <BLANKLINE>
    ...
     LP: <a class="bug-link" href="/bugs/10">#10</a>
     LP: <a class="bug-link" href="/bugs/999">#999</a>
     LP: #badid
    ...

We should see some changelog information on the main package page.

    >>> user_browser.open("http://launchpad.test/ubuntu/+source/pmount/")
    >>> user_browser.title
    'pmount package : Ubuntu'


