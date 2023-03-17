Branch mirror failure messages
==============================

If a branch fails to mirror, that information is displayed in the mirror's
page, together with the last failure message we got when mirroring.

    >>> from lp.testing import ANONYMOUS, login, logout
    >>> login(ANONYMOUS)
    >>> eric = factory.makePerson(name="eric", email="eric@example.com")
    >>> from lp.code.enums import BranchType
    >>> mirror_branch = factory.makeAnyBranch(
    ...     branch_type=BranchType.MIRRORED, owner=eric
    ... )
    >>> mirror_name = mirror_branch.unique_name
    >>> from lp.services.webapp import canonical_url
    >>> branch_location = str(canonical_url(mirror_branch))
    >>> mirror_branch.startMirroring()
    >>> mirror_branch.mirrorFailed('Cannot access branch at "example.com".')
    >>> logout()

    >>> def print_browser_tag(browser, tag_id):
    ...     tag = find_tag_by_id(browser.contents, tag_id)
    ...     if tag is None:
    ...         print(tag)
    ...     else:
    ...         print(extract_text(tag))
    ...

The initial error message doesn't give a count or last failure.

    >>> browser = setupBrowser(auth="Basic eric@example.com:test")
    >>> browser.open(branch_location)
    >>> print_browser_tag(browser, "mirror-failure")
    This branch may be out of date, as Launchpad was not able to
    access it ... ago. (Cannot access branch at "example.com".)
    Launchpad will try again in ...
    If you have fixed the problem, please ask Launchpad to try again.

The user is shown a button "Try again".  Clicking on this will get
the branch to be mirrored ASAP.

    >>> browser.getControl("Try again").click()
    >>> print_browser_tag(browser, "mirror-failure")
    This branch may be out of date, as Launchpad was not able to
    access it ... ago. (Cannot access branch at "example.com".)
    Launchpad will try again shortly.

A subsequent failure shows:

    >>> login(ANONYMOUS)
    >>> from zope.component import getUtility
    >>> from lp.code.interfaces.branchlookup import IBranchLookup
    >>> mirror_branch = getUtility(IBranchLookup).getByUniqueName(mirror_name)
    >>> mirror_branch.startMirroring()
    >>> mirror_branch.mirrorFailed('Cannot access branch at "example.com".')
    >>> logout()

    >>> browser.open(branch_location)
    >>> print_browser_tag(browser, "mirror-failure")
    Launchpad has not been able to mirror this branch. The last attempt
    was ... ago. (Cannot access branch at "example.com".)
    Launchpad will try again in ...
    If you have fixed the problem, please ask Launchpad to try again.

If the mirror had been mirrored at some stage, the error is slightly
different.

    >>> from datetime import datetime, timezone
    >>> login("eric@example.com")  # To get Launchpad.Edit on the branch.
    >>> mirror_branch = getUtility(IBranchLookup).getByUniqueName(mirror_name)
    >>> mirror_branch.last_mirrored = datetime(
    ...     2007, 12, 25, 12, tzinfo=timezone.utc
    ... )
    >>> mirror_branch.startMirroring()
    >>> mirror_branch.mirrorFailed('Cannot access branch at "example.com".')
    >>> logout()

    >>> browser.open(branch_location)
    >>> print_browser_tag(browser, "mirror-failure")
    This branch may be out of date, as Launchpad has not been able to
    access between 2007-12-25 and ... ago.
    (Cannot access branch at "example.com".)
    Launchpad will try again in ...
    If you have fixed the problem, please ask Launchpad to try again.

If the branch has been disabled due to excessive failures, we get
a different message again.

    >>> login("eric@example.com")  # To get Launchpad.Edit on the branch.
    >>> mirror_branch = getUtility(IBranchLookup).getByUniqueName(mirror_name)
    >>> mirror_branch.mirror_failures = 100
    >>> mirror_branch.startMirroring()
    >>> mirror_branch.mirrorFailed('Cannot access branch at "example.com".')
    >>> logout()

    >>> browser.open(branch_location)
    >>> print_browser_tag(browser, "mirror-failure")
    Launchpad no longer mirrors this branch, because 101 attempts failed.
    (Cannot access branch at "example.com".)
    If you have fixed the problem, please ask Launchpad to try again.

