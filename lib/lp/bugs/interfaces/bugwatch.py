# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Bug watch interfaces."""

__metaclass__ = type

__all__ = [
    'BugWatchActivityStatus',
    'IBugWatch',
    'IBugWatchActivity',
    'IBugWatchSet',
    'NoBugTrackerFound',
    'UnrecognizedBugTrackerURL',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Int, TextLine, Text
from lazr.enum import DBEnumeratedType, DBItem

from canonical.launchpad import _
from canonical.launchpad.fields import StrippedTextLine
from canonical.launchpad.interfaces.launchpad import IHasBug
from lp.bugs.interfaces.bugtracker import IBugTracker

from lazr.restful.declarations import (
    export_as_webservice_entry, exported)
from lazr.restful.fields import CollectionField, Reference, ReferenceChoice


class BugWatchActivityStatus(DBEnumeratedType):
    """An enumeration of possible BugWatch errors."""

    UNKNOWN = DBItem(999, """
        Unknown

        Launchpad encountered an unexpected error when trying to
        retrieve the bug from the remote server.
        """)

    BUG_NOT_FOUND = DBItem(1, """
        Bug Not Found

        Launchpad could not find the specified bug on the remote server.
        """)

    CONNECTION_ERROR = DBItem(2, """
        Connection Error

        Launchpad was unable to connect to the remote server.
        """)

    INVALID_BUG_ID = DBItem(3, """
        Invalid Bug ID

        The specified bug ID is not valid.
        """)

    TIMEOUT = DBItem(4, """
        Timeout

        Launchpad encountered a timeout when trying to connect to the
        remote server and was unable to retrieve the bug's status.
        """)

    UNPARSABLE_BUG = DBItem(5, """
        Unparsable Bug

        Launchpad could not extract a status from the data it received
        from the remote server.
        """)

    UNPARSABLE_BUG_TRACKER = DBItem(6, """
        Unparsable Bug Tracker Version

        Launchpad could not determine the version of the bug tracker
        software running on the remote server.
        """)

    UNSUPPORTED_BUG_TRACKER = DBItem(7, """
        Unsupported Bugtracker

        The remote server is using bug tracker software which Launchpad
        does not currently support.
        """)

    PRIVATE_REMOTE_BUG = DBItem(8, """
        Private Remote Bug

        The bug is marked as private on the remote bug tracker.
        Launchpad cannot import the status of private remote bugs.
        """)


class IBugWatch(IHasBug):
    """A bug on a remote system."""
    export_as_webservice_entry()

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = exported(
        Reference(title=_('Bug'), schema=Interface, # Redefined in bug.py
                  required=True, readonly=True))
    bugtracker = exported(
        ReferenceChoice(
            title=_('Bug System'), required=True,
            schema=IBugTracker, vocabulary='BugTracker',
            description=_(
                "You can register new bug trackers from the Launchpad "
                "Bugs home page.")),
        exported_as='bug_tracker')
    remotebug = exported(
        StrippedTextLine(
            title=_('Remote Bug'), required=True,
            readonly=False, description=_(
                "The bug number of this bug in the remote bug tracker.")),
        exported_as='remote_bug')
    remotestatus = exported(
        TextLine(title=_('Remote Status')),
        exported_as='remote_status')
    remote_importance = exported(
        TextLine(title=_('Remote Importance')))
    lastchanged = exported(
        Datetime(title=_('Last Changed')),
        exported_as='date_last_changed')
    lastchecked = exported(
        Datetime(title=_('Last Checked')),
        exported_as='date_last_checked')
    last_error_type = exported(
        Choice(title=_('Last Error Type'), vocabulary=BugWatchActivityStatus))
    datecreated = exported(
        Datetime(title=_('Date Created'), required=True, readonly=True),
        exported_as='date_created')
    owner = exported(
        Reference(title=_('Owner'), required=True,
                  readonly=True, schema=Interface))
    activity = Attribute('The activity history of this BugWatch.')
    next_check = exported(
        Datetime(title=_('Next Check')),
        exported_as='date_next_checked')

    # Useful joins.
    bugtasks = exported(
        CollectionField(
            description=_(
                'The tasks which this watch will affect. '
                'In Launchpad, a bug watch can be linked to one or more '
                'tasks, and if it is linked and we notice a status change '
                'in the watched bug then we will try to update the '
                'Launchpad bug task accordingly.'),
            # value_type is redefined in bugtask.py, to use the right
            # interface.
            value_type=Reference(schema=Interface,)),
            exported_as='bug_tasks')

    # Properties.
    needscheck = Attribute("A True or False indicator of whether or not "
        "this watch needs to be synchronised. The algorithm used considers "
        "the severity of the bug, as well as the activity on the bug, to "
        "ensure that we spend most effort on high-importance and "
        "high-activity bugs.")

    unpushed_comments = Attribute(
        "A set of comments on this BugWatch that need to be pushed to "
        "the remote bug tracker.")

    # Required for Launchpad pages.
    title = exported(
        Text(title=_('Bug watch title'), readonly=True))

    url = exported(
        Text(title=_('The URL at which to view the remote bug.'),
             readonly=True))

    def updateImportance(remote_importance, malone_importance):
        """Update the importance of the bug watch and any linked bug task.

        The lastchanged attribute gets set to the current time.
        """

    def updateStatus(remote_status, malone_status):
        """Update the status of the bug watch and any linked bug task.

        The lastchanged attribute gets set to the current time.
        """

    def destroySelf():
        """Delete this bug watch."""

    def getLastErrorMessage():
        """Return a string describing the contents of last_error_type."""

    def hasComment(comment_id):
        """Return True if a comment has been imported for the BugWatch.

        If the comment has not been imported, return False.

        :param comment_id: The remote ID of the comment.
        """

    def addComment(comment_id, message):
        """Link and imported comment to the BugWatch.

        :param comment_id: The remote ID of the comment.

        :param message: The imported comment as a Launchpad Message object.
        """

    def getImportedBugMessages():
        """Return all the `IBugMessage`s that have been imported."""

    def addActivity(result=None, message=None, oops_id=None):
        """Add an `IBugWatchActivity` record for this BugWatch."""


# Defined here because of circular imports.
IBugTracker['watches'].value_type.schema = IBugWatch


class IBugWatchSet(Interface):
    """The set of `IBugWatch`es."""

    bug = Int(title=_("Bug id"), readonly=True)
    title = Attribute('Title')

    def __getitem__(key):
        """Get a BugWatch"""

    def __iter__():
        """Iterate through BugWatches for a given bug."""

    def get(id):
        """Get an IBugWatch by its ID.

        Raise a NotFoundError if there is no IBugWatch
        matching the given id.
        """

    def search():
        """Search through all the IBugWatches in the system."""

    def fromText(text, bug, owner):
        """Create one or more BugWatch's by analysing the given text. This
        will look for reference to known or new bug tracking instances and
        create the relevant watches. It returns a (possibly empty) list of
        watches created.
        """

    def fromMessage(message, bug):
        """Create one or more BugWatch's by analysing the given email. The
        owner of the BugWatch's will be the sender of the message.
        It returns a (possibly empty) list of watches created.
        """

    def createBugWatch(bug, owner, bugtracker, remotebug):
        """Create an IBugWatch.

        :bug: The IBug to which the watch is linked.
        :owner: The IPerson who created the IBugWatch.
        :bugtracker: The external IBugTracker.
        :remotebug: A string.
        """

    def extractBugTrackerAndBug(url):
        """Extract the bug tracker and the bug number for the given URL.

        A tuple in the form of (bugtracker, remotebug) is returned,
        where bugtracker is a registered IBugTracer, and remotebug is a
        text string.

        A NoBugTrackerFound exception is raised if the base URL can be
        extracted, but no such bug tracker is registered in Launchpad.

        If no bug tracker type can be guessed, None is returned.
        """

    def getBugWatchesForRemoteBug(self, remote_bug, bug_watch_ids=None):
        """Returns bug watches referring to the given remote bug.

        Returns a set of those bug watches, optionally limited to
        those with IDs in `bug_watch_ids`, that refer to `remote_bug`.

        :param remote_bug_id: The ID of the remote bug.
        :type remote_bug_id: See `IBugWatch.remotebug`.

        :param bug_watch_ids: A collection of `BugWatch` IDs.
        :type bug_watch_ids: An iterable of `int`s, or `None`.
        """

    # XXX: GavinPanella bug=570277 2010-04-26: In bulkSetError() the
    # last_error_type argument accepts the same values as the result
    # argument to bulkAddActivity(). Using different terms for
    # essentially the same thing is confusing.

    def bulkSetError(references, last_error_type=None):
        """Efficiently update the status of the given bug watches.

        Sets the `last_error_type` field as instructed, updates
        `lastchecked` to now and resets `next_check` to None, all in
        the most efficient way possible.

        :param references: An iterable of `IBugWatch` objects or
            primary keys for the same.
        :param last_error_type: A member of `BugWatchActivityStatus`
            or None.
        """

    def bulkAddActivity(references, result=None, message=None, oops_id=None):
        """Efficiently add activity for the given bug watches.

        Add `BugWatchActivity` records for the given bug watches in
        the most efficient way possible.

        :param references: An iterable of `IBugWatch` objects or
            primary keys for the same.
        :param result: See `IBugWatch.addActivity`.
        :param message: See `IBugWatch.addActivity`.
        :param oops_id: See `IBugWatch.addActivity`.
        """


class NoBugTrackerFound(Exception):
    """No bug tracker with the base_url is registered in Launchpad."""

    def __init__(self, base_url, remote_bug, bugtracker_type):
        Exception.__init__(self, base_url, remote_bug, bugtracker_type)
        self.base_url = base_url
        self.remote_bug = remote_bug
        self.bugtracker_type = bugtracker_type


class UnrecognizedBugTrackerURL(Exception):
    """The given URL isn't used by any bug tracker we support."""


class IBugWatchActivity(Interface):
    """A record of a single BugWatch update."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The unique id of this activity record."))
    bug_watch = Reference(
        title=_('Bug watch'), required=True, readonly=True, schema=IBugWatch,
        description=_(
            "The BugWatch whose activity is recorded in this record"))
    activity_date = Datetime(
        title=_('Activity date'), required=True, readonly=True,
        description=_("The date on which this activity occurred."))
    result = Choice(
        title=_('Result'), vocabulary=BugWatchActivityStatus, readonly=True,
        description=_("The result of the activity."))
    message = Text(
        title=_('Message'), readonly=True,
        description=_("The message associated with this activity."))
    oops_id = Text(
        title=_('OOPS ID'), readonly=True,
        description=_("The OOPS ID associated with this activity."))

