# Copyright 2010-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for the Launchpad application.

Note that these are not interfaces to application content objects.
"""

__all__ = [
    "IHasIcon",
    "IHasLogo",
    "IHasMugshot",
    "IHeadingContext",
    "ILaunchpadCelebrities",
    "ILaunchpadUsage",
    "IPrivacy",
    "IServiceUsage",
]

from lazr.restful.declarations import exported
from zope.interface import Attribute, Interface
from zope.schema import Bool, Choice

from lp import _
from lp.app.enums import ServiceUsage


class ILaunchpadCelebrities(Interface):
    """Well known things.

    Celebrities are database objects that have a well-known name.
    """

    admin = Attribute("The 'admins' team.")
    software_center_agent = Attribute("The Software Center Agent.")
    bug_importer = Attribute("The bug importer.")
    bug_watch_updater = Attribute("The Bug Watch Updater.")
    buildd_admin = Attribute("The Build Daemon administrator.")
    commercial_admin = Attribute("The Launchpad Commercial team.")
    debbugs = Attribute("The Debian Bug Tracker")
    debian = Attribute("The Debian Distribution.")
    english = Attribute("The English language.")
    gnome_bugzilla = Attribute("The Gnome Bugzilla.")
    janitor = Attribute("The Launchpad Janitor.")
    katie = Attribute("The Debian Auto-sync user.")
    launchpad = Attribute("The Launchpad project.")
    launchpad_developers = Attribute("The Launchpad development team.")
    obsolete_junk = Attribute("The Obsolete Junk project.")
    ppa_admin = Attribute("The Launchpad PPA Admins team.")
    ppa_key_guard = Attribute("The PPA signing keys owner.")
    ppa_self_admins = Attribute("The Launchpad PPA Self Admins team.")
    registry_experts = Attribute("The Registry Administrators team.")
    rosetta_experts = Attribute("The Rosetta Experts team.")
    savannah_tracker = Attribute("The GNU Savannah Bug Tracker.")
    sourceforge_tracker = Attribute("The SourceForge Bug Tracker")
    ubuntu = Attribute("The Ubuntu Distribution.")
    ubuntu_archive_mirror = Attribute("The main archive mirror for Ubuntu.")
    ubuntu_bugzilla = Attribute("The Ubuntu Bugzilla.")
    ubuntu_cdimage_mirror = Attribute("The main cdimage mirror for Ubuntu.")
    ubuntu_sso = Attribute("The Ubuntu One login service.")
    ubuntu_techboard = Attribute("The Ubuntu technical board.")
    vcs_imports = Attribute("The 'vcs-imports' team.")

    def isCelebrityPerson(name):
        """Return true if there is an IPerson celebrity with the given name."""

    def clearCache():
        """Clear any cached celebrities."""


class IServiceUsage(Interface):
    """Pillar service usages."""

    # XXX: BradCrittenden 2010-08-06 bug=n/a:  I hate using the term 'pillar'
    # but cannot use 'project' or 'distribution'.  The phrase 'Where does'
    # implies an actual location not an answer of "Launchpad, externally, or
    # neither."
    answers_usage = Choice(
        title=_("Type of service for answers application"),
        description=_("Where does this pillar have an Answers forum?"),
        default=ServiceUsage.UNKNOWN,
        vocabulary=ServiceUsage,
    )
    blueprints_usage = Choice(
        title=_("Type of service for blueprints application"),
        description=_("Where does this pillar host blueprints?"),
        default=ServiceUsage.UNKNOWN,
        vocabulary=ServiceUsage,
    )
    codehosting_usage = Choice(
        title=_("Type of service for hosting code"),
        description=_("Where does this pillar host code?"),
        default=ServiceUsage.UNKNOWN,
        vocabulary=ServiceUsage,
    )
    translations_usage = exported(
        Choice(
            title=_("Type of service for translations application"),
            description=_("Where does this pillar do translations?"),
            default=ServiceUsage.UNKNOWN,
            vocabulary=ServiceUsage,
        ),
        as_of="devel",
    )
    bug_tracking_usage = Choice(
        title=_("Type of service for tracking bugs"),
        description=_("Where does this pillar track bugs?"),
        default=ServiceUsage.UNKNOWN,
        vocabulary=ServiceUsage,
    )
    uses_launchpad = Bool(title=_("Uses Launchpad for something."))


class ILaunchpadUsage(Interface):
    """How the project uses Launchpad."""

    official_answers = exported(
        Bool(
            title=_("People can ask questions in Launchpad Answers"),
            required=True,
        )
    )
    official_blueprints = exported(
        Bool(title=_("This project uses blueprints"), required=True)
    )
    official_codehosting = exported(
        Bool(
            title=_(
                "Code for this project is published in Bazaar branches on"
                " Launchpad"
            ),
            required=True,
        )
    )
    official_malone = exported(
        Bool(
            title=_("Bugs in this project are tracked in Launchpad"),
            required=True,
        ),
        exported_as="official_bugs",
    )
    official_anything = Bool(title=_("Uses Launchpad for something"))
    enable_bug_expiration = Bool(
        title=_('Expire "Incomplete" bug reports when they become inactive'),
        required=True,
    )


class IHasIcon(Interface):
    """An object that can have a custom icon."""

    # Each of the objects that implements this needs a custom schema, so
    # here we can just use Attributes
    icon = Attribute("The 14x14 icon.")


class IHasLogo(Interface):
    """An object that can have a custom logo."""

    # Each of the objects that implements this needs a custom schema, so
    # here we can just use Attributes
    logo = Attribute("The 64x64 logo.")


class IHasMugshot(Interface):
    """An object that can have a custom mugshot."""

    # Each of the objects that implements this needs a custom schema, so
    # here we can just use Attributes
    mugshot = Attribute("The 192x192 mugshot.")


class IPrivacy(Interface):
    """Something that can be private."""

    private = Bool(
        title=_("This is private"),
        required=False,
        description=_(
            "Private objects are visible to members or subscribers."
        ),
    )


class IHeadingContext(Interface):
    """Something that appears in a page's header section.

    This is a marker to allow views to avoid duplicating header
    information in the body. The header is generated from
    IHeadingBreadcrumbs, so you also need to define one of those for
    each of these.
    """
