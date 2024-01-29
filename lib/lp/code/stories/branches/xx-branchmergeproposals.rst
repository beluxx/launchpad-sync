Branch Merge Proposals
======================

Branch merge proposals are where you show the intent of merging
the code from one branch into another.

In order to test notifications, we need a subscriber for the branch.

    >>> from lp.testing import login, logout
    >>> login("admin@canonical.com")
    >>> from zope.component import getUtility
    >>> from lp.code.enums import (
    ...     BranchMergeProposalStatus,
    ...     BranchSubscriptionNotificationLevel,
    ...     CodeReviewNotificationLevel,
    ... )
    >>> from lp.code.interfaces.branchlookup import IBranchLookup
    >>> from lp.code.tests.helpers import (
    ...     make_merge_proposal_without_reviewers,
    ... )
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> subscriber = getUtility(IPersonSet).getByEmail(
    ...     "foo.bar@canonical.com"
    ... )
    >>> branch = getUtility(IBranchLookup).getByUniqueName(
    ...     "~name12/firefox/main"
    ... )
    >>> _unused = branch.subscribe(
    ...     subscriber,
    ...     BranchSubscriptionNotificationLevel.NOEMAIL,
    ...     None,
    ...     CodeReviewNotificationLevel.FULL,
    ...     subscriber,
    ... )

Also subscribe to gnome-terminal, since Firefox tests are mixed with
Gnome Terminal tests.

    >>> branch = getUtility(IBranchLookup).getByUniqueName(
    ...     "~name12/gnome-terminal/main"
    ... )
    >>> _unused = branch.subscribe(
    ...     subscriber,
    ...     BranchSubscriptionNotificationLevel.NOEMAIL,
    ...     None,
    ...     CodeReviewNotificationLevel.FULL,
    ...     subscriber,
    ... )
    >>> from lp.code.tests.helpers import make_erics_fooix_project
    >>> locals().update(make_erics_fooix_project(factory))
    >>> logout()

Any logged in user can register a merge proposal.  Registering
a merge proposal is done from the source branch, and the link
is `Propose for merging`.


Registering a merge proposal
----------------------------

Logged in users can register a merge proposal.

    >>> nopriv_browser = setupBrowser(auth="Basic no-priv@canonical.com:test")
    >>> nopriv_browser.open(
    ...     "http://code.launchpad.test/~name12/gnome-terminal/klingon"
    ... )
    >>> nopriv_browser.getLink("Propose for merging").click()
    >>> nopriv_browser.getControl(
    ...     name="field.target_branch.target_branch"
    ... ).value = "~name12/gnome-terminal/main"
    >>> nopriv_browser.getControl(name="field.prerequisite_branch").value = (
    ...     "~name12/gnome-terminal/pushed"
    ... )
    >>> print_tag_with_id(nopriv_browser.contents, "field.reviewer")
    <BLANKLINE>

There is a cancel link shown with the buttons.

    >>> cancel = nopriv_browser.getLink("Cancel")
    >>> nopriv_browser.getControl("Propose Merge").click()

Registering the merge proposal takes the user to the new merge proposal.

    >>> klingon_proposal = nopriv_browser.url
    >>> print(klingon_proposal)
    http://code.launchpad.test/~name12/gnome-terminal/klingon/+merge/...

The summary reflects the selected target and prerequisite.

    >>> def print_summary(browser):
    ...     print(
    ...         extract_text(
    ...             find_tag_by_id(browser.contents, "proposal-summary")
    ...         )
    ...     )
    ...
    >>> print_summary(nopriv_browser)
    Status:
    ...
    Proposed branch:
    lp://dev/~name12/gnome-terminal/klingon
    Merge into:
    lp://dev/~name12/gnome-terminal/main
    Prerequisite:
    lp://dev/~name12/gnome-terminal/pushed
    To merge this branch:
    bzr merge lp://dev/~name12/gnome-terminal/klingon
    Related bugs:
    Link a bug report


Editing a commit message
------------------------

