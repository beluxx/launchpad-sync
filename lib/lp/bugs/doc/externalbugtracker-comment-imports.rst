ExternalBugTracker comment imports
**********************************

Some ExternalBugTrackers support the importing of comments from the
remote bug tracker into Launchpad.

In order to demonstrate this we need to create example Bug, BugTracker
and BugWatch instances with which to work.

    >>> from zope.interface import implementer
    >>> from lp.bugs.tests.externalbugtracker import (
    ...     new_bugtracker)
    >>> from lp.services.messages.interfaces.message import IMessageSet
    >>> from lp.testing.dbuser import lp_dbuser
    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.bugs.interfaces.bugmessage import IBugMessageSet
    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> from lp.bugs.interfaces.bugwatch import IBugWatchSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet

    >>> bug_tracker = new_bugtracker(BugTrackerType.BUGZILLA)

    >>> with lp_dbuser():
    ...     sample_person = getUtility(IPersonSet).getByEmail(
    ...         'test@canonical.com')
    ...     firefox = getUtility(IProductSet).getByName('firefox')
    ...     bug = firefox.createBug(
    ...         CreateBugParams(sample_person, "Yet another test bug",
    ...             "Yet another test description.",
    ...             subscribe_owner=False))
    ...     bug_watch = bug.addWatch(bug_tracker, '123456', sample_person)

The ISupportsCommentImport interface defines the methods that external
bug trackers which support comment imports must provide. This interface
defines four methods: getCommentIds(), fetchComments(),
getPosterForComment() and getMessageForComment().

In order to test the importing of comments we will create a new
ExternalBugTracker class which implements these three methods.

    >>> from lp.bugs.externalbugtracker import (
    ...     ExternalBugTracker)
    >>> from lp.bugs.interfaces.externalbugtracker import (
    ...     ISupportsCommentImport)
    >>> @implementer(ISupportsCommentImport)
    ... class CommentImportingExternalBugTracker(ExternalBugTracker):
    ...
    ...     comment_dict = {}
    ...     remote_comments = {
    ...         '1': "Example comment the first",
    ...         '2': "Example comment the second",
    ...         '3': "Example comment the third"}
    ...     comment_datecreated = None
    ...
    ...     poster_tuple = ("Joe Bloggs", "joe.bloggs@example.com")
    ...
    ...     def fetchComments(self, bug_watch, comment_ids):
    ...         for id, comment in self.remote_comments.items():
    ...             if id in comment_ids:
    ...                 self.comment_dict[id] = comment
    ...
    ...     def getCommentIds(self, bug_watch):
    ...         return sorted(self.remote_comments.keys())
    ...
    ...     def getPosterForComment(self, bug_watch, comment_id):
    ...         """Return a tuple of (displayname, email)."""
    ...         return self.poster_tuple
    ...
    ...     def getMessageForComment(self, bug_watch, comment_id, poster):
    ...         """Return a Message object for a comment."""
    ...         message = getUtility(IMessageSet).fromText(
    ...             "Some subject or other",
    ...             self.comment_dict[comment_id], owner=poster,
    ...             datecreated=self.comment_datecreated,
    ...             rfc822msgid=comment_id)
    ...         return message

    >>> external_bugtracker = CommentImportingExternalBugTracker(
    ...     'http://example.com/')

The CheckwatchesMaster method importBugComments() is responsible for
calling the three methods of ISupportsCommentImport in turn to import
comments. Calling importBugComments() and passing it our new
comment-importing ExternalBugTracker instance will result in the three
comments in the comment_dict being imported into Launchpad.

    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.bugs.scripts.checkwatches.core import CheckwatchesMaster
    >>> from lp.bugs.scripts.checkwatches.tests.test_bugwatchupdater import (
    ...     make_bug_watch_updater)

    >>> bugwatch_updater = make_bug_watch_updater(
    ...     CheckwatchesMaster(transaction, logger=FakeLogger()),
    ...     bug_watch, external_bugtracker)
    >>> bugwatch_updater.importBugComments()
    INFO Imported 3 comments for remote bug 123456 on ...

