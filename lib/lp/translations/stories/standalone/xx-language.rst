

Languages view
==============

Here is the tale of languages. We will see how to create, find and edit
them.


Getting there
-------------

Launchpad Translations has a main page.

    >>> admin_browser.open('http://translations.launchpad.test/')

There we can find a link to browse and manage languages.

    >>> admin_browser.getLink('18 languages').click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/+languages


Adding new languages
--------------------

Following the link from the translations main page, there is a form to
add new languages.

    >>> admin_browser.getLink('Add new language').click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/+languages/+add

Which detects an attempt to create duplicate Languages, such as Spanish,
which is already registered:

    >>> browser.open('http://translations.launchpad.test/+languages/es')
    >>> print(browser.url)
    http://translations.launchpad.test/+languages/es

If someone tries to create a new language with the same language code,
the system detects it and warns the user.

    >>> admin_browser.getControl('The ISO 639').value = 'es'
    >>> admin_browser.getControl('English name').value = 'Foos'
    >>> admin_browser.getControl('Add').click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/+languages/+add

    >>> for tag in find_tags_by_class(admin_browser.contents, 'message'):
    ...     print(tag.decode_contents())
    There is 1 error.
    There is already a language with that code.

But, with a new language, it will succeed.

    >>> browser.open('http://translations.launchpad.test/+languages/foos')
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...

    >>> admin_browser.getControl('The ISO 639').value = 'foos'
    >>> admin_browser.getControl('English name').value = 'Foos'
    >>> admin_browser.getControl('Add').click()

And the system forwards us to its main page:

    >>> print(admin_browser.url)
    http://translations.launchpad.test/+languages/foos

A normal user will not be able to see or use the url to add languages.

    >>> user_browser.open('http://translations.launchpad.test/+languages')
    >>> print(user_browser.url)
    http://translations.launchpad.test/+languages

    >>> user_browser.getLink('Add new language')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/+languages/+add')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...


Searching for a language
------------------------

From the top languages page, anyone can find languages.

    >>> browser.open('http://translations.launchpad.test/+languages')
    >>> print(browser.url)
    http://translations.launchpad.test/+languages

    >>> text_search = browser.getControl(name='field.search_lang')
    >>> text_search.value = 'Spanish'
    >>> browser.getControl('Find language', index=0).click()
    >>> print(browser.url)  # noqa
    http://translations.launchpad.test/+languages/+index?field.search_lang=Spanish


Read language information
-------------------------

Following one of the found languages, we can see a brief information
about the selected language.

    >>> browser.getLink('Spanish').click()
    >>> print(browser.url)
    http://translations.launchpad.test/+languages/es

    >>> print(extract_text(find_portlet(browser.contents, 'Plural forms'
    ...     ).decode_contents()))
    Plural forms
    Spanish has 2 plural forms:
    Form 0 for 1.
    Form 1 for 0, 2, 3, 4, 5, 6...
    When ...

    >>> translationteams_portlet = find_portlet(
    ...     browser.contents, 'Translation teams')
    >>> print(translationteams_portlet)
    <...
    ...testing Spanish team...
    ...Just a testing team...

    >>> countries_portlet = find_portlet(browser.contents, 'Countries')
    >>> print(countries_portlet)
    <...
    ...Argentina...
    ...Bolivia...
    ...Chile...
    ...Colombia...
    ...Costa Rica...
    ...Dominican Republic...
    ...Ecuador...
    ...El Salvador...
    ...Guatemala...
    ...Honduras...
    ...Mexico...
    ...Nicaragua...
    ...Panama...
    ...Paraguay...
    ...Peru...
    ...Puerto Rico...
    ...Spain...
    ...United States...
    ...Uruguay...
    ...Venezuela...

    >>> topcontributors_portlet = find_portlet(
    ...     browser.contents, 'Top contributors')
    >>> print(topcontributors_portlet)
    <...
    ...Carlos Perelló Marín...

Our test sample data does not know about plural forms of
Abkhazian and about countries where this language is spoken.

