# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for pofile translate pages."""

__metaclass__ = type
__all__ = []

from canonical.launchpad.windmill.testing import constants, lpuser
from lp.translations.windmill.testing import TranslationsWindmillLayer
from lp.testing import WindmillTestCase


class POFileNewTranslationFieldKeybindings(WindmillTestCase):
    """Tests for keybinding actions associated to the translation field.

    These tests should cover both simple (ie. pt) and composed (ie. pt_br)
    language codes.
    """

    layer = TranslationsWindmillLayer
    suite_name = 'POFile Translate'

    def _checkTranslationAutoselect(
        self, url, new_translation_id, new_translation_select_id):
        """Checks that the select radio button is checked when typing a new
        translation.
        """
        # Go to the translation page.
        self.client.open(url=url)
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        self.test_user.ensure_login(self.client)

        # Wait for the new translation field and it's associated radio button.
        self.client.waits.forElement(
            id=new_translation_id, timeout=constants.FOR_ELEMENT)
        self.client.waits.forElement(
            id=new_translation_select_id, timeout=constants.FOR_ELEMENT)

        # Check that the associated radio button is not selected.
        self.client.asserts.assertNotChecked(id=new_translation_select_id)

        # Type a new translation.
        self.client.type(
            id=new_translation_id, text=u'New translation')

        # Check that the associated radio button is selected.
        self.client.asserts.assertChecked(id=new_translation_select_id)

    def test_pofile_new_translation_autoselect(self):
        """Test for automatically selecting new translation on text input.

        When new text is typed into the new translation text fields, the
        associated radio button should be automatically selected.
        """
        self.test_user = lpuser.TRANSLATIONS_ADMIN

        # Test the zoom out view for Evolution trunk Spanish (es).
        start_url = ('http://translations.launchpad.dev:8085/'
                        'evolution/trunk/+pots/evolution-2.2/es/+translate')
        new_translation_id = u'msgset_1_es_translation_0_new'
        new_translation_select_id = u'msgset_1_es_translation_0_new_select'
        self._checkTranslationAutoselect(
            start_url, new_translation_id, new_translation_select_id)

        # Test the zoom in view for Evolution trunk Brazilian (pt_BR).
        start_url = ('http://translations.launchpad.dev:8085/'
                        'evolution/trunk/+pots/evolution-2.2/'
                        'pt_BR/1/+translate')
        new_translation_id = u'msgset_1_pt_BR_translation_0_new'
        new_translation_select_id = u'msgset_1_pt_BR_translation_0_new_select'
        self._checkTranslationAutoselect(
            start_url, new_translation_id, new_translation_select_id)

        # Test the zoom out view for Ubuntu Hoary Brazilian (pt_BR).
        start_url = ('http://translations.launchpad.dev:8085/'
                        'ubuntu/hoary/+source/mozilla/+pots/pkgconf-mozilla/'
                        'pt_BR/1/+translate')
        new_translation_id = u'msgset_152_pt_BR_translation_0_new'
        new_translation_select_id = (u'msgset_152_pt_BR'
                                       '_translation_0_new_select')
        self._checkTranslationAutoselect(
            start_url, new_translation_id, new_translation_select_id)

    def _checkResetTranslationSelect(
        self, client, checkbox, singular_new_select, singular_current_select,
        singular_new_field=None, plural_new_select=None):
        """Checks that the new translation select radio buttons are checked
        when ticking 'Someone should review this translation' checkbox.
        """

        client.waits.forElement(
            id=checkbox, timeout=constants.FOR_ELEMENT)
        client.waits.forElement(
            id=singular_new_select, timeout=constants.FOR_ELEMENT)
        client.waits.forElement(
            id=singular_current_select, timeout=constants.FOR_ELEMENT)
        if plural_new_select is not None:
            client.waits.forElement(
                id=plural_new_select, timeout=constants.FOR_ELEMENT)
        if singular_new_field is not None:
            client.waits.forElement(
                id=singular_new_field, timeout=constants.FOR_ELEMENT)

        # Check that initialy the checkbox is not checked and
        # that the radio buttons are not selected.
        client.asserts.assertNotChecked(id=checkbox)
        client.asserts.assertNotChecked(id=singular_new_select)
        client.asserts.assertChecked(id=singular_current_select)
        if plural_new_select is not None:
            client.asserts.assertNotChecked(id=plural_new_select)

        # Check the checkbox
        client.click(id=checkbox)

        # Check that the checkbox and the new translation radio buttons are
        # selected.
        client.asserts.assertChecked(id=checkbox)
        client.asserts.assertChecked(id=singular_new_select)
        client.asserts.assertNotChecked(id=singular_current_select)
        if plural_new_select is not None:
            client.asserts.assertChecked(id=plural_new_select)

        # Then then we uncheck the 'Someone needs to review this translation'
        # checkbox.
        client.click(id=checkbox)

        # Unchecking the 'Someone needs to review this translation' checkbox
        # when the 'New translation' field is empty, will select the current
        # translation.
        client.asserts.assertNotChecked(id=checkbox)
        client.asserts.assertNotChecked(id=singular_new_select)
        client.asserts.assertChecked(id=singular_current_select)
        if plural_new_select is not None:
            client.asserts.assertNotChecked(id=plural_new_select)

        if singular_new_field is not None:
            # Checking again the 'Someone need to review this translation'
            # checkbox, type some text and unchecking it should keep the new
            # translation fields selected
            client.click(id=checkbox)
            client.type(text=u'some test', id=singular_new_field)
            client.click(id=checkbox)

            client.asserts.assertNotChecked(id=checkbox)
            client.asserts.assertChecked(id=singular_new_select)
            client.asserts.assertNotChecked(id=singular_current_select)
            if plural_new_select is not None:
                client.asserts.assertNotChecked(id=plural_new_select)

    def test_pofile_reset_translation_select(self):
        """Test for automatically selecting new translation when
        'Someone needs to review this translations' is checked.
        """
        client = self.client
        user = lpuser.TRANSLATIONS_ADMIN

        # Go to the zoom in page for a translation with plural forms.
        self.client.open(
            url='http://translations.launchpad.dev:8085/'
                'ubuntu/hoary/+source/evolution/+pots/'
                'evolution-2.2/es/15/+translate')
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        user.ensure_login(self.client)

        checkbox = u'msgset_144_force_suggestion'
        singular_new_select = u'msgset_144_es_translation_0_new_select'
        singular_new_field = u'msgset_144_es_translation_0_new'
        singular_current_select = u'msgset_144_es_translation_0_radiobutton'
        plural_new_select = u'msgset_144_es_translation_1_new_select'
        self._checkResetTranslationSelect(
            client,
            checkbox=checkbox,
            singular_new_select=singular_new_select,
            singular_new_field=singular_new_field,
            singular_current_select=singular_current_select,
            plural_new_select=plural_new_select)

        # Go to the zoom in page for a pt_BR translation with plural forms.
        # pt_BR is a language code using the same delimiter as HTTP form
        # fields and are prone to errors.
        self.client.open(
            url='http://translations.launchpad.dev:8085/'
                'ubuntu/hoary/+source/evolution/+pots/'
                'evolution-2.2/pt_BR/15/+translate')
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        checkbox = u'msgset_144_force_suggestion'
        singular_new_select = u'msgset_144_pt_BR_translation_0_new_select'
        singular_new_field = u'msgset_144_pt_BR_translation_0_new'
        singular_current_select = u'msgset_144_pt_BR_translation_0_radiobutton'
        plural_new_select = u'msgset_144_pt_BR_translation_1_new_select'
        self._checkResetTranslationSelect(
            client,
            checkbox=checkbox,
            singular_new_select=singular_new_select,
            singular_new_field=singular_new_field,
            singular_current_select=singular_current_select,
            plural_new_select=plural_new_select)

        # Go to the zoom in page for a translation without plural forms.
        self.client.open(
            url='http://translations.launchpad.dev:8085/'
                'ubuntu/hoary/+source/evolution/+pots/'
                'evolution-2.2/es/19/+translate')
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        checkbox = u'msgset_148_force_suggestion'
        singular_new_select = u'msgset_148_es_translation_0_new_select'
        singular_current_select = u'msgset_148_es_translation_0_radiobutton'
        self._checkResetTranslationSelect(
            client,
            checkbox=checkbox,
            singular_new_select=singular_new_select,
            singular_current_select=singular_current_select)

        # Go to the zoom out page for some translations.
        self.client.open(
            url='http://translations.launchpad.dev:8085/'
                'ubuntu/hoary/+source/evolution/+pots/'
                'evolution-2.2/es/+translate')
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        checkbox = u'msgset_130_force_suggestion'
        singular_new_select = u'msgset_130_es_translation_0_new_select'
        singular_current_select = u'msgset_130_es_translation_0_radiobutton'
        self._checkResetTranslationSelect(
            client,
            checkbox=checkbox,
            singular_new_select=singular_new_select,
            singular_current_select=singular_current_select)

        # Ensure that the other radio buttons are not changed
        client.asserts.assertNotChecked(
            id=u'msgset_131_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_132_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_133_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_134_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_135_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_136_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_137_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_138_es_translation_0_new_select')
        client.asserts.assertNotChecked(
            id=u'msgset_139_es_translation_0_new_select')