These three comments will be linked to the bug watch from which they
were imported. They also have the remote_comment_id attribute set.

    >>> bug_watch = getUtility(IBugWatchSet).get(bug_watch.id)
    >>> def print_bug_messages(bug, bug_watch):
    ...     for message in bug.messages[1:]:
    ...         bug_message = getUtility(IBugMessageSet).getByBugAndMessage(
    ...             bug, message)
    ...         print(bug_message.bugwatch == bug_watch)
    ...         print("%s: %s" % (
    ...             bug_message.remote_comment_id,
    ...             bug_message.message.text_contents))
    >>> print_bug_messages(bug, bug_watch)
    True
    1: Example comment the first
    True
    2: Example comment the second
    True
    3: Example comment the third

If another comment is added on the remote tracker and the comment import
process is run again only the new comment will be imported.

    >>> external_bugtracker.remote_comments['four'] = "Yet another comment."

    >>> transaction.commit()

    >>> bugwatch_updater.importBugComments()
    INFO Imported 1 comments for remote bug 123456 on ...

Once again, the newly-imported comment will be linked to the bug watch
form which it was imported.

    >>> print_bug_messages(bug, bug_watch)
    True
    1: Example comment the first
    True
    2: Example comment the second
    True
    3: Example comment the third
    True
    four: Yet another comment.


Creating Person records
***********************

In the examples above, joe.bloggs@example.com was used as the poster of
all the comments. Since Joe didn't have a Launchpad account, it was
created automatically for him, with the email address marked as
invalid.

    >>> joe = getUtility(IPersonSet).getByEmail('joe.bloggs@example.com',
    ...                                         filter_status=False)
    >>> bug.messages[-1].owner == joe
    True

    >>> print(joe.displayname)
    Joe Bloggs
    >>> print(joe.preferredemail)
    None
    >>> print(joe.creation_rationale.name)
    BUGIMPORT
    >>> print(joe.creation_comment)
    when importing comments for Bugzilla *TESTING* #123456.

If the poster's email is already registered in Launchpad, the comment
is associated with the existing person.

    >>> no_priv = getUtility(IPersonSet).getByName('no-priv')
    >>> no_priv.preferredemail is not None
    True

    >>> external_bugtracker.poster_tuple = (
    ...     'No Priv', 'no-priv@canonical.com')
    >>> external_bugtracker.remote_comments['no-priv-comment'] = (
    ...     "The fifth comment.")

    >>> transaction.commit()

    >>> bugwatch_updater.importBugComments()
    INFO Imported 1 comments for remote bug 123456 on ...

    >>> print(bug.messages[-1].owner.name)
    no-priv

It's also possible for Launchpad to create Persons from remote
bugtracker users when the remote bugtracker doesn't specify an email
address. In those cases, the ExternalBugTracker's getPosterForComment()
method will return a tuple of (displayname, None), which can then be
used to create a Person based on the displayname alone.

    >>> external_bugtracker.poster_tuple = (u'noemail', None)
    >>> external_bugtracker.remote_comments['no-email-comment'] = (
    ...     "Yet another comment.")

    >>> transaction.commit()

    >>> bugwatch_updater.importBugComments()
    INFO Imported 1 comments for remote bug 123456 on ...

    >>> print(bug.messages[-1].owner.name)
    noemail-bugzilla-checkwatches-1

    >>> print(bug.messages[-1].owner.preferredemail)
    None

A BugTrackerPerson record will have been created to map the new Person
to the name 'noemail' on our example bugtracker.

    >>> bug_watch.bugtracker.getLinkedPersonByName(u'noemail')
    <lp.bugs.model.bugtrackerperson.BugTrackerPerson ...>

