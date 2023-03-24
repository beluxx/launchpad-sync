Edi a bug watch
================


After a bug watch is recorded, it is possible to go back and change it.

    >>> admin_browser.open("http://bugs.launchpad.test/bugs/1/+watch/2")
    >>> admin_browser.getControl(
    ...     "URL"
    ... ).value = "https://bugzilla.mozilla.org/show_bug.cgi?id=1000"
    >>> admin_browser.getControl("Change").click()
    >>> admin_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'
    >>> "https://bugzilla.mozilla.org/show_bug.cgi?id=1000" in (
    ...     admin_browser.contents
    ... )
    True

The URL supplied must be a valid bug tracker URL and must point to a
bug tracker already registered with Launchpad.

    >>> admin_browser.open("http://bugs.launchpad.test/bugs/1/+watch/2")
    >>> admin_browser.getControl(
    ...     "URL"
    ... ).value = "https://bugzilla.mozilla.org/foo_bug.cgi?id=1000"
    >>> admin_browser.getControl("Change").click()
    >>> admin_browser.url
    'http://bugs.launchpad.test/bugs/1/+watch/2/+edit'
    >>> for message in find_tags_by_class(admin_browser.contents, "message"):
    ...     print(extract_text(message))
    ...
    There is 1 error.
    Invalid bug tracker URL.

Likewise, stupid URLs are rejected with a polite error message.

    >>> admin_browser.getControl("URL").value = "GELLER"
    >>> admin_browser.getControl("Change").click()
    >>> admin_browser.url
    'http://bugs.launchpad.test/bugs/1/+watch/2/+edit'
    >>> for message in find_tags_by_class(admin_browser.contents, "message"):
    ...     print(extract_text(message))
    ...
    There is 1 error.
    "GELLER" is not a valid URI


BugWatch details
----------------

The +edit page for a watch also displays some details about the watch.

    >>> for data_tag in find_tags_by_class(
    ...     admin_browser.contents, "bugwatch-data"
    ... ):
    ...     print(extract_text(data_tag.decode_contents()))
    Tracker: The Mozilla.org Bug Tracker
    Remote bug ID: 1000
    Last status: None recorded
    Changed: 2004-10-04
    Checked: 2004-10-04
    Next check: Not yet scheduled
    Created: 2004-10-04
    Created by: Mark Shuttleworth

If we change the next_check date of the watch its will be shown in the
Next check column.

    >>> from zope.component import getUtility
    >>> from datetime import datetime, timedelta, timezone
    >>> from zope.security.proxy import removeSecurityProxy

    >>> from lp.testing import login, logout
    >>> from lp.bugs.interfaces.bugwatch import IBugWatchSet

    >>> login("foo.bar@canonical.com")
    >>> watch = getUtility(IBugWatchSet).get(2)
    >>> removeSecurityProxy(watch).next_check = datetime(
    ...     2010, 4, 8, 16, 7, tzinfo=timezone.utc
    ... )
    >>> logout()

    >>> admin_browser.open("http://bugs.launchpad.test/bugs/1/+watch/2")
    >>> data_tag = find_tag_by_id(
    ...     admin_browser.contents, "bugwatch-next_check"
    ... )
    >>> print(extract_text(data_tag.decode_contents()))
    Next check: 2010-04-08...


Recent activity
---------------

Recent activity on a bug watch is shown on the page as a list of
activity entries. When a watch has not been checked, no activity is
shown.

    >>> user_browser.open("http://bugs.launchpad.test/bugs/1/+watch/2")
    >>> recent_activity_list = find_tag_by_id(
    ...     user_browser.contents, "recent-watch-activity"
    ... )
    >>> print(recent_activity_list)
    None

Adding some activity to the watch will cause it to show up in the recent
activity list.

    >>> login("foo.bar@canonical.com")
    >>> watch = getUtility(IBugWatchSet).get(2)
    >>> watch.addActivity()
    >>> logout()

    >>> user_browser.open("http://bugs.launchpad.test/bugs/1/+watch/2")
    >>> recent_activity_list = find_tag_by_id(
    ...     user_browser.contents, "recent-watch-activity"
    ... )
    >>> print(extract_text(recent_activity_list))
    Update completed successfully ... ago

