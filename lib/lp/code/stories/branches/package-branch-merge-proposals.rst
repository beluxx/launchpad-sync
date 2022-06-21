Package branch merge proposals
==============================

Package branches can be used for merge proposals just like normal upstream
branches.

    >>> login(ANONYMOUS)
    >>> eric = factory.makePerson(name="eric", email="eric@example.com")
    >>> b1 = factory.makePackageBranch(owner=eric)
    >>> b2 = factory.makePackageBranch(
    ...     owner=eric, sourcepackage=b1.sourcepackage)
    >>> b1_url = canonical_url(b1)
    >>> b2_name = b2.unique_name
    >>> logout()


    >>> browser = setupBrowser(auth='Basic eric@example.com:test')
    >>> browser.open(b1_url)
    >>> browser.getLink('Propose for merging').click()
    >>> browser.getControl(
    ...     name="field.target_branch.target_branch").value = b2_name
    >>> browser.getControl('Propose Merge').click()
