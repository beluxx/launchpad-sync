===========================
Product Edit and Administer
===========================

Page to edit a product - does the page load as the product owner?

    >>> browser = setupBrowser(auth='Basic test@canonical.com:test')
    >>> browser.open('http://launchpad.test/firefox')
    >>> browser.getLink('Change details').click()
    >>> print(browser.url)
    http://launchpad.test/firefox/+edit

    >>> print(browser.title)
    Change Mozilla Firefox's details...

We try to change the project related to that product. First with a
invalid project.

    >>> browser.getControl('Part of', index=0).value = 'asdasfasd'
    >>> browser.getControl(name='field.actions.change').click()
    >>> for message in find_tags_by_class(browser.contents, 'error'):
    ...     print(message.decode_contents())
    There is 1 error.
    <BLANKLINE>
    ...
    <div class="message">Invalid value</div>
    ...

Now we try to edit with a project that exists.

    >>> browser.getControl('Part of', index=0).value = 'gnome'
    >>> browser.getControl(name='field.actions.change').click()
    >>> print(browser.url)
    http://launchpad.test/firefox

Now we test if we edited it successfully.

    >>> print(extract_text(find_tag_by_id(browser.contents, 'partof')))
    Part of: GNOME


Administering Products
======================

But administrators can access the page:

    >>> admin_browser.open('http://launchpad.test/firefox')
    >>> admin_browser.getLink('Administer').click()

    >>> admin_browser.url
    'http://launchpad.test/firefox/+admin'

    >>> print(admin_browser.title)
    Administer Mozilla Firefox...

And in that page they can set aliases to the product.

    >>> admin_browser.getControl('Aliases').value
    ''

    >>> admin_browser.getControl('Aliases').value = 'iceweasel'
    >>> admin_browser.getControl('Change').click()

    >>> admin_browser.getLink('Administer').click()
    >>> admin_browser.getControl('Aliases').value
    'iceweasel'


Renaming Products
=================

First a user adds a product named newproductname.

    >>> user_browser.open('http://launchpad.test/products/+new')
    >>> user_browser.getControl('URL', index=0).value = 'newproductname'
    >>> user_browser.getControl('Name').value = 'dname'
    >>> user_browser.getControl('Summary').value = 'summary'
    >>> user_browser.getControl('Continue').click()

    >>> user_browser.getControl(
    ...     name='field.description').value = 'description'
    >>> user_browser.getControl(name='field.licenses').value = ['GNU_GPL_V2']
    >>> user_browser.getControl(name='field.license_info').value = 'foo'
    >>> user_browser.getControl('Complete Registration').click()
    >>> print(user_browser.url)
    http://launchpad.test/newproductname

Then a product named newproductname2.

    >>> user_browser.open('http://launchpad.test/products/+new')
    >>> user_browser.getControl('URL', index=0).value = 'newproductname2'
    >>> user_browser.getControl('Name').value = 'dname2'
    >>> user_browser.getControl('Summary').value = 'summary2'
    >>> user_browser.getControl('Continue').click()

    >>> user_browser.getControl(name='field.description').value = (
    ...     'description2')
    >>> user_browser.getControl(name='field.licenses').value = ['GNU_GPL_V2']
    >>> user_browser.getControl(name='field.license_info').value = 'foo'
    >>> user_browser.getControl('Complete Registration').click()
    >>> print(user_browser.url)
    http://launchpad.test/newproductname2

Now we try to change newproductname2's name to newproductname.

    >>> admin_browser.open(
    ...     'http://launchpad.test/newproductname2/+admin')
    >>> admin_browser.getControl('Name').value = 'newproductname'
    >>> admin_browser.getControl(name='field.actions.change').click()
    >>> for message in find_tags_by_class(admin_browser.contents, 'error'):
    ...     print(message.decode_contents())
    There is 1 error.
    <BLANKLINE>
    ...
    ...newproductname is already used...
    ...
    <BLANKLINE>

Now we try to change it to newproductname3.  We expect that the change
will be accepted because there is no product called newproductname3

    >>> admin_browser.getControl('Name').value = 'newproductname3'
    >>> admin_browser.getControl(name='field.actions.change').click()
    >>> print(admin_browser.url)
    http://launchpad.test/newproductname3


Changing Maintainer and Registrant
==================================

Administrators can change the owner of a project.

    >>> admin_browser.open(
    ...     'http://launchpad.test/newproductname3')
    >>> print(extract_text(find_tag_by_id(admin_browser.contents, 'owner')))
    Maintainer: No Privileges Person
    ...

    >>> admin_browser.open(
    ...     'http://launchpad.test/newproductname3/+admin')
    >>> admin_browser.getControl('Maintainer').value = 'cprov'
    >>> admin_browser.getControl(name='field.actions.change').click()
    >>> print(extract_text(find_tag_by_id(admin_browser.contents, 'owner')))
    Maintainer: Celso Providelo
    ...

