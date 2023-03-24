External bug trackers
=====================

Launchpad can link to bugs in external bug trackers. The list of bug
trackers Launchpad knows about is accessible from the Bugs front page.

    >>> user_browser.open("http://bugs.launchpad.test/")
    >>> user_browser.getLink("bug trackers").click()
    >>> user_browser.title
    'Bug trackers registered in Launchpad'

Anyone logged in is able to register a new bug tracker.

    >>> user_browser.getLink("Register another bug tracker").click()
    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/+newbugtracker'

    >>> print(user_browser.title)
    Register an external bug tracker...

In case the user gets cold feet, there is always a cancel link that
takes them back to the bug tracker listing page.

    >>> user_browser.getLink("Cancel").url
    'http://bugs.launchpad.test/bugs/bugtrackers'

Supported external bug tracker types include Bugzilla, Debbugs, Roundup,
SourceForge and Trac. We don't provide all of these as options to the
user. We don't provide Debbugs because the status synchronisation script
requires manual set up of a bug archive mirror.

    >>> for control in user_browser.getControl("Bug Tracker Type").controls:
    ...     print(control.optionValue)
    ...
    Bugzilla
    Roundup
    Trac
    SourceForge or SourceForge derivative
    Mantis
    Request Tracker (RT)
    Savane
    PHP Project Bugtracker
    Google Code
    GitHub Issues
    GitLab Issues

The bug tracker name is used in URLs and certain characters (like '!')
aren't allowed.

    >>> user_browser.getControl("Name").value = "testmantis!"
    >>> user_browser.getControl("Bug Tracker Type").getControl(
    ...     "Mantis"
    ... ).click()
    >>> user_browser.getControl("Title").value = "Test Mantis Tracker"
    >>> user_browser.getControl(
    ...     "Summary"
    ... ).value = "This is a test MANTIS tracker."
    >>> url = "http://mantis.testing.org/"
    >>> user_browser.getControl("Location").value = url
    >>> user_browser.getControl("Contact details").value = "blah blah"
    >>> user_browser.getControl("Add").click()

    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/+newbugtracker'

    >>> for message in find_tags_by_class(user_browser.contents, "message"):
    ...     print(extract_text(message))
    ...
    There is 1 error.
    Invalid name 'testmantis!'.  Names must be at least two characters ...

If a bug tracker is already registered with the same location, the user
is informed about it.

    >>> user_browser.getControl("Name").value = "testmantis"
    >>> user_browser.getControl(
    ...     "Location"
    ... ).value = "http://bugzilla.mozilla.org/"
    >>> user_browser.getControl("Add").click()

    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/+newbugtracker'

    >>> for message in find_tags_by_class(user_browser.contents, "message"):
    ...     print(extract_text(message))
    ...
    There is 1 error.
    http://bugzilla.mozilla.org/ is already registered in Launchpad
    as "The Mozilla.org Bug Tracker" (mozilla.org).

The same happens if the requested URL is aliased to another bug tracker.
Aliases can be edited once a bug tracker has been added, but for now
we'll dig directly to the database.

    >>> from zope.component import getUtility
    >>> from lp.bugs.interfaces.bugtracker import (
    ...     BugTrackerType,
    ...     IBugTrackerSet,
    ... )
    >>> from lp.testing import login, logout
    >>> login("test@canonical.com")
    >>> gnome_bugzilla = getUtility(IBugTrackerSet).getByName(
    ...     "gnome-bugzilla"
    ... )
    >>> gnome_bugzilla.aliases = ["http://alias.example.com/"]
    >>> logout()

    >>> user_browser.getControl(
    ...     "Location"
    ... ).value = "http://alias.example.com/"
    >>> user_browser.getControl("Add").click()

    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/+newbugtracker'

    >>> for message in find_tags_by_class(user_browser.contents, "message"):
    ...     print(extract_text(message))
    ...
    There is 1 error.
    http://alias.example.com/ is already registered in Launchpad
    as "GnomeGBug GTracker" (gnome-bugzilla).