If an update fails, that too will be reflected in the list.

    >>> from lp.bugs.interfaces.bugwatch import BugWatchActivityStatus
    >>> login("foo.bar@canonical.com")
    >>> watch = getUtility(IBugWatchSet).get(2)
    >>> watch.addActivity(result=BugWatchActivityStatus.BUG_NOT_FOUND)
    >>> logout()

    >>> user_browser.open("http://bugs.launchpad.test/bugs/1/+watch/2")
    >>> recent_activity_list = find_tag_by_id(
    ...     user_browser.contents, "recent-watch-activity"
    ... )
    >>> print(extract_text(recent_activity_list))
    Update failed with error 'Bug Not Found' ... ago
    Update completed successfully ... ago

If a failure has an OOPS ID attached to it, that too will be reflected
in the list.

    >>> login("foo.bar@canonical.com")
    >>> watch = getUtility(IBugWatchSet).get(2)
    >>> watch.addActivity(
    ...     result=BugWatchActivityStatus.COMMENT_IMPORT_FAILED,
    ...     oops_id="OOPS-12345TEST",
    ... )
    >>> logout()

    >>> user_browser.open("http://bugs.launchpad.test/bugs/1/+watch/2")
    >>> recent_activity_list = find_tag_by_id(
    ...     user_browser.contents, "recent-watch-activity"
    ... )
    >>> print(extract_text(recent_activity_list))
    Update failed with error 'Unable to import...' (OOPS-12345TEST) ... ago
    Update failed with error 'Bug Not Found' ... ago
    Update completed successfully ... ago

If a Launchpad developer views the page the OOPS IDs will be linkified.

    >>> admin_browser.open("http://bugs.launchpad.test/bugs/1/+watch/2")
    >>> oops_link = admin_browser.getLink("OOPS-12345TEST")
    >>> print(oops_link.url)
    http...OOPS-12345TEST


Rescheduling a watch
--------------------

It's possible to reschedule a failing watch via the BugWatch +edit page
by clicking the "Update Now" button.

For a new watch, the "Update Now" button isn't shown.

    >>> login("foo.bar@canonical.com")
    >>> bug_watch = factory.makeBugWatch()
    >>> removeSecurityProxy(bug_watch).next_check = None
    >>> watch_url = "http://bugs.launchpad.test/bugs/%s/+watch/%s" % (
    ...     bug_watch.bug.id,
    ...     bug_watch.id,
    ... )
    >>> logout()

    >>> user_browser.open(watch_url)
    >>> user_browser.getControl("Update Now")
    Traceback (most recent call last):
      ...
    LookupError: label ...'Update Now'
    ...

If the watch has been checked but has never failed, the button will
remain hidden.

    >>> login("foo.bar@canonical.com")
    >>> bug_watch.addActivity()
    >>> logout()

    >>> user_browser.open(watch_url)
    >>> user_browser.getControl("Update Now")
    Traceback (most recent call last):
      ...
    LookupError: label ...'Update Now'
    ...

If the watch has failed less than 60% of its recent checks, the button
will appear on the page.

    >>> login("foo.bar@canonical.com")
    >>> bug_watch.addActivity(result=BugWatchActivityStatus.BUG_NOT_FOUND)
    >>> logout()

    >>> user_browser.open(watch_url)
    >>> reschedule_button = user_browser.getControl("Update Now")

    >>> data_tag = find_tag_by_id(
    ...     user_browser.contents, "bugwatch-next_check"
    ... )
    >>> print(extract_text(data_tag.decode_contents()))
    Next check: Not yet scheduled

Clicking the Update Now button will schedule it to be checked
immediately.

    >>> reschedule_button.click()

    >>> for message in find_tags_by_class(
    ...     user_browser.contents, "informational message"
    ... ):
    ...     print(extract_text(message))
    The ... bug watch has been scheduled for immediate checking.

