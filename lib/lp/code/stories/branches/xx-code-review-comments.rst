Code Review Comments
====================

Set up required objects.  We need to be admin to add a landing target to a
random branch.

    >>> login("foo.bar@canonical.com")
    >>> eric = factory.makePerson(
    ...     name="eric",
    ...     email="eric@example.com",
    ...     displayname="Eric the Viking",
    ... )
    >>> merge_proposal = factory.makeBranchMergeProposal(reviewer=eric)
    >>> merge_proposal_url = canonical_url(merge_proposal)
    >>> merge_proposal_path = canonical_url(
    ...     merge_proposal, force_local_path=True
    ... )
    >>> logout()

    >>> eric_browser = setupBrowser(auth="Basic eric@example.com:test")
    >>> eric_browser.open(merge_proposal_url)
    >>> eric_browser.getLink("Add a review or comment").click()
    >>> eric_browser.getControl(name="field.comment").value = (
    ...     "This is a "
    ...     "very long comment about what things should be done to the source "
    ...     "branch to land it.  When this comment is replied to, it "
    ...     "should wrap the line properly."
    ... )
    >>> eric_browser.getControl(name="field.actions.add").click()
    >>> eric_browser.url == merge_proposal_url
    True

Adding a comment or review to a merge proposal will take the user back
to the main merge proposal page.

    >>> anon_browser.open(merge_proposal_url)
    >>> def print_comments(klass, browser=None, index=0):
    ...     if browser is None:
    ...         browser = anon_browser
    ...     tags = find_tags_by_class(browser.contents, klass)
    ...     for count, tag in enumerate(tags):
    ...         if count == index:
    ...             print(extract_text(tag))
    ...

    >>> print_comments("boardCommentDetails")
    Revision history for this message
    Eric the Viking (eric) wrote ...
    >>> print_comments("comment-text")
    This is a very long comment about what things should be done to the
    source branch to land it. When this comment is replied to, it should
    wrap the line properly.
    >>> print_comments("boardCommentFooter")
    Reply

The person's name links back to the main site for that person.

    >>> print(anon_browser.getLink("Eric the Viking").url)
    http://launchpad.test/~eric

Reply link is displayed even if the user isn't logged in.

    >>> anon_browser.getLink("Reply").click()
    Traceback (most recent call last):
    zope.security.interfaces.Unauthorized: ...

We can reply to a comment.

    >>> eric_browser.open(merge_proposal_url)
    >>> eric_browser.getLink("Reply").click()


XXX: Bjorn Tillenius 2010-05-19 bug=582842: Following test disabled,
since it failed spuriously in buildbot.

#    >>> print(eric_browser.getControl(name='field.comment').value.replace(
#    ...     '\r\n', '\n'))
#    This is a very long comment about what things should be done to the
#    source branch to land it.  When this comment is replied to, it should
#    wrap the line properly.

    >>> eric_browser.getControl(name="field.comment").value = (
    ...     "I like this.\n"
    ...     "I wish I had time to review it properly\n\n"
    ...     "This is a longer\nmessage with several\nlines\n"
    ...     "Email me at eric@vikings-r-us.example.com for more details"
    ... )
    >>> eric_browser.getControl(name="field.actions.add").click()

After this, we are taken to the main page for the merge proposal

    >>> print_comments("comment-text", eric_browser, index=1)
    I like this.
    I wish I had time to review it properly
    This is a longer message with several lines
    Email me at eric@vikings-r-us.example.com for more details

Email addresses in code review comments are hidden for users not logged in.

    >>> anon_browser.open(merge_proposal_url)
    >>> print_comments("comment-text", anon_browser, index=1)
    I like this.
    I wish I had time to review it properly
    This is a longer message with several lines
    Email me at &lt;email address hidden&gt; for more details