After successfully registering the bug tracker, the user is redirected
to the bug tracker page.

    >>> user_browser.getControl("Location").value = url
    >>> user_browser.getControl("Add").click()

    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/testmantis'

    >>> print(user_browser.title)
    Test Mantis Tracker : Bug trackers

    >>> "Test Mantis Tracker" in user_browser.contents
    True

    >>> "This is a test MANTIS tracker." in user_browser.contents
    True

For Email Address bug trackers, we show the upstream email address as
the location of the bug tracker, but obfuscate it for anonymous users:

    >>> user_browser.open("http://launchpad.test/bugs/bugtrackers/email")
    >>> user_bugtracker_url_list = find_tag_by_id(
    ...     user_browser.contents, "bugtracker-urls"
    ... )
    >>> anon_browser.open("http://launchpad.test/bugs/bugtrackers/email")
    >>> anon_bugtracker_url_list = find_tag_by_id(
    ...     anon_browser.contents, "bugtracker-urls"
    ... )

    >>> print(extract_text(user_bugtracker_url_list))
    mailto:bugs@example.com

    >>> print(extract_text(anon_bugtracker_url_list))
    mailto:&lt;email address hidden&gt;

The `Summary` and `Contact Details` fields are optional - creating a
bugtracker without them is acceptable.

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/+newbugtracker"
    ... )
    >>> user_browser.getControl("Name").value = "test-bugzilla"
    >>> user_browser.getControl("Title").value = "Test Bugzilla"
    >>> user_browser.getControl("Bug Tracker Type").value = ["Bugzilla"]
    >>> user_browser.getControl(
    ...     "Location"
    ... ).value = "http://bugzilla.example.org/"
    >>> user_browser.getControl("Add").click()
    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/test-bugzilla'

    >>> login("test@canonical.com")
    >>> bugtrackerset = getUtility(IBugTrackerSet)
    >>> test_tracker = bugtrackerset.getByName("testmantis")
    >>> test_tracker.bugtrackertype == BugTrackerType.MANTIS
    True

    >>> logout()

If we try to add a bugtracker with the same name of a existing one,
we'll get a nice error message.

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/+newbugtracker"
    ... )

    >>> user_browser.getControl("Name").value = "testmantis"
    >>> user_browser.getControl("Bug Tracker Type").getControl(
    ...     "Mantis"
    ... ).click()
    >>> user_browser.getControl("Title").value = "Test Mantis Tracker"
    >>> user_browser.getControl(
    ...     "Summary"
    ... ).value = "This is a test TRAC tracker."
    >>> url = "http://trac.example.org/tickets"
    >>> user_browser.getControl("Location").value = url
    >>> user_browser.getControl("Contact details").value = "blah blah"
    >>> user_browser.getControl("Add").click()

    >>> message = "testmantis is already in use by another bugtracker."
    >>> message in user_browser.contents
    True

We can edit the details of the newly added bugtracker.

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/testmantis/"
    ... )
    >>> user_browser.getLink("Change details").click()

    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/testmantis/+edit'

    >>> print(user_browser.title)
    Change details for the...

    >>> user_browser.getControl("Name").value = "testbugzilla"
    >>> user_browser.getControl("Title").value = "A test Bugzilla Tracker"
    >>> user_browser.getControl("Bug Tracker Type").getControl(
    ...     "Bugzilla"
    ... ).click()
    >>> user_browser.getControl(
    ...     "Summary"
    ... ).value = "This is used to be a test TRAC bug tracker."

There is a cancel link if we change our mind:

    >>> user_browser.getLink("Cancel").url
    'http://bugs.launchpad.test/bugs/bugtrackers/testmantis'

It's not possible to change the base URL to something that another bug
tracker uses.

    >>> user_browser.getControl(
    ...     "Location", index=0
    ... ).value = "http://bugzilla.mozilla.org/"
    >>> user_browser.getControl("Change").click()

    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/testmantis/+edit'

    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    http://bugzilla.mozilla.org/ is already registered in Launchpad
    as "The Mozilla.org Bug Tracker" (mozilla.org).

