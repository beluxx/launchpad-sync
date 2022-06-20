Bug Watch Edit Page
===================

It's possible to edit a bug watch on +edit, as well as deleting it.
Deleting a bug watch is only possible when the bug watch isn't linked to
a bug task.

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> linked_bugwatches = [
    ...     bugwatch for bugwatch in bug_one.watches
    ...     if bugwatch.bugtasks]
    >>> unlinked_bugwatches = [
    ...     bugwatch for bugwatch in bug_one.watches
    ...     if not bugwatch.bugtasks]

    >>> from zope.component import getMultiAdapter
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> linked_bugwatch_view = getMultiAdapter(
    ...     (linked_bugwatches.pop(), LaunchpadTestRequest()), name='+edit')
    >>> linked_bugwatch_view.initialize()
    >>> [action.label for action in linked_bugwatch_view.actions
    ...  if action.available()]
    ['Change']

    >>> unlinked_bugwatch_view = getMultiAdapter(
    ...     (unlinked_bugwatches.pop(), LaunchpadTestRequest()), name='+edit')
    >>> unlinked_bugwatch_view.initialize()
    >>> [action.label for action in unlinked_bugwatch_view.actions
    ...  if action.available()]
    ['Change', 'Delete Bug Watch']


Recent activity
---------------

The Bug Watch +edit page displays a list of the recent activity for the
watch. This is provided by the BugWatch activity portlet view and can be
accessed via the recent_watch_activity property of BugWatchView.

We'll create a new watch in order to demonstrate this.

    >>> from lp.testing import login
    >>> login('foo.bar@canonical.com')
    >>> new_watch = factory.makeBugWatch()

The view for the new watch will have an empty recent_watch_activity list
since it hasn't been updated yet.

    >>> new_watch_view = create_initialized_view(
    ...     new_watch, '+portlet-activity')
    >>> len(new_watch_view.recent_watch_activity)
    0

The BugWatch +edit view has a watch_has_activity property, which is used
to determine whether the recent activity portlet should be displayed.

    >>> new_watch_edit_view = create_initialized_view(
    ...     new_watch, '+edit')
    >>> print(new_watch_edit_view.watch_has_activity)
    False

Adding a successful activity entry for the watch will cause it to show
up on the BugWatchView's recent_watch_activity property.

    >>> new_watch.addActivity()
    >>> len(new_watch_view.recent_watch_activity)
    1

The BugWatch +edit view's watch_has_activity property will also have
changed.

    >>> new_watch_edit_view = create_initialized_view(
    ...     new_watch, '+edit')
    >>> print(new_watch_edit_view.watch_has_activity)
    True

Each entry in the recent_watch_activity list is a dict containing data
about the activity.

    >>> from pprint import pprint
    >>> for activity_dict in new_watch_view.recent_watch_activity:
    ...     pprint(activity_dict)
    {'completion_message': 'completed successfully',
     'date': datetime.datetime(...tzinfo=<UTC>),
     'icon': '/@@/yes',
     'oops_id': None,
     'result_text': 'Synchronisation succeeded'}

If an activity entry records a failure, the 'icon' entry in the dict
will point to the 'no' icon and the completion_message will explain the
failure.

We'll commit the transaction to make sure that the two activities have
different dates.

    >>> import transaction
    >>> transaction.commit()

    >>> from lp.bugs.interfaces.bugwatch import BugWatchActivityStatus
    >>> new_watch.addActivity(result=BugWatchActivityStatus.BUG_NOT_FOUND)
    >>> for activity_dict in new_watch_view.recent_watch_activity:
    ...     pprint(activity_dict)
    {'completion_message': "failed with error 'Bug Not Found'",
     'date': datetime.datetime(...tzinfo=<UTC>),
     'icon': '/@@/no',
     'oops_id': None,
     'result_text': 'Bug Not Found'}
    {'completion_message': 'completed successfully',
     'date': datetime.datetime(...tzinfo=<UTC>),
     'icon': '/@@/yes',
     'oops_id': None,
     'result_text': 'Synchronisation succeeded'}


