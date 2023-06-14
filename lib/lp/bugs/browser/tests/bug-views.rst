Bug Filing Pages
================

Filing a Bug
------------

There are three objects on which you can file a bug. An
ObjectCreatedEvent is published when the bug is filed. Let's register
an event listener to demonstrate this.

    >>> from lazr.lifecycle.event import IObjectCreatedEvent
    >>> import transaction

    >>> from lp.bugs.interfaces.bug import IBug
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.testing.fixture import ZopeEventHandlerFixture

    >>> def on_created_event(object, event):
    ...     print("ObjectCreatedEvent: %r" % object)
    ...
    >>> on_created_listener = ZopeEventHandlerFixture(
    ...     on_created_event, (IBug, IObjectCreatedEvent)
    ... )
    >>> on_created_listener.setUp()

1. Filing a bug on a distribution.

The distribution filebug page will attach a bugtask to a sourcepackage
if the user provides a valid package name when reporting the bug.

If the package name entered by the user happens to be a binary package
name, that information is recorded in the description, and the first
comment, of the bug report.

    >>> from zope.component import getMultiAdapter, getUtility
    >>> from lp.services.webapp.interfaces import (
    ...     ILaunchBag,
    ...     IOpenLaunchBag,
    ... )
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> from lp.bugs.interfaces.bugtasksearch import BugTaskSearchParams
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet

    >>> launchbag = getUtility(IOpenLaunchBag)
    >>> login("foo.bar@canonical.com")

    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "field.title": "bug in bin pkg",
    ...         "field.comment": "a bug in a bin pkg",
    ...         "packagename_option": "choose",
    ...         "field.packagename": "linux-2.6.12",
    ...         "field.actions.submit_bug": "Submit Bug Report",
    ...     },
    ... )

    >>> ubuntu_filebug = getMultiAdapter((ubuntu, request), name="+filebug")
    >>> launchbag.clear()
    >>> launchbag.add(ubuntu)

    >>> ubuntu_filebug.initialize()
    ObjectCreatedEvent: <Bug object>

    >>> launchbag.clear()

    >>> current_user = getUtility(ILaunchBag).user
    >>> search_params = BugTaskSearchParams(
    ...     searchtext="bin pkg", user=current_user
    ... )

    >>> latest_ubuntu_bugtask = ubuntu.searchTasks(search_params)[0]

The user specified a binary package name, so that's been added to the
bug description and the first comment:

    >>> print(latest_ubuntu_bugtask.bug.description)
    a bug in a bin pkg

the source package from which the binary was built has been set on
the bugtask.

    >>> print(latest_ubuntu_bugtask.sourcepackagename.name)
    linux-source-2.6.15

2. Filing a bug on a product.

    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "field.title": "a firefox bug",
    ...         "field.comment": "a test bug",
    ...         "field.actions.submit_bug": "Submit Bug Report",
    ...     },
    ... )

    >>> firefox_filebug = getMultiAdapter((firefox, request), name="+filebug")

    >>> firefox_filebug.initialize()
    ObjectCreatedEvent: <Bug object>

3. Filing a bug on a distribution source package.

You can also access the +filebug page from a sourcepackage.

    >>> ubuntu_firefox = ubuntu.getSourcePackage("mozilla-firefox")

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "field.title": "a firefox bug",
    ...         "field.comment": "a test bug",
    ...         "packagename_option": "choose",
    ...         "field.packagename": "mozilla-firefox",
    ...         "field.actions.submit_bug": "Submit Bug Report",
    ...     },
    ... )

    >>> ubuntu_firefox_filebug = getMultiAdapter(
    ...     (ubuntu_firefox, request), name="+filebug"
    ... )

    >>> launchbag.add(ubuntu)

    >>> ubuntu_firefox_filebug.initialize()
    ObjectCreatedEvent: <Bug object>

    >>> launchbag.clear()

Adding Comments
---------------

Let's flush all changes so far to ensure we're looking at a consistent view of
the database.

    >>> flush_database_updates()
    >>> transaction.commit()