If the user inadvertently enters an invalid URL, they are shown an
informative error message explaining why it is invalid.

    >>> user_browser.getControl(
    ...     "Location", index=0
    ... ).value = "what? my wife does this stuff"
    >>> user_browser.getControl("Change").click()

    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    "what? my wife does this stuff" is not a valid URI

    >>> user_browser.getControl(
    ...     "Location", index=0
    ... ).value = "http://ξνεr.been.fishing?"
    >>> user_browser.getControl("Change").click()

    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    URIs must consist of ASCII characters

After successfully editing the bug tracker information, the user is
redirected to the bug tracker page. Note that the change we made to the
bugtracker name is reflected in the url.

    >>> user_browser.getControl("Location", index=0).value = url
    >>> user_browser.getControl("Change").click()

    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/testbugzilla'

And now the test tracker should have been updated:

    >>> "A test Bugzilla Tracker" in user_browser.contents
    True

    >>> "This is used to be a test TRAC bug tracker." in user_browser.contents
    True

    >>> login("test@canonical.com")
    >>> test_tracker = bugtrackerset.getByName("testbugzilla")
    >>> test_tracker.bugtrackertype == BugTrackerType.BUGZILLA
    True

    >>> logout()

But we forgot, the URL we need actually uses the https scheme. It's easy
to change.

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/testbugzilla"
    ... )
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(user_browser.contents, "bugtracker-urls")
    ...     )
    ... )
    http://trac.example.org/tickets
    http://mantis.testing.org/ (Alias)

    >>> user_browser.getLink("Change details").click()
    >>> user_browser.getControl(
    ...     "Location", index=0
    ... ).value = "https://trac.example.org/tickets"
    >>> user_browser.getControl("Change").click()

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(user_browser.contents, "bugtracker-urls")
    ...     )
    ... )
    https://trac.example.org/tickets
    http://mantis.testing.org/ (Alias)


Aliases
-------

We can associate multiple URLs or email addresses with a bug tracker. An
alias can represent another valid location for a bug tracker, or just a
commonly seen typo. Aliases are used to catch user mistakes; only the
primary Location is used to access the remote bug tracker.

They're added on the normal Change Details page.

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/testbugzilla"
    ... )
    >>> user_browser.getLink("Change details").click()

    >>> user_browser.getControl(
    ...     "Location aliases"
    ... ).value = "http://pseudonym.example.com/"
    >>> user_browser.getControl("Change").click()

    >>> bugtracker_url_list = find_tag_by_id(
    ...     user_browser.contents, "bugtracker-urls"
    ... )
    >>> print(extract_text(bugtracker_url_list))
    https://trac.example.org/tickets
    http://pseudonym.example.com/ (Alias)

It's not possible to add an alias that already refers to another
bugtracker.

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/testbugzilla/+edit"
    ... )
    >>> user_browser.getControl(
    ...     "Location aliases"
    ... ).value = "http://bugzilla.mozilla.org/"
    >>> user_browser.getControl("Change").click()

    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    http://bugzilla.mozilla.org/ is already registered in Launchpad
    as "The Mozilla.org Bug Tracker" (mozilla.org).

Multiple aliases can be entered by separating URLs with whitespace.

    >>> user_browser.getControl("Location aliases").value = (
    ...     "    http://wolverhampton.example.com/    "
    ...     "  http://toadhall.example.com/      \n"
    ...     "mailto:cupboardy@notaword.com "
    ...     " https://wibble.example.com/   \n\n\n"
    ... )
    >>> user_browser.getControl("Change").click()

    >>> bugtracker_url_list = find_tag_by_id(
    ...     user_browser.contents, "bugtracker-urls"
    ... )
    >>> print(extract_text(bugtracker_url_list))
    https://trac.example.org/tickets
    http://toadhall.example.com/ (Alias)
    http://wolverhampton.example.com/ (Alias)
    https://wibble.example.com/ (Alias)
    mailto:cupboardy@notaword.com (Alias)

If the user inadvertently enters one or more invalid URLs, they are
shown informative error messages.

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/testbugzilla/+edit"
    ... )
    >>> user_browser.getControl(
    ...     "Location aliases"
    ... ).value = "ξνεr been http://fishing?"
    >>> user_browser.getControl("Change").click()

    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    URIs must consist of ASCII characters
    "been" is not a valid URI


Deleting a bug tracker
----------------------