We will see a note about missing plural forms and a link to Rosetta
add question page for informing Rosetta admin about the right plural
form.

    >>> browser.open('http://translations.launchpad.test/+languages/ab')
    >>> print(extract_text(find_portlet(browser.contents, 'Plural forms'
    ...     ).decode_contents()))
    Plural forms
    Unfortunately, Launchpad doesn't know the plural
    form information for this language...

    >>> print(browser.getLink(id='plural_question').url)
    http://answers.launchpad.test/launchpad/+addquestion

We will see a note that Launchpad does not know in which countries
this language is spoken and a link to add question page for informing
Rosetta admin about the countries where this page is officially spoken.

    >>> countries_portlet = find_portlet(browser.contents, 'Countries')
    >>> print(countries_portlet)
    <...
    Abkhazian is not registered as being spoken in any
    country...

    >>> print(browser.getLink(id='country_question').url)
    http://answers.launchpad.test/launchpad/+addquestion


Edit language information
-------------------------

Finally, there is the edit form to change language basic information.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/+languages/es')
    >>> print(user_browser.url)
    http://translations.launchpad.test/+languages/es

A plain user is not able to reach it.

    >>> user_browser.getLink('Administer')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/+languages/es/+admin')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

An admin, though, will see the link and will be able to edit it.

    >>> from lp.testing.pages import strip_label

    >>> admin_browser.open(
    ...     'http://translations.launchpad.test/+languages/es')
    >>> print(admin_browser.url)
    http://translations.launchpad.test/+languages/es

    >>> admin_browser.getLink('Administer').click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/+languages/es/+admin

    >>> print(admin_browser.getControl('ISO 639').value)
    es

    >>> print(admin_browser.getControl('English name').value)
    Spanish

    >>> print(admin_browser.getControl('Native name').value)

    >>> print(admin_browser.getControl('Number of plural forms').value)
    2

    >>> print(admin_browser.getControl('Plural form expression').value)
    n != 1

    >>> print(admin_browser.getControl('Visible').optionValue)
    on

    >>> print(admin_browser.getControl('Text direction').displayValue)
    ['Left to Right']

    >>> control = admin_browser.getControl(name='field.countries')
    >>> print([strip_label(country) for country in control.displayValue])
    ['Argentina', 'Bolivia', 'Chile', 'Colombia',
     'Costa Rica', 'Dominican Republic', 'Ecuador',
     'El Salvador', 'Guatemala', 'Honduras', 'Mexico',
     'Nicaragua', 'Panama', 'Paraguay', 'Peru',
     'Puerto Rico', 'Spain', 'United States', 'Uruguay',
     'Venezuela']

Changing values and submitting the form will allow the admin to change
values.

If the new language code already exists, the system will show a failure
so the user can fix it.

    >>> admin_browser.getControl('ISO 639').value = 'fr'
    >>> admin_browser.getControl('Admin Language').click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/+languages/es/+admin

    >>> for tag in find_tags_by_class(admin_browser.contents, 'message'):
    ...     print(tag.decode_contents())
    There is 1 error.
    There is already a language with that code.

Changing values to correct content works:

    >>> admin_browser.getControl('ISO 639').value = 'bars'
    >>> admin_browser.getControl('English name').value = 'Changed field'
    >>> spokenin_control = admin_browser.getControl(name='field.countries')
    >>> spokenin_control.getControl('Argentina').selected = False
    >>> spokenin_control.getControl('France').selected = True
    >>> admin_browser.getControl('Admin Language').click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/+languages/bars

And we can validate it:

    >>> admin_browser.getLink('Administer').click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/+languages/bars/+admin

    >>> print(admin_browser.getControl('ISO 639').value)
    bars

    >>> print(admin_browser.getControl('English name').value)
    Changed field

    >>> control = admin_browser.getControl(name='field.countries')
    >>> print([strip_label(country) for country in control.displayValue])
    ['Bolivia', 'Chile', 'Colombia', 'Costa Rica',
     'Dominican Republic', 'Ecuador', 'El Salvador', 'France',
     'Guatemala', 'Honduras', 'Mexico', 'Nicaragua',
     'Panama', 'Paraguay', 'Peru', 'Puerto Rico', 'Spain',
     'United States', 'Uruguay', 'Venezuela']

That was a renaming action, which means that language code 'es' doesn't
exist anymore.

    >>> browser.open('http://translations.launchpad.test/+languages/es')
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...