To add new comments, users POST to the +addcomment page:

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "field.subject": latest_ubuntu_bugtask.bug.title,
    ...         "field.comment": "I can reproduce this bug.",
    ...         "field.actions.save": "Save Changes",
    ...     },
    ... )
    >>> ubuntu_addcomment = getMultiAdapter(
    ...     (latest_ubuntu_bugtask, request), name="+addcomment-form"
    ... )
    >>> ubuntu_addcomment.initialize()

They may even, by mistake, post the same comment twice:

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "field.subject": latest_ubuntu_bugtask.bug.title,
    ...         "field.comment": "I can reproduce this bug.",
    ...         "field.actions.save": "Save Changes",
    ...     },
    ... )
    >>> ubuntu_addcomment = getMultiAdapter(
    ...     (latest_ubuntu_bugtask, request), name="+addcomment-form"
    ... )
    >>> ubuntu_addcomment.initialize()

Comments are cached in the view, so we need to flush updates and then
grab a new view to actually see them:

    >>> flush_database_updates()
    >>> transaction.commit()

    >>> ubuntu_bugview = getMultiAdapter(
    ...     (latest_ubuntu_bugtask, request), name="+index"
    ... )
    >>> print(len(ubuntu_bugview.comments))
    3
    >>> for c in ubuntu_bugview.comments:
    ...     print("%d %s: %s" % (c.index, c.owner.name, c.text_contents))
    ...
    0 name16: a bug in a bin pkg
    1 name16: I can reproduce this bug.
    2 name16: I can reproduce this bug.


Description and Comment Display
-------------------------------

When a user posts a new bug, the first comment and the description are
identical. Take as an example the first bug posted above:

    >>> print(latest_ubuntu_bugtask.bug.description)
    a bug in a bin pkg

Its description has the same contents as the bug's first comment:

    >>> print(latest_ubuntu_bugtask.bug.messages[0].text_contents)
    a bug in a bin pkg

The view class offers a method to check exactly that:

    >>> ubuntu_bugview.wasDescriptionModified()
    False

If we go ahead and modify the description, however:

    >>> latest_ubuntu_bugtask.bug.description = "A bug in the linux kernel"
    >>> flush_database_updates()
    >>> transaction.commit()

    >>> ubuntu_bugview.wasDescriptionModified()
    True

The displayable comments for a bug can be obtained from the view
property activity_and_comments.

    >>> comments = [
    ...     event.get("comment")
    ...     for event in ubuntu_bugview.activity_and_comments
    ...     if event.get("comment")
    ... ]

Because we omit the first comment, and because the third comment is
identical to the second, we really only display one comment:

    >>> print(len(comments))
    1
    >>> for c in comments:
    ...     print("%d %s: %s" % (c.index, c.owner.name, c.text_contents))
    ...
    1 name16: I can reproduce this bug.

(Unregister our listener, since we no longer need it.)

    >>> on_created_listener.cleanUp()


Bug Portlets
============

Duplicates Portlet
------------------

The duplicate bugs portlet lists duplicates of the current bug. If the
duplicate bug affects the current context, the link to the dupe will
remain in the current context. If the dupe has not been reported in
the current context, the dupe link will be to the generic
/bugs/$bug.id redirect link.

    >>> bugtaskset = getUtility(IBugTaskSet)
    >>> bugset = getUtility(IBugSet)

Bug 6 is a duplicate of bug 5, and since both bugs affect Firefox, the
duplicate link remains in the current context.

    >>> bug_five_in_firefox = bugtaskset.get(14)

    >>> print(bug_five_in_firefox.bug.id)
    5
    >>> print(bug_five_in_firefox.product.name)
    firefox


    >>> bug_page_view = getMultiAdapter(
    ...     (bug_five_in_firefox.bug, request), name="+portlet-duplicates"
    ... )

    >>> bug_six = bugset.get(6)

    >>> getUtility(IOpenLaunchBag).add(bug_five_in_firefox)

    >>> for dupe in bug_page_view.duplicates():
    ...     print(dupe["url"])
    ...
    http://.../firefox/+bug/6

Bug 2 is not reported in Firefox. Let's mark bug 2 as a dupe of bug 5,
and see how the returned link changes.

    >>> bug_two = bugset.get(2)
    >>> bug_five = bugset.get(5)
    >>> bug_two.markAsDuplicate(bug_five)

    >>> bug_page_view = getMultiAdapter(
    ...     (bug_five_in_firefox.bug, request), name="+portlet-duplicates"
    ... )

    >>> for dupe in bug_page_view.duplicates():
    ...     print(dupe["url"])
    ...
    http://.../bugs/2
    ...