If a merge proposal is resubmitted, the comments on the superseded proposal
are also displayed in the new proposal.

    >>> login("foo.bar@canonical.com")
    >>> new_merge_proposal = merge_proposal.resubmit(
    ...     merge_proposal.registrant
    ... )
    >>> new_merge_proposal_url = canonical_url(new_merge_proposal)
    >>> logout()
    >>> anon_browser.open(new_merge_proposal_url)
    >>> print_comments("comment-text", anon_browser, index=0)
    This is a very long comment about what things should be done to the
    source branch to land it. When this comment is replied to, it should
    wrap the line properly.
    >>> print_comments("boardCommentDetails", anon_browser, index=0)
    Revision history for this message
    Eric the Viking (eric) wrote ... ago:
    Posted in a previous version of this proposal #
    >>> details = find_tags_by_class(
    ...     anon_browser.contents, "boardCommentDetails"
    ... )[0]
    >>> links = details.find_all("a")
    >>> print(links[1]["href"] == merge_proposal_path)
    True


Reviewing
---------

If the user wants to review the branch, they click on the 'Add a review or
comment' link.

    >>> eric_browser.getLink("Add a review or comment").click()
    >>> eric_browser.getControl(name="field.vote").displayValue = ["Abstain"]
    >>> eric_browser.getControl("Review type").value = "timeless"
    >>> eric_browser.getControl("Save Comment").click()

    >>> print_comments("boardCommentDetails", eric_browser, index=2)
    Revision history for this message
    Eric the Viking ... ago: #
    >>> print_comments("boardCommentActivity", eric_browser, index=0)
    review: Abstain (timeless)
    >>> print_comments("boardCommentBody", eric_browser, index=2)


Vote summaries
--------------

The summary of the votes that have been made for a code review are shown
in a table at the top of the page.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(eric_browser.contents, "code-review-votes")
    ...     )
    ... )
    Reviewer                     Review Type    Date Requested    Status
    Eric the Viking (community)  timeless       ...               Abstain...
    a moment ago
    Review via email: mp+...@code.launchpad.test


Commits shown in the conversation
---------------------------------

If the source branch is updated during the review process, the commits are
shown as part of the conversation at the time they were pushed to Launchpad.

    >>> login("admin@canonical.com")
    >>> from lp.code.tests.helpers import add_revision_to_branch
    >>> bmp = factory.makeBranchMergeProposal()
    >>> from datetime import datetime, timedelta
    >>> import pytz
    >>> review_date = datetime(2009, 9, 10, tzinfo=pytz.UTC)
    >>> bmp.requestReview(review_date)
    >>> revision_date = review_date + timedelta(days=1)
    >>> for date in range(2):
    ...     ignored = add_revision_to_branch(
    ...         factory,
    ...         bmp.source_branch,
    ...         revision_date,
    ...         commit_msg="Testing commits in conversation",
    ...     )
    ...     ignored = add_revision_to_branch(
    ...         factory,
    ...         bmp.source_branch,
    ...         revision_date,
    ...         commit_msg="and it works!",
    ...     )
    ...     revision_date += timedelta(days=1)
    ...
    >>> url = canonical_url(bmp)
    >>> logout()

    >>> browser.open(url)
    >>> print_tag_with_id(browser.contents, "conversation")
    lp://dev/... updated on 2009-09-12 ...
    1. By ... on 2009-09-11
    Testing commits in conversation
    2. By ... on 2009-09-11
    and it works!
    3. By ... on 2009-09-12
    Testing commits in conversation
    4. By ... on 2009-09-12
    and it works!

