# Copyright 2016-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snappy series interfaces."""

__all__ = [
    'ISnappyDistroSeries',
    'ISnappyDistroSeriesSet',
    'ISnappySeries',
    'ISnappySeriesSet',
    'NoSuchSnappySeries',
    ]

from lazr.restful.declarations import (
    call_with,
    collection_default_content,
    export_factory_operation,
    export_read_operation,
    exported,
    exported_as_webservice_collection,
    exported_as_webservice_entry,
    operation_for_version,
    operation_parameters,
    operation_returns_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import Reference
from zope.component import getUtility
from zope.interface import Interface
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Int,
    List,
    TextLine,
    )

from lp import _
from lp.app.errors import NameLookupFailed
from lp.app.validators.name import name_validator
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.series import SeriesStatus
from lp.services.fields import (
    ContentNameField,
    PublicPersonChoice,
    Title,
    )


class NoSuchSnappySeries(NameLookupFailed):
    """The requested `SnappySeries` does not exist."""

    _message_prefix = "No such snappy series"


class SnappySeriesNameField(ContentNameField):
    """Ensure that `ISnappySeries` has unique names."""

    errormessage = _("%s is already in use by another series.")

    @property
    def _content_iface(self):
        """See `UniqueField`."""
        return ISnappySeries

    def _getByName(self, name):
        """See `ContentNameField`."""
        try:
            return getUtility(ISnappySeriesSet).getByName(name)
        except NoSuchSnappySeries:
            return None


class ISnappySeriesView(Interface):
    """`ISnappySeries` attributes that anyone can view."""

    id = Int(title=_("ID"), required=True, readonly=True)

    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))

    registrant = exported(PublicPersonChoice(
        title=_("Registrant"), required=True, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_("The person who registered this snappy series.")))


class ISnappySeriesEditableAttributes(Interface):
    """`ISnappySeries` attributes that can be edited.

    Anyone can view these attributes, but they need launchpad.Edit to change.
    """

    name = exported(SnappySeriesNameField(
        title=_("Name"), required=True, readonly=False,
        constraint=name_validator))

    display_name = exported(TextLine(
        title=_("Display name"), required=True, readonly=False))

    title = Title(title=_("Title"), required=True, readonly=True)

    status = exported(Choice(
        title=_("Status"), required=True, vocabulary=SeriesStatus))

    preferred_distro_series = exported(Reference(
        IDistroSeries, title=_("Preferred distro series"),
        required=False, readonly=False))

    usable_distro_series = exported(List(
        title=_("Usable distro series"),
        description=_(
            "The distro series that can be used for this snappy series."),
        value_type=Reference(schema=IDistroSeries),
        required=True, readonly=False))

    can_infer_distro_series = exported(Bool(
        title=_("Can infer distro series?"), required=True, readonly=False,
        description=_(
            "True if inferring a distro series from snapcraft.yaml is "
            "supported for this snappy series.")))


# XXX cjwatson 2016-04-13 bug=760849: "beta" is a lie to get WADL
# generation working.  Individual attributes must set their version to
# "devel".
@exported_as_webservice_entry(plural_name="snappy_serieses", as_of="beta")
class ISnappySeries(ISnappySeriesView, ISnappySeriesEditableAttributes):
    """A series for snap packages in the store."""


class ISnappyDistroSeries(Interface):
    """A snappy/distro series link."""

    snappy_series = Reference(
        ISnappySeries, title=_("Snappy series"), readonly=True)
    distro_series = Reference(
        IDistroSeries, title=_("Distro series"), required=False, readonly=True)
    preferred = Bool(
        title=_("Preferred"),
        required=True, readonly=False,
        description=_(
            "True if this identifies the default distro series for builds "
            "for this snappy series."))

    title = Title(title=_("Title"), required=True, readonly=True)


class ISnappySeriesSetEdit(Interface):
    """`ISnappySeriesSet` methods that require launchpad.Edit permission."""

    @call_with(registrant=REQUEST_USER)
    @export_factory_operation(
        ISnappySeries, ["name", "display_name", "status"])
    @operation_for_version("devel")
    def new(registrant, name, display_name, status, date_created=None):
        """Create an `ISnappySeries`."""


@exported_as_webservice_collection(ISnappySeries)
class ISnappySeriesSet(ISnappySeriesSetEdit):
    """Interface representing the set of snappy series."""

    def __iter__():
        """Iterate over `ISnappySeries`."""

    def __getitem__(name):
        """Return the `ISnappySeries` with this name."""

    @operation_parameters(
        name=TextLine(title=_("Snappy series name"), required=True))
    @operation_returns_entry(ISnappySeries)
    @export_read_operation()
    @operation_for_version("devel")
    def getByName(name):
        """Return the `ISnappySeries` with this name.

        :raises NoSuchSnappySeries: if no snappy series exists with this name.
        """

    @collection_default_content()
    def getAll():
        """Return all `ISnappySeries`."""


class ISnappyDistroSeriesSet(Interface):
    """Interface representing the set of snappy/distro series links."""

    def getByBothSeries(snappy_series, distro_series):
        """Return a `SnappyDistroSeries` for this pair of series, or None."""

    def getAll():
        """Return all `SnappyDistroSeries`."""