Bug Attachments
---------------

We show bug attachments in two lists: patches and non-patch attachments.
Sequences with data about patch and non-patch attachments are provided
by the properties `patches` and `regular_attachments` of the class
BugView. The elements of the sequences are dictionaries containing
the the attachment itself and a ProxiedLibraryFileAlias for the
librarian file of the attachment.

    >>> from lp.bugs.browser.bug import BugView
    >>> login("foo.bar@canonical.com")
    >>> request = LaunchpadTestRequest()
    >>> bug_seven = bugset.get(7)
    >>> attachment_1 = factory.makeBugAttachment(
    ...     bug=bug_seven,
    ...     description="attachment 1",
    ...     is_patch=False,
    ...     filename="a1",
    ... )
    >>> attachment_2 = factory.makeBugAttachment(
    ...     bug=bug_seven,
    ...     description="attachment 2",
    ...     is_patch=False,
    ...     filename="a2",
    ... )
    >>> patch_1 = factory.makeBugAttachment(
    ...     bug=bug_seven, description="patch 1", is_patch=True, filename="p1"
    ... )
    >>> patch_2 = factory.makeBugAttachment(
    ...     bug=bug_seven, description="patch 2", is_patch=True, filename="p2"
    ... )
    >>> view = BugView(bug_seven, request)
    >>> for attachment in view.regular_attachments:
    ...     print(attachment.title)
    ...
    attachment 1
    attachment 2
    >>> for patch in view.patches:
    ...     print(patch.title)
    ...
    patch 1
    patch 2
    >>> for attachment in view.regular_attachments:
    ...     print(attachment.displayed_url)
    ...
    http://bugs.launchpad.test/firefox/+bug/5/+attachment/.../+files/a1
    http://bugs.launchpad.test/firefox/+bug/5/+attachment/.../+files/a2
    >>> for patch in view.patches:
    ...     print(patch.displayed_url)
    ...
    http://bugs.launchpad.test/firefox/+bug/5/+attachment/.../+files/p1
    http://bugs.launchpad.test/firefox/+bug/5/+attachment/.../+files/p2


Bug Navigation
--------------

The +subscribe link has different text depending on if the user is
subscribed to the bug, or if a team the user of a member of is
subscribed to it.

If the user isn't subscribed to the bug , 'Subscribe' is shown.

    >>> login("foo.bar@canonical.com")
    >>> foo_bar = getUtility(IPersonSet).getByEmail("foo.bar@canonical.com")
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> bug_one.isSubscribed(foo_bar)
    False

    >>> from lp.bugs.browser.bug import BugContextMenu
    >>> bug_one_bugtask = bug_one.bugtasks[0]
    >>> getUtility(IOpenLaunchBag).clear()
    >>> getUtility(IOpenLaunchBag).add(bug_one_bugtask)
    >>> bug_menu = BugContextMenu(bug_one_bugtask)
    >>> bug_menu.subscription().text
    'Subscribe'

    >>> bug_menu.subscription().icon
    'add'

If we subscribe Foo Bar, 'Edit subscription' is shown.

    >>> bug_one.subscribe(foo_bar, foo_bar)
    <BugSubscription ...>
    >>> bug_menu = BugContextMenu(bug_one_bugtask)
    >>> bug_menu.subscription().text
    'Edit subscription'

    >>> bug_menu.subscription().icon
    'edit'

If we subscribe one of the teams that Foo Bar is a member of, it will
still say 'Edit subscription':

    >>> launchpad_team = getUtility(IPersonSet).getByName("launchpad")
    >>> foo_bar.inTeam(launchpad_team)
    True
    >>> bug_one.subscribe(launchpad_team, launchpad_team)
    <BugSubscription ...>
    >>> bug_menu = BugContextMenu(bug_one_bugtask)
    >>> bug_menu.subscription().text
    'Edit subscription'

    >>> bug_menu.subscription().icon
    'edit'

