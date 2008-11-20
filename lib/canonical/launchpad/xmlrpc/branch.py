# Copyright 2006 Canonical Ltd.  All rights reserved.

# Disable pylint 'should have "self" as first argument' warnings.
# pylint: disable-msg=E0213

"""Branch XMLRPC API."""

__metaclass__ = type
__all__ = [
    'BranchSetAPI', 'IBranchSetAPI', 'IPublicCodehostingAPI',
    'PublicCodehostingAPI']

import os

from zope.component import getUtility
from zope.interface import Interface, implements
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces import (
    BranchCreationException, BranchCreationForbidden, BranchType, IBranch,
    IBranchSet, IBugSet,
    ILaunchBag, IPersonSet, IProductSet, NotFoundError)
from canonical.launchpad.interfaces.distribution import IDistribution
from canonical.launchpad.interfaces.pillar import IPillarNameSet
from canonical.launchpad.interfaces.project import IProject
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp import LaunchpadXMLRPCView, canonical_url
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.uri import URI
from canonical.launchpad.xmlrpc import faults


class IBranchSetAPI(Interface):
    """An XMLRPC interface for dealing with branches.

    This XML-RPC interface was introduced to support Bazaar 0.8-2, which is
    included in Ubuntu 6.06. This interface cannot be removed until Ubuntu
    6.06 is end-of-lifed.
    """

    def register_branch(branch_url, branch_name, branch_title,
                        branch_description, author_email, product_name,
                        owner_name=''):
        """Register a new branch in Launchpad."""

    def link_branch_to_bug(branch_url, bug_id, whiteboard):
        """Link the branch to the bug."""


class BranchSetAPI(LaunchpadXMLRPCView):

    implements(IBranchSetAPI)

    def register_branch(self, branch_url, branch_name, branch_title,
                        branch_description, author_email, product_name,
                        owner_name=''):
        """See IBranchSetAPI."""
        registrant = getUtility(ILaunchBag).user
        assert registrant is not None, (
            "register_branch shouldn't be accessible to unauthenicated"
            " requests.")

        person_set = getUtility(IPersonSet)
        if owner_name:
            owner = person_set.getByName(owner_name)
            if owner is None:
                return faults.NoSuchPersonWithName(owner_name)
            if not registrant.inTeam(owner):
                return faults.NotInTeam(registrant.name, owner_name)
        else:
            owner = registrant

        if product_name:
            product = getUtility(IProductSet).getByName(product_name)
            if product is None:
                return faults.NoSuchProduct(product_name)
        else:
            product = None

        # Branch URLs in Launchpad do not end in a slash, so strip any
        # slashes from the end of the URL.
        branch_url = branch_url.rstrip('/')

        branch_set = getUtility(IBranchSet)
        existing_branch = branch_set.getByUrl(branch_url)
        if existing_branch is not None:
            return faults.BranchAlreadyRegistered(branch_url)

        try:
            unicode_branch_url = branch_url.decode('utf-8')
            url = IBranch['url'].validate(unicode_branch_url)
        except LaunchpadValidationError, exc:
            return faults.InvalidBranchUrl(branch_url, exc)

        # We want it to be None in the database, not ''.
        if not branch_description:
            branch_description = None
        if not branch_title:
            branch_title = None

        if not branch_name:
            branch_name = unicode_branch_url.split('/')[-1]

        if author_email:
            author = person_set.getByEmail(author_email)
        else:
            author = registrant
        if author is None:
            return faults.NoSuchPerson(
                type="author", email_address=author_email)

        try:
            if branch_url:
                branch_type = BranchType.MIRRORED
            else:
                branch_type = BranchType.HOSTED
            branch = branch_set.new(
                branch_type=branch_type,
                name=branch_name, registrant=registrant, owner=owner,
                product=product, url=branch_url, title=branch_title,
                summary=branch_description, author=author)
            if branch_type == BranchType.MIRRORED:
                branch.requestMirror()
        except BranchCreationForbidden:
            return faults.BranchCreationForbidden(product.displayname)
        except BranchCreationException, err:
            return faults.BranchNameInUse(err)
        except LaunchpadValidationError, err:
            return faults.InvalidBranchName(err)

        return canonical_url(branch)

    def link_branch_to_bug(self, branch_url, bug_id, whiteboard):
        """See IBranchSetAPI."""
        branch = getUtility(IBranchSet).getByUrl(url=branch_url)
        if branch is None:
            return faults.NoSuchBranch(branch_url)
        try:
            bug = getUtility(IBugSet).get(bug_id)
        except NotFoundError:
            return faults.NoSuchBug(bug_id)
        if not whiteboard:
            whiteboard = None

        # Since this API is controlled using launchpad.AnyPerson there must be
        # an authenticated person, so use this person as the registrant.
        registrant = getUtility(ILaunchBag).user
        bug.addBranch(branch, registrant=registrant, whiteboard=whiteboard)
        return canonical_url(bug)