If the remote person is invalid (i.e. a Launchpad Person can't be
created for them) an error will be logged and the comment will not be
imported.

    >>> external_bugtracker.poster_tuple = (None, None)
    >>> external_bugtracker.remote_comments['invalid-person-comment'] = (
    ...     "This will not be imported.")

    >>> transaction.commit()

    >>> bugwatch_updater.importBugComments()
    WARNING Unable to import remote comment author. No email address
    or display name found. (OOPS-...)
    INFO Imported 0 comments for remote bug 123456 on ...

    >>> print(bug.messages[-1].text_contents)
    Yet another comment.

Let's delete that comment now so that it doesn't break later tests.

    >>> del external_bugtracker.remote_comments['invalid-person-comment']
    >>> external_bugtracker.poster_tuple = (
    ...     'No Priv', 'no-priv@canonical.com')


BugWatch comment importing functionality
****************************************

The IBugWatch interface provides methods for linking imported comments
to bug watches and for checking whether an imported comment is already
linked to a bug watch.

The method IBugWatch.hasComment() can be used to check whether a comment
has been linked to a bug watch. If we create an example comment without
linking it to the bug watch this method will, of course, return False.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> janitor = getUtility(ILaunchpadCelebrities).janitor
    >>> message = getUtility(IMessageSet).fromText(
    ...     "Example Message", "With example content for you to read.",
    ...     owner=janitor)

    >>> comment_id = 'a-comment'

    >>> bug_watch = getUtility(IBugWatchSet).get(bug_watch.id)

    >>> bug_watch.hasComment(comment_id)
    False

IBugWatch provides an addComment() method by which comments can be
linked to a bug watch. This method accepts a Launchpad Message object
representing the comment itself and a comment_id paramter, which can be
used to pass the ID of the comment on the remote bug tracker from which
the comment was imported. It returns the created IBugMessage.

    >>> bug_messsage = bug_watch.addComment(comment_id, message)
    >>> bug_messsage.bug == bug_watch.bug
    True
    >>> bug_messsage.message == message
    True

After using addComment() to add a comment, hasComment() will return True
for that comment.

    >>> bug_watch.hasComment(comment_id)
    True

We can also see that the message we passed to addComment() has been
linked to the bug watch by examining the BugMessage which links the
message and the bug to which the watch belongs.

    >>> bug_message = getUtility(IBugMessageSet).getByBugAndMessage(
    ...     bug, message)

    >>> bug_message.bugwatch == bug_watch
    True

The list of imported messages can be retrieved using
getImportedBugMessages(). Messages that are linked to the bug watch but
don't have a remote_comment_id are comments waiting to be pushed to the
remote tracker and will not be returned by getImportedBugMessages()

    >>> with lp_dbuser():
    ...     bug_watch2 = factory.makeBugWatch('42')
    ...     ignore = bug_watch2.bug.newMessage(
    ...         owner=bug_watch2.bug.owner, subject='None',
    ...         content='Imported comment', bugwatch=bug_watch2,
    ...         remote_comment_id='test')
    ...     ignore = bug_watch2.bug.newMessage(
    ...         owner=bug_watch2.bug.owner, subject='None',
    ...         content='Native comment')
    ...     ignore = bug_watch2.bug.newMessage(
    ...         owner=bug_watch2.bug.owner, subject='None',
    ...         content='Pushable comment', bugwatch=bug_watch2)

    >>> for bug_message in bug_watch2.getImportedBugMessages():
    ...     print(bug_message.message.text_contents)
    Imported comment

    >>> transaction.commit()


Importing two messages with the same ID
***************************************

It is possible for two Messages with the same ID to coexist within
Launchpad, for example if a comment on a bug was sent to both Launchpad
and to DebBugs and the subsequently imported into Launchpad from the
DebBugs database.

