# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Processor interfaces."""

__all__ = [
    'IProcessor',
    'IProcessorSet',
    'ProcessorNotFound',
    ]

from lazr.restful.declarations import (
    collection_default_content,
    export_read_operation,
    exported,
    exported_as_webservice_collection,
    exported_as_webservice_entry,
    operation_for_version,
    operation_parameters,
    operation_returns_entry,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Text,
    TextLine,
    )

from lp import _
from lp.app.errors import NameLookupFailed


class ProcessorNotFound(NameLookupFailed):
    """Exception raised when a processor name isn't found."""
    _message_prefix = 'No such processor'


# XXX: BradCrittenden 2011-06-20 bug=760849: The following use of 'beta'
# is a work-around to allow the WADL to be generated.  It is a bald-faced
# lie, though.  The class is being exported in 'devel' but in order to get
# the WADL generation work it must be back-dated to the earliest version.
# Note that individual attributes and methods can and must truthfully set
# 'devel' as their version.
@exported_as_webservice_entry(publish_web_link=False, as_of='beta')
class IProcessor(Interface):
    """The SQLObject Processor Interface"""

    id = Attribute("The Processor ID")
    name = exported(
        TextLine(title=_("Name"),
                 description=_("The Processor Name")),
        as_of='devel', readonly=True)
    title = exported(
        TextLine(title=_("Title"),
                 description=_("The Processor Title")),
        as_of='devel', readonly=True)
    description = exported(
        Text(title=_("Description"),
             description=_("The Processor Description")),
        as_of='devel', readonly=True)
    restricted = exported(
        Bool(title=_("Whether this processor is restricted.")),
        as_of='devel', readonly=True)
    build_by_default = exported(
        Bool(title=_(
            "Whether this processor is enabled on archives by default.")),
        as_of='devel', readonly=True)
    supports_virtualized = exported(
        Bool(
            title=_("Supports virtualized builds"),
            description=_(
                "Whether the processor has virtualized builders. If not, "
                "archives that require virtualized builds won't build on "
                "this processor.")),
        as_of='devel', readonly=True)
    supports_nonvirtualized = exported(
        Bool(
            title=_("Supports non-virtualized builds"),
            description=_(
                "Whether the processor has non-virtualized builders. If not, "
                "all builds for this processor will build on virtualized "
                "builders, even for non-virtualized archives.")),
        as_of='devel', readonly=True)


@exported_as_webservice_collection(IProcessor)
class IProcessorSet(Interface):
    """Operations related to Processor instances."""

    @operation_parameters(
        name=TextLine(required=True))
    @operation_returns_entry(IProcessor)
    @export_read_operation()
    @operation_for_version('devel')
    def getByName(name):
        """Return the IProcessor instance with the matching name.

        :param name: The name to look for.
        :raise ProcessorNotFound: if there is no processor with that name.
        :return: A `IProcessor` instance if found
        """

    @collection_default_content()
    def getAll():
        """Return all the `IProcessor` known to Launchpad."""

    def new(name, title, description, restricted=False,
            build_by_default=False, supports_virtualized=False,
            supports_nonvirtualized=True):
        """Create a new processor.

        :param name: Name of the processor.
        :param title: Title for the processor.
        :param description: Extended description of the processor.
        :param restricted: Whether the processor is restricted.
        :return: a `IProcessor`.
        """
