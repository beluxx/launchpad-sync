Checks that an empty translation is not checked with pygettextpo

    >>> browser = setupBrowser(auth='Basic carlos@canonical.com:test')
    >>> browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'evolution/+pots/evolution-2.2/es/+translate?start=12&batch=1')

The msgid for msgset_142 uses a format string ('%s') and that means that the
translation should use it too. If the translation is empty, our validation
system should not detect that as an error.

    >>> print(browser.contents)
    <!DOCTYPE...
    ...Migrating `...%s...':...

We set the translation empty:

    >>> browser.getControl(
    ...     name='msgset_142_es_translation_0_radiobutton').value = [
    ...          'msgset_142_es_translation_0_new']
    >>> browser.getControl(name='msgset_142_es_translation_0_new').value = ''

Submit the form.

    >>> browser.getControl(name='submit_translations').click()

We should be redirected to the next page because the validation didn't get
it as an error.

    >>> print(browser.url)  # noqa
    http://translations.launchpad.test/ubuntu/hoary/+source/evolution/+pots/evolution-2.2/es/+translate?batch=1&memo=13&start=13
