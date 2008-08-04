# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Classes related to OpenID discovery."""

__metaclass__ = type
__all__ = [
    'XRDSContentNegotiationMixin',
    ]

from openid.yadis.accept import getAcceptable
from openid.yadis.constants import YADIS_CONTENT_TYPE, YADIS_HEADER_NAME

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.interfaces.account import IAccountSet
from canonical.launchpad.interfaces.launchpad import (
    IOpenIdApplication, NotFoundError)
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.launchpad.interfaces.openidserver import (
    IOpenIDRPConfigSet, IOpenIDPersistentIdentity)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.webapp import canonical_url, LaunchpadView
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.publisher import (
    Navigation, RedirectionView, stepthrough, stepto)
from canonical.launchpad.webapp.vhosts import allvhosts


class OpenIdApplicationURL:
    """Canonical URL data for `IOpenIdApplication`"""
    implements(ICanonicalUrlData)

    path = ''
    inside = None
    rootsite = 'openid'

    def __init__(self, context):
        self.context = context


class OpenIdApplicationNavigation(Navigation):
    """Navigation for `IOpenIdApplication`"""
    usedfor = IOpenIdApplication

    @stepthrough('+id')
    def traverse_id(self, name):
        """Traverse to persistent OpenID identity URLs."""
        account = getUtility(IAccountSet).getByOpenIdIdentifier(name)
        if account is not None:
            return IOpenIDPersistentIdentity(account)
        else:
            return None

    @stepto('+rpconfig')
    def rpconfig(self):
        return getUtility(IOpenIDRPConfigSet)

    @stepto('token')
    def token(self):
        """Traverse to login tokens."""
        # We need to traverse the 'token' namespace in order to allow people
        # to create new accounts and reset their passwords. This can't clash
        # with a person's name because it's a blacklisted name.
        return getUtility(ILoginTokenSet)

    def traverse(self, name):
        """Redirect person names to equivalent persistent identity URLs."""
        person = getUtility(IPersonSet).getByName(name)
        if person is not None and person.is_openid_enabled:
            openid_identity = IOpenIDPersistentIdentity(person.account)
            target = openid_identity.openid_identity_url
            return RedirectionView(target, self.request, 303)
        else:
            raise NotFoundError(name)


class XRDSContentNegotiationMixin:
    """A mixin that does content negotiation to support XRDS discovery."""

    enable_xrds_discovery = True

    def xrds(self):
        """Render the XRDS document for this content object."""
        self.request.response.setHeader('Content-Type', YADIS_CONTENT_TYPE)
        data = self.xrds_template()
        return data.encode('utf-8')

    def _getURL(self):
        """Return the URL as sent by the browser."""
        url = self.request.getApplicationURL() + self.request['PATH_INFO']
        query_string = self.request.get('QUERY_STRING', '')
        if query_string:
            url += '?' + query_string
        return url

    def render(self):
        """Render a page supporting XRDS discovery."""
        # While Zope doesn't care about extra slashes, such
        # differences result in different identity URLs.  To avoid
        # confusion, we redirect to our canonical URL if we aren't
        # already there.
        current_url = self._getURL()
        expected_url = canonical_url(self.context)
        if current_url != expected_url:
            self.request.response.redirect(expected_url)
            return ''

        if self.enable_xrds_discovery:
            # Tell the user agent that we do different things depending on
            # the value of the "Accept" header.
            self.request.response.setHeader('Vary', 'Accept')

            accept_content = self.request.get('HTTP_ACCEPT', '')
            acceptable = getAcceptable(accept_content,
                                       ['text/html', YADIS_CONTENT_TYPE])
            # Return the XRDS document if it is preferred to text/html.
            for mtype in acceptable:
                if mtype == 'text/html':
                    break
                elif mtype == YADIS_CONTENT_TYPE:
                    return self.xrds()
                else:
                    raise AssertionError(
                        'Unexpected acceptable content type: %s' % mtype)

            # Add a header pointing to the location of the XRDS document
            # and chain to the default render() method.
            self.request.response.setHeader(
                YADIS_HEADER_NAME, '%s/+xrds' % canonical_url(self.context))
        return super(XRDSContentNegotiationMixin, self).render()

    @cachedproperty
    def openid_server_url(self):
        """The OpenID Server endpoint URL for Launchpad."""
        return allvhosts.configs['openid'].rooturl + '+openid'


class PersistentIdentityView(XRDSContentNegotiationMixin, LaunchpadView):
    """Render the OpenID identity page."""

    xrds_template = ViewPageTemplateFile("../templates/person-xrds.pt")

    @cachedproperty
    def person_url(self):
        """The absolute URL for the person's Launchpad profile."""
        person = getUtility(IPersonSet).getByAccount(self.context.account)
        return canonical_url(person, rootsite='mainsite')

    @cachedproperty
    def openid_identity_url(self):
        """The person's persistent OpenID identity URL."""
        return canonical_url(self.context)


class OpenIdApplicationIndexView(XRDSContentNegotiationMixin, LaunchpadView):
    """Render the OpenID index page."""

    xrds_template = ViewPageTemplateFile(
        "../templates/openidapplication-xrds.pt")
