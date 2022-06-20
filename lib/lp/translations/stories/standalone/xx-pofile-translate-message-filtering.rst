Message Filters on +translate Page
==================================

While doing translations, there is a functionality that allows the user
to filter the kind of messages that should be shown.

For this test, we know that the valid msgsets that this form uses are
the ones with the ids between 130 and 151. By default, view shows the
messages in the batches of 10 items.

    >>> import re
    >>> from lp.testing.pages import extract_url_parameter

    # This describes the HTML tag ids we'll be looking for below.

    >>> match_translation_id = 'msgset_([0-9]+)_es_translation_0$'

    # This function will be used to check the content of the browser.

    >>> def print_shown_messages(browser, soup=None):
    ...     """Print the id/value of all shown translations on the page."""
    ...     # Map msgset_ids to HTML tags
    ...     translations = {}
    ...
    ...     if soup is None:
    ...         soup = find_main_content(browser.contents)
    ...     for tag in soup.find_all('label'):
    ...         id = tag.get('id')
    ...         if id is not None:
    ...             match = re.match(match_translation_id, id)
    ...             if match:
    ...                 translations[int(match.group(1))] = tag
    ...
    ...     # Print matching HTML tags, in numeric order of msgset id
    ...     for msgset_id in sorted(translations.keys()):
    ...         translation = translations[msgset_id]
    ...         print("%d: '%s'" % (
    ...             msgset_id, translation.decode_contents().strip()))


Filters
-------

No Privileges Person visits the evolution-2.2 package in Ubuntu Hoary to
review the state of the translation.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/'
    ...     '+source/evolution/+pots/evolution-2.2/es/+translate')
    >>> print(user_browser.title)
    Spanish (es) : Template ...evolution-2.2... :
    Hoary (5.04) : Translations : evolution package : Ubuntu

They can see that there are 22 messages.

    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    1 ... 10  of 22 results

There is also an option for changing which items to show/translate on
this page, and which alternate language to get suggestions from (tested
in xx-pofile-translate-alternative-language.rst).

    >>> print(contents)
    <... Translating ... using ... as a guide...


Untranslated
............

No Privileges Person chooses to see the untranslated messages in the
evolution-2.2 sourcepackage. They set the view filter to 'Untranslated'
to filter the messages. They see 15 messages are not translated.

    >>> user_browser.getControl(name='show', index=1).value = ['untranslated']
    >>> user_browser.getControl('Change').click()
    >>> re.match('[^?]*', user_browser.url).group()
    'http://.../evolution-2.2/es/+translate'

    >>> print(extract_url_parameter(user_browser.url, 'batch'))
    batch=10

    >>> print(extract_url_parameter(user_browser.url, 'show'))
    show=untranslated

    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    1 ... 10  of 15 results

    >>> print_shown_messages(user_browser, contents)
    132: '(no translation yet)'
    133: '(no translation yet)'
    135: '(no translation yet)'
    136: '(no translation yet)'
    137: '(no translation yet)'
    138: '(no translation yet)'
    139: '(no translation yet)'
    140: '(no translation yet)'
    141: '(no translation yet)'
    142: '(no translation yet)'

Only the first 10 messages were shown. No Privileges Person views the
next page of messages to confirm the three remaining messages show.

    >>> user_browser.getLink('Next').click()
    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    11 ... 15  of 15 results

    >>> print_shown_messages(user_browser, contents)
    146: '(no translation yet)'
    148: '(no translation yet)'
    149: '(no translation yet)'
    150: '(no translation yet)'
    151: '(no translation yet)'

In the case of the 'Untranslated' filter, users can change the set of
filtered messages by making updates to messages. No Privileges Person
decides to use the 'Untranslated' filter to locate messages that need
translations into Australian English.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/'
    ...     '+source/evolution/+pots/evolution-2.2/en_AU/+translate')
    >>> user_browser.getControl(name='show', index=1).value = ['untranslated']
    >>> user_browser.getControl('Change').click()
    >>> print(user_browser.title)
    English (Australia) (en_AU) : Template ...evolution-2.2... :
    Hoary (5.04) : Translations : evolution package : Ubuntu

    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    1 ... 10  of 22 results

    >>> user_browser.getControl(
    ...     name='msgset_130_en_AU_translation_0_radiobutton').value = [
    ...         'msgset_130_en_AU_translation_0_new']
    >>> user_browser.getControl(
    ...     name='msgset_130_en_AU_translation_0_new').value = 'addressbook'
    >>> user_browser.getControl('Save & Continue').click()

The batch of 'Untranslated' messages was decremented by 1. No Privileges
Person can see that the next page of messages starts on 10, not 11, and
that there are 21 untranslated messages.

    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    10 ... 19  of 21 results

