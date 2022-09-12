Email Notifications for Branch Merge Proposals
==============================================

Subscribers to any of the branches involved in the merge proposal get
notifications.


Subscription
------------

When subscribers subscribe to branches, they can specify what level of
notification they would like to receive.

    >>> from lp.code.enums import (
    ...     BranchSubscriptionDiffSize,
    ...     BranchSubscriptionNotificationLevel,
    ...     CodeReviewNotificationLevel,
    ... )
    >>> from lp.code.interfaces.branchmergeproposal import (
    ...     IBranchMergeProposalJobSource,
    ... )
    >>> from lp.code.tests.helpers import (
    ...     make_merge_proposal_without_reviewers,
    ... )
    >>> from lp.services.config import config
    >>> from lp.testing.dbuser import dbuser
    >>> from lp.testing.mail_helpers import pop_notifications
    >>> import transaction
    >>> login("test@canonical.com")
    >>> target_owner = factory.makePerson(email="target_owner@example.com")
    >>> target_branch = factory.makeBranch(owner=target_owner)
    >>> bmp = make_merge_proposal_without_reviewers(
    ...     factory, target=target_branch
    ... )
    >>> previewdiff = factory.makePreviewDiff(merge_proposal=bmp)
    >>> transaction.commit()
    >>> source_subscriber = factory.makePerson(
    ...     email="source@example.com",
    ...     name="source-subscriber",
    ...     displayname="Source Subscriber",
    ... )
    >>> _unused = bmp.source_branch.subscribe(
    ...     source_subscriber,
    ...     BranchSubscriptionNotificationLevel.NOEMAIL,
    ...     BranchSubscriptionDiffSize.NODIFF,
    ...     CodeReviewNotificationLevel.STATUS,
    ...     source_subscriber,
    ... )
    >>> target_subscriber = factory.makePerson(
    ...     email="target@example.com",
    ...     name="target-subscriber",
    ...     displayname="Target Subscriber",
    ... )
    >>> target_subscription = bmp.target_branch.subscribe(
    ...     target_subscriber,
    ...     BranchSubscriptionNotificationLevel.NOEMAIL,
    ...     BranchSubscriptionDiffSize.NODIFF,
    ...     CodeReviewNotificationLevel.FULL,
    ...     target_subscriber,
    ... )

The owners of the branches are subscribed when the branches are created.
We know the target_owner from when the target branch was created above.
    >>> source_owner = bmp.source_branch.owner


Notification Recipients
-----------------------

Recipients are determined using getNotificationRecipients.

    >>> recipients = bmp.getNotificationRecipients(
    ...     CodeReviewNotificationLevel.STATUS
    ... )

Subscribers to all related branches are candidates.

    >>> all_subscribers = set(
    ...     [source_owner, target_owner, source_subscriber, target_subscriber]
    ... )
    >>> all_subscribers == set(recipients.keys())
    True

Only subscribers whose level is >= the minimum level are selected.

    >>> full_subscribers = set(
    ...     [source_owner, target_owner, target_subscriber]
    ... )
    >>> recipients = bmp.getNotificationRecipients(
    ...     CodeReviewNotificationLevel.FULL
    ... )
    >>> full_subscribers == set(recipients.keys())
    True

Now we will unsubscribe the branch owners to simplify the rest of the test.

    >>> bmp.source_branch.unsubscribe(source_owner, source_owner)
    >>> bmp.target_branch.unsubscribe(target_owner, target_owner)
    >>> recipients = bmp.getNotificationRecipients(
    ...     CodeReviewNotificationLevel.FULL
    ... )

The value assigned to the recipient is a utility class to generate useful
values for the email headers and footers.

    >>> [reason] = recipients.values()
    >>> print(reason.mail_header)
    Subscriber
    >>> print(reason.getReason())
    You are subscribed to branch ...


Email
-----

Jobs for notifications are automagically generated when the merge proposal
is created.  When those jobs are run, the email is sent from the registrant.

    >>> source_branch = bmp.source_branch
    >>> factory.makeRevisionsForBranch(source_branch, count=1)
    >>> target_branch = bmp.target_branch

Login to delete the proposal.

    >>> login("admin@canonical.com")
    >>> bmp.deleteProposal()
    >>> notifications = pop_notifications()
    >>> registrant = factory.makePerson(
    ...     displayname="Eric", email="eric@example.com"
    ... )