class IPublicCodehostingAPI(Interface):
    """The public codehosting API."""

    def resolve_lp_path(path):
        """Expand the path segment of an lp: URL into a list of branch URLs.

        This method is added to support Bazaar 0.93. It cannot be removed
        until we stop supporting Bazaar 0.93.

        :return: A dict containing a single 'urls' key that maps to a list of
            URLs. Clients should use the first URL in the list that they can
            support.  Returns a Fault if the path does not resolve to a
            branch.
        """


class _NonexistentBranch:
    """Used to represent a branch that was requested but doesn't exist."""

    def __init__(self, unique_name):
        self.unique_name = unique_name
        self.branch_type = None


class PublicCodehostingAPI(LaunchpadXMLRPCView):
    """See `IPublicCodehostingAPI`."""

    implements(IPublicCodehostingAPI)

    supported_schemes = 'bzr+ssh', 'http'

    def _getBazaarHost(self):
        """Return the hostname for the codehosting server."""
        return URI(config.codehosting.supermirror_root).host


    def _getBranch(self, unique_name):
        """Return a branch or _NonexistentBranch for the given unique name.

        :param unique_name: A string of the form "~user/project/branch".
        :return: The corresponding Branch object if the branch exists, a
            _NonexistentBranch stub object if the branch does not exist or
            faults.InvalidBranchIdentifier if unique_name is invalid.
        """
        if unique_name[0] != '~':
            return faults.InvalidBranchIdentifier(unique_name)
        branch = getUtility(IBranchSet).getByUniqueName(unique_name)
        if check_permission('launchpad.View', branch):
            return branch
        else:
            return self._getNonexistentBranch(unique_name)

    def _getResultDict(self, branch, suffix=None):
        """Return a result dict with a list of URLs for the given branch.

        :param branch: A Branch object or a _NonexistentBranch object.
        :param suffix: The section of the path that follows the branch
            specification.
        :return: {'urls': [list_of_branch_urls]}.
        """
        if branch.branch_type == BranchType.REMOTE:
            if branch.url is None:
                return faults.NoUrlForBranch(branch.unique_name)
            return dict(urls=[branch.url])
        else:
            result = dict(urls=[])
            host = self._getBazaarHost()
            for scheme in self.supported_schemes:
                path = '/' + branch.unique_name
                if suffix is not None:
                    path = os.path.join(path, suffix)
                result['urls'].append(
                    str(URI(host=host, scheme=scheme, path=path)))
            return result

    def resolve_lp_path(self, path):
        """See `IPublicCodehostingAPI`."""
        strip_path = path.strip('/')
        if strip_path == '':
            return faults.InvalidBranchIdentifier(path)
        try:
            branch, suffix = getUtility(IBranchSet).getByLPPath(strip_path)
            branch = removeSecurityProxy(branch)
        except faults.NoSuchBranch:
            branch = _NonexistentBranch(strip_path)
            suffix = None
        except faults.NoSuchProduct, e:
            pillar = getUtility(IPillarNameSet).getByName(e.product_name)
            if pillar:
                if IProject.providedBy(pillar):
                    pillar_type = 'project group'
                elif IDistribution.providedBy(pillar):
                    pillar_type = 'distribution'
                else:
                    raise AssertionError(
                        "pillar of unknown type %s" % pillar)
                return faults.NoDefaultBranchForPillar(
                    e.product_name, pillar_type)
            else:
                return faults.NoSuchProduct(e.product_name)
        except faults.LaunchpadFault, e:
            return e
        return self._getResultDict(branch, suffix)
