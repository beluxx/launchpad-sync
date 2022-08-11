==================
Upgrading Branches
==================

Launchpad can upgrade branches that were in an older format to a more up to
date format.


Creating the branch
===================

Branches are not available to be upgraded if they are in a more up to date
format.

    >>> from lp.code.bzr import BranchFormat, RepositoryFormat
    >>> login('foo.bar@canonical.com')
    >>> domino = factory.makePerson(name='domino', email="fats@domino.com")
    >>> twist = factory.makeAnyBranch(
    ...     branch_format=BranchFormat.BZR_BRANCH_6,
    ...     repository_format=RepositoryFormat.BZR_CHK_2A,
    ...     owner=domino)
    >>> branch_url = canonical_url(twist)
    >>> logout()


Requesting an upgrade
=====================

Only those with edit permissions on a branch can request an upgrade.

    >>> nopriv_browser = setupBrowser(
    ...     auth='Basic nopriv@canonical.com:test')
    >>> nopriv_browser.open(branch_url)
    >>> link = nopriv_browser.getLink('Upgrade this branch')
    Traceback (most recent call last):
    zope.testbrowser.browser.LinkNotFoundError

    >>> domino_browser = setupBrowser(
    ...     auth='Basic fats@domino.com:test')
    >>> domino_browser.open(branch_url)
    >>> domino_browser.getLink("Upgrade this branch").click()
    >>> print(domino_browser.url)
    http://code.launchpad.test/~domino/.../+upgrade
    >>> domino_browser.getControl('Upgrade').click()

    >>> print_feedback_messages(domino_browser.contents)
    An upgrade of this branch is in progress.
