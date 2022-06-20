Bug trackers in Launchpad
=========================

The bug trackers index page has the same navigation as the main Bugs
page, with the addition of a breadcrumb itself.

    >>> user_browser.open('http://launchpad.test/bugs/bugtrackers')
    >>> print(user_browser.title)
    Bug trackers registered in Launchpad

The page presents a table with all bugtrackers currently registered:

    >>> def print_tracker_table(browser):
    ...     table = find_tag_by_id(browser.contents, 'trackers')
    ...     for row in table.tbody.find_all('tr'):
    ...         title, location, linked, type, watches = row.find_all('td')
    ...         print('------------------------')
    ...         print('\n'.join([
    ...             extract_text(title),
    ...             extract_text(location),
    ...             '  --> %s' % (location.a and location.a.get('href')),
    ...             ' '.join(extract_text(linked).split()),
    ...             extract_text(type),
    ...             extract_text(watches)]))

    >>> print_tracker_table(user_browser)
    ------------------------
    Debian Bug tracker
    http://bugs.debian.org
      --> http://bugs.debian.org
    —
    Debbugs
    5
    ------------------------
    Email bugtracker
    mailto:bugs@example.com
      --> mailto:bugs@example.com
    —
    Email Address
    0
    ------------------------
    T'other Gnome GBugGTracker
    http://bugzilla.gnome.org/
      --> http://bugzilla.gnome.org/
    —
    Bugzilla
    0
    ------------------------
    ...

Email addresses are obfuscated if the user is not logged-in. The title
of the bug tracker might contain an email address - especially
auto-created ones - so the title is also obfuscated.

    >>> admin_browser.open(
    ...     'http://launchpad.test/bugs/bugtrackers/email/+edit')
    >>> admin_browser.getControl('Title').value = (
    ...     'an@email.address bug tracker')
    >>> admin_browser.getControl('Change').click()

    >>> anon_browser.open('http://launchpad.test/bugs/bugtrackers')
    >>> print_tracker_table(anon_browser)
    ------------------------
    ...
    &lt;email address hidden&gt; bug tracker
    mailto:&lt;email address hidden&gt;
      --> None
    —
    Email Address
    0
    ------------------------
    ...

The watch counts match the number of bugs listed, of course:

    >>> user_browser.getLink("Debian Bug tracker").click()
    >>> nav = find_tags_by_class(user_browser.contents,
    ...     'batch-navigation-index')
    >>> print(extract_text(nav[0]))
    1 → 5 of 5 results

The listing also displays projects and projects linked to bug trackers.
Let's link a pair to debbugs:

    >>> def link_to_debbugs(name):
    ...     admin_browser.open(
    ...         "http://launchpad.test/%s/+configure-bugtracker" % name)
    ...     admin_browser.getControl("In a registered bug tracker").click()
    ...     bt = admin_browser.getControl(name="field.bugtracker.bugtracker")
    ...     bt.value = 'debbugs'
    ...     admin_browser.getControl("Change").click()
    ...
    >>> link_to_debbugs('upstart')
    >>> link_to_debbugs('derby')

And re-render the table:

    >>> user_browser.open('http://launchpad.test/bugs/bugtrackers')
    >>> print_tracker_table(user_browser)
    ------------------------
    Debian Bug tracker
    http://bugs.debian.org
      --> http://bugs.debian.org
    Derby, Upstart
    Debbugs
    5
    ------------------------
    ...

    >>> user_browser.getLink("Upstart").click()
    >>> user_browser.url
    'http://launchpad.test/upstart'

Add a third and a fourth to show ellipsizing. Note that projects
linked to bugtrackers are also linked.

    >>> link_to_debbugs('a52dec')
    >>> link_to_debbugs('iso-codes')

    >>> user_browser.open('http://launchpad.test/bugs/bugtrackers')
    >>> print_tracker_table(user_browser)
    ------------------------
    Debian Bug tracker
    http://bugs.debian.org
      --> http://bugs.debian.org
    a52dec, Derby, iso-codes …
    Debbugs
    5
    ------------------------
    ...
    GnomeGBug GTracker
    http://bugzilla.gnome.org/bugs
      --> http://bugzilla.gnome.org/bugs
    GNOME Terminal, GNOME
    Bugzilla
    2
    ------------------------
    ...

There's also a convenient link to take you to the page where you
register a new tracker:

    >>> user_browser.getLink("Register another bug tracker").click()
    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/+newbugtracker'