If we now unsubscribe Foo Bar, it will say 'Subscribe', since team
unsubsription is handled by the remove icon next the team in the
subscribers portlet.

    >>> bug_one.unsubscribe(foo_bar, foo_bar)

    >>> bug_menu = BugContextMenu(bug_one_bugtask)
    >>> bug_menu.subscription().text
    'Subscribe'

    >>> bug_menu.subscription().icon
    'add'

If the user is logged out, it says 'Subscribe/Unsubscribe', since we
can't know if the user is subscribed or not.

    >>> login(ANONYMOUS)
    >>> bug_menu = BugContextMenu(bug_one_bugtask)
    >>> bug_menu.subscription().text
    'Subscribe/Unsubscribe'

    >>> bug_menu.subscription().icon
    'edit'

    Subscribers from duplicates have the option to unsubscribe as well. For
    example, Steve Alexander can currently subscribe to bug #3.

    >>> bug_three = bugset.get(3)
    >>> bug_three_bugtask = bug_three.bugtasks[0]
    >>> getUtility(IOpenLaunchBag).clear()
    >>> getUtility(IOpenLaunchBag).add(bug_three_bugtask)

    >>> login("steve.alexander@ubuntulinux.com")

    >>> bug_menu = BugContextMenu(bug_three_bugtask)
    >>> bug_menu.subscription().text
        'Subscribe'

    Bug if bug #2, a bug that Steve is directly subscribed to, is marked as
    a dupe of bug #3, then Steve gets indirectly subscribed to bug #3, and
    is presented with the "Edit subscription" link.

    >>> bug_two.markAsDuplicate(bug_three)

    >>> bug_menu.subscription().text
    'Edit subscription'

    Now, let's revert that duplicate marking and demonstrate it again, this
    time where the subscription from the duplicate is of a /team/ of which
    the current user is a member. So, for Foo Bar, bug #3 has a simple
    Subscribe link initially.

    >>> bug_two.markAsDuplicate(None)

    >>> login("foo.bar@canonical.com")

    >>> bug_menu.subscription().text
        'Subscribe'

    Now let's subscribe Ubuntu Team directly to bug #2. When bug #2 is duped
    against bug #3, the link didn't change to Subscribe/Unsubscribe

    >>> ubuntu_team = getUtility(IPersonSet).getByName("ubuntu-team")
    >>> bug_two.subscribe(ubuntu_team, ubuntu_team)
    <BugSubscription ...>

    >>> bug_two.markAsDuplicate(bug_three)

    >>> bug_menu.subscription().text
    'Subscribe'


BugTasks and Nominations Table
------------------------------

Content is rendered at the top of the bug page which shows both bugtasks
and nominations and various links like "Does this bug affect you" and
"Also Affects Project" etc. This content is rendered with the
+bugtasks-and-nominations-portal view.

    >>> request = LaunchpadTestRequest()

    >>> bugtasks_and_nominations_view = getMultiAdapter(
    ...     (bug_one_bugtask.bug, request),
    ...     name="+bugtasks-and-nominations-portal",
    ... )
    >>> bugtasks_and_nominations_view.initialize()

The bugtasks and nominations table itself is rendered with the
+bugtasks-and-nominations-table view.

    >>> request = LaunchpadTestRequest()

    >>> bugtasks_and_nominations_view = getMultiAdapter(
    ...     (bug_one_bugtask.bug, request),
    ...     name="+bugtasks-and-nominations-table",
    ... )
    >>> bugtasks_and_nominations_view.initialize()

The getBugTaskAndNominationViews method returns a list of views for
bugtasks and nominations to render in the table, sorted by
bugtargetdisplayname. Approved nominations are not included in the
returned results, because an approved nomination will have created a
task anyway.

    >>> from lp.bugs.interfaces.bugnomination import IBugNomination
    >>> from lp.bugs.interfaces.bugtask import IBugTask

    >>> def get_object_type(task_or_nomination):
    ...     if IBugTask.providedBy(task_or_nomination):
    ...         return "bugtask"
    ...     elif IBugNomination.providedBy(task_or_nomination):
    ...         return "nomination"
    ...     else:
    ...         return "unknown"
    ...

    >>> def print_tasks_and_nominations(task_and_nomination_views):
    ...     for task_or_nomination_view in task_and_nomination_views:
    ...         task_or_nomination = task_or_nomination_view.context
    ...         print(
    ...             "%s, %s, %s"
    ...             % (
    ...                 get_object_type(task_or_nomination),
    ...                 task_or_nomination.status.title,
    ...                 task_or_nomination.target.bugtargetdisplayname,
    ...             )
    ...         )
    ...

    >>> task_and_nomination_views = (
    ...     bugtasks_and_nominations_view.getBugTaskAndNominationViews()
    ... )

    >>> print_tasks_and_nominations(task_and_nomination_views)
    bugtask, New, Mozilla Firefox
    nomination, Nominated, Mozilla Firefox 1.0
    bugtask, Confirmed, mozilla-firefox (Debian)
    bugtask, New, mozilla-firefox (Ubuntu)
    nomination, Nominated, Ubuntu Hoary

