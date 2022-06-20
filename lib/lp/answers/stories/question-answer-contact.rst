Answer Contacts
===============

Each product and distros can have answer contacts. Answer contacts
receive notifications for new questions as well as changes to existing
ones.

The list of answer contacts is displayed in the 'Answer Contact' portlet
which is available on the 'Answers' facet of the product or
distribution.

    >>> browser.addHeader('Authorization', 'Basic test@canonical.com:test')
    >>> browser.addHeader('Accept-Language', 'en, es')
    >>> browser.open('http://launchpad.test/ubuntu/+questions')
    >>> print(extract_text(
    ...     find_tag_by_id(
    ...         browser.contents, 'portlet-answer-contacts-ubuntu')))
    Answer contacts for Ubuntu

Anybody can become an answer contact. To register as an answer contact,
the user clicks on the 'Set answer Contact' link:

    >>> browser.getLink('Set answer contact').click()
    >>> print(browser.title)
    Answer contact for...

    >>> description = find_main_content(browser.contents).p
    >>> print(extract_text(description))
    An answer contact...will receive changes related to all questions
    (written in one of your preferred languages)...

That page displays a series of checkboxes. One for the user and one for
each team that user is an administrator of.

    >>> browser.getControl(
    ...     name='field.answer_contact_teams').options
    ['landscape-developers', 'launchpad-users']

The user can select any of these checkboxes to register as an answer
contact themselves or one of the team for which they're an administrator. In
our case, the user decides to register themselves and the Landscape
Developers team.

    >>> browser.getControl(
    ...     "I want to be an answer contact for Ubuntu").selected = True
    >>> browser.getControl("Landscape Developers").selected = True
    >>> browser.getControl('Continue').click()

Answer contacts must tell Launchpad which languages they provide help
in. As a convenience, the Answer Tracker will set the Person's preferred
languages for them. The browser languages are used for a Person. In the
case of a Team, only English is added. Sample Person reads the notice
that their preferred languages were set, and uses the link to in the
notice to review the changes. Sample Person's browser sends the accept-
languages header with English and Spanish.

    >>> browser.getLink('Your preferred languages').click()
    >>> print(browser.title)
    Language preferences...

    >>> browser.getControl('English', index=0).selected
    True

    >>> browser.getControl('Spanish').selected
    True

To remove oneself from the answer contacts, the user uses the same 'Set
answer contact' link and uncheck themselves or the team they want to remove
from the answer contact list.

    >>> browser.open('http://launchpad.test/ubuntu/+questions')
    >>> browser.getLink('Set answer contact').click()
    >>> browser.getControl(
    ...     "I want to be an answer contact for Ubuntu").selected
    True

    >>> browser.getControl("Landscape Developers").selected
    True

    >>> browser.getControl("Landscape Developers").selected = False
    >>> browser.getControl('Continue').click()

A confirmation message is displayed:

    >>> for tag in find_tags_by_class(browser.contents, 'message'):
    ...     print(tag.decode_contents())
    Landscape Developers has been removed as an answer contact for Ubuntu.


Product Answer Contacts
-----------------------

The 'Set answer contact' action is also available on products:

    >>> browser.open('http://answers.launchpad.test/firefox')
    >>> browser.getLink('Set answer contact').click()
    >>> print(browser.title)
    Answer contact for...

    >>> print(browser.url)
    http://answers.launchpad.test/firefox/+answer-contact


Answer Contact teams and preferred languages
--------------------------------------------

Answer contacts support questions written in their preferred languages.
Team, may have preferred languages, but do not normally configure them.
So teams are given English language by default when a team becomes an
answer contact. Team admins may configure a team's preferred languages
to set exactly which languages the team supports.

Sample Person visits the Answers facet of Ubuntu as described in the
main story above. They want Landscape Developers team to be answer
contacts for Ubuntu, but only for Spanish questions to keep the email
traffic to a manageable volume.

    >>> browser.open('http://answers.launchpad.test/ubuntu/')
    >>> print(browser.title)
    Questions : Ubuntu

    >>> browser.getLink('Set answer contact').click()
    >>> browser.getControl("Landscape Developers").selected = True
    >>> browser.getControl('Continue').click()
    >>> for message in find_tags_by_class(browser.contents, 'message'):
    ...     print(extract_text(message))
    Landscape Developers has been added as an answer contact for Ubuntu.

Sample Person navigates to the team page to set it's preferred
languages. They must add Spanish to the team's preferred languages.

    >>> browser.open('http://launchpad.test/~landscape-developers')
    >>> browser.title
    'Landscape Developers in Launchpad'

    >>> browser.getLink('Set preferred languages').click()
    >>> print(browser.title)
    Language preferences...

Sample Person may be surprised to see English is already selected. Per
the notification issued in the first example above, English was added to
the team's preferred languages. We did not see the notification this
time since the languages are set. Sample Person unselects English, and
selects Spanish.

    >>> browser.getControl('English', index=0).selected
    True

    >>> browser.getControl('English', index=0).selected = False
    >>> browser.getControl('Spanish').selected = True
    >>> browser.getControl('Save').click()
