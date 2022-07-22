# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "UnknownFileType",
    "ValidateTranslationsFile",
]

import logging
import os.path
from optparse import OptionParser

from lp.services import scripts
from lp.translations.utilities.gettext_po_parser import POParser


class UnknownFileType(Exception):
    """File's type is not recognized."""


def validate_unknown_file_type(filename, content):
    """Fail validation: unknown file type."""
    raise UnknownFileType("Unrecognized file type for '%s'." % filename)


def validate_po(filename, content):
    """Validate a gettext PO or POT file."""
    POParser().parse(content)


class ValidateTranslationsFile:
    """Parse translations files to see if they are well-formed."""

    name = "validate-translations-file"

    validators = {
        "po": validate_po,
        "pot": validate_po,
    }

    def __init__(self, test_args=None):
        """Set up basic facilities, similar to `LaunchpadScript`."""
        self.parser = OptionParser()
        scripts.logger_options(self.parser, default=logging.INFO)
        self.options, self.args = self.parser.parse_args(args=test_args)
        self.logger = scripts.logger(self.options, self.name)

    def main(self):
        """Validate file(s)."""
        failures = 0
        files = len(self.args)
        self.logger.info("Validating %d file(s)." % files)

        for filename in self.args:
            if not self._readAndValidate(filename):
                failures += 1

        if failures == 0:
            self.logger.info("OK.")
        elif failures > 1:
            self.logger.error("%d failures in %d files." % (failures, files))
        elif files > 1:
            self.logger.error("1 failure in %d files." % files)
        else:
            self.logger.error("Validation failed.")

        if failures == 0:
            return 0
        else:
            return 1

    def _pickValidator(self, filename):
        """Select the appropriate validator for a file."""
        base, ext = os.path.splitext(filename)
        if ext is not None and ext.startswith("."):
            ext = ext[1:]
        return self.validators.get(ext, validate_unknown_file_type)

    def _validateContent(self, filename, content):
        """Validate in-memory file contents.

        :param filename: Name of this file.
        :param content: Contents of this file, as raw bytes.
        :return: Whether the file was parsed successfully.
        """
        validator = self._pickValidator(filename)
        try:
            validator(filename, content)
        except (SystemError, AssertionError):
            raise
        except UnknownFileType:
            raise
        except Exception as e:
            self.logger.warning("Failure in '%s': %s" % (filename, e))
            return False

        return True

    def _readAndValidate(self, filename):
        """Read given file and validate it.

        :param filename: Name of a file to read.
        :return: Whether the file was parsed successfully.
        """
        with open(filename, "rb") as f:
            content = f.read()
        return self._validateContent(filename, content)
