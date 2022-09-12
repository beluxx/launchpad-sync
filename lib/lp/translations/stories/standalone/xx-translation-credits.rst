Translation credits
===================

Translation credit strings are automatically updated with contributors
through Launchpad.

ALSA Utils template contains both KDE- and GNOME-style translation credit
messages.  Carlos is going to update this translation to Serbian,
which has so far been untranslated.

    >>> browser = setupBrowser(auth="Basic carlos@canonical.com:test")
    >>> browser.open(
    ...     "http://translations.launchpad.test/alsa-utils/trunk/+pots/"
    ...     "alsa-utils/sr/+translate"
    ... )

GNOME-style credits string is 'translation-credits'.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "msgset_199_singular")
    ...     )
    ... )
    translation-credits

This has no translation yet:

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             browser.contents, "msgset_199_sr_translation_0"
    ...         )
    ...     )
    ... )
    (no translation yet)

And there is no input field allowing changing this message.

    >>> print(
    ...     find_tag_by_id(
    ...         browser.contents, "msgset_199_sr_translation_0_new"
    ...     )
    ... )
    None

KDE-style translation credits are split into two messages, with emails
in one, and names in other.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "msgset_200_singular")
    ...     )
    ... )
    _: EMAIL OF TRANSLATORS...Your emails
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "msgset_201_singular")
    ...     )
    ... )
    _: NAME OF TRANSLATORS...Your names

These are locked as well:

    >>> print(
    ...     find_tag_by_id(
    ...         browser.contents, "msgset_200_sr_translation_0_new"
    ...     )
    ... )
    None
    >>> print(
    ...     find_tag_by_id(
    ...         browser.contents, "msgset_201_sr_translation_0_new"
    ...     )
    ... )
    None

We can translate a non-translator credits message, which will update
displayed credits once we submit the translation.

    >>> inputradio = browser.getControl(
    ...     name="msgset_198_sr_translation_0_radiobutton"
    ... )
    >>> inputradio.value = ["msgset_198_sr_translation_0_new"]
    >>> inputfield = browser.getControl(
    ...     name="msgset_198_sr_translation_0_new"
    ... )
    >>> inputfield.value = "Test translation"
    >>> browser.getControl("Save & Continue").click()
    >>> print(browser.url)  # noqa
    http://translations.launchpad.test/alsa-utils/trunk/+pots/alsa-utils/sr/+translate

Translation has been updated.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             browser.contents, "msgset_198_sr_translation_0"
    ...         )
    ...     )
    ... )
    Test translation

And translation credits now list Carlos.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             browser.contents, "msgset_199_sr_translation_0"
    ...         )
    ...     )
    ... )
    Launchpad Contributions:
    Carlos Perelló Marín http://translations.launchpad.test/~carlos

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             browser.contents, "msgset_200_sr_translation_0"
    ...         )
    ...     )
    ... )
    ,,carlos@canonical.com

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             browser.contents, "msgset_201_sr_translation_0"
    ...         )
    ...     )
    ... )
    ,Launchpad Contributions:,Carlos Perelló Marín
