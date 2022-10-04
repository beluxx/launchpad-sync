Bug listings
============

This test looks at various aspects of bug listings. Here's a very basic
use case: Sample Person views the bug task listing for the Mozilla
project.  Bugs in the Firefox product are displayed.

    >>> from lp.bugs.tests.bug import print_bugtasks
    >>> user_browser.open("http://launchpad.test/mozilla/+bugs")
    >>> print_bugtasks(user_browser.contents)
    15 Nonsensical bugs are useless Mozilla
     Thunderbird Unknown New
    5 Firefox install instructions should be complete
     Mozilla Firefox Critical New
    4 Reflow problems with complex page layouts
     Mozilla Firefox Medium New
    1 Firefox does not support SVG
     Mozilla Firefox Low New

Debian must enable the Launchpad bug tracker to access bugs.

    >>> from lp.testing.service_usage_helpers import set_service_usage
    >>> set_service_usage("debian", bug_tracking_usage="LAUNCHPAD")

Bug listings default to open bugtasks:

    >>> user_browser.open("http://launchpad.test/debian/+bugs")
    >>> print_bugtasks(user_browser.contents)
    3 Bug Title Test mozilla-firefox (Debian) Unknown New
    1 Firefox does not support SVG mozilla-firefox (Debian) Low Confirmed
    2 Blackhole Trash folder mozilla-firefox (Debian) Low Confirmed

But you can make it show fixed ones to:

    >>> user_browser.open(
    ...     "http://launchpad.test/debian/+bugs"
    ...     "?field.status=FIXRELEASED&search=Search"
    ... )
    >>> print_bugtasks(user_browser.contents)
    8 Printing doesn't work mozilla-firefox (Debian) Medium Fix Released


Example listings
----------------

An anonymous user views the bug tasks in upstream Ubuntu.

    >>> set_service_usage("tomcat", bug_tracking_usage="LAUNCHPAD")
    >>> anon_browser.open("http://launchpad.test/tomcat/+bugs")
    >>> print_bugtasks(anon_browser.contents)
    2 Blackhole Trash folder Tomcat Low New

Foo Bar views the upstream Ubuntu bug tasks listing. Note that they can
see the extra "quick search" links "my todo list" and "submitted by
me".

    >>> admin_browser.open("http://launchpad.test/tomcat/+bugs")
    >>> print_bugtasks(admin_browser.contents)
    2 Blackhole Trash folder Tomcat Low New

Sample Person views the bug task listing. Since they're the upstream
Firefox maintainer, they also see the Assign to Milestone widget.

    >>> user_browser.open("http://launchpad.test/firefox/+bugs")
    >>> print_bugtasks(user_browser.contents)
    5 Firefox install instructions should be complete
     Mozilla Firefox Critical New
    4 Reflow problems with complex page layouts
     Mozilla Firefox Medium New
    1 Firefox does not support SVG
     Mozilla Firefox Low New

View the distribution bug listing as Foo Bar, who's a maintainer.

    >>> admin_browser.open("http://launchpad.test/ubuntu/+bugs")
    >>> print_bugtasks(admin_browser.contents)
    1 Firefox does not support SVG mozilla-firefox (Ubuntu) Medium New
    9 Thunderbird crashes thunderbird (Ubuntu) Medium Confirmed
    10 another test bug linux-source-2.6.15 (Ubuntu) Medium New
    2 Blackhole Trash folder Ubuntu Medium New

If inadvertently we copy and paste a newline character in the search
text field, it'll be replaced by spaces and the search will work fine.

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/+bugs"
    ...     "?field.searchtext=blackhole%0D%0Atrash%0D%0Afolder&search=Search"
    ...     "&orderby=-importance"
    ... )
    >>> user_browser.getControl(name="field.searchtext").value
    'blackhole trash folder'
    >>> print_bugtasks(user_browser.contents)
    2 Blackhole Trash folder Ubuntu Medium New

