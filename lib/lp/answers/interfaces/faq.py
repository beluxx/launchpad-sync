# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for FAQ document."""

__metaclass__ = type

__all__ = [
    'IFAQ',
    'IFAQSet',
    ]

from lazr.restful.declarations import (
    export_as_webservice_entry,
    exported,
    )
from lazr.restful.fields import Reference
from zope.interface import Attribute
from zope.schema import (
    Datetime,
    Int,
    Text,
    TextLine,
    )

from lp import _
from lp.answers.interfaces.faqcollection import IFAQCollection
from lp.answers.interfaces.faqtarget import IFAQTarget
from lp.registry.interfaces.role import IHasOwner
from lp.services.fields import (
    PublicPersonChoice,
    Title,
    )


class IFAQ(IHasOwner):
    """A document containing the answer to a commonly asked question.

    The answer can be in the document itself or can be hosted on a separate
    web site and referred to by URL.
    """

    export_as_webservice_entry('faq', as_of='beta')

    id = exported(Int(
        title=_('FAQ Number'),
        description=_('The unique number identifying the FAQ in Launchpad.'),
        required=True, readonly=True))

    title = exported(Title(
        title=_('Title'),
        description=_('The title describing this FAQ, often a question.'),
        required=True))

    keywords = exported(TextLine(
        title=_('Keywords'),
        description=_('One or more terms that relate to this FAQ.'),
        required=False))

    content = exported(Text(
        title=_('Content'),
        description=_(
            'The answer for this FAQ in plain text. You may choose to '
            'include a URL to an external FAQ.'),
        required=True))

    date_created = exported(Datetime(
        title=_('Created'), required=True, readonly=True))

    last_updated_by = exported(PublicPersonChoice(
        title=_('Last Updated By'),
        description=_('The last person who modified the document.'),
        vocabulary='ValidPersonOrTeam', required=False, readonly=True))

    date_last_updated = exported(Datetime(
        title=_('Last Updated'), required=False, readonly=True))

    target = exported(Reference(
        title=_('Target'),
        description=_('Product or distribution containing this FAQ.'),
        schema=IFAQTarget,
        required=True, readonly=True))

    related_questions = Attribute(
        _('The set of questions linked to this FAQ.'))


class IFAQSet(IFAQCollection):
    """`IFAQCollection` of all the FAQs existing in Launchpad.

    This interface is provided by a global utility object which can
    be used to search or retrieve any FAQ registered in Launchpad.
    """
