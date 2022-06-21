Setting the branch for a product series
=======================================

A product series should have a branch set for it.  The branch can be
hosted on Launchpad or somewhere else.  Foreign branches can be in
Bazaar, Git, Subversion, or CVS.  Though internally Launchpad treats those
scenarios differently we provide a single page to the user to set up the
branch.

At present, the unified page for setting up the branch is not linked
from anywhere, so it must be navigated to directly.

    >>> browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> browser.open('http://launchpad.test/firefox/trunk/+setbranch')

The default choice for the type of branch to set is one that
already exists on Launchpad.

    >>> print_radio_button_field(browser.contents, 'branch_type')
    (*) Link to a Bazaar branch already on Launchpad
    ( ) Import a branch hosted somewhere else


Linking to an existing branch
-----------------------------

A user can choose to link to an existing branch on Launchpad.

    >>> login('test@canonical.com')
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.product import IProductSet
    >>> productset = getUtility(IProductSet)
    >>> firefox = productset.getByName('firefox')
    >>> branch = factory.makeBranch(
    ...     name="firefox-hosted-branch", product=firefox)
    >>> branch_name = branch.unique_name
    >>> logout()

    >>> browser.getControl(name='field.branch_location').value = branch_name
    >>> browser.getControl('Update').click()
    >>> print_feedback_messages(browser.contents)
    Series code location updated.
    >>> print(browser.url)
    http://launchpad.test/firefox/trunk


Linking to an external branch
-----------------------------

An external branch can be linked.  The branch can be a Bazaar branch
or be a Git, Subversion, or CVS branch.

Each of these types must provide the URL of the external repository,
the branch name to use in Launchpad, and the branch owner.

    >>> browser.open('http://launchpad.test/firefox/trunk/+setbranch')
    >>> browser.getControl('Import a branch hosted somewhere else').click()
    >>> browser.getControl('Branch name').value = 'bzr-firefox-branch'
    >>> browser.getControl(name='field.rcs_type').value = ['BZR']
    >>> browser.getControl('Branch URL').value = (
    ...     'https://bzr.example.com/branch')
    >>> browser.getControl('Update').click()
    >>> print_feedback_messages(browser.contents)
    Code import created and branch linked to the series.
    >>> print(browser.url)
    http://launchpad.test/firefox/trunk

The process is the same for a Git external branch, though the novel
"git://" scheme can also be used.

    >>> browser.open('http://launchpad.test/firefox/trunk/+setbranch')
    >>> browser.getControl('Import a branch hosted somewhere else').click()
    >>> browser.getControl('Branch name').value = 'git-firefox-branch'
    >>> browser.getControl(name='field.rcs_type').value = ['GIT']
    >>> browser.getControl('Branch URL').value = (
    ...     'git://git.example.com/branch')
    >>> browser.getControl('Update').click()
    >>> print_feedback_messages(browser.contents)
    Code import created and branch linked to the series.
    >>> print(browser.url)
    http://launchpad.test/firefox/trunk

Likewise Subversion can use the "svn://" scheme.

    >>> browser.open('http://launchpad.test/firefox/trunk/+setbranch')
    >>> browser.getControl('Import a branch hosted somewhere else').click()
    >>> browser.getControl('Branch name').value = 'svn-firefox-branch'
    >>> browser.getControl(name='field.rcs_type').value = ['BZR_SVN']
    >>> browser.getControl('Branch URL').value = (
    ...     'svn://svn.example.com/branch')
    >>> browser.getControl('Update').click()
    >>> print_feedback_messages(browser.contents)
    Code import created and branch linked to the series.
    >>> print(browser.url)
    http://launchpad.test/firefox/trunk

The branch owner can be the logged in user or one of their teams.

    >>> browser.open('http://launchpad.test/firefox/trunk/+setbranch')
    >>> browser.getControl('Import a branch hosted somewhere else').click()
    >>> browser.getControl('Branch name').value = 'git-firefox-branch'
    >>> browser.getControl(name='field.rcs_type').value = ['GIT']
    >>> browser.getControl('Branch URL').value = (
    ...     'http://git.example.com/branch')
    >>> browser.getControl('Branch owner').value = ['hwdb-team']
    >>> browser.getControl('Update').click()
    >>> print_feedback_messages(browser.contents)
    Code import created and branch linked to the series.
    >>> print(browser.url)
    http://launchpad.test/firefox/trunk
    >>> login('test@canonical.com')
    >>> firefox_trunk = firefox.getSeries('trunk')
    >>> print(firefox_trunk.branch.unique_name)
    ~hwdb-team/firefox/git-firefox-branch
    >>> print(firefox_trunk.branch.owner.name)
    hwdb-team
    >>> logout()