The Delete button is in the Change Details page. But first we need an
example bug tracker:

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/+newbugtracker"
    ... )
    >>> user_browser.getControl("Name").value = "freddy"
    >>> user_browser.getControl("Title").value = "Freddy's Bugs"
    >>> user_browser.getControl(
    ...     "Location"
    ... ).value = "http://freddy.example.com/"
    >>> user_browser.getControl("Add").click()

Being brand-new and pristine, there will be nothing to prevent its
deletion yet:

    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers/freddy'

    >>> user_browser.getLink("Change details").click()
    >>> user_browser.getControl("Delete").click()

    >>> user_browser.url
    'http://bugs.launchpad.test/bugs/bugtrackers'

    >>> print_feedback_messages(user_browser.contents)
    Freddy's Bugs has been deleted.

Bug trackers can be deleted by anyone, subject to a few restrictions:

- Firstly, deletion will be denied if bug tracker is set as the

  official bug tracker for a product or product group.

- Secondly, only certain privileged users can delete the bug watches

  for a bug tracker en masse.

- Thirdly, no bug tracker can be deleted if messages have been

  imported via one if its bug watches.

- Finally, if a bug tracker is also a Launchpad Celebrity it may not

  be deleted.

These conditions are checked on entry to the bug tracker edit page and
also on form submission. If the conditions are not met, the delete
button is not displayed and a list of reasons are shown.

The first and second restrictions both apply to the GNOME Bugzilla:

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/gnome-bugzilla/+edit"
    ... )
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             user_browser.contents,
    ...             "bugtracker-delete-not-possible-reasons",
    ...         )
    ...     )
    ... )
    Please note, this bug tracker cannot be deleted because:
      This is the bug tracker for GNOME and GNOME Terminal.
      There are linked bug watches and only members of ...Launchpad
        Administrators...

    >>> user_browser.getControl("Delete")
    Traceback (most recent call last):
    ...
    LookupError: label ...'Delete'
    ...

Note how we tell the user about _all_ the restrictions they face. In
this instance the user would have the option of persuading the GNOME
Project to use Launchpad to track bugs then asking an administrator to
delete the bug tracker, or, more likely, abandon their quest. (And even
if GNOME did switch to Launchpad, we'd probably still keep the tracker
for historical purposes.)

The second, third and fourth restrictions apply to the Debian Bug
Tracker:

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/debbugs/+edit"
    ... )

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             user_browser.contents,
    ...             "bugtracker-delete-not-possible-reasons",
    ...         )
    ...     )
    ... )
    Please note, this bug tracker cannot be deleted because:
      There are linked bug watches and only members of ...Launchpad
        Administrators...

    >>> user_browser.getControl("Delete")
    Traceback (most recent call last):
    ...
    LookupError: label ...'Delete'
    ...

Again, we tell the user about all the restrictions they have stumbled
on. A more privileged user would not stumble at the second hurdle,
deleting bug watches en masse:

    >>> admin_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/debbugs/+edit"
    ... )
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             admin_browser.contents,
    ...             "bugtracker-delete-not-possible-reasons",
    ...         )
    ...     )
    ... )
    Please note, this bug tracker cannot be deleted because:
      Bug comments have been imported via this bug tracker.
      This bug tracker is protected from deletion.

    >>> admin_browser.getControl("Delete")
    Traceback (most recent call last):
    ...
    LookupError: label ...'Delete'
    ...


Disabling a bug tracker
-----------------------

It's also possible for bug trackers to be disabled, for example if they
misbehave and cause a lot of noise in the checkwatches output.

Ordinary users can't disable a bug tracker.

    >>> user_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/debbugs/+edit"
    ... )
    >>> user_browser.getControl(name="field.active")
    Traceback (most recent call last):
      ...
    LookupError: name ...'field.active'
    ...

But admins can.

    >>> admin_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/debbugs/+edit"
    ... )
    >>> admin_browser.getControl(name="field.active").value = ["Off"]
    >>> admin_browser.getControl("Change").click()

    >>> message = find_tag_by_id(admin_browser.contents, "inactive-message")
    >>> print(extract_text(message))
    Bug watch updates for Debian Bug tracker are disabled.