Since the plan is to merge a branch into another branch, it makes sense that a
commit message can be set.

    >>> nopriv_browser.getLink(url="edit-commit-message").click()
    >>> nopriv_browser.getControl(name="field.commit_message").value = (
    ...     "Add more <b>mojo</b>"
    ... )
    >>> nopriv_browser.getControl("Update").click()

    >>> print_tag_with_id(nopriv_browser.contents, "edit-commit_message")
    Edit
    Commit message
    Add more &lt;b&gt;mojo&lt;/b&gt;

A commit message can be removed deleting the text when editing.

    >>> nopriv_browser.getLink(url="edit-commit-message").click()
    >>> nopriv_browser.getControl(name="field.commit_message").value = ""
    >>> nopriv_browser.getControl("Update").click()

    >>> print_tag_with_id(nopriv_browser.contents, "commit-message")
    Set commit message
    ...


Deleting merge proposals
------------------------

Merge proposals can be deleted, when either abandoned or created in error.
When a merge proposal is deleted, the user is taken back to the main page
for the source_branch.

    >>> login("foo.bar@canonical.com")
    >>> bmp = factory.makeBranchMergeProposal(registrant=eric)
    >>> bmp_url = canonical_url(bmp)
    >>> branch_url = canonical_url(bmp.source_branch)
    >>> logout()
    >>> eric_browser = setupBrowser(auth="Basic eric@example.com:test")
    >>> eric_browser.open(bmp_url)
    >>> eric_browser.getLink("Delete proposal to merge").click()
    >>> cancel = eric_browser.getLink("Cancel")
    >>> eric_browser.getControl("Delete proposal").click()
    >>> eric_browser.url == branch_url
    True

    >>> sample_browser = setupBrowser(auth="Basic test@canonical.com:test")


Requesting reviews
------------------

Any newly created merge proposal will have the reviewer set if a default
has been defined or the branch owner will be used.
    >>> sample_browser.open(klingon_proposal)
    >>> pending = find_tag_by_id(sample_browser.contents, "code-review-votes")
    >>> print(extract_text(pending))
    Reviewer          Review Type    Date Requested    Status
    Sample Person                    ... ago           Pending [Review]
    Review via email: mp+...@code.launchpad.test
                                                 Request another review

The status of the merge proposal is updated to "Needs review".

    >>> print_summary(sample_browser)
    Status: Needs review
    ...

Additional reviews can be requested.

    >>> sample_browser.getLink("Request another review").click()
    >>> sample_browser.getControl("Reviewer").value = "mark"
    >>> sample_browser.getControl("Request Review").click()

You can even re-request the same person to review, so that a new email is
sent.

    >>> sample_browser.getLink("Request another review").click()
    >>> sample_browser.getControl("Reviewer").value = "name12"
    >>> sample_browser.getControl("Review type").value = "second"
    >>> sample_browser.getControl("Request Review").click()

Only the last request is listed, showing the last review type.

    >>> pending = find_tag_by_id(sample_browser.contents, "code-review-votes")
    >>> print(extract_text(pending))
    Reviewer          Review Type    Date Requested    Status
    Mark Shuttleworth                ... ago           Pending
    Sample Person     second         ... ago           Pending [Review]
    Review via email: mp+...@code.launchpad.test
                                                 Request another review


Reviewing
---------

People not logged in cannot perform reviews.

    >>> anon_browser.open(klingon_proposal)
    >>> link = anon_browser.getLink("[Review]")
    Traceback (most recent call last):
    zope.testbrowser.browser.LinkNotFoundError

People who are logged in can perform reviews.

    >>> nopriv_browser.open(klingon_proposal)
    >>> nopriv_browser.getLink("Add a review or comment").click()
    >>> nopriv_browser.getControl(name="field.comment").value = (
    ...     "Don't like it"
    ... )
    >>> nopriv_browser.getControl(name="field.vote").getControl(
    ...     "Disapprove"
    ... ).click()
    >>> nopriv_browser.getControl("Save Comment").click()
    >>> pending = find_tag_by_id(nopriv_browser.contents, "code-review-votes")
    >>> print(extract_text(pending))
    Reviewer                         Review Type  Date Requested Status
    No Privileges Person (community)                             Disapprove
    ...

