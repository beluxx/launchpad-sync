Answer Contacts for Distribution Source Package
===============================================

Support on source packages is handled both by the source package answer
contacts as well as the distribution answer contacts.

    # Register a Sample Person as an answer contact for the distribution.
    >>> from zope.component import getUtility
    >>> from lp.testing import login, logout
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> login("test@canonical.com")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")

Answer contacts must speak a language.

    >>> user = getUtility(ILaunchBag).user
    >>> user.addLanguage(getUtility(ILanguageSet)["en"])
    >>> ubuntu.addAnswerContact(user, user)
    True
    >>> flush_database_updates()
    >>> logout()

To reflect this, a user visiting a source package 'Answers' facet will
see both a portlet listing the answer contacts for the source package
and another one listing those of the distribution.

    >>> anon_browser.open("http://launchpad.test/ubuntu/+source/evolution")
    >>> anon_browser.getLink("Answers").click()
    >>> portlet = find_portlet(
    ...     anon_browser.contents, "Answer contacts for evolution in Ubuntu"
    ... )

To register themselves as answer contact, the user clicks on the
'Set answer contact' link. They need to login to access that function.

    >>> anon_browser.getLink("Set answer contact").click()
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

    >>> browser.addHeader("Authorization", "Basic test@canonical.com:test")
    >>> browser.open(
    ...     "http://launchpad.test/ubuntu/+source/evolution/+questions"
    ... )
    >>> browser.getLink("Answers").click()
    >>> browser.getLink("Set answer contact").click()
    >>> print(browser.title)
    Answer contact for evolution package...

On this page, the user can choose to become an answer contact by
clicking a checkbox. All the teams they're a member of are also displayed,
and they can register these teams as well.

    >>> browser.getControl(
    ...     "I want to be an answer contact for evolution"
    ... ).selected
    False
    >>> browser.getControl(
    ...     "I want to be an answer contact for " "evolution"
    ... ).selected = True
    >>> browser.getControl("Landscape Developers").selected
    False
    >>> browser.getControl("Landscape Developers").selected = True

To save their choices, the user clicks on the 'Continue' button and
a message is displayed to confirm the changes:

    >>> browser.getControl("Continue").click()
    >>> for message in find_tags_by_class(browser.contents, "message"):
    ...     print(extract_text(message))
    ...
    You have been added as an answer contact for evolution in Ubuntu.
    English was added to Landscape Developers's preferred languages.
    Landscape Developers has been added as an answer contact for
    evolution in Ubuntu.

To unregister as answer contact, the same page is used. Instead this
time, we unselect the checkboxes:

    >>> browser.getLink("Set answer contact").click()
    >>> browser.getControl(
    ...     "I want to be an answer contact for evolution"
    ... ).selected
    True
    >>> browser.getControl(
    ...     "I want to be an answer contact for " "evolution"
    ... ).selected = False

Again a confirmation message is displayed.

    >>> browser.getControl("Continue").click()
    >>> for message in find_tags_by_class(browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    You have been removed as an answer contact for evolution in Ubuntu.
