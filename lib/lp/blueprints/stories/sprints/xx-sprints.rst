Launchpad Sprint Tracker
========================

Launchpad lets us register a meeting, and then keep track of which specs are
due to be discussed at that meeting. As a result we can schedule and
prioritize BOF's at the meeting, using an as-yet-undeveloped
schedul-o-matic.

    >>> import datetime as dt
    >>> from pytz import UTC
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login("test@canonical.com")
    >>> rome_sprint = factory.makeSprint(name="rome", title="Rome")
    >>> logout()
    >>> ignored = login_person(rome_sprint.owner)
    >>> rome_sprint.time_ends = dt.datetime.now(UTC) + dt.timedelta(30)
    >>> rome_sprint.time_starts = dt.datetime.now(UTC) + dt.timedelta(20)
    >>> sample_person = getUtility(IPersonSet).getByName("name12")
    >>> rome_sprint.driver = sample_person
    >>> logout()

Let's start by viewing the list of sprints registered.

    >>> user_browser.open("http://launchpad.test/sprints")
    >>> user_browser.title
    'Meetings and sprints registered in Launchpad'

    >>> print(find_tag_by_id(user_browser.contents, "application-summary"))
    <p ...
      Launchpad can help you organize your developer sprints, summits and
      gatherings. Register the meeting here, then you can invite people to
      nominate blueprints for discussion at the event. The meeting drivers
      control the agenda, but everyone can see what's proposed and what's
      been accepted.
    </p>

Now lets have a look at one sprint in particular. We expect to have a sprint
called "paris" in the sample data. Note that this list only shows meetings
in the future, so there is a timebomb here for 2011 or so...

    >>> user_browser.getLink("Rome").click()
    >>> user_browser.url
    'http://launchpad.test/sprints/rome'

Creating new sprints
====================

We should also be able to create a new sprint. We do this off the
Sprints +new page.

    >>> user_browser.open("http://launchpad.test/sprints")
    >>> user_browser.getLink("Register a meeting").click()

    >>> print(user_browser.title)
    Register a meeting...