People can claim reviews for teams of which they are a member.

    >>> sample_browser.open(klingon_proposal)
    >>> sample_browser.getLink("Request another review").click()
    >>> sample_browser.getControl("Reviewer").value = "hwdb-team"
    >>> sample_browser.getControl("Review type").value = "claimable"
    >>> sample_browser.getControl("Request Review").click()
    >>> pending = find_tag_by_id(sample_browser.contents, "code-review-votes")
    >>> print(extract_text(pending))
    Reviewer                         Review Type  Date Requested Status...
    HWDB Team                        claimable    ... ago        Pending ...
    >>> foobar_browser = setupBrowser(auth="Basic foo.bar@canonical.com:test")
    >>> foobar_browser.open(klingon_proposal)
    >>> foobar_browser.getControl("Claim review").click()
    >>> pending = find_tag_by_id(foobar_browser.contents, "code-review-votes")

After claiming a review, the claimant is listed instead of their team.

    >>> print(extract_text(pending))
    Reviewer                         Review Type  Date Requested Status...
    Foo Bar                          claimable    ... ago        Pending ...

The claimant can reassign the review to someone else.

    >>> foobar_browser.getLink("Reassign").click()
    >>> foobar_browser.getControl("Reviewer").value = "no-priv"
    >>> foobar_browser.getControl("Reassign").click()

If the person already has a review, the user gets an error...

    >>> print_feedback_messages(foobar_browser.contents)
    There is 1 error.
    No Privileges Person (no-priv) has already reviewed this

... if not, the review is reassigned.

    >>> foobar_browser.getControl("Reviewer").value = "hwdb-team"
    >>> foobar_browser.getControl("Reassign").click()

The review is now reassigned to the HWDB team.

    >>> print_tag_with_id(foobar_browser.contents, "code-review-votes")
    Reviewer                         Review Type  Date Requested Status...
    HWDB Team                        claimable    ... ago        Pending ...


Resubmitting proposals
----------------------

If a proposal ends up getting rejected, the proposal can be resubmitted.
Actually you can resubmit a proposal that hasn't been superseded or merged
already, but mostly you resubmit rejected proposals.  When a proposal is
resubmitted, a new proposal is registered with the same source and target
branches but with the state set to work-in-progress.

    >>> login("foo.bar@canonical.com")
    >>> bmp = factory.makeBranchMergeProposal(target_branch=trunk)
    >>> bmp_url = canonical_url(bmp)
    >>> logout()
    >>> eric_browser.open(bmp_url)
    >>> eric_browser.getLink("Resubmit proposal").click()

This takes the user to the resubmission page.

    >>> eric_browser.getControl("Resubmit").click()

The new merge proposal is created as needs review, and there is
a link back to the superseded proposal.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(eric_browser.contents, "superseded-proposal")
    ...     )
    ... )
    This proposal supersedes a proposal from ...

    >>> import re
    >>> eric_browser.getLink(re.compile("proposal from .*")).click()
    >>> print_summary(eric_browser)
    Status: Superseded
    ...

The earlier superseded proposal also has a link back to the
new proposal that supersedes it.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(eric_browser.contents, "superseded-by")
    ...     )
    ... )
    This proposal has been superseded by a proposal from ...
    >>> link = eric_browser.getLink(re.compile("proposal from .*"))
    >>> superseding_url = link.url

The superseded proposal can't be made active because of the duplicate
proposal.  It can only be set to another inactive state like "rejected" or
"merged".

    >>> eric_browser.getLink("Edit status").click()
    >>> def print_options(field):
    ...     for option in field.options:
    ...         print(option)
    ...
    >>> print_options(eric_browser.getControl(name="field.queue_status"))
    REJECTED
    MERGED

