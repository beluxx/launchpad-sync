Translations Relicensing
========================

When Karl visits +translate page for the first time, he is sent
to a form to indicate whether he agrees to license his translations
under the revised BSD licence.

    >>> browser = setupBrowser(auth="Basic karl@canonical.com:test")
    >>> browser.open(
    ...     "http://translations.launchpad.test/alsa-utils/trunk/"
    ...     "+pots/alsa-utils/es/+translate"
    ... )
    >>> browser.url
    'http://translations.launchpad.test/~karl/+licensing?back_to=...'

Karl realises that he is not on the translate page, he can see that
that this page has information about relicensing.

    >>> print(browser.title)
    Licensing : Translations...
    >>> print(extract_text(find_main_content(browser.contents)))
    Translations licensing by Karl Tilbury
    ...

Karl is asked whether he wants to license his translations.

    >>> radiobuttons = browser.getControl(name="field.allow_relicensing")

The default choice is to permit relicensing.

    >>> radiobuttons.value
    ['BSD']

Karl chooses "no".

    >>> radiobuttons.value = ["REMOVE"]
    >>> browser.getControl("Confirm").click()

Karl sees a notice acknowledging his choice.

    >>> print_feedback_messages(browser.contents)
    We respect your choice...

He's also forwarded back to the Spanish alsa-utils translations page.

    >>> browser.url
    'http://translations.launchpad.test/...+pots/alsa-utils/es/+translate'

However, this page is now read-only for Karl, and there are no textareas
nor input boxes available.

    >>> main_content = find_tag_by_id(
    ...     browser.contents, "messages_to_translate"
    ... )
    >>> for textarea in main_content.find_all("textarea"):
    ...     print("Found textarea:\n%s" % textarea)
    ...

    >>> for input in main_content.find_all("input"):
    ...     print("Found input:\n%s" % input)
    ...

Karl changes his mind. He returns to the licensing page.

    >>> browser.open("http://translations.launchpad.test/~karl/")
    >>> browser.getLink("Translations licensing").click()
    >>> browser.url
    'http://translations.launchpad.test/~karl/+licensing'
    >>> print(browser.title)
    Licensing : Translations...

Karl sees that the current value is 'no', which he set before.

    >>> radiobuttons = browser.getControl(name="field.allow_relicensing")
    >>> print(radiobuttons.value)
    ['REMOVE']

He changes it again.

    >>> radiobuttons.value = ["BSD"]
    >>> browser.getControl("Confirm").click()

    >>> print_feedback_messages(browser.contents)
    Thank you for BSD-licensing your translations.

Karl can now browse to a +translate page without being forwarded.

    >>> browser.open(
    ...     "http://translations.launchpad.test/alsa-utils/trunk/"
    ...     "+pots/alsa-utils/es/+translate"
    ... )
    >>> browser.url
    'http://.../alsa-utils/trunk/+pots/alsa-utils/es/+translate'
    >>> print(browser.title)
    Spanish (es) : Template ...alsa-utils... : Series trunk :
    Translations : alsa-utils


Permissions
-----------

If another logged-in user comes across Karl's translations page, they see
no link to change Karl's licensing choice.

    >>> user_browser.open("http://translations.launchpad.test/~karl/")
    >>> user_browser.getLink("Translations licensing")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

Typing in the URL directly doesn't work either.

    >>> user_browser.open(
    ...     "http://translations.launchpad.test/~karl/+licensing"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...
