======================
Codes of conduct views
======================

Signed code of conduct for a user
---------------------------------

The PersonCodeOfConductEditView controls ~person/+codesofconduct.  It displays
the person's name in the page label.

    >>> login('admin@canonical.com')
    >>> geddy = factory.makePerson(displayname='Geddy Lee')
    >>> view = create_initialized_view(geddy, '+codesofconduct')
    >>> print(view.label)
    Codes of Conduct for Geddy Lee


Directions for signing code of conduct
--------------------------------------

If the user hasn't signed the code of conduct and does not have a GPG
key registered, directions are shown.

    >>> def print_coc_directions(content):
    ...     ol = content.find('ol')
    ...     if ol is not None:
    ...         for index, li in enumerate(ol.find_all('li')):
    ...             print('%s. %s' % ((index+1), extract_text(li)))
    >>> user = factory.makePerson()
    >>> ignored = login_person(user)
    >>> from lp.registry.interfaces.codeofconduct import ICodeOfConductSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.testing.pages import (
    ...     extract_text, find_tag_by_id)
    >>> coc_set = getUtility(ICodeOfConductSet)
    >>> view = create_initialized_view(coc_set, '+index', principal=user)
    >>> print_coc_directions(find_tag_by_id(view.render(), 'maincontent'))
    1. Register an OpenPGP key.
    2. Download the current Code of Conduct.
    3. Sign it!

If the user hasn't signed the code of conduct but does have a GPG key
registered, directions are shown with a message indicating that the
first step can be skipped.

    >>> _ignore = factory.makeGPGKey(user)
    >>> view = create_initialized_view(coc_set, '+index', principal=user)
    >>> print_coc_directions(find_tag_by_id(view.render(), 'maincontent'))
    1. Register an OpenPGP key.
       It appears you have already done this.
       The key ... is registered on your account.
       You can skip to the next step if you are not intending
       on signing with a different key.
    2. Download the current Code of Conduct.
    3. Sign it!

If the user has multiple keys, a count is shown.

    >>> _ignore = factory.makeGPGKey(user)
    >>> view = create_initialized_view(coc_set, '+index', principal=user)
    >>> print_coc_directions(find_tag_by_id(view.render(), 'maincontent'))
    1. Register an OpenPGP key.
       It appears you have already done this.
       2 keys are registered on your account.
       You can skip to the next step if you are not intending
       on signing with a different key.
    2. Download the current Code of Conduct.
    3. Sign it!

If the user has already signed the code of conduct, no directions are shown.

    >>> admin = getUtility(IPersonSet).getByEmail('admin@canonical.com')
    >>> ignored = login_person(admin)
    >>> view = create_initialized_view(coc_set, '+index', principal=admin)
    >>> content = find_tag_by_id(view.render(), 'maincontent')
    >>> print_coc_directions(content)
    >>> print(extract_text(content))
    Ubuntu Codes of Conduct...
    Congratulations, you have already signed the Ubuntu Code of Conduct...