If we make the superseding proposal inactive, we can set the original back to
work-in-progress.

    >>> eric_browser.open(superseding_url)
    >>> eric_browser.getLink("Edit status").click()
    >>> eric_browser.getControl(name="field.queue_status").displayValue = [
    ...     "Merged"
    ... ]
    >>> eric_browser.getControl("Change Status").click()
    >>> print_summary(eric_browser)
    Status: Merged
    ...
    >>> eric_browser.open(bmp_url)
    >>> print_summary(eric_browser)
    Status: Superseded
    ...
    >>> eric_browser.getLink("Edit status").click()
    >>> print_options(eric_browser.getControl(name="field.queue_status"))
    WORK_IN_PROGRESS
    NEEDS_REVIEW
    CODE_APPROVED
    REJECTED
    MERGED

Merged proposals can be reset to other values, because they may have been
marked merged by mistake, in the UI.

    >>> eric_browser.getControl(name="field.queue_status").displayValue = [
    ...     "Merged"
    ... ]
    >>> eric_browser.getControl("Change Status").click()
    >>> print_summary(eric_browser)
    Status: Merged
    ...
    >>> eric_browser.getLink("Edit status").click()
    >>> print_options(eric_browser.getControl(name="field.queue_status"))
    WORK_IN_PROGRESS
    NEEDS_REVIEW
    CODE_APPROVED
    REJECTED
    MERGED


Default target branches
-----------------------

Almost all of the proposals to merge branches will be created
on feature branches where the target branch is the development
focus branch.  With that in mind, we want the default option
(when proposing a new branch to land) to target the development
focus branch.

If there is no development focus branch, then just the normal
branch widget is shown.

    # A helpful function to determine target branch widgets.
    >>> import re
    >>> def get_target_branch_widgets(browser):
    ...     main = find_main_content(browser.contents)
    ...     return main.find_all(
    ...         "input", attrs={"name": re.compile("target_branch")}
    ...     )
    ...

    >>> nopriv_browser.open(
    ...     "http://code.launchpad.test/~mark/firefox/release-0.8"
    ... )
    >>> nopriv_browser.getLink("Propose for merging").click()
    >>> for widget in get_target_branch_widgets(nopriv_browser):
    ...     print(widget)
    ...
    <input ... type="text" ...

Test validation of errors...

The target branch is a required field, so attempting to register without
setting it gives an appropriate error.

    >>> nopriv_browser.getControl("Propose Merge").click()
    >>> print_feedback_messages(nopriv_browser.contents)
    There is 1 error.
    Required input is missing.

Invalid errors are also shown.

    >>> nopriv_browser.getControl(
    ...     name="field.target_branch.target_branch"
    ... ).value = "fooix"
    >>> nopriv_browser.getControl("Propose Merge").click()
    >>> print_feedback_messages(nopriv_browser.contents)
    There is 1 error.
    Invalid value


When a branch is set as the development focus, then a radio button
is shown.

    >>> admin_browser.open("http://launchpad.test/firefox/trunk")
    >>> admin_browser.getLink("Link to branch").click()
    >>> admin_browser.getControl(name="field.branch_location").value = (
    ...     "~name12/firefox/main"
    ... )
    >>> admin_browser.getControl("Update").click()

    # Just show the radio buttons for the branch widgets.
    >>> def print_radio_options(browser):
    ...     widgets = get_target_branch_widgets(browser)
    ...     for widget in widgets:
    ...         if widget["type"] == "radio":
    ...             try:
    ...                 checked = widget["checked"]
    ...             except KeyError:
    ...                 checked = ""
    ...             print(widget["value"], checked)
    ...

Also the main development focus is selected.

    >>> nopriv_browser.open(
    ...     "http://code.launchpad.test/~mark/firefox/release-0.8"
    ... )
    >>> nopriv_browser.getLink("Propose for merging").click()
    >>> print_radio_options(nopriv_browser)
    ~name12/firefox/main checked
    other

If the user has also targeted a branch other than the development
focus before, then that is also shown as a radio option.

    >>> nopriv_browser.getControl("Other").click()
    >>> nopriv_browser.getControl(
    ...     name="field.target_branch.target_branch"
    ... ).value = "~mark/firefox/release-0.9"
    >>> nopriv_browser.getControl("Propose Merge").click()

    >>> nopriv_browser.open(
    ...     "http://code.launchpad.test/~mark/firefox/release-0.9.2"
    ... )
    >>> nopriv_browser.getLink("Propose for merging").click()
    >>> print_radio_options(nopriv_browser)
    ~name12/firefox/main checked
    ~mark/firefox/release-0.9
    other


