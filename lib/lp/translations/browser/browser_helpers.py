# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translation-related formatting functions."""

__all__ = [
    'contract_rosetta_escapes',
    'convert_newlines_to_web_form',
    'count_lines',
    'expand_rosetta_escapes',
    'parse_cformat_string',
    'text_to_html',
    ]

from math import ceil
import re

from lp.services import helpers
from lp.services.webapp.escaping import html_escape
from lp.translations.interfaces.translations import TranslationConstants


class UnrecognisedCFormatString(ValueError):
    """Exception: C-style format string fails to parse."""


def contract_rosetta_escapes(text):
    """Replace Rosetta escape sequences with the real characters."""
    return helpers.text_replaced(text, {'[tab]': '\t',
                                        r'\[tab]': '[tab]',
                                        '[nbsp]': '\u00a0',
                                        r'\[nbsp]': '[nbsp]',
                                        '[nnbsp]': '\u202f',
                                        r'\[nnbsp]': '[nnbsp]'})


def expand_rosetta_escapes(unicode_text):
    """Replace characters needing a Rosetta escape sequences."""
    escapes = {'\t': TranslationConstants.TAB_CHAR,
               '[tab]': TranslationConstants.TAB_CHAR_ESCAPED,
               '\u00a0': TranslationConstants.NO_BREAK_SPACE_CHAR,
               '[nbsp]': TranslationConstants.NO_BREAK_SPACE_CHAR_ESCAPED,
               '\u202f': TranslationConstants.NARROW_NO_BREAK_SPACE_CHAR,
               '[nnbsp]':
    TranslationConstants.NARROW_NO_BREAK_SPACE_CHAR_ESCAPED}
    return helpers.text_replaced(unicode_text, escapes)


def text_to_html(text, flags, space=TranslationConstants.SPACE_CHAR,
               newline=TranslationConstants.NEWLINE_CHAR):
    """Convert a unicode text to a HTML representation."""
    if text is None:
        return None

    markup_lines = []
    # Replace leading and trailing spaces on each line with special markup.
    if '\r\n' in text:
        newline_chars = '\r\n'
    elif '\r' in text:
        newline_chars = '\r'
    else:
        newline_chars = '\n'
    for line in text.split(newline_chars):
        # Pattern:
        # - group 1: zero or more spaces: leading whitespace
        # - group 2: zero or more groups of (zero or
        #   more spaces followed by one or more non-spaces): maximal string
        #   which doesn't begin or end with whitespace
        # - group 3: zero or more spaces: trailing whitespace
        match = re.match('^( *)((?: *[^ ]+)*)( *)$', line)

        if match:
            format_segments = None
            if 'c-format' in flags:
                try:
                    format_segments = parse_cformat_string(match.group(2))
                except UnrecognisedCFormatString:
                    pass
            if format_segments is not None:
                markup = ''
                for segment in format_segments:
                    type, content = segment

                    if type == 'interpolation':
                        markup += ('<code>%s</code>' % html_escape(content))
                    elif type == 'string':
                        markup += html_escape(content)
            else:
                markup = html_escape(match.group(2))
            markup_lines.append(
                space * len(match.group(1))
                + markup
                + space * len(match.group(3)))
        else:
            raise AssertionError(
                "A regular expression that should always match didn't.")

    return expand_rosetta_escapes(newline.join(markup_lines))


def convert_newlines_to_web_form(unicode_text):
    """Convert Unicode string to CR/LF line endings as used in web forms.

    Any style of line endings is accepted: MacOS-style CR, MS-DOS-style
    CR/LF, or rest-of-world-style LF.
    """
    if unicode_text is None:
        return None

    assert isinstance(unicode_text, str), (
        "The given text must be unicode instead of %s" % type(unicode_text))

    if unicode_text is None:
        return None
    elif '\r\n' in unicode_text:
        # The text is already using the windows newline chars
        return unicode_text
    elif '\n' in unicode_text:
        return helpers.text_replaced(unicode_text, {'\n': '\r\n'})
    else:
        return helpers.text_replaced(unicode_text, {'\r': '\r\n'})


def count_lines(text):
    """Count the number of physical lines in a string.

    This is always at least as large as the number of logical lines in a
    string.
    """
    if text is None:
        return 0

    CHARACTERS_PER_LINE = 60
    count = 0

    for line in text.split('\n'):
        if len(line) == 0:
            count += 1
        else:
            count += int(ceil(float(len(line)) / CHARACTERS_PER_LINE))

    return count


def parse_cformat_string(string):
    """Parse C-style format string into sequence of segments.

    The result is a sequence of tuples (type, content), where ``type`` is
    either "string" (for a plain piece of string) or "interpolation" (for a
    printf()-style substitution).  The other part of the tuple, ``content``,
    will be the part of the input string that makes up the given element, so
    either plain text or a printf substitution such as ``%s`` or ``%.3d``.

    As in printf(), the double parenthesis (%%) is taken as plain text.
    """
    # The sequence '%%' is not counted as an interpolation. Perhaps splitting
    # into 'special' and 'non-special' sequences would be better.

    # This function works on the basis that s can be one of three things: an
    # empty string, a string beginning with a sequence containing no
    # interpolations, or a string beginning with an interpolation.
    segments = []
    end = string
    plain_re = re.compile('(%%|[^%])+')
    interpolation_re = re.compile('%[^diouxXeEfFgGcspmn]*[diouxXeEfFgGcspmn]')

    while end:
        # Check for a interpolation-less prefix.
        match = plain_re.match(end)
        if match:
            segment = match.group(0)
            segments.append(('string', segment))
            end = end[len(segment):]
            continue

        # Check for an interpolation sequence at the beginning.
        match = interpolation_re.match(end)
        if match:
            segment = match.group(0)
            segments.append(('interpolation', segment))
            end = end[len(segment):]
            continue

        # Give up.
        raise UnrecognisedCFormatString(string)

    return segments
