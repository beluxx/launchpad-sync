# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'ITimezoneNameVocabulary',
    ]

from zope.interface import Interface


class ITimezoneNameVocabulary(Interface):
    """A vocabulary of timezone names."""
