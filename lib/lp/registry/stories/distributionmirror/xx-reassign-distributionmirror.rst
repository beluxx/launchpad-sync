XXX: This test must be generalized and used like
tests/questiontarget.rst, to test reassignment in all contexts that
allow them. -- Guilherme Salgado, 2006-10-27

    These are the variables that will be defined in each setup hook once we
    move to a generic test used for all objects that can be reassigned.
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distributionmirror import (
    ...     IDistributionMirrorSet,
    ... )
    >>> login(ANONYMOUS)
    >>> context = getUtility(IDistributionMirrorSet).getByName(
    ...     "archive-mirror"
    ... )
    >>> owner_attribute_name = "owner"
    >>> context_url = "http://launchpad.test/ubuntu/+mirror/archive-mirror"
    >>> logout()

Distribution mirrors can be reassigned by anybody with the launchpad.Edit
permission on them. Mark is the owner of the archive-mirror.

    >>> user_browser.open(context_url)
    >>> user_browser.getLink("Change")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.open(context_url + "/+reassign")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> browser.addHeader("Authorization", "Basic mark@example.com:test")
    >>> browser.open(context_url)
    >>> browser.getLink("Change owner").click()
    >>> browser.url
    'http://launchpad.test/ubuntu/+mirror/archive-mirror/+reassign'

First we'll enter an unexistent name.

    >>> browser.getControl(name="field.owner").value = "unexistent-name"
    >>> browser.getControl(name="field.existing").value = ["existing"]
    >>> browser.getControl("Change").click()
    >>> browser.url
    'http://launchpad.test/ubuntu/+mirror/archive-mirror/+reassign'
    >>> for tag in find_tags_by_class(browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There is 1 error.
    There's no person/team named 'unexistent-name' in Launchpad.

We also try to use the name of an unvalidated account, which can't be used as
the owner of something.

    >>> from lp.registry.model.person import Person
    >>> Person.byName("matsubara").is_valid_person_or_team
    False
    >>> browser.getControl(name="field.owner").value = "matsubara"
    >>> browser.getControl("Change").click()
    >>> browser.url
    'http://launchpad.test/ubuntu/+mirror/archive-mirror/+reassign'
    >>> for tag in find_tags_by_class(browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There is 1 error.
    The person/team named 'matsubara' is not a valid owner for ...

Now we try to create a team using a name that is already taken.

    >>> browser.getControl(name="field.owner").value = "name16"
    >>> browser.getControl(name="field.existing").value = ["new"]
    >>> browser.getControl("Change").click()
    >>> browser.url
    'http://launchpad.test/ubuntu/+mirror/archive-mirror/+reassign'
    >>> for tag in find_tags_by_class(browser.contents, "message"):
    ...     print(tag.decode_contents())
    ...
    There is 1 error.
    There's already a person/team with the name 'name16' in Launchpad...

Okay, let's do it properly now and reassign it to an existing (and validated)
account.

    >>> salgado = Person.byName("salgado")
    >>> salgado.is_valid_person_or_team
    True

    >>> browser.getControl(name="field.owner").value = "salgado"
    >>> browser.getControl(name="field.existing").value = ["existing"]
    >>> browser.getControl("Change").click()
    >>> browser.url
    'http://launchpad.test/ubuntu/+mirror/archive-mirror'
    >>> login(ANONYMOUS)
    >>> context = getUtility(IDistributionMirrorSet).getByName(
    ...     "archive-mirror"
    ... )
    >>> salgado.id == getattr(context, owner_attribute_name).id
    True
    >>> logout()