When No Privileges Person returns to the previous page, they can see the
first 10 untranslated messages. The message is translated is not
displayed.

    >>> user_browser.getLink("Previous").click()
    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    1 ... 10  of 21 results

    >>> print(find_tag_by_id(
    ...     user_browser.contents, 'msgset_130_en_AU_translation_0'))
    None

Projects can restrict translation to privileged users. The messages that
No Privileges Person adds to upstream Evolution are then taken as
suggestions, not translations. Their changes do not change the total
number of untranslated messages; they do not affect the batch
navigation.

    >>> from zope.component import getUtility
    >>> from lp.testing import login, logout
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> from lp.translations.interfaces.translator import ITranslatorSet

    # Evolution uses Restricted mode, so a translation without reviewer
    # is closed.  Assign an en_AU reviewer to active the translation.

    >>> login('foo.bar@canonical.com')
    >>> evolution = getUtility(IProductSet).getByName('evolution')
    >>> evolution_translation_group = evolution.translationgroup
    >>> ozzie_english =  getUtility(ILanguageSet)['en_AU']
    >>> foobar = getUtility(IPersonSet).getByName('name16')
    >>> translator_set = getUtility(ITranslatorSet)
    >>> foo_bar_translator = translator_set.new(
    ...     translationgroup=evolution_translation_group,
    ...     language=ozzie_english, translator=foobar)
    >>> logout()

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/'
    ...     'evolution/trunk/+pots/evolution-2.2/en_AU/+translate')
    >>> user_browser.getControl(name='show', index=1).value = ['untranslated']
    >>> user_browser.getControl('Change').click()
    >>> print(user_browser.title)
    English (Australia) (en_AU) : Template ...evolution-2.2... :
    Series trunk : Translations : Evolution

    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    1 ... 10  of 22 results

    >>> user_browser.getControl(
    ...     name='msgset_1_en_AU_translation_0_new_checkbox').value = True
    >>> user_browser.getControl(
    ...     name='msgset_1_en_AU_translation_0_new').value = 'fnord'
    >>> user_browser.getControl('Save & Continue').click()

No Privileges Person can see that the number of untranslated messages
has not changed, and that they are seeing messages 11 though 20.

    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    11 ... 20  of 22 results

They return to the previous page to check that their suggestion of 'fnord'
was accepted.

    >>> user_browser.getLink('Previous').click()
    >>> contents = find_main_content(user_browser.contents)
    >>> contents.find(text='fnord').parent
    <div ... id="msgset_1_en_AU_suggestion_..._0" lang="en-AU">fnord</div>


Messages changed in Ubuntu
..........................

No Privileges Person can see entries which have changed in Ubuntu.
There is only one message in the batch.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/'
    ...     '+source/evolution/+pots/evolution-2.2/es/+translate')
    >>> user_browser.getControl(name='show', index=1).displayValue = [
    ...     'changed in Ubuntu']
    >>> user_browser.getControl('Change').click()
    >>> print(extract_url_parameter(user_browser.url, 'batch'))
    batch=10

    >>> print(extract_url_parameter(user_browser.url, 'show'))
    show=changed_in_ubuntu

    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    1 ... 1  of 1 result

    >>> print_shown_messages(user_browser, contents)
    134: '<samp> </samp>caratas'

Now that the messages are filtered, there is no Next link, since there
is only one page of messages. If No Privileges Person submits the form,
the browser is redirected to the first batch.

    >>> user_browser.getControl('Save & Continue').click()
    >>> print(extract_url_parameter(user_browser.url, 'batch'))
    batch=10

    >>> print(extract_url_parameter(user_browser.url, 'show'))
    show=changed_in_ubuntu

    >>> print_shown_messages(user_browser)
    134: '<samp> </samp>caratas'


Messages with new suggestions
.............................

No Privileges Person chooses to view messages with new suggestions
submitted after they were last reviewed. There is only one message in
the batch.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/'
    ...     '+source/evolution/+pots/evolution-2.2/es/+translate')
    >>> user_browser.getControl(name='show', index=1).displayValue = [
    ...     'with new suggestions']
    >>> user_browser.getControl('Change').click()
    >>> print(extract_url_parameter(user_browser.url, 'batch'))
    batch=10

    >>> print(extract_url_parameter(user_browser.url, 'show'))
    show=new_suggestions

    >>> print_shown_messages(user_browser)
    134: '<samp> </samp>caratas'