Looking at the watch +edit page again, we can see that the watch has
been scheduled.

    >>> user_browser.open(watch_url)
    >>> data_tag = find_tag_by_id(
    ...     user_browser.contents, "bugwatch-next_check"
    ... )
    >>> print(extract_text(data_tag.decode_contents()))
    Next check: 2...

The button will no longer be shown on the page.

    >>> reschedule_button = user_browser.getControl("Update Now")
    Traceback (most recent call last):
      ...
    LookupError: label ...'Update Now'
    ...

If a watch has run once and failed once, the reschedule button will be
shown.

    >>> login("foo.bar@canonical.com")
    >>> bug_watch = factory.makeBugWatch()
    >>> removeSecurityProxy(bug_watch).next_check = None
    >>> bug_watch.addActivity(result=BugWatchActivityStatus.BUG_NOT_FOUND)
    >>> watch_url = "http://bugs.launchpad.test/bugs/%s/+watch/%s" % (
    ...     bug_watch.bug.id,
    ...     bug_watch.id,
    ... )
    >>> logout()

    >>> user_browser.open(watch_url)
    >>> reschedule_button = user_browser.getControl("Update Now")
    >>> reschedule_button.click()

    >>> for message in find_tags_by_class(
    ...     user_browser.contents, "informational message"
    ... ):
    ...     print(extract_text(message))
    The ... bug watch has been scheduled for immediate checking.

However, once the watch succeeds the button will disappear, even though
the watch has failed > 60% of the time. This is because the most recent
check succeeded, so there's no point in allowing users to reschedule the
watch for checking.

    >>> login("foo.bar@canonical.com")
    >>> removeSecurityProxy(bug_watch).next_check = datetime.now(
    ...     timezone.utc
    ... ) + timedelta(days=7)
    >>> bug_watch.addActivity()
    >>> logout()

    >>> user_browser.open(watch_url)
    >>> user_browser.getControl("Update Now")
    Traceback (most recent call last):
      ...
    LookupError: label ...'Update Now'
    ...


Resetting a watch
-----------------

It's possible to reset a watch at any time by clicking the "Reset this
watch" button on the watch's page.

    >>> from lp.testing.sampledata import ADMIN_EMAIL
    >>> login(ADMIN_EMAIL)
    >>> bug_watch = factory.makeBugWatch()
    >>> removeSecurityProxy(bug_watch).lastchecked = datetime.now(
    ...     timezone.utc
    ... )
    >>> watch_url = "http://bugs.launchpad.test/bugs/%s/+watch/%s" % (
    ...     bug_watch.bug.id,
    ...     bug_watch.id,
    ... )
    >>> logout()

The "Reset this watch" button will appear for administrators.

    >>> admin_browser.open(watch_url)
    >>> admin_browser.getControl("Reset this watch")
    <SubmitControl...>

It also appears for registry experts.

    >>> from lp.testing import login_celebrity

    >>> registry_expert = login_celebrity("registry_experts")
    >>> registry_browser = setupBrowser(
    ...     auth="Basic %s:test" % registry_expert.preferredemail.email
    ... )
    >>> logout()

    >>> registry_browser.open(watch_url)
    >>> reset_button = registry_browser.getControl("Reset this watch")

Clicking the button will reset the watch completely.

    >>> reset_button.click()
    >>> for message in find_tags_by_class(
    ...     registry_browser.contents, "informational message"
    ... ):
    ...     print(extract_text(message))
    The ... bug watch has been reset.

    >>> data_tag = find_tag_by_id(
    ...     user_browser.contents, "bugwatch-lastchecked"
    ... )
    >>> print(extract_text(data_tag.decode_contents()))
    Checked:

Should a non-admin, non-Launchpad-developer user visit the page, the
button will not appear.

    >>> user_browser.open(watch_url)
    >>> user_browser.getControl("Reset this watch")
    Traceback (most recent call last):
      ...
    LookupError: label ...'Reset this watch'
    ...
