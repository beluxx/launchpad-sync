Sprint Attendance Pages
=======================

SprintAttendanceAddView is the view that handles attendance to meetings.
The view descends from BaseSprintAttendanceAddView which provides date
handling.

    >>> from lp.blueprints.browser.sprintattendance import (
    ...     BaseSprintAttendanceAddView)
    >>> from lp.blueprints.interfaces.sprint import ISprintSet

    >>> ubz = getUtility(ISprintSet)['ubz']
    >>> sprint_attendance_view = create_view(ubz, name='+attend')
    >>> isinstance(sprint_attendance_view, BaseSprintAttendanceAddView)
    True

The view captures the user's time_start and time_ends attendance.

    >>> sprint_attendance_view.field_names
    ['time_starts', 'time_ends', 'is_physical']

The view also defines a next_url and cancel_url.

    >>> print(sprint_attendance_view.next_url)
    http://launchpad.test/sprints/ubz

    >>> print(sprint_attendance_view.cancel_url)
    http://launchpad.test/sprints/ubz

A helper function to test date handling.

    >>> def create_sprint_attendance_view(sprint, dates):
    ...     time_starts, time_ends = dates
    ...     form = {
    ...         'field.time_starts': time_starts,
    ...         'field.time_ends': time_ends,
    ...         'field.is_physical': 'yes',
    ...         'field.actions.register': 'Register'}
    ...     return create_initialized_view(sprint, name='+attend', form=form)

This sprint doesn't have any attendees. It dose have the required dates
set.

    >>> [attendee.name for attendee in ubz.attendees]
    []

    >>> ubz.time_starts
    datetime.datetime(2005, 10, 7, 23, 30, tzinfo=<UTC>)

    >>> ubz.time_ends
    datetime.datetime(2005, 11, 17, 0, 11, tzinfo=<UTC>)

    >>> login('test@canonical.com')

Choosing a starting date after the ending date returns a nice error
message.

    >>> dates = ['2005-11-15', '2005-10-09']
    >>> sprint_attendance_view = create_sprint_attendance_view(ubz, dates)
    >>> print(sprint_attendance_view.getFieldError('time_ends'))
    The end time must be after the start time.

Choosing a starting date too far after the meeting's end returns an
error message.

    >>> dates = ['2006-01-01', '2006-02-01']
    >>> sprint_attendance_view = create_sprint_attendance_view(ubz, dates)
    >>> print(sprint_attendance_view.getFieldError('time_starts'))
    Please pick a date before 2005-11-16 19:11

Choosing a ending date more than a day before the meeting's start
returns an error message.

    >>> dates = ['2005-07-01', '2005-08-01']
    >>> sprint_attendance_view = create_sprint_attendance_view(ubz, dates)
    >>> print(sprint_attendance_view.getFieldError('time_ends'))
    Please pick a date after 2005-10-07 19:30

Entering a starting date just before the meeting's start date or a
finishing date just after the meeting's end date works because we assume
you wanted the meeting's start and end dates respectively.

    >>> dates = ['2005-10-07 09:00', '2005-11-17 19:05']
    >>> sprint_attendance_view = create_sprint_attendance_view(ubz, dates)
    >>> sprint_attendance_view.errors
    []

Sample Person is now listed as an attendee.

    >>> ubz = getUtility(ISprintSet)['ubz']
    >>> for attendee in ubz.attendees:
    ...     print(attendee.name)
    name12

    >>> sprint_attendance = ubz.attendances[0]

    >>> ubz.time_starts == sprint_attendance.time_starts
    True

    >>> ubz.time_ends == sprint_attendance.time_ends
    True


Physical attendance
-------------------

The most common kind of attendance is that the user will be physically
present at the sprint.

    >>> person = factory.makePerson(name='brown')
    >>> ignored = login_person(person)
    >>> form = {
    ...     'field.time_starts': '2005-10-07 09:00',
    ...     'field.time_ends': '2005-10-17 19:05',
    ...     'field.is_physical': 'yes',
    ...     'field.actions.register': 'Register'}
    >>> view = create_initialized_view(ubz, name='+attend', form=form)
    >>> view.errors
    []

    >>> [sprint_attendance] = [attendance for attendance in ubz.attendances
    ...                        if attendance.attendee.name == 'brown']
    >>> sprint_attendance.is_physical
    True

Some users attend the sprint virtually, such as via IRC, VOIP, or by
using their psychotic powers :).

    >>> person = factory.makePerson(name='black')
    >>> ignored = login_person(person)
    >>> form = {
    ...     'field.time_starts': '2005-10-07 09:00',
    ...     'field.time_ends': '2005-10-17 19:05',
    ...     'field.is_physical': 'no',
    ...     'field.actions.register': 'Register'}
    >>> view = create_initialized_view(ubz, name='+attend', form=form)
    >>> view.errors
    []

    >>> [sprint_attendance] = [attendance for attendance in ubz.attendances
    ...                        if attendance.attendee.name == 'black']
    >>> sprint_attendance.is_physical
    False


The +attend view
----------------

The +attend view has a label.

    >>> sprint_attendance_view = create_view(ubz, name='+attend')
    >>> print(sprint_attendance_view.label)
    Register your attendance


The +register views
-------------------

The +register view has a label too.

    >>> view = create_view(ubz, name='+register')
    >>> print(view.label)
    Register someone else

The view descends from BaseSprintAttendanceAddView.

    >>> isinstance(view, BaseSprintAttendanceAddView)
    True

It also requires the attendee field so that a user can register someone
else.

    >>> view.field_names
    ['attendee', 'time_starts', 'time_ends', 'is_physical']

    >>> person = factory.makePerson(name='greene')
    >>> form = {
    ...     'field.attendee': 'greene',
    ...     'field.time_starts': '2005-10-07 09:00',
    ...     'field.time_ends': '2005-10-17 19:05',
    ...     'field.is_physical': 'yes',
    ...     'field.actions.register': 'Register'}
    >>> view = create_initialized_view(ubz, name='+register', form=form)
    >>> view.errors
    []

    >>> for attendee in ubz.attendees:
    ...     print(attendee.name)
    black brown greene name12


Exporting the list of attendees
-------------------------------

The list of a sprint's attendees can be exported as a CSV file,
containing some details about each of the attendees.

If the person has specified their time zone in Launchpad, the CSV will
include it.

    >>> view = create_view(ubz, '+attendees-csv')
    >>> lines =  view.render().strip().splitlines()
    >>> print(lines[0])
    Launchpad username,Display name,...Timezone,...Physically present

    >>> print(lines[-1])
    name12,Sample Person,...Australia/Perth,...True
