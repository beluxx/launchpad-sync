# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Security policies for using content objects."""

__metaclass__ = type
__all__ = ['AuthorizationBase']

from zope.interface import implements, Interface
from zope.component import getUtility

from canonical.launchpad.interfaces.account import IAccount
from lp.archiveuploader.permission import can_upload_to_archive
from canonical.launchpad.interfaces.emailaddress import IEmailAddress
from lp.registry.interfaces.announcement import IAnnouncement
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.archivepermission import (
    IArchivePermissionSet)
from lp.soyuz.interfaces.archiveauthtoken import IArchiveAuthToken
from lp.soyuz.interfaces.archivesubscriber import (
    IArchiveSubscriber, IPersonalArchiveSubscription)
from lp.code.interfaces.branch import (
    IBranch, user_has_special_branch_access)
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposal)
from lp.code.interfaces.branchsubscription import (
    IBranchSubscription)
from lp.bugs.interfaces.bug import IBug
from lp.bugs.interfaces.bugattachment import IBugAttachment
from lp.bugs.interfaces.bugbranch import IBugBranch
from lp.bugs.interfaces.bugnomination import IBugNomination
from lp.bugs.interfaces.bugtracker import IBugTracker
from lp.soyuz.interfaces.build import IBuild
from lp.soyuz.interfaces.builder import IBuilder, IBuilderSet
from lp.code.interfaces.codeimport import ICodeImport
from lp.code.interfaces.codeimportjob import (
    ICodeImportJobSet, ICodeImportJobWorkflow)
from lp.code.interfaces.codeimportmachine import (
    ICodeImportMachine)
from lp.code.interfaces.codereviewcomment import (
    ICodeReviewComment, ICodeReviewCommentDeletion)
from lp.code.interfaces.codereviewvote import (
    ICodeReviewVoteReference)
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionmirror import (
    IDistributionMirror)
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.translations.interfaces.distroserieslanguage import (
    IDistroSeriesLanguage)
from lp.translations.utilities.permission_helpers import (
    is_admin_or_rosetta_expert)
from lp.registry.interfaces.entitlement import IEntitlement
from canonical.launchpad.interfaces.hwdb import (
    IHWDBApplication, IHWDevice, IHWDeviceClass, IHWDriver, IHWDriverName,
    IHWDriverPackageName, IHWSubmission, IHWSubmissionDevice, IHWVendorID)
from lp.services.worlddata.interfaces.language import ILanguage, ILanguageSet
from lp.translations.interfaces.languagepack import ILanguagePack
from canonical.launchpad.interfaces.launchpad import (
    IBazaarApplication, IHasBug, IHasDrivers, ILaunchpadCelebrities)
from lp.registry.interfaces.role import IHasOwner
from lp.registry.interfaces.location import IPersonLocation
from lp.registry.interfaces.mailinglist import IMailingListSet
from lp.registry.interfaces.milestone import (
    IMilestone, IProjectMilestone)
from canonical.launchpad.interfaces.oauth import (
    IOAuthAccessToken, IOAuthRequestToken)
from lp.soyuz.interfaces.packageset import IPackageset, IPackagesetSet
from lp.translations.interfaces.pofile import IPOFile
from lp.translations.interfaces.potemplate import (
    IPOTemplate, IPOTemplateSubset)
from lp.soyuz.interfaces.publishing import (
    IBinaryPackagePublishingHistory, ISourcePackagePublishingHistory)
from lp.soyuz.interfaces.queue import (
    IPackageUpload, IPackageUploadQueue)
from lp.registry.interfaces.packaging import IPackaging
from lp.registry.interfaces.person import (
    IPerson, ITeam, PersonVisibility)
from lp.registry.interfaces.pillar import IPillar
from lp.registry.interfaces.poll import (
    IPoll, IPollOption, IPollSubset)
from lp.registry.interfaces.product import IProduct, IProductSet
from lp.registry.interfaces.productrelease import (
    IProductRelease, IProductReleaseFile)
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.project import IProject, IProjectSet
from lp.code.interfaces.seriessourcepackagebranch import (
    IMakeOfficialBranchLinks, ISeriesSourcePackageBranch)
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.soyuz.interfaces.sourcepackagerelease import (
    ISourcePackageRelease)
from lp.blueprints.interfaces.specification import ISpecification
from lp.blueprints.interfaces.specificationbranch import (
    ISpecificationBranch)
from lp.blueprints.interfaces.specificationsubscription import (
    ISpecificationSubscription)
from lp.blueprints.interfaces.sprint import ISprint
from lp.blueprints.interfaces.sprintspecification import (
    ISprintSpecification)
from lp.registry.interfaces.teammembership import ITeamMembership
from lp.translations.interfaces.translationgroup import (
    ITranslationGroup, ITranslationGroupSet)
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue, ITranslationImportQueueEntry)
from lp.translations.interfaces.translationsperson import (
    ITranslationsPerson)
from lp.translations.interfaces.translator import (
    ITranslator, IEditTranslator)

from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import IAuthorization

from lp.answers.interfaces.faq import IFAQ
from lp.answers.interfaces.faqtarget import IFAQTarget
from lp.answers.interfaces.question import IQuestion
from lp.answers.interfaces.questiontarget import IQuestionTarget


class AuthorizationBase:
    implements(IAuthorization)
    permission = None
    usedfor = None

    def __init__(self, obj):
        self.obj = obj

    def checkUnauthenticated(self):
        """See `IAuthorization.checkUnauthenticated`.

        :return: True or False.
        """
        return False

    def checkAuthenticated(self, user):
        """Return True if the given person has the given permission.

        This method is implemented by security adapters that have not
        been updated to work in terms of IAccount.

        :return: True or False.
        """
        return False

    def checkAccountAuthenticated(self, account):
        """See `IAuthorization.checkAccountAuthenticated`.

        :return: True or False.
        """
        # For backward compatibility, delegate to one of
        # checkAuthenticated() or checkUnauthenticated().
        person = IPerson(account, None)
        if person is None:
            return self.checkUnauthenticated()
        else:
            return self.checkAuthenticated(person)


class ViewByLoggedInUser(AuthorizationBase):
    """The default ruleset for the launchpad.View permission.

    By default, any logged-in user can see anything. More restrictive
    rulesets are defined in other IAuthorization implementations.
    """
    permission = 'launchpad.View'
    usedfor = Interface

    def checkAuthenticated(self, user):
        """Any authenticated user can see this object."""
        return True


class AdminByAdminsTeam(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = Interface

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class AdminByCommercialTeamOrAdmins(AuthorizationBase):
    permission = 'launchpad.Commercial'
    usedfor = Interface

    def checkAuthenticated(self, user):
        celebrities = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(celebrities.commercial_admin)
                or user.inTeam(celebrities.admin))


class ReviewByRegistryExpertsOrAdmins(AuthorizationBase):
    permission = 'launchpad.ProjectReview'
    usedfor = None

    def checkAuthenticated(self, user):
        celebrities = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(celebrities.registry_experts)
                or user.inTeam(celebrities.admin))


class ReviewProduct(ReviewByRegistryExpertsOrAdmins):
    usedfor = IProduct


class ReviewProductSet(ReviewByRegistryExpertsOrAdmins):
    usedfor = IProductSet


class ReviewProject(ReviewByRegistryExpertsOrAdmins):
    usedfor = IProject


class ReviewProjectSet(ReviewByRegistryExpertsOrAdmins):
    usedfor = IProjectSet


class ViewPillar(AuthorizationBase):
    usedfor = IPillar
    permission = 'launchpad.View'

    def checkUnauthenticated(self):
        return self.obj.active

    def checkAuthenticated(self, user):
        """The Admins & Commercial Admins can see inactive pillars."""
        if self.obj.active:
            return True
        else:
            celebrities = getUtility(ILaunchpadCelebrities)
            return (user.inTeam(celebrities.commercial_admin)
                    or user.inTeam(celebrities.registry_experts)
                    or user.inTeam(celebrities.admin))