We can demonstrate this by creating two messages with the same message
ID.

    >>> with lp_dbuser():
    ...     message_one = getUtility(IMessageSet).fromText(
    ...         "Example Message", "With example content for you to read.",
    ...         owner=janitor)
    ...     message_two = getUtility(IMessageSet).fromText(
    ...         "Example Message", "With example content for you to read.",
    ...         rfc822msgid=message_one.rfc822msgid, owner=janitor)

    >>> message_one.rfc822msgid == message_two.rfc822msgid
    True

We will use message_one to represent a message which was sent directly
to Launchpad. Since it was a comment on a bug, we link it to that bug.

    >>> bug.linkMessage(message_one)
    <BugMessage...>

The bug watch which we created earlier will not be linked to the message
since it was not imported for that bug watch.

    >>> bug_watch = getUtility(IBugWatchSet).get(bug_watch.id)
    >>> bug_watch.hasComment(message_one.rfc822msgid)
    False

Now the comment import process runs and the message is imported from the
DebBugs database. The message is linked to the bug watch for which it
was imported.

    >>> bug_watch.addComment(message_two.rfc822msgid, message_two)
    <BugMessage at ...>
    >>> bug_watch.hasComment(message_two.rfc822msgid)
    True

We can see that only the second message is linked to the bug watch by
examining the BugMessages which link the messages to the bug.

    >>> bug_message_one = getUtility(IBugMessageSet).getByBugAndMessage(
    ...     bug, message_one)
    >>> bug_message_two = getUtility(IBugMessageSet).getByBugAndMessage(
    ...     bug, message_two)

    >>> print(bug_message_one.bugwatch)
    None

    >>> bug_message_two.bugwatch == bug_watch
    True


Importing comments with CVE references
**************************************

If a comment contains a CVE reference, that CVE reference will be
imported and linked to the bug.  However, the user who authored the
comment containing the CVE reference doesn't get any karma from this
since they aren't a valid Launchpad user, having been created during the
import process.

We'll create a bug watch and add a listener to check for Karma events.

    >>> from lp.testing.karma import KarmaAssignedEventListener
    >>> with lp_dbuser():
    ...     bug_watch = factory.makeBugWatch('123456')
    ...     karma_helper = KarmaAssignedEventListener()
    ...     karma_helper.register_listener()

Importing a comment with a CVE reference will produce a CVE link in
Launchpad but will result in no Karma records being created.

    >>> external_bugtracker.remote_comments = {
    ...     '5':"A comment containing a CVE entry: CVE-1991-9911."}
    >>> bugwatch_updater = make_bug_watch_updater(
    ...     CheckwatchesMaster(transaction, logger=FakeLogger()),
    ...     bug_watch, external_bugtracker)
    >>> bugwatch_updater.importBugComments()
    INFO Imported 1 comments for remote bug 123456...

    >>> for cve in bug_watch.bug.cves:
    ...     print(cve.displayname)
    CVE-1991-9911

Karma is only awarded for actions that occur within Launchpad. If an
imported comment was authored by a valid Launchpad user, that user will
receive no karma. We'll demonstrate this by making an comment which
includes a CVE reference appear to come from a valid Launchpad user.

    >>> foo_bar = getUtility(IPersonSet).getByName('name16')
    >>> external_bugtracker.poster_tuple = (
    ...     foo_bar.displayname, foo_bar.preferredemail.email)
    >>> external_bugtracker.remote_comments['6'] = (
    ...     "Another comment, another CVE: CVE-1999-0593.")

Once again, CVE links are created but no karma is assigned.

    >>> transaction.commit()

    >>> bugwatch_updater.importBugComments()
    INFO Imported 1 comments for remote bug 123456...

    >>> for cve in sorted([cve.displayname for cve in bug_watch.bug.cves]):
    ...     print(cve)
    CVE-1991-9911
    CVE-1999-0593

    >>> karma_helper.unregister_listener()

Email notifications
*******************

