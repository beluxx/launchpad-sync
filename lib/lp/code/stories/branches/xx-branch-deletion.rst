Deleting branches
=================

Branches that have no revisions or links to other Launchpad objects
can be deleted.  The main use for this is to allow users to delete
branches that have been created in error.

    >>> from lp.code.enums import BranchType
    >>> login(ANONYMOUS)
    >>> alice = factory.makePerson(name="alice", email="alice@example.com")
    >>> product = factory.makeProduct(
    ...     name='earthlynx', displayname="Earth Lynx", owner=alice)
    >>> branch = factory.makeProductBranch(
    ...     product=product, branch_type=BranchType.HOSTED)
    >>> productseries = factory.makeProductSeries(
    ...     product=product, branch=branch)
    >>> ignored = login_person(alice)
    >>> product.development_focus = productseries
    >>> delete_branch = factory.makeProductBranch(
    ...     name='to-delete', owner=alice,
    ...     product=product, branch_type=BranchType.HOSTED)
    >>> logout()

    >>> browser = setupBrowser(auth="Basic alice@example.com:test")
    >>> browser.open('http://code.launchpad.test/~alice/earthlynx/to-delete')
    >>> print(browser.title)
    to-delete : Code : Earth Lynx

The newly created branch has an action 'Delete branch'.

    >>> delete_link = browser.getLink('Delete branch')
    >>> print(delete_link.url)
    http://code.launchpad.test/~alice/earthlynx/to-delete/+delete

When the user clicks on the link, they are informed what will happen if they
delete the branch.

    >>> delete_link.click()
    >>> print(extract_text(find_main_content(browser.contents)))
    Delete branch lp://dev/~alice/earthlynx/to-delete
    to-delete ...
    Branch deletion is permanent.
    or Cancel

Once the branch has been deleted, the user is taken back to the code
listing for deleted branch's product, and a message is shown saying that
the branch has been deleted.

    >>> browser.getControl('Delete').click()
    >>> print(browser.url)
    http://code.launchpad.test/earthlynx
    >>> print_feedback_messages(browser.contents)
    Branch ~alice/earthlynx/to-delete deleted...

If the branch is junk, then the user is taken back to the code listing for
the deleted branch's owner.

    >>> ignored = login_person(alice)
    >>> delete_branch = factory.makePersonalBranch(
    ...     name='to-delete', owner=alice)
    >>> logout()
    >>> browser.open('http://code.launchpad.test/~alice/+junk/to-delete')
    >>> browser.getLink('Delete branch').click()
    >>> browser.getControl('Delete').click()
    >>> print(browser.url)
    http://code.launchpad.test/~alice
    >>> print_feedback_messages(browser.contents)
    Branch ~alice/+junk/to-delete deleted...

Branches that are stacked upon cannot be deleted.

    >>> from lp.testing.sampledata import ADMIN_EMAIL
    >>> login(ADMIN_EMAIL)
    >>> stacked_upon = factory.makeAnyBranch()
    >>> stacked = factory.makeAnyBranch(stacked_on=stacked_upon)
    >>> branch_location = canonical_url(stacked_upon)
    >>> logout()

Even if you are an admin.

    >>> admin_browser.open(branch_location)
    >>> admin_browser.getLink('Delete branch').click()
    >>> print(extract_text(find_main_content(admin_browser.contents)))
    Delete branch...
    This branch cannot be deleted as it has 1 branch sharing revisions.

However, you can delete a branch that's the official branch of a source
package, when you also have the permission to set the official package branch.

    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> login(ADMIN_EMAIL)
    >>> branch = factory.makePackageBranch(owner=alice)
    >>> package = branch.sourcepackage
    >>> package.setBranch(PackagePublishingPocket.RELEASE, branch, alice)
    >>> branch_url = canonical_url(branch)

    # Give Alice permission to change the official branch.
    >>> archive = package.get_default_archive()
    >>> archive.newPackageUploader(alice, package.name)
    <...>
    >>> logout()

    >>> browser.open(branch_url)
    >>> browser.getLink('Delete branch').click()
    >>> browser.getControl('Delete').click()
    >>> print_feedback_messages(browser.contents)
    Branch ... deleted...
