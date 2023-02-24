Translation Submissions
=======================

This pagetest is used to check general behaviour of IPOFile translation
submissions.

For specific tests, you can see:

xx-pofile-translate-empty-strings-without-validation.rst
xx-pofile-translate-gettext-error-middle-page.rst
xx-pofile-translate-html-tags-escape.rst
xx-pofile-translate-lang-direction.rst
xx-pofile-translate-alternative-language.rst
xx-pofile-translate-message-filtering.rst
xx-pofile-translate-newlines-check.rst
xx-pofile-translate-performance.rst

    >>> from zope.component import getUtility
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet

    >>> login(ANONYMOUS)
    >>> utility = getUtility(IPOTemplateSet)
    >>> _ = utility.populateSuggestivePOTemplatesCache()
    >>> logout()


Anonymous access
----------------

Anonymous users are able to browse translations, but not to change them
through the translation form.

    >>> browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/+source/"
    ...     "evolution/+pots/evolution-2.2/es/+translate"
    ... )

The page is rendered in read-only mode, without any textareas for input.

    >>> main_content = find_tag_by_id(
    ...     browser.contents, "messages_to_translate"
    ... )
    >>> for textarea in main_content.find_all("textarea"):
    ...     print("Found textarea:\n%s" % textarea)
    ...

In fact, no input widgets at all are displayed.

    >>> for input in main_content.find_all("input"):
    ...     print("Found input:\n%s" % input)
    ...

As an anynoymous user you will have access to the download and details
pages for the pofile this message belongs to. The link to upload page
should not be in that list and so does the link for switching between
translator and reviewer working mode.

    >>> nav = find_tag_by_id(browser.contents, "nav-pofile-subpages")
    >>> print(extract_text(nav))
    Download translation Translation details

Download translations and Translation details should linked to the proper
pages

    >> print(nav.getLink("Download translation").url)
    https://.../hoary/+source/evolution/+pots/evolution-2.2/es/+export
    >> print(nav.getLink("Translation details").url)
    https://.../hoary/+source/evolution/+pots/evolution-2.2/es/+details

Rendering the form in read-only mode does not actually stop an anonymous
visitor (e.g. a spam bot, or a user whose login has expired) from submitting
data. That part is more convenience than security. The server does not
remember what form it provided to which requester.


Translation Admin Access
------------------------

Let's log in.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/+source/"
    ...     "evolution/+pots/evolution-2.2/es/+translate"
    ... )

As a translation admin you will have access to the download, upload
and details pages for the pofile this message belongs to. In the same time
you have access to the link for switching between translator and reviewer
working mode

    >>> nav = find_tag_by_id(admin_browser.contents, "nav-pofile-subpages")
    >>> print(extract_text(nav))
    Download translation Upload translation Translation details
    Reviewer mode (What's this?)

All those links should linked the proper pages

    >> print(nav.getLink("Download translation").url)
    https://.../hoary/+source/evolution/+pots/evolution-2.2/es/+export
    >> print(nav.getLink("Upload translation").url)
    https://.../hoary/+source/evolution/+pots/evolution-2.2/es/+upload
    >> print(nav.getLink("Translation details").url)
    https://.../hoary/+source/evolution/+pots/evolution-2.2/es/+details


Requesting English and its variant languages
--------------------------------------------

English is not translatable since we store the untranslated messages
as English. The translate view uses often uses two languages during
the translation, one for the PO message set, and the other to 'make
suggestions from'. English cannot be either of these.

If someone were to attempt an English translation, to create an 'en'
PO message set, they will get an error. The user would generally have
to hack the URL, but they may have old bookmarks, or have followed old
links from off-site; Launchpad did make links for English translations
in the past.

    >>> browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/+source/"
    ...     "evolution/+pots/evolution-2.2/en/+translate"
    ... )
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: Object: ... name: 'en'

See xx-pofile-translate-alternative-language.rst for details about
the 'make suggestions from' feature.


Form elements
-------------

