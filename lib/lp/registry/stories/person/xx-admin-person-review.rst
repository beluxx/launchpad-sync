Review person
=============

Registry admins can review users and update some of their information.

    >>> email = "expert@example.com"
    >>> expert = factory.makeRegistryExpert(email=email)
    >>> expert_browser = setupBrowser(auth='Basic %s:test' % email)
    >>> logout()

    >>> expert_browser.open('http://launchpad.test/~salgado')
    >>> expert_browser.getLink('Administer').click()
    >>> print(expert_browser.url)
    http://launchpad.test/~salgado/+review

    >>> print(expert_browser.title)
    Review person...

    >>> expert_browser.getControl('Name', index=0).value = 'no-way'
    >>> expert_browser.getControl('Personal standing').value = ['GOOD']
    >>> expert_browser.getControl(
    ...     name='field.personal_standing_reason').value = 'good guy'
    >>> expert_browser.getControl('Change').click()
    >>> print(expert_browser.url)
    http://launchpad.test/~no-way

Registry experts can't change the displayname.

    >>> expert_browser.getLink('Administer').click()
    >>> expert_browser.getControl(
    ...     'Display Name', index=0).value = 'The one and only Salgado'
    >>> expert_browser.getControl('Change').click()
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

But Launchpad admins can.
    >>> admin_browser.open('http://launchpad.test/~no-way/+review')
    >>> admin_browser.getControl('Name', index=0).value = 'salgado'
    >>> admin_browser.getControl(
    ...     'Display Name', index=0).value = 'The one and only Salgado'
    >>> admin_browser.getControl('Change').click()
    >>> print(admin_browser.title)
    The one and only Salgado in Launchpad
    >>> print(admin_browser.url)
    http://launchpad.test/~salgado


Review account
--------------

The review page has a link to the review account page.

    >>> expert_browser.open('http://launchpad.test/~salgado')
    >>> expert_browser.getLink('Administer Account').click()
    >>> print(expert_browser.title)
    Review person's account...

The +reviewaccount page displays account information that is normally
hidden from the UI.

    >>> content = find_main_content(expert_browser.contents)
    >>> for tr in content.find(id='summary').find_all('tr'):
    ...     print(extract_text(tr))
    Created: 2005-06-06
    Creation reason: Created by the owner themselves, coming from Launchpad.
    OpenID identifiers: salgado_oid
    Email addresses: guilherme.salgado@canonical.com
    Guessed email addresses: salgado@ubuntu.com
    Status history:

The page also contains a link back to the +review page.

    >>> link = expert_browser.getLink(url='+review')
    >>> print(link.text)
    edit[IMG] Review the user's Launchpad information
