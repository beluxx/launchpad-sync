Here is the story for translating a single message
==================================================

Here we are going to check the basic behaviour of the translation form
when we render just one message with all available information for it.

The suggestive-templates cache needs to be up to date.

    >>> from zope.component import getUtility
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet

    >>> login(ANONYMOUS)
    >>> utility = getUtility(IPOTemplateSet)
    >>> dummy = utility.populateSuggestivePOTemplatesCache()
    >>> logout()


Getting there
-------------

First, we need to be sure that anonymous users are able to browse
translations but are unable to actually change them.

    >>> browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/evolution-2.2/es/5')

We are in read only mode, so there shouldn't be any textareas:

    >>> main_content = find_tag_by_id(
    ...     browser.contents, 'messages_to_translate')
    >>> for textarea in main_content.find_all('textarea'):
    ...     raise AssertionError('Found textarea:\n%s' % textarea)

Neither any input widget:

    >>> for input in main_content.find_all('input'):
    ...     raise AssertionError('Found input:\n%s' % input)

As an anynoymous user you will have access to the download and details
pages for the pofile this message belongs to. The link to upload page
and the link for switching between translator and reviewer working mode
will not be displayed in that list.

    >>> nav = find_tag_by_id(browser.contents, 'nav-pofile-subpages')
    >>> print(extract_text(nav))
    Download translation Translation details

Download translations and Translation details should linked to the
proper pages

  >> print(nav.getLink("Download translation").url)
  https://.../hoary/+source/evolution/+pots/evolution-2.2/es/+export
  >> print(nav.getLink("Translation details").url)
  https://.../hoary/+source/evolution/+pots/evolution-2.2/es/+details

Let's log in.

    >>> browser = setupBrowser(auth='Basic carlos@canonical.com:test')

Now, we are going to test common parts of the navigation.

The main page for a pomsgset object should redirect us to the
translation form.

    >>> browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/evolution-2.2/es/1')