Because the server does not remember what forms it served to whom, it is
essential that every form element identifier provide all the context the
server needs to find back the objects it relates to. These HTML identifiers
are created in several places in the code and parsed in yet other places, so
they must adhere religiously to an agreed-to format.

    >>> def get_tags(browser, attribute, prefix):
    ...     """Extract tag "attributes" in page that begin with "prefix"."""
    ...     import re
    ...
    ...     content = find_main_content(browser.contents)
    ...     ids = [
    ...         tag.get(attribute)
    ...         for tag in content.find_all()
    ...         if re.match(prefix, tag.get(attribute, ""))
    ...     ]
    ...     return sorted(ids)
    ...

    >>> browser = setupBrowser(auth="Basic carlos@canonical.com:test")
    >>> browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "ubuntu/hoary/+source/evolution/+pots/evolution-2.2"
    ...     "/en_AU/+translate?field.alternative_language=es"
    ... )

Elements related 1:1 to a translatable message on this form have names and
identifiers constructed as "msgset_<id>," where <id> is the unpadded decimal
id of their POTMsgSet. The singular form, which plays a special role, has a
suffix 'singular' appended. We'll see other suffixes later.

    >>> msgset_130 = get_tags(browser, "id", "msgset_130")
    >>> for id in msgset_130:
    ...     print(id)
    ...
    msgset_130
    ...
    msgset_130_singular...

HTML element identifiers for suggestions and translations on this form are
constructed as an underscore-separated sequence of:

    * the string 'msgset';
    * the id for the POTMsgSet they pertain to;
    * language code, e.g. 'kr' or 'en_UK';
    * type, either 'translation' or 'suggestion';
    * plural-form number;
    * optional suffix describing the element, such as 'radiobutton.'

    >>> for id in msgset_130:
    ...     print(id)
    ...
    msgset_130
    msgset_130_en_AU_translation_0
    msgset_130_en_AU_translation_0_new
    msgset_130_en_AU_translation_0_new_select
    msgset_130_en_AU_translation_0_radiobutton
    msgset_130_es_suggestion_562_0
    msgset_130_es_suggestion_562_0_origin
    msgset_130_es_suggestion_562_0_radiobutton
    msgset_130_force_suggestion
    msgset_130_singular
    msgset_130_singular_copy_text

Radio buttons are grouped by their name attribute. The translate page shows
each translatable message with one radiobutton to select the existing
translation (the default); a group (possibly empty) of suggested translations;
and one for a custom translation entered into a text input field.

Here we see an example where one suggestion is offered
(there are three external suggestions, two of them are rejected),
making for three identically-named radio buttons and sundry other HTML tags.

    >>> browser.open(
    ...     "http://translations.launchpad.test/alsa-utils/trunk/"
    ...     "+pots/alsa-utils/es/+translate"
    ... )
    >>> msgset_198 = get_tags(browser, "name", "msgset_198")
    >>> for name in msgset_198:
    ...     print(name)
    ...
    msgset_198
    msgset_198_es_needsreview
    msgset_198_es_translation_0_new
    msgset_198_es_translation_0_radiobutton
    msgset_198_es_translation_0_radiobutton
    msgset_198_es_translation_0_radiobutton

There are many variants of this id structure, generated in several places and
for several objects, all generated by the same methods.

    >>> browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/+source/"
    ...     "evolution/+pots/evolution-2.2/es/5/+translate"
    ... )
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             browser.contents, "msgset_134_es_suggestion_694_0"
    ...         )
    ...     )
    ... )
    tarjetas


Missing plural forms information
--------------------------------

If the plural forms are not known for a language, users can not add
new translations and are asked to help Launchpad Translations by providing
the plural form informations.

This notice is display when doing batch translations or translating a
single message.

    >>> browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/"
    ...     "+source/evolution/+pots/evolution-2.2/ab/+translate"
    ... )
    >>> print_feedback_messages(browser.contents)
    Launchpad can’t handle the plural items ...

    >>> browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/"
    ...     "+source/evolution/+pots/evolution-2.2/ab/5/+translate"
    ... )
    >>> print_feedback_messages(browser.contents)
    Launchpad can’t handle the plural items ...
