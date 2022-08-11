ProductEditPeopleView
=====================

Reassignment to an IPerson
--------------------------

A product can be reassigned to another person. Firefox is owned by Sample
Person (name12).

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.product import IProductSet

    >>> productset = getUtility(IProductSet)
    >>> firefox = productset.getByName('firefox')
    >>> sample_person = firefox.owner
    >>> print(sample_person.name)
    name12

No Privileges Person is taking over the project, but they cannot access the
view because they are not yet an owner/maintainer or admin.

    >>> from lp.services.webapp.authorization import check_permission

    >>> login('no-priv@canonical.com')
    >>> view = create_view(firefox, '+edit-people')
    >>> check_permission('launchpad.Edit', view)
    False

Sample person, as the owner/maintainer can change the owner/maintainer
to No Privileges Person.

    >>> ignored = login_person(sample_person)
    >>> form = {
    ...     'field.owner': 'no-priv',
    ...     'field.actions.save': 'Save changes',
    ...     }

    >>> view = create_initialized_view(firefox, '+edit-people', form=form)
    >>> view.errors
    []

    >>> print(firefox.owner.name)
    no-priv

Ownership can not be transferred to an open team.

    >>> owner = factory.makePerson()
    >>> ignored = login_person(owner)
    >>> product = factory.makeProduct(owner=owner)
    >>> from lp.registry.interfaces.person import TeamMembershipPolicy
    >>> team = factory.makeTeam(
    ...     name='open', membership_policy=TeamMembershipPolicy.OPEN)
    >>> form = {
    ...     'field.owner': 'open',
    ...     'field.actions.save': 'Save changes',
    ...     }

    >>> transaction.commit()
    >>> view = create_initialized_view(product, '+edit-people', form=form)
    >>> for error in view.errors:
    ...     print(error)
    You must choose a valid person or team to be the owner for ...


Assigning to Registry Administrators
------------------------------------

As a short-cut, a checkbox is presented to disclaim the maintainer
role and transfer it to the Registry Administrators team.

    >>> ignored = login_person(sample_person)
    >>> product = factory.makeProduct(owner=sample_person)
    >>> transaction.commit()

    >>> form = {
    ...     'field.transfer_to_registry': 'on',
    ...     'field.actions.save': 'Save changes',
    ...     }

    >>> view = create_initialized_view(product, '+edit-people', form=form)
    >>> view.errors
    []

    >>> print(product.owner.name)
    registry

Not specifying the owner/maintainer nor checking the checkbox is an error.

    >>> form = {
    ...     'field.actions.save': 'Save changes',
    ...     }

    >>> view = create_initialized_view(product, '+edit-people', form=form)
    >>> for error in view.errors:
    ...     print(error)
    You must specify a maintainer or select the checkbox.

Selecting both the owner/maintainer and the checkbox is also an error.

    >>> product = factory.makeProduct(owner=sample_person)
    >>> transaction.commit()
    >>> form = {
    ...     'field.owner': 'no-priv',
    ...     'field.transfer_to_registry': 'on',
    ...     'field.actions.save': 'Save changes',
    ...     }

    >>> view = create_initialized_view(product, '+edit-people', form=form)
    >>> for error in view.errors:
    ...     print(error)
    You may not specify a new owner if you select the checkbox.
