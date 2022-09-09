Translation Access Display
==========================

Ed Minh, an administrator, visits a translation page for Evolution.  The
page tells him what translation team is responsible for maintaining that
translation, and also reminds him that he has full editing privileges.

    >>> def print_tag(page, id):
    ...     """Find and print tag with given id."""
    ...     tag = find_tag_by_id(page, id)
    ...     if tag is None:
    ...         print("None")
    ...     else:
    ...         print(tag.decode_contents())
    ...

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "evolution/trunk/+pots/evolution-2.2/es/+translate"
    ... )
    >>> print_tag(admin_browser.contents, "translation-managers")
    This translation is managed by <...testing Spanish team<...>, assigned by
    <...Just a testing team<...>.

    >>> print_tag(admin_browser.contents, "translation-access")
    You have full access to this translation.

Users with full access will also have an option to switch between translator
and reviewer working mode.

    >>> switch_working_mode = find_tag_by_id(
    ...     admin_browser.contents, "translation-switch-working-mode"
    ... )
    >>> switch_working_mode is not None
    True

Displaying translation groups and reviewers
-------------------------------------------

Evolution is part of the Gnome project group, and when Gnome sets a
translation group of its own, that too is shown here.

    >>> import re

    >>> from zope.component import getUtility
    >>> from zope.security.proxy import removeSecurityProxy

    >>> from lp.services.database.constants import UTC_NOW
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> from lp.translations.model.translationgroup import TranslationGroup

    >>> login("admin@canonical.com")
    >>> spanish = getUtility(ILanguageSet)["es"]
    >>> evolution = removeSecurityProxy(getUtility(IProductSet)["evolution"])
    >>> foobar = getUtility(IPersonSet).getByName("name16")
    >>> gnomegroup = TranslationGroup(
    ...     name="gnomegroup",
    ...     title="Gnome translation group",
    ...     summary="Testing group",
    ...     datecreated=UTC_NOW,
    ...     owner=foobar,
    ... )
    >>> evolution.projectgroup.translationgroup = gnomegroup
    >>> logout()

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "evolution/trunk/+pots/evolution-2.2/es/+translate"
    ... )
    >>> print_tag(admin_browser.contents, "translation-managers")
    This translation is managed by <...testing Spanish team<...>, assigned by
    <...Just a testing team<...>, and <...gnomegroup<...>.

If the two groups are identical, however, it is only listed once.

    >>> evolution.projectgroup.translationgroup = evolution.translationgroup

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "evolution/trunk/+pots/evolution-2.2/es/+translate"
    ... )
    >>> managers_tag = find_tag_by_id(
    ...     admin_browser.contents, "translation-managers"
    ... ).decode_contents()
    >>> print(re.search(",\s+and", managers_tag))
    None

If no translation group is assigned, the page also mentions that.

    >>> original_translation_group = evolution.translationgroup
    >>> evolution.translationgroup = None
    >>> evolution.projectgroup.translationgroup = None

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "evolution/trunk/+pots/evolution-2.2/es/+translate"
    ... )
    >>> print_tag(admin_browser.contents, "translation-managers")
    No translation group has been assigned.

    # Restore old situation.
    >>> evolution.translationgroup = original_translation_group


Displaying access privileges
----------------------------

Ann Ominous is not logged in.  She visits the same translation and sees
the same information, except she's not allowed to enter anything.

    >>> anon_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "evolution/trunk/+pots/evolution-2.2/es/+translate"
    ... )
    >>> print_tag(anon_browser.contents, "translation-managers")
    This translation is managed by <...testing Spanish team<...>, assigned by
    <...Just a testing team<...>.

    >>> print_tag(anon_browser.contents, "translation-access")
    You are not logged in.  Please log in to work on translations.

Joe Regular is logged in, but has no particular relationship to this
translation.  The page informs Joe that he can enter suggestions, which
will be held for review by the translation's managers.

    >>> user_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "evolution/trunk/+pots/evolution-2.2/es/+translate"
    ... )
    >>> print_tag(user_browser.contents, "translation-access")
    Your suggestions will be held for review by the managers of this
    translation.

Users without full access will not have an option to switch between translator
and reviewer working mode.

    >>> switch_working_mode = find_tag_by_id(
    ...     user_browser.contents, "translation-switch-working-mode"
    ... )
    >>> switch_working_mode is not None
    False

If Evolution's translation is set to Closed mode, Joe will not be able
to submit suggestions.

    >>> from lp.translations.enums import TranslationPermission
    >>> evolution.translationpermission = TranslationPermission.CLOSED
    >>> user_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "evolution/trunk/+pots/evolution-2.2/es/+translate"
    ... )
    >>> print_tag(user_browser.contents, "translation-access")
    This template can be translated only by its managers.

If users are not allowed to submit suggestions, they will also not have an
option to switch between translator and reviewer working mode.

    >>> switch_working_mode = find_tag_by_id(
    ...     user_browser.contents, "translation-switch-working-mode"
    ... )
    >>> switch_working_mode is not None
    False

There is a special case where Joe visits a translation into a language
that isn't covered by the translation group: Joe is told he cannot enter
translations, and invited to contact the translation group about setting
up translation for this language.

    # XXX: JeroenVermeulen 2008-06-19 bug=197223: This test will work
    # once we stop inviting suggestions for untended Restricted
    # translations.

    #>>> evolution.translationpermission = TranslationPermission.RESTRICTED
    #>>> user_browser.open(
    #...     'http://translations.launchpad.test/'
    #...     'evolution/trunk/+pots/evolution-2.2/nl/+translate')
    #>>> print_tag(user_browser.contents, 'translation-access')
    #There is nobody to manage translation into this particular language.
    #If you are interested in working on it, please contact the
    #translation group.

Finally, if there is no translation group at all and the permissions do
not allow Joe to translate, the page shows that the translation is
closed and no option to switch between translator and reviewer working mode
will be displayed.

    >>> evolution.translationpermission = TranslationPermission.CLOSED
    >>> evolution.translationgroup = None
    >>> user_browser.open(
    ...     "http://translations.launchpad.test/"
    ...     "evolution/trunk/+pots/evolution-2.2/es/+translate"
    ... )
    >>> print_tag(user_browser.contents, "translation-access")
    This translation is not open for changes.

    >>> switch_working_mode = find_tag_by_id(
    ...     user_browser.contents, "translation-switch-working-mode"
    ... )
    >>> switch_working_mode is not None
    False