Merge Proposal Bug and Spec Links
---------------------------------

A branch merge proposal should show the bugs fixed and/or specs implemented
in the source branch.

    >>> def print_bugs_and_specs(browser):
    ...     for id in "related-bugs", "related-blueprints":
    ...         links = find_tag_by_id(browser.contents, id)
    ...         if links == None:
    ...             print(links)
    ...         else:
    ...             print(extract_text(links))
    ...

    >>> login("admin@canonical.com")
    >>> bmp = factory.makeBranchMergeProposal()
    >>> bmp_url = canonical_url(bmp)
    >>> logout()

If there are no related bugs, the corresponding section should only show a
"Link to bug report" link; if there are no related blueprints, there should
be no corresponding section.

    >>> nopriv_browser.open(bmp_url)
    >>> print_bugs_and_specs(nopriv_browser)
    Related bugs: Link a bug report
    None

    >>> login("admin@canonical.com")
    >>> bug = factory.makeBug(title="Bug for linking")
    >>> link = bmp.source_branch.linkBug(bug, bmp.source_branch.owner)
    >>> logout()

The section is shown if there are links.

    >>> nopriv_browser.open(bmp_url)
    >>> print_bugs_and_specs(nopriv_browser)
    Related bugs: Bug #...: Bug for linking Undecided New Link a bug report
    None


Target branch edge cases
------------------------

When the development focus branch is proposed for merging,
don't suggest that we merge it onto itself.

    >>> nopriv_browser.open("http://code.launchpad.test/~name12/firefox/main")
    >>> nopriv_browser.getLink("Propose for merging").click()
    >>> print_radio_options(nopriv_browser)
    ~mark/firefox/release-0.9 checked
    other

If we are looking to propose a branch that has been targeted before,
we don't show that branch as a possible target (as it is the source
branch).

    >>> nopriv_browser.open(
    ...     "http://code.launchpad.test/~mark/firefox/release-0.9"
    ... )
    >>> nopriv_browser.getLink("Propose for merging").click()
    >>> print_radio_options(nopriv_browser)
    ~name12/firefox/main checked
    other


Registering a merge, and junk branches
--------------------------------------

Junk branches cannot be proposed for merging.  The action option is not
shown for junk branches.

    >>> nopriv_browser.open("http://code.launchpad.test/~mark/+junk/testdoc")
    >>> nopriv_browser.getLink("Propose for merging").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

Even if the user hand crafts the URL to look like a proposal to merge,
they'll get a 404.

    >>> nopriv_browser.open(
    ...     "http://code.launchpad.test/~mark/+junk/testdoc/+register-merge"
    ... )
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...


Displaying a preview diff
-------------------------

Create merge proposal with a preview diff, and go to its index page.

    >>> login("admin@canonical.com")
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from difflib import unified_diff
    >>> from lp.code.model.diff import PreviewDiff
    >>> diff_text = "".join(unified_diff("", ["Fake Diff\u1010"]))
    >>> bmp = factory.makeBranchMergeProposal()
    >>> preview_diff = PreviewDiff.create(bmp, diff_text, "a", "b", None, "")
    >>> transaction.commit()
    >>> url = canonical_url(bmp)
    >>> logout()
    >>> def get_review_diff():
    ...     nopriv_browser.open(url)
    ...     return find_tag_by_id(nopriv_browser.contents, "review-diff")
    ...

The text of the review diff is in the page.

    >>> print(backslashreplace(extract_text(get_review_diff())))
    Preview Diff
    [H/L] Next/Prev Comment, [J/K] Next/Prev File, [N/P] Next/Prev Hunk
    Download diff
    Side-by-side diff
    1
    ---
    2
    +++
    3
    @@ -0,0 +1 @@
    4
    +Fake Diff\u1010