First we'll test the name field validator.

    >>> user_browser.getControl("Name").value = "ltsp_on_steroids!"
    >>> user_browser.getControl("Title").value = "LTSP On Steroids"
    >>> summary = "This is a sprint summary. Some words about the sprint"
    >>> user_browser.getControl("Summary").value = summary
    >>> user_browser.getControl("Driver").value = "kamion"
    >>> user_browser.getControl("Home Page").value = "http://www.willy.net"
    >>> user_browser.getControl("Timezone").value = ["UTC"]
    >>> user_browser.getControl(
    ...     "Starting Date and Time"
    ... ).value = "10 Oct 2006 09:15"
    >>> user_browser.getControl(
    ...     "Finishing Date and Time"
    ... ).value = "13 Oct 2006 16:00"
    >>> user_browser.getControl("Add Sprint").click()

    >>> for tag in find_tags_by_class(user_browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There is 1 error.
    <BLANKLINE>
    Invalid name 'ltsp_on_steroids!'. Names must be at least two characters...

Register a sprint with the same name of a existing one also returns a
nice error message

    >>> user_browser.getControl("Name").value = "ubz"
    >>> user_browser.getControl("Add Sprint").click()

    >>> for tag in find_tags_by_class(user_browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There is 1 error.
    <BLANKLINE>
    ubz is already in use by another sprint.

Create a new sprint with a finish date before the starting date returns
a error message.

    >>> user_browser.getControl("Name").value = "ltsponsteroids"
    >>> user_browser.getControl(
    ...     "Starting Date and Time"
    ... ).value = "13 Oct 2006 09:15 "
    >>> user_browser.getControl(
    ...     "Finishing Date and Time"
    ... ).value = "10 Oct 2006 16:00"
    >>> user_browser.getControl("Add Sprint").click()

    >>> for tag in find_tags_by_class(user_browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There is 1 error.
    <BLANKLINE>
    This event can't start after it ends

Also, the date is now presented in a canonicalised format, with time in
minutes rather than second-level accuracy:

    >>> user_browser.getControl("Starting Date and Time").value
    '2006-10-13 09:15'

    >>> user_browser.getControl("Finishing Date and Time").value
    '2006-10-10 16:00'

Fix the date and try again. We're redirected to the sprint home page for
the new sprint.

    >>> user_browser.getControl(
    ...     "Starting Date and Time"
    ... ).value = "10 Oct 2006 09:15 "
    >>> user_browser.getControl(
    ...     "Finishing Date and Time"
    ... ).value = "13 Oct 2006 16:00"
    >>> user_browser.getControl(
    ...     "Is the sprint being held in a physical " "location?"
    ... ).selected = False
    >>> user_browser.getControl("Add Sprint").click()

    >>> user_browser.url
    'http://launchpad.test/sprints/ltsponsteroids'

Since the sprint's time zone was set to UTC, the dates are displayed in
that time zone:

    >>> print(
    ...     extract_text(find_tag_by_id(user_browser.contents, "start-end"))
    ... )
    Starts: 09:15 UTC on Tuesday, 2006-10-10
    Ends: 16:00 UTC on Friday, 2006-10-13

Because this is a brand new sprint, it will have no specs, and we should
see a warning to that effect on the page.

    >>> message = "Nobody has yet proposed any blueprints for discussion"
    >>> message in user_browser.contents
    True

Add a new sprint with a different time zone is also handled correctly.

    >>> user_browser.open("http://launchpad.test/sprints/+new")
    >>> user_browser.getControl("Name").value = "africa-sprint"
    >>> user_browser.getControl("Title").value = "Africa Sprint"
    >>> summary = "This is a sprint summary. Some words about the sprint"
    >>> user_browser.getControl("Summary").value = summary
    >>> user_browser.getControl("Home Page").value = "http://www.ubuntu.com"
    >>> user_browser.getControl("Timezone").value = ["Africa/Johannesburg"]
    >>> user_browser.getControl(
    ...     "Starting Date and Time"
    ... ).value = "10 Jul 2006 09:15"
    >>> user_browser.getControl(
    ...     "Finishing Date and Time"
    ... ).value = "13 Jul 2006 16:00"
    >>> user_browser.getControl("Add Sprint").click()

    >>> user_browser.url
    'http://launchpad.test/sprints/africa-sprint'

    >>> print(
    ...     extract_text(find_tag_by_id(user_browser.contents, "start-end"))
    ... )
    Starts: 09:15 SAST on Monday, 2006-07-10
    Ends: 16:00 SAST on Thursday, 2006-07-13



We should be able to edit the details on a sprint but the menus are only
available to those who have permissions to edit that sprint.

    >>> anon_browser.open("http://launchpad.test/sprints/ubz")
    >>> print(anon_browser.title)
    Ubuntu Below Zero : Meetings

    >>> anon_browser.getLink("Change details")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

We will log in as Sample Person and edit the ubz sprint.

    >>> browser.addHeader("Authorization", "Basic test@canonical.com:test")

    >>> browser.open("http://launchpad.test/sprints/ubz")
    >>> print(browser.title)
    Ubuntu Below Zero : Meetings

    >>> address = "Holiday Inn Select, Downtown Montreal, Canada"
    >>> address in browser.contents
    False
    >>> browser.getLink("Change details").click()
    >>> browser.url
    'http://launchpad.test/sprints/ubz/+edit'
    >>> browser.getLink("Cancel").url
    'http://launchpad.test/sprints/ubz'

The sprint start and end times are expressed to the nearest minute, and
not the second:

    >>> start_control = browser.getControl("Starting Date and Time")
    >>> start_control.value
    '2005-10-07 19:30'
    >>> end_control = browser.getControl("Finishing Date and Time")
    >>> end_control.value
    '2005-11-16 19:11'

If we alter the date to an ending date that precedes the starting date we
should receive a nice error message.

    >>> start_control.value = "2006-01-10 23:30"
    >>> end_control.value = "2005-02-12 00:11"
    >>> browser.getControl("Change").click()

    >>> for tag in find_tags_by_class(browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There is 1 error.
    This event can't start after it ends

We fix the dates and change the address, we expect to be redirected to the
sprint home page.

    >>> browser.getControl("Timezone").value = ["America/Toronto"]
    >>> browser.getControl(
    ...     "Starting Date and Time"
    ... ).value = "2006-01-10 08:30"
    >>> browser.getControl(
    ...     "Finishing Date and Time"
    ... ).value = "2006-02-12 17:00"
    >>> browser.getControl("Meeting Address").value = address
    >>> browser.getControl("Change").click()

    >>> browser.url
    'http://launchpad.test/sprints/ubz'


The address of the sprint is now visible.

    >>> print(
    ...     extract_text(find_tag_by_id(browser.contents, "sprint-address"))
    ... )
    Address: Holiday Inn Select, Downtown Montreal, Canada

    >>> print(extract_text(find_tag_by_id(browser.contents, "start-end")))
    Starts: 08:30 EST on Tuesday, 2006-01-10
    Ends: 17:00 EST on Sunday, 2006-02-12


If we just change the time zone on the edit form, the start and finish
dates will be changed too, since they follow local time:

    >>> browser.open("http://launchpad.test/sprints/ubz/+edit")
    >>> browser.getControl("Timezone").value = ["Australia/Darwin"]
    >>> browser.getControl("Change").click()
    >>> print(browser.url)
    http://launchpad.test/sprints/ubz

    >>> print(extract_text(find_tag_by_id(browser.contents, "start-end")))
    Starts: 08:30 ACST on Tuesday, 2006-01-10
    Ends: 17:00 ACST on Sunday, 2006-02-12


We should be able to see the workload of a sprint:

    >>> anon_browser.open("http://launchpad.test/sprints/ubz/+assignments")
    >>> print(anon_browser.title)
    Assignments : Blueprints : Ubuntu Below Zero : Meetings

We should be able to see the spec assignment table of a sprint:

    >>> mainarea = find_main_content(anon_browser.contents)
    >>> for header in mainarea.find_all("th"):
    ...     print(header.decode_contents())
    ...
    Priority
    Name
    Definition
    Delivery
    Assignee
    Drafter
    Approver

And we should be able to see the workload page of a sprint even when there's
no spec assigned to people.

    >>> anon_browser.open(
    ...     "http://launchpad.test/sprints/ltsponsteroids/+assignments"
    ... )
    >>> notice = find_tag_by_id(anon_browser.contents, "no-blueprints")
    >>> print(extract_text(notice))
    There are no open blueprints.


Sprint Registration
===================

It should be possible to register yourself to attend the sprint:

    >>> browser.addHeader("Authorization", "Basic test@canonical.com:test")

    >>> browser.open("http://launchpad.test/sprints/ubz")

    >>> browser.getLink("Register yourself").click()
    >>> browser.url
    'http://launchpad.test/sprints/ubz/+attend'

    >>> print(browser.title)
    Register your attendance : Ubuntu Below Zero : Meetings

Invalid dates, for instance entering a starting date after the ending
date, are reported as errors to the users. (See also the tests in
lib/lp/blueprints/browser/tests/sprintattendance-views.rst)

By default, the form will be pre-filled out with arrival and departure
dates that correspond to the full length of the conference and imply the
user will be available to participate in any session.

    >>> browser.getControl("From").value
    '2006-01-10 08:30'

    >>> browser.getControl("To").value
    '2006-02-12 17:00'

    >>> browser.getControl(name="field.is_physical").value
    ['yes']

We accept a starting date up to one day before the sprint starts (which
we will map to starting at the start of the sprint), and a departure
date up to one day after the sprint ends.

    >>> browser.getControl("From").value = "2006-01-10 10:30:00"
    >>> browser.getControl("To").value = "2005-02-04 20:11:00"
    >>> browser.getControl("Register").click()

    >>> print(browser.url)
    http://launchpad.test/sprints/ubz/+attend

    >>> for tag in find_tags_by_class(browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There is 1 error.
    Please pick a date after 2006-01-10 08:30

An attendance that starts after the end of the sprint is also an error:

    >>> browser.getControl("From").value = "2010-01-10 10:30:00"
    >>> browser.getControl("To").value = "2010-07-10 22:11:00"
    >>> browser.getControl("Register").click()

    >>> print(browser.url)
    http://launchpad.test/sprints/ubz/+attend

    >>> for tag in find_tags_by_class(browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There are 2 errors.
    Please pick a date before 2006-02-12 17:00
    Please pick a date before 2006-02-13 17:00

Similarly, an attendance that ends before the start of a sprint is an
error:

    >>> browser.getControl("From").value = "1980-01-10 10:30:00"
    >>> browser.getControl("To").value = "1990-07-10 22:11:00"
    >>> browser.getControl("Register").click()

    >>> print(browser.url)
    http://launchpad.test/sprints/ubz/+attend

    >>> for tag in find_tags_by_class(browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There are 2 errors.
    Please pick a date after 2006-01-09 08:30
    Please pick a date after 2006-01-10 08:30

With the dates fixed, Sample person can attend the sprint.  The user is
staying an extra week past the end of the sprint, which is fine since
the date range overlaps that of the sprint.

    >>> browser.getControl("From").value = "2006-01-10 10:30:00"
    >>> browser.getControl("To").value = "2006-02-12 20:11:00"
    >>> browser.getControl("Register").click()
    >>> browser.url
    'http://launchpad.test/sprints/ubz'

Now, Sample Person should be listed as an attendee.

    >>> def print_attendees(sprint_page):
    ...     """Print the attendees listed in the attendees portlet."""
    ...     attendees_portlet = find_portlet(sprint_page, "Attendees")
    ...     for li in attendees_portlet.find_all("ul")[0].find_all("li"):
    ...         print(li.a.string)
    ...

    >>> print_attendees(browser.contents)
    Sample Person

If we return to the "Register Yourself" form, the previously entered
dates are prefilled (they have been clamped to the sprint duration):

    >>> browser.getLink("Register yourself").click()
    >>> print(browser.getControl("From").value)
    2006-01-10 10:30

    >>> print(browser.getControl("To").value)
    2006-02-12 17:00

Also, it is possible to register someone else. Let's register Carlos.

    >>> browser.open("http://launchpad.test/sprints/ubz")
    >>> browser.getLink("Register someone else").click()
    >>> browser.url
    'http://launchpad.test/sprints/ubz/+register'

By default, the form is pre-filled with attendance times that match the
start and end of the conference.

    >>> browser.getControl("From").value
    '2006-01-10 08:30'

    >>> browser.getControl("To").value
    '2006-02-12 17:00'

    >>> browser.getControl(name="field.is_physical").value
    ['yes']

Sample Person can set a specific start and end time for participation,
and specify that they are registering Carlos.

    >>> browser.getControl("Attendee").value = "carlos@canonical.com"
    >>> browser.getControl("From").value = "2006-01-10 18:30:00"
    >>> browser.getControl("To").value = "2006-02-12 15:11:00"
    >>> browser.getControl("Register").click()

    >>> browser.url
    'http://launchpad.test/sprints/ubz'

Sample Person registers Salgado as well.

    >>> browser.getLink("Register someone else").click()
    >>> browser.url
    'http://launchpad.test/sprints/ubz/+register'

    >>> browser.getControl(
    ...     "Attendee"
    ... ).value = "guilherme.salgado@canonical.com"
    >>> browser.getControl(name="field.is_physical").value = ["no"]
    >>> browser.getControl("Register").click()

And verifies that Carlos and Salgado are now listed:

    >>> print_attendees(browser.contents)
    Carlos Perelló Marín
    Guilherme Salgado
    Sample Person

In order to make it easy to organize a meeting, we provide a facility
for exporting the list of attendees in CSV format to registered users,
drivers, owners, and admins.

First, we add a couple of IRC nicknames for Carlos.

    >>> from operator import attrgetter
    >>> from lp.testing import login, logout
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.model.person import IrcID
    >>> login("carlos@canonical.com")
    >>> carlos = getUtility(IPersonSet).getByName("carlos")
    >>> IrcID(person=carlos, network="freenode", nickname="carlos")
    <IrcID at ...>

    >>> IrcID(person=carlos, network="QuakeNet", nickname="qarlos")
    <IrcID at ...>

    >>> for ircid in sorted(carlos.ircnicknames, key=attrgetter("nickname")):
    ...     print(ircid.nickname)
    ...
    carlos
    qarlos

    >>> logout()

    >>> browser.getLink("Export attendees to CSV").click()
    >>> print(browser.headers["content-type"])
    text/csv;charset=...utf-8...

    >>> carlos_browser = setupBrowser(auth="Basic carlos@canonical.com:test")
    >>> carlos_browser.open("http://launchpad.test/sprints/ubz")
    >>> carlos_browser.getLink("Export attendees to CSV").click()
    >>> print(carlos_browser.headers["content-type"])
    text/csv;charset=...utf-8...

    >>> admin_browser.open("http://launchpad.test/sprints/ubz")
    >>> admin_browser.getLink("Export attendees to CSV").click()
    >>> print(admin_browser.headers["content-type"])
    text/csv;charset=...utf-8...

The resulting CSV file lists physical attendance correctly.

    >>> import csv
    >>> import io
    >>> ubz_csv = list(csv.DictReader(io.StringIO(browser.contents)))
    >>> [
    ...     (row["Launchpad username"], row["Physically present"])
    ...     for row in ubz_csv
    ... ]
    [('carlos', 'True'), ('salgado', 'False'), ('name12', 'True')]

Unregistered and anonymous users cannot access the CSV report.

    >>> user_browser.open("http://launchpad.test/sprints/ubz")
    >>> user_browser.getLink("Export attendees to CSV").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> anon_browser.open("http://launchpad.test/sprints/ubz/+attendees-csv")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Registering somebody for a remote-only sprint doesn't offer the choice of
physical or remote attendance, and the CSV report always reports such people
as attending remotely.

    >>> browser.open("http://launchpad.test/sprints/ltsponsteroids")
    >>> browser.getLink("Register yourself").click()
    >>> browser.getControl(name="field.is_physical")
    Traceback (most recent call last):
    ...
    LookupError:...
    >>> browser.getControl("Register").click()

    >>> browser.getLink("Export attendees to CSV").click()
    >>> ltsp_csv = list(csv.DictReader(io.StringIO(browser.contents)))
    >>> [
    ...     (row["Launchpad username"], row["Physically present"])
    ...     for row in ltsp_csv
    ... ]
    [('name12', 'False')]
