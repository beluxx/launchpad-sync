Translations to Complete
------------------------

Jean Champollion is a translator.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> login(ANONYMOUS)

    >>> jean = factory.makePerson(name='jean', email='jean@example.com')

Jean has been working on French translations for Foux in Launchpad.

    >>> foux = factory.makeProduct(name='foux')
    >>> trunk = foux.getSeries('trunk')
    >>> template = factory.makePOTemplate(productseries=trunk)
    >>> pofile = factory.makePOFile(potemplate=template, language_code='fr')
    >>> pofile = removeSecurityProxy(pofile)

    >>> potmsgset = factory.makePOTMsgSet(
    ...     potemplate=template, singular='a', sequence=1)
    >>> message = factory.makeCurrentTranslationMessage(
    ...     potmsgset=potmsgset, pofile=pofile, translator=jean,
    ...     translations=['un'])

Foux needs more strings translated.

    >>> removeSecurityProxy(pofile.potemplate).messagecount = 2

    >>> logout()

Jean visits his Translations dashboard.

    >>> jean_browser = setupBrowser(auth='Basic jean@example.com:test')
    >>> jean_home = 'http://translations.launchpad.test/~jean'
    >>> jean_browser.open(jean_home)

The dashboard shows a listing of translations that need Jean's help.

    >>> tag = find_tag_by_id(
    ...     jean_browser.contents, 'translations-to-complete-table')
    >>> print(tag.decode_contents())

Only Jean sees his personal listing.

    >>> user_browser.open(jean_home)
    >>> tag = find_tag_by_id(
    ...     user_browser.contents, 'translations-to-complete-table')
    >>> print(tag)
    None

Pierre is not a translator.  Pierre does not get such a listing either.

    >>> login(ANONYMOUS)
    >>> pierre = factory.makePerson(name='pierre', email='pierre@example.com')
    >>> logout()

    >>> pierre_browser = setupBrowser(auth='Basic pierre@example.com:test')
    >>> pierre_browser.open('http://translations.launchpad.test/~pierre')
    >>> tag = find_tag_by_id(
    ...     pierre_browser.contents, 'translations-to-complete-table')
    >>> print(tag)
    None


Teams
-----

The Rosetta administrators, as a special case, can act as a translator
for automatically generated messages.  Nevertheless, its Translations
page does not show any translations to complete--even to a member of the team.

    >>> login('carlos@canonical.com')
    >>> from zope.component import getUtility
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> pofile = factory.makePOFile('ru')
    >>> rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
    >>> message = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile, translator=rosetta_experts, translations=['x'])
    >>> logout()

    >>> carlos_browser = setupBrowser('Basic carlos@canonical.com:test')
    >>> experts_home = 'http://translations.launchpad.test/~rosetta-admins'
    >>> carlos_browser.open(experts_home)

    >>> print(extract_text(find_tag_by_id(
    ...     jean_browser.contents, 'translations-to-complete-table')))