Do an advanced search with dupes turned on and find the duplicate in the
results.

    >>> anon_browser.open(
    ...     "http://launchpad.test/firefox/+bugs"
    ...     "?field.searchtext=&field.status%3Alist=New"
    ...     "&field.status%3Alist=Confirmed&field.status-empty-marker=1"
    ...     "&field.importance-empty-marker=1&field.assignee="
    ...     "&field.unassigned.used=&field.omit_dupes="
    ...     "&field.milestone-empty-marker=1&search=Search"
    ... )
    >>> print_bugtasks(anon_browser.contents)
    5 Firefox install instructions should be complete
     Mozilla Firefox Critical New
    6 Firefox crashes when Save As dialog for a nonexistent window is closed
     Mozilla Firefox High New
    4 Reflow problems with complex page layouts
     Mozilla Firefox Medium New
    1 Firefox does not support SVG
     Mozilla Firefox Low New


Critical bugs
-------------

A list of critical bugs reported in a given upstream can be viewed by
clicking the "critical" quick search link. Debian has no open critical bugs:

    >>> user_browser.open(
    ...     "http://launchpad.test/debian/+bugs"
    ...     "?field.status%3Alist=New&field.status%3Alist=Confirmed"
    ...     "&field.importance%3Alist=Critical&search=Search"
    ... )
    >>> print_bugtasks(user_browser.contents)
    <BLANKLINE>

But Firefox has a fixed one that Foo Bar can see:

    >>> admin_browser.open(
    ...     "http://launchpad.test/firefox/+bugs"
    ...     "?search=Search&field.importance=Critical&field.status=New"
    ...     "&field.status=Confirmed&field.status=In+Progress"
    ...     "&field.status=Incomplete&field.status=Fix+Committed"
    ... )
    >>> print_bugtasks(admin_browser.contents)
    5 Firefox install instructions should be complete
     Mozilla Firefox Critical New


My todo list
------------

The "my todo list" link gives the logged in user the ability to
quickly see which bugs have been assigned to them.

    >>> user_browser.open(
    ...     "http://launchpad.test/debian/+bugs"
    ...     "?field.status%3Alist=New&field.status%3Alist=Confirmed"
    ...     "&field.assignee=name12&search=Search"
    ... )
    >>> print_bugtasks(user_browser.contents)
    2 Blackhole Trash folder mozilla-firefox (Debian) Low Confirmed

This also works for upstream listings:

    >>> user_browser.open(
    ...     "http://launchpad.test/firefox/+bugs"
    ...     "?field.assignee=name12&search=Search"
    ... )
    >>> print_bugtasks(user_browser.contents)
    5 Firefox install instructions should be complete
     Mozilla Firefox Critical New


Looking at unassigned bugs
--------------------------

View the unassigned bug tasks listing as user Sample Person.

    >>> user_browser.open(
    ...     "http://launchpad.test/firefox/+bugs"
    ...     "?searchtext=&field.milestone-empty-marker=1"
    ...     "&field.status%3Alist=New&field.status%3Alist=Confirmed"
    ...     "&field.status-empty-marker=1&field.importance-empty-marker=1"
    ...     "&assignee_option=none&field.assignee="
    ...     "&field.milestone-empty-marker=1&search=Search"
    ... )
    >>> print_bugtasks(user_browser.contents)
    4 Reflow problems with complex page layouts
     Mozilla Firefox Medium New


Search criteria is persistent
-----------------------------

The bug listing pages save their search criteria.

    >>> browser.open("http://launchpad.test/ubuntu/+bugs")
    >>> print_bugtasks(browser.contents)
    1 Firefox does not support SVG mozilla-firefox (Ubuntu) Medium New
    9 Thunderbird crashes thunderbird (Ubuntu) Medium Confirmed
    10 another test bug linux-source-2.6.15 (Ubuntu) Medium New
    2 Blackhole Trash folder Ubuntu Medium New

If, for example, you click on one of the canned search links. These
links are in the portlet "Filters"; its content is served in a separate
request, issued by regular browsers via Javascript.

    >>> browser.open(
    ...     "http://launchpad.test/ubuntu/+bugtarget-portlet-bugfilters-info"
    ... )
    >>> browser.getLink("New").click()

The result set is filtered to show only New bugs.

    >>> print_bugtasks(browser.contents)
    1 Firefox does not support SVG mozilla-firefox (Ubuntu) Medium New
    10 another test bug linux-source-2.6.15 (Ubuntu) Medium New
    2 Blackhole Trash folder Ubuntu Medium New


Searching for simple strings
----------------------------

