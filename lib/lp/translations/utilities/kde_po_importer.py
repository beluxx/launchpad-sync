# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Import module for legacy KDE .po files.

This is an extension of standard gettext PO files.
You can read more about this file format from:

 * http://l10n.kde.org/docs/translation-howto/gui-peculiarities.html
 * http://docs.kde.org/development/en/kdesdk/kbabel/kbabel-pluralforms.html
 * http://websvn.kde.org/branches/KDE/3.5/kdelibs/kdecore/klocale.cpp
"""

__all__ = [
    'KdePOImporter'
    ]

from zope.interface import implementer

from lp.translations.interfaces.translationfileformat import (
    TranslationFileFormat,
    )
from lp.translations.interfaces.translationimporter import (
    ITranslationFormatImporter,
    )
from lp.translations.utilities.gettext_po_importer import GettextPOImporter


@implementer(ITranslationFormatImporter)
class KdePOImporter(GettextPOImporter):
    """Support class for importing KDE .po files."""

    def getFormat(self, file_contents):
        """See `ITranslationFormatImporter`."""
        # XXX DaniloSegan 20070904: I first tried using POParser()
        # to check if the file is a legacy KDE PO file or not, but
        # that is too slow in some cases like tarball uploads (processing
        # of all PO files in a tarball is done in the same transaction,
        # and with extremely big PO files, this will be too slow).  Thus,
        # a heuristic verified to be correct on all PO files from
        # Ubuntu language packs.
        msgid_start = False
        for line in file_contents:
            if line == b'msgid ""\n':
                msgid_start = True
            elif (line.startswith(b'msgid "_n: ') or
                  (msgid_start and line.startswith(b'"_n: ')) or
                  line.startswith(b'msgid "_: ') or
                  (msgid_start and line.startswith(b'"_: '))):
                return TranslationFileFormat.KDEPO
            else:
                msgid_start = False
        else:
            return TranslationFileFormat.PO

    priority = 10

    content_type = 'application/x-po'

    def parse(self, translation_import_queue_entry):
        """See `ITranslationFormatImporter`."""
        translation_file = GettextPOImporter.parse(
            self, translation_import_queue_entry)

        plural_prefix = '_n: '
        context_prefix = '_: '

        for message in translation_file.messages:
            msgid = message.msgid_singular
            if msgid.startswith(plural_prefix) and '\n' in msgid:
                # This is a KDE plural form
                singular, plural = msgid[len(plural_prefix):].split('\n')

                message.msgid_singular = singular
                message.msgid_plural = plural
                msgstrs = message._translations
                if len(msgstrs) > 0:
                    message._translations = msgstrs[0].split('\n')

                self.internal_format = TranslationFileFormat.KDEPO
            elif msgid.startswith(context_prefix) and '\n' in msgid:
                # This is a KDE context message
                message.context, message.msgid_singular = (
                    msgid[len(context_prefix):].split('\n', 1))
                self.internal_format = TranslationFileFormat.KDEPO
            else:
                # Other messages are left as they are parsed by
                # GettextPOImporter
                pass

        return translation_file
