When Launchpad Bugs is not used to track bugs
=============================================

We do some special handling of the cases where upstream doesn't use
Launchpad as their official bugtracker. In this situation, we want to
tell people what their options are.


Upstreams
---------

Alsa-utils, for instance, doesn't use Launchpad Bugs:

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/alsa-utils/+filebug')
    >>> for message in find_tags_by_class(
    ...     user_browser.contents, 'highlight-message'):
    ...     print(extract_text(message))
    alsa-utils does not use Launchpad as its bug tracker.

But it's packaged in Ubuntu and Debian, and we suggest those packages
for filing bugs:

    >>> user_browser.getLink("Ubuntu alsa-utils") is not None
    True

We don't know what bug tracker they use either:

    >>> "doesn't know what bug tracker" in user_browser.contents
    True

    >>> user_browser.getLink("Tell us about it.") is not None
    True

Gnomebaker doesn't use Launchpad Bugs either. We don't have packaging
information for it:

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/gnomebaker/+filebug')
    >>> for message in find_tags_by_class(
    ...     user_browser.contents, 'highlight-message'):
    ...     print(extract_text(message))
    gnomebaker does not use Launchpad as its bug tracker.

    >>> user_browser.getLink("linking them for us.") is not None
    True

But we are advised to file bugs in the upstream bug tracker:

    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents, 'bugtarget-upstream-bugtracker-info')))
    Bugs in upstream gnomebaker should be reported in its official bug
    tracker, GnomeGBug GTracker

    >>> user_browser.getLink("GnomeGBug GTracker").url
    'http://bugzilla.gnome.org/bugs'

The advice is slightly different if the upstream bug tracker is actually
an email address.

    >>> admin_browser.open(
    ...     'http://launchpad.test/jokosher/+configure-bugtracker')
    >>> admin_browser.getControl(
    ...     'By emailing an upstream bug contact').selected = True
    >>> admin_browser.getControl(
    ...     name='field.bugtracker.upstream_email_address').value = (
    ...         'puff@magicdragon.example.com')
    >>> admin_browser.getControl('Change').click()

    >>> user_browser.open('http://bugs.launchpad.test/jokosher/+filebug')

    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents, 'bugtarget-upstream-bugtracker-info')))
    Bugs in upstream Jokosher should be sent to
    mailto:puff@magicdragon.example.com

    >>> user_browser.getLink("mailto:puff@magicdragon.example.com").url
    'mailto:puff@magicdragon.example.com'


Advanced Filebug
................

The same happens with the advanced filebug form:

    >>> user_browser.open(
    ...     "http://launchpad.test/products/alsa-utils/+filebug")
    >>> for message in find_tags_by_class(
    ...     user_browser.contents, 'highlight-message'):
    ...     print(extract_text(message))
    alsa-utils does not use Launchpad as its bug tracker.


Distros
-------

Distributions have less options available if they don't use Launchpad:

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/debian/+filebug')
    >>> for message in find_tags_by_class(
    ...     user_browser.contents, 'highlight-message'):
    ...     print(extract_text(message))
    Debian does not use Launchpad as its bug tracker.

They get the same messages in the advanced filebug page:

    >>> user_browser.open(
    ...     "http://launchpad.test/distros/debian/+filebug")
    >>> for message in find_tags_by_class(
    ...     user_browser.contents, 'highlight-message'):
    ...     print(extract_text(message))
    Debian does not use Launchpad as its bug tracker.


Distro Source Packages
----------------------

It's also not possible to file a bug on any of the distribution's source
package.

    >>> user_browser.open(
    ...     "http://launchpad.test/debian/+source/mozilla-firefox/"
    ...     "+filebug")
    >>> for message in find_tags_by_class(
    ...     user_browser.contents, 'highlight-message'):
    ...     print(extract_text(message))
    Debian does not use Launchpad as its bug tracker.

Not even using the advanced filebug page:

    >>> user_browser.open(
    ...     "http://launchpad.test/distros/debian/+source/mozilla-firefox/"
    ...     "+filebug")
    >>> for message in find_tags_by_class(
    ...     user_browser.contents, 'highlight-message'):
    ...     print(extract_text(message))
    Debian does not use Launchpad as its bug tracker.


