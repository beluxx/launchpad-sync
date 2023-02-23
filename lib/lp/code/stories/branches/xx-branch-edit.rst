Editing Branches
================

Once a branch has been created in Launchpad, most of the details are
able to be edited by the owner of the branch.  The registrant and
date_created are not editable for obvious reasons.


Editing branch details
----------------------

First, check that the edit link is visible on the branch page and click
on that link to load the +edit form for the branch.

    >>> from lp.services.mail import stub
    >>> stub.test_emails = []

The link to edit the branch details is only available to the branch
owner, Launchpad administrators or members of the Bazaar Experts team.

    >>> admin_browser.open(
    ...     "http://code.launchpad.test/~name12/gnome-terminal/klingon"
    ... )
    >>> link = admin_browser.getLink("Change branch details")

    >>> admin_browser = setupBrowser(auth="Basic admin@canonical.com:test")
    >>> admin_browser.open(
    ...     "http://code.launchpad.test/~name12/gnome-terminal/klingon"
    ... )
    >>> link = admin_browser.getLink("Change branch details")

    >>> nopriv_browser = setupBrowser(auth="Basic nopriv@canonical.com:test")
    >>> nopriv_browser.open(
    ...     "http://code.launchpad.test/~name12/gnome-terminal/klingon"
    ... )
    >>> link = nopriv_browser.getLink("Change branch details")
    Traceback (most recent call last):
    zope.testbrowser.browser.LinkNotFoundError

    >>> browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> browser.open(
    ...     "http://code.launchpad.test/~name12/gnome-terminal/klingon"
    ... )
    >>> browser.getLink("Change branch details").click()
    >>> browser.url
    'http://code.launchpad.test/~name12/gnome-terminal/klingon/+edit'

The form should have been filled with sample data values.

    >>> print(browser.getControl("Branch URL").value)
    http://trekkies.example.com/gnome-terminal/klingon

Then, post the changes to the summary. Also add a trailing slash to the
URL.

    >>> browser.getControl("Branch URL").value += "/"
    >>> browser.getControl(
    ...     "Description"
    ... ).value = "Klingon support for Gnome Terminal"
    >>> browser.getControl("Change Branch").click()

We should be redirected to the branch page, check that our changes were
taken into account. The trailing slash added to the URL has been
ignored.

Since the details have been changed, emails should have been sent out.
Emails go out to all the subscribers.  Now there are no subscribers
so there should be no emails.

    >>> from zope.component import getUtility
    >>> from lp.code.interfaces.branchjob import IBranchModifiedMailJobSource
    >>> from lp.services.config import config
    >>> from lp.services.job.runner import JobRunner

    >>> def run_modified_mail_jobs():
    ...     with permissive_security_policy(
    ...         config.IBranchModifiedMailJobSource.dbuser
    ...     ):
    ...         job_source = getUtility(IBranchModifiedMailJobSource)
    ...         JobRunner.fromReady(job_source).runAll()
    ...

    >>> run_modified_mail_jobs()
    >>> len(stub.test_emails)
    0

    >>> print(browser.url)
    http://code.launchpad.test/~name12/gnome-terminal/klingon

    >>> print(extract_text(find_tag_by_id(browser.contents, "branch-info")))
    Branch information ...
    Project:  GNOME Terminal
    Status: Experimental Edit
    Location: http://trekkies.example.com/gnome-terminal/klingon
    Last mirrored: ...

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "branch-description").p
    ...     )
    ... )
    Klingon support for Gnome Terminal


Editing the Lifecycle Status
----------------------------

To change the branch status, the +edit page is also used:

    >>> browser.open(
    ...     "http://code.launchpad.test"
    ...     "/~name12/gnome-terminal/klingon/+edit"
    ... )

The form displays the branch current status.

    >>> print_radio_button_field(browser.contents, "lifecycle_status")
    (*) Experimental
    ( ) Development
    ( ) Mature
    ( ) Merged
    ( ) Abandoned

The user selects the new status value:

    >>> browser.getControl("Merged").click()
    >>> browser.getControl("Change Branch").click()

The branch page is displayed with the new status:

    >>> browser.url
    'http://code.launchpad.test/~name12/gnome-terminal/klingon'

    >>> contents = browser.contents
    >>> status_tag = find_tag_by_id(contents, "edit-lifecycle_status")
    >>> print(extract_text(status_tag))
    Merged Edit

