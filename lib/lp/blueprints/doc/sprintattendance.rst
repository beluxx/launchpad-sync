SprintAttendance
================

The SprintAttendance object links a person to a sprint. It records additional
information about the attendance. The start and end date-times are required
and they must be UTC

    >>> import datetime
    >>> import pytz
    >>> from lp.blueprints.model.sprintattendance import SprintAttendance

    >>> sprint = factory.makeSprint(title='lunarbase')
    >>> person = factory.makePerson(name='scarlet')
    >>> UTC = pytz.timezone('UTC')
    >>> time_starts = datetime.datetime(2019, 6, 21, 0, 0, 0, 0, UTC)
    >>> time_ends = datetime.datetime(2019, 7, 4, 0, 0, 0, 0, UTC)
    >>> sprint_attendance = SprintAttendance(
    ...     sprint=sprint, attendee=person)
    >>> sprint_attendance.time_starts = time_starts
    >>> sprint_attendance.time_ends = time_ends

The SprintAttendance object implements ISprintAttendance.

    >>> from lp.testing import verifyObject
    >>> from lp.blueprints.interfaces.sprintattendance import (
    ...     ISprintAttendance)
    >>> verifyObject(ISprintAttendance, sprint_attendance)
    True

The sprint and user can be accessed via the sprint and user attributes.

    >>> print(sprint_attendance.sprint.title)
    lunarbase
    >>> print(sprint_attendance.attendee.name)
    scarlet

The time of the users arrival and departure can be retrieved from the
time_start and time_end attributes respectively.

    >>> print(sprint_attendance.time_starts)
    2019-06-21 00:00:00+00:00
    >>> print(sprint_attendance.time_ends)
    2019-07-04 00:00:00+00:00

SprintAttendance records whether the user intend to be physically present
at the sprint; a false value implies virtual attendance. The default value
is true.

    >>> sprint_attendance.is_physical
    True
