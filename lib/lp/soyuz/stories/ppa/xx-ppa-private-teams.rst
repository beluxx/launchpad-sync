Personal Package Archives for private teams
===========================================


Activating Personal Package Archives for Private Teams
------------------------------------------------------

Private teams can have PPAs and the process of activation is the same
as for individuals and public teams.

Create a private team.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import (
    ...     IPersonSet,
    ...     PersonVisibility,
    ...     TeamMembershipPolicy,
    ... )
    >>> login("foo.bar@canonical.com")
    >>> person_set = getUtility(IPersonSet)
    >>> cprov = person_set.getByName("cprov")
    >>> priv_team = factory.makeTeam(
    ...     name="private-team",
    ...     owner=cprov,
    ...     displayname="Private Team",
    ...     visibility=PersonVisibility.PRIVATE,
    ...     membership_policy=TeamMembershipPolicy.MODERATED,
    ... )
    >>> logout()

A section named 'Personal Package Archives' is presented in the
user/team page.

    >>> browser = setupBrowser(
    ...     auth="Basic celso.providelo@canonical.com:test"
    ... )
    >>> browser.open("http://launchpad.test/~private-team")

    >>> print_tag_with_id(browser.contents, "ppas")
    Personal package archives
    Create a new PPA

The form looks almost identical to that for a public team.

    >>> browser.getLink("Create a new PPA").click()
    >>> print(browser.title)
    Activate PPA : ...Private Team...

There is, however, an extra bit of information indicating the new PPA
will be private.

    >>> print_tag_with_id(browser.contents, "ppa-privacy-statement")
    Since 'Private Team' is a private team this PPA will be private.

The URL template also shows the private URL.

    >>> print(extract_text(first_tag_by_class(browser.contents, "form")))
    URL:
      http://private-ppa.launchpad.test/private-team/
      At least one lowercase letter or number, followed by letters, numbers,
      dots, hyphens or pluses. Keep this name short; it is used in URLs.
    ...


    >>> browser.getControl(
    ...     name="field.displayname"
    ... ).value = "Private Team PPA"
    >>> browser.getControl(name="field.accepted").value = True
    >>> browser.getControl("Activate").click()
    >>> print(browser.title)
    Private Team PPA : “Private Team” team


Administrator changes to the PPA
--------------------------------

An administrator viewing the PPA administration page sees that it is
marked private.

    >>> admin_browser.open(
    ...     "http://launchpad.test/~private-team/+archive/ppa/+admin"
    ... )
    >>> admin_browser.getControl(name="field.private").value
    True

Attempting to change the PPA to public is thwarted.

    >>> admin_browser.getControl(name="field.private").value = False
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    Private teams may not have public archives.