To avoid needing to access branches, pre-populate diffs.

    >>> bmp = source_branch.addLandingTarget(
    ...     registrant, target_branch, needs_review=True
    ... )
    >>> previewdiff = factory.makePreviewDiff(merge_proposal=bmp)
    >>> transaction.commit()

Fake the update preview diff as done.

    >>> bmp.next_preview_diff_job.start()
    >>> bmp.next_preview_diff_job.complete()
    >>> [job] = list(getUtility(IBranchMergeProposalJobSource).iterReady())
    >>> with dbuser(config.IBranchMergeProposalJobSource.dbuser):
    ...     job.run()
    ...
    >>> notifications = pop_notifications(
    ...     sort_key=lambda n: n.get("X-Envelope-To")
    ... )

An email is sent to subscribers of either branch and the default reviewer.

    >>> for notification in notifications:
    ...     print(notification["X-Envelope-To"])
    ...
    source@example.com
    target@example.com
    target_owner@example.com

    >>> notification = notifications[0]
    >>> print(notification["From"])
    Eric <mp+...@code.launchpad.test>
    >>> print(notification["Subject"])
    [Merge] lp://dev/~person-name... into lp://dev/~person-name...
    >>> print(notification["X-Launchpad-Project"])
    product-name...
    >>> print(notification["X-Launchpad-Branch"])
    ~person-name...
    >>> print(notification["X-Launchpad-Message-Rationale"])
    Subscriber
    >>> print(notification["X-Launchpad-Message-For"])
    source-subscriber
    >>> print(notification.get_payload(decode=True).decode())
    Eric has proposed merging
    lp://dev/~person-name...into lp://dev/~person-name...
    --
    You are subscribed to branch ...


If there is an initial commit message or reviewers then they are also included
in the email.

    >>> bob = factory.makePerson(
    ...     name="bob", displayname="Bob the Builder", email="bob@example.com"
    ... )
    >>> mary = factory.makePerson(
    ...     name="mary", displayname="Mary Jones", email="mary@example.com"
    ... )
    >>> reviewers = ((bob, None), (mary, "ui"))
    >>> from textwrap import dedent
    >>> initial_comment = dedent(
    ...     """\
    ...     This is the initial commit message.
    ...
    ...     It is included in the initial email sent out.
    ...     """
    ... )
    >>> bmp.deleteProposal()
    >>> bmp = source_branch.addLandingTarget(
    ...     registrant,
    ...     target_branch,
    ...     description=initial_comment,
    ...     review_requests=reviewers,
    ...     needs_review=True,
    ... )
    >>> previewdiff = factory.makePreviewDiff(merge_proposal=bmp)
    >>> transaction.commit()

Fake the update preview diff as done.

    >>> bmp.next_preview_diff_job.start()
    >>> bmp.next_preview_diff_job.complete()
    >>> [job] = list(getUtility(IBranchMergeProposalJobSource).iterReady())
    >>> with dbuser(config.IBranchMergeProposalJobSource.dbuser):
    ...     job.run()
    ...
    >>> notifications = pop_notifications(
    ...     sort_key=lambda n: n.get("X-Envelope-To")
    ... )
    >>> for notification in notifications:
    ...     print(
    ...         "%s, %s, %s"
    ...         % (
    ...             notification["X-Envelope-To"],
    ...             notification["X-Launchpad-Message-Rationale"],
    ...             notification["X-Launchpad-Message-For"],
    ...         )
    ...     )
    ...
    bob@example.com, Reviewer, bob
    mary@example.com, Reviewer, mary
    source@example.com, Subscriber, source-subscriber
    target@example.com, Subscriber, target-subscriber
    >>> notification = notifications[0]
    >>> print(notification.get_payload()[0].get_payload(decode=True).decode())
    Eric has proposed merging
    lp://dev/~person-name...into lp://dev/~person-name...
    <BLANKLINE>
    Requested reviews:
        Bob the Builder (bob)
        Mary Jones (mary): ui
    <BLANKLINE>
    For more details, see:
    http://code.launchpad.test/~person-name...
    <BLANKLINE>
    This is the initial commit message.
    <BLANKLINE>
    It is included in the initial email sent out.
    <BLANKLINE>
    --
    ...
