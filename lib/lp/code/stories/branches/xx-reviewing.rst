Reviewing a merge proposal
==========================

A frequent use case is when a team is asked to review, and a member of that
team review the proposal on behalf of the team.

    >>> login(ANONYMOUS)
    >>> eric = factory.makePerson(name='eric', email='eric@example.com')
    >>> vikings = factory.makeTeam(owner=eric, name='vikings')
    >>> from lp.code.tests.helpers import (
    ...     make_merge_proposal_without_reviewers)
    >>> bmp = make_merge_proposal_without_reviewers(factory)
    >>> ignored = login_person(bmp.registrant)
    >>> ignored = bmp.nominateReviewer(vikings, bmp.registrant)
    >>> url = canonical_url(bmp)
    >>> logout()

When the user looks at the merge proposal page, they see their team name in
the reviewer block with the link '[Review]'.

    >>> browser = setupBrowser(auth='Basic eric@example.com:test')
    >>> browser.open(url)
    >>> print_tag_with_id(browser.contents, 'code-review-votes')
    Reviewer    Review Type    Date Requested   Status
    Vikings                    ... ago          Pending   [Review]
    Review via email:   mp...@code.launchpad.test

    >>> browser.getLink('[Review]').click()

The user can then add their comment.

    >>> browser.getControl('Comment').value = 'Looks good'
    >>> browser.getControl('Save Review').click()

The team review is now claimed by the user.

    >>> print_tag_with_id(browser.contents, 'code-review-votes')
    Reviewer    Review Type    Date Requested   Status
    Eric (community)           ... ago          Approve ... ago
    Review via email:   mp...@code.launchpad.test