class EditAccount(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IAccount

    def checkAccountAuthenticated(self, account):
        if account == self.obj:
            return True
        user = IPerson(account, None)
        return (user is not None and
                user.inTeam(getUtility(ILaunchpadCelebrities).admin))


class ViewAccount(EditAccount):
    permission = 'launchpad.View'


class EditOAuthAccessToken(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IOAuthAccessToken

    def checkAuthenticated(self, user):
        return (self.obj.person == user
                or user.inTeam(getUtility(ILaunchpadCelebrities).admin))


class EditOAuthRequestToken(EditOAuthAccessToken):
    permission = 'launchpad.Edit'
    usedfor = IOAuthRequestToken


class EditBugNominationStatus(AuthorizationBase):
    permission = 'launchpad.Driver'
    usedfor = IBugNomination

    def checkAuthenticated(self, user):
        return self.obj.canApprove(user)


class EditByOwnersOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def checkAuthenticated(self, user):
        return (user.inTeam(self.obj.owner)
                or user.inTeam(getUtility(ILaunchpadCelebrities).admin))


class EditProduct(EditByOwnersOrAdmins):
    usedfor = IProduct


class EditPackaging(EditByOwnersOrAdmins):
    usedfor = IPackaging


class EditProductReleaseFile(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IProductReleaseFile

    def checkAuthenticated(self, user):
        return EditProductRelease(self.obj.productrelease).checkAuthenticated(
            user)


class AdminDistributionMirrorByDistroOwnerOrMirrorAdminsOrAdmins(
        AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IDistributionMirror

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.distribution.owner) or
                user.inTeam(admins) or
                user.inTeam(self.obj.distribution.mirror_admin))


class EditDistributionMirrorByOwnerOrDistroOwnerOrMirrorAdminsOrAdmins(
        AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IDistributionMirror

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or user.inTeam(admins) or
                user.inTeam(self.obj.distribution.owner) or
                user.inTeam(self.obj.distribution.mirror_admin))


class EditSpecificationBranch(AuthorizationBase):

    usedfor = ISpecificationBranch
    permission = 'launchpad.Edit'

    def checkAuthenticated(self, user):
        """See `IAuthorization.checkAuthenticated`.

        :return: True or False.
        """
        return True


class ViewSpecificationBranch(EditSpecificationBranch):

    permission = 'launchpad.View'

    def checkUnauthenticated(self):
        """See `IAuthorization.checkUnauthenticated`.

        :return: True or False.
        """
        return True


class EditSpecificationByTargetOwnerOrOwnersOrAdmins(AuthorizationBase):
    """We want everybody "related" to a specification to be able to edit it.
    You are related if you have a role on the spec, or if you have a role on
    the spec target (distro/product) or goal (distroseries/productseries).
    """

    permission = 'launchpad.Edit'
    usedfor = ISpecification

    def checkAuthenticated(self, user):
        assert self.obj.target
        admins = getUtility(ILaunchpadCelebrities).admin
        goaldrivers = []
        goalowner = None
        if self.obj.goal is not None:
            goalowner = self.obj.goal.owner
            goaldrivers = self.obj.goal.drivers
        for driver in goaldrivers:
            if user.inTeam(driver):
                return True
        return (user.inTeam(self.obj.target.owner) or
                user.inTeam(goalowner) or
                user.inTeam(self.obj.owner) or
                user.inTeam(self.obj.drafter) or
                user.inTeam(self.obj.assignee) or
                user.inTeam(self.obj.approver) or
                user.inTeam(admins))


class AdminSpecification(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = ISpecification

    def checkAuthenticated(self, user):
        assert self.obj.target
        targetowner = self.obj.target.owner
        targetdrivers = self.obj.target.drivers
        for driver in targetdrivers:
            if user.inTeam(driver):
                return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(targetowner) or user.inTeam(admins))


class DriverSpecification(AuthorizationBase):
    permission = 'launchpad.Driver'
    usedfor = ISpecification

    def checkAuthenticated(self, user):
        # If no goal is proposed for the spec then there can be no
        # drivers for it - we use launchpad.Driver on a spec to decide
        # if the person can see the page which lets you decide whether
        # to accept the goal, and if there is no goal then this is
        # extremely difficult to do :-)
        return (
            self.obj.goal and
            check_permission("launchpad.Driver", self.obj.goal))


class EditSprintSpecification(AuthorizationBase):
    """The sprint owner or driver can say what makes it onto the agenda for
    the sprint.
    """
    permission = 'launchpad.Driver'
    usedfor = ISprintSpecification

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.sprint.owner) or
                user.inTeam(self.obj.sprint.driver) or
                user.inTeam(admins))


class DriveSprint(AuthorizationBase):
    """The sprint owner or driver can say what makes it onto the agenda for
    the sprint.
    """
    permission = 'launchpad.Driver'
    usedfor = ISprint

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(self.obj.driver) or
                user.inTeam(admins))


class Sprint(AuthorizationBase):
    """An attendee, owner, or driver of a sprint."""
    permission = 'launchpad.View'
    usedfor = ISprint

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(self.obj.driver) or
                user in [attendance.attendee
                         for attendance in self.obj.attendances] or
                user.inTeam(admins))


class EditSpecificationSubscription(AuthorizationBase):
    """The subscriber, and people related to the spec or the target of the
    spec can determine who is essential."""
    permission = 'launchpad.Edit'
    usedfor = ISpecificationSubscription

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        if self.obj.specification.goal is not None:
            for driver in self.obj.specification.goal.drivers:
                if user.inTeam(driver):
                    return True
        else:
            for driver in self.obj.specification.target.drivers:
                if user.inTeam(driver):
                    return True
        return (user.inTeam(self.obj.person) or
                user.inTeam(self.obj.specification.owner) or
                user.inTeam(self.obj.specification.assignee) or
                user.inTeam(self.obj.specification.drafter) or
                user.inTeam(self.obj.specification.approver) or
                user.inTeam(admins))


class OnlyRosettaExpertsAndAdmins(AuthorizationBase):
    """Base class that allow access to Rosetta experts and Launchpad admins.
    """

    def checkAuthenticated(self, user):
        """Allow Launchpad's admins and Rosetta experts edit all fields."""
        return is_admin_or_rosetta_expert(user)


class AdminProductTranslations(AuthorizationBase):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IProduct

    def checkAuthenticated(self, user):
        """Is the user able to manage `IProduct` translations settings?

        Any Launchpad/Launchpad Translations administrator or owners are
        able to change translation settings for a product.
        """
        return (user.inTeam(self.obj.owner) or
                is_admin_or_rosetta_expert(user))


