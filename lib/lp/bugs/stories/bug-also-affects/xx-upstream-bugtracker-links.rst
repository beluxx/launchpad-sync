Links to upstream bug trackers
==============================

Sometimes people will want to mark a bug as being upstream but will
either not know what the bug's upstream URL is or will know that the bug
is not yet filed upstream.

If a  project is linked to an upstream bug tracker and there is a record
of the remote product it uses on that bug tracker, links will be shown
on the +choose-affected-product form to that bug tracker's bug filing
and search forms.

    >>> user_browser.open("http://launchpad.test/bugs/13/")
    >>> user_browser.getLink(url="+choose-affected-product").click()
    >>> user_browser.getControl("Project").value = "thunderbird"
    >>> user_browser.getControl("Continue").click()

Thunderbird isn't linked to an upstream tracker, so the text is more
general.

    >>> text = find_tag_by_id(user_browser.contents, "upstream-text")
    >>> print(extract_text(text))
    Mozilla Thunderbird
    doesn't use Launchpad to track its bugs. If you know this bug
    has been reported in another bug tracker, you can link to it;
    Launchpad will keep track of its status for you.
    I have the URL for the upstream bug...

If we link Thunderbird to an upstream bug tracker, the text will change
to reflect this.

    >>> admin_browser.open(
    ...     "http://launchpad.test/thunderbird/+configure-bugtracker"
    ... )
    >>> admin_browser.getControl(name="field.bugtracker").value = ["external"]
    >>> admin_browser.getControl(
    ...     name="field.bugtracker.bugtracker"
    ... ).value = "mozilla.org"
    >>> admin_browser.getControl("Change").click()

    >>> user_browser.open("http://launchpad.test/bugs/13/")
    >>> user_browser.getLink(url="+choose-affected-product").click()
    >>> user_browser.getControl("Project").value = "thunderbird"
    >>> user_browser.getControl("Continue").click()

    >>> text = find_tag_by_id(user_browser.contents, "upstream-text")
    >>> print(extract_text(text))
    Mozilla Thunderbird
    uses The Mozilla.org Bug Tracker to
    track its bugs. If you know this bug has been reported there,
    you can link to it; Launchpad will keep track of its status
    for you.
    I have the URL for the upstream bug...

If the project that the user links to is one that has its remote_product
set, links to the upstream bug tracker's bug filing and search forms
will be displayed.

    >>> user_browser.open("http://launchpad.test/bugs/13/")
    >>> user_browser.getLink(url="+choose-affected-product").click()
    >>> user_browser.getControl("Project").value = "gnome-terminal"
    >>> user_browser.getControl("Continue").click()

    >>> text = find_tag_by_id(user_browser.contents, "upstream-text")
    >>> print(extract_text(text))
    GNOME Terminal uses GnomeGBug GTracker to track its bugs.
    If you know this bug has been reported there, you can link to it;
    Launchpad will keep track of its status for you.
    If you want to report this bug on GnomeGBug GTracker before adding
    the link to Launchpad you can use the GnomeGBug GTracker bug filing
    form. If you want to search for this bug on GnomeGBug GTracker
    before adding the link to Launchpad you can use the GnomeGBug
    GTracker search form...

The description given in the link to the bug filing form contains a
link back to bug 13, the place where it was originally filed.

    >>> from urllib.parse import (
    ...     parse_qs,
    ...     urlparse,
    ... )

    >>> url = user_browser.getLink(text="bug filing form").url
    >>> scheme, netloc, path, params, query, fragment = urlparse(url)
    >>> [long_desc] = parse_qs(query)["long_desc"]

    >>> print(long_desc)
    Originally reported at:
      http://bugs.launchpad.test/bugs/13
    <BLANKLINE>
    The messages placed on this bug are for eyeball viewing of JS and
    CSS behaviour.

If the remote bug tracker is one for which Launchpad doesn't offer a bug
filing link, such as Debbugs, only a search link will be displayed.

    >>> admin_browser.open(
    ...     "http://launchpad.test/gnome-terminal/+configure-bugtracker"
    ... )
    >>> admin_browser.getControl(
    ...     "In a registered bug tracker:"
    ... ).selected = True
    >>> admin_browser.getControl(
    ...     name="field.bugtracker.bugtracker"
    ... ).value = "debbugs"
    >>> admin_browser.getControl("Change").click()

    >>> user_browser.open("http://launchpad.test/bugs/13/")
    >>> user_browser.getLink(url="+choose-affected-product").click()
    >>> user_browser.getControl("Project").value = "gnome-terminal"
    >>> user_browser.getControl("Continue").click()

    >>> text = find_tag_by_id(user_browser.contents, "upstream-text")
    >>> print(extract_text(text))
    GNOME Terminal uses Debian Bug tracker to track its bugs.
    If you know this bug has been reported there, you can link to it;
    Launchpad will keep track of its status for you.
    If you want to search for this bug on Debian Bug tracker
    before adding the link to Launchpad you can use the Debian Bug
    tracker search form...


Setting the remote project
==========================

The remote_product field, which stores a Product's ID on the remote bug
tracker, can be set from the +configure-bugtracker page, too.

    >>> admin_browser.open(
    ...     "http://launchpad.test/thunderbird/+configure-bugtracker"
    ... )
    >>> admin_browser.getControl(
    ...     name="field.remote_product"
    ... ).value = "Thunderbird"
    >>> admin_browser.getControl("Change").click()

    >>> admin_browser.open(
    ...     "http://launchpad.test/thunderbird/+configure-bugtracker"
    ... )
    >>> print(admin_browser.getControl(name="field.remote_product").value)
    Thunderbird
