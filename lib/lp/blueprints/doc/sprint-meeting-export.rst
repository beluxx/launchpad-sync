The sprint meeting export view exports information about the
specifications to be discussed at a given sprint.  The view is primarily
designed for use with the sprint scheduler tool.

While the data could be used by other tools, it is not a stable
interface and may change in the future.  The name of the view ('+temp-
meeting-export') and the comment at the top of the XML are intended to
communicate this.

First we import the classes required to test the view:

    >>> from datetime import datetime
    >>> from pytz import timezone
    >>> from zope.component import getUtility, getMultiAdapter
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.blueprints.browser.sprint import SprintMeetingExportView
    >>> from lp.blueprints.interfaces.sprint import ISprintSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet

Look up a few Launchpad objects to be used in the tests

    >>> ubz = getUtility(ISprintSet)['ubz']
    >>> carlos = getUtility(IPersonSet).getByName('carlos')
    >>> mark = getUtility(IPersonSet).getByName('mark')
    >>> sampleperson = getUtility(IPersonSet).getByName('name12')
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> svg_support = firefox.getSpecification('svg-support')
    >>> ext_spec = firefox.getSpecification('extension-manager-upgrades')
    >>> js_spec = firefox.getSpecification('e4x')

Create a view for the UBZ sprint meeting export:

    >>> request = LaunchpadTestRequest()
    >>> view = getMultiAdapter((ubz, request), name='+temp-meeting-export')

Verify that the view is a SprintMeetingExportView:

    >>> isinstance(view, SprintMeetingExportView)
    True

There are currently no people registered for the sprint:

    >>> view.initialize()
    >>> view.attendees
    []

While there are three sprints registered for the ubz sprint, only two
have a priority above LOW, so they are the only ones exposed by the view:

    >>> ubz.specificationLinks().count()
    3

    >>> len(view.specifications)
    2

    >>> for spec in view.specifications:
    ...     print(spec['spec'].name)
    svg-support
    extension-manager-upgrades

We now subscribe Sample Person to the Extension Manager Upgrades spec
and check the list of interested people:

    >>> essential=False
    >>> ext_spec.subscribe(sampleperson, sampleperson, essential)
    <lp.blueprints.model.specificationsubscription.SpecificationSubscription
    object at ...>

    >>> view = getMultiAdapter((ubz, request), name='+temp-meeting-export')
    >>> view.initialize()

The person does not show up as interested in the spec though. Only the
specification assignee is listed (the drafter would be too if one was
assigned).

    >>> from operator import itemgetter
    >>> for person in sorted(
    ...         view.specifications[1]['interested'], key=itemgetter('name')):
    ...     print(person['name'])
    carlos

This is because sample person has not registered as an attendee of the
sprint.  If we add them as an attendee, then they will be available:

    >>> time_starts = datetime(2005, 10, 8, 7, 0, 0, tzinfo=timezone('UTC'))
    >>> time_ends = datetime(2005, 11, 17, 20, 0, 0, tzinfo=timezone('UTC'))
    >>> ignored = login_person(sampleperson)
    >>> ubz.attend(sampleperson, time_starts, time_ends, True)
    <...SprintAttendance ...>
    >>> logout()

    >>> login(ANONYMOUS)
    >>> view = getMultiAdapter((ubz, request), name='+temp-meeting-export')
    >>> view.initialize()
    >>> for person in sorted(
    ...         view.specifications[1]['interested'], key=itemgetter('name')):
    ...     print(person['name'])
    carlos
    name12

The person is also included in the list of attendees:

    >>> len(view.attendees)
    1

    >>> print(view.attendees[0]['name'])
    name12

    >>> print(view.attendees[0]['displayname'])
    Sample Person

    >>> print(view.attendees[0]['start'])
    2005-10-08T07:00:00Z

    >>> print(view.attendees[0]['end'])
    2005-11-17T20:00:00Z

If a specification's priority is undefined or marked as not for us, then
it is not included in the meeting list for the sprint.  The javascript
spec is one such spec.  First we will accept it for the sprint:

    >>> print(js_spec.priority.name)
    NOTFORUS

    >>> link = js_spec.sprint_links[0]
    >>> link.sprint == ubz
    True

    >>> ignored = login_person(ubz.owner)
    >>> ubz.acceptSpecificationLinks([link.id], mark)
    0

Even though the Javascript spec has now been accepted for the sprint
now, it is not listed by the view because of its priority:

    >>> view = getMultiAdapter((ubz, request), name='+temp-meeting-export')
    >>> view.initialize()
    >>> spec_names = [spec['spec'].name for spec in view.specifications]
    >>> js_spec.name not in spec_names
    True

If we decline the extension manager spec, it disapears from the list of
specs:

    >>> link = ext_spec.sprint_links[0]
    >>> link.sprint == ubz
    True

    >>> ubz.declineSpecificationLinks([link.id], mark)
    0

    >>> view = getMultiAdapter((ubz, request), name='+temp-meeting-export')
    >>> view.initialize()
    >>> len(view.specifications)
    1
