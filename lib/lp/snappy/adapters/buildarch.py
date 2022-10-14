# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "determine_architectures_to_build",
]

from collections import Counter
from typing import Any, Dict, List, Optional, Union

from lp.services.helpers import english_list
from lp.snappy.interfaces.snapbase import SnapBaseFeature
from lp.snappy.model.snapbase import SnapBase


class SnapArchitecturesParserError(Exception):
    """Base class for all exceptions in this module."""


class MissingPropertyError(SnapArchitecturesParserError):
    """Error for when an expected property is not present in the YAML."""

    def __init__(self, prop):
        super().__init__(
            "Architecture specification is missing the {!r} property".format(
                prop
            )
        )
        self.property = prop


class IncompatibleArchitecturesStyleError(SnapArchitecturesParserError):
    """Error for when architectures mix incompatible styles."""

    def __init__(self):
        super().__init__(
            "'architectures' must either be a list of strings or dicts, not "
            "both"
        )


class DuplicateBuildOnError(SnapArchitecturesParserError):
    """Error for when multiple `build-on`s include the same architecture."""

    def __init__(self, duplicates):
        super().__init__(
            "{} {} present in the 'build-on' of multiple items".format(
                english_list(duplicates),
                "is" if len(duplicates) == 1 else "are",
            )
        )


class UnsupportedBuildOnError(SnapArchitecturesParserError):
    """Error for when a requested architecture is not supported."""

    def __init__(self, build_on):
        super().__init__(
            "build-on specifies no supported architectures: {!r}".format(
                build_on
            )
        )
        self.build_on = build_on


class SnapArchitecture:
    """A single entry in the snapcraft.yaml 'architectures' list."""

    def __init__(
        self,
        build_on: Union[str, List[str]],
        build_for: Optional[Union[str, List[str]]] = None,
        build_error: Optional[str] = None,
    ):
        """Create a new architecture entry.

        :param build_on: string or list; build-on property from
            snapcraft.yaml.
        :param build_for: string or list; build-for property from
            snapcraft.yaml (defaults to build_on).
        :param build_error: string; build-error property from
            snapcraft.yaml.
        """
        self.build_on = (
            [build_on] if isinstance(build_on, str) else build_on
        )  # type: List[str]
        if build_for:
            self.build_for = (
                [build_for] if isinstance(build_for, str) else build_for
            )  # type: List[str]
        else:
            self.build_for = self.build_on
        self.build_error = build_error

    @classmethod
    def from_dict(cls, properties):
        """Create a new architecture entry from a dict."""
        try:
            build_on = properties["build-on"]
        except KeyError:
            raise MissingPropertyError("build-on")

        build_for = properties.get("build-for", properties.get("run-on"))

        return cls(
            build_on=build_on,
            build_for=build_for,
            build_error=properties.get("build-error"),
        )


class SnapBuildInstance:
    """A single instance of a snap that should be built.

    It has two useful attributes:

      - architecture: The architecture tag that should be used to build the
            snap.
      - target_architectures: The architecture tags of the snaps expected to
            be produced by this recipe (which may differ from `architecture`
            in the case of cross-building)
      - required: Whether or not failure to build should cause the entire
            set to fail.
    """

    def __init__(
        self,
        architecture: SnapArchitecture,
        supported_architectures: List[str],
    ):
        """Construct a new `SnapBuildInstance`.

        :param architecture: `SnapArchitecture` instance.
        :param supported_architectures: List of supported architectures,
            sorted by priority.
        """
        try:
            self.architecture = next(
                arch
                for arch in supported_architectures
                if arch in architecture.build_on
            )
        except StopIteration:
            raise UnsupportedBuildOnError(architecture.build_on)

        self.target_architectures = architecture.build_for
        self.required = architecture.build_error != "ignore"


def determine_architectures_to_build(
    snap_base: Optional[SnapBase],
    snapcraft_data: Dict[str, Any],
    supported_arches: List[str],
) -> List[SnapBuildInstance]:
    """Return a list of architectures to build based on snapcraft.yaml.

    :param snap_base: Name of the snap base.
    :param snapcraft_data: A parsed snapcraft.yaml.
    :param supported_arches: An ordered list of all architecture tags that
        we can create builds for.
    :return: a list of `SnapBuildInstance`s.
    """
    architectures_list = snapcraft_data.get(
        "architectures"
    )  # type: Optional[List]

    if architectures_list:
        # First, determine what style we're parsing.  Is it a list of
        # strings or a list of dicts?
        if all(isinstance(a, str) for a in architectures_list):
            # If a list of strings (old style), then that's only a single
            # item.
            architectures = [SnapArchitecture(build_on=architectures_list)]
        elif all(isinstance(arch, dict) for arch in architectures_list):
            # If a list of dicts (new style), then that's multiple items.
            architectures = [
                SnapArchitecture.from_dict(a) for a in architectures_list
            ]
        else:
            # If a mix of both, bail.  We can't reasonably handle it.
            raise IncompatibleArchitecturesStyleError()
    else:
        # If no architectures are specified, build one for each supported
        # architecture.
        architectures = [
            SnapArchitecture(build_on=a) for a in supported_arches
        ]

    allow_duplicate_build_on = (
        snap_base
        and snap_base.features.get(SnapBaseFeature.ALLOW_DUPLICATE_BUILD_ON)
    ) or False
    if not allow_duplicate_build_on:
        # Ensure that multiple `build-on` items don't include the same
        # architecture; this is ambiguous and forbidden by snapcraft prior
        # to core22. Checking this here means that we don't get duplicate
        # supported_arch results below.

        # XXX andrey-fedoseev 2022-08-22: we should use the `SnapBase` model
        # to store the specific features of each base rather than hard-coding
        # the base names here
        build_ons = Counter()
        for arch in architectures:
            build_ons.update(arch.build_on)
        duplicates = {arch for arch, count in build_ons.items() if count > 1}
        if duplicates:
            raise DuplicateBuildOnError(duplicates)

    architectures_to_build = []
    for arch in architectures:
        try:
            architectures_to_build.append(
                SnapBuildInstance(arch, supported_arches)
            )
        except UnsupportedBuildOnError:
            # Snaps are allowed to declare that they build on architectures
            # that Launchpad doesn't currently support (perhaps they're
            # upcoming, or perhaps they used to be supported).  We just
            # ignore those.
            pass
    return architectures_to_build
