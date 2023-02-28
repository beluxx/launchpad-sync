Dismissing suggestions
======================

Not all suggestions that are made for a translation do become the current
translation of a message. If the current translation is good enough, new
suggestions can be dismissed to keep them off the page.

    >>> from zope.component import getUtility
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet

    >>> login(ANONYMOUS)
    >>> utility = getUtility(IPOTemplateSet)
    >>> _ = utility.populateSuggestivePOTemplatesCache()
    >>> logout()


First the admin (or anybody with edit rights) adds a translation.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/alsa-utils"
    ...     "/trunk/+pots/alsa-utils/de/+translate"
    ... )
    >>> admin_browser.getControl(
    ...     name="msgset_198_de_translation_0_new"
    ... ).value = "The great new translation."
    >>> admin_browser.getControl(
    ...     name="msgset_198_de_translation_0_radiobutton"
    ... ).value = ["msgset_198_de_translation_0_new"]
    >>> admin_browser.getControl("Save & Continue").click()
    >>> print(admin_browser.url)
    http://translations.../alsa-utils/trunk/+pots/alsa-utils/de/+translate
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             admin_browser.contents, "msgset_198_de_translation_0"
    ...         )
    ...     )
    ... )
    The great new translation.

Now somebody else comes and makes a really bad suggestion.

    >>> user_browser.open(
    ...     "http://translations.launchpad.test/alsa-utils"
    ...     "/trunk/+pots/alsa-utils/de/+translate"
    ... )
    >>> user_browser.getControl(
    ...     name="msgset_198_de_translation_0_new"
    ... ).value = "The really bad suggestion."
    >>> user_browser.getControl(
    ...     name="msgset_198_de_translation_0_radiobutton"
    ... ).value = ["msgset_198_de_translation_0_new"]
    >>> user_browser.getControl(
    ...     name="msgset_198_de_needsreview"
    ... ).value = "force_suggestion"
    >>> user_browser.getControl("Save & Continue").click()
    >>> print(user_browser.url)
    http://translations.../alsa-utils/trunk/+pots/alsa-utils/de/+translate

But it's only a suggestion, so the translation remains unchanged.

    >>> import re
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             user_browser.contents, "msgset_198_de_translation_0"
    ...         )
    ...     )
    ... )
    The great new translation.
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             user_browser.contents,
    ...             re.compile(r"^msgset_198_de_suggestion_\d+_0$"),
    ...         )
    ...     )
    ... )
    The really bad suggestion.

In order to get rid of this, the admin chooses to keep the great new
translation and to dismiss all suggestions.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/alsa-utils"
    ...     "/trunk/+pots/alsa-utils/de/+translate"
    ... )
    >>> admin_browser.getControl(
    ...     name="msgset_198_dismiss"
    ... ).value = "dismiss_suggestions"
    >>> admin_browser.getControl("Save & Continue").click()
    >>> print(admin_browser.url)
    http://translations.../alsa-utils/trunk/+pots/alsa-utils/de/+translate

The great new translation is still intact.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             admin_browser.contents, "msgset_198_de_translation_0"
    ...         )
    ...     )
    ... )
    The great new translation.

But the really bad suggestion is gone.

    >>> print(
    ...     find_tag_by_id(
    ...         admin_browser.contents, "msgset_198_de_suggestion_702_0"
    ...     )
    ... )
    None

External suggestions
--------------------

External suggestions cannot be dismissed, they are staying around. Here is
such a case.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/evolution/"
    ...     "trunk/+pots/evolution-2.2/es/5/+translate"
    ... )
    >>> admin_browser.getControl(
    ...     name="msgset_5_dismiss"
    ... ).value = "dismiss_suggestions"
    >>> admin_browser.getControl("Save & Continue").click()
    >>> print(admin_browser.url)
    http://translations.../evolution/trunk/+pots/evolution-2.2/es/6/+translate

There are still suggestions because they are external.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/evolution/"
    ...     "trunk/+pots/evolution-2.2/es/5/+translate"
    ... )
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             admin_browser.contents, "msgset_5_es_suggestion_686_0"
    ...         )
    ...     )
    ... )
    caratas

But the checkbox for dismissal is gone.

    >>> print(find_tag_by_id(admin_browser.contents, "msgset_5_dismiss"))
    None