class AdminSeriesByVCSImports(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IProductSeries

    def checkAuthenticated(self, user):
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        return user.inTeam(vcs_imports)


class EditProjectMilestoneNever(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IProjectMilestone

    def checkAuthenticated(self, user):
        """IProjectMilestone is a fake content object."""
        return False


class EditMilestoneByTargetOwnerOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IMilestone

    def checkAuthenticated(self, user):
        """Authorize the product or distribution owner."""
        celebrities = getUtility(ILaunchpadCelebrities)
        if user.inTeam(celebrities.admin):
            return True
        if (self.obj.series_target is not None
            and user.inTeam(self.obj.series_target.driver)):
            # The user is a release manager.
            # XXX sinzui 2009-07-18 bug=40978: The series_target should never
            # be None, but Milestones in the production DB are like this.
            return True
        return user.inTeam(self.obj.target.owner)


class AdminMilestoneByLaunchpadAdmins(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IMilestone

    def checkAuthenticated(self, user):
        """Only the Launchpad admins need this, we are only going to use it
        for connecting up series and distroseriess where we did not have
        them."""
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class EditTeamByTeamOwnerOrLaunchpadAdmins(AuthorizationBase):
    permission = 'launchpad.Owner'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """Only the team owner and Launchpad admins need this.
        """
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(self.obj.teamowner) or user.inTeam(admins)


class EditTeamByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """The team owner and team admins have launchpad.Edit on that team.

        The Launchpad admins also have launchpad.Edit on all teams.
        """
        return can_edit_team(self.obj, user)


class EditTeamMembershipByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITeamMembership

    def checkAuthenticated(self, user):
        return can_edit_team(self.obj.team, user)


# XXX: 2008-08-01, salgado: At some point we should protect ITeamMembership
# with launchpad.View so that this adapter is used.  For now, though, it's
# going to be used only on the webservice (which explicitly checks for
# launchpad.View) so that we don't leak memberships of private teams.
class ViewTeamMembership(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = ITeamMembership

    def checkUnauthenticated(self):
        """Unauthenticated users can only view public memberships."""
        return self.obj.team.visibility == PersonVisibility.PUBLIC

    def checkAuthenticated(self, user):
        """Verify that the user can view the team's membership.

        Anyone can see a public team's membership. Only a team member or
        a Launchpad admin can view a private membership.
        """
        if self.obj.team.visibility == PersonVisibility.PUBLIC:
            return True
        admins = getUtility(ILaunchpadCelebrities).admin
        if user.inTeam(admins) or user.inTeam(self.obj.team):
            return True
        return False


class EditPersonBySelfOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPerson

    def checkAuthenticated(self, user):
        """A user can edit the Person who is herself.

        The admin team can also edit any Person.
        """
        admins = getUtility(ILaunchpadCelebrities).admin
        return self.obj.id == user.id or user.inTeam(admins)


class EditTranslationsPersonByPerson(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITranslationsPerson

    def checkAuthenticated(self, user):
        person = self.obj.person
        admins = getUtility(ILaunchpadCelebrities).admin
        return person == user or user.inTeam(admins)


class ViewPersonLocation(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IPersonLocation

    def checkUnauthenticated(self):
        return self.obj.visible

    def checkAuthenticated(self, user):
        if self.obj.visible:
            return True
        else:
            admins = getUtility(ILaunchpadCelebrities).admin
            return user == self.obj.person or user.inTeam(admins)


class EditPersonBySelf(AuthorizationBase):
    permission = 'launchpad.Special'
    usedfor = IPerson

    def checkAuthenticated(self, user):
        """A user can edit the Person who is herself."""
        return self.obj.id == user.id


class EditAccountBySelf(AuthorizationBase):
    permission = 'launchpad.Special'
    usedfor = IAccount

    def checkAccountAuthenticated(self, account):
        """A user can edit the Account who is herself."""
        return self.obj == account


class ViewPublicOrPrivateTeamMembers(AuthorizationBase):
    """Restrict viewing of private memberships of teams.

    Only members of a team with a private membership can view the
    membership list.
    """
    permission = 'launchpad.View'
    usedfor = IPerson

    def checkUnauthenticated(self):
        """Unauthenticated users can only view public memberships."""
        if self.obj.visibility == PersonVisibility.PUBLIC:
            return True
        return False

    def checkAccountAuthenticated(self, account):
        """See `IAuthorization.checkAccountAuthenticated`.

        Verify that the user can view the team's membership.

        Anyone can see a public team's membership. Only a team member
        or a Launchpad admin can view a private membership.
        """
        if self.obj.visibility == PersonVisibility.PUBLIC:
            return True
        user = IPerson(account, None)
        if user is None:
            return False
        admins = getUtility(ILaunchpadCelebrities).admin
        if user.inTeam(admins) or user.inTeam(self.obj):
            return True
        return False


class EditPollByTeamOwnerOrTeamAdminsOrAdmins(
        EditTeamMembershipByTeamOwnerOrTeamAdminsOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IPoll


class EditPollSubsetByTeamOwnerOrTeamAdminsOrAdmins(
        EditPollByTeamOwnerOrTeamAdminsOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IPollSubset


class EditPollOptionByTeamOwnerOrTeamAdminsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPollOption

    def checkAuthenticated(self, user):
        return can_edit_team(self.obj.poll.team, user)


class AdminDistribution(AdminByAdminsTeam):
    """Soyuz involves huge chunks of data in the archive and librarian,
    so for the moment we are locking down admin and edit on distributions
    and distroseriess to the Launchpad admin team."""
    permission = 'launchpad.Admin'
    usedfor = IDistribution


class EditDistributionByDistroOwnersOrAdmins(AuthorizationBase):
    """The owner of a distribution should be able to edit its
    information; it is mainly administrative data, such as bug
    contacts. Note that creation of new distributions and distribution
    series is still protected with launchpad.Admin"""
    permission = 'launchpad.Edit'
    usedfor = IDistribution

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(admins))


class AppendDistributionByDriversOrOwnersOrAdmins(AuthorizationBase):
    """Distribution drivers, owners, and admins may plan releases.

    Drivers of `IDerivativeDistribution`s can create series. Owners and
    admins can create series for all `IDistribution`s.
    """
    permission = 'launchpad.Append'
    usedfor = IDistribution

    def checkAuthenticated(self, user):
        if user.inTeam(self.obj.driver) and not self.obj.full_functionality:
            # Drivers of derivative distributions can create a series that
            # they will be the release manager for.
            return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(admins))


class EditDistributionSourcePackageByDistroOwnersOrAdmins(AuthorizationBase):
    """The owner of a distribution should be able to edit its source
    package information"""
    permission = 'launchpad.Edit'
    usedfor = IDistributionSourcePackage

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.distribution.owner) or
                user.inTeam(admins))


class AdminDistroSeries(AdminByAdminsTeam):
    """Soyuz involves huge chunks of data in the archive and librarian,
    so for the moment we are locking down admin and edit on distributions
    and distroseriess to the Launchpad admin team.

    NB: Please consult with SABDFL before modifying this permission because
        changing it could cause the archive to get rearranged, with tons of
        files moved to the new namespace, and mirrors would get very very
        upset. Then James T would be on your case.
    """
    permission = 'launchpad.Admin'
    usedfor = IDistroSeries


class EditDistroSeriesByOwnersOrDistroOwnersOrAdmins(AuthorizationBase):
    """The owner of the distro series should be able to modify some of the
    fields on the IDistroSeries

    NB: there is potential for a great mess if this is not done correctly so
    please consult with Kiko and MDZ on the mailing list before modifying
    these permissions.
    """
    permission = 'launchpad.Edit'
    usedfor = IDistroSeries

    def checkAuthenticated(self, user):
        if (user.inTeam(self.obj.driver)
            and not self.obj.distribution.full_functionality):
            # The series driver (release manager) may edit a series if the
            # distribution is an `IDerivativeDistribution`
            return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.owner) or
                user.inTeam(self.obj.distribution.owner) or
                user.inTeam(admins))


class SeriesDrivers(AuthorizationBase):
    """Drivers can approve or decline features and target bugs.

    Drivers exist for distribution and product series.  Distribution and
    product owners are implicitly drivers too.
    """
    permission = 'launchpad.Driver'
    usedfor = IHasDrivers

    def checkAuthenticated(self, user):
        for driver in self.obj.drivers:
            if user.inTeam(driver):
                return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(self.obj.owner) or user.inTeam(admins)


class ViewProductSeries(AuthorizationBase):

    usedfor = IProductSeries
    permision = 'launchpad.View'

    def checkUnauthenticated(self):
        """See `IAuthorization.checkUnauthenticated`.

        :return: True or False.
        """
        return True

    def checkAuthenticated(self, user):
        """See `IAuthorization.checkAuthenticated`.

        :return: True or False.
        """
        return True


class EditProductSeries(EditByOwnersOrAdmins):
    usedfor = IProductSeries

    def checkAuthenticated(self, user):
        """Allow product owner, Rosetta Experts, or admins."""
        if (user.inTeam(self.obj.product.owner) or
            user.inTeam(self.obj.driver)):
            # The user is the owner of the product, or the release manager.
            return True
        # Rosetta experts need to be able to upload translations.
        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
        if user.inTeam(rosetta_experts):
            return True
        return EditByOwnersOrAdmins.checkAuthenticated(
            self, user)


class EditBugTask(AuthorizationBase):
    """Permission checker for editing objects linked to a bug.

    Allow any logged-in user to edit objects linked to public
    bugs. Allow only explicit subscribers to edit objects linked to
    private bugs.
    """
    permission = 'launchpad.Edit'
    usedfor = IHasBug

    def checkAuthenticated(self, user):
        admins = getUtility(ILaunchpadCelebrities).admin

        if user.inTeam(admins):
            # Admins can always edit bugtasks, whether they're reported on a
            # private bug or not.
            return True

        if not self.obj.bug.private:
            # This is a public bug, so anyone can edit it.
            return True
        else:
            # This is a private bug, and we know the user isn't an admin, so
            # we'll only allow editing if the user is explicitly subscribed to
            # this bug.
            for subscription in self.obj.bug.subscriptions:
                if user.inTeam(subscription.person):
                    return True

            return False


class PublicToAllOrPrivateToExplicitSubscribersForBugTask(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IHasBug

    def checkAuthenticated(self, user):
        return self.obj.bug.userCanView(user)

    def checkUnauthenticated(self):
        """Allow anonymous users to see non-private bugs only."""
        return not self.obj.bug.private


class EditPublicByLoggedInUserAndPrivateByExplicitSubscribers(
    AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBug

    def checkAuthenticated(self, user):
        """Allow any logged in user to edit a public bug, and only
        explicit subscribers to edit private bugs.
        """
        admins = getUtility(ILaunchpadCelebrities).admin
        if not self.obj.private:
            # This is a public bug.
            return True
        elif user.inTeam(admins):
            # Admins can edit all bugs.
            return True
        else:
            # This is a private bug. Only explicit subscribers may edit it.
            for subscription in self.obj.subscriptions:
                if user.inTeam(subscription.person):
                    return True

        return False

    def checkUnauthenticated(self):
        """Never allow unauthenticated users to edit a bug."""
        return False


class PublicToAllOrPrivateToExplicitSubscribersForBug(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IBug

    def checkAuthenticated(self, user):
        """Allow any user to see non-private bugs, but only explicit
        subscribers to see private bugs.
        """
        return self.obj.userCanView(user)

    def checkUnauthenticated(self):
        """Allow anonymous users to see non-private bugs only."""
        return not self.obj.private


class EditBugBranch(EditPublicByLoggedInUserAndPrivateByExplicitSubscribers):
    permission = 'launchpad.Edit'
    usedfor = IBugBranch

    def __init__(self, bug_branch):
        # The same permissions as for the BugBranch's bug should apply
        # to the BugBranch itself.
        EditPublicByLoggedInUserAndPrivateByExplicitSubscribers.__init__(
            self, bug_branch.bug)


class ViewBugAttachment(PublicToAllOrPrivateToExplicitSubscribersForBug):
    """Security adapter for viewing a bug attachment.

    If the user is authorized to view the bug, he's allowed to view the
    attachment.
    """
    permission = 'launchpad.View'
    usedfor = IBugAttachment

    def __init__(self, bugattachment):
        PublicToAllOrPrivateToExplicitSubscribersForBug.__init__(
            self, bugattachment.bug)


class EditBugAttachment(
    EditPublicByLoggedInUserAndPrivateByExplicitSubscribers):
    """Security adapter for editing a bug attachment.

    If the user is authorized to view the bug, he's allowed to edit the
    attachment.
    """
    permission = 'launchpad.Edit'
    usedfor = IBugAttachment

    def __init__(self, bugattachment):
        EditPublicByLoggedInUserAndPrivateByExplicitSubscribers.__init__(
            self, bugattachment.bug)


class ViewAnnouncement(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IAnnouncement

    def checkUnauthenticated(self):
        """Let anonymous users see published announcements."""
        if self.obj.published:
            return True
        return False

    def checkAuthenticated(self, user):
        """Keep project news invisible to end-users unless they are project
        admins, until the announcements are published."""

        # Every user can view published announcements.
        if self.obj.published:
            return True

        # Project drivers can view any project announcements.
        assert self.obj.target
        if self.obj.target.drivers:
            for driver in self.obj.target.drivers:
                if user.inTeam(driver):
                    return True
        if user.inTeam(self.obj.target.owner):
            return True

        # Launchpad admins can view any announcement.
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class EditAnnouncement(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IAnnouncement

    def checkAuthenticated(self, user):
        """Allow the project owner and drivers to edit any project news."""

        assert self.obj.target
        if self.obj.target.drivers:
            for driver in self.obj.target.drivers:
                if user.inTeam(driver):
                    return True
        if user.inTeam(self.obj.target.owner):
            return True

        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class UseApiDoc(AuthorizationBase):
    permission = 'zope.app.apidoc.UseAPIDoc'
    usedfor = Interface

    def checkAuthenticated(self, user):
        return True


class OnlyBazaarExpertsAndAdmins(AuthorizationBase):
    """Base class that allows only the Launchpad admins and Bazaar
    experts."""

    def checkAuthenticated(self, user):
        bzrexperts = getUtility(ILaunchpadCelebrities).bazaar_experts
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins) or user.inTeam(bzrexperts)


class OnlyVcsImportsAndAdmins(AuthorizationBase):
    """Base class that allows only the Launchpad admins and VCS Imports
    experts."""

    def checkAuthenticated(self, user):
        vcsexpert = getUtility(ILaunchpadCelebrities).vcs_imports
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins) or user.inTeam(vcsexpert)


class AdminTheBazaar(OnlyVcsImportsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = IBazaarApplication


class EditCodeImport(OnlyVcsImportsAndAdmins):
    """Control who can edit the object view of a CodeImport.

    Currently, we restrict the visibility of the new code import
    system to members of ~vcs-imports and Launchpad admins.
    """
    permission = 'launchpad.Edit'
    usedfor = ICodeImport


class SeeCodeImportJobSet(OnlyVcsImportsAndAdmins):
    """Control who can see the CodeImportJobSet utility.

    Currently, we restrict the visibility of the new code import
    system to members of ~vcs-imports and Launchpad admins.
    """
    permission = 'launchpad.View'
    usedfor = ICodeImportJobSet


class EditCodeImportJobWorkflow(OnlyVcsImportsAndAdmins):
    """Control who can use the CodeImportJobWorkflow utility.

    Currently, we restrict the visibility of the new code import
    system to members of ~vcs-imports and Launchpad admins.
    """
    permission = 'launchpad.Edit'
    usedfor = ICodeImportJobWorkflow


class EditCodeImportMachine(OnlyVcsImportsAndAdmins):
    """Control who can edit the object view of a CodeImportMachine.

    Access is restricted to members of ~vcs-imports and Launchpad admins.
    """
    permission = 'launchpad.Edit'
    usedfor = ICodeImportMachine


class AdminDistributionTranslations(OnlyRosettaExpertsAndAdmins,
                                    EditDistributionByDistroOwnersOrAdmins):
    """Class for deciding who can administer distribution translations.

    This class is used for `launchpad.TranslationsAdmin` privilege on
    `IDistribution` and `IDistroSeries` and corresponding `IPOTemplate`s,
    and limits access to Rosetta experts, Launchpad admins and distribution
    translation group owner.
    """
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IDistribution

    def checkAuthenticated(self, user):
        """Is the user able to manage `IDistribution` translations settings?

        Any Launchpad/Launchpad Translations administrator or people allowed
        to edit distribution details are able to change translation settings
        for a distribution.
        """
        # Translation group owner for a distribution is also a
        # translations administrator for it.
        translation_group = self.obj.translationgroup
        if translation_group and user.inTeam(translation_group.owner):
            return True
        else:
            return (
                OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user) or
                EditDistributionByDistroOwnersOrAdmins.checkAuthenticated(
                    self, user))


# Please keep AdminPOTemplateSubset in sync with this, unless you
# know exactly what you are doing.
class AdminPOTemplateDetails(OnlyRosettaExpertsAndAdmins):
    """Controls administration of an `IPOTemplate`.

    Allow all persons that can also administer the translations to
    which this template belongs to and also translation group owners.

    Product owners does not have administrative privileges.
    """
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IPOTemplate

    def checkAuthenticated(self, user):
        template = self.obj
        if template.distroseries is not None:
            # Template is on a distribution.
            distribution = template.distroseries.distribution
            return (
                AdminDistributionTranslations(
                    distribution).checkAuthenticated(user))

        else:
            # Template is on a product.
            return OnlyRosettaExpertsAndAdmins.checkAuthenticated(
                self, user)


class EditPOTemplateDetails(AdminPOTemplateDetails, EditByOwnersOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IPOTemplate

    def checkAuthenticated(self, user):
        """Allow anyone with admin rights; owners, product owners and
        distribution owners; and for distros, translation group owners.
        """
        if (self.obj.productseries is not None and
            user.inTeam(self.obj.productseries.product.owner)):
            # The user is the owner of the product.
            return True

        return (
            AdminPOTemplateDetails.checkAuthenticated(self, user) or
            EditByOwnersOrAdmins.checkAuthenticated(self, user))


# XXX: Carlos Perello Marin 2005-05-24 bug=753:
# This should be using SuperSpecialPermissions when implemented.
class AddPOTemplate(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Append'
    usedfor = IProductSeries


class EditPOFileDetails(EditByOwnersOrAdmins):
    usedfor = IPOFile

    def checkAuthenticated(self, user):
        """Allow anyone that can edit translations, owner, experts and admis.
        """
        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts

        return (EditByOwnersOrAdmins.checkAuthenticated(self, user) or
                self.obj.canEditTranslations(user) or
                user.inTeam(rosetta_experts))


class AdminTranslator(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ITranslator

    def checkAuthenticated(self, user):
        """Allow the owner of a translation group to edit the translator
        of any language in the group."""
        return (user.inTeam(self.obj.translationgroup.owner) or
                OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user))


class EditTranslator(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Edit'
    usedfor = IEditTranslator

    def checkAuthenticated(self, user):
        """Allow the translator and the group owner to edit parts of
        the translator entry."""
        return (user.inTeam(self.obj.translator) or
                user.inTeam(self.obj.translationgroup.owner) or
                OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user))


class EditTranslationGroup(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Edit'
    usedfor = ITranslationGroup

    def checkAuthenticated(self, user):
        """Allow the owner of a translation group to edit the translator
        of any language in the group."""
        return (user.inTeam(self.obj.owner) or
                OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user))


class EditTranslationGroupSet(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ITranslationGroupSet


class DownloadFullSourcePackageTranslations(OnlyRosettaExpertsAndAdmins):
    """Restrict full `SourcePackage` translation downloads.

    Experience shows that the export queue can easily get swamped by
    large export requests.  Email leads us to believe that many of the
    users making these requests are looking for language packs, or for
    individual translations rather than the whole package.  That's why
    this class defines who is allowed to make those requests.
    """

    permission = 'launchpad.ExpensiveRequest'
    usedfor = ISourcePackage

    def _userInAnyOfTheTeams(self, user, archive_permissions):
        if archive_permissions is None or len(archive_permissions) == 0:
            return False
        for permission in archive_permissions:
            if user.inTeam(permission.person):
                return True
        return False

    def checkAuthenticated(self, user):
        """Define who may download these translations.

        Admins and Translations admins have access, as does the owner of
        the translation group (if applicable) and distribution uploaders.
        """
        distribution = self.obj.distribution
        translation_group = distribution.translationgroup
        return (
            # User is admin of some relevant kind.
            OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user) or
            # User is part of the 'driver' team for the distribution.
            (self._userInAnyOfTheTeams(user, distribution.uploaders)) or
            # User is owner of applicable translation group.
            (translation_group is not None and
             user.inTeam(translation_group.owner)))


class EditBugTracker(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBugTracker

    def checkAuthenticated(self, user):
        """Any logged-in user can edit a bug tracker."""
        return True


class EditProductRelease(EditByOwnersOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IProductRelease

    def checkAuthenticated(self, user):
        if (user.inTeam(self.obj.productseries.owner) or
            user.inTeam(self.obj.productseries.product.owner) or
            user.inTeam(self.obj.productseries.driver)):
            # The user is an owner or a release manager.
            return True
        return EditByOwnersOrAdmins.checkAuthenticated(
            self, user)


class AdminTranslationImportQueueEntry(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ITranslationImportQueueEntry

    def checkAuthenticated(self, user):
        if OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user):
            return True

        # As a special case, the Ubuntu translation group owners can
        # manage Ubuntu uploads.
        if self.obj.isUbuntuAndIsUserTranslationGroupOwner(user):
            return True

        return False


class EditTranslationImportQueueEntry(AdminTranslationImportQueueEntry):
    permission = 'launchpad.Edit'
    usedfor = ITranslationImportQueueEntry

    def checkAuthenticated(self, user):
        """Anyone who can admin an entry, plus its owner or the owner of the
        product or distribution, can edit it.
        """
        if AdminTranslationImportQueueEntry.checkAuthenticated(self, user):
            return True
        if self.obj.isUserUploaderOrOwner(user):
            return True

        return False


class AdminTranslationImportQueue(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ITranslationImportQueue


class EditPackageUploadQueue(AdminByAdminsTeam):
    permission = 'launchpad.Edit'
    usedfor = IPackageUploadQueue

    def checkAuthenticated(self, user):
        """Check user presence in admins or distroseries upload admin team."""
        if AdminByAdminsTeam.checkAuthenticated(self, user):
            return True

        permission_set = getUtility(IArchivePermissionSet)
        permissions = permission_set.componentsForQueueAdmin(
            self.obj.distroseries.main_archive, user)
        return permissions.count() > 0


class EditPackageUpload(AdminByAdminsTeam):
    permission = 'launchpad.Edit'
    usedfor = IPackageUpload

    def checkAuthenticated(self, user):
        """Return True if user has an ArchivePermission or is an admin.

        If it's a delayed-copy, check if the user can upload to its targeted
        archive.
        """
        if AdminByAdminsTeam.checkAuthenticated(self, user):
            return True

        if self.obj.is_delayed_copy:
            archive_append = AppendArchive(self.obj.archive)
            return archive_append.checkAuthenticated(user)

        permission_set = getUtility(IArchivePermissionSet)
        permissions = permission_set.componentsForQueueAdmin(
            self.obj.archive, user)
        if permissions.count() == 0:
            return False
        allowed_components = set(
            permission.component for permission in permissions)
        existing_components = self.obj.components
        # The intersection of allowed_components and
        # existing_components must be equal to existing_components
        # to allow the operation to go ahead.
        return (allowed_components.intersection(existing_components)
                == existing_components)


class AdminByBuilddAdmin(AuthorizationBase):
    permission = 'launchpad.Admin'

    def checkAuthenticated(self, user):
        """Allow admins and buildd_admins."""
        lp_admin = getUtility(ILaunchpadCelebrities).admin
        if user.inTeam(lp_admin):
            return True
        buildd_admin = getUtility(ILaunchpadCelebrities).buildd_admin
        return user.inTeam(buildd_admin)


class AdminBuilderSet(AdminByBuilddAdmin):
    usedfor = IBuilderSet


class AdminBuilder(AdminByBuilddAdmin):
    usedfor = IBuilder


# XXX cprov 2006-07-31: As soon as we have external builders, as presumed
# in the original plan, we should grant some rights to the owners and
# that's what Edit is for.
class EditBuilder(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = IBuilder


class AdminBuildRecord(AdminByBuilddAdmin):
    usedfor = IBuild


class EditBuildRecord(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = IBuild

    def checkAuthenticated(self, user):
        """Check write access for user and different kinds of archives.

        Allow
            * BuilddAdmins, for any archive.
            * The PPA owner for PPAs
            * users with upload permissions (for the respective distribution)
              otherwise.
        """
        if AdminByBuilddAdmin.checkAuthenticated(self, user):
            return True

        # If it's a PPA or a copy archive only allow its owner.
        if self.obj.archive.is_ppa or self.obj.archive.is_copy:
            return (self.obj.archive.owner and
                    user.inTeam(self.obj.archive.owner))

        # Primary or partner section here: is the user in question allowed
        # to upload to the respective component? Allow user to retry build
        # if so.
        if self.obj.archive.canUpload(user, self.obj.current_component):
            return True
        else:
            return self.obj.archive.canUpload(
                user, self.obj.sourcepackagerelease.sourcepackagename)


class ViewBuildRecord(EditBuildRecord):
    permission = 'launchpad.View'

    # This code MUST match the logic in IBuildSet.getBuildsForBuilder()
    # otherwise users are likely to get 403 errors, or worse.

    def checkAuthenticated(self, user):
        """Private restricts to admins and archive members."""
        if not self.obj.archive.private:
            # Anyone can see non-private archives.
            return True

        if user.inTeam(self.obj.archive.owner):
            # Anyone in the PPA team gets the nod.
            return True

        # LP admins may also see it.
        lp_admin = getUtility(ILaunchpadCelebrities).admin
        if user.inTeam(lp_admin):
            return True

        # If the permission check on the sourcepackagerelease for this
        # build passes then it means the build can be released from
        # privacy since the source package is published publicly.
        # This happens when copy-package is used to re-publish a private
        # package in the primary archive.
        auth_spr = ViewSourcePackageRelease(self.obj.sourcepackagerelease)
        if auth_spr.checkAuthenticated(user):
            return True

        # You're not a celebrity, get out of here.
        return False

    def checkUnauthenticated(self):
        """Unauthenticated users can see the build if it's not private."""
        if not self.obj.archive.private:
            return True

        # See comment above.
        auth_spr = ViewSourcePackageRelease(self.obj.sourcepackagerelease)
        return auth_spr.checkUnauthenticated()


class AdminQuestion(AdminByAdminsTeam):
    permission = 'launchpad.Admin'
    usedfor = IQuestion

    def checkAuthenticated(self, user):
        """Allow only admins and owners of the question pillar target."""
        context = self.obj.product or self.obj.distribution
        return (AdminByAdminsTeam.checkAuthenticated(self, user) or
                user.inTeam(context.owner))


class ModerateQuestion(AdminQuestion):
    permission = 'launchpad.Moderate'
    usedfor = IQuestion

    def checkAuthenticated(self, user):
        """Allow user who can administer the question and answer contacts."""
        if AdminQuestion.checkAuthenticated(self, user):
            return True
        for answer_contact in self.obj.target.answer_contacts:
            if user.inTeam(answer_contact):
                return True
        return False


class QuestionOwner(AuthorizationBase):
    permission = 'launchpad.Owner'
    usedfor = IQuestion

    def checkAuthenticated(self, user):
        """Allow the question's owner."""
        return user.inTeam(self.obj.owner)


class ModerateFAQTarget(EditByOwnersOrAdmins):
    permission = 'launchpad.Moderate'
    usedfor = IFAQTarget

    def checkAuthenticated(self, user):
        """Allow people with launchpad.Edit or an answer contact."""
        if EditByOwnersOrAdmins.checkAuthenticated(self, user):
            return True
        if IQuestionTarget.providedBy(self.obj):
            for answer_contact in self.obj.answer_contacts:
                if user.inTeam(answer_contact):
                    return True
        return False


class EditFAQ(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IFAQ

    def checkAuthenticated(self, user):
        """Everybody who has launchpad.Moderate on the FAQ target is allowed.
        """
        return ModerateFAQTarget(self.obj.target).checkAuthenticated(user)


def can_edit_team(team, user):
    """Return True if the given user has edit rights for the given team."""
    if user.inTeam(getUtility(ILaunchpadCelebrities).admin):
        return True
    else:
        return team in user.getAdministratedTeams()


class AdminLanguageSet(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ILanguageSet


class AdminLanguage(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ILanguage


class AccessBranch(AuthorizationBase):
    """Controls visibility of branches.

    A person can see the branch if the branch is public, they are the owner
    of the branch, they are in the team that owns the branch, subscribed to
    the branch, or a launchpad administrator.
    """
    permission = 'launchpad.View'
    usedfor = IBranch

    def checkAuthenticated(self, user):
        return self.obj.visibleByUser(user)

    def checkUnauthenticated(self):
        return self.obj.visibleByUser(None)


class EditBranch(AuthorizationBase):
    """The owner, bazaar experts or admins can edit branches."""
    permission = 'launchpad.Edit'
    usedfor = IBranch

    def checkAuthenticated(self, user):
        can_edit = (
            user.inTeam(self.obj.owner) or
            user_has_special_branch_access(user) or
            can_upload_linked_package(user, self.obj))
        if can_edit:
            return True
        # It used to be the case that all import branches were owned by the
        # special, restricted team ~vcs-imports. For these legacy code import
        # branches, we still want the code import registrant to be able to
        # edit them. Similarly, we still want vcs-imports members to be able
        # to edit those branches.
        code_import = self.obj.code_import
        if code_import is None:
            return False
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        return (
            user.inTeam(vcs_imports)
            or (self.obj.owner == vcs_imports
                and user.inTeam(code_import.registrant)))


def can_upload_linked_package(person, branch):
    """True if person may upload the package linked to `branch`."""
    # No associated `ISuiteSourcePackage` data -> not an official branch.
    # Abort.
    ssp_list = branch.associatedSuiteSourcePackages()
    if len(ssp_list) < 1:
        return False

    # XXX al-maisan, 2009-10-20: a branch may currently be associated with a
    # number of (distroseries, sourcepackagename, pocket) combinations.
    # This does not seem right. But until the database model is fixed we work
    # around this by assuming that things are fine as long as we find at least
    # one combination that allows us to upload the corresponding source
    # package.
    for ssp in ssp_list:
        if can_upload_to_archive(person, ssp):
            return True
    return False


class AdminBranch(AuthorizationBase):
    """The bazaar experts or admins can administer branches."""
    permission = 'launchpad.Admin'
    usedfor = IBranch

    def checkAuthenticated(self, user):
        celebs = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(celebs.admin) or
                user.inTeam(celebs.bazaar_experts))


# Please keep this in sync with AdminPOTemplateDetails.  Note that
# this permission controls access to browsing into individual
# potemplates, but it's on a different object (POTemplateSubset)
# from AdminPOTemplateDetails, even though it looks almost identical
class AdminPOTemplateSubset(OnlyRosettaExpertsAndAdmins):
    """Controls administration of an `IPOTemplateSubset`.

    Allow all persons that can also administer the translations to
    which this template belongs to and also translation group owners.

    Product owners does not have administrative privileges.
    """
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IPOTemplateSubset

    def checkAuthenticated(self, user):
        template_set = self.obj
        if template_set.distroseries is not None:
            distribution = template_set.distroseries.distribution
            return (
                AdminDistributionTranslations(
                    distribution).checkAuthenticated(user))
        else:
            # Template is on a product.
            return OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user)


class AdminDistroSeriesLanguage(AdminDistributionTranslations):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IDistroSeriesLanguage

    def checkAuthenticated(self, user):
        """Is the user able to manage `IDistroSeriesLanguage` translations

        Disribution managers can also manage IDistroSeriesLanguage
        """
        return (AdminDistributionTranslations(
            self.obj.distroseries.distribution).checkAuthenticated(user))


class AdminDistroSeriesTranslations(AdminDistributionTranslations):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IDistroSeries

    def checkAuthenticated(self, user):
        """Is the user able to manage `IDistroSeries` translations

        Disribution managers can also manage IDistroSeries
        """
        return (AdminDistributionTranslations(
            self.obj.distribution).checkAuthenticated(user))


class BranchSubscriptionEdit(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBranchSubscription

    def checkAuthenticated(self, user):
        """Is the user able to edit a branch subscription?

        Any team member can edit a branch subscription for their team.
        Launchpad Admins can also edit any branch subscription.
        """
        celebs = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(self.obj.person) or
                user.inTeam(celebs.admin) or
                user.inTeam(celebs.bazaar_experts))


class BranchSubscriptionView(BranchSubscriptionEdit):
    permission = 'launchpad.View'


class BranchMergeProposalView(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IBranchMergeProposal

    def checkAuthenticated(self, user):
        """Is the user able to view the branch merge proposal?

        The user can see a merge proposal between two branches
        that the user can see.
        """
        return (AccessBranch(self.obj.source_branch).checkAuthenticated(user)
                and
                AccessBranch(self.obj.target_branch).checkAuthenticated(user))

    def checkUnauthenticated(self):
        """Is anyone able to view the branch merge proposal?

        Anyone can see a merge proposal between two public branches.
        """
        return (AccessBranch(self.obj.source_branch).checkUnauthenticated()
                and
                AccessBranch(self.obj.target_branch).checkUnauthenticated())


class CodeReviewVoteReferenceEdit(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ICodeReviewVoteReference

    def checkAuthenticated(self, user):
        """Only the affected teams may change the review request.

        The registrant may reassign the request to another entity.
        A member of the review team may assign it to themselves.
        A person to whom it is assigned may delegate it to someone else.
        """
        return (user.inTeam(self.obj.reviewer) or
                user.inTeam(self.obj.registrant))


class CodeReviewCommentView(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = ICodeReviewComment

    def checkAuthenticated(self, user):
        """Is the user able to view the code review comment?

        The user can see a code review comment if they can see the branch
        merge proposal.
        """
        bmp_checker = BranchMergeProposalView(self.obj.branch_merge_proposal)
        return bmp_checker.checkAuthenticated(user)

    def checkUnauthenticated(self):
        """Are not-logged-in people able to view the code review comment?

        They can see a code review comment if they can see the branch merge
        proposal.
        """
        bmp_checker = BranchMergeProposalView(self.obj.branch_merge_proposal)
        return bmp_checker.checkUnauthenticated()


class CodeReviewCommentDelete(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ICodeReviewCommentDeletion

    def checkAuthenticated(self, user):
        """Is the user able to view the code review message?

        The user can see a code review message if they can see the branch
        merge proposal.
        """
        bmp_checker = BranchMergeProposalEdit(self.obj.branch_merge_proposal)
        return bmp_checker.checkAuthenticated(user)

    def checkUnauthenticated(self):
        """Are not-logged-in people able to view the code review message?

        They can see a code review message if they can see the branch merge
        proposal.
        """
        bmp_checker = BranchMergeProposalEdit(self.obj.branch_merge_proposal)
        return bmp_checker.checkUnauthenticated()


class BranchMergeProposalEdit(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBranchMergeProposal

    def checkAuthenticated(self, user):
        """Is the user able to edit the branch merge request?

        The user is able to edit if they are:
          * the registrant of the merge proposal
          * the owner of the source_branch
          * the owner of the target_branch
          * the reviewer for the target_branch
          * an administrator
        """
        celebs = getUtility(ILaunchpadCelebrities)
        return (user.inTeam(self.obj.registrant) or
                user.inTeam(self.obj.source_branch.owner) or
                user.inTeam(self.obj.target_branch.owner) or
                user.inTeam(self.obj.target_branch.reviewer) or
                user.inTeam(celebs.admin) or
                user.inTeam(celebs.bazaar_experts))


class ViewEntitlement(AuthorizationBase):
    """Permissions to view IEntitlement objects.

    Allow the owner of the entitlement, the entitlement registrant,
    or any member of the team or any admin to view the entitlement.
    """
    permission = 'launchpad.View'
    usedfor = IEntitlement

    def checkAuthenticated(self, user):
        """Is the user able to view an Entitlement attribute?

        Any team member can edit a branch subscription for their team.
        Launchpad Admins can also edit any branch subscription.
        """
        admins = getUtility(ILaunchpadCelebrities).admin
        return (user.inTeam(self.obj.person) or
                user.inTeam(self.obj.registrant) or
                user.inTeam(admins))


class AdminDistroSeriesLanguagePacks(
    OnlyRosettaExpertsAndAdmins,
    EditDistroSeriesByOwnersOrDistroOwnersOrAdmins):
    permission = 'launchpad.LanguagePacksAdmin'
    usedfor = IDistroSeries

    def checkAuthenticated(self, user):
        """Is the user able to manage `IDistroSeries` language packs?

        Any Launchpad/Launchpad Translations administrator, people allowed to
        edit distroseries or members of IDistribution.language_pack_admin team
        are able to change the language packs available.
        """
        return (
            OnlyRosettaExpertsAndAdmins.checkAuthenticated(self, user) or
            EditDistroSeriesByOwnersOrDistroOwnersOrAdmins.checkAuthenticated(
                self, user) or
            user.inTeam(self.obj.distribution.language_pack_admin))


class AdminLanguagePack(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.LanguagePacksAdmin'
    usedfor = ILanguagePack


class ViewHWSubmission(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IHWSubmission

    def checkAuthenticated(self, user):
        """Can the user view the submission details?

        Submissions that not marked private are publicly visible,
        private submissions may only be accessed by their owner and by
        admins.
        """
        if not self.obj.private:
            return True

        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(self.obj.owner) or user.inTeam(admins)

    def checkUnauthenticated(self):
        return not self.obj.private


class EditHWSubmission(AdminByAdminsTeam):
    permission = 'launchpad.Edit'
    usedfor = IHWSubmission


class ViewHWDBBase(AuthorizationBase):
    """Base class to restrict access to HWDB data to members of the HWDB team.
    """
    permission = 'launchpad.View'

    def checkAuthenticated(self, user):
        """We give for now access only to Canonical employees."""
        hwdb_team = getUtility(ILaunchpadCelebrities).hwdb_team
        return user.inTeam(hwdb_team)

    def checkUnauthenticated(self):
        """No access for anonymous users."""
        return False


class ViewHWDriver(ViewHWDBBase):
    usedfor = IHWDriver


class ViewHWDriverName(ViewHWDBBase):
    usedfor = IHWDriverName


class ViewHWDriverPackageName(ViewHWDBBase):
    usedfor = IHWDriverPackageName


class ViewHWVendorID(ViewHWDBBase):
    usedfor = IHWVendorID


class ViewHWDevice(ViewHWDBBase):
    usedfor = IHWDevice


class ViewHWSubmissionDevice(ViewHWDBBase):
    usedfor = IHWSubmissionDevice


class ViewHWDBApplication(ViewHWDBBase):
    usedfor = IHWDBApplication


class ViewHWDeviceClass(ViewHWDBBase):
    usedfor = IHWDeviceClass


class ViewArchive(AuthorizationBase):
    """Restrict viewing of private archives.

    Only admins or members of a team with a private membership can
    view the archive.
    """
    permission = 'launchpad.View'
    usedfor = IArchive

    def checkAuthenticated(self, user):
        """Verify that the user can view the archive.

        Anyone can see a public and enabled archive.

        Only Launchpad admins and uploaders can view private or disabled
        archives.
        """
        # No further checks are required if the archive is public and
        # enabled.
        if not self.obj.private and self.obj.enabled:
            return True

        # Administrator are allowed to view private archives.
        celebrities = getUtility(ILaunchpadCelebrities)
        if (user.inTeam(celebrities.admin)
            or user.inTeam(celebrities.commercial_admin)):
            return True

        # Owners can view the PPA.
        if user.inTeam(self.obj.owner):
            return True

        # Uploaders can view private PPAs.
        if self.obj.is_ppa and self.obj.canUpload(user):
            return True

        return False

    def checkUnauthenticated(self):
        """Unauthenticated users can see the PPA if it's not private."""
        return not self.obj.private and self.obj.enabled


class AppendArchive(AuthorizationBase):
    """Restrict appending (upload and copy) operations on archives.

    No one can upload to disabled archives.

    PPA upload rights are managed via `IArchive.canUpload`;

    Appending to PRIMARY, PARTNER or COPY archives is restricted to owners.

    Appending to ubuntu main archives can also be done by the
    'ubuntu-security' celebrity.
    """
    permission = 'launchpad.Append'
    usedfor = IArchive

    def checkAuthenticated(self, user):
        if not self.obj.enabled:
            return False

        if user.inTeam(self.obj.owner):
            return True

        if self.obj.is_ppa and self.obj.canUpload(user):
            return True

        celebrities = getUtility(ILaunchpadCelebrities)
        if (self.obj.is_main and
            self.obj.distribution == celebrities.ubuntu and
            user.inTeam(celebrities.ubuntu_security)):
            return True

        return False


class ViewArchiveAuthToken(AuthorizationBase):
    """Restrict viewing of archive tokens.

    The user just needs to be mentioned in the token, have append privilege
    to the archive or be an admin.
    """
    permission = "launchpad.View"
    usedfor = IArchiveAuthToken

    def checkAuthenticated(self, user):
        if user == self.obj.person:
            return True
        auth_edit = EditArchiveAuthToken(self.obj)
        return auth_edit.checkAuthenticated(user)


class EditArchiveAuthToken(AuthorizationBase):
    """Restrict editing of archive tokens.

    The user should have append privileges to the context archive, or be an
    admin.
    """
    permission = "launchpad.Edit"
    usedfor = IArchiveAuthToken

    def checkAuthenticated(self, user):
        auth_append = AppendArchive(self.obj.archive)
        if auth_append.checkAuthenticated(user):
            return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class ViewPersonalArchiveSubscription(AuthorizationBase):
    """Restrict viewing of personal archive subscriptions (non-db class).

    The user should be the subscriber, have append privilege to the archive
    or be an admin.
    """
    permission = "launchpad.View"
    usedfor = IPersonalArchiveSubscription

    def checkAuthenticated(self, user):
        if user == self.obj.subscriber:
            return True
        append_archive = AppendArchive(self.obj.archive)

        if append_archive.checkAuthenticated(user):
            return True

        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class ViewArchiveSubscriber(AuthorizationBase):
    """Restrict viewing of archive subscribers.

    The user should be the subscriber, have append privilege to the
    archive or be an admin.
    """
    permission = "launchpad.View"
    usedfor = IArchiveSubscriber

    def checkAuthenticated(self, user):
        if user.inTeam(self.obj.subscriber):
            return True
        auth_edit = EditArchiveSubscriber(self.obj)
        return auth_edit.checkAuthenticated(user)


class EditArchiveSubscriber(AuthorizationBase):
    """Restrict editing of archive subscribers.

    The user should have append privilege to the archive or be an admin.
    """
    permission = "launchpad.Edit"
    usedfor = IArchiveSubscriber

    def checkAuthenticated(self, user):
        auth_append = AppendArchive(self.obj.archive)
        if auth_append.checkAuthenticated(user):
            return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)


class ViewSourcePackagePublishingHistory(AuthorizationBase):
    """Restrict viewing of source publications."""
    permission = "launchpad.View"
    usedfor = ISourcePackagePublishingHistory

    def checkAuthenticated(self, user):
        view_archive = ViewArchive(self.obj.archive)
        if view_archive.checkAuthenticated(user):
            return True
        admins = getUtility(ILaunchpadCelebrities).admin
        return user.inTeam(admins)

    def checkUnauthenticated(self):
        return not self.obj.archive.private


class ViewBinaryPackagePublishingHistory(ViewSourcePackagePublishingHistory):
    """Restrict viewing of binary publications."""
    usedfor = IBinaryPackagePublishingHistory


class ViewSourcePackageRelease(AuthorizationBase):
    """Restrict viewing of source packages.

    Packages that are only published in private archives are subject to the
    same viewing rules as the archive (see class ViewArchive).

    If the package is published in any non-private archive, then it is
    automatically viewable even if the package is also published in
    a private archive.
    """
    permission = 'launchpad.View'
    usedfor = ISourcePackageRelease

    def checkAuthenticated(self, user):
        """Verify that the user can view the sourcepackagerelease."""
        for archive in self.obj.published_archives:
            auth_archive = ViewArchive(archive)
            if auth_archive.checkAuthenticated(user):
                return True
        return False

    def checkUnauthenticated(self):
        """Check unauthenticated users.

        Unauthenticated users can see the package as long as it's published
        in a non-private archive.
        """
        for archive in self.obj.published_archives:
            if not archive.private:
                return True
        return False


class MailingListApprovalByExperts(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IMailingListSet

    def checkAuthenticated(self, user):
        experts = getUtility(ILaunchpadCelebrities).mailing_list_experts
        return user.inTeam(experts)


class ConfigureTeamMailingList(AuthorizationBase):
    permission = 'launchpad.MailingListManager'
    usedfor = ITeam

    def checkAuthenticated(self, user):
        """Check to see if the user can manage a mailing list.

        A team's owner or administrator, the Launchpad administrators, and
        Launchpad mailing list experts can all manage a team's mailing list
        through its +mailinglist page.

        :param user: The user whose permission is being checked.
        :type user: `IPerson`
        :return: True if the user can manage a mailing list, otherwise False.
        :rtype: boolean
        """
        # The team owner, the Launchpad mailing list experts and the Launchpad
        # administrators can all view a team's +mailinglist page.
        celebrities = getUtility(ILaunchpadCelebrities)
        team = ITeam(self.obj)
        return (
            (team is not None and team in user.getAdministratedTeams()) or
            user.inTeam(celebrities.admin) or
            user.inTeam(celebrities.mailing_list_experts))


class ViewEmailAddress(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IEmailAddress

    def checkUnauthenticated(self):
        """See `AuthorizationBase`."""
        # Email addresses without an associated Person cannot be seen by
        # anonymous users.
        if self.obj.person is None:
            return False
        return not self.obj.person.hide_email_addresses

    def checkAccountAuthenticated(self, account):
        """Can the user see the details of this email address?

        If the email address' owner doesn't want his email addresses to be
        hidden, anyone can see them.  Otherwise only the owner himself or
        admins can see them.
        """
        # Always allow users to see their own email addresses.
        if self.obj.account == account:
            return True

        if not (self.obj.person is None or
                self.obj.person.hide_email_addresses):
            return True

        user = IPerson(account, None)
        if user is None:
            return False

        celebrities = getUtility(ILaunchpadCelebrities)
        return (self.obj.person is not None and user.inTeam(self.obj.person)
                or user.inTeam(celebrities.commercial_admin)
                or user.inTeam(celebrities.registry_experts)
                or user.inTeam(celebrities.admin))


class EditEmailAddress(EditByOwnersOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IEmailAddress

    def checkAccountAuthenticated(self, account):
        # Always allow users to see their own email addresses.
        if self.obj.account == account:
            return True
        return super(EditEmailAddress, self).checkAccountAuthenticated(
            account)


class EditArchivePermissionSet(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IArchivePermissionSet

    def checkAuthenticated(self, user):
        """Users must be an admin or a member of the tech board."""
        celebrities = getUtility(ILaunchpadCelebrities)
        return (
            user.inTeam(celebrities.admin)
            or user.inTeam(celebrities.ubuntu_techboard))


class LinkOfficialSourcePackageBranches(AuthorizationBase):
    """Who can source packages to their official branches?

    Only members of the ~ubuntu-branches celebrity team! Or admins.
    """

    permission = 'launchpad.Edit'
    usedfor = IMakeOfficialBranchLinks

    def checkUnauthenticated(self):
        return False

    def checkAuthenticated(self, user):
        celebrities = getUtility(ILaunchpadCelebrities)
        return (
            user.inTeam(celebrities.ubuntu_branches)
            or user.inTeam(celebrities.admin))


class ChangeOfficialSourcePackageBranchLinks(AuthorizationBase):
    """Who can change the links from source packages to their branches?

    Only members of the ~ubuntu-branches celebrity team! Or admins.
    """

    permission = 'launchpad.Edit'
    usedfor = ISeriesSourcePackageBranch

    def checkUnauthenticated(self):
        return False

    def checkAuthenticated(self, user):
        celebrities = getUtility(ILaunchpadCelebrities)
        return (
            user.inTeam(celebrities.ubuntu_branches)
            or user.inTeam(celebrities.admin))


class EditPackageset(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPackageset

    def checkAuthenticated(self, user):
        """The owner of a package set can edit the object."""
        celebrities = getUtility(ILaunchpadCelebrities)
        return (
            user.inTeam(self.obj.owner)
            or user.inTeam(celebrities.admin))


class EditPackagesetSet(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPackagesetSet

    def checkAuthenticated(self, user):
        """Users must be an admin or a member of the tech board."""
        celebrities = getUtility(ILaunchpadCelebrities)
        return (
            user.inTeam(celebrities.admin)
            or user.inTeam(celebrities.ubuntu_techboard))