The same thing works for Git.  Note that the hosting client returns newest
log entries first.

    >>> from lp.code.tests.helpers import GitHostingFixture
    >>> from lp.services.utils import seconds_since_epoch

    >>> login("admin@canonical.com")
    >>> bmp = factory.makeBranchMergeProposalForGit()
    >>> bmp.requestReview(review_date)
    >>> commit_date = review_date + timedelta(days=1)
    >>> hosting_fixture = GitHostingFixture()
    >>> for i in range(2):
    ...     hosting_fixture.getLog.result.insert(
    ...         0,
    ...         {
    ...             "sha1": str(i * 2) * 40,
    ...             "message": "Testing commits in conversation",
    ...             "author": {
    ...                 "name": bmp.registrant.display_name,
    ...                 "email": bmp.registrant.preferredemail.email,
    ...                 "time": int(seconds_since_epoch(commit_date)),
    ...             },
    ...         },
    ...     )
    ...     hosting_fixture.getLog.result.insert(
    ...         0,
    ...         {
    ...             "sha1": str(i * 2 + 1) * 40,
    ...             "message": "and it works!",
    ...             "author": {
    ...                 "name": bmp.registrant.display_name,
    ...                 "email": bmp.registrant.preferredemail.email,
    ...                 "time": int(seconds_since_epoch(commit_date)),
    ...             },
    ...         },
    ...     )
    ...     commit_date += timedelta(days=1)
    ...
    >>> url = canonical_url(bmp)
    >>> logout()

    >>> with hosting_fixture:
    ...     browser.open(url)
    ...
    >>> print_tag_with_id(browser.contents, "conversation")
    ~.../+git/...:... updated on 2009-09-12 ...
    0000000... by ... on 2009-09-11
    Testing commits in conversation
    1111111... by ... on 2009-09-11
    and it works!
    2222222... by ... on 2009-09-12
    Testing commits in conversation
    3333333... by ... on 2009-09-12
    and it works!


Inline Comments
---------------

The code review inline comments support is entirely implemented in
Javascript. The current implementation relies on comments being
rendered with the following 'data-' attributes:

    # Created a new review comment with associated inline comments
    # on the superseded and on the new MP.
    >>> login("foo.bar@canonical.com")
    >>> previewdiff = factory.makePreviewDiff(merge_proposal=merge_proposal)
    >>> new_previewdiff = factory.makePreviewDiff(
    ...     merge_proposal=new_merge_proposal
    ... )
    >>> transaction.commit()
    >>> comment1 = merge_proposal.createComment(
    ...     eric,
    ...     None,
    ...     content="a_content",
    ...     previewdiff_id=previewdiff.id,
    ...     inline_comments={"1": "No!"},
    ... )
    >>> comment2 = new_merge_proposal.createComment(
    ...     eric,
    ...     None,
    ...     content="a_content",
    ...     previewdiff_id=new_previewdiff.id,
    ...     inline_comments={"1": "Yes!"},
    ... )
    >>> transaction.commit()
    >>> previewdiff_id = previewdiff.id
    >>> new_previewdiff_id = new_previewdiff.id
    >>> logout()

    >>> def get_comment_attributes(contents):
    ...     result = {}
    ...     comments = find_tags_by_class(contents, "boardCommentDetails")
    ...     for comment in comments:
    ...         tds = comment.find_all("td")
    ...         if len(tds) == 0:
    ...             continue
    ...         td = tds[0]
    ...         if td.get("data-previewdiff-id"):
    ...             result[td["data-previewdiff-id"]] = td.get(
    ...                 "data-from-superseded", "-"
    ...             )
    ...     return result
    ...

The 'data-' attributes:

 * 'previewdiff-id': used to load the corresponding `PreviewDiff`.
 * 'from_superseded': 'True' or 'False' whether the context MP is
                      superseded by another. Used to suppress context
                      handlers on superseded comments.

They are always available in `BranchMergeProposal` pages.

    >>> anon_browser.open(merge_proposal_url)
    >>> comments = get_comment_attributes(anon_browser.contents)
    >>> comments[str(previewdiff_id)] == "False"
    True
    >>> str(new_previewdiff_id) in comments
    False

When visualized in the new merge proposal the comments from the original
merge proposal are marked as 'superseded' and there is a new and
non-superseded local comment.

    >>> anon_browser.open(new_merge_proposal_url)
    >>> comments = get_comment_attributes(anon_browser.contents)
    >>> comments[str(previewdiff_id)] == "True"
    True
    >>> comments[str(new_previewdiff_id)] == "False"
    True
