# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Preferred charsets."""

__all__ = ["Utf8PreferredCharsets"]

from zope.component import adapter
from zope.i18n.interfaces import IUserPreferredCharsets
from zope.interface import implementer
from zope.publisher.interfaces.http import IHTTPRequest


@adapter(IHTTPRequest)
@implementer(IUserPreferredCharsets)
class Utf8PreferredCharsets:
    """An IUserPreferredCharsets which always chooses utf-8."""

    def __init__(self, request):
        self.request = request

    def getPreferredCharsets(self):
        """See IUserPreferredCharsets."""
        return ["utf-8"]
