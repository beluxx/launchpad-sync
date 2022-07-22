# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Archive dependencies helper function.

This module contains the static maps representing the 'layered' component
and pocket dependencies and helper function to handle `ArchiveDependency`
records.

 * pocket_dependencies: static map of pocket dependencies

Auxiliary functions exposed for testing purposes:

 * get_components_for_context: return the corresponding component
       dependencies for a component and pocket, this result is known as
       'ogre_components';
 * get_primary_current_component: return the component where the
       building source is published in the primary archive.

`sources_list` content generation.

 * get_sources_list_for_building: return a list of `sources_list` lines
       that should be used to build the given `IBuild`.

"""

__all__ = [
    "default_component_dependency_name",
    "default_pocket_dependency",
    "expand_dependencies",
    "get_components_for_context",
    "get_primary_current_component",
    "get_sources_list_for_building",
    "pocket_dependencies",
]

import base64
import logging
import traceback

from lazr.uri import URI
from twisted.internet import defer
from twisted.internet.threads import deferToThread
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.errors import NotFoundError
from lp.registry.interfaces.distroseriesparent import IDistroSeriesParentSet
from lp.registry.interfaces.pocket import PackagePublishingPocket, pocketsuffix
from lp.services.gpg.interfaces import GPGKeyNotFoundError, IGPGHandler
from lp.services.timeout import default_timeout
from lp.soyuz.enums import ArchivePurpose, PackagePublishingStatus
from lp.soyuz.interfaces.archive import ALLOW_RELEASE_BUILDS
from lp.soyuz.interfaces.component import IComponentSet

component_dependencies = {
    "main": ["main"],
    "restricted": ["main", "restricted"],
    "universe": ["main", "universe"],
    "multiverse": ["main", "restricted", "universe", "multiverse"],
    "partner": ["partner"],
}

# If strict_supported_component_dependencies is disabled, treat the
# left-hand components like the right-hand components for the purposes of
# finding component dependencies.
lax_component_map = {
    "main": "universe",
    "restricted": "multiverse",
}

pocket_dependencies = {
    PackagePublishingPocket.RELEASE: (PackagePublishingPocket.RELEASE,),
    PackagePublishingPocket.SECURITY: (
        PackagePublishingPocket.RELEASE,
        PackagePublishingPocket.SECURITY,
    ),
    PackagePublishingPocket.UPDATES: (
        PackagePublishingPocket.RELEASE,
        PackagePublishingPocket.SECURITY,
        PackagePublishingPocket.UPDATES,
    ),
    PackagePublishingPocket.BACKPORTS: (
        PackagePublishingPocket.RELEASE,
        PackagePublishingPocket.SECURITY,
        PackagePublishingPocket.UPDATES,
        PackagePublishingPocket.BACKPORTS,
    ),
    PackagePublishingPocket.PROPOSED: (
        PackagePublishingPocket.RELEASE,
        PackagePublishingPocket.SECURITY,
        PackagePublishingPocket.UPDATES,
        PackagePublishingPocket.PROPOSED,
    ),
}

default_pocket_dependency = PackagePublishingPocket.UPDATES

default_component_dependency_name = "multiverse"


def get_components_for_context(component, distroseries, pocket):
    """Return the components allowed to be used in the build context.

    :param component: the context `IComponent`.
    :param distroseries: the context `IDistroSeries`.
    :param pocket: the context `IPocket`.
    :return: a list of component names.
    """
    # BACKPORTS should be able to fetch build dependencies from any
    # component in order to cope with component changes occurring
    # across distroseries. See bug #198936 for further information.
    if pocket == PackagePublishingPocket.BACKPORTS:
        return component_dependencies["multiverse"]

    component_name = component.name
    if not distroseries.strict_supported_component_dependencies:
        component_name = lax_component_map.get(component_name, component_name)
    return component_dependencies[component_name]


def get_primary_current_component(archive, distroseries, sourcepackagename):
    """Return the component of the primary archive ancestry.

    If no ancestry could be found, default to 'universe'.
    """
    primary_archive = archive.distribution.main_archive
    if sourcepackagename is None:
        ancestry = None
    else:
        ancestry = primary_archive.getPublishedSources(
            name=sourcepackagename, distroseries=distroseries, exact_match=True
        ).first()

    if ancestry is not None:
        return ancestry.component
    else:
        return getUtility(IComponentSet)["universe"]


def expand_dependencies(
    archive,
    distro_arch_series,
    pocket,
    component,
    source_package_name,
    archive_dependencies,
    tools_source=None,
    tools_fingerprint=None,
    logger=None,
):
    """Return the set of dependency archives, pockets and components.

    :param archive: the context `IArchive`.
    :param distro_arch_series: the context `IDistroArchSeries`.
    :param pocket: the context `PackagePublishingPocket`.
    :param component: the context `IComponent`.
    :param source_package_name: A source package name (as text)
    :param archive_dependencies: a sequence of `IArchiveDependency` objects
        to use as additional user-selected archive dependencies.
    :param tools_source: if not None, a sources.list entry to use as an
        additional dependency for build tools, just before the default
        primary archive.
    :param tools_fingerprint: if not None, the OpenPGP signing key
        fingerprint for the archive given in `tools_source`.
    :param logger: an optional logger.
    :return: a list of (archive, distro_arch_series, pocket, [component]),
        representing the dependencies defined by the given build context.
    """
    distro_series = distro_arch_series.distroseries
    deps = []

    # Add implicit self-dependency for non-primary contexts.
    if archive.purpose in ALLOW_RELEASE_BUILDS:
        for expanded_pocket in pocket_dependencies[pocket]:
            deps.append(
                (
                    archive,
                    distro_arch_series,
                    expanded_pocket,
                    get_components_for_context(
                        component, distro_series, expanded_pocket
                    ),
                )
            )

    primary_component = get_primary_current_component(
        archive, distro_series, source_package_name
    )
    # Consider user-selected archive dependencies.
    for archive_dependency in archive_dependencies:
        # When the dependency component is undefined, we should use
        # the component where the source is published in the primary
        # archive.
        if archive_dependency.component is None:
            archive_component = primary_component
        else:
            archive_component = archive_dependency.component
        components = get_components_for_context(
            archive_component, distro_series, archive_dependency.pocket
        )
        # Follow pocket dependencies.
        for expanded_pocket in pocket_dependencies[archive_dependency.pocket]:
            deps.append(
                (
                    archive_dependency.dependency,
                    distro_arch_series,
                    expanded_pocket,
                    components,
                )
            )

    # Consider build tools archive dependencies.
    if tools_source is not None:
        try:
            deps.append(
                (
                    tools_source % {"series": distro_series.name},
                    tools_fingerprint,
                )
            )
        except Exception:
            # Someone messed up the configuration; don't add it.
            if logger is not None:
                logger.error(
                    "Exception processing build tools sources.list entry:\n%s"
                    % traceback.format_exc()
                )

    # Consider primary archive dependency override. Add the default
    # primary archive dependencies if it's not present.
    if not any(
        archive_dependency.dependency == archive.distribution.main_archive
        for archive_dependency in archive_dependencies
    ):
        primary_dependencies = _get_default_primary_dependencies(
            archive, distro_arch_series, component, pocket
        )
        deps.extend(primary_dependencies)

    # Add dependencies for overlay archives defined in DistroSeriesParent.
    # This currently only applies for derived distributions but in the future
    # should be merged with ArchiveDependency so we don't have two separate
    # tables essentially doing the same thing.
    dsp_set = getUtility(IDistroSeriesParentSet)
    for dsp in dsp_set.getFlattenedOverlayTree(distro_series):
        try:
            dep_arch_series = dsp.parent_series.getDistroArchSeries(
                distro_arch_series.architecturetag
            )
            dep_archive = dsp.parent_series.distribution.main_archive
            components = get_components_for_context(
                dsp.component, dep_arch_series.distroseries, dsp.pocket
            )
            # Follow pocket dependencies.
            for expanded_pocket in pocket_dependencies[dsp.pocket]:
                deps.append(
                    (dep_archive, dep_arch_series, expanded_pocket, components)
                )
        except NotFoundError:
            pass

    return deps


@defer.inlineCallbacks
def get_sources_list_for_building(
    behaviour,
    distroarchseries,
    sourcepackagename,
    archive_dependencies=None,
    tools_source=None,
    tools_fingerprint=None,
    logger=None,
):
    """Return sources.list entries and keys required to build the given item.

    The sources.list entries are returned in the order that is most useful:
     1. the context archive itself
     2. external dependencies
     3. user-selected archive dependencies
     4. the default primary archive

    The keys are in an arbitrary order.

    :param behaviour: the `IBuildFarmJobBehaviour` for the context
        `IBuildFarmJob`.
    :param distroarchseries: A `IDistroArchSeries`
    :param sourcepackagename: A source package name (as text)
    :param archive_dependencies: a sequence of `IArchiveDependency` objects
        to use as additional user-selected archive dependencies.  If None,
        use the dependencies of the build's archive.
    :param tools_source: if not None, a sources.list entry to use as an
        additional dependency for build tools, just before the default
        primary archive.
    :param tools_fingerprint: if not None, the OpenPGP signing key
        fingerprint for the archive given in `tools_source`.
    :param logger: an optional logger.
    :return: a Deferred resolving to a tuple containing a list of deb
        sources.list entries (lines) and a list of base64-encoded public
        keys.
    """
    build = behaviour.build
    if archive_dependencies is None:
        archive_dependencies = build.archive.dependencies
    deps = expand_dependencies(
        build.archive,
        distroarchseries,
        build.pocket,
        build.current_component,
        sourcepackagename,
        archive_dependencies,
        tools_source=tools_source,
        tools_fingerprint=tools_fingerprint,
        logger=logger,
    )
    (
        sources_list_lines,
        trusted_keys,
    ) = yield _get_sources_list_for_dependencies(
        behaviour, deps, logger=logger
    )

    external_dep_lines = []
    # Append external sources.list lines for this build if specified.  No
    # series substitution is needed here, so we don't have to worry about
    # malformedness.
    dependencies = build.external_dependencies
    if dependencies is not None:
        for line in dependencies.splitlines():
            external_dep_lines.append(line)
    # Append external sources.list lines for this archive if it's
    # specified in the configuration.
    try:
        dependencies = build.archive.external_dependencies
        if dependencies is not None:
            for archive_dep in dependencies.splitlines():
                line = archive_dep % (
                    {"series": distroarchseries.distroseries.name}
                )
                external_dep_lines.append(line)
    except Exception:
        # Malformed external dependencies can incapacitate the build farm
        # manager (lp:516169). That's obviously not acceptable.
        # Log the error, and disable the PPA.
        logger = logging.getLogger()
        logger.error(
            "Exception during external dependency processing:\n%s"
            % traceback.format_exc()
        )
        # Disable the PPA if needed. This will suspend all the pending binary
        # builds associated with the problematic PPA.
        if build.archive.enabled == True:
            build.archive.disable()

    # For an unknown reason (perhaps because OEM has archives with
    # binaries that need to override primary binaries of the same
    # version), we want the external dependency lines to show up second:
    # after the archive itself, but before any other dependencies.
    return (
        [sources_list_lines[0]] + external_dep_lines + sources_list_lines[1:],
        trusted_keys,
    )


def _has_published_binaries(archive, distroarchseries, pocket):
    """Whether or not the archive dependency has published binaries."""
    # The primary archive dependencies are always relevant.
    if archive.purpose == ArchivePurpose.PRIMARY:
        return True

    published_binaries = archive.getAllPublishedBinaries(
        distroarchseries=distroarchseries,
        pocket=pocket,
        status=PackagePublishingStatus.PUBLISHED,
    )
    return not published_binaries.is_empty()


@defer.inlineCallbacks
def _get_binary_sources_list_line(
    behaviour, archive, distroarchseries, pocket, components
):
    """Return the corresponding binary sources_list line."""
    # Encode the private PPA repository password in the
    # sources_list line. Note that the buildlog will be
    # sanitized to not expose it.
    if archive.private:
        uri = URI(archive.archive_url)
        macaroon_raw = yield behaviour.issueMacaroon()
        uri = uri.replace(userinfo="buildd:%s" % macaroon_raw)
        url = str(uri)
    else:
        url = archive.archive_url

    suite = distroarchseries.distroseries.name + pocketsuffix[pocket]
    return "deb %s %s %s" % (url, suite, " ".join(components))


@defer.inlineCallbacks
def _get_sources_list_for_dependencies(behaviour, dependencies, logger=None):
    """Return sources.list entries and keys.

    Process the given list of dependency tuples for the given
    `DistroArchseries`.

    :param behaviour: the build's `IBuildFarmJobBehaviour`.
    :param dependencies: list of 3 elements tuples as:
        (`IArchive`, `IDistroArchSeries`, `PackagePublishingPocket`,
         list of `IComponent` names)
    :param distroarchseries: target `IDistroArchSeries`;

    :return: a tuple containing a list of sources.list formatted lines and a
        list of base64-encoded public keys.
    """
    sources_list_lines = []
    trusted_keys = {}
    # The handler's security proxying doesn't protect anything useful here,
    # and the thread that we defer key retrieval to doesn't have an
    # interaction.
    gpghandler = removeSecurityProxy(getUtility(IGPGHandler))
    for dep in dependencies:
        if len(dep) == 2:
            sources_list_line, fingerprint = dep
            sources_list_lines.append(sources_list_line)
        else:
            archive, distro_arch_series, pocket, components = dep
            has_published_binaries = _has_published_binaries(
                archive, distro_arch_series, pocket
            )
            if not has_published_binaries:
                continue
            archive_components = {
                component.name
                for component in archive.getComponentsForSeries(
                    distro_arch_series.distroseries
                )
            }
            components = [
                component
                for component in components
                if component in archive_components
            ]
            sources_list_line = yield _get_binary_sources_list_line(
                behaviour, archive, distro_arch_series, pocket, components
            )
            sources_list_lines.append(sources_list_line)
            fingerprint = archive.signing_key_fingerprint
        if fingerprint is not None and fingerprint not in trusted_keys:

            def get_key():
                with default_timeout(15.0):
                    try:
                        return gpghandler.retrieveKey(fingerprint)
                    except GPGKeyNotFoundError as e:
                        # For now, just log this and proceed without the
                        # key.  We'll have to fix any outstanding cases of
                        # this before we can switch to requiring
                        # authentication across the board.
                        if logger is not None:
                            logger.warning(str(e))
                        return None

            key = yield deferToThread(get_key)
            if key is not None:
                trusted_keys[fingerprint] = base64.b64encode(
                    key.export()
                ).decode("ASCII")

    return (sources_list_lines, [v for k, v in sorted(trusted_keys.items())])


def _get_default_primary_dependencies(
    archive, distro_arch_series, component, pocket
):
    """Return the default primary dependencies for a given context.

    :param archive: the context `IArchive`.
    :param distro_arch_series: the context `IDistroArchSeries`.
    :param component: the context `IComponent`.
    :param pocket: the context `PackagePublishingPocket`.

    :return: a list containing the default dependencies to primary
        archive.
    """
    if archive.purpose in ALLOW_RELEASE_BUILDS:
        component = getUtility(IComponentSet)[
            default_component_dependency_name
        ]
        pocket = default_pocket_dependency
    primary_components = get_components_for_context(
        component, distro_arch_series.distroseries, pocket
    )
    primary_pockets = pocket_dependencies[pocket]

    primary_dependencies = []
    for pocket in primary_pockets:
        primary_dependencies.append(
            (
                archive.distribution.main_archive,
                distro_arch_series,
                pocket,
                primary_components,
            )
        )

    return primary_dependencies
