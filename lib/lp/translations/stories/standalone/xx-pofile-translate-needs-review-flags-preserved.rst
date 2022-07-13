Someone should review this translation usage
============================================

Forcing suggestions
-------------------

When translating is restricted to a particular set of users
(like Evolution product is restricted for Spanish), other users
don't see a checkbox named 'Someone should review this translation'.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/evolution/trunk/+pots/'
    ...     'evolution-2.2/es/1/+translate')

So, the checkbox is not shown.

    >>> needs_review_set = user_browser.getControl(
    ...     'Someone should review this translation')
    Traceback (most recent call last):
    ...
    LookupError: label ...'Someone...

If the same user tries translating for another, unrestricted project,
they get to see the checkbox:

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/evolution-2.2/es/1/+translate')
    >>> needs_review_set = user_browser.getControl(
    ...     'Someone should review this translation')
    >>> needs_review_set.selected
    False

To send a suggestion instead of making an approved translation,
a translator needs to mark the needs review checkbox.

    >>> needs_review_set.selected = True
    >>> user_browser.getControl(
    ...     name='msgset_130_es_translation_0_radiobutton').value = [
    ...         'msgset_130_es_translation_0_new']
    >>> user_browser.getControl(
    ...     name='msgset_130_es_translation_0_new').value = "New suggestion"
    >>> user_browser.getControl('Save & Continue').click()
    >>> print(user_browser.url)  # noqa
    http://translations.launchpad.test/ubuntu/hoary/+source/evolution/+pots/evolution-2.2/es/2/+translate

The needs review flag is unset when we go back to the previous message.

    >>> user_browser.getLink('Previous').click()
    >>> needs_review_set = user_browser.getControl(
    ...     'Someone should review this translation')
    >>> needs_review_set.selected
    False

But a new suggestion is provided for this message.

    >>> import re
    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents,
    ...     re.compile(r'^msgset_130_es_suggestion_\d+_0$'))))
    New suggestion


Resetting translations
----------------------

If the 'Someone should review this translation' checkbox is used without
adding any new suggestions or adding an empty string, the current translation
will be reset causing all suggestions entered for this message to be listed
again.

A new translation is entered and checked that it was saved as the current
translation, while no suggestions are displayed.

    >>> admin_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/man/es/1/+translate')
    >>> inputradio = admin_browser.getControl(
    ...    name='msgset_166_es_translation_0_radiobutton')
    >>> inputradio.value = ['msgset_166_es_translation_0_new']
    >>> inputfield = admin_browser.getControl(
    ...     name='msgset_166_es_translation_0_new')
    >>> inputfield.value = 'New test translation'
    >>> admin_browser.getControl('Save & Continue').click()
    >>> print(extract_text(find_tag_by_id(admin_browser.contents,
    ...                             'messages_to_translate')))
    1. English: test man page
    Current Spanish: New test translation Translated and reviewed ...
    New translation:
    Someone should review this translation
    Located in ...

'Someone should review this translation' can be used to reset the translation,
when a new empty translation is added and marked as needing review.
After clicking 'Save & Continue', all translations entered for this
message will be listed as suggestions.

    >>> admin_browser.getControl(
    ...     'Someone should review this translation').selected = True
    >>> inputradio = admin_browser.getControl(
    ...    name='msgset_166_es_translation_0_radiobutton')
    >>> inputradio.value = ['msgset_166_es_translation_0_new']
    >>> admin_browser.getControl('Save & Continue').click()
    >>> print(extract_text(find_tag_by_id(admin_browser.contents,
    ...                             'messages_to_translate')))
    1. English: test man page
    Current Spanish: (no translation yet)
    Suggestions:
    New test translation Suggested by Foo Bar ...
    blah, blah, blah Suggested by Carlos ...
    lalalala Suggested by Carlos ...
    just a translation Suggested by Sample Person ...
    Dismiss all suggestions above.
    New translation:
    Someone should review this translation
    Located in ...
