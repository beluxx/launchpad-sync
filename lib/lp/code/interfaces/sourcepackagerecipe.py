# Copyright 2009-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface of the `SourcePackageRecipe` content type."""

__all__ = [
    'IRecipeBranchSource',
    'ISourcePackageRecipe',
    'ISourcePackageRecipeData',
    'ISourcePackageRecipeDataSource',
    'ISourcePackageRecipeSource',
    'MINIMAL_RECIPE_TEXT_BZR',
    'MINIMAL_RECIPE_TEXT_GIT',
    'RecipeBranchType',
    ]


from textwrap import dedent

from lazr.enum import (
    EnumeratedType,
    Item,
    )
from lazr.lifecycle.snapshot import doNotSnapshot
from lazr.restful.declarations import (
    call_with,
    export_read_operation,
    export_write_operation,
    exported,
    exported_as_webservice_entry,
    mutator_for,
    operation_for_version,
    operation_parameters,
    operation_returns_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    ReferenceChoice,
    )
from lazr.restful.interface import copy_field
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Int,
    List,
    Text,
    TextLine,
    )

from lp import _
from lp.app.validators.name import name_validator
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.gitrepository import IGitRepository
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.role import IHasOwner
from lp.services.fields import (
    Description,
    PersonChoice,
    PublicPersonChoice,
    )
from lp.soyuz.interfaces.archive import IArchive


MINIMAL_RECIPE_TEXT_BZR = dedent('''\
    # bzr-builder format 0.3 deb-version {debupstream}-0~{revno}
    %s
    ''')


MINIMAL_RECIPE_TEXT_GIT = dedent('''\
    # git-build-recipe format 0.4 deb-version {debupstream}-0~{revtime}
    %s %s
    ''')


class ISourcePackageRecipeData(Interface):
    """A recipe as database data, not text."""

    base_branch = exported(
        Reference(
            IBranch, title=_("The base branch used by this recipe."),
            required=False, readonly=True))
    base_git_repository = exported(
        Reference(
            IGitRepository,
            title=_("The base Git repository used by this recipe."),
            required=False, readonly=True))
    base = Attribute(
        "The base branch/repository used by this recipe (VCS-agnostic).")

    deb_version_template = exported(
        TextLine(
            title=_('deb-version template'), readonly=True,
            description=_(
                'The template that will be used to generate a deb version.')))

    def getReferencedBranches():
        """An iterator of the branches referenced by this recipe."""


class RecipeBranchType(EnumeratedType):
    """The revision control system used for a recipe."""

    BZR = Item("Bazaar")

    GIT = Item("Git")


class IRecipeBranchSource(Interface):

    def getParsedRecipe(recipe_text):
        """Parse recipe text into recipe data.

        :param recipe_text: Recipe text as a string.
        :return: a tuple of a `RecipeBranch` representing the recipe and a
            `RecipeBranchType` indicating the revision control system to be
            used for the recipe.
        """


class ISourcePackageRecipeDataSource(Interface):

    def createManifestFromText(text, sourcepackage_recipe_build):
        """Create a manifest for the specified build.

        :param text: The text of the recipe to create a manifest for.
        :param sourcepackage_recipe_build: The build to associate the manifest
            with.
        :return: an instance of `SourcePackageRecipeData`.
        """


class ISourcePackageRecipeView(Interface):
    """IBranch attributes that require launchpad.View permission."""

    id = Int()

    date_created = Datetime(required=True, readonly=True)

    registrant = exported(
        PublicPersonChoice(
            title=_("The person who created this recipe."),
            required=True, readonly=True,
            vocabulary='ValidPersonOrTeam'))

    def getRecipeText(validate=False):
        """Return the text of this recipe.

        :param validate: If True, check that the recipe text can be parsed.
        """

    recipe_text = exported(Text(readonly=True))

    pending_builds = exported(doNotSnapshot(
        CollectionField(
            title=_("The pending builds of this recipe."),
            description=_('Pending builds of this recipe, sorted in '
                    'descending order of creation.'),
            value_type=Reference(schema=Interface),
            readonly=True)))

    completed_builds = exported(doNotSnapshot(
        CollectionField(
            title=_("The completed builds of this recipe."),
            description=_('Completed builds of this recipe, sorted in '
                    'descending order of finishing (or starting if not'
                    'completed successfully).'),
            value_type=Reference(schema=Interface),
            readonly=True)))

    builds = exported(doNotSnapshot(
        CollectionField(
            title=_("All builds of this recipe."),
            description=_('All builds of this recipe, sorted in '
                    'descending order of finishing (or starting if not'
                    'completed successfully).'),
            value_type=Reference(schema=Interface),
            readonly=True)))

    last_build = exported(
        Reference(
            Interface,
            title=_("The the most recent build of this recipe."),
            readonly=True))

    @call_with(requester=REQUEST_USER)
    @operation_parameters(
        archive=Reference(schema=IArchive),
        distroseries=Reference(schema=IDistroSeries),
        pocket=Choice(vocabulary=PackagePublishingPocket,))
    @operation_returns_entry(Interface)
    @export_write_operation()
    @operation_for_version("beta")
    def requestBuild(archive, distroseries, requester, pocket):
        """Request that the recipe be built in to the specified archive.

        :param archive: The IArchive which you want the build to end up in.
        :param requester: the person requesting the build.
        :param pocket: the pocket that should be targeted.
        :raises: various specific upload errors if the requestor is not
            able to upload to the archive.
        """

    def containsUnbuildableSeries(archive):
        """Does the recipe contain series that can not be built into.
        """

    @export_write_operation()
    @operation_for_version("beta")
    def performDailyBuild():
        """Perform a build into the daily build archive."""

    @export_read_operation()
    @operation_for_version("devel")
    def getPendingBuildInfo():
        """Find distroseries and archive data for pending builds.

        Return a list of dict(
        distroseries:distroseries.displayname
        archive:archive.token)
        The archive reference is as defined by the archive vocab.
        This information is used to construct the request builds popup form.
        """