Set the branch status back to its initial state.

    >>> browser.open(
    ...     "http://code.launchpad.test"
    ...     "/~name12/gnome-terminal/klingon/+edit"
    ... )
    >>> browser.getControl("Experimental").click()
    >>> browser.getControl("Change Branch").click()


Changing branch name
--------------------

The edit form allows changing the name of a branch, and must correctly
redirect to the new branch page.

    >>> browser.getLink("Change branch details").click()
    >>> browser.getControl("Name").value = "junk"
    >>> browser.getControl("Change Branch").click()
    >>> browser.url
    'http://code.launchpad.test/~name12/gnome-terminal/junk'

Branch names are less strictly constrained than most others in Launchpad
-- they are not restricted to lower case, and can contain underscores in
addition to the plus signs, dots and hyphens allowed by the default name
validator.

    >>> browser.getLink("Change branch details").click()
    >>> browser.getControl("Name").value = "USELESS_junk"
    >>> browser.getControl("Change Branch").click()
    >>> browser.url
    'http://code.launchpad.test/~name12/gnome-terminal/USELESS_junk'

We can also reset the branch name to its original value, and check that
the branch was moved back to its original location.

    >>> browser.getLink("Change branch details").click()
    >>> browser.getControl("Name").value = "junk.dev"
    >>> browser.getControl("Change Branch").click()
    >>> browser.url
    'http://code.launchpad.test/~name12/gnome-terminal/junk.dev'


Name conflicts
--------------

The product and branch name contributes to the unique name of a branch.
The name of a branch has to be unique over all the branches of that
product for the given branch owner.

Since we can't change the product on the edit form, we only have to
worry about conflicts when changing the branch name.

Let's try to change the name of the branch to the name of some branch we
already own in the same product.

    >>> browser.open(
    ...     "http://code.launchpad.test" "/~name12/gnome-terminal/main/+edit"
    ... )
    >>> browser.getControl("Name").value = "2.6"
    >>> browser.getControl("Change Branch").click()
    >>> browser.url
    'http://code.launchpad.test/~name12/gnome-terminal/main/+edit'

    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    You already have a branch for GNOME Terminal called 2.6.


URL validation
--------------

Edit forms do the same URL validation checks as the add forms.

    >>> browser.open("http://code.launchpad.test/~name12/gnome-terminal/main")
    >>> browser.getLink("Change branch details").click()
    >>> browser.getControl(
    ...     "Branch URL"
    ... ).value = "http://bazaar.launchpad.test/~foo/bar/baz"
    >>> browser.getControl("Change Branch").click()

    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    For Launchpad to mirror a branch, the original branch cannot be
    on launchpad.test.

Check that when editing a hosted branch the URL field is not shown.

    >>> browser.open(
    ...     "http://code.launchpad.test/~name12/gnome-terminal/scanned"
    ... )
    >>> browser.getLink("Change branch details").click()
    >>> browser.getControl(
    ...     "Branch URL"
    ... ).value = "http://acme.example.com/~foo/bar/baz"
    Traceback (most recent call last):
    ...
    LookupError: label ...'Branch URL'
    ...


Editing the whiteboard
----------------------

The whiteboard is only visible and editable on import branches, and is
editable by any user.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.code.enums import (
    ...     BranchSubscriptionNotificationLevel,
    ...     BranchSubscriptionDiffSize,
    ...     CodeReviewNotificationLevel,
    ... )
    >>> login("admin@canonical.com")
    >>> sample_person = getUtility(IPersonSet).getByName("name12")
    >>> foogoo = factory.makeProduct(name="foogoo", owner=sample_person)
    >>> foogoo_svn_import = factory.makeProductCodeImport(
    ...     svn_branch_url="http://foogoo.example.com",
    ...     branch_name="foogoo-svn",
    ...     product=foogoo,
    ...     registrant=sample_person,
    ... )
    >>> foogoo_svn = foogoo_svn_import.branch
    >>> _unused = foogoo_svn.subscribe(
    ...     sample_person,
    ...     BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
    ...     BranchSubscriptionDiffSize.NODIFF,
    ...     CodeReviewNotificationLevel.NOEMAIL,
    ...     sample_person,
    ... )
    >>> logout()

    >>> nopriv_browser = setupBrowser(auth="Basic no-priv@canonical.com:test")
    >>> nopriv_browser.open(
    ...     "http://code.launchpad.test" "/~name12/foogoo/foogoo-svn"
    ... )
    >>> whiteboard_tag = find_tag_by_id(
    ...     nopriv_browser.contents, "branch-whiteboard-value"
    ... )