After creating bug supervisors for Ubuntu and Firefox Let's nominate the bug
for upstream and an Ubuntu series and see how the list changes.

    >>> from lp.testing.sampledata import ADMIN_EMAIL
    >>> from zope.component import getUtility
    >>> from zope.security.proxy import removeSecurityProxy
    >>>
    >>> login(ADMIN_EMAIL)
    >>> nominator = factory.makePerson(name="nominator")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> ubuntu = removeSecurityProxy(ubuntu)
    >>> ubuntu.bug_supervisor = nominator
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> firefox = removeSecurityProxy(firefox)
    >>> firefox.bug_supervisor = nominator

(Login as a bug supervisor to be able to nominate.)

    >>> ignored = login_person(nominator)

    >>> current_user = getUtility(ILaunchBag).user
    >>> ubuntu_warty = ubuntu.getSeries("warty")
    >>> firefox_trunk = firefox.getSeries("trunk")

    >>> bug_one.addNomination(current_user, target=ubuntu_warty)
    <BugNomination ...>
    >>> bug_one.addNomination(current_user, target=firefox_trunk)
    <BugNomination ...>

    >>> task_and_nomination_views = (
    ...     bugtasks_and_nominations_view.getBugTaskAndNominationViews()
    ... )

    >>> print_tasks_and_nominations(task_and_nomination_views)
    bugtask, New, Mozilla Firefox
    nomination, Nominated, Mozilla Firefox 1.0
    nomination, Nominated, Mozilla Firefox trunk
    bugtask, Confirmed, mozilla-firefox (Debian)
    bugtask, New, mozilla-firefox (Ubuntu)
    nomination, Nominated, Ubuntu Hoary
    nomination, Nominated, Ubuntu Warty

Let's add another affected package in Ubuntu to the bug.

    >>> evolution = ubuntu.getSourcePackage("evolution")

    >>> current_user = getUtility(ILaunchBag).user

    >>> bugtaskset.createTask(bug_one, current_user, evolution)
    <BugTask ...>

A nomination row will be included for evolution now too.

    >>> bugtasks_and_nominations_view.initialize()
    >>> task_and_nomination_views = (
    ...     bugtasks_and_nominations_view.getBugTaskAndNominationViews()
    ... )

    >>> print_tasks_and_nominations(task_and_nomination_views)
    bugtask, New, Mozilla Firefox
    nomination, Nominated, Mozilla Firefox 1.0
    nomination, Nominated, Mozilla Firefox trunk
    bugtask, New, evolution (Ubuntu)
    nomination, Nominated, Ubuntu Hoary
    nomination, Nominated, Ubuntu Warty
    bugtask, Confirmed, mozilla-firefox (Debian)
    bugtask, New, mozilla-firefox (Ubuntu)
    nomination, Nominated, Ubuntu Hoary
    nomination, Nominated, Ubuntu Warty

When a nomination is approved, it turns into a task; the nomination is
no longer shown. Declined nominations continue to be shown.

