# Copyright 2009-2022 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Security policies for using content objects."""

__all__ = [
    'AdminByAdminsTeam',
    'AdminByBuilddAdmin',
    'AdminByCommercialTeamOrAdmins',
    'BugTargetOwnerOrBugSupervisorOrAdmins',
    'EditByOwnersOrAdmins',
    'EditByRegistryExpertsOrAdmins',
    'EditPackageBuild',
    'is_commercial_case',
    'ModerateByRegistryExpertsOrAdmins',
    'OnlyBazaarExpertsAndAdmins',
    'OnlyRosettaExpertsAndAdmins',
    'OnlyVcsImportsAndAdmins',
    ]

from datetime import (
    datetime,
    timedelta,
    )

import pytz
from zope.component import queryAdapter
from zope.interface import Interface

from lp.app.interfaces.security import IAuthorization
from lp.app.security import (
    AnonymousAuthorization,
    AuthorizationBase,
    DelegatedAuthorization,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfig
from lp.blueprints.interfaces.specification import (
    ISpecification,
    ISpecificationPublic,
    ISpecificationView,
    )
from lp.blueprints.interfaces.specificationbranch import ISpecificationBranch
from lp.blueprints.interfaces.specificationsubscription import (
    ISpecificationSubscription,
    )
from lp.blueprints.interfaces.sprint import ISprint
from lp.blueprints.interfaces.sprintspecification import ISprintSpecification
from lp.bugs.interfaces.bugtarget import IOfficialBugTagTargetRestricted
from lp.bugs.interfaces.structuralsubscription import IStructuralSubscription
from lp.buildmaster.interfaces.builder import (
    IBuilder,
    IBuilderSet,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.buildmaster.interfaces.packagebuild import IPackageBuild
from lp.charms.interfaces.charmbase import (
    ICharmBase,
    ICharmBaseSet,
    )
from lp.charms.interfaces.charmrecipe import (
    ICharmRecipe,
    ICharmRecipeBuildRequest,
    )
from lp.charms.interfaces.charmrecipebuild import ICharmRecipeBuild
from lp.oci.interfaces.ocipushrule import IOCIPushRule
from lp.oci.interfaces.ocirecipe import (
    IOCIRecipe,
    IOCIRecipeBuildRequest,
    )
from lp.oci.interfaces.ocirecipebuild import IOCIRecipeBuild
from lp.oci.interfaces.ocirecipesubscription import IOCIRecipeSubscription
from lp.oci.interfaces.ociregistrycredentials import IOCIRegistryCredentials
from lp.registry.interfaces.ociproject import IOCIProject
from lp.registry.interfaces.ociprojectseries import IOCIProjectSeries
from lp.registry.interfaces.role import IHasOwner
from lp.services.auth.interfaces import IAccessToken
from lp.services.config import config
from lp.services.identity.interfaces.emailaddress import IEmailAddress
from lp.services.librarian.interfaces import ILibraryFileAliasWithParent
from lp.services.messages.interfaces.message import IMessage
from lp.services.messages.interfaces.messagerevision import IMessageRevision
from lp.services.oauth.interfaces import (
    IOAuthAccessToken,
    IOAuthRequestToken,
    )
from lp.services.openid.interfaces.openididentifier import IOpenIdIdentifier
from lp.services.webapp.interfaces import ILaunchpadRoot
from lp.services.webhooks.interfaces import (
    IWebhook,
    IWebhookDeliveryJob,
    )
from lp.services.worlddata.interfaces.country import ICountry
from lp.services.worlddata.interfaces.language import (
    ILanguage,
    ILanguageSet,
    )
from lp.snappy.interfaces.snap import (
    ISnap,
    ISnapBuildRequest,
    )
from lp.snappy.interfaces.snapbase import (
    ISnapBase,
    ISnapBaseSet,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuild
from lp.snappy.interfaces.snappyseries import (
    ISnappySeries,
    ISnappySeriesSet,
    )
from lp.snappy.interfaces.snapsubscription import ISnapSubscription
from lp.translations.interfaces.customlanguagecode import ICustomLanguageCode
from lp.translations.interfaces.languagepack import ILanguagePack
from lp.translations.interfaces.pofile import IPOFile
from lp.translations.interfaces.potemplate import IPOTemplate
from lp.translations.interfaces.translationgroup import (
    ITranslationGroup,
    ITranslationGroupSet,
    )
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    ITranslationImportQueueEntry,
    )
from lp.translations.interfaces.translationsperson import ITranslationsPerson
from lp.translations.interfaces.translationtemplatesbuild import (
    ITranslationTemplatesBuild,
    )
from lp.translations.interfaces.translator import (
    IEditTranslator,
    ITranslator,
    )


def is_commercial_case(obj, user):
    """Is this a commercial project and the user is a commercial admin?"""
    return obj.has_current_commercial_subscription and user.in_commercial_admin


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


class AnyAllowedPersonDeferredToView(AuthorizationBase):
    """The default ruleset for the launchpad.AnyAllowedPerson permission.

    An authenticated user is delegated to the View security adapter. Since
    anonymous users are not logged in, they are denied.
    """
    permission = 'launchpad.AnyAllowedPerson'
    usedfor = Interface

    def checkUnauthenticated(self):
        return False

    def checkAuthenticated(self, user):
        yield self.obj, 'launchpad.View'


class AnyLegitimatePerson(AuthorizationBase):
    """The default ruleset for the launchpad.AnyLegitimatePerson permission.

    Some operations are open to Launchpad users in general, but we still don't
    want drive-by vandalism.
    """
    permission = 'launchpad.AnyLegitimatePerson'
    usedfor = Interface

    def checkUnauthenticated(self):
        return False

    def _hasEnoughKarma(self, user):
        return user.person.karma >= config.launchpad.min_legitimate_karma

    def _isOldEnough(self, user):
        return (
            datetime.now(pytz.UTC) - user.person.account.date_created >=
            timedelta(days=config.launchpad.min_legitimate_account_age))

    def checkAuthenticated(self, user):
        if not self._hasEnoughKarma(user) and not self._isOldEnough(user):
            return False
        return self.forwardCheckAuthenticated(
            user, self.obj, 'launchpad.AnyAllowedPerson')


class LimitedViewDeferredToView(AuthorizationBase):
    """The default ruleset for the launchpad.LimitedView permission.

    Few objects define LimitedView permission because it is only needed
    in cases where a user may know something about a private object. The
    default behaviour is to check if the user has launchpad.View permission;
    private objects must define their own launchpad.LimitedView checker to
    truly check the permission.
    """
    permission = 'launchpad.LimitedView'
    usedfor = Interface

    def checkUnauthenticated(self):
        yield self.obj, 'launchpad.View'

    def checkAuthenticated(self, user):
        yield self.obj, 'launchpad.View'


class AdminByAdminsTeam(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = Interface

    def checkAuthenticated(self, user):
        return user.in_admin


class AdminByCommercialTeamOrAdmins(AuthorizationBase):
    permission = 'launchpad.Commercial'
    usedfor = Interface

    def checkAuthenticated(self, user):
        return user.in_commercial_admin or user.in_admin


class EditByRegistryExpertsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ILaunchpadRoot

    def checkAuthenticated(self, user):
        return user.in_admin or user.in_registry_experts


class ModerateByRegistryExpertsOrAdmins(AuthorizationBase):
    permission = 'launchpad.Moderate'
    usedfor = None

    def checkAuthenticated(self, user):
        return user.in_admin or user.in_registry_experts


class ViewOpenIdIdentifierBySelfOrAdmin(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IOpenIdIdentifier

    def checkAuthenticated(self, user):
        return user.in_admin or user.person.accountID == self.obj.accountID


class EditOAuthAccessToken(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IOAuthAccessToken

    def checkAuthenticated(self, user):
        return self.obj.person == user.person or user.in_admin


class EditOAuthRequestToken(EditOAuthAccessToken):
    permission = 'launchpad.Edit'
    usedfor = IOAuthRequestToken


class EditAccessToken(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IAccessToken

    def checkAuthenticated(self, user):
        if user.inTeam(self.obj.owner):
            return True
        # Being able to edit the token doesn't allow extracting the secret,
        # so it's OK to allow the owner of the target to do so too.  This
        # allows target owners to exercise some control over access to their
        # object.
        adapter = queryAdapter(
            self.obj.target, IAuthorization, 'launchpad.Edit')
        if adapter is not None and adapter.checkAuthenticated(user):
            return True
        return False


class EditByOwnersOrAdmins(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IHasOwner

    def checkAuthenticated(self, user):
        return user.isOwner(self.obj) or user.in_admin


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


class AnonymousAccessToISpecificationPublic(AnonymousAuthorization):
    """Anonymous users have launchpad.View on ISpecificationPublic.

    This is only needed because lazr.restful is hard-coded to check that
    permission before returning things in a collection.
    """

    permission = 'launchpad.View'
    usedfor = ISpecificationPublic


class ViewSpecification(AuthorizationBase):

    permission = 'launchpad.LimitedView'
    usedfor = ISpecificationView

    def checkAuthenticated(self, user):
        return self.obj.userCanView(user)

    def checkUnauthenticated(self):
        return self.obj.userCanView(None)


class EditSpecificationByRelatedPeople(AuthorizationBase):
    """We want everybody "related" to a specification to be able to edit it.
    You are related if you have a role on the spec, or if you have a role on
    the spec target (distro/product) or goal (distroseries/productseries).
    """

    permission = 'launchpad.Edit'
    usedfor = ISpecification

    def checkAuthenticated(self, user):
        assert self.obj.target
        goal = self.obj.goal
        if goal is not None:
            if user.isOwner(goal) or user.isDriver(goal):
                return True
        return (user.in_admin or
                user.in_registry_experts or
                user.isOwner(self.obj.target) or
                user.isDriver(self.obj.target) or
                user.isOneOf(
                    self.obj, ['owner', 'drafter', 'assignee', 'approver']))


class AdminSpecification(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = ISpecification

    def checkAuthenticated(self, user):
        assert self.obj.target
        return (
                user.in_admin or
                user.in_registry_experts or
                user.isOwner(self.obj.target) or
                user.isDriver(self.obj.target))


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
            self.forwardCheckAuthenticated(user, self.obj.goal))


class EditSprintSpecification(AuthorizationBase):
    """The sprint owner or driver can say what makes it onto the agenda for
    the sprint.
    """
    permission = 'launchpad.Driver'
    usedfor = ISprintSpecification

    def checkAuthenticated(self, user):
        sprint = self.obj.sprint
        return user.isOwner(sprint) or user.isDriver(sprint) or user.in_admin


class DriveSprint(AuthorizationBase):
    """The sprint owner or driver can say what makes it onto the agenda for
    the sprint.
    """
    permission = 'launchpad.Driver'
    usedfor = ISprint

    def checkAuthenticated(self, user):
        return (user.isOwner(self.obj) or
                user.isDriver(self.obj) or
                user.in_admin)


class ViewSprint(AuthorizationBase):
    """An attendee, owner, or driver of a sprint."""
    permission = 'launchpad.View'
    usedfor = ISprint

    def checkAuthenticated(self, user):
        return (user.isOwner(self.obj) or
                user.isDriver(self.obj) or
                user.person in [attendance.attendee
                            for attendance in self.obj.attendances] or
                user.in_admin)


class EditSprint(EditByOwnersOrAdmins):
    usedfor = ISprint


class ModerateSprint(ModerateByRegistryExpertsOrAdmins):
    """The sprint owner, registry experts, and admins can moderate sprints."""
    permission = 'launchpad.Moderate'
    usedfor = ISprint

    def checkAuthenticated(self, user):
        return (
            super().checkAuthenticated(user) or
            user.isOwner(self.obj))


class EditSpecificationSubscription(AuthorizationBase):
    """The subscriber, and people related to the spec or the target of the
    spec can determine who is essential."""
    permission = 'launchpad.Edit'
    usedfor = ISpecificationSubscription

    def checkAuthenticated(self, user):
        if self.obj.specification.goal is not None:
            if user.isDriver(self.obj.specification.goal):
                return True
        else:
            if user.isDriver(self.obj.specification.target):
                return True
        return (user.inTeam(self.obj.person) or
                user.isOneOf(
                    self.obj.specification,
                    ['owner', 'drafter', 'assignee', 'approver']) or
                user.in_admin)


class OnlyRosettaExpertsAndAdmins(AuthorizationBase):
    """Base class that allow access to Rosetta experts and Launchpad admins.
    """

    def checkAuthenticated(self, user):
        """Allow Launchpad's admins and Rosetta experts edit all fields."""
        return user.in_admin or user.in_rosetta_experts


class EditTranslationsPersonByPerson(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITranslationsPerson

    def checkAuthenticated(self, user):
        person = self.obj.person
        return person == user.person or user.in_admin


class BugTargetOwnerOrBugSupervisorOrAdmins(AuthorizationBase):
    """Product's owner and bug supervisor can set official bug tags."""

    permission = 'launchpad.BugSupervisor'
    usedfor = IOfficialBugTagTargetRestricted

    def checkAuthenticated(self, user):
        return (user.inTeam(self.obj.bug_supervisor) or
                user.inTeam(self.obj.owner) or
                user.in_admin)


class ViewCountry(AnonymousAuthorization):
    """Anyone can view a Country."""
    usedfor = ICountry


class EditStructuralSubscription(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IStructuralSubscription

    def checkAuthenticated(self, user):
        """Who can edit StructuralSubscriptions."""

        assert self.obj.target

        # Removal of a target cascades removals to StructuralSubscriptions,
        # so we need to allow editing to those who can edit the target itself.
        can_edit_target = self.forwardCheckAuthenticated(
            user, self.obj.target)

        # Who is actually allowed to edit a subscription is determined by
        # a helper method on the model.
        can_edit_subscription = self.obj.target.userCanAlterSubscription(
            self.obj.subscriber, user.person)

        return (can_edit_target or can_edit_subscription)


class OnlyBazaarExpertsAndAdmins(AuthorizationBase):
    """Base class that allows only the Launchpad admins and Bazaar
    experts."""

    def checkAuthenticated(self, user):
        return user.in_admin


class OnlyVcsImportsAndAdmins(AuthorizationBase):
    """Base class that allows only the Launchpad admins and VCS Imports
    experts."""

    def checkAuthenticated(self, user):
        return user.in_admin or user.in_vcs_imports


class ViewPOTemplates(AnonymousAuthorization):
    """Anyone can view an IPOTemplate."""
    usedfor = IPOTemplate


class AdminPOTemplateDetails(OnlyRosettaExpertsAndAdmins):
    """Controls administration of an `IPOTemplate`.

    Allow all persons that can also administer the translations to
    which this template belongs to and also translation group owners.

    Product owners does not have administrative privileges.
    """

    permission = 'launchpad.Admin'
    usedfor = IPOTemplate

    def checkAuthenticated(self, user):
        template = self.obj
        if user.in_rosetta_experts or user.in_admin:
            return True
        if template.distroseries is not None:
            # Template is on a distribution.
            return (
                self.forwardCheckAuthenticated(user, template.distroseries,
                                               'launchpad.TranslationsAdmin'))
        else:
            # Template is on a product.
            return False


class EditPOTemplateDetails(AuthorizationBase):
    permission = 'launchpad.TranslationsAdmin'
    usedfor = IPOTemplate

    def checkAuthenticated(self, user):
        template = self.obj
        if template.distroseries is not None:
            # Template is on a distribution.
            return (
                user.isOwner(template) or
                self.forwardCheckAuthenticated(user, template.distroseries))
        else:
            # Template is on a product.
            return (
                user.isOwner(template) or
                self.forwardCheckAuthenticated(user, template.productseries))


class ViewPOFile(AnonymousAuthorization):
    """Anyone can view an IPOFile."""
    usedfor = IPOFile


class EditPOFile(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IPOFile

    def checkAuthenticated(self, user):
        """The `POFile` itself keeps track of this permission."""
        return self.obj.canEditTranslations(user.person)


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


class AdminTranslationImportQueueEntry(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = ITranslationImportQueueEntry

    def checkAuthenticated(self, user):
        if self.obj.distroseries is not None:
            series = self.obj.distroseries
        else:
            series = self.obj.productseries
        return (
            self.forwardCheckAuthenticated(user, series,
                                           'launchpad.TranslationsAdmin'))


class EditTranslationImportQueueEntry(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ITranslationImportQueueEntry

    def checkAuthenticated(self, user):
        """Anyone who can admin an entry, plus its owner or the owner of the
        product or distribution, can edit it.
        """
        return (self.forwardCheckAuthenticated(
                    user, self.obj, 'launchpad.Admin') or
                user.inTeam(self.obj.importer))


class AdminTranslationImportQueue(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ITranslationImportQueue


class AdminByBuilddAdmin(AuthorizationBase):
    permission = 'launchpad.Admin'

    def checkAuthenticated(self, user):
        """Allow admins and buildd_admins."""
        return user.in_buildd_admin or user.in_admin


class AdminBuilderSet(AdminByBuilddAdmin):
    usedfor = IBuilderSet


class AdminBuilder(AdminByBuilddAdmin):
    usedfor = IBuilder


class EditBuilder(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = IBuilder


class ModerateBuilder(EditBuilder):
    permission = 'launchpad.Moderate'
    usedfor = IBuilder

    def checkAuthenticated(self, user):
        return (user.in_registry_experts or
                super().checkAuthenticated(user))


class AdminBuildRecord(AdminByBuilddAdmin):
    usedfor = IBuildFarmJob


class EditBuildFarmJob(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = IBuildFarmJob


class EditPackageBuild(EditBuildFarmJob):
    usedfor = IPackageBuild

    def checkAuthenticated(self, user):
        """Check if the user has access to edit the archive."""
        if EditBuildFarmJob.checkAuthenticated(self, user):
            return True

        # If the user is in the owning team for the archive,
        # then they have access to edit the builds.
        # If it's a PPA or a copy archive only allow its owner.
        return (self.obj.archive.owner and
                user.inTeam(self.obj.archive.owner))


class ViewTranslationTemplatesBuild(DelegatedAuthorization):
    """Permission to view an `ITranslationTemplatesBuild`.

    Delegated to the build's branch.
    """
    permission = 'launchpad.View'
    usedfor = ITranslationTemplatesBuild

    def __init__(self, obj):
        super().__init__(obj, obj.branch)


class ViewLanguageSet(AnonymousAuthorization):
    """Anyone can view an ILangaugeSet."""
    usedfor = ILanguageSet


class AdminLanguageSet(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ILanguageSet


class ViewLanguage(AnonymousAuthorization):
    """Anyone can view an ILangauge."""
    usedfor = ILanguage


class AdminLanguage(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.Admin'
    usedfor = ILanguage


class AdminCustomLanguageCode(AuthorizationBase):
    """Controls administration for a custom language code.

    Whoever can admin a product's or distribution's translations can also
    admin the custom language codes for it.
    """
    permission = 'launchpad.TranslationsAdmin'
    usedfor = ICustomLanguageCode

    def checkAuthenticated(self, user):
        return self.forwardCheckAuthenticated(
            user,
            self.obj.product or self.obj.distribution
            )


class AdminLanguagePack(OnlyRosettaExpertsAndAdmins):
    permission = 'launchpad.LanguagePacksAdmin'
    usedfor = ILanguagePack


class ViewEmailAddress(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IEmailAddress

    def checkUnauthenticated(self):
        """See `AuthorizationBase`."""
        # Anonymous users can never see email addresses.
        return False

    def checkAuthenticated(self, user):
        """Can the user see the details of this email address?

        If the email address' owner doesn't want their email addresses to be
        hidden, anyone can see them.  Otherwise only the owner themselves or
        admins can see them.
        """
        # Always allow users to see their own email addresses.
        if self.obj.person == user:
            return True

        if not (self.obj.person is None or
                self.obj.person.hide_email_addresses):
            return True

        return (self.obj.person is not None and user.inTeam(self.obj.person)
                or user.in_commercial_admin
                or user.in_registry_experts
                or user.in_admin)


class EditEmailAddress(EditByOwnersOrAdmins):
    permission = 'launchpad.Edit'
    usedfor = IEmailAddress

    def checkAuthenticated(self, user):
        # Always allow users to see their own email addresses.
        if self.obj.person == user:
            return True
        return super().checkAuthenticated(user)


class EditLibraryFileAliasWithParent(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ILibraryFileAliasWithParent

    def checkAuthenticated(self, user):
        """Only persons which can edit an LFA's parent can edit an LFA.

        By default, a LibraryFileAlias does not know about its parent.
        Such aliases are never editable. Use an adapter to provide a
        parent object.

        If a parent is known, users which can edit the parent can also
        edit properties of the LibraryFileAlias.
        """
        parent = getattr(self.obj, '__parent__', None)
        if parent is None:
            return False
        return self.forwardCheckAuthenticated(user, parent)


class ViewLibraryFileAliasWithParent(AuthorizationBase):
    """Authorization class for viewing LibraryFileAliass having a parent."""

    permission = 'launchpad.View'
    usedfor = ILibraryFileAliasWithParent

    def checkAuthenticated(self, user):
        """Only persons which can edit an LFA's parent can edit an LFA.

        By default, a LibraryFileAlias does not know about its parent.

        If a parent is known, users which can view the parent can also
        view the LibraryFileAlias.
        """
        parent = getattr(self.obj, '__parent__', None)
        if parent is None:
            return False
        return self.forwardCheckAuthenticated(user, parent)


class SetMessageVisibility(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IMessage

    def checkAuthenticated(self, user):
        """Admins and registry admins can set bug comment visibility."""
        return (user.in_admin or user.in_registry_experts)


class EditMessage(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IMessage

    def checkAuthenticated(self, user):
        """Only message owner can edit it."""
        return user.isOwner(self.obj)


class EditMessageRevision(DelegatedAuthorization):
    permission = 'launchpad.Edit'
    usedfor = IMessageRevision

    def __init__(self, obj):
        super().__init__(obj, obj.message, 'launchpad.Edit')


class ViewPublisherConfig(AdminByAdminsTeam):
    usedfor = IPublisherConfig


class ViewWebhook(AuthorizationBase):
    """Webhooks can be viewed and edited by someone who can edit the target."""
    permission = 'launchpad.View'
    usedfor = IWebhook

    def checkUnauthenticated(self):
        return False

    def checkAuthenticated(self, user):
        yield self.obj.target, 'launchpad.Edit'


class ViewWebhookDeliveryJob(DelegatedAuthorization):
    """Webhooks can be viewed and edited by someone who can edit the target."""
    permission = 'launchpad.View'
    usedfor = IWebhookDeliveryJob

    def __init__(self, obj):
        super().__init__(obj, obj.webhook, 'launchpad.View')


class ViewSnap(AuthorizationBase):
    """Private snaps are only visible to their owners and admins."""
    permission = 'launchpad.View'
    usedfor = ISnap

    def checkAuthenticated(self, user):
        return self.obj.visibleByUser(user.person)

    def checkUnauthenticated(self):
        return self.obj.visibleByUser(None)


class EditSnap(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ISnap

    def checkAuthenticated(self, user):
        return (
            user.isOwner(self.obj) or
            user.in_commercial_admin or user.in_admin)


class AdminSnap(AuthorizationBase):
    """Restrict changing build settings on snap packages.

    The security of the non-virtualised build farm depends on these
    settings, so they can only be changed by "PPA"/commercial admins, or by
    "PPA" self admins on snap packages that they can already edit.
    """
    permission = 'launchpad.Admin'
    usedfor = ISnap

    def checkAuthenticated(self, user):
        if user.in_ppa_admin or user.in_commercial_admin or user.in_admin:
            return True
        return (
            user.in_ppa_self_admins
            and EditSnap(self.obj).checkAuthenticated(user))


class SnapSubscriptionEdit(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ISnapSubscription

    def checkAuthenticated(self, user):
        """Is the user able to edit a Snap recipe subscription?

        Any team member can edit a Snap recipe subscription for their
        team.
        Launchpad Admins can also edit any Snap recipe subscription.
        The owner of the subscribed Snap can edit the subscription. If
        the Snap owner is a team, then members of the team can edit
        the subscription.
        """
        return (user.inTeam(self.obj.snap.owner) or
                user.inTeam(self.obj.person) or
                user.inTeam(self.obj.subscribed_by) or
                user.in_admin)


class SnapSubscriptionView(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = ISnapSubscription

    def checkUnauthenticated(self):
        return self.obj.snap.visibleByUser(None)

    def checkAuthenticated(self, user):
        return self.obj.snap.visibleByUser(user.person)


class ViewSnapBuildRequest(DelegatedAuthorization):
    permission = 'launchpad.View'
    usedfor = ISnapBuildRequest

    def __init__(self, obj):
        super().__init__(obj, obj.snap, 'launchpad.View')


class ViewSnapBuild(DelegatedAuthorization):
    permission = 'launchpad.View'
    usedfor = ISnapBuild

    def iter_objects(self):
        yield self.obj.snap
        yield self.obj.archive


class EditSnapBuild(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = ISnapBuild

    def checkAuthenticated(self, user):
        """Check edit access for snap package builds.

        Allow admins, buildd admins, and the owner of the snap package.
        (Note that the requester of the build is required to be in the team
        that owns the snap package.)
        """
        auth_snap = EditSnap(self.obj.snap)
        if auth_snap.checkAuthenticated(user):
            return True
        return super().checkAuthenticated(user)


class AdminSnapBuild(AdminByBuilddAdmin):
    usedfor = ISnapBuild


class ViewSnappySeries(AnonymousAuthorization):
    """Anyone can view an `ISnappySeries`."""
    usedfor = ISnappySeries


class EditSnappySeries(EditByRegistryExpertsOrAdmins):
    usedfor = ISnappySeries


class EditSnappySeriesSet(EditByRegistryExpertsOrAdmins):
    usedfor = ISnappySeriesSet


class ViewSnapBase(AnonymousAuthorization):
    """Anyone can view an `ISnapBase`."""
    usedfor = ISnapBase


class EditSnapBase(EditByRegistryExpertsOrAdmins):
    usedfor = ISnapBase


class EditSnapBaseSet(EditByRegistryExpertsOrAdmins):
    usedfor = ISnapBaseSet


class ViewOCIProject(AnonymousAuthorization):
    """Anyone can view an `IOCIProject`."""
    usedfor = IOCIProject


class EditOCIProject(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IOCIProject

    def checkAuthenticated(self, user):
        """Maintainers, drivers, and admins can drive projects."""
        return (user.in_admin or
                user.isDriver(self.obj.pillar) or
                self.obj.pillar.canAdministerOCIProjects(user))


class EditOCIProjectSeries(DelegatedAuthorization):
    permission = 'launchpad.Edit'
    usedfor = IOCIProjectSeries

    def __init__(self, obj):
        super().__init__(obj, obj.oci_project)


class ViewOCIRecipeBuildRequest(DelegatedAuthorization):
    permission = 'launchpad.View'
    usedfor = IOCIRecipeBuildRequest

    def __init__(self, obj):
        super().__init__(obj, obj.recipe, 'launchpad.View')


class ViewOCIRecipe(AnonymousAuthorization):
    """Anyone can view public `IOCIRecipe`, but only subscribers can view
    private ones.
    """
    usedfor = IOCIRecipe

    def checkUnauthenticated(self):
        return self.obj.visibleByUser(None)

    def checkAuthenticated(self, user):
        return self.obj.visibleByUser(user.person)


class EditOCIRecipe(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IOCIRecipe

    def checkAuthenticated(self, user):
        return (
            user.isOwner(self.obj) or
            user.in_commercial_admin or user.in_admin)


class AdminOCIRecipe(AuthorizationBase):
    """Restrict changing build settings on OCI recipes.

    The security of the non-virtualised build farm depends on these
    settings, so they can only be changed by "PPA"/commercial admins, or by
    "PPA" self admins on OCI recipes that they can already edit.
    """
    permission = 'launchpad.Admin'
    usedfor = IOCIRecipe

    def checkAuthenticated(self, user):
        if user.in_ppa_admin or user.in_commercial_admin or user.in_admin:
            return True
        return (
            user.in_ppa_self_admins
            and EditSnap(self.obj).checkAuthenticated(user))


class OCIRecipeSubscriptionEdit(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IOCIRecipeSubscription

    def checkAuthenticated(self, user):
        """Is the user able to edit an OCI recipe subscription?

        Any team member can edit a OCI recipe subscription for their
        team.
        Launchpad Admins can also edit any OCI recipe subscription.
        The owner of the subscribed OCI recipe can edit the subscription. If
        the OCI recipe owner is a team, then members of the team can edit
        the subscription.
        """
        return (user.inTeam(self.obj.recipe.owner) or
                user.inTeam(self.obj.person) or
                user.inTeam(self.obj.subscribed_by) or
                user.in_admin)


class OCIRecipeSubscriptionView(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IOCIRecipeSubscription

    def checkUnauthenticated(self):
        return self.obj.recipe.visibleByUser(None)

    def checkAuthenticated(self, user):
        return self.obj.recipe.visibleByUser(user.person)


class ViewOCIRecipeBuild(DelegatedAuthorization):
    permission = 'launchpad.View'
    usedfor = IOCIRecipeBuild

    def iter_objects(self):
        yield self.obj.recipe


class EditOCIRecipeBuild(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = IOCIRecipeBuild

    def checkAuthenticated(self, user):
        """Check edit access for OCI recipe builds.

        Allow admins, buildd admins, and the owner of the OCI recipe.
        (Note that the requester of the build is required to be in the team
        that owns the OCI recipe.)
        """
        auth_recipe = EditOCIRecipe(self.obj.recipe)
        if auth_recipe.checkAuthenticated(user):
            return True
        return super().checkAuthenticated(user)


class AdminOCIRecipeBuild(AdminByBuilddAdmin):
    usedfor = IOCIRecipeBuild


class ViewOCIRegistryCredentials(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IOCIRegistryCredentials

    def checkAuthenticated(self, user):
        # This must be kept in sync with user_can_edit_credentials_for_owner
        # in lp.oci.interfaces.ociregistrycredentials.
        return (
            user.isOwner(self.obj) or
            user.in_admin)


class ViewOCIPushRule(AnonymousAuthorization):
    """Anyone can view an `IOCIPushRule`."""
    usedfor = IOCIPushRule


class OCIPushRuleEdit(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IOCIPushRule

    def checkAuthenticated(self, user):
        return (
            user.isOwner(self.obj.recipe) or
            user.in_commercial_admin or user.in_admin)


class ViewCharmRecipe(AuthorizationBase):
    """Private charm recipes are only visible to their owners and admins."""
    permission = 'launchpad.View'
    usedfor = ICharmRecipe

    def checkAuthenticated(self, user):
        return self.obj.visibleByUser(user.person)

    def checkUnauthenticated(self):
        return self.obj.visibleByUser(None)


class EditCharmRecipe(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = ICharmRecipe

    def checkAuthenticated(self, user):
        return (
            user.isOwner(self.obj) or
            user.in_commercial_admin or user.in_admin)


class AdminCharmRecipe(AuthorizationBase):
    """Restrict changing build settings on charm recipes.

    The security of the non-virtualised build farm depends on these
    settings, so they can only be changed by "PPA"/commercial admins, or by
    "PPA" self admins on charm recipes that they can already edit.
    """
    permission = 'launchpad.Admin'
    usedfor = ICharmRecipe

    def checkAuthenticated(self, user):
        if user.in_ppa_admin or user.in_commercial_admin or user.in_admin:
            return True
        return (
            user.in_ppa_self_admins
            and EditCharmRecipe(self.obj).checkAuthenticated(user))


class ViewCharmRecipeBuildRequest(DelegatedAuthorization):
    permission = 'launchpad.View'
    usedfor = ICharmRecipeBuildRequest

    def __init__(self, obj):
        super().__init__(obj, obj.recipe, 'launchpad.View')


class ViewCharmRecipeBuild(DelegatedAuthorization):
    permission = 'launchpad.View'
    usedfor = ICharmRecipeBuild

    def iter_objects(self):
        yield self.obj.recipe


class EditCharmRecipeBuild(AdminByBuilddAdmin):
    permission = 'launchpad.Edit'
    usedfor = ICharmRecipeBuild

    def checkAuthenticated(self, user):
        """Check edit access for snap package builds.

        Allow admins, buildd admins, and the owner of the charm recipe.
        (Note that the requester of the build is required to be in the team
        that owns the charm recipe.)
        """
        auth_recipe = EditCharmRecipe(self.obj.recipe)
        if auth_recipe.checkAuthenticated(user):
            return True
        return super().checkAuthenticated(user)


class AdminCharmRecipeBuild(AdminByBuilddAdmin):
    usedfor = ICharmRecipeBuild


class ViewCharmBase(AnonymousAuthorization):
    """Anyone can view an `ICharmBase`."""
    usedfor = ICharmBase


class EditCharmBase(EditByRegistryExpertsOrAdmins):
    usedfor = ICharmBase


class EditCharmBaseSet(EditByRegistryExpertsOrAdmins):
    usedfor = ICharmBaseSet
