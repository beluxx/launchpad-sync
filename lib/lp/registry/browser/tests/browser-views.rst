Browser view helpers
====================

Tests for browser.__init__.


MilestoneOverlayMixin
---------------------

The MilestoneOverlayMixin provides data that is needed by milestoneoverlay.js.
The milestone_form_uri property is the location of the rendered form. The
javascript calls newMilestone on the object at series_api_uri.

    >>> from lp.services.webapp import LaunchpadView
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.registry.browser import MilestoneOverlayMixin

    >>> class MilestoneCreatorView(LaunchpadView, MilestoneOverlayMixin):
    ...     """A stub view to verify a mixin."""
    >>> product = factory.makeProduct(name='app')
    >>> series = factory.makeProductSeries(name='stable', product=product)
    >>> view = MilestoneCreatorView(series, LaunchpadTestRequest())
    >>> print(view.milestone_form_uri)
    http://launchpad.test/app/stable/+addmilestone/++form++
    >>> print(view.series_api_uri)
    /app/stable


StatusCount
-----------

The get_status_counts function returns a list StatusCounts summarising an
iterable of items. The items can be different kinds of objects so long
as they all have the same attribute name to count, and the object in that
attribute has the required attribute to sort.

    >>> from lp.registry.browser import get_status_counts
    >>> from lp.registry.interfaces.series import SeriesStatus

    >>> class Concept:
    ...     def __init__(self, status, person):
    ...         self.status = status
    ...         self.person = person

    >>> class Artefact(Concept):
    ...     pass

    >>> a_person = factory.makePerson(name='andy', displayname="Andy")
    >>> b_person = factory.makePerson(name='bob', displayname="Bob")

    >>> concept_1 = Concept(SeriesStatus.EXPERIMENTAL, a_person)
    >>> artefact_2 = Artefact(SeriesStatus.EXPERIMENTAL, b_person)
    >>> artefact_3 = Artefact(SeriesStatus.CURRENT, b_person)

The common example is for counting the status enums for an object. The default
rule is to sort on the 'sortkey' attribute of the object being counted.

    >>> items = (concept_1, artefact_2, artefact_3)
    >>> for status_count in get_status_counts(items, 'status'):
    ...     print(status_count.count, status_count.status)
    2 Experimental
    1 Current Stable Release

The attribute to sort on can be specified.

    >>> for status_count in get_status_counts(items, 'status', key='title'):
    ...     print(status_count.count, status_count.status)
    1 Current Stable Release
    2 Experimental

The object being counted does not need to be an enum, but it probably needs
to specify the attribute to sort on.

    >>> for status_count in get_status_counts(
    ...     items, 'person', key='displayname'):
    ...     print(status_count.count, status_count.status.displayname)
    1 Andy
    2 Bob

If the object being counted is None, it is ignored.

    >>> artefact_2.person = None
    >>> for status_count in get_status_counts(
    ...     items, 'person', key='displayname'):
    ...     print(status_count.count, status_count.status.displayname)
    1 Andy
    1 Bob