When bug comments are imported, notifications are sent to inform the bug
subscribers about it. The first time we import comments from a bug
watch, there can be a lot of comments. To avoid causing a lot of email
notifications to be sent, only one notification is sent for all the
comments.

    >>> from lp.bugs.model.bugnotification import BugNotification
    >>> from lp.services.database.interfaces import IStore
    >>> old_notifications = set()
    >>> def get_new_notifications(bug):
    ...     new_notifications = [
    ...         notification for notification in IStore(BugNotification).find(
    ...             BugNotification, bug=bug).order_by(BugNotification.id)
    ...         if notification not in old_notifications]
    ...     old_notifications.update(new_notifications)
    ...     return new_notifications

    >>> import pytz
    >>> from datetime import datetime, timedelta
    >>> now = datetime(2008, 9, 12, 15, 30, 45, tzinfo=pytz.timezone('UTC'))
    >>> with lp_dbuser():
    ...     test_bug = factory.makeBug(date_created=now)
    ...     bug_watch = factory.makeBugWatch('42', bug=test_bug)

    >>> get_new_notifications(bug_watch.bug)
    [...]

    >>> external_bugtracker.remote_comments = {
    ...     '1': 'First imported comment (initial import)',
    ...     '2': 'Second imported comment (initial import)',
    ...     }
    >>> external_bugtracker.comment_datecreated = now + timedelta(hours=1)

    >>> transaction.commit()

    >>> bugwatch_updater = make_bug_watch_updater(
    ...     CheckwatchesMaster(transaction, logger=FakeLogger()),
    ...     bug_watch, external_bugtracker)
    >>> bugwatch_updater.importBugComments()
    INFO Imported 2 comments for remote bug 42 ...

    >>> notifications = get_new_notifications(bug=bug_watch.bug)
    >>> len(notifications)
    1

The notification is marked as being a comment, and the Bug Watch Updater
is used as the From address.

    >>> notifications[0].is_comment
    True
    >>> print(notifications[0].message.owner.name)
    bug-watch-updater

    >>> print(notifications[0].message.text_contents)
    Launchpad has imported 2 comments from the remote bug at
    http://.../show_bug.cgi?id=42.
    <BLANKLINE>
    If you reply to an imported comment from within Launchpad, your comment
    will be sent to the remote bug automatically. Read more about
    Launchpad's inter-bugtracker facilities at
    https://help.launchpad.net/InterBugTracking.
    <BLANKLINE>
    ------------------------------------------------------------------------
    On 2008-09-12T16:30:45+00:00 Foo Bar wrote:
    <BLANKLINE>
    First imported comment (initial import)
    <BLANKLINE>
    Reply at: http://.../.../+bug/.../comments/1
    <BLANKLINE>
    ------------------------------------------------------------------------
    On ... Foo Bar wrote:
    <BLANKLINE>
    Second imported comment (initial import)
    <BLANKLINE>
    Reply at: http://.../.../+bug/.../comments/2

If we already have comments imported for a bug watch, one notification
will be sent for each subsequent imported comment, even if there is
more than one.

    >>> get_new_notifications(bug_watch.bug)
    [...]

    >>> external_bugtracker.poster_tuple = (
    ...     "Joe Bloggs", "joe.bloggs@example.com")
    >>> external_bugtracker.remote_comments = {
    ...     '3': 'Third imported comment (initial import)',
    ...     '4': 'Fourth imported comment (initial import)',
    ...     }
    >>> bug_watch.getImportedBugMessages().is_empty()
    False

    >>> transaction.commit()

    >>> bugwatch_updater.importBugComments()
    INFO Imported 2 comments for remote bug 42 ...

    >>> notifications = get_new_notifications(bug_watch.bug)
    >>> len(notifications)
    2
    >>> for notification in notifications:
    ...     print("%s wrote: %s" % (
    ...         notification.message.owner.name,
    ...         notification.message.text_contents))
    joe-bloggs wrote: Third imported comment (initial import)
    joe-bloggs wrote: Fourth imported comment (initial import)