When we are on the first message, we should be 100% sure that the
'First' and 'Previous' links are hidden and 'Next' and 'Last' are the
right ones.

    >>> browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/evolution-2.2/es/1/+translate')

    >>> browser.getLink('First')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> browser.getLink('Prev')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> next = browser.getLink('Next')
    >>> print(next.url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/2/+translate

    >>> print(browser.getLink('Last').url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/22/+translate

And the link to the IPOFile view should be there too:

    >>> zoom_link = browser.getLink(id="zoom-out")
    >>> print(zoom_link.url)
    http://.../+source/evolution/+pots/evolution-2.2/es/+translate?start=0

when we choose the next entry, all links should appear.

    >>> next.click()
    >>> print(browser.getLink('First').url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/1/+translate

    >>> print(browser.getLink('Previous').url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/1/+translate

    >>> print(browser.getLink('Next').url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/3/+translate

    >>> last = browser.getLink('Last')
    >>> print(last.url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/22/+translate

And the link to the IPOFile view should be there too:

    >>> zoom_link = browser.getLink(id="zoom-out")
    >>> print(zoom_link.url)
    http://.../+source/evolution/+pots/evolution-2.2/es/+translate?start=1

And the last one.

    >>> last.click()
    >>> print(browser.getLink('First').url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/1/+translate

    >>> prev = browser.getLink('Previous')
    >>> print(prev.url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/21/+translate

    >>> browser.getLink('Next')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> browser.getLink('Last')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

And the link to the IPOFile view should be there too:

    >>> zoom_link = browser.getLink(id="zoom-out")
    >>> print(zoom_link.url)
    http://.../+source/evolution/+pots/evolution-2.2/es/+translate?start=21

Let's test the ones at the end of the form.

    >>> prev.click()
    >>> print(browser.getLink('First').url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/1/+translate

    >>> print(browser.getLink('Previous').url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/20/+translate

    >>> print(browser.getLink('Next').url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/22/+translate

    >>> print(browser.getLink('Last').url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/22/+translate

As a translation admin you will have access to the download and details
pages for the pofile this message belongs to. In the same time you have
access to the link for switching between translator and reviewer working
mode

    >>> nav = find_tag_by_id(browser.contents, 'nav-pofile-subpages')
    >>> print(extract_text(nav))
    Download translation Translation details
    Reviewer mode (What's this?)

All those links should linked the proper pages

  >> print(nav.getLink("Download translation").url)
  https://.../hoary/+source/evolution/+pots/evolution-2.2/es/+export
  >> print(nav.getLink("Upload translation").url)
  https://.../hoary/+source/evolution/+pots/evolution-2.2/es/+upload
  >> print(nav.getLink("Translation details").url)
  https://.../hoary/+source/evolution/+pots/evolution-2.2/es/+details

Now, we are going to check a message submission.

    >>> browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/evolution-2.2/es/13/+translate')

Check that the message #13 is without translation.

First what we represent in the form when there is no translation:

    >>> print(find_tag_by_id(
    ...     browser.contents, 'msgset_142').decode_contents())
    13.
    <input name="msgset_142" type="hidden"/>

    >>> print(find_tag_by_id(
    ...     browser.contents, 'msgset_142_singular').decode_contents())
    Migrating `<code>%s</code>':

    >>> print(find_tag_by_id(
    ...     browser.contents,
    ...     'msgset_142_es_translation_0').decode_contents())
    (no translation yet)

And also, we don't get anyone as the Last translator because there is no
translation at all ;-)

    >>> find_tag_by_id(browser.contents, 'translated_and_reviewed_by') is None
    True

    >>> find_tag_by_id(browser.contents, 'translated_by') is None
    True

    >>> find_tag_by_id(browser.contents, 'reviewed_by') is None
    True

Let's submit an invalid value for this message #13.

    >>> browser.getControl(
    ...     name='msgset_142_es_translation_0_radiobutton').value = [
    ...         'msgset_142_es_translation_0_new']
    >>> browser.getControl(
    ...     name='msgset_142_es_translation_0_new').value = 'foo %i'
    >>> browser.getControl(name='submit_translations').click()
    >>> print(browser.url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/13/+translate

    >>> for tag in find_tags_by_class(browser.contents, 'error'):
    ...     print(tag)
    <div class="error message">There is an error in the translation you
      provided. Please correct it before continuing.</div>
    <tr class="error translation">
      <th colspan="3">
        <strong>Error in Translation:</strong>
      </th>
      <td></td>
      <td>
        <div>
          format specifications in 'msgid' and 'msgstr' for argument 1 are not
          the same
        </div>
      </td>
    </tr>

The message is still without translation:

    >>> print(find_tag_by_id(
    ...     browser.contents, 'msgset_142').decode_contents())
    13.
    <input name="msgset_142" type="hidden"/>

    >>> print(find_tag_by_id(
    ...     browser.contents, 'msgset_142_singular').decode_contents())
    Migrating `<code>%s</code>':

    >>> print(find_tag_by_id(
    ...     browser.contents,
    ...     'msgset_142_es_translation_0').decode_contents())
    (no translation yet)

And now a good submit.

    >>> browser.getControl(
    ...     name='msgset_142_es_translation_0_radiobutton').value = [
    ...         'msgset_142_es_translation_0_new']
    >>> browser.getControl(
    ...     name='msgset_142_es_translation_0_new').value = 'foo %s'
    >>> browser.getControl(name='submit_translations').click()

We moved to the next message, that means this submission worked.

    >>> print(browser.url)
    http:/.../hoary/+source/evolution/+pots/evolution-2.2/es/14/+translate

Now, it has the submitted value.

    >>> browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/evolution-2.2/es/13/+translate')

Check that the message #13 has the new value we submitted.

    >>> print(find_tag_by_id(
    ...     browser.contents, 'msgset_142').decode_contents())
    13.
    <input name="msgset_142" type="hidden"/>

    >>> print(find_tag_by_id(
    ...     browser.contents, 'msgset_142_singular').decode_contents())
    Migrating `<code>%s</code>':

    >>> print(find_tag_by_id(
    ...     browser.contents,
    ...     'msgset_142_es_translation_0').decode_contents())
    foo <code>%s</code>

And now, we get the translator and reviewer, who happen to be the same
in this instance.

    >>> find_tag_by_id(browser.contents, 'translated_and_reviewed_by') is None
    False

    >>> find_tag_by_id(browser.contents, 'translated_by') is None
    True

    >>> find_tag_by_id(browser.contents, 'reviewed_by') is None
    True

In some other cases where translator and reviewer are different, they
are both shown separately:

    >>> browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/man/es/1/+translate')
    >>> find_tag_by_id(browser.contents, 'translated_and_reviewed_by') is None
    True

    >>> find_tag_by_id(browser.contents, 'translated_by') is None
    False

    >>> find_tag_by_id(browser.contents, 'reviewed_by') is None
    False

Now, we will check suggestions in this form.

    >>> browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/evolution-2.2/es/14/+translate')

Check that suggestions come in from other contexts:

    >>> "Suggested in" in browser.contents
    True

    >>> find_tag_by_id(browser.contents, 'msgset_143_es_suggestion_697_0')
    <...suggestion added by a non-editor for a multiline entry...>

Check that no other suggestions are presented (since no others are
relevant for this message):

    >>> "Suggested by" in browser.contents
    False

    >>> "Used in" in browser.contents
    False

Check for the translator note:

    >>> note = "This is an example of commenttext for a multiline"
    >>> note in browser.contents
    True

Also check that the alternative language selection is working:

    >>> browser.getControl(name='field.alternative_language').getControl(
    ...     'Catalan (ca)').click()
    >>> browser.getControl('Change').click()
    >>> browser.url
    'http:/...field.alternative_language=ca...'

If we specify more than one alternative language in the URL, we get an
UnexpectedFormData exception:

    >>> browser.open(
    ...  'http://translations.launchpad.test/ubuntu/hoary/+source/evolution/'
    ...  '+pots/evolution-2.2/es/14/+translate?field.alternative_language=ca&'
    ...  'field.alternative_language=es')
    Traceback (most recent call last):
    ...
    lp.app.errors.UnexpectedFormData: You specified...

Let's see what happens when we do a submission with a lock_timestamp
older than the review date for current translation.

First, we get a browser instance that will be the last one submitting
the changes.

    >>> slow_submission = setupBrowser(auth='Basic carlos@canonical.com:test')
    >>> slow_submission.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/evolution-2.2/es/14/+translate')
    >>> import transaction
    >>> transaction.commit()

Now, we get another instance that will be submitted before
'slow_submission'.

    >>> fast_submission = setupBrowser(auth='Basic carlos@canonical.com:test')
    >>> fast_submission.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/evolution-2.2/es/14/+translate')

Let's change the translation.

    >>> fast_submission.getControl(
    ...     name='msgset_143_es_translation_0_radiobutton').value = [
    ...         'msgset_143_es_translation_0_new']
    >>> fast_submission.getControl(
    ...     name='msgset_143_es_translation_0_new').value = u'blah'

And submit it.

    >>> fast_submission.getControl(name='submit_translations').click()
    >>> print(fast_submission.url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/15/+translate

Now, we check that the translation we are going to add is not yet in the
form, so we can check later that it's added as a suggestion:

    >>> 'foo!!' in fast_submission.contents
    False

Now, we update the translation in slow_submission.

    >>> slow_submission.getControl(
    ...     name='msgset_143_es_translation_0_radiobutton').value = [
    ...         'msgset_143_es_translation_0_new']
    >>> slow_submission.getControl(
    ...     name='msgset_143_es_translation_0_new').value = u'foo!!'

We submit it

    >>> slow_submission.getControl(name='submit_translations').click()
    >>> print(slow_submission.url)
    http://.../hoary/+source/evolution/+pots/evolution-2.2/es/14/+translate

    >>> for tag in find_tags_by_class(slow_submission.contents, 'error'):
    ...     print(tag)
    <div class="error message">There is an error in the translation you
      provided. Please correct it before continuing.</div>
    <tr class="error translation">
      <th colspan="3">
        <strong>Error in Translation:</strong>
      </th>
      <td></td>
      <td>
        <div>
          This translation has changed since you last saw it.  To avoid
          accidentally reverting work done by others, we added your
          translations as suggestions.  Please review the current values.
        </div>
      </td>
    </tr>

Also, we should still have previous translation:

    >>> print(find_tag_by_id(
    ...     slow_submission.contents, 'msgset_143').decode_contents())
    14.
    <input name="msgset_143" type="hidden"/>

    >>> print(find_tag_by_id(
    ...     slow_submission.contents,
    ...     'msgset_143_singular').decode_contents())
    The location and hierarchy of the Evolution contact...

    >>> print(find_tag_by_id(
    ...     slow_submission.contents,
    ...     'msgset_143_es_translation_0').decode_contents())
    blah

But also, the new one should appear in the form.

    >>> import re
    >>> elements = find_main_content(slow_submission.contents).find_all(
    ...     True, {'id': re.compile(r'^msgset_143_es_suggestion_\d+_0$')})
    >>> for element in elements:
    ...     print(element.decode_contents())
    La ubicación ...
    Tenga paciencia ...
    foo!!
    This is a suggestion ...
    It should work! :-P


Unreviewed translations
-----------------------

If there is a message which has a translation, but no reviewer (eg.
uploaded from a package), it only shows the translator, and not
reviewer.

    >>> browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'mozilla/+pots/pkgconf-mozilla/de/1/+translate')
    >>> print(extract_text(
    ...     find_tag_by_id(browser.contents, "translated_by").parent))
    Translated by Helge Kreutzmann on 2005-05-06

    >>> print(find_tag_by_id(browser.contents, "reviewed_by"))
    None

    >>> print(find_tag_by_id(browser.contents, "translated_and_reviewed_by"))
    None


Translating context
-------------------

Going to a translation page for a message with the context displays the
context.

    >>> browser.open(
    ...     'http://translations.launchpad.test/alsa-utils/trunk/+pots/'
    ...     'alsa-utils/sr/+translate')
    >>> print(extract_text(find_tag_by_id(
    ...     browser.contents, "msgset_198_context").parent))
    Something

We can change a translation for messages with context.

    >>> browser.getControl(
    ...     name='msgset_198_sr_translation_0_radiobutton').value = [
    ...         'msgset_198_sr_translation_0_new']
    >>> browser.getControl(
    ...     name='msgset_198_sr_translation_0_new').value = u'blah'

And submit it.

    >>> browser.getControl(name='submit_translations').click()
    >>> print(browser.url)
    http://.../alsa-utils/trunk/+pots/alsa-utils/sr/+translate

And the translation is now updated.

    >>> print(extract_text(
    ...     find_tag_by_id(browser.contents, "msgset_198_sr_translation_0")))
    blah


Empty imported messages
-----------------------

Empty messages coming from import are not shown as 'packaged'
suggestions, even if we keep them to know when were they deactivated.

Initially, a message has a non-empty packaged translation.

    >>> browser.open('http://translations.launchpad.test/ubuntu/hoary/'
    ...              '+source/evolution/+pots/evolution-2.2/es/5/+translate')
    >>> packaged = find_tag_by_id(browser.contents, 'msgset_134_other')
    >>> print(extract_text(packaged))
    In upstream: tarjetas

First, we look for an existing imported translation in evolution PO file
in Ubuntu Hoary.  We can't modify "imported" messages through web UI, so
we do it directly in the database.

    >>> from zope.component import getUtility
    >>> from lp.testing import login, logout
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet)
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> from lp.translations.interfaces.side import TranslationSide
    >>> login("carlos@canonical.com")
    >>> carlos = getUtility(IPersonSet).getByName('carlos')

    >>> evo_sourcepackagename = getUtility(ISourcePackageNameSet)['evolution']
    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> hoary = ubuntu['hoary']
    >>> evo_potemplatesubset = getUtility(IPOTemplateSet).getSubset(
    ...     distroseries=hoary, sourcepackagename=evo_sourcepackagename)
    >>> evolution_potemplate = evo_potemplatesubset['evolution-2.2']
    >>> evolution_pofile = evolution_potemplate.getPOFileByLang('es')
    >>> potmsgset = evolution_potemplate.getPOTMsgSetByMsgIDText(' cards')
    >>> spanish = evolution_pofile.language

    >>> upstream_message = potmsgset.getCurrentTranslation(
    ...     evolution_potemplate, spanish,
    ...     side=TranslationSide.UPSTREAM)
    >>> for translation in upstream_message.translations:
    ...     print(translation)
    ... # doctest: -NORMALIZE_WHITESPACE
     tarjetas

We replace it with an empty, imported translation:

    >>> empty_upstream_message = factory.makeSuggestion(
    ...     potmsgset=potmsgset, pofile=evolution_pofile, translator=carlos,
    ...     translations={0: u''})
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(upstream_message).is_current_upstream = False
    >>> removeSecurityProxy(empty_upstream_message).is_current_upstream = True
    >>> for translation in empty_upstream_message.translations:
    ...     print(translation)
    <BLANKLINE>

    >>> logout()

If we browse to the page for this message, we won't be able to see a
packaged translation anymore.

    >>> browser.open('http://translations.launchpad.test/ubuntu/hoary/'
    ...              '+source/evolution/+pots/evolution-2.2/es/5/+translate')
    >>> packaged = find_tag_by_id(browser.contents, 'msgset_134_other')

Also, the page now displays a "(not translated yet)" message.

    >>> print(extract_text(packaged))
    In upstream: (not translated yet)


Shared and diverged translations
--------------------------------

We create a POFile with one shared translation, which we want to diverge
from.

    >>> login('foo.bar@canonical.com')
    >>> pofile = factory.makePOFile('sr')
    >>> potmsgset = factory.makePOTMsgSet(pofile.potemplate, sequence=1)
    >>> translationmessage = factory.makeCurrentTranslationMessage(
    ...     potmsgset=potmsgset, pofile=pofile,
    ...     translations=[u"shared translation"])
    >>> translationmessage.setPOFile(pofile)
    >>> message_url = '/'.join(
    ...     [canonical_url(translationmessage, rootsite='translations'),
    ...      '+translate'])
    >>> pofile_url = (
    ...     canonical_url(pofile, rootsite='translations') + '/+translate')
    >>> logout()

On the POFile +translate page, no divergence check box is shown.

    >>> browser.open(pofile_url)
    >>> diverge_check_box = browser.getControl(
    ...     name='msgset_%d_diverge' % (potmsgset.id))
    Traceback (most recent call last):
    ...
    LookupError: name...

However, once we zoom in on the message, check box to diverge a
translation is shown.

    >>> browser.open(message_url)
    >>> diverge_check_box = browser.getControl(
    ...     name='msgset_%d_diverge' % (potmsgset.id))
    >>> diverge_check_box.value
    []

We can check the box to add a new translation and diverge it.

    >>> diverge_check_box.value = ['diverge_translation']
    >>> html_id = 'msgset_%d_%s_translation_0' % (
    ...     potmsgset.id, pofile.language.code)
    >>> browser.getControl(name=html_id + '_radiobutton').value = [
    ...         html_id + '_new']
    >>> browser.getControl(name=html_id + '_new').value = 'diverged'
    >>> browser.getControl(name='submit_translations').click()

Since we've got only one message, this page is reloaded, and a "Shared"
translation is shown separately, and there is no check box to diverge a
translation.

    >>> diverge_check_box = browser.getControl(
    ...     name='msgset_%d_diverge' % (potmsgset.id))
    Traceback (most recent call last):
    ...
    LookupError: name...

    >>> shared_html_id = 'msgset_%d_%s_suggestion_%d_0' % (
    ...     potmsgset.id, pofile.language.code, translationmessage.id)
    >>> shared_message_tag = find_tag_by_id(browser.contents, shared_html_id)
    >>> print(extract_text(shared_message_tag))
    shared translation

    >>> print(extract_text(find_tag_by_id(browser.contents, html_id)))
    diverged