The bugtask search facility supports searching on a simple text
string.

    >>> user_browser.open(
    ...     "http://launchpad.test/firefox/+bugs"
    ...     "?field.searchtext=install&search=Search&advanced=&milestone=1"
    ...     "&status=10&status=20&assignee=all"
    ... )
    >>> print_bugtasks(user_browser.contents)
    5 Firefox install instructions should be complete
     Mozilla Firefox Critical New
    1 Firefox does not support SVG
     Mozilla Firefox Low New

If we search for something and get no matches, it'll say so in a meaningful
way instead of displaying an empty table.

    >>> user_browser.open(
    ...     "http://launchpad.test/firefox/+bugs"
    ...     "?field.searchtext=fdsadsf&search=Search&advanced=&milestone=1"
    ...     "&status=10&status=20&assignee=all"
    ... )
    >>> print(user_browser.contents)
    <...
    ...No results for search...
    ...

Similarly, if we don't do a search and there are no open bugs on that product,
it'll say so.

    >>> set_service_usage("iso-codes", bug_tracking_usage="LAUNCHPAD")
    >>> user_browser.open("http://launchpad.test/iso-codes/+bugs")
    >>> print(user_browser.contents)
    <...
    ...There are currently no open bugs...
    ...


Bug Badge Decoration
--------------------

We display bug badges for associated branches, specifications, patches, etc.

    >>> def names_and_branches(contents):
    ...     listing = find_tag_by_id(contents, "bugs-table-listing")
    ...     for row in listing.find_all(None, {"class": "buglisting-row"}):
    ...         badge_cell = row.find(None, {"class": "bug-related-icons"})
    ...         spans = badge_cell.find_all("span")
    ...         for span in spans:
    ...             print("  Badge:", span.get("alt"))
    ...

For instance, these are the badges on the firefox bug listing:

    >>> browser.open("http://bugs.launchpad.test/firefox/+bugs")
    >>> names_and_branches(browser.contents)
      Badge: branch
      Badge: branch
      Badge: blueprint

Milestones are also presented as badges on bugs, and linked to the
relevant listings:

    >>> browser.open(
    ...     "http://bugs.launchpad.test/debian/sarge/+source/mozilla-firefox"
    ... )
    >>> milestone = find_tags_by_class(browser.contents, "sprite milestone")
    >>> print(milestone[0])
    <a alt="milestone 3.1" class="sprite milestone"
       href="http://launchpad.test/debian/+milestone/3.1"
       title="Linked to milestone 3.1"></a>


Patches also appear as badges in bug listings.

    >>> from io import BytesIO
    >>> from lp.testing import login, logout
    >>> from zope.component import getUtility
    >>> from lp.services.messages.interfaces.message import IMessageSet
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> import transaction
    >>> login("foo.bar@canonical.com")
    >>> foobar = getUtility(IPersonSet).getByName("name16")
    >>> message = getUtility(IMessageSet).fromText(
    ...     subject="test subject",
    ...     content="a comment for the attachment",
    ...     owner=foobar,
    ... )
    >>> bugset = getUtility(IBugSet)
    >>> bug_one = bugset.get(1)
    >>> bug_one.addAttachment(
    ...     owner=foobar,
    ...     data=BytesIO(b"file data"),
    ...     filename="foo.bar",
    ...     url=None,
    ...     description="this fixes the bug",
    ...     comment=message,
    ...     is_patch=True,
    ... )
    <lp.bugs.model.bugattachment.BugAttachment object at ...>
    >>> transaction.commit()
    >>> logout()
    >>> browser.open("http://bugs.launchpad.test/firefox/+bugs")
    >>> names_and_branches(browser.contents)
      Badge: branch
      Badge: branch
      Badge: blueprint
      Badge: haspatch


Bug heat in listings
--------------------

Bug listings display the bug heat in the last column. Heat is displayed
as a number.

    >>> user_browser.open(
    ...     "http://launchpad.test/firefox/+bugs"
    ...     "?field.searchtext=install&search=Search&advanced=&milestone=1"
    ...     "&status=10&status=20&assignee=all"
    ... )
    >>> print_bugtasks(user_browser.contents, show_heat=True)
    5 Firefox install instructions should be complete
     Mozilla Firefox Critical New 0
    1 Firefox does not support SVG
     Mozilla Firefox Low New 4

