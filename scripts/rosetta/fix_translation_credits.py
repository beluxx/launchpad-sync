#!/usr/bin/python2 -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Mark all translation credits as translated."""

import _pythonpath  # noqa: F401

from lp.services.scripts.base import LaunchpadScript
from lp.translations.scripts.fix_translation_credits import (
    FixTranslationCreditsProcess,
    )


class FixTranslationCredits(LaunchpadScript):
    """Go through all POFiles and mark translation credits as translated."""

    def main(self):
        fixer = FixTranslationCreditsProcess(self.txn, self.logger)
        fixer.run()


if __name__ == '__main__':
    script = FixTranslationCredits(name="fix-translation-credits",
                                   dbuser='rosettaadmin')
    script.lock_and_run()
