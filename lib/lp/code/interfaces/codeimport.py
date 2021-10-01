# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code import interfaces."""

__all__ = [
    'ICodeImport',
    'ICodeImportSet',
    ]

import re

from lazr.restful.declarations import (
    call_with,
    export_write_operation,
    exported,
    exported_as_webservice_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import ReferenceChoice
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Datetime,
    Int,
    TextLine,
    Timedelta,
    )

from lp import _
from lp.app.validators import LaunchpadValidationError
from lp.code.enums import (
    CodeImportReviewStatus,
    RevisionControlSystems,
    TargetRevisionControlSystems,
    )
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.gitrepository import IGitRepository
from lp.services.fields import (
    PublicPersonChoice,
    URIField,
    )


# CVSROOT parsing based on cscvs.

class CVSRootError(Exception):
    """Raised when trying to use a CVSROOT with invalid syntax."""

    def __init__(self, root):
        super(CVSRootError, self).__init__(self, 'bad CVSROOT: %r' % root)


_cvs_root_parser = re.compile(r"""
    ^:(?P<method>[^:]+):
    (?:
        (?:
            (?P<username>[^:/]+)
            (?::(?P<password>[^:/]+))?
        @)?
        (?P<hostname>[^:/]+)
        (?::(?P<port>\\d+))?
    :?)?
    (?P<path>/.*)$
    """, flags=re.X)


def _normalise_cvs_root(root):
    """Take in a CVSROOT and normalise it to the :scheme:.... format."""
    root = str(root)
    if not root:
        raise CVSRootError(root)
    if root.startswith(":"):
        return root
    if root.startswith("/"):
        return ":local:%s" % root
    if ":" not in root:
        if '/' not in root:
            raise CVSRootError(root)
        root = "%s:%s" % (root[:root.find("/")-1], root[root.find("/"):])
    return ":ext:%s" % root


def validate_cvs_root(cvsroot):
    try:
        match = _cvs_root_parser.match(_normalise_cvs_root(cvsroot))
        if match is None:
            raise CVSRootError(cvsroot)
        method, username, password, hostname, port, path = match.groups()
    except CVSRootError as e:
        raise LaunchpadValidationError(e)
    if method == 'local':
        raise LaunchpadValidationError('Local CVS roots are not allowed.')
    if not hostname:
        raise LaunchpadValidationError('CVS root is invalid.')
    if hostname.count('.') == 0:
        raise LaunchpadValidationError(
            'Please use a fully qualified host name.')
    return True


def validate_cvs_module(cvsmodule):
    valid_module = re.compile('^[a-zA-Z][a-zA-Z0-9_/.+-]*$')
    if not valid_module.match(cvsmodule):
        raise LaunchpadValidationError(
            'The CVS module contains illegal characters.')
    if cvsmodule == 'CVS':
        raise LaunchpadValidationError(
            'A CVS module can not be called "CVS".')
    return True