(First, login as an admin, to ensure we have the privileges to
approve/decline nominations.)

    >>> login("foo.bar@canonical.com")
    >>> current_user = getUtility(ILaunchBag).user

    >>> ubuntu_hoary = ubuntu.getSeries("hoary")
    >>> hoary_nomination = bug_one.getNominationFor(ubuntu_hoary)
    >>> warty_nomination = bug_one.getNominationFor(ubuntu_warty)

    >>> hoary_nomination.approve(current_user)
    >>> warty_nomination.decline(current_user)

    >>> bugtasks_and_nominations_view.initialize()
    >>> task_and_nomination_views = (
    ...     bugtasks_and_nominations_view.getBugTaskAndNominationViews()
    ... )

    >>> print_tasks_and_nominations(task_and_nomination_views)
    bugtask, New, Mozilla Firefox
    nomination, Nominated, Mozilla Firefox 1.0
    nomination, Nominated, Mozilla Firefox trunk
    bugtask, New, evolution (Ubuntu)
    nomination, Declined, Ubuntu Warty
    bugtask, New, evolution (Ubuntu Hoary)
    bugtask, Confirmed, mozilla-firefox (Debian)
    bugtask, New, mozilla-firefox (Ubuntu)
    nomination, Declined, Ubuntu Warty
    bugtask, New, mozilla-firefox (Ubuntu Hoary)

Bug Edit Page
=============

The bug edit page is used to edit the summary, description,
and bug tags. If the user try to add a tag that hasn't been used in the
current context, we display a confirmation button, which shouldn't be
automatically rendered by the form template. In order to show how it
works, let's override the edit page, making it a bit shorter, and
initialize the test harness.

    >>> from lp.bugs.browser.bug import BugEditView
    >>> class BugEditViewTest(BugEditView):
    ...     def index(self):
    ...         print("EDIT BUG")
    ...

    >>> firefox_task = bug_one.bugtasks[0]
    >>> print(firefox_task.bugtargetdisplayname)
    Mozilla Firefox
    >>> from lp.testing.deprecated import LaunchpadFormHarness
    >>> bug_edit = LaunchpadFormHarness(firefox_task, BugEditViewTest)

Initially, the normal edit page is shown, with a single button.

    >>> bug_edit.view.render()
    EDIT BUG
    >>> bug_edit.view.field_names
    ['title', 'description', 'tags']
    >>> [action.label for action in bug_edit.view.actions]
    ['Change']

If we fill in some values and submit the action, the view will redirect
and the bug will have been edited.

    >>> login("test@canonical.com")
    >>> edit_values = {
    ...     "field.title": "New title",
    ...     "field.description": "New description.",
    ...     "field.tags": "doc",
    ... }

    >>> bug_edit.submit("change", edit_values)
    >>> bug_edit.hasErrors()
    False
    >>> bug_edit.wasRedirected()
    True
    >>> print(bug_one.title)
    New title
    >>> print(bug_one.description)
    New description.
    >>> for tag in bug_one.tags:
    ...     print(tag)
    ...
    doc

Emails are sent out by adding entries to the bugnotification table. We
need to know how many messages are currently in that table.

    >>> from lp.bugs.model.bugnotification import BugNotification
    >>> from lp.services.database.interfaces import IStore
    >>> bn_set = IStore(BugNotification).find(BugNotification, bug=bug_one)
    >>> start_bugnotification_count = bn_set.count()

Add 'new-tag' multiple times so that we can verify that it will only be added
once.

    >>> edit_values["field.tags"] = "new-tag doc new-tag"
    >>> bug_edit.submit("change", edit_values)
    >>> bug_edit.hasErrors()
    False
    >>> bug_edit.wasRedirected()
    True
    >>> for tag in bug_one.tags:
    ...     print(tag)
    ...
    doc
    new-tag

Since the 'new-tag' was added, a new entry in the bugnotification table
should exist.

    >>> bn_set = (
    ...     IStore(BugNotification)
    ...     .find(BugNotification, bug=bug_one)
    ...     .order_by(BugNotification.id)
    ... )
    >>> start_bugnotification_count == bn_set.count() - 1
    True
    >>> print(bn_set.last().message.text_contents)
    ** Tags added: new-tag


Displaying BugActivity interleaved with comments
------------------------------------------------

BugTaskView offers a means for us to get a list of comments and activity
for a bug, ordered by date.

