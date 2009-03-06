# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Publisher mixins for the webservice.

This module defines classes that are usually needed for integration
with the Zope publisher.
"""

__metaclass__ = type
__all__ = [
    'WebServicePublicationMixin',
    'WebServiceRequestTraversal',
    'WEBSERVICE_PATH_OVERRIDE',
    ]

import urllib

from zope.component import getMultiAdapter, queryAdapter, queryMultiAdapter
from zope.interface import alsoProvides, implements
from zope.publisher.interfaces import NotFound
from zope.schema.interfaces import IBytes
from zope.security.checker import ProxyFactory

from lazr.uri import URI

from canonical.lazr.interfaces.rest import (
    IByteStorage, ICollection, IEntry, IEntryField, IHTTPResource,
    IWebBrowserInitiatedRequest, WebServiceLayer)
from canonical.lazr.interfaces.fields import ICollectionField
from canonical.lazr.rest.resource import (
    CollectionResource, EntryField, EntryFieldResource,
    EntryResource, ScopedCollection)

# Any requests that have the following element at the beginning of their
# PATH_INFO will be handled by the web service, as if they had gone to
# api.launchpad.net.
WEBSERVICE_PATH_OVERRIDE = 'api'

class WebServicePublicationMixin:
    """A mixin for webservice publication. 

    This should usually be mixed-in with ZopePublication, or Browser,
    or HTTPPublication"""


    def traverseName(self, request, ob, name):
        """See `zope.publisher.interfaces.IPublication`.

        In addition to the default traversal implementation, this publication
        also handle traversal to collection scoped into an entry.
        """
        # If this is the last traversal step, then look first for a scoped
        # collection. This is done because although Navigation handles
        # traversal to entries in a scoped collection, they don't usually
        # handle traversing to the scoped collection itself.
        if len(request.getTraversalStack()) == 0:
            try_special_traversal = True
            try:
                entry = IEntry(ob)
            except TypeError:
                try_special_traversal = False
            result = None
            if try_special_traversal:
                field = entry.schema.get(name)
                if ICollectionField.providedBy(field):
                    result = self._traverseToScopedCollection(
                        request, entry, field, name)
                elif IBytes.providedBy(field):
                    result = self._traverseToByteStorage(
                        request, entry, field, name)
                elif field is not None:
                    result = EntryField(entry, field, name)
            if result is not None:
                return result
        return super(WebServicePublicationMixin, self).traverseName(
            request, ob, name)

    def _traverseToByteStorage(self, request, entry, field, name):
        """Try to traverse to a byte storage resource in entry."""
        # Even if the library file is None, we want to allow
        # traversal, because the request might be a PUT request
        # creating a file here.
        return getMultiAdapter((entry, field.bind(entry)), IByteStorage)

    def _traverseToScopedCollection(self, request, entry, field, name):
        """Try to traverse to a collection in entry.

        This is done because we don't usually traverse to attributes
        representing a collection in our regular Navigation.

        This method returns None if a scoped collection cannot be found.
        """
        collection = getattr(entry, name, None)
        if collection is None:
            return None
        scoped_collection = ScopedCollection(entry.context, entry)
        # Tell the IScopedCollection object what collection it's managing,
        # and what the collection's relationship is to the entry it's
        # scoped to.
        scoped_collection.collection = collection
        scoped_collection.relationship = field
        return scoped_collection

    def getDefaultTraversal(self, request, ob):
        """See `zope.publisher.interfaces.browser.IBrowserPublication`.

        The WebService doesn't use the getDefaultTraversal() extension
        mechanism, because it only applies to GET, HEAD, and POST methods.

        See getResource() for the alternate mechanism.
        """
        # Don't traverse to anything else.
        return ob, None

    def getResource(self, request, ob):
        """Return the resource that can publish the object ob.

        This is done at the end of traversal.  If the published object
        supports the ICollection, or IEntry interface we wrap it into the
        appropriate resource.
        """
        if (ICollection.providedBy(ob) or
            queryAdapter(ob, ICollection) is not None):
            # Object supports ICollection protocol.
            resource = CollectionResource(ob, request)
        elif (IEntry.providedBy(ob) or
              queryAdapter(ob, IEntry) is not None):
            # Object supports IEntry protocol.
            resource = EntryResource(ob, request)
        elif (IEntryField.providedBy(ob) or
              queryAdapter(ob, IEntryField) is not None):
            # Object supports IEntryField protocol.
            resource = EntryFieldResource(ob, request)
        elif queryMultiAdapter((ob, request), IHTTPResource) is not None:
            # Object can be adapted to a resource.
            resource = queryMultiAdapter((ob, request), IHTTPResource)
        elif IHTTPResource.providedBy(ob):
            # A resource knows how to take care of itself.
            return ob
        else:
            # This object should not be published on the web service.
            raise NotFound(ob, '')

        # Wrap the resource in a security proxy.
        return ProxyFactory(resource)

    def callObject(self, request, object):
        """Help web browsers handle redirects correctly."""
        value = super(
            WebServicePublicationMixin, self).callObject(request, object)
        if request.response.getStatus() / 100 == 3:
            vhost = URI(request.getApplicationURL()).host
            if IWebBrowserInitiatedRequest.providedBy(request):
                # This request was (probably) sent by a web
                # browser. Because web browsers, content negotiation,
                # and redirects are a deadly combination, we're going
                # to help the browser out a little.
                #
                # We're going to take the current request's "Accept"
                # header and put it into the URL specified in the
                # Location header. When the web browser makes its
                # request, it will munge the original 'Accept' header,
                # but because the URL it's accessing will include the
                # old header in the "ws.accept" header, we'll still be
                # able to serve the right document.
                location = request.response.getHeader("Location", None)
                if location is not None:
                    accept = request.response.getHeader(
                        "Accept", "application/json")
                    qs_append = "ws.accept=" + urllib.quote(accept)
                    uri = URI(location)
                    if uri.query is None:
                        uri.query = qs_append
                    else:
                        uri.query += '&' + qs_append
                    request.response.setHeader("Location", str(uri))
        return value


class WebServiceRequestTraversal:
    """Mixin providing web-service resource wrapping in traversal.

    This should be mixed in the request using to the base publication used.
    """
    implements(WebServiceLayer)

    def traverse(self, ob):
        """See `zope.publisher.interfaces.IPublisherRequest`.

        This is called once at the beginning of the traversal process.

        WebService requests call the `WebServicePublication.getResource()`
        on the result of the base class's traversal.
        """
        self._removeVirtualHostTraversals()
        result = super(WebServiceRequestTraversal, self).traverse(ob)
        return self.publication.getResource(self, result)

    def _removeVirtualHostTraversals(self):
        """Remove the /api and /beta traversal names."""
        names = list()
        api = self._popTraversal(WEBSERVICE_PATH_OVERRIDE)
        if api is not None:
            names.append(api)
            # Requests that use the webservice path override are
            # usually made by web browsers. Mark this request as one
            # initiated by a web browser, for the sake of
            # optimizations later in the request lifecycle.
            alsoProvides(self, IWebBrowserInitiatedRequest)

        # Only accept versioned URLs.
        beta = self._popTraversal('beta')
        if beta is not None:
            names.append(beta)
            self.setVirtualHostRoot(names=names)
        else:
            raise NotFound(self, '', self)

    def _popTraversal(self, name):
        """Remove a name from the traversal stack, if it is present.

        :return: The name of the element removed, or None if the stack
            wasn't changed.
        """
        stack = self.getTraversalStack()
        if len(stack) > 0 and stack[-1] == name:
            item = stack.pop()
            self.setTraversalStack(stack)
            return item
        return None