There is the "Try again" button available to have the user let Launchpad
know that they have fixed the problem.

    >>> browser.getControl("Try again").click()
    >>> print_browser_tag(browser, "mirror-failure")
    This branch may be out of date, as Launchpad has not been able to
    access between 2007-12-25 and ... ago.
    (Cannot access branch at "example.com".)
    Launchpad will try again shortly.

Launchpad admins can see the detailed message.

    >>> admin_browser.open(branch_location)
    >>> print_browser_tag(admin_browser, "mirror-failure")
    This branch may be out of date, as Launchpad has not been able to
    access between 2007-12-25 and ... ago.
    (Cannot access branch at "example.com".)
    Launchpad will try again shortly.

If the user is not logged in, or is not the owner of the branch, or an admin
they get a summary failure message.

    >>> anon_browser.open(branch_location)
    >>> print_browser_tag(anon_browser, "mirror-failure")
    This branch may be out of date, because Launchpad has not been able to
    access it since 2007-12-25.

If a branch failed to mirror but no failure message was stored, we properly
report the absence of an error message.

    >>> login("eric@example.com")  # To get Launchpad.Edit on the branch.
    >>> mirror_branch = getUtility(IBranchLookup).getByUniqueName(mirror_name)
    >>> mirror_branch.mirror_status_message = None
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> flush_database_updates()
    >>> logout()

    >>> browser.open(branch_location)
    >>> print_browser_tag(browser, "mirror-failure")
    This branch may be out of date, as Launchpad has not been able to
    access between 2007-12-25 and ... ago.
    The cause of the error is not available.
    Launchpad will try again shortly.

Ultimately, if a branch was successfully mirrored, then we obviously won't
display any failure-related information.

    >>> login(ANONYMOUS)
    >>> mirror_branch = getUtility(IBranchLookup).getByUniqueName(mirror_name)
    >>> mirror_branch.startMirroring()
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(mirror_branch).branchChanged(
    ...     "", "some-revision-id", None, None, None
    ... )
    >>> logout()

    >>> browser.open(branch_location)
    >>> print_browser_tag(browser, "mirror-failure")
    None


Errors for ssh protocols
------------------------

If a branch has a sftp or bzr+ssh URL, immediately display an error message
(even before mirroring is attempted) and do not display the mirror failure
message.  Any ssh access requires that Launchpad use client ssh keys
or passwords, neither of which is currently supported.

    >>> login(ANONYMOUS)
    >>> mirror_branch = factory.makeAnyBranch(
    ...     branch_type=BranchType.MIRRORED,
    ...     url="sftp://example.com/bad/location",
    ... )
    >>> branch_location = canonical_url(mirror_branch)
    >>> logout()

    >>> browser = setupBrowser()
    >>> browser.open(branch_location)
    >>> print_browser_tag(browser, "mirror-failure")
    None
    >>> print_browser_tag(browser, "mirror-of-ssh")
    Launchpad cannot mirror this branch because its URL uses sftp or bzr+ssh.


Remote branches don't error on ssh access
-----------------------------------------

If a remote branch specifies a location with the scheme 'sftp' or 'bzr+ssh'
then there is no error shown.

    >>> login(ANONYMOUS)
    >>> remote_branch = factory.makeAnyBranch(
    ...     branch_type=BranchType.REMOTE,
    ...     url="bzr+ssh://example.com/remote/branch",
    ... )
    >>> branch_location = canonical_url(remote_branch)
    >>> logout()

    >>> browser = setupBrowser()
    >>> browser.open(branch_location)
    >>> print(find_tag_by_id(browser.contents, "mirror-failure"))
    None
    >>> print(find_tag_by_id(browser.contents, "mirror-of-ssh"))
    None