No Privileges Person decides to dismiss the suggestions by providing a
better translation.

    >>> user_browser.getControl(
    ...     name='msgset_134_es_translation_0_radiobutton').value = [
    ...         'msgset_134_es_translation_0_new']
    >>> user_browser.getControl(
    ...     name='msgset_134_es_translation_0_new').value = 'tarjetas'
    >>> user_browser.getControl('Save & Continue').click()

Since this was the only suggestion and No Privileges Person has reviewed
it, the filter for new suggestions is empty now.

    >>> description = first_tag_by_class(user_browser.contents,
    ...     'documentDescription')
    >>> print(extract_text(description))
    There are no messages that match this filtering.


Invalid show option values
--------------------------

There was once a filter option called need_review.  It no longer exists,
but is quietly accepted.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/'
    ...     '+source/evolution/+pots/evolution-2.2/es/+translate'
    ...     '?show=need_review')

The page will actually show the "all" filter.

    >>> user_browser.getControl(name='show', index=1).displayValue
    ['all items']


Batch parameters when changing filters
--------------------------------------

When the filter changes, the batch is reset to the start of the set of
messages, while preserving the batch size. No Privileges Person can see
the batch header when they switch the filter to show 'untranslated'
message; they are seeing the first batch.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/'
    ...     '+source/evolution/+pots/evolution-2.2/es/+translate')
    >>> user_browser.getLink('Last').click()
    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    21 ... 22  of 22 results

    >>> user_browser.getControl(name='show', index=1).value = ['untranslated']
    >>> user_browser.getControl('Change').click()
    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    1 ... 10  of 15 results


Filters and error display
-------------------------

When there are errors in translations that No Privileges Person submits,
they see a general error message at the top of the page, plus individual
error messages for the individual problematic translations.

The error page shows the same messages that the user submitted for: it
is the same batch, shown with the same filter (see bug 112308).

No Privileges Person submits a bad translation, one that lacks
conversion specifications the original message has, and is shown an
error.

    >>> print(find_tag_by_id(
    ...     user_browser.contents, 'msgset_142_singular').decode_contents())
    Migrating ...%s...

    >>> user_browser.getControl(
    ...     name='msgset_142_es_translation_0_radiobutton').value = [
    ...         'msgset_142_es_translation_0_new']
    >>> user_browser.getControl(
    ...     name='msgset_142_es_translation_0_new').value = ('Migrando...')
    >>> user_browser.getControl(name='submit_translations').click()

The exact same batch of messages is shown again, but with the error.

    >>> user_browser.getControl(name='show', index=1).value
    ['untranslated']

    >>> contents = find_main_content(user_browser.contents)
    >>> print_batch_header(contents)
    1 ... 10  of 15 results

    >>> print_shown_messages(user_browser, contents)
    132: '(no translation yet)'
    133: '(no translation yet)'
    135: '(no translation yet)'
    136: '(no translation yet)'
    137: '(no translation yet)'
    138: '(no translation yet)'
    139: '(no translation yet)'
    140: '(no translation yet)'
    141: '(no translation yet)'
    142: '(no translation yet)'

    >>> for tag in find_tags_by_class(user_browser.contents, 'error'):
    ...     print(tag.decode_contents())
    There is an error in a translation you provided.
    Please correct it before continuing.
    ...Error in Translation:...
    number of format specifications in 'msgid' and 'msgstr' does not match
    ...


Filters and alternative languages
---------------------------------

Handling of http parameters gets a bit more complex when forms are
posted. Nonetheless users can submit translations while combining
message filters with alternative suggestion languages. No Privileges
Person submits Chinese translations using Spanish suggestions.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/'
    ...     '+source/evolution/+pots/evolution-2.2/zh_CN/+translate')
    >>> user_browser.getControl(name='show', index=1).value = ['untranslated']
    >>> user_browser.getControl('Change').click()
    >>> user_browser.getControl(name='field.alternative_language').getControl(
    ...     user_browser.toStr('Spanish (es)')).selected = True
    >>> user_browser.getControl('Change').click()

    >>> user_browser.getControl(
    ...     name='msgset_130_zh_CN_translation_0_radiobutton').value = [
    ...         'msgset_130_zh_CN_translation_0_new']
    >>> user_browser.getControl(
    ...     name='msgset_130_zh_CN_translation_0_new').value = 'Chinese!'
    >>> user_browser.getControl(name='submit_translations').click()

When they return to the first page of messages, they are still shown Spanish
suggestions.

    >>> user_browser.getLink("Previous").click()

    >>> text = extract_text(find_main_content(user_browser.contents))
    >>> print(text)
    Translating...
    English: current addressbook folder
    Current Chinese (China): (no translation yet)
    Suggestions:
    carpeta de libretas de direcciones actual
    Spanish
    ...
