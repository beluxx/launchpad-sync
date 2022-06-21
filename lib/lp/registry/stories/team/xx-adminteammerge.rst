Merging Teams
=============

There's a separate page for merging teams.  We can't merge teams with
active members, so the user will first have to confirm that the
members should be deactivated before the teams are merged.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login('foo.bar@canonical.com')
    >>> registry_expert = factory.makePerson(email='reg@example.com')
    >>> new_team = factory.makeTeam(
    ...     name="new-team", email="new_team@example.com")
    >>> registry_experts = getUtility(IPersonSet).getByName('registry')
    >>> ignored = registry_experts.addMember(
    ...     registry_expert, registry_experts.teamowner)
    >>> logout()
    >>> registry_browser = setupBrowser(auth='Basic reg@example.com:test')
    >>> registry_browser.open('http://launchpad.test/people/+adminteammerge')
    >>> registry_browser.getControl('Duplicated Team').value = (
    ...     'new-team')
    >>> registry_browser.getControl('Target Team').value = 'guadamen'
    >>> registry_browser.getControl('Merge').click()

    >>> registry_browser.url
    'http://launchpad.test/people/+adminteammerge'
    >>> print_feedback_messages(registry_browser.contents)
    New Team has 1 active members which will have to be deactivated
    before the teams can be merged.

    >>> registry_browser.getControl('Deactivate Members and Merge').click()
    >>> registry_browser.url
    'http://launchpad.test/~guadamen'

    >>> print_feedback_messages(registry_browser.contents)
    A merge is queued and is expected to complete in a few minutes.