If a user looks at a disabled bug tracker they'll see a message
notifying them that it has been disabled.

    >>> user_browser.open("http://launchpad.test/bugs/bugtrackers/debbugs")
    >>> message = find_tag_by_id(user_browser.contents, "inactive-message")
    >>> print(extract_text(message))
    Bug watch updates for Debian Bug tracker are disabled.

And if the users views a bug with a watch against a disabled bug tracker
they'll see a notification telling them that the bug tracker has been
disabled.

    >>> user_browser.open("http://launchpad.test/bugs/15")
    >>> print_feedback_messages(user_browser.contents)
    Bug watch updates for Debian Bug tracker are disabled.

Inactive bug trackers are displayed in a separate table from the active
ones on the bug tracker index page.

    >>> user_browser.open("http://launchpad.test/bugs/bugtrackers")
    >>> inactive_trackers_table = find_tag_by_id(
    ...     user_browser.contents, "inactive-trackers"
    ... )
    >>> print(extract_text(inactive_trackers_table))
    Title               Location...
    Debian Bug tracker  http://bugs.debian.org...

The admin can re-activate the bug tracker.

    >>> admin_browser.open(
    ...     "http://launchpad.test/bugs/bugtrackers/debbugs/+edit"
    ... )
    >>> admin_browser.getControl(name="field.active").value = ["On"]
    >>> admin_browser.getControl("Change").click()

    >>> message = find_tag_by_id(user_browser.contents, "inactive-message")
    >>> print(message)
    None

The user will no longer see any messages.

    >>> user_browser.open("http://launchpad.test/bugs/bugtrackers/debbugs")
    >>> message = find_tag_by_id(user_browser.contents, "inactive-message")
    >>> print(message)
    None

The message won't appear on the bug pages either.

    >>> user_browser.open("http://launchpad.test/bugs/15")
    >>> print_feedback_messages(user_browser.contents)

And the inactive bug trackers table will have disappeared since there
are no inactive bug trackers.

    >>> inactive_trackers_table = find_tag_by_id(
    ...     user_browser.contents, "inactive-trackers"
    ... )
    >>> print(inactive_trackers_table)
    None


Overview pages
--------------

When looking at a bug tracker page, a list of bug watches is displayed:

    >>> anon_browser.open("http://launchpad.test/bugs/bugtrackers/debbugs")
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(anon_browser.contents, "latestwatches")
    ...     )
    ... )
    Launchpad bug  Remote bug  Status  Last check  Next check
    #15: Nonse...  308994      open...
    #3:  Bug T...  327549
    #2:  Black...  327452
    #1:  Firef...  304014
    #7:  A tes...  280883

Scheduling any of the watches will change their "Next check" column.

    >>> from datetime import datetime, timezone
    >>> from zope.security.proxy import removeSecurityProxy

    >>> login("foo.bar@canonical.com")
    >>> debbugs = getUtility(IBugTrackerSet).getByName("debbugs")
    >>> watch_15 = debbugs.watches[0]
    >>> removeSecurityProxy(watch_15).next_check = datetime(
    ...     2010, 4, 9, 9, 50, 0, tzinfo=timezone.utc
    ... )
    >>> logout()

    >>> anon_browser.open("http://launchpad.test/bugs/bugtrackers/debbugs")
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(anon_browser.contents, "latestwatches")
    ...     )
    ... )
    Launchpad bug  Remote bug  Status  Last check  Next check
    #15: Nonse...  308994      open... 2007-12-18    2010-04-09 09:50:00 UTC
    #3:  Bug T...  327549
    #2:  Black...  327452
    #1:  Firef...  304014
    #7:  A tes...  280883


Private bugs
............

If the user is not permitted to view one of the watches only very basic
details are displayed. For example, when a bug watch is associated with
a private bug:

    >>> admin_browser.open(
    ...     "http://launchpad.test/debian/+source/mozilla-firefox/+bug/3/"
    ...     "+secrecy"
    ... )
    >>> admin_browser.getControl("Private", index=1).selected = True
    >>> admin_browser.getControl("Change").click()

    >>> anon_browser.open("http://launchpad.test/bugs/bugtrackers/debbugs")
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(anon_browser.contents, "latestwatches")
    ...     )
    ... )
    Launchpad bug                      Remote bug  Status...
    #15: Nonse...                      308994...
    #3:  (Private)                     -
    #2:  Blackhole Trash folder        327452
    #1:  Firefox does not support SVG  304014
    #7:  A test bug                    280883