There is also a link to the diff URL, which is the preview diff URL plus
"+files/preview.diff". It redirects logged in users to the file in the
restricted librarian.

    >>> link = get_review_diff().find("a")
    >>> print(extract_text(link))
    Download diff

    >>> print(link["href"])
    http://.../+preview-diff/.../+files/preview.diff

    >>> from lazr.uri import URI
    >>> print(
    ...     http(
    ...         r"""
    ... GET %s HTTP/1.1
    ... Authorization: Basic no-priv@canonical.com:test
    ... """
    ...         % URI(link["href"]).path
    ...     )
    ... )
    HTTP/1.1 303 See Other
    ...
    Location: https://...restricted.../...txt?token=...
    ...

If no diff is present, nothing is shown.

    >>> from storm.store import Store
    >>> Store.of(preview_diff).remove(preview_diff)
    >>> from lp.services.propertycache import get_property_cache
    >>> del get_property_cache(bmp).preview_diffs
    >>> print(get_review_diff())
    None

If the review diff is empty, then we say it is empty.

    >>> login("admin@canonical.com")
    >>> preview_diff = PreviewDiff.create(bmp, b"", "c", "d", None, "")
    >>> logout()
    >>> print(extract_text(get_review_diff()))
    Preview Diff
    Empty


Preview diff generation status
------------------------------

    >>> update = find_tag_by_id(
    ...     nopriv_browser.contents, "diff-pending-update"
    ... )
    >>> print(extract_text(update))
    Updating diff...
    An updated diff will be available in a few minutes.  Reload to see the
    changes.
    >>> job = removeSecurityProxy(bmp).next_preview_diff_job
    >>> job.start()
    >>> job.complete()
    >>> transaction.commit()
    >>> nopriv_browser.open(url)
    >>> print(find_tag_by_id(nopriv_browser.contents, "diff-pending-update"))
    None


Merge proposal details shown on the branch page
-----------------------------------------------

A branch that has a merge proposal, but no requested reviews shows this on the
branch page. We create a proposal using the factory since we want to force
one without a reviewer.

    >>> login("foo.bar@canonical.com")
    >>> source_branch = getUtility(IBranchLookup).getByUniqueName(
    ...     "~fred/fooix/feature"
    ... )
    >>> fooix = getUtility(IProductSet).getByName("fooix")
    >>> bmp = make_merge_proposal_without_reviewers(
    ...     factory,
    ...     registrant=eric,
    ...     source=source_branch,
    ...     target=fooix.development_focus.branch,
    ...     set_state=BranchMergeProposalStatus.NEEDS_REVIEW,
    ... )
    >>> bmp_url = canonical_url(bmp)
    >>> branch_url = canonical_url(bmp.source_branch)
    >>> logout()
    >>> nopriv_browser.open(branch_url)
    >>> print_tag_with_id(nopriv_browser.contents, "landing-targets")
    Ready for review for merging into lp://dev/fooix
      No reviews requested

If there are reviews either pending or completed these are also shown.

The api tag is a hidden anchor that holds the URL for the merge proposal api
access.

    >>> nopriv_browser.open("http://code.launchpad.test/~fred/fooix/proposed")
    >>> print_tag_with_id(nopriv_browser.contents, "landing-targets")
    Ready for review for merging into lp://dev/fooix
      Eric the Viking: Pending (code) requested ... ago
      Diff: 47 lines (+7/-13) 2 files modified
      file1 (+3/-8)
      file2 (+4/-5)
      api


Merge proposal details shown on the bug page
--------------------------------------------

If a branch with a merge proposal is linked to a bug, the merge proposal
details are shown on the bug page under the branch link.

    >>> login("admin@canonical.com")
    >>> bug = factory.makeBug(target=fooix)
    >>> ignored = bug.linkBranch(proposed, fred)
    >>> bug_url = canonical_url(bug)
    >>> logout()

    >>> nopriv_browser.open(bug_url)
    >>> print_tag_with_id(nopriv_browser.contents, "bug-branches")
    Related branches
    lp://dev/~fred/fooix/proposed
      Ready for review for merging into lp://dev/fooix
        Eric the Viking: Pending (code) requested ... ago
        Diff: 47 lines (+7/-13) 2 files modified
        file1 (+3/-8)
        file2 (+4/-5)
	api