class ISourcePackageRecipeEditableAttributes(IHasOwner):
    """ISourcePackageRecipe attributes that can be edited.

    These attributes need launchpad.View to see, and launchpad.Edit to change.
    """
    daily_build_archive = exported(Reference(
        IArchive, title=_("The archive to use for daily builds.")))

    builder_recipe = Attribute(
        _("The bzr-builder data structure for the recipe."))

    owner = exported(
        PersonChoice(
            title=_('Owner'),
            required=True, readonly=False,
            vocabulary='UserTeamsParticipationPlusSelf',
            description=_("The person or team who can edit this recipe.")))

    distroseries = exported(List(
        ReferenceChoice(schema=IDistroSeries,
            vocabulary='BuildableDistroSeries'),
        title=_("Default distribution series"),
        description=_("If built daily, these are the distribution "
            "versions that the recipe will be built for."),
        readonly=True))
    build_daily = exported(Bool(
        title=_("Built daily"),
        description=_(
            "Automatically build each day, if the source has changed.")))

    name = exported(TextLine(
            title=_("Name"), required=True,
            constraint=name_validator,
            description=_(
                "The name of the recipe is part of the URL and needs to "
                "be unique for the given owner.")))

    description = exported(Description(
        title=_('Description'), required=False,
        description=_('A short description of the recipe.')))

    date_last_modified = exported(
        Datetime(required=True, readonly=True))

    is_stale = exported(
        Bool(title=_('Recipe is stale.'), required=True, readonly=True))


class ISourcePackageRecipeEdit(Interface):
    """ISourcePackageRecipe methods that require launchpad.Edit permission."""

    @mutator_for(ISourcePackageRecipeView['recipe_text'])
    @operation_for_version("devel")
    @operation_parameters(
        recipe_text=copy_field(
            ISourcePackageRecipeView['recipe_text']))
    @export_write_operation()
    @operation_for_version("beta")
    def setRecipeText(recipe_text):
        """Set the text of the recipe."""

    @mutator_for(ISourcePackageRecipeEditableAttributes['distroseries'])
    @operation_parameters(distroseries=copy_field(
        ISourcePackageRecipeEditableAttributes['distroseries']))
    @export_write_operation()
    @operation_for_version("devel")
    def updateSeries(distroseries):
        """Replace this recipe's distro series."""


class ISourcePackageRecipeDelete(Interface):
    """ISourcePackageRecipe methods that require launchpad.Delete."""

    def destroySelf():
        """Remove this SourcePackageRecipe from the database.

        This requires deleting any rows with non-nullable foreign key
        references to this object.
        """


@exported_as_webservice_entry(as_of="beta")
class ISourcePackageRecipe(ISourcePackageRecipeData,
    ISourcePackageRecipeEdit, ISourcePackageRecipeEditableAttributes,
    ISourcePackageRecipeView):
    """An ISourcePackageRecipe describes how to build a source package.

    More precisely, it describes how to combine a number of branches into a
    debianized source tree.
    """


class ISourcePackageRecipeSource(Interface):
    """A utility of this interface can be used to create and access recipes.
    """

    def new(registrant, owner, distroseries, name,
            builder_recipe, description, date_created):
        """Create an `ISourcePackageRecipe`."""

    def exists(owner, name):
        """Check to see if a recipe by the same name and owner exists."""