First, some set-up.

    >>> from datetime import datetime, timedelta, timezone
    >>> from lp.bugs.adapters.bugchange import (
    ...     BugLocked,
    ...     BugLockReasonSet,
    ...     BugTaskImportanceExplanationChange,
    ...     BugTaskStatusExplanationChange,
    ...     BugTitleChange,
    ...     BugUnlocked,
    ... )
    >>> from lp.bugs.enums import BugLockStatus
    >>> nowish = datetime(2009, 3, 26, 21, 37, 45, tzinfo=timezone.utc)

    >>> login("foo.bar@canonical.com")
    >>> product = factory.makeProduct(name="testproduct")
    >>> bug = factory.makeBug(title="A bug title", target=product)
    >>> title_change = BugTitleChange(
    ...     when=nowish,
    ...     person=foo_bar,
    ...     what_changed="title",
    ...     old_value=bug.title,
    ...     new_value="A new bug title",
    ... )
    >>> bug.addChange(title_change)

    >>> nowish = nowish + timedelta(days=1)
    >>> locked = BugLocked(
    ...     when=nowish,
    ...     person=foo_bar,
    ...     old_status=BugLockStatus.UNLOCKED,
    ...     new_status=BugLockStatus.COMMENT_ONLY,
    ...     reason="too hot",
    ... )
    >>> bug.addChange(locked)
    >>> nowish = nowish + timedelta(days=1)
    >>> lock_reason_updated = BugLockReasonSet(
    ...     when=nowish,
    ...     person=foo_bar,
    ...     old_reason="too hot",
    ...     new_reason="too hot!",
    ... )
    >>> bug.addChange(lock_reason_updated)
    >>> nowish = nowish + timedelta(days=1)
    >>> lock_reason_unset = BugLockReasonSet(
    ...     when=nowish,
    ...     person=foo_bar,
    ...     old_reason="too hot!",
    ...     new_reason=None,
    ... )
    >>> bug.addChange(lock_reason_unset)
    >>> nowish = nowish + timedelta(days=1)
    >>> unlocked = BugUnlocked(
    ...     when=nowish, person=foo_bar, old_status=BugLockStatus.COMMENT_ONLY
    ... )
    >>> bug.addChange(unlocked)
    >>> nowish = nowish + timedelta(days=1)
    >>> importance_explanation_set = BugTaskImportanceExplanationChange(
    ...     when=nowish,
    ...     person=foo_bar,
    ...     what_changed="importance explanation",
    ...     old_value=None,
    ...     new_value="This is a security issue",
    ...     bug_task=bug.default_bugtask,
    ... )
    >>> bug.addChange(importance_explanation_set)
    >>> status_explanation_set = BugTaskStatusExplanationChange(
    ...     when=nowish,
    ...     person=foo_bar,
    ...     what_changed="status explanation",
    ...     old_value=None,
    ...     new_value="Blocked on foo",
    ...     bug_task=bug.default_bugtask,
    ... )
    >>> bug.addChange(status_explanation_set)

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "field.subject": bug.title,
    ...         "field.comment": "A comment, for the reading of.",
    ...         "field.actions.save": "Save Changes",
    ...     },
    ... )
    >>> view = getMultiAdapter(
    ...     (bug.bugtasks[0], request), name="+addcomment-form"
    ... )
    >>> view.initialize()

    >>> flush_database_updates()
    >>> transaction.commit()

    >>> request = LaunchpadTestRequest(method="GET")
    >>> view = getMultiAdapter((bug.bugtasks[0], request), name="+index")

The activity_and_comments property of BugTaskView is a list of comments
and activity on a bug, ordered by the date that they occurred. Each item
is encapsulated in a dict, in the form: {'comment': <BugComment>} or
{'activity': [<BugActivityItem>...]}. Each dict also contains a 'date'
item, which is used to sort the list.