@exported_as_webservice_entry()
class ICodeImport(Interface):
    """A code import to a Bazaar Branch."""

    id = Int(readonly=True, required=True)
    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)

    branch = exported(
        ReferenceChoice(
            title=_('Branch'), required=False, readonly=True,
            vocabulary='Branch', schema=IBranch,
            description=_("The Bazaar branch produced by the "
                "import system.")))
    git_repository = exported(
        ReferenceChoice(
            title=_('Git repository'), required=False, readonly=True,
            vocabulary='GitRepository', schema=IGitRepository,
            description=_(
                "The Git repository produced by the import system.")))
    target = Attribute(
        "The branch/repository produced by the import system (VCS-agnostic).")

    registrant = PublicPersonChoice(
        title=_('Registrant'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam',
        description=_("The person who initially requested this import."))

    review_status = exported(
        Choice(
            title=_("Review Status"), vocabulary=CodeImportReviewStatus,
            default=CodeImportReviewStatus.REVIEWED, readonly=True,
            description=_("Only reviewed imports are processed.")))

    rcs_type = exported(
        Choice(
            title=_("Type of RCS"), readonly=True,
            required=True, vocabulary=RevisionControlSystems,
            description=_("The revision control system to import from.")))

    target_rcs_type = exported(
        Choice(
            title=_("Type of target RCS"), readonly=True,
            required=True, vocabulary=TargetRevisionControlSystems,
            description=_("The revision control system to import to.")))

    url = exported(
        URIField(title=_("URL"), required=False, readonly=True,
            description=_("The URL of the VCS branch."),
            allowed_schemes=["http", "https", "svn", "git", "bzr", "ftp"],
            allow_userinfo=True,
            allow_port=True,
            allow_query=False,      # Query makes no sense in Subversion.
            allow_fragment=False,   # Fragment makes no sense in Subversion.
            trailing_slash=False))  # See http://launchpad.net/bugs/56357.

    cvs_root = exported(
        TextLine(title=_("Repository"), required=False, readonly=True,
            constraint=validate_cvs_root,
            description=_("The CVSROOT. "
                "Example: :pserver:anonymous@anoncvs.gnome.org:/cvs/gnome")))

    cvs_module = exported(
        TextLine(title=_("Module"), required=False, readonly=True,
            constraint=validate_cvs_module,
            description=_("The path to import within the repository."
                " Usually, it is the name of the project.")))

    date_last_successful = exported(
        Datetime(title=_("Last successful"), required=False, readonly=True))

    update_interval = Timedelta(
        title=_("Update interval"), required=False, description=_(
        "The user-specified time between automatic updates of this import. "
        "If this is unspecified, the effective update interval is a default "
        "value selected by Launchpad administrators."))

    effective_update_interval = Timedelta(
        title=_("Effective update interval"), required=True, readonly=True,
        description=_(
        "The effective time between automatic updates of this import. "
        "If the user did not specify an update interval, this is a default "
        "value selected by Launchpad administrators."))

    def getImportDetailsForDisplay():
        """Get a one-line summary of the location this import is from."""

    import_job = Choice(
        title=_("Current job"),
        readonly=True, vocabulary='CodeImportJob',
        description=_(
            "The current job for this import, either pending or running."))

    results = Attribute("The results for this code import.")

    consecutive_failure_count = Attribute(
        "How many times in a row this import has failed.")

    def updateFromData(data, user):
        """Modify attributes of the `CodeImport`.

        Creates and returns a MODIFY `CodeImportEvent` if changes were made.

        This method preserves the invariant that a `CodeImportJob` exists for
        a given import if and only if its review_status is REVIEWED, creating
        and deleting jobs as necessary.

        :param data: dictionary whose keys are attribute names and values are
            attribute values.
        :param user: user who made the change, to record in the
            `CodeImportEvent`.  May be ``None``.
        :return: The MODIFY `CodeImportEvent`, if any changes were made, or
            None if no changes were made.
        """

    def updateURL(new_url, user):
        """Update the URL for this `CodeImport`.

        A separate setter as it has lower permissions than updateFromData.
        :param new_url: string of the proposed new URL.
        :param user: user who made the change, to record in the
            `CodeImportEvent`.  May be ``None``.
        :return: The MODIFY `CodeImportEvent`, if any changes were made, or
            None if no changes were made.
        """

    def tryFailingImportAgain(user):
        """Try a failing import again.

        This method sets the review_status back to REVIEWED and requests the
        import be attempted as soon as possible.

        The import must be in the FAILING state.

        :param user: the user who is requesting the import be tried again.
        """

    @call_with(requester=REQUEST_USER)
    @export_write_operation()
    def requestImport(requester, error_if_already_requested=False):
        """Request that an import be tried soon.

        This method will schedule an import to happen soon for this branch.

        The import must be in the Reviewed state, if not then a
        CodeImportNotInReviewedState error will be thrown. If using the
        API then a status code of 400 will result.

        If the import is already running then a CodeImportAlreadyRunning
        error will be thrown. If using the API then a status code of
        400 will result.

        The two cases can be distinguished over the API by seeing if the
        exception names appear in the body of the response.

        If used over the API and the request has already been made then this
        method will silently do nothing.
        If called internally then the error_if_already_requested parameter
        controls whether a CodeImportAlreadyRequested exception will be
        thrown in that situation.

        :return: None
        """


class ICodeImportSet(Interface):
    """Interface representing the set of code imports."""

    def new(registrant, context, branch_name, rcs_type, target_rcs_type,
            url=None, cvs_root=None, cvs_module=None, review_status=None,
            owner=None):
        """Create a new CodeImport.

        :param context: An `IHasCodeImports` that the code is associated with.
        :param owner: The `IPerson` to set as the owner of the branch, or
            None to use registrant. registrant must be a member of owner to
            do this.
        """

    def get(id):
        """Get a CodeImport by its id.

        Raises `NotFoundError` if no such import exists.
        """

    def getByBranch(branch):
        """Get the CodeImport, if any, associated with a Branch."""

    def getByGitRepository(repository):
        """Get the CodeImport, if any, associated with a GitRepository."""

    def getByCVSDetails(cvs_root, cvs_module):
        """Get the CodeImport with the specified CVS details."""

    def getByURL(url, target_rcs_type):
        """Get the CodeImport with the URL and target RCS type."""

    def delete(id):
        """Delete a CodeImport given its id."""

    def search(review_status=None, rcs_type=None, target_rcs_type=None):
        """Find the CodeImports of the given status and type.

        :param review_status: An entry from the `CodeImportReviewStatus`
            schema, or None, which signifies 'any status'.
        :param rcs_type: An entry from the `RevisionControlSystems`
            schema, or None, which signifies 'any type'.
        :param target_rcs_type: An entry from the
            `TargetRevisionControlSystems` schema, or None, which signifies
            'any type'.
        """