Note that even the remote bug number is hidden.

But... why doesn't Launchpad just show me the watches that I'm allowed
to see, and omit the rest?

Firstly, for this to work, Launchpad would need to recalculate totals on
the bug tracker summary page (/bugs/bugtrackers) and in each bug tracker
page (e.g. /bugs/bugtrackers/debbugs). That's complex and not good for
performance, and the work needed to make the performance good would make
it fragile. Without the recalculated totals it would be confusing for
users, and look like Launchpad is broken.

Secondly, these pages are also useful for administrators and users of
the remote trackers to see what's going on. Giving them an adjusted
total is misleading. There would be a disconnect between what Launchpad
reports and what it does, which again could lead them to think that
Launchpad is broken or lying.


Anonymous users
...............

Email addresses in remote watch URLs are obfuscated when viewed by
anonymous users.

First we must create a new bug watch on an Email Address bug tracker:

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test"
    ...     "/jokosher/+bug/12/+choose-affected-product"
    ... )
    >>> user_browser.getControl("Project").value = "gnome-terminal"
    >>> user_browser.getControl("Continue").click()
    >>> user_browser.getControl(name="field.link_upstream_how").value = [
    ...     "EMAIL_UPSTREAM_DONE"
    ... ]
    >>> user_browser.getControl(
    ...     name="field.upstream_email_address_done"
    ... ).value = "bugs@example.com"
    >>> user_browser.getControl("Add to Bug Report").click()

Then we can see how logged-in users and anonymous users see the page:

    >>> def print_watches(browser):
    ...     watches = find_tag_by_id(
    ...         browser.contents, "latestwatches"
    ...     ).tbody.find_all("tr")
    ...     for watch in watches:
    ...         (
    ...             bug,
    ...             remote_bug,
    ...             status,
    ...             last_checked,
    ...             next_check,
    ...         ) = watch.find_all("td")
    ...         print(extract_text(bug))
    ...         print(
    ...             "  --> %s: %s"
    ...             % (
    ...                 extract_text(remote_bug),
    ...                 (remote_bug.a and remote_bug.a.get("href")),
    ...             )
    ...         )
    ...

    >>> user_browser.open("http://launchpad.test/bugs/bugtrackers/email")
    >>> print_watches(user_browser)
    #12:
    Copy, Cut and Delete operations should work on selections
      --> —: mailto:bugs@example.com

    >>> anon_browser.open("http://launchpad.test/bugs/bugtrackers/email")
    >>> print_watches(anon_browser)
    #12:
    Copy, Cut and Delete operations should work on selections
      --> —: None

Info portlet
------------

Some information about the bug tracker is displayed in a portlet on the
bug tracker page.

    >>> user_browser.open("http://launchpad.test/bugs/bugtrackers/email")
    >>> print(extract_text(find_portlet(user_browser.contents, "Details")))
    Details
    Location:
    mailto:bugs@example.com
    Tracker type:
    Email Address
    Created by:
    Foo Bar

If the user is not logged in, email addresses in the Location field
above are obfuscated:

    >>> anon_browser.open("http://launchpad.test/bugs/bugtrackers/email")
    >>> print(extract_text(find_portlet(anon_browser.contents, "Details")))
    Details
    Location:
    mailto:&lt;email address hidden&gt;
    ...

If the bug tracker has contact details, they will be shown:

    >>> anon_browser.open(
    ...     "http://bugs.launchpad.test/bugs/bugtrackers/gnome-bugzilla"
    ... )
    >>> print(extract_text(find_portlet(anon_browser.contents, "Details")))
    Details
    Location:
    http://bugzilla.gnome.org/bugs
    http://alias.example.com/ (Alias)
    Tracker type:
    Bugzilla
    Contact details:
    Jeff Waugh, in his pants.
    Created by:
    Foo Bar


