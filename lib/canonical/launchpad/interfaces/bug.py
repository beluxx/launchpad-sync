__metaclass__ = object

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.schema.interfaces import IText, ITextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.lp import dbschema
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.fields import Title, Summary


# CONTENT
class IBug(Interface):
    """The core bug entry."""

    id = Int(
            title=_('Bug ID'), required=True, readonly=True,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Nickname'), required=False,
            description=_("""A short and unique name for this bug. Very few
                bugs have a nickname, they are just bugs that are so
                significant that people will actually remember the
                name. Please don't set a nickname for the bug unless you
                are certain that this is the sort of bug that the entire
                community, upstream and all distro's, will phear."""),
            constraint=valid_name,
            )
    title = Title(
            title=_('Title'), required=True,
            description=_("""A one-line summary of the problem"""),
            )
    shortdesc = Summary(
            title=_('Summary'), required=False,
            description=_("""The bug summary is a single paragraph
            description that should capture the essence of the bug, where it
            has been observed, and what triggers it."""),
            )
    description = Text(
            title=_('Description'), required=False,
            description=_("""A detailed description of the problem,
            including the steps required to reproduce it""")
            )
    ownerID = Int(
            title=_('Owner'), required=True, readonly=True
            )
    owner = Attribute("The owner's IPerson")
    duplicateof = Int(
            title=_('Duplicate Of'), required=False,
            )
    communityscore = Int(
            title=_('Community Score'), required=True, readonly=True,
            default=0,
            )
    communitytimestamp = Datetime(
            title=_('Community Timestamp'), required=True, readonly=True,
            #default=datetime.utcnow,
            )
    hits = Int(
            title=_('Hits'), required=True, readonly=True,
            default=0,
            )
    hitstimestamp = Datetime(
            title=_('Hits Timestamp'), required=True, readonly=True,
            #default=datetime.utcnow,
            )
    activityscore = Int(
            title=_('Activity Score'), required=True, readonly=True,
            default=0,
            )
    activitytimestamp = Datetime(
            title=_('Activity Timestamp'),
            required=True, readonly=True,
            #default=datetime.utcnow,
            )
    private = Bool(
            title=_("Is this bug security related?"), required=False,
            description=_(
                "Check the box if this bug exposes a security vulnerability. If "
                "you're not sure, leave this unchecked."),
            default=False)

    activity = Attribute('SQLObject.Multijoin of IBugActivity')
    messages = Attribute('SQLObject.RelatedJoin of IMessages')
    bugtasks = Attribute('SQLObject.Multijoin of IBugTask')
    productinfestations = Attribute('List of product release infestations.')
    packageinfestations = Attribute('List of package release infestations.')
    watches = Attribute('SQLObject.Multijoin of IBugWatch')
    externalrefs = Attribute('SQLObject.Multijoin of IBugExternalRef')
    cverefs = Attribute('CVE references for this bug')
    subscriptions = Attribute('SQLObject.Multijoin of IBugSubscription')

    def followup_title():
        """Return a candidate title for a followup message."""


class IBugAddForm(IBug):
    """Information we need to create a bug"""
    id = Int(title=_("Bug #"), required=False)
    product = Choice(
            title=_("Product"), required=False,
            description=_("""The thing you found this bug in,
            which was installed by something other than apt-get, rpm,
            emerge or similar"""),
            vocabulary="Product")
    sourcepackagename = Choice(
            title=_("Source Package Name"), required=False,
            description=_("""The distribution package you found
            this bug in, which was installed via apt-get, rpm,
            emerge or similar."""),
            vocabulary="SourcePackageName")
    distribution = Choice(
            title=_("Linux Distribution"), required=False,
            description=_("""Debian, Redhat, Gentoo, etc."""),
            vocabulary="Distribution")
    binarypackage = Choice(
            title=_("Binary Package"), required=False,
            vocabulary="BinaryPackage")
    owner = Int(title=_("Owner"), required=True)
    comment = Text(title=_('Comment'), required=True,
            description=_("""A detailed description of the problem you are
            seeing."""))

# Interfaces for set
class IBugSet(IAddFormCustomization):
    """A set for bugs."""

    title = Attribute('Title')

    def __getitem__(key):
        """Get a Bug."""

    def __iter__():
        """Iterate through Bugs."""

    def get(bugid):
        """Get a specific bug by its ID."""
