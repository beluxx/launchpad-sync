# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for creating navigation breadcrumbs."""

__all__ = [
    'Breadcrumb',
    'DisplaynameBreadcrumb',
    'NameBreadcrumb',
    'TitleBreadcrumb',
    ]

from zope.interface import implementer

from lp.services.webapp import canonical_url
from lp.services.webapp.interfaces import (
    IBreadcrumb,
    ICanonicalUrlData,
    )


@implementer(IBreadcrumb)
class Breadcrumb:
    """See `IBreadcrumb`.

    This class is intended for use as an adapter.
    """

    text = None
    _detail = None
    _url = None
    inside = None
    rootsite_override = None

    def __init__(self, context, url=None, text=None, inside=None,
                 rootsite=None):
        self.context = context
        if url is not None:
            self._url = url
        if text is not None:
            self.text = text
        if inside is not None:
            self.inside = inside
        if rootsite is not None:
            self.rootsite_override = rootsite

    @property
    def rootsite(self):
        """The rootsite of this breadcrumb's URL.

        If the `ICanonicalUrlData` for our context defines a rootsite, we
        return that, otherwise we return 'mainsite'.
        """
        if self.rootsite_override is not None:
            return self.rootsite_override
        url_data = ICanonicalUrlData(self.context)
        if url_data.rootsite:
            return url_data.rootsite
        else:
            return 'mainsite'

    @property
    def url(self):
        if self._url is None:
            return canonical_url(self.context, rootsite=self.rootsite)
        else:
            return self._url

    @property
    def detail(self):
        """See `IBreadcrumb`.

        Subclasses may choose to provide detail text that will be used
        to make the page title for the last item traversed.
        """
        return self._detail or self.text

    def __repr__(self):
        return "<%s url='%s' text='%s'>" % (
            self.__class__.__name__, self.url, self.text)


class NameBreadcrumb(Breadcrumb):
    """An `IBreadcrumb` that uses the context's name as its text."""

    @property
    def text(self):
        return self.context.name


class DisplaynameBreadcrumb(Breadcrumb):
    """An `IBreadcrumb` that uses the context's displayname as its text."""

    @property
    def text(self):
        return self.context.displayname


class TitleBreadcrumb(Breadcrumb):
    """An `IBreadcrumb` that uses the context's title as its text."""

    @property
    def text(self):
        return self.context.title
