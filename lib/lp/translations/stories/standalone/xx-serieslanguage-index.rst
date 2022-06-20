Product or distribution release series language overview
========================================================

These pages are used by translators for accessing all templates in a
release series and viewing translation statistics for each template for
a specific language

The Translations page for a product release series with multiple
templates links to per-language overviews.

    >>> browser.open('http://translations.launchpad.test/evolution/trunk/')
    >>> browser.getLink('Portuguese (Brazil)').click()
    >>> print(browser.url)
    http://translations.launchpad.test/evolution/trunk/+lang/pt_BR

    >>> print(browser.title)
    Portuguese (Brazil) (pt_BR) : Series trunk : Translations : Evolution

Since there is no translation team to manage Portuguese (Brazil) language
in the Evolution's translation group, all users will be informed about it
and pointed to the translation group owner.

    >>> print(extract_text(find_tag_by_id(
    ...     browser.contents, 'group-team-info')))
    There is no team to manage Evolution translations to ...
    To set one up, please get in touch with Carlos Perelló Marín.

Anonymous users are informed that in order to make translations they
need to login first.

    >>> print(extract_text(
    ...     find_tag_by_id(browser.contents, 'translation-access-level')))
    You are not logged in. Please log in to work on translations...

Authenticated users will see information about what they can do in
these translations. Things like review, only add suggestion or no
changes at all.

If a product or distribution had no translation group, visitors are
informed about this fact and will be able to add translations without
requiring a review.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+lang/es')
    >>> print(extract_text(
    ...     find_tag_by_id(user_browser.contents, 'group-team-info')))
    There is no translation group to manage Ubuntu translations.

Create a translation group for Ubuntu, together with a translation
person for managing Ubuntu Spanish translations and set translation
policy to RESTRICTED.
This is done to so see what the page will look like when they exist.

    >>> from zope.component import getUtility
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.translations.enums import TranslationPermission
    >>> login('foo.bar@canonical.com')
    >>> utc_owner = factory.makePerson(displayname='Some Guy')
    >>> utc_team = factory.makeTeam(
    ...     owner=utc_owner, name='utc-team',
    ...     displayname='Ubuntu Translation Coordinators')
    >>> utg = factory.makeTranslationGroup(
    ...     owner=utc_team, name='utg', title='Ubuntu Translation Group')
    >>> st_coordinator = factory.makePerson(
    ...     name="ubuntu-l10n-es",
    ...     displayname='Ubuntu Spanish Translators')
    >>> dude = factory.makePerson(name="dude", email="dude@ex.com")
    >>> ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    >>> ubuntu.translationgroup = utg
    >>> ubuntu.translationpermission = TranslationPermission.RESTRICTED
    >>> translators = factory.makeTranslator(
    ...     'es', group=utg, person=st_coordinator)
    >>> no_license_translator = factory.makeTranslator(
    ...     'es', person=dude, license=False)
    >>> logout()

Spanish has a translation team for managing its translations and all
Evolution Spanish templates can be accessed from the distribution series
translation page.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/')
    >>> user_browser.getLink('Spanish').click()
    >>> print(user_browser.url)
    http://translations.launchpad.test/ubuntu/hoary/+lang/es

    >>> print(extract_text(
    ...     find_tag_by_id(user_browser.contents, 'group-team-info')))
    These Ubuntu translations are managed by Ubuntu Spanish Translators.

Authenticated users can add suggestion but will be held for review by
the members of Spanish translations team.

    >>> print(extract_text(
    ...     find_tag_by_id(
    ...         user_browser.contents, 'translation-access-level')))
    Your suggestions will be held for review by
    Ubuntu Spanish Translator...
    please get in touch with Ubuntu Spanish Translators...

Users will see three references to the team managing these translations.

    >>> print(user_browser.getLink('Ubuntu Spanish Translator').url)
    http://launchpad.test/~ubuntu-l10n-es

Catalan has no translation team for managing translations and since
there is no one to review the work, authenticated users can not add
suggestions.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/')
    >>> user_browser.getLink('Catalan').click()
    >>> print(user_browser.url)
    http://translations.launchpad.test/ubuntu/hoary/+lang/ca

    >>> print(extract_text(
    ...     find_tag_by_id(user_browser.contents, 'group-team-info')))
    There is no team to manage ... To set one up, please get in touch
    with Ubuntu Translation Coordinators.

    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents, 'translation-access-level')))
    Since there is nobody to manage translation ...
    you cannot add new suggestions. If you are interested in making
    translations, please contact Ubuntu Translation Coordinators...

    >>> print(user_browser.getLink('Ubuntu Translation Coordinators').url)
    http://launchpad.test/~utc-team

Members of translation team and translations admins have full access to
translations. They can add and review translations.

    >>> admin_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+lang/ro')
    >>> print(extract_text(find_tag_by_id(
    ...     admin_browser.contents, 'translation-access-level')))
    You can add and review translations...

For projects using closed translations policy, a translator that is not
member of the translation team appointed for that language will not
be allowed to make any changes.

    >>> login('foo.bar@canonical.com')
    >>> ubuntu.translationpermission = TranslationPermission.CLOSED
    >>> logout()

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+lang/ro')
    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents, 'translation-access-level')))
    These templates can be translated only by their managers...

Translation policy is rolled back to not affect other tests.

    >>> login('foo.bar@canonical.com')
    >>> ubuntu.translationpermission = TranslationPermission.RESTRICTED
    >>> logout()

Translators that have not agreed with the licence can not make
translations, and will see a link to the licence page.

    >>> no_license_browser = setupBrowser(
    ...     auth='Basic dude@ex.com:test')
    >>> no_license_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+lang/ro')
    >>> print(extract_text(find_tag_by_id(
    ...     no_license_browser.contents, 'translation-access-level')))
    To make translations in Launchpad you need to agree with
    the Translations licensing...

    >>> print(no_license_browser.getLink('Translations licensing').url)
    http://translations.launchpad.test/~dude/+licensing

For projects with no translation group, translators see a note stating
this fact. No access level information is displayed.

    >>> login('foo.bar@canonical.com')
    >>> ubuntu.translationgroup = None
    >>> logout()

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+lang/ro')
    >>> print(extract_text(
    ...     find_tag_by_id(user_browser.contents, 'group-team-info')))
    There is no translation group to manage Ubuntu translations.

    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents, 'translation-access-level')))
    Templates which are more important to translate are listed first.

Translation group configuration is rolled back to not affect other tests.

    >>> login('foo.bar@canonical.com')
    >>> ubuntu.translationgroup = utg
    >>> logout()

The details of the page are tested at the view level.
