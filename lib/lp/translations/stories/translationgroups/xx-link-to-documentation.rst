Each translation team can provide a link to an external page that
documents the translation process for the team and provides style guides.
The link is displayed on each page where translations are entered.
Currently, the translation group responsible for the Spanish translations of
evolution do not have such a link.

    >>> anon_browser.open(
    ...     'http://translations.launchpad.test/evolution/trunk/'
    ...     '+pots/evolution-2.2/es/+translate')
    >>> print(first_tag_by_class(anon_browser.contents, 'style_guide_url'))
    None

Carlos is the owner of the testing-translation-team group and can change
translators.

    >>> carlos_browser = setupBrowser(auth='Basic carlos@canonical.com:test')
    >>> carlos_browser.open(
    ...     'http://translations.launchpad.test/'
    ...     '+groups/testing-translation-team/es/+admin')
    >>> print(carlos_browser.title)
    Just a testing team...

This way he can also set the documentation URL.

    >>> carlos_browser.getControl('Translation guidelines').value = (
    ...     'http://www.ubuntu.com/')
    >>> carlos_browser.getControl('Change').click()
    >>> print(carlos_browser.url)
    http://translations.launchpad.test/+groups/testing-translation-team

The link now appears in the table next to the name of the team.

    >>> team = first_tag_by_class(carlos_browser.contents, 'translator-team')
    >>> print(extract_text(team.find_all('a')[0]))
    testing Spanish team

    >>> link = first_tag_by_class(carlos_browser.contents, 'translator-link')
    >>> print(link.find_all('a')[0]['href'])
    http://www.ubuntu.com/

Back on the translations page, the link is now present, too.

    >>> anon_browser.open(
    ...     'http://translations.launchpad.test/evolution/trunk/'
    ...     '+pots/evolution-2.2/es/+translate')
    >>> style_guide_url = first_tag_by_class(
    ...     anon_browser.contents, 'style-guide-url')
    >>> print(extract_text(style_guide_url))
    testing Spanish team guidelines
    >>> print(style_guide_url['href'])
    http://www.ubuntu.com/

Carlos appoints Sample Person as a translator for Esperanto.

    >>> carlos_browser.open(
    ...     'http://translations.launchpad.test/'
    ...     '+groups/testing-translation-team/+appoint')
    >>> carlos_browser.getControl('Language').value = ['eo']
    >>> carlos_browser.getControl('Translator').value = 'name12'
    >>> carlos_browser.getControl('Appoint').click()
    >>> print(carlos_browser.url)
    http://translations.launchpad.test/+groups/testing-translation-team

Sample Person can not administer their ITranslator record but they can edit
the documentation url through the edit view.

    >>> test_browser = setupBrowser(auth='Basic test@canonical.com:test')
    >>> from zope.security.interfaces import Unauthorized
    >>> try:
    ...     test_browser.open(
    ...         'http://translations.launchpad.test/'
    ...         '+groups/testing-translation-team/eo/+admin')
    ... except Unauthorized as e:
    ...     print(e)
    (...'launchpad.Admin')
    >>> test_browser.open(
    ...     'http://translations.launchpad.test/'
    ...     '+groups/testing-translation-team/eo/+edit')
    >>> print(test_browser.title)
    Set Esperanto guidelines...

    >>> test_browser.getControl('Translation guidelines').value = (
    ...     'http://www.launchpad.net/')
    >>> test_browser.getControl('Set guidelines').click()
    >>> print(test_browser.url)
    http://translations.launchpad.test/~name12
    >>> translator_listing = find_tag_by_id(
    ...     test_browser.contents, 'translation-group-memberships')
    >>> print(extract_text(translator_listing))
    Translation group
    Language
    Translation guidelines
    Just a testing team
    Esperanto
    http://www.launchpad.net/
    Edit


Notification display
--------------------

You can see on Spanish Evolution translation page how are translation
instructions displayed.

    >>> evolution_spanish_url = ('http://translations.launchpad.test/'
    ...     'evolution/trunk/+pots/evolution-2.2/es/+translate')

    # We've already confirmed setting URLs works: define methods
    # to change them more easily.
    >>> def set_group_url(browser, url):
    ...     group_edit_url = ("http://translations.launchpad.test/"
    ...         "+groups/testing-translation-team/+edit")
    ...     browser.open(group_edit_url)
    ...     browser.getControl('Translation instructions').value = url
    ...     browser.getControl('Change').click()

    >>> def set_team_url(browser, url):
    ...     team_edit_url = ("http://translations.launchpad.test/"
    ...         "+groups/testing-translation-team/es/+edit")
    ...     browser.open(team_edit_url)
    ...     browser.getControl('Translation guidelines').value = url
    ...     browser.getControl('Set guidelines').click()

    >>> def get_notification_content(browser):
    ...     tags = find_tags_by_class(
    ...         browser.contents, 'important-notice-container')
    ...     if len(tags) > 0:
    ...         return tags[0]
    ...     else:
    ...         return None

When no documentation URLs are set, no notification will be displayed.

    >>> set_group_url(carlos_browser, '')
    >>> set_team_url(carlos_browser, '')

    >>> browser.open(evolution_spanish_url)
    >>> print(get_notification_content(browser))
    None

Setting a group documentation URL will show the notification with the link
to said documentation.

    >>> set_group_url(carlos_browser, u'https://help.launchpad.net/')
    >>> browser.open(evolution_spanish_url)
    >>> notification = get_notification_content(browser)
    >>> print(extract_text(notification))
    Before translating, be sure to go through Just a testing team
    instructions.

    >>> links = notification.find_all('a')
    >>> print(links[0]['href'])
    https://help.launchpad.net/

Adding the Spanish team documentation URL adds another link.

    >>> set_team_url(carlos_browser, 'https://help.launchpad.net/Spanish')
    >>> browser.open(evolution_spanish_url)
    >>> notification = get_notification_content(browser)
    >>> print(extract_text(notification))
    Before translating, be sure to go through Just a testing team
    instructions and Spanish guidelines.

    >>> links = notification.find_all('a')
    >>> print(links[0]['href'])
    https://help.launchpad.net/
    >>> print(links[1]['href'])
    https://help.launchpad.net/Spanish

When there is no group documentation, but only team documentation,
the narrative is changed a bit to include the full team name.

    >>> set_group_url(carlos_browser, '')
    >>> browser.open(evolution_spanish_url)
    >>> notification = get_notification_content(browser)
    >>> print(extract_text(notification))
    Before translating, be sure to go through testing Spanish team
    guidelines.

    >>> links = notification.find_all('a')
    >>> print(links[0]['href'])
    https://help.launchpad.net/Spanish
