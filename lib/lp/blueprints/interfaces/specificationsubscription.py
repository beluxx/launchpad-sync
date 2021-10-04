# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Specification subscription interfaces."""

__all__ = [
    'ISpecificationSubscription',
    ]

from lazr.restful.declarations import (
    call_with,
    export_read_operation,
    exported_as_webservice_entry,
    operation_for_version,
    REQUEST_USER,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Int,
    )

from lp import _
from lp.services.fields import PersonChoice


@exported_as_webservice_entry(publish_web_link=False, as_of='devel')
class ISpecificationSubscription(Interface):
    """A subscription for a person to a specification."""

    id = Int(
        title=_('ID'), required=True, readonly=True)
    person = PersonChoice(
            title=_('Subscriber'), required=True,
            vocabulary='ValidPersonOrTeam', readonly=True,
            description=_(
            'The person you would like to subscribe to this blueprint. '
            'They will be notified of the subscription by email.')
            )
    personID = Attribute('db person value')
    specification = Int(title=_('Specification'), required=True,
        readonly=True)
    specificationID = Attribute('db specification value')
    essential = Bool(title=_('Participation essential'), required=True,
        description=_('Check this if participation in the design of '
        'the feature is essential.'),
        default=False)

    @call_with(user=REQUEST_USER)
    @export_read_operation()
    @operation_for_version("devel")
    def canBeUnsubscribedByUser(user):
        """Can the user unsubscribe the subscriber from the specification?"""