If we iterate over the list of activity_and_comments we can examine, in
order, the comments and activity that have taken place on a bug.

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "testproduct.status": "Confirmed",
    ...         "testproduct.actions.save": "Save Changes",
    ...     },
    ... )
    >>> view = getMultiAdapter((bug.bugtasks[0], request), name="+editstatus")
    >>> view.initialize()

    >>> view = getMultiAdapter((bug.bugtasks[0], request), name="+index")
    >>> view.initialize()

    >>> def print_activities(activities):
    ...     for activity in activities:
    ...         target_name = activity["target"]
    ...         if target_name is None:
    ...             print("Changed:")
    ...         else:
    ...             print("Changed in %s:" % target_name)
    ...         activity_items = activity["activity"]
    ...         for activity_item in activity_items:
    ...             print(
    ...                 "* %s: %s => %s"
    ...                 % (
    ...                     activity_item.change_summary,
    ...                     activity_item.oldvalue,
    ...                     activity_item.newvalue,
    ...                 )
    ...             )
    ...

    >>> def print_comment(comment):
    ...     print(comment.text_for_display)
    ...     print_activities(comment.activity)
    ...

    >>> def print_activity_and_comments(activity_and_comments):
    ...     for activity_or_comment in activity_and_comments:
    ...         print("-- {person.name} --".format(**activity_or_comment))
    ...         if "activity" in activity_or_comment:
    ...             print_activities(activity_or_comment["activity"])
    ...         if "comment" in activity_or_comment:
    ...             print_comment(activity_or_comment["comment"])
    ...

    >>> print_activity_and_comments(view.activity_and_comments)
    -- name16 --
    Changed:
    * summary: A bug title => A new bug title
    -- name16 --
    Changed:
    * lock status: Unlocked => Comment-only
    -- name16 --
    Changed:
    * lock reason: too hot => too hot!
    -- name16 --
    Changed:
    * lock reason: too hot! => unset
    -- name16 --
    Changed:
    * lock status: Comment-only => Unlocked
    -- name16 --
    Changed in testproduct:
    * importance explanation: unset => This is a security issue
    * status explanation: unset => Blocked on foo
    -- name16 --
    A comment, for the reading of.
    Changed in testproduct:
    * status: New => Confirmed

If a comment and a BugActivity item occur at the same time, the activity
item will be returned in the comment's activity property rather than as
an activity item in its own right. This allows us to group coincidental
comments and activity together.

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "testproduct.status": "Confirmed",
    ...         "testproduct.importance": "High",
    ...         "testproduct.comment_on_change": "I triaged it.",
    ...         "testproduct.actions.save": "Save Changes",
    ...     },
    ... )
    >>> view = getMultiAdapter((bug.bugtasks[0], request), name="+editstatus")
    >>> view.initialize()

    >>> view = getMultiAdapter((bug.bugtasks[0], request), name="+index")
    >>> view.initialize()

Looking at activity_and_comments will give us the same results as
before, plus the new comment, since the changes we just made were
grouped with that comment.

    >>> print_activity_and_comments(view.activity_and_comments)
    -- name16 --
    Changed:
    * summary: A bug title => A new bug title
    -- name16 --
    Changed:
    * lock status: Unlocked => Comment-only
    -- name16 --
    Changed:
    * lock reason: too hot => too hot!
    -- name16 --
    Changed:
    * lock reason: too hot! => unset
    -- name16 --
    Changed:
    * lock status: Comment-only => Unlocked
    -- name16 --
    Changed in testproduct:
    * importance explanation: unset => This is a security issue
    * status explanation: unset => Blocked on foo
    -- name16 --
    A comment, for the reading of.
    -- name16 --
    I triaged it.
    Changed in testproduct:
    * importance: Undecided => High
    * status: New => Confirmed


Getting the list of possible duplicates for a new bug
-----------------------------------------------------

It's possible to get a list of the possible duplicates for a new bug by
using the +filebug-show-similar view of a BugTarget.

The +filebug-show-similar view takes a single parameter, 'title'. It
uses this to search for similar bugs.

    >>> request = LaunchpadTestRequest(method="GET", form={"title": "a"})
    >>> view = getMultiAdapter(
    ...     (firefox, request), name="+filebug-show-similar"
    ... )
    >>> view.initialize()

The view offers a list of bugs similar to the one whose title we just
searched for.

    >>> for bug in view.similar_bugs:
    ...     print(bug.title)
    ...
    New title
    Reflow problems with complex page layouts
    Firefox install instructions should be complete
    a firefox bug

If we refine the search criteria, we'll get different results.

    >>> request = LaunchpadTestRequest(
    ...     method="GET", form={"title": "problems"}
    ... )
    >>> view = getMultiAdapter(
    ...     (firefox, request), name="+filebug-show-similar"
    ... )
    >>> view.initialize()
    >>> for bug in view.similar_bugs:
    ...     print(bug.title)
    ...
    Reflow problems with complex page layouts