There is no whiteboard section shown if there is no whiteboard value
set.

    >>> stub.test_emails = []
    >>> print(whiteboard_tag)
    None

    >>> nopriv_browser.getLink("Edit whiteboard").click()

    >>> nopriv_browser.getControl("Whiteboard").value = "New whiteboard value"
    >>> nopriv_browser.getControl("Change Branch").click()

    >>> whiteboard_tag = find_tag_by_id(
    ...     nopriv_browser.contents, "branch-whiteboard-value"
    ... )
    >>> print(extract_text(whiteboard_tag))
    New whiteboard value

The subscribers of the branch are notified that someone else has
modified the details of the branch.

    >>> run_modified_mail_jobs()
    >>> len(stub.test_emails)
    1

    >>> from lp.testing.mail_helpers import print_emails

    >>> print_emails(decode=True)
    From: No Privileges Person <no-priv@canonical.com>
    To: Sample Person <test@canonical.com>
    Subject: [Branch ~name12/foogoo/foogoo-svn]
    ...
    New whiteboard value
    <BLANKLINE>
    --
    lp://dev/~name12/foogoo/foogoo-svn
    http://code.launchpad.test/~name12/foogoo/foogoo-svn
    <BLANKLINE>
    You are subscribed to branch lp://dev/~name12/foogoo/foogoo-svn.
    To unsubscribe from this branch go to
    http://code.l.../~name12/foogoo/foogoo-svn/+edit-subscription
    <BLANKLINE>
    ----------------------------------------


Changing the branch owner
-------------------------

The user is able to change the owner of the branch using the edit
details page.

    >>> browser.open("http://code.launchpad.test/~name12/gnome-terminal/main")
    >>> browser.getLink("Change branch details").click()
    >>> browser.getControl("Owner").displayValue = ["Landscape Developers"]
    >>> browser.getControl("Change Branch").click()

When the owner is changed a notification is shown.

    >>> print_feedback_messages(browser.contents)
    The branch owner has been changed to Landscape Developers ...


Assignment to anyone
....................

Bazaar Experts and Launchpad administrators are able to reassign a
branch to any valid person or team.

    >>> admin_browser.open("http://code.launchpad.test/~name12/firefox/main")
    >>> admin_browser.getLink("Change branch details").click()
    >>> admin_browser.getControl("Owner").value = "mark"
    >>> admin_browser.getControl("Change Branch").click()
    >>> print(admin_browser.url)
    http://code.launchpad.test/~mark/firefox/main


Package branch editing by Uploaders
-----------------------------------

Official branches for distro series source packages are editable by
valid package uploaders.  The normal branch owner vocabulary is the
editor and the teams that they are a member of.  Official branches may
well have an owner that is different to the editor.

    >>> login("admin@canonical.com")
    >>> from lp.code.tests.helpers import make_official_package_branch
    >>> owner = factory.makePerson(
    ...     name="official-owner", displayname="Jane Doe"
    ... )
    >>> branch = make_official_package_branch(factory, owner=owner)
    >>> editor = factory.makePerson(name="editor", email="editor@example.com")
    >>> archive = branch.distroseries.distribution.main_archive
    >>> spn = branch.sourcepackage.sourcepackagename
    >>> from lp.soyuz.interfaces.archivepermission import (
    ...     IArchivePermissionSet,
    ... )
    >>> permission_set = getUtility(IArchivePermissionSet)
    >>> ignored = permission_set.newPackageUploader(archive, editor, spn)
    >>> branch_url = canonical_url(branch)
    >>> logout()

Even though the branch owner is not related to the editor, they stay as
the default owner for this branch.

    >>> browser = setupBrowser(auth="Basic editor@example.com:test")
    >>> browser.open(branch_url)
    >>> browser.getLink("Change branch details").click()

The owner is still the original owner.

    >>> browser.getControl("Owner").displayValue
    ['Jane Doe (official-owner)']

But the editor has the option to change the owner to themselves.

    >>> browser.getControl("Owner").displayOptions
    ['Jane Doe (official-owner)', 'Editor (editor)']


