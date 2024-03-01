In Launchpad Translations, new lines matter with textareas.

This test checks that we don't miss or add extra new lines. Changes to this
test are quite fragile because we depend a lot on how new lines are handled
in textareas by web browsers. Seems like they strip any new line character
after the opening <textarea> tag and thus, we must add such extra new line
always, to prevent that content starting with new line characters lose it on
submission. For more details, please see
https://bugzilla.mozilla.org/show_bug.cgi?id=299009

    >>> def print_tags(browser, tags):
    ...     """Print [tags] from browser.contents. End each with '--'."""
    ...     soup = find_main_content(browser.contents)
    ...     for tag in soup.find_all(attrs={"id": tags}):
    ...         print("%s\n--\n" % tag.decode_contents())
    ...

    >>> browser = setupBrowser(auth="Basic carlos@canonical.com:test")
    >>> browser.open(
    ...     "http://translations.launchpad.test/ubuntu/hoary/+source/"
    ...     "evolution/+pots/evolution-2.2/es/+translate?start=19&batch=1"
    ... )

We can see that the message we are interested in is not translated.

    >>> print_tags(
    ...     browser,
    ...     [
    ...         "msgset_149",
    ...         "msgset_149_singular",
    ...         "msgset_149_es_translation_0",
    ...     ],
    ... )
    20.
    <input name="msgset_149" type="hidden"/>
    --
    Please select a key size in bits.  The cipher you have chosen...
    --
    (no translation yet)
    --

Now, we submit some text with new lines before and after the text, the
answer should have exactly those strings.

    >>> browser.getControl(
    ...     name="msgset_149_es_translation_0_radiobutton"
    ... ).value = ["msgset_149_es_translation_0_new"]
    >>> browser.getControl(name="msgset_149_es_translation_0_new").value = (
    ...     "\r\nfoo\r\n\r\n"
    ... )
    >>> browser.getControl(name="submit_translations").click()
    >>> print(browser.url)  # noqa
    http://translations.launchpad.test/ubuntu/hoary/+source/evolution/+pots/evolution-2.2/es/+translate?start=19&batch=1
    >>> print(
    ...     find_tag_by_id(
    ...         browser.contents, "msgset_149_es_translation_0_new"
    ...     )
    ... )
    <textarea ... name="msgset_149_es_translation_0_new"...>

    foo

    </textarea>

And finally, a line that does not start with a new line so we are sure we
don't get extra whitespaces. The NORMALIZE_WHITESPACE must be there, if you
change the test, to be 100% sure that the textarea content is the right one.

    >>> browser.getControl(
    ...     name="msgset_149_es_translation_0_radiobutton"
    ... ).value = ["msgset_149_es_translation_0_new"]
    >>> browser.getControl(name="msgset_149_es_translation_0_new").value = (
    ...     "foo"
    ... )
    >>> browser.getControl(name="submit_translations").click()
    >>> print(browser.url)  # noqa
    http://translations.launchpad.test/ubuntu/hoary/+source/evolution/+pots/evolution-2.2/es/+translate?start=19&batch=1
    >>> print(
    ...     find_tag_by_id(
    ...         browser.contents, "msgset_149_es_translation_0_new"
    ...     )
    ... )
    ... # doctest: -NORMALIZE_WHITESPACE
    <textarea ... name="msgset_149_es_translation_0_new"...>
    foo</textarea>

Now, Check that even though the user forgot the trailing new line char,
Launchpad adds it automatically.

    >>> browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/es/+translate?start=21&batch=1"
    ... )
    >>> browser.getControl(
    ...     name="msgset_165_es_translation_0_radiobutton"
    ... ).value = ["msgset_165_es_translation_0_new"]
    >>> browser.getControl(name="msgset_165_es_translation_0_new").value = (
    ...     b"%s: la opcion \xc2\xab%s\xc2\xbb es ambigua"
    ... )
    >>> browser.getControl(name="submit_translations").click()

We were redirected to the next form, the translation was accepted.

    >>> print(browser.url)  # noqa
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-2.2/es/+translate?batch=1

Get previous page to check that the save translation is the right one.

    >>> browser.getLink("Last").click()

And, as we can see, we get the trailing new line char

    >>> print_tags(
    ...     browser,
    ...     [
    ...         "msgset_165",
    ...         "msgset_165_singular",
    ...         "msgset_165_es_translation_0",
    ...     ],
    ... )
    23.
    <input name="msgset_165" type="hidden"/>
    --
    <code>%s</code>: option `<code>%s</code>' is ambiguous...
    --
    <code>%s</code>: la opcion «<code>%s</code>» es ambigua<img alt=""
    src="/@@/translation-newline"/><br/>
    --

Now, we do the right submit, with one trailing new line...

    >>> browser.getControl(
    ...     name="msgset_165_es_translation_0_radiobutton"
    ... ).value = ["msgset_165_es_translation_0_new"]
    >>> browser.getControl(name="msgset_165_es_translation_0_new").value = (
    ...     b"%s: la opcion \xc2\xab%s\xc2\xbb es ambigua\r\n"
    ... )
    >>> browser.getControl(name="submit_translations").click()

We were redirected to the next form, the translation was accepted.

    >>> print(browser.url)  # noqa
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-2.2/es/+translate?batch=1

Get previous page to check that the save translation is the right one.

    >>> browser.getLink("Last").click()

And, as we can see, we get the same output, just one trailing newline char.

    >>> print_tags(
    ...     browser,
    ...     [
    ...         "msgset_165",
    ...         "msgset_165_singular",
    ...         "msgset_165_es_translation_0",
    ...     ],
    ... )
    23.
    <input name="msgset_165" type="hidden"/>
    --
    <code>%s</code>: option `<code>%s</code>' is ambiguous...
    --
    <code>%s</code>: la opcion «<code>%s</code>» es ambigua<img alt=""
    src="/@@/translation-newline"/><br/>
    --

Last check, the user sends two new line chars instead of just one...

    >>> browser.getControl(
    ...     name="msgset_165_es_translation_0_radiobutton"
    ... ).value = ["msgset_165_es_translation_0_new"]
    >>> browser.getControl(name="msgset_165_es_translation_0_new").value = (
    ...     b"%s: la opcion \xc2\xab%s\xc2\xbb es ambigua\r\n\r\n"
    ... )
    >>> browser.getControl(name="submit_translations").click()

We were redirected to the next form, the translation was accepted.

    >>> print(browser.url)  # noqa
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-2.2/es/+translate?batch=1

Get previous page to check that the save translation is the right one.

    >>> browser.getLink("Last").click()

And Launchpad comes to the rescue and stores just one!

    >>> print_tags(
    ...     browser,
    ...     [
    ...         "msgset_165",
    ...         "msgset_165_singular",
    ...         "msgset_165_es_translation_0",
    ...     ],
    ... )
    23.
    <input name="msgset_165" type="hidden"/>
    --
    <code>%s</code>: option `<code>%s</code>' is ambiguous...
    --
    <code>%s</code>: la opcion «<code>%s</code>» es ambigua<img alt=""
    src="/@@/translation-newline"/><br/>
    --
