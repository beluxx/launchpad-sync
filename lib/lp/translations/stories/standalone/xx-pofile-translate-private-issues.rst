When being in read only mode, the well known msgids from GNOME or KDE to add
translation credits with email address should be rendered, but with a message
saying that the translations, and thus, the email address are only available
if you log in.

    >>> browser.open(
    ...     "http://translations.launchpad.test/alsa-utils/trunk/+pots/"
    ...     "alsa-utils/es/+translate"
    ... )

The GNOME standard string for credits is well handled.

    >>> msgid = find_tag_by_id(browser.contents, "msgset_199_singular")
    >>> print(msgid.decode_contents())
    translation-credits

    >>> translation = find_tag_by_id(
    ...     browser.contents, "msgset_199_es_translation_0"
    ... )
    >>> print(translation.decode_contents())
    To prevent privacy issues, this translation is not available to anonymous
    users,<br/> if you want to see it, please, <a href="+login">log in</a>
    first.

And the same for KDE one.

    >>> msgid = find_tag_by_id(browser.contents, "msgset_200_singular")
    >>> print(msgid.decode_contents())
    _: EMAIL OF TRANSLATORS<img alt="" src="/@@/translation-newline"/><br/>
    Your emails

    >>> translation = find_tag_by_id(
    ...     browser.contents, "msgset_200_es_translation_0"
    ... )
    >>> print(translation.decode_contents())
    To prevent privacy issues, this translation is not available to anonymous
    users,<br/> if you want to see it, please, <a href="+login">log in</a>
    first.

Also, suggestions should not appear.

    >>> find_tag_by_id(
    ...     browser.contents, "msgset_199_es_suggestion_709_0"
    ... ) is None
    True


But, if you are logged in, the system will show you the data.

    >>> user_browser.open(
    ...     "http://translations.launchpad.test/alsa-utils/trunk/+pots/"
    ...     "alsa-utils/es/+translate"
    ... )

The GNOME standard string for credits is now available:

    >>> msgid = find_tag_by_id(user_browser.contents, "msgset_199_singular")
    >>> print(msgid.decode_contents())
    translation-credits

    >>> translation = find_tag_by_id(
    ...     user_browser.contents, "msgset_199_es_translation_0"
    ... )
    >>> print(extract_text(translation.decode_contents()))
    Launchpad Contributions:
    Carlos ... http://translations.launchpad.test/~carlos

And the same for KDE one.

    >>> msgid = find_tag_by_id(user_browser.contents, "msgset_200_singular")
    >>> print(msgid.decode_contents())
    _: EMAIL OF TRANSLATORS<img alt="" src="/@@/translation-newline"/><br/>
    Your emails

    >>> translation = find_tag_by_id(
    ...     user_browser.contents, "msgset_200_es_translation_0"
    ... )
    >>> print(translation.decode_contents())
    ,,carlos@canonical.com

Also, suggestions should not appear.

    >>> suggestion = find_tag_by_id(
    ...     user_browser.contents, "msgset_199_es_suggestion_709_0"
    ... )
    >>> print(suggestion)
    None