And the registrant can also be changed, even though this should rarely
happen. The registrant is a read-only field that is set when the product
is created but we allow admins to change it to correct data.

    >>> admin_browser.open(
    ...     'http://launchpad.test/newproductname3')
    >>> print(extract_text(
    ...     find_tag_by_id(admin_browser.contents, 'registration')))
    Registered ... by No Privileges Person

    >>> admin_browser.open(
    ...     'http://launchpad.test/newproductname3/+admin')
    >>> admin_browser.getControl('Registrant').value = 'cprov'
    >>> admin_browser.getControl(name='field.actions.change').click()
    >>> print(extract_text(
    ...     find_tag_by_id(admin_browser.contents, 'registration')))
    Registered ... by Celso Providelo

The registrant really should only be a person, not a team, but that
constraint has to be relaxed to account for old data where we do have
teams as registrants.

    >>> admin_browser.open('http://launchpad.test/newproductname3/+admin')
    >>> admin_browser.getControl('Registrant').value = 'registry'
    >>> admin_browser.getControl('Change').click()
    >>> print(extract_text(
    ...     find_tag_by_id(admin_browser.contents, 'registration')))
    Registered ... by Registry Administrators


Registry Experts
================

If we add them to the Registry Experts team:

    >>> admin_browser.open("http://launchpad.test/~registry/+addmember")
    >>> admin_browser.getControl('New member').value = 'no-priv'
    >>> admin_browser.getControl('Add Member').click()

But they can access +admin, though it is more restricted than that for admins.

    >>> from lp.testing import login, logout
    >>> login('admin@canonical.com')
    >>> product = factory.makeProduct(name='trebuche')
    >>> logout()

The registry experts do not have access to the maintainer or
registrant fields.

    >>> browser = setupBrowser(auth="Basic no-priv@canonical.com:test")
    >>> browser.open('http://launchpad.test/trebuche/+admin')
    >>> browser.getControl('Maintainer')
    Traceback (most recent call last):
    ...
    LookupError: label ...'Maintainer'
    ...
    >>> browser.getControl('Registrant')
    Traceback (most recent call last):
    ...
    LookupError: label ...'Registrant'
    ...

But registry experts can change a product name and set an alias.

    >>> browser.getControl('Name').value = 'trebuchet'
    >>> browser.getControl('Aliases').value = 'trebucket'
    >>> browser.getControl('Change').click()

    >>> browser.getLink('Administer').click()
    >>> print(browser.getControl('Name').value)
    trebuchet
    >>> print(browser.getControl('Aliases').value)
    trebucket


Deactivate a product
====================

The Admins and Registry Experts can deactivate a project.

    >>> login('foo.bar@canonical.com')
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> registry_member = factory.makePerson(
    ...     name='reggie', email='reggie@example.com')
    >>> celebs = getUtility(ILaunchpadCelebrities)
    >>> registry = celebs.registry_experts
    >>> ignored = registry.addMember(registry_member, registry.teamowner)
    >>> logout()

    >>> registry_browser = setupBrowser(
    ...     auth='Basic reggie@example.com:test')

    >>> registry_browser.open('http://launchpad.test/bzr/+review-license')
    >>> registry_browser.getControl(name='field.active').value = False
    >>> registry_browser.getControl(name='field.actions.change').click()
    >>> print(registry_browser.url)
    http://launchpad.test/bzr

The product overview page should show a notice that a product is
inactive with a link to a form to re-activate it. Admins and Commercial
Admins can still see the product, but regular users can't.

    >>> registry_browser.open('http://launchpad.test/bzr')
    >>> contents = find_main_content(registry_browser.contents)
    >>> print(extract_text(contents.find(id='project-inactive')))
    This project is currently inactive ...

    >>> admin_browser.open('http://launchpad.test/bzr')
    >>> contents = find_main_content(admin_browser.contents)
    >>> print(extract_text(contents.find(id='project-inactive')))
    This project is currently inactive ...

The product can then be reactivated.

    >>> registry_browser.getLink('Review project').click()
    >>> print(registry_browser.url)
    http://launchpad.test/bzr/+review-license

    >>> registry_browser.getControl(name='field.active').value = True
    >>> registry_browser.getControl(name='field.actions.change').click()
    >>> print(registry_browser.url)
    http://launchpad.test/bzr

    >>> contents = find_main_content(registry_browser.contents)
    >>> print(contents.find(id='project-inactive'))
    None

Revert team memberships.

    >>> login('foo.bar@canonical.com')
    >>> nopriv = getUtility(IPersonSet).getByName('no-priv')
    >>> nopriv.leave(celebs.registry_experts)
    >>> registry_member.leave(celebs.registry_experts)
    >>> logout()
