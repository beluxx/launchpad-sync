# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Launchpad bug-related database table classes."""

__metaclass__ = type

__all__ = [
    'Bug',
    'BugAffectsPerson',
    'BugBecameQuestionEvent',
    'BugSet',
    'BugTag',
    'FileBugData',
    'get_bug_tags',
    'get_bug_tags_open_count',
    ]


from cStringIO import StringIO
from datetime import (
    datetime,
    timedelta,
    )
from email.Utils import make_msgid
import operator
import re

from lazr.lifecycle.event import (
    ObjectCreatedEvent,
    ObjectDeletedEvent,
    ObjectModifiedEvent,
    )
from lazr.lifecycle.snapshot import Snapshot
from pytz import timezone
from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLMultipleJoin,
    SQLObjectNotFound,
    SQLRelatedJoin,
    StringCol,
    )
from storm.expr import (
    And,
    Count,
    Func,
    LeftJoin,
    Max,
    Not,
    Or,
    Select,
    SQL,
    SQLRaw,
    Union,
    )
from storm.info import ClassAlias
from storm.store import (
    EmptyResultSet,
    Store,
    )
from zope.component import getUtility
from zope.contenttype import guess_content_type
from zope.event import notify
from zope.interface import (
    implements,
    providedBy,
    )
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (
    cursor,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.database.librarian import LibraryFileAlias
from canonical.launchpad.database.message import (
    Message,
    MessageChunk,
    MessageSet,
    )
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces.launchpad import (
    ILaunchpadCelebrities,
    IPersonRoles,
    )
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.interfaces.message import (
    IMessage,
    IndexedMessage,
    )
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.answers.interfaces.questiontarget import IQuestionTarget
from lp.app.enums import ServiceUsage
from lp.app.errors import (
    NotFoundError,
    UserCannotUnsubscribePerson,
    )
from lp.bugs.adapters.bugchange import (
    BranchLinkedToBug,
    BranchUnlinkedFromBug,
    BugConvertedToQuestion,
    BugWatchAdded,
    BugWatchRemoved,
    SeriesNominated,
    UnsubscribedFromBug,
    )
from lp.bugs.interfaces.bug import (
    IBug,
    IBugBecameQuestionEvent,
    IBugSet,
    IFileBugData,
    InvalidDuplicateValue,
    )
from lp.bugs.interfaces.bugactivity import IBugActivitySet
from lp.bugs.interfaces.bugattachment import (
    BugAttachmentType,
    IBugAttachmentSet,
    )
from lp.bugs.interfaces.bugmessage import IBugMessageSet
from lp.bugs.interfaces.bugnomination import (
    NominationError,
    NominationSeriesObsoleteError,
    )
from lp.bugs.interfaces.bugnotification import IBugNotificationSet
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    IBugTaskSet,
    UNRESOLVED_BUGTASK_STATUSES,
    )
from lp.bugs.interfaces.bugtracker import BugTrackerType
from lp.bugs.interfaces.bugwatch import IBugWatchSet
from lp.bugs.interfaces.cve import ICveSet
from lp.bugs.mail.bugnotificationrecipients import BugNotificationRecipients
from lp.bugs.model.bugattachment import BugAttachment
from lp.bugs.model.bugbranch import BugBranch
from lp.bugs.model.bugcve import BugCve
from lp.bugs.model.bugmessage import BugMessage
from lp.bugs.model.bugnomination import BugNomination
from lp.bugs.model.bugnotification import BugNotification
from lp.bugs.model.bugsubscription import BugSubscription
from lp.bugs.model.bugtarget import OfficialBugTag
from lp.bugs.model.bugtask import (
    BugTask,
    bugtask_sort_key,
    get_bug_privacy_filter,
    NullBugTask,
    )
from lp.bugs.model.bugwatch import BugWatch
from lp.hardwaredb.interfaces.hwdb import IHWSubmissionBugSet
from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import validate_public_person
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.model.person import (
    Person,
    ValidPersonCache,
    )
from lp.registry.model.pillar import pillar_sort_key
from lp.registry.model.teammembership import TeamParticipation
from lp.services.fields import DuplicateBug
from lp.services.propertycache import (
    cachedproperty,
    clear_property_cache,
    get_property_cache,
    )


_bug_tag_query_template = """
        SELECT %(columns)s FROM %(tables)s WHERE
            %(condition)s GROUP BY BugTag.tag ORDER BY BugTag.tag"""


def get_bug_tags(context_clause):
    """Return all the bug tags as a list of strings.

    context_clause is a SQL condition clause, limiting the tags to a
    specific context. The SQL clause can only use the BugTask table to
    choose the context.
    """
    from_tables = ['BugTag', 'BugTask']
    select_columns = ['BugTag.tag']
    conditions = ['BugTag.bug = BugTask.bug', '(%s)' % context_clause]

    cur = cursor()
    cur.execute(_bug_tag_query_template % dict(
            columns=', '.join(select_columns),
            tables=', '.join(from_tables),
            condition=' AND '.join(conditions)))
    return shortlist([row[0] for row in cur.fetchall()])


def get_bug_tags_open_count(context_condition, user):
    """Return all the used bug tags with their open bug count.

    :param context_condition: A Storm SQL expression, limiting the
        used tags to a specific context. Only the BugTask table may be
        used to choose the context.
    :param user: The user performing the search.

    :return: A list of tuples, (tag name, open bug count).
    """
    open_statuses_condition = BugTask.status.is_in(
        UNRESOLVED_BUGTASK_STATUSES)
    columns = [
        BugTag.tag,
        Count(),
        ]
    tables = [
        BugTag,
        LeftJoin(Bug, Bug.id == BugTag.bugID),
        LeftJoin(
            BugTask,
            And(BugTask.bugID == Bug.id, open_statuses_condition)),
        ]
    where_conditions = [
        open_statuses_condition,
        context_condition,
        ]
    privacy_filter = get_bug_privacy_filter(user)
    if privacy_filter:
        where_conditions.append(SQLRaw(privacy_filter))
    store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
    result = store.execute(Select(
        columns=columns, where=And(*where_conditions), tables=tables,
        group_by=BugTag.tag, order_by=BugTag.tag))
    return shortlist([(row[0], row[1]) for row in result.get_all()])


def snapshot_bug_params(bug_params):
    """Return a snapshot of a `CreateBugParams` object."""
    return Snapshot(
        bug_params, names=[
            "owner", "title", "comment", "description", "msg",
            "datecreated", "security_related", "private",
            "distribution", "sourcepackagename", "binarypackagename",
            "product", "status", "subscribers", "tags",
            "subscribe_owner", "filed_by"])


class BugTag(SQLBase):
    """A tag belonging to a bug."""

    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    tag = StringCol(notNull=True)


class BugBecameQuestionEvent:
    """See `IBugBecameQuestionEvent`."""
    implements(IBugBecameQuestionEvent)

    def __init__(self, bug, question, user):
        self.bug = bug
        self.question = question
        self.user = user


class Bug(SQLBase):
    """A bug."""

    implements(IBug)

    _defaultOrder = '-id'

    # db field names
    name = StringCol(unique=True, default=None)
    title = StringCol(notNull=True)
    description = StringCol(notNull=False,
                            default=None)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    duplicateof = ForeignKey(
        dbName='duplicateof', foreignKey='Bug', default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_last_updated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    private = BoolCol(notNull=True, default=False)
    date_made_private = UtcDateTimeCol(notNull=False, default=None)
    who_made_private = ForeignKey(
        dbName='who_made_private', foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    security_related = BoolCol(notNull=True, default=False)

    # useful Joins
    activity = SQLMultipleJoin('BugActivity', joinColumn='bug', orderBy='id')
    messages = SQLRelatedJoin('Message', joinColumn='bug',
                           otherColumn='message',
                           intermediateTable='BugMessage',
                           prejoins=['owner'],
                           orderBy=['datecreated', 'id'])
    bug_messages = SQLMultipleJoin(
        'BugMessage', joinColumn='bug', orderBy='id')
    watches = SQLMultipleJoin(
        'BugWatch', joinColumn='bug', orderBy=['bugtracker', 'remotebug'])
    cves = SQLRelatedJoin('Cve', intermediateTable='BugCve',
        orderBy='sequence', joinColumn='bug', otherColumn='cve')
    cve_links = SQLMultipleJoin('BugCve', joinColumn='bug', orderBy='id')
    duplicates = SQLMultipleJoin(
        'Bug', joinColumn='duplicateof', orderBy='id')
    specifications = SQLRelatedJoin('Specification', joinColumn='bug',
        otherColumn='specification', intermediateTable='SpecificationBug',
        orderBy='-datecreated')
    questions = SQLRelatedJoin('Question', joinColumn='bug',
        otherColumn='question', intermediateTable='QuestionBug',
        orderBy='-datecreated')
    linked_branches = SQLMultipleJoin(
        'BugBranch', joinColumn='bug', orderBy='id')
    date_last_message = UtcDateTimeCol(default=None)
    number_of_duplicates = IntCol(notNull=True, default=0)
    message_count = IntCol(notNull=True, default=0)
    users_affected_count = IntCol(notNull=True, default=0)
    users_unaffected_count = IntCol(notNull=True, default=0)
    heat = IntCol(notNull=True, default=0)
    heat_last_updated = UtcDateTimeCol(default=None)
    latest_patch_uploaded = UtcDateTimeCol(default=None)

    @cachedproperty
    def _subscriber_cache(self):
        """Caches known subscribers."""
        return set()

    @cachedproperty
    def _subscriber_dups_cache(self):
        """Caches known subscribers to dupes."""
        return set()

    @cachedproperty
    def _unsubscribed_cache(self):
        """Cache known non-subscribers."""
        return set()

    @property
    def latest_patch(self):
        """See `IBug`."""
        # We want to retrieve the most recently added bug attachment
        # that is of type BugAttachmentType.PATCH. In order to find
        # this attachment, we should in theory sort by
        # BugAttachment.message.datecreated. Since we don't have
        # an index for Message.datecreated, such a query would be
        # quite slow. We search instead for the BugAttachment with
        # the largest ID for a given bug. This is "nearly" equivalent
        # to searching the record with the maximum value of
        # message.datecreated: The only exception is the rare case when
        # two BugAttachment records are simultaneuosly added to the same
        # bug, where bug_attachment_1.id < bug_attachment_2.id, while
        # the Message record for bug_attachment_2 is created before
        # the Message record for bug_attachment_1. The difference of
        # the datecreated values of the Message records is in this case
        # probably smaller than one second and the selection of the
        # "most recent" patch anyway somewhat arbitrary.
        return Store.of(self).find(
            BugAttachment, BugAttachment.id == Select(
                Max(BugAttachment.id),
                And(BugAttachment.bug == self.id,
                    BugAttachment.type == BugAttachmentType.PATCH))).one()

    @property
    def comment_count(self):
        """See `IBug`."""
        return self.message_count - 1

    @property
    def users_affected(self):
        """See `IBug`."""
        return Store.of(self).find(
            Person, BugAffectsPerson.person == Person.id,
            BugAffectsPerson.affected,
            BugAffectsPerson.bug == self)

    @property
    def users_unaffected(self):
        """See `IBug`."""
        return Store.of(self).find(
            Person, BugAffectsPerson.person == Person.id,
            Not(BugAffectsPerson.affected),
            BugAffectsPerson.bug == self)

    @property
    def user_ids_affected_with_dupes(self):
        """Return all IDs of Persons affected by this bug and its dupes.
        The return value is a Storm expression.  Running a query with
        this expression returns a result that may contain the same ID
        multiple times, for example if that person is affected via
        more than one duplicate."""
        return Union(
            Select(Person.id,
                   And(BugAffectsPerson.person == Person.id,
                       BugAffectsPerson.affected,
                       BugAffectsPerson.bug == self)),
            Select(Person.id,
                   And(BugAffectsPerson.person == Person.id,
                       BugAffectsPerson.bug == Bug.id,
                       BugAffectsPerson.affected,
                       Bug.duplicateof == self.id)))

    @property
    def users_affected_with_dupes(self):
        """See `IBug`."""
        return Store.of(self).find(
            Person,
            Person.id.is_in(self.user_ids_affected_with_dupes))

    @property
    def users_affected_count_with_dupes(self):
        """See `IBug`."""
        return self.users_affected_with_dupes.count()

    @property
    def indexed_messages(self):
        """See `IMessageTarget`."""
        return self._indexed_messages(include_content=True)

    def _indexed_messages(self, include_content=False, include_parents=True):
        """Get the bugs messages, indexed.

        :param include_content: If True retrieve the content for the messages
            too.
        :param include_parents: If True retrieve the object for parent
            messages too. If False the parent attribute will be *forced* to
            None to reduce database lookups.
        """
        # Make all messages be 'in' the main bugtask.
        inside = self.default_bugtask
        store = Store.of(self)
        message_by_id = {}
        if include_parents:
            to_messages = lambda rows: [row[0] for row in rows]
        else:
            to_messages = lambda rows: rows

        def eager_load_owners(messages):
            # Because we may have multiple owners, we spend less time
            # in storm with very large bugs by not joining and instead
            # querying a second time. If this starts to show high db
            # time, we can left outer join instead.
            owner_ids = set(message.ownerID for message in messages)
            owner_ids.discard(None)
            if not owner_ids:
                return
            list(store.find(Person, Person.id.is_in(owner_ids)))

        def eager_load_content(messages):
            # To avoid the complexity of having multiple rows per
            # message, or joining in the database (though perhaps in
            # future we should do that), we do a single separate query
            # for the message content.
            message_ids = set(message.id for message in messages)
            chunks = store.find(
                MessageChunk, MessageChunk.messageID.is_in(message_ids))
            chunks.order_by(MessageChunk.id)
            chunk_map = {}
            for chunk in chunks:
                message_chunks = chunk_map.setdefault(chunk.messageID, [])
                message_chunks.append(chunk)
            for message in messages:
                if message.id not in chunk_map:
                    continue
                cache = get_property_cache(message)
                cache.text_contents = Message.chunks_text(
                    chunk_map[message.id])

        def eager_load(rows, slice_info):
            messages = to_messages(rows)
            eager_load_owners(messages)
            if include_content:
                eager_load_content(messages)

        def index_message(row, index):
            # convert row to an IndexedMessage
            if include_parents:
                message, parent = row
                if parent is not None:
                    # If there is an IndexedMessage available as parent, use
                    # that to reduce on-demand parent lookups.
                    parent = message_by_id.get(parent.id, parent)
            else:
                message = row
                parent = None # parent attribute is not going to be accessed.
            result = IndexedMessage(message, inside, index, parent)
            # This message may be the parent for another: stash it to permit
            # use.
            message_by_id[message.id] = result
            return result
        # There is possibly some nicer way to do this in storm, but
        # this is a lot easier to figure out.
        if include_parents:
            ParentMessage = ClassAlias(Message, name="parent_message")
            tables = SQL("""
Message left outer join
message as parent_message on (
    message.parent=parent_message.id and
    parent_message.id in (
        select bugmessage.message from bugmessage where bugmessage.bug=%s)),
BugMessage""" % sqlvalues(self.id))
            results = store.using(tables).find(
                (Message, ParentMessage),
                BugMessage.bugID == self.id,
                BugMessage.messageID == Message.id,
                )
        else:
            results = store.find(Message,
                BugMessage.bugID == self.id,
                BugMessage.messageID == Message.id,
                )
        results.order_by(Message.datecreated, Message.id)
        return DecoratedResultSet(results, index_message,
            pre_iter_hook=eager_load, slice_info=True)

    @property
    def displayname(self):
        """See `IBug`."""
        dn = 'Bug #%d' % self.id
        if self.name:
            dn += ' ('+self.name+')'
        return dn

    @cachedproperty
    def bugtasks(self):
        """See `IBug`."""
        result = BugTask.select('BugTask.bug = %s' % sqlvalues(self.id))
        result = result.prejoin(
            ["assignee", "product", "sourcepackagename",
             "owner", "bugwatch"])
        # Do not use the default orderBy as the prejoins cause ambiguities
        # across the tables.
        result = result.orderBy("id")
        result = sorted(result, key=bugtask_sort_key)
        return result

    @property
    def default_bugtask(self):
        """See `IBug`."""
        return Store.of(self).find(
            BugTask, bug=self).order_by(BugTask.id).first()

    @property
    def is_complete(self):
        """See `IBug`."""
        for task in self.bugtasks:
            if not task.is_complete:
                return False
        return True

    @property
    def affected_pillars(self):
        """See `IBug`."""
        result = set()
        for task in self.bugtasks:
            result.add(task.pillar)
        return sorted(result, key=pillar_sort_key)

    @property
    def permits_expiration(self):
        """See `IBug`.

        This property checks the general state of the bug to determine if
        expiration is permitted *if* a bugtask were to qualify for expiration.
        This property does not check the bugtask preconditions to identify
        a specific bugtask that can expire.

        :See: `IBug.can_expire` or `BugTaskSet.findExpirableBugTasks` to
            check or get a list of bugs that can expire.
        """
        # Bugs cannot be expired if any bugtask is valid.
        expirable_status_list = [
            BugTaskStatus.INCOMPLETE, BugTaskStatus.INVALID,
            BugTaskStatus.WONTFIX]
        has_an_expirable_bugtask = False
        for bugtask in self.bugtasks:
            if bugtask.status not in expirable_status_list:
                # We found an unexpirable bugtask; the bug cannot expire.
                return False
            if (bugtask.status == BugTaskStatus.INCOMPLETE
                and bugtask.pillar.enable_bug_expiration):
                # This bugtasks meets the basic conditions to expire.
                has_an_expirable_bugtask = True

        return has_an_expirable_bugtask

    @property
    def can_expire(self):
        """See `IBug`.

        Only Incomplete bug reports that affect a single pillar with
        enabled_bug_expiration set to True can be expired. To qualify for
        expiration, the bug and its bugtasks meet the follow conditions:

        1. The bug is inactive; the last update of the bug is older than
            Launchpad expiration age.
        2. The bug is not a duplicate.
        3. The bug has at least one message (a request for more information).
        4. The bug does not have any other valid bugtasks.
        5. The bugtask belongs to a project with enable_bug_expiration set
           to True.
        6. The bugtask has the status Incomplete.
        7. The bugtask is not assigned to anyone.
        8. The bugtask does not have a milestone.
        """
        # IBugTaskSet.findExpirableBugTasks() is the authoritative determiner
        # if a bug can expire, but it is expensive. We do a general check
        # to verify the bug permits expiration before using IBugTaskSet to
        # determine if a bugtask can cause expiration.
        if not self.permits_expiration:
            return False

        days_old = config.malone.days_before_expiration
        # Do the search as the Janitor, to ensure that this bug can be
        # found, even if it's private. We don't have access to the user
        # calling this property. If the user has access to view this
        # property, he has permission to see the bug, so we're not
        # exposing something we shouldn't. The Janitor has access to
        # view all bugs.
        bugtasks = getUtility(IBugTaskSet).findExpirableBugTasks(
            days_old, getUtility(ILaunchpadCelebrities).janitor, bug=self)
        return bugtasks.count() > 0

    def isExpirable(self, days_old=None):
        """See `IBug`."""

        # If days_old is None read it from the Launchpad configuration
        # and use that value
        if days_old is None:
            days_old = config.malone.days_before_expiration

        # IBugTaskSet.findExpirableBugTasks() is the authoritative determiner
        # if a bug can expire, but it is expensive. We do a general check
        # to verify the bug permits expiration before using IBugTaskSet to
        # determine if a bugtask can cause expiration.
        if not self.permits_expiration:
            return False

        # Do the search as the Janitor, to ensure that this bug can be
        # found, even if it's private. We don't have access to the user
        # calling this property. If the user has access to view this
        # property, he has permission to see the bug, so we're not
        # exposing something we shouldn't. The Janitor has access to
        # view all bugs.
        bugtasks = getUtility(IBugTaskSet).findExpirableBugTasks(
            days_old, getUtility(ILaunchpadCelebrities).janitor, bug=self)
        return bugtasks.count() > 0

    @property
    def initial_message(self):
        """See `IBug`."""
        store = Store.of(self)
        messages = store.find(
            Message,
            BugMessage.bug == self,
            BugMessage.message == Message.id).order_by('id')
        return messages.first()

    @cachedproperty
    def official_tags(self):
        """See `IBug`."""
        # Da circle of imports forces the locals.
        from lp.registry.model.distribution import Distribution
        from lp.registry.model.product import Product
        table = OfficialBugTag
        table = LeftJoin(
            table,
            Distribution,
            OfficialBugTag.distribution_id==Distribution.id)
        table = LeftJoin(
            table,
            Product,
            OfficialBugTag.product_id==Product.id)
        # When this method is typically called it already has the necessary
        # info in memory, so rather than rejoin with Product etc, we do this
        # bit in Python. If reviewing performance here feel free to change.
        clauses = []
        for task in self.bugtasks:
            clauses.append(
                # Storm cannot compile proxied objects.
                removeSecurityProxy(task.target._getOfficialTagClause()))
        clause = Or(*clauses)
        return list(Store.of(self).using(table).find(OfficialBugTag.tag,
            clause).order_by(OfficialBugTag.tag).config(distinct=True))

    def followup_subject(self):
        """See `IBug`."""
        return 'Re: '+ self.title

    @property
    def has_patches(self):
        """See `IBug`."""
        return self.latest_patch_uploaded is not None

    def subscribe(self, person, subscribed_by, suppress_notify=True,
                  level=None):
        """See `IBug`."""
        if level is None:
            level = BugNotificationLevel.COMMENTS

        # first look for an existing subscription
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                return sub

        sub = BugSubscription(
            bug=self, person=person, subscribed_by=subscribed_by,
            bug_notification_level=level)

        # Ensure that the subscription has been flushed.
        Store.of(sub).flush()

        # In some cases, a subscription should be created without
        # email notifications.  suppress_notify determines if
        # notifications are sent.
        if suppress_notify is False:
            notify(ObjectCreatedEvent(sub, user=subscribed_by))

        self.updateHeat()
        return sub

    def unsubscribe(self, person, unsubscribed_by):
        """See `IBug`."""
        # Drop cached subscription info.
        clear_property_cache(self)
        if person is None:
            person = unsubscribed_by

        for sub in self.subscriptions:
            if sub.person.id == person.id:
                if not sub.canBeUnsubscribedByUser(unsubscribed_by):
                    raise UserCannotUnsubscribePerson(
                        '%s does not have permission to unsubscribe %s.' % (
                            unsubscribed_by.displayname,
                            person.displayname))

                self.addChange(UnsubscribedFromBug(
                    when=UTC_NOW, person=unsubscribed_by,
                    unsubscribed_user=person))
                store = Store.of(sub)
                store.remove(sub)
                # Make sure that the subscription removal has been
                # flushed so that code running with implicit flushes
                # disabled see the change.
                store.flush()
                self.updateHeat()
                del get_property_cache(self)._known_viewers
                return

    def unsubscribeFromDupes(self, person, unsubscribed_by):
        """See `IBug`."""
        if person is None:
            person = unsubscribed_by

        bugs_unsubscribed = []
        for dupe in self.duplicates:
            if dupe.isSubscribed(person):
                dupe.unsubscribe(person, unsubscribed_by)
                bugs_unsubscribed.append(dupe)

        return bugs_unsubscribed

    def isSubscribed(self, person):
        """See `IBug`."""
        return self.personIsDirectSubscriber(person)

    def isSubscribedToDupes(self, person):
        """See `IBug`."""
        return self.personIsSubscribedToDuplicate(person)

    @property
    def subscriptions(self):
        """The set of `BugSubscriptions` for this bug."""
        # XXX: kiko 2006-09-23: Why is subscriptions ordered by ID?
        results = Store.of(self).find(
            (Person, BugSubscription),
            BugSubscription.person_id == Person.id,
            BugSubscription.bug_id == self.id).order_by(BugSubscription.id)
        return DecoratedResultSet(results, operator.itemgetter(1))

    def getDirectSubscriptions(self):
        """See `IBug`."""
        # Cache valid persons so that <person>.is_valid_person can
        # return from the cache. This operation was previously done at
        # the same time as retrieving the bug subscriptions (as a left
        # join). However, this ran slowly (far from optimal query
        # plan), so we're doing it as two queries now.
        valid_persons = Store.of(self).find(
            (Person, ValidPersonCache),
            Person.id == ValidPersonCache.id,
            ValidPersonCache.id == BugSubscription.person_id,
            BugSubscription.bug == self)
        # Suck in all the records so that they're actually cached.
        list(valid_persons)
        # Do the main query.
        return Store.of(self).find(
            BugSubscription,
            BugSubscription.person_id == Person.id,
            BugSubscription.bug == self).order_by(
            Func('person_sort_key', Person.displayname, Person.name))

    def getDirectSubscribers(self, recipients=None, level=None):
        """See `IBug`.

        The recipients argument is private and not exposed in the
        interface. If a BugNotificationRecipients instance is supplied,
        the relevant subscribers and rationales will be registered on
        it.
        """
        if level is None:
            level = BugNotificationLevel.NOTHING

        subscribers = list(
            Person.select("""
                Person.id = BugSubscription.person
                AND BugSubscription.bug = %s
                AND BugSubscription.bug_notification_level >= %s""" %
                sqlvalues(self.id, level),
                orderBy="displayname", clauseTables=["BugSubscription"]))
        if recipients is not None:
            for subscriber in subscribers:
                recipients.addDirectSubscriber(subscriber)
        return subscribers

    def getIndirectSubscribers(self, recipients=None, level=None):
        """See `IBug`.

        See the comment in getDirectSubscribers for a description of the
        recipients argument.
        """
        # "Also notified" and duplicate subscribers are mutually
        # exclusive, so return both lists.
        indirect_subscribers = (
            self.getAlsoNotifiedSubscribers(recipients, level) +
            self.getSubscribersFromDuplicates(recipients, level))

        # Remove security proxy for the sort key, but return
        # the regular proxied object.
        return sorted(
            indirect_subscribers,
            key=lambda x: removeSecurityProxy(x).displayname)

    def getSubscriptionsFromDuplicates(self, recipients=None):
        """See `IBug`."""
        if self.private:
            return []
        # For each subscription to each duplicate of this bug, find the
        # earliest subscription for each subscriber. Eager load the
        # subscribers.
        return DecoratedResultSet(
            IStore(BugSubscription).find(
                # XXX: GavinPanella 2010-09-17 bug=374777: This SQL(...) is a
                # hack; it does not seem to be possible to express DISTINCT ON
                # with Storm.
                (SQL("DISTINCT ON (BugSubscription.person) 0 AS ignore"),
                 Person, BugSubscription),
                Bug.duplicateof == self,
                BugSubscription.bug_id == Bug.id,
                BugSubscription.person_id == Person.id).order_by(
                BugSubscription.person_id),
            operator.itemgetter(2))

    def getSubscribersFromDuplicates(self, recipients=None, level=None):
        """See `IBug`.

        See the comment in getDirectSubscribers for a description of the
        recipients argument.
        """
        if self.private:
            return []

        if level is None:
            notification_level = BugNotificationLevel.NOTHING
        else:
            notification_level = level

        dupe_details = dict(
            Store.of(self).find(
                (Person, Bug),
                BugSubscription.person == Person.id,
                BugSubscription.bug_id == Bug.id,
                BugSubscription.bug_notification_level >= notification_level,
                Bug.duplicateof == self.id))

        dupe_subscribers = set(dupe_details)

        # Direct and "also notified" subscribers take precedence over
        # subscribers from dupes. Note that we don't supply recipients
        # here because we are doing this to /remove/ subscribers.
        dupe_subscribers -= set(self.getDirectSubscribers())
        dupe_subscribers -= set(self.getAlsoNotifiedSubscribers())

        if recipients is not None:
            for subscriber in dupe_subscribers:
                recipients.addDupeSubscriber(
                    subscriber, dupe_details[subscriber])

        return sorted(
            dupe_subscribers, key=operator.attrgetter("displayname"))

    def getSubscribersForPerson(self, person):
        """See `IBug."""

        assert person is not None

        def cache_unsubscribed(rows):
            if not rows:
                self._unsubscribed_cache.add(person)

        def cache_subscriber(row):
            _, subscriber, subscription = row
            if subscription.bug_id == self.id:
                self._subscriber_cache.add(subscriber)
            else:
                self._subscriber_dups_cache.add(subscriber)
            return subscriber
        return DecoratedResultSet(Store.of(self).find(
            # XXX: RobertCollins 2010-09-22 bug=374777: This SQL(...) is a
            # hack; it does not seem to be possible to express DISTINCT ON
            # with Storm.
            (SQL("DISTINCT ON (Person.name, BugSubscription.person) "
                 "0 AS ignore"),
             # Return people and subscriptions
             Person, BugSubscription),
            # For this bug or its duplicates
            Or(
                Bug.id == self.id,
                Bug.duplicateof == self.id),
            # Get subscriptions for these bugs
            BugSubscription.bug_id == Bug.id,
            # Filter by subscriptions to any team person is in.
            # Note that teamparticipation includes self-participation entries
            # (person X is in the team X)
            TeamParticipation.person == person.id,
            # XXX: Storm fails to compile this, so manually done.
            # bug=https://bugs.launchpad.net/storm/+bug/627137
            # RBC 20100831
            SQL("""TeamParticipation.team = BugSubscription.person"""),
            # Join in the Person rows we want
            # XXX: Storm fails to compile this, so manually done.
            # bug=https://bugs.launchpad.net/storm/+bug/627137
            # RBC 20100831
            SQL("""Person.id = TeamParticipation.team"""),
            ).order_by(Person.name),
            cache_subscriber, pre_iter_hook=cache_unsubscribed)

    def getSubscriptionForPerson(self, person):
        """See `IBug`."""
        store = Store.of(self)
        return store.find(
            BugSubscription,
            BugSubscription.person == person,
            BugSubscription.bug == self).one()

    def getAlsoNotifiedSubscribers(self, recipients=None, level=None):
        """See `IBug`.

        See the comment in getDirectSubscribers for a description of the
        recipients argument.
        """
        if self.private:
            return []

        also_notified_subscribers = set()

        for bugtask in self.bugtasks:
            if bugtask.assignee:
                also_notified_subscribers.add(bugtask.assignee)
                if recipients is not None:
                    recipients.addAssignee(bugtask.assignee)

            # If the target's bug supervisor isn't set,
            # we add the owner as a subscriber.
            pillar = bugtask.pillar
            if pillar.bug_supervisor is None and pillar.official_malone:
                    also_notified_subscribers.add(pillar.owner)
                    if recipients is not None:
                        recipients.addRegistrant(pillar.owner, pillar)

        # Structural subscribers.
        also_notified_subscribers.update(
            getUtility(IBugTaskSet).getStructuralSubscribers(
                self.bugtasks, recipients=recipients, level=level))

        # Direct subscriptions always take precedence over indirect
        # subscriptions.
        direct_subscribers = set(self.getDirectSubscribers())

        # Remove security proxy for the sort key, but return
        # the regular proxied object.
        return sorted(
            (also_notified_subscribers - direct_subscribers),
            key=lambda x: removeSecurityProxy(x).displayname)

    def getBugNotificationRecipients(self, duplicateof=None, old_bug=None,
                                     level=None,
                                     include_master_dupe_subscribers=False):
        """See `IBug`."""
        recipients = BugNotificationRecipients(duplicateof=duplicateof)
        self.getDirectSubscribers(recipients)
        if self.private:
            assert self.getIndirectSubscribers() == [], (
                "Indirect subscribers found on private bug. "
                "A private bug should never have implicit subscribers!")
        else:
            self.getIndirectSubscribers(recipients, level=level)
            if include_master_dupe_subscribers and self.duplicateof:
                # This bug is a public duplicate of another bug, so include
                # the dupe target's subscribers in the recipient list. Note
                # that we only do this for duplicate bugs that are public;
                # changes in private bugs are not broadcast to their dupe
                # targets.
                dupe_recipients = (
                    self.duplicateof.getBugNotificationRecipients(
                        duplicateof=self.duplicateof, level=level))
                recipients.update(dupe_recipients)
        # XXX Tom Berger 2008-03-18:
        # We want to look up the recipients for `old_bug` too,
        # but for this to work, this code has to move out of the
        # class and into a free function, since `old_bug` is a
        # `Snapshot`, and doesn't have any of the methods of the
        # original `Bug`.
        return recipients

    def addChangeNotification(self, text, person, recipients=None, when=None):
        """See `IBug`."""
        if recipients is None:
            recipients = self.getBugNotificationRecipients(
                level=BugNotificationLevel.METADATA)
        if when is None:
            when = UTC_NOW
        message = MessageSet().fromText(
            self.followup_subject(), text, owner=person, datecreated=when)
        getUtility(IBugNotificationSet).addNotification(
             bug=self, is_comment=False,
             message=message, recipients=recipients)

    def addCommentNotification(self, message, recipients=None):
        """See `IBug`."""
        if recipients is None:
            recipients = self.getBugNotificationRecipients(
                level=BugNotificationLevel.COMMENTS)
        getUtility(IBugNotificationSet).addNotification(
             bug=self, is_comment=True,
             message=message, recipients=recipients)

    def addChange(self, change, recipients=None):
        """See `IBug`."""
        when = change.when
        if when is None:
            when = UTC_NOW

        # Only try to add something to the activity log if we have some
        # data.
        activity_data = change.getBugActivity()
        if activity_data is not None:
            getUtility(IBugActivitySet).new(
                self, when, change.person,
                activity_data['whatchanged'],
                activity_data.get('oldvalue'),
                activity_data.get('newvalue'),
                activity_data.get('message'))

        notification_data = change.getBugNotification()
        if notification_data is not None:
            assert notification_data.get('text') is not None, (
                "notification_data must include a `text` value.")

            self.addChangeNotification(
                notification_data['text'], change.person, recipients,
                when)

        self.updateHeat()

    def expireNotifications(self):
        """See `IBug`."""
        for notification in BugNotification.selectBy(
                bug=self, date_emailed=None):
            notification.date_emailed = UTC_NOW
            notification.syncUpdate()

    def newMessage(self, owner=None, subject=None,
                   content=None, parent=None, bugwatch=None,
                   remote_comment_id=None):
        """Create a new Message and link it to this bug."""
        if subject is None:
            subject = self.followup_subject()
        msg = Message(
            parent=parent, owner=owner, subject=subject,
            rfc822msgid=make_msgid('malone'))
        MessageChunk(message=msg, content=content, sequence=1)

        bugmsg = self.linkMessage(
            msg, bugwatch, remote_comment_id=remote_comment_id)
        if not bugmsg:
            return

        notify(ObjectCreatedEvent(bugmsg, user=owner))

        return bugmsg.message

    def linkMessage(self, message, bugwatch=None, user=None,
                    remote_comment_id=None):
        """See `IBug`."""
        if message not in self.messages:
            if user is None:
                user = message.owner

            result = BugMessage(bug=self, message=message,
                bugwatch=bugwatch, remote_comment_id=remote_comment_id)
            getUtility(IBugWatchSet).fromText(
                message.text_contents, self, user)
            self.findCvesInText(message.text_contents, user)
            # XXX 2008-05-27 jamesh:
            # Ensure that BugMessages get flushed in same order as
            # they are created.
            Store.of(result).flush()
            return result

    def addTask(self, owner, target):
        """See `IBug`."""
        product = None
        product_series = None
        distribution = None
        distro_series = None
        source_package_name = None

        # Turn `target` into something more useful.
        if IProduct.providedBy(target):
            product = target
        if IProductSeries.providedBy(target):
            product_series = target
        if IDistribution.providedBy(target):
            distribution = target
        if IDistroSeries.providedBy(target):
            distro_series = target
        if IDistributionSourcePackage.providedBy(target):
            distribution = target.distribution
            source_package_name = target.sourcepackagename
        if ISourcePackage.providedBy(target):
            if target.distroseries is not None:
                distro_series = target.distroseries
                source_package_name = target.sourcepackagename
            elif target.distribution is not None:
                distribution = target.distribution
                source_package_name = target.sourcepackagename
            else:
                source_package_name = target.sourcepackagename

        new_task = getUtility(IBugTaskSet).createTask(
            self, owner=owner, product=product,
            productseries=product_series, distribution=distribution,
            distroseries=distro_series,
            sourcepackagename=source_package_name)

        # When a new task is added the bug's heat becomes relevant to the
        # target's max_bug_heat.
        target.recalculateBugHeatCache()

        return new_task

    def addWatch(self, bugtracker, remotebug, owner):
        """See `IBug`."""
        # We shouldn't add duplicate bug watches.
        bug_watch = self.getBugWatch(bugtracker, remotebug)
        if bug_watch is None:
            bug_watch = BugWatch(
                bug=self, bugtracker=bugtracker,
                remotebug=remotebug, owner=owner)
            Store.of(bug_watch).flush()
        self.addChange(BugWatchAdded(UTC_NOW, owner, bug_watch))
        notify(ObjectCreatedEvent(bug_watch, user=owner))
        return bug_watch

    def removeWatch(self, bug_watch, user):
        """See `IBug`."""
        self.addChange(BugWatchRemoved(UTC_NOW, user, bug_watch))
        bug_watch.destroySelf()

    def addAttachment(self, owner, data, comment, filename, is_patch=False,
                      content_type=None, description=None):
        """See `IBug`."""
        if isinstance(data, str):
            filecontent = data
        else:
            filecontent = data.read()

        if is_patch:
            content_type = 'text/plain'
        else:
            if content_type is None:
                content_type, encoding = guess_content_type(
                    name=filename, body=filecontent)

        filealias = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(filecontent),
            file=StringIO(filecontent), contentType=content_type,
            restricted=self.private)

        return self.linkAttachment(
            owner, filealias, comment, is_patch, description)

    def linkAttachment(self, owner, file_alias, comment, is_patch=False,
                       description=None, send_notifications=True):
        """See `IBug`.

        This method should only be called by addAttachment() and
        FileBugViewBase.submit_bug_action, otherwise
        we may get inconsistent settings of bug.private and
        file_alias.restricted.

        :param send_notifications: Control sending of notifications for this
            attachment. This is disabled when adding attachments from 'extra
            data' in the filebug form, because that triggered hundreds of DB
            inserts and thus timeouts. Defaults to sending notifications.
        """
        if is_patch:
            attach_type = BugAttachmentType.PATCH
        else:
            attach_type = BugAttachmentType.UNSPECIFIED

        if description:
            title = description
        else:
            title = file_alias.filename

        if IMessage.providedBy(comment):
            message = comment
        else:
            message = self.newMessage(
                owner=owner, subject=description, content=comment)

        return getUtility(IBugAttachmentSet).create(
            bug=self, filealias=file_alias, attach_type=attach_type,
            title=title, message=message,
            send_notifications=send_notifications)

    def hasBranch(self, branch):
        """See `IBug`."""
        branch = BugBranch.selectOneBy(branch=branch, bug=self)

        return branch is not None

    def linkBranch(self, branch, registrant):
        """See `IBug`."""
        for bug_branch in shortlist(self.linked_branches):
            if bug_branch.branch == branch:
                return bug_branch

        bug_branch = BugBranch(
            branch=branch, bug=self, registrant=registrant)
        branch.date_last_modified = UTC_NOW

        self.addChange(BranchLinkedToBug(UTC_NOW, registrant, branch, self))
        notify(ObjectCreatedEvent(bug_branch))

        return bug_branch

    def unlinkBranch(self, branch, user):
        """See `IBug`."""
        bug_branch = BugBranch.selectOneBy(bug=self, branch=branch)
        if bug_branch is not None:
            self.addChange(BranchUnlinkedFromBug(UTC_NOW, user, branch, self))
            notify(ObjectDeletedEvent(bug_branch, user=user))
            bug_branch.destroySelf()

    @cachedproperty
    def has_cves(self):
        """See `IBug`."""
        return bool(self.cves)

    def linkCVE(self, cve, user):
        """See `IBug`."""
        if cve not in self.cves:
            bugcve = BugCve(bug=self, cve=cve)
            notify(ObjectCreatedEvent(bugcve, user=user))
            return bugcve

    # XXX intellectronica 2008-11-06 Bug #294858:
    # See lp.bugs.interfaces.bug
    def linkCVEAndReturnNothing(self, cve, user):
        """See `IBug`."""
        self.linkCVE(cve, user)
        return None

    def unlinkCVE(self, cve, user):
        """See `IBug`."""
        for cve_link in self.cve_links:
            if cve_link.cve.id == cve.id:
                notify(ObjectDeletedEvent(cve_link, user=user))
                BugCve.delete(cve_link.id)
                break

    def findCvesInText(self, text, user):
        """See `IBug`."""
        cves = getUtility(ICveSet).inText(text)
        for cve in cves:
            self.linkCVE(cve, user)

    # Several other classes need to generate lists of bugs, and
    # one thing they often have to filter for is completeness. We maintain
    # this single canonical query string here so that it does not have to be
    # cargo culted into Product, Distribution, ProductSeries etc
    completeness_clause = """
        BugTask.bug = Bug.id AND """ + BugTask.completeness_clause

    def canBeAQuestion(self):
        """See `IBug`."""
        return (self._getQuestionTargetableBugTask() is not None
            and self.getQuestionCreatedFromBug() is None)

    def _getQuestionTargetableBugTask(self):
        """Return the only bugtask that can be a QuestionTarget, or None.

        Bugs that are also in external bug trackers cannot be converted
        to questions. This is also true for bugs that are being developed.
        None is returned when either of these conditions are true.

        The bugtask is selected by these rules:
        1. It's status is not Invalid.
        2. It is not a conjoined slave.
        Only one bugtask must meet both conditions to be return. When
        zero or many bugtasks match, None is returned.
        """
        # XXX sinzui 2007-10-19:
        # We may want to removed the bugtask.conjoined_master check
        # below. It is used to simplify the task of converting
        # conjoined bugtasks to question--since slaves cannot be
        # directly updated anyway.
        non_invalid_bugtasks = [
            bugtask for bugtask in self.bugtasks
            if (bugtask.status != BugTaskStatus.INVALID
                and bugtask.conjoined_master is None)]
        if len(non_invalid_bugtasks) != 1:
            return None
        [valid_bugtask] = non_invalid_bugtasks
        if valid_bugtask.pillar.bug_tracking_usage == ServiceUsage.LAUNCHPAD:
            return valid_bugtask
        else:
            return None

    def convertToQuestion(self, person, comment=None):
        """See `IBug`."""
        question = self.getQuestionCreatedFromBug()
        assert question is None, (
            'This bug was already converted to question #%s.' % question.id)
        bugtask = self._getQuestionTargetableBugTask()
        assert bugtask is not None, (
            'A question cannot be created from this bug without a '
            'valid bugtask.')

        bugtask_before_modification = Snapshot(
            bugtask, providing=providedBy(bugtask))
        bugtask.transitionToStatus(BugTaskStatus.INVALID, person)
        edited_fields = ['status']
        if comment is not None:
            self.newMessage(
                owner=person, subject=self.followup_subject(),
                content=comment)
        notify(
            ObjectModifiedEvent(
                object=bugtask,
                object_before_modification=bugtask_before_modification,
                edited_fields=edited_fields,
                user=person))

        question_target = IQuestionTarget(bugtask.target)
        question = question_target.createQuestionFromBug(self)
        self.addChange(BugConvertedToQuestion(UTC_NOW, person, question))
        get_property_cache(self)._question_from_bug = question

        notify(BugBecameQuestionEvent(self, question, person))
        return question

    @cachedproperty
    def _question_from_bug(self):
        for question in self.questions:
            if (question.ownerID == self.ownerID
                and question.datecreated == self.datecreated):
                return question
        return None

    def getQuestionCreatedFromBug(self):
        """See `IBug`."""
        return self._question_from_bug

    def getMessageChunks(self):
        """See `IBug`."""
        query = """
            Message.id = MessageChunk.message AND
            BugMessage.message = Message.id AND
            BugMessage.bug = %s
            """ % sqlvalues(self)

        chunks = MessageChunk.select(query,
            clauseTables=["BugMessage", "Message"],
            # XXX: kiko 2006-09-16 bug=60745:
            # There is an issue that presents itself
            # here if we prejoin message.owner: because Message is
            # already in the clauseTables, the SQL generated joins
            # against message twice and that causes the results to
            # break.
            prejoinClauseTables=["Message"],
            # Note the ordering by Message.id here; while datecreated in
            # production is never the same, it can be in the test suite.
            orderBy=["Message.datecreated", "Message.id",
                     "MessageChunk.sequence"])
        chunks = list(chunks)

        # Since we can't prejoin, cache all people at once so we don't
        # have to do it while rendering, which is a big deal for bugs
        # with a million comments.
        owner_ids = set()
        for chunk in chunks:
            if chunk.message.ownerID:
                owner_ids.add(str(chunk.message.ownerID))
        list(Person.select("ID in (%s)" % ",".join(owner_ids)))

        return chunks

    def getNullBugTask(self, product=None, productseries=None,
                    sourcepackagename=None, distribution=None,
                    distroseries=None):
        """See `IBug`."""
        return NullBugTask(bug=self, product=product,
                           productseries=productseries,
                           sourcepackagename=sourcepackagename,
                           distribution=distribution,
                           distroseries=distroseries)

    def addNomination(self, owner, target):
        """See `IBug`."""
        if not self.canBeNominatedFor(target):
            raise NominationError(
                "This bug cannot be nominated for %s." %
                    target.bugtargetdisplayname)

        distroseries = None
        productseries = None
        if IDistroSeries.providedBy(target):
            distroseries = target
            if target.status == SeriesStatus.OBSOLETE:
                raise NominationSeriesObsoleteError(
                    "%s is an obsolete series." % target.bugtargetdisplayname)
        else:
            assert IProductSeries.providedBy(target)
            productseries = target

        if not (check_permission("launchpad.BugSupervisor", target) or
                check_permission("launchpad.Driver", target)):
            raise NominationError(
                "Only bug supervisors or owners can nominate bugs.")

        nomination = BugNomination(
            owner=owner, bug=self, distroseries=distroseries,
            productseries=productseries)
        self.addChange(SeriesNominated(UTC_NOW, owner, target))
        return nomination

    def canBeNominatedFor(self, target):
        """See `IBug`."""
        try:
            self.getNominationFor(target)
        except NotFoundError:
            # No nomination exists. Let's see if the bug is already
            # directly targeted to this nomination target.
            if IDistroSeries.providedBy(target):
                series_getter = operator.attrgetter("distroseries")
                pillar_getter = operator.attrgetter("distribution")
            elif IProductSeries.providedBy(target):
                series_getter = operator.attrgetter("productseries")
                pillar_getter = operator.attrgetter("product")
            else:
                return False

            for task in self.bugtasks:
                if series_getter(task) == target:
                    # The bug is already targeted at this
                    # nomination target.
                    return False

            # No nomination or tasks are targeted at this
            # nomination target. But we also don't want to nominate for a
            # series of a product or distro for which we don't have a
            # plain pillar task.
            for task in self.bugtasks:
                if pillar_getter(task) == pillar_getter(target):
                    return True

            # No tasks match the candidate's pillar. We must refuse.
            return False
        else:
            # The bug is already nominated for this nomination target.
            return False

    def getNominationFor(self, target):
        """See `IBug`."""
        if IDistroSeries.providedBy(target):
            filter_args = dict(distroseriesID=target.id)
        elif IProductSeries.providedBy(target):
            filter_args = dict(productseriesID=target.id)
        else:
            return None

        nomination = BugNomination.selectOneBy(bugID=self.id, **filter_args)

        if nomination is None:
            raise NotFoundError(
                "Bug #%d is not nominated for %s." % (
                self.id, target.displayname))

        return nomination

    def getNominations(self, target=None, nominations=None):
        """See `IBug`."""
        # Define the function used as a sort key.
        def by_bugtargetdisplayname(nomination):
            """Return the friendly sort key verson of displayname."""
            return nomination.target.bugtargetdisplayname.lower()

        if nominations is None:
            nominations = BugNomination.selectBy(bugID=self.id)
        if IProduct.providedBy(target):
            filtered_nominations = []
            for nomination in shortlist(nominations):
                if (nomination.productseries and
                    nomination.productseries.product == target):
                    filtered_nominations.append(nomination)
            nominations = filtered_nominations
        elif IDistribution.providedBy(target):
            filtered_nominations = []
            for nomination in shortlist(nominations):
                if (nomination.distroseries and
                    nomination.distroseries.distribution == target):
                    filtered_nominations.append(nomination)
            nominations = filtered_nominations

        return sorted(nominations, key=by_bugtargetdisplayname)

    def getBugWatch(self, bugtracker, remote_bug):
        """See `IBug`."""
        # If the bug tracker is of BugTrackerType.EMAILADDRESS we can
        # never tell if a bug is already being watched upstream, since
        # the remotebug field for such bug watches contains either '' or
        # an RFC822 message ID. In these cases, then, we always return
        # None for the sake of sanity.
        if bugtracker.bugtrackertype == BugTrackerType.EMAILADDRESS:
            return None

        # XXX: BjornT 2006-10-11:
        # This matching is a bit fragile, since bugwatch.remotebug
        # is a user editable text string. We should improve the
        # matching so that for example '#42' matches '42' and so on.
        return BugWatch.selectFirstBy(
            bug=self, bugtracker=bugtracker, remotebug=str(remote_bug),
            orderBy='id')

    def setStatus(self, target, status, user):
        """See `IBug`."""
        bugtask = self.getBugTask(target)
        if bugtask is None:
            if IProductSeries.providedBy(target):
                bugtask = self.getBugTask(target.product)
            elif ISourcePackage.providedBy(target):
                current_distro_series = target.distribution.currentseries
                current_package = current_distro_series.getSourcePackage(
                    target.sourcepackagename.name)
                if self.getBugTask(current_package) is not None:
                    # The bug is targeted to the current series, don't
                    # fall back on the general distribution task.
                    return None
                distro_package = target.distribution.getSourcePackage(
                    target.sourcepackagename.name)
                bugtask = self.getBugTask(distro_package)
            else:
                return None

        if bugtask is None:
            return None

        if bugtask.conjoined_master is not None:
            bugtask = bugtask.conjoined_master

        if bugtask.status == status:
            return None

        bugtask_before_modification = Snapshot(
            bugtask, providing=providedBy(bugtask))
        bugtask.transitionToStatus(status, user)
        notify(ObjectModifiedEvent(
            bugtask, bugtask_before_modification, ['status'], user=user))

        return bugtask

    def setPrivate(self, private, who):
        """See `IBug`.

        We also record who made the change and when the change took
        place.
        """
        if self.private != private:
            if private:
                # Change indirect subscribers into direct subscribers
                # *before* setting private because
                # getIndirectSubscribers() behaves differently when
                # the bug is private.
                for person in self.getIndirectSubscribers():
                    self.subscribe(person, who)

            self.private = private

            if private:
                self.who_made_private = who
                self.date_made_private = UTC_NOW
            else:
                self.who_made_private = None
                self.date_made_private = None

            # XXX: This should be a bulk update. RBC 20100827
            # bug=https://bugs.launchpad.net/storm/+bug/625071
            for attachment in self.attachments_unpopulated:
                attachment.libraryfile.restricted = private

            # Correct the heat for the bug immediately, so that we don't have
            # to wait for the next calculation job for the adjusted heat.
            self.updateHeat()
            return True # Changed.
        else:
            return False # Not changed.

    def setSecurityRelated(self, security_related):
        """Setter for the `security_related` property."""
        if self.security_related != security_related:
            self.security_related = security_related

            # Correct the heat for the bug immediately, so that we don't have
            # to wait for the next calculation job for the adjusted heat.
            self.updateHeat()

            return True # Changed
        else:
            return False # Unchanged

    def getBugTask(self, target):
        """See `IBug`."""
        for bugtask in self.bugtasks:
            if bugtask.target == target:
                return bugtask

        return None

    def _getTags(self):
        """Get the tags as a sorted list of strings."""
        return self._cached_tags

    @cachedproperty
    def _cached_tags(self):
        return list(Store.of(self).find(
            BugTag.tag,
            BugTag.bugID==self.id).order_by(BugTag.tag))

    def _setTags(self, tags):
        """Set the tags from a list of strings."""
        # In order to preserve the ordering of the tags, delete all tags
        # and insert the new ones.
        new_tags = set([tag.lower() for tag in tags])
        old_tags = set(self.tags)
        del get_property_cache(self)._cached_tags
        added_tags = new_tags.difference(old_tags)
        removed_tags = old_tags.difference(new_tags)
        for removed_tag in removed_tags:
            tag = BugTag.selectOneBy(bug=self, tag=removed_tag)
            tag.destroySelf()
        for added_tag in added_tags:
            BugTag(bug=self, tag=added_tag)
        Store.of(self).flush()

    tags = property(_getTags, _setTags)

    @staticmethod
    def getBugTasksByPackageName(bugtasks):
        """See IBugTask."""
        bugtasks_by_package = {}
        for bugtask in bugtasks:
            bugtasks_by_package.setdefault(bugtask.sourcepackagename, [])
            bugtasks_by_package[bugtask.sourcepackagename].append(bugtask)
        return bugtasks_by_package

    def _getAffectedUser(self, user):
        """Return the `IBugAffectsPerson` for a user, or None

        :param user: An `IPerson` that may be affected by the bug.
        :return: An `IBugAffectsPerson` or None.
        """
        if user is None:
            return None
        else:
            return Store.of(self).get(
                BugAffectsPerson, (self.id, user.id))

    def isUserAffected(self, user):
        """See `IBug`."""
        bap = self._getAffectedUser(user)
        if bap is not None:
            return bap.affected
        else:
            return None

    def _flushAndInvalidate(self):
        """Flush all changes to the store and re-read `self` from the DB."""
        store = Store.of(self)
        store.flush()
        store.invalidate(self)

    def markUserAffected(self, user, affected=True):
        """See `IBug`."""
        bap = self._getAffectedUser(user)
        if bap is None:
            BugAffectsPerson(bug=self, person=user, affected=affected)
            self._flushAndInvalidate()
        else:
            if bap.affected != affected:
                bap.affected = affected
                self._flushAndInvalidate()

        # Loop over dupes.
        for dupe in self.duplicates:
            if dupe._getAffectedUser(user) is not None:
                dupe.markUserAffected(user, affected)

        self.updateHeat()

    def markAsDuplicate(self, duplicate_of):
        """See `IBug`."""
        field = DuplicateBug()
        field.context = self
        current_duplicateof = self.duplicateof
        try:
            if duplicate_of is not None:
                field._validate(duplicate_of)
            if self.duplicates:
                for duplicate in self.duplicates:
                    # Fire a notify event in model code since moving
                    # duplicates of a duplicate does not normally fire an
                    # event.
                    dupe_before = Snapshot(
                        duplicate, providing=providedBy(duplicate))
                    duplicate.markAsDuplicate(duplicate_of)
                    notify(ObjectModifiedEvent(
                            duplicate, dupe_before, 'duplicateof'))
            self.duplicateof = duplicate_of
        except LaunchpadValidationError, validation_error:
            raise InvalidDuplicateValue(validation_error)

        if duplicate_of is not None:
            # Update the heat of the master bug and set this bug's heat
            # to 0 (since it's a duplicate, it shouldn't have any heat
            # at all).
            self.setHeat(0)
            duplicate_of.updateHeat()
        else:
            # Otherwise, recalculate this bug's heat, since it will be 0
            # from having been a duplicate. We also update the bug that
            # was previously duplicated.
            self.updateHeat()
            current_duplicateof.updateHeat()

    def setCommentVisibility(self, user, comment_number, visible):
        """See `IBug`."""
        bug_message_set = getUtility(IBugMessageSet)
        bug_message = bug_message_set.getByBugAndMessage(
            self, self.messages[comment_number])
        bug_message.visible = visible

    @cachedproperty
    def _known_viewers(self):
        """A dict of of known persons able to view this bug.

        Seed it by including the list of all owners of bugtasks for the bug.
        """
        bugtask_owners = [bt.pillar.owner.id for bt in self.bugtasks]
        return set(bugtask_owners)

    def userCanView(self, user):
        """See `IBug`.

        Note that Editing is also controlled by this check,
        because we permit editing of any bug one can see.
        """
        if user.id in self._known_viewers:
            return True
        if not self.private:
            # This is a public bug.
            return True
        elif IPersonRoles(user).in_admin:
            # Admins can view all bugs.
            return True
        else:
            # This is a private bug. Only explicit subscribers may view it.
            for subscription in self.subscriptions:
                if user.inTeam(subscription.person):
                    self._known_viewers.add(user.id)
                    return True
        return False

    def linkHWSubmission(self, submission):
        """See `IBug`."""
        getUtility(IHWSubmissionBugSet).create(submission, self)

    def unlinkHWSubmission(self, submission):
        """See `IBug`."""
        getUtility(IHWSubmissionBugSet).remove(submission, self)

    def getHWSubmissions(self, user=None):
        """See `IBug`."""
        return getUtility(IHWSubmissionBugSet).submissionsForBug(self, user)

    def personIsDirectSubscriber(self, person):
        """See `IBug`."""
        if person in self._subscriber_cache:
            return True
        if person in self._unsubscribed_cache:
            return False
        if person is None:
            return False
        store = Store.of(self)
        subscriptions = store.find(
            BugSubscription,
            BugSubscription.bug == self,
            BugSubscription.person == person)
        return not subscriptions.is_empty()

    def personIsAlsoNotifiedSubscriber(self, person):
        """See `IBug`."""
        # We have to use getAlsoNotifiedSubscribers() here and iterate
        # over what it returns because "also notified subscribers" is
        # actually a composite of bug contacts, structural subscribers
        # and assignees. As such, it's not possible to get them all with
        # one query.
        also_notified_subscribers = self.getAlsoNotifiedSubscribers()

        return person in also_notified_subscribers

    def personIsSubscribedToDuplicate(self, person):
        """See `IBug`."""
        if person in self._subscriber_dups_cache:
            return True
        if person in self._unsubscribed_cache:
            return False
        if person is None:
            return False
        store = Store.of(self)
        subscriptions_from_dupes = store.find(
            BugSubscription,
            Bug.duplicateof == self,
            BugSubscription.bug_id == Bug.id,
            BugSubscription.person == person)

        return not subscriptions_from_dupes.is_empty()

    def setHeat(self, heat, timestamp=None):
        """See `IBug`."""
        if timestamp is None:
            timestamp = UTC_NOW

        if heat < 0:
            heat = 0

        self.heat = heat
        self.heat_last_updated = timestamp
        for task in self.bugtasks:
            task.target.recalculateBugHeatCache()

    def updateHeat(self):
        """See `IBug`."""
        if self.duplicateof is not None:
            # If this bug is a duplicate we don't try to calculate its
            # heat.
            return

        # We need to flush the store first to ensure that changes are
        # reflected in the new bug heat total.
        store = Store.of(self)
        store.flush()

        self.heat = SQL("calculate_bug_heat(%s)" % sqlvalues(self))
        self.heat_last_updated = UTC_NOW
        for task in self.bugtasks:
            task.target.recalculateBugHeatCache()
        store.flush()

    def _attachments_query(self):
        """Helper for the attachments* properties."""
        # bug attachments with no LibraryFileContent have been deleted - the
        # garbo_daily run will remove the LibraryFileAlias asynchronously.
        # See bug 542274 for more details.
        store = Store.of(self)
        return store.find(
            (BugAttachment, LibraryFileAlias),
            BugAttachment.bug == self,
            BugAttachment.libraryfile == LibraryFileAlias.id,
            LibraryFileAlias.content != None).order_by(BugAttachment.id)

    @property
    def attachments(self):
        """See `IBug`.

        This property does eager loading of the index_messages so that
        the API which wants the message_link for the attachment can
        answer that without O(N^2) overhead. As such it is moderately
        expensive to call (it currently retrieves all messages before
        any attachments, and does this when attachments is evaluated,
        not when the resultset is processed).
        """
        message_to_indexed = {}
        for message in self._indexed_messages(include_parents=False):
            message_to_indexed[message.id] = message

        def set_indexed_message(row):
            attachment = row[0]
            # row[1] - the LibraryFileAlias is now in the storm cache and
            # will be found without a query when dereferenced.
            indexed_message = message_to_indexed.get(attachment._messageID)
            if indexed_message is not None:
                get_property_cache(attachment).message = indexed_message
            return attachment
        rawresults = self._attachments_query()
        return DecoratedResultSet(rawresults, set_indexed_message)

    @property
    def attachments_unpopulated(self):
        """See `IBug`.

        This version does not pre-lookup messages and LibraryFileAliases.

        The regular 'attachments' property does prepopulation because it is
        exposed in the API.
        """
        # Grab the attachment only; the LibraryFileAlias will be eager loaded.
        return DecoratedResultSet(
            self._attachments_query(),
            operator.itemgetter(0))


class BugSet:
    """See BugSet."""
    implements(IBugSet)

    valid_bug_name_re = re.compile(r'''^[a-z][a-z0-9\\+\\.\\-]+$''')

    def get(self, bugid):
        """See `IBugSet`."""
        try:
            return Bug.get(bugid)
        except SQLObjectNotFound:
            raise NotFoundError(
                "Unable to locate bug with ID %s." % str(bugid))

    def getByNameOrID(self, bugid):
        """See `IBugSet`."""
        if self.valid_bug_name_re.match(bugid):
            bug = Bug.selectOneBy(name=bugid)
            if bug is None:
                raise NotFoundError(
                    "Unable to locate bug with ID %s." % bugid)
        else:
            try:
                bug = self.get(bugid)
            except ValueError:
                raise NotFoundError(
                    "Unable to locate bug with nickname %s." % bugid)
        return bug

    def searchAsUser(self, user, duplicateof=None, orderBy=None, limit=None):
        """See `IBugSet`."""
        where_clauses = []
        if duplicateof:
            where_clauses.append("Bug.duplicateof = %d" % duplicateof.id)

        admins = getUtility(ILaunchpadCelebrities).admin
        if user:
            if not user.inTeam(admins):
                # Enforce privacy-awareness for logged-in, non-admin users,
                # so that they can only see the private bugs that they're
                # allowed to see.
                where_clauses.append("""
                    (Bug.private = FALSE OR
                     Bug.id in (
                         SELECT Bug.id
                         FROM Bug, BugSubscription, TeamParticipation
                         WHERE Bug.id = BugSubscription.bug AND
                             TeamParticipation.person = %(personid)s AND
                             BugSubscription.person = TeamParticipation.team))
                             """ % sqlvalues(personid=user.id))
        else:
            # Anonymous user; filter to include only public bugs in
            # the search results.
            where_clauses.append("Bug.private = FALSE")

        other_params = {}
        if orderBy:
            other_params['orderBy'] = orderBy
        if limit:
            other_params['limit'] = limit

        return Bug.select(
            ' AND '.join(where_clauses), **other_params)

    def queryByRemoteBug(self, bugtracker, remotebug):
        """See `IBugSet`."""
        bug = Bug.selectFirst("""
                bugwatch.bugtracker = %s AND
                bugwatch.remotebug = %s AND
                bugwatch.bug = bug.id
                """ % sqlvalues(bugtracker.id, str(remotebug)),
                distinct=True,
                clauseTables=['BugWatch'],
                orderBy=['datecreated'])
        return bug

    def createBug(self, bug_params):
        """See `IBugSet`."""
        # Make a copy of the parameter object, because we might modify some
        # of its attribute values below.
        params = snapshot_bug_params(bug_params)

        if params.product and params.product.private_bugs:
            # If the private_bugs flag is set on a product, then
            # force the new bug report to be private.
            params.private = True

        bug, event = self.createBugWithoutTarget(params)

        if params.security_related:
            assert params.private, (
                "A security related bug should always be private by default.")
            if params.product:
                context = params.product
            else:
                context = params.distribution

            if context.security_contact:
                bug.subscribe(context.security_contact, params.owner)
            else:
                bug.subscribe(context.owner, params.owner)
        # XXX: ElliotMurphy 2007-06-14: If we ever allow filing private
        # non-security bugs, this test might be simplified to checking
        # params.private.
        elif params.product and params.product.private_bugs:
            # Subscribe the bug supervisor to all bugs,
            # because all their bugs are private by default
            # otherwise only subscribe the bug reporter by default.
            if params.product.bug_supervisor:
                bug.subscribe(params.product.bug_supervisor, params.owner)
            else:
                bug.subscribe(params.product.owner, params.owner)
        else:
            # nothing to do
            pass

        # Create the task on a product if one was passed.
        if params.product:
            getUtility(IBugTaskSet).createTask(
                bug=bug, product=params.product, owner=params.owner,
                status=params.status)

        # Create the task on a source package name if one was passed.
        if params.distribution:
            getUtility(IBugTaskSet).createTask(
                bug=bug, distribution=params.distribution,
                sourcepackagename=params.sourcepackagename,
                owner=params.owner, status=params.status)

        # Tell everyone.
        notify(event)

        # Calculate the bug's initial heat.
        bug.updateHeat()

        return bug

    def createBugWithoutTarget(self, bug_params):
        """See `IBugSet`."""
        # Make a copy of the parameter object, because we might modify some
        # of its attribute values below.
        params = snapshot_bug_params(bug_params)

        if not (params.comment or params.description or params.msg):
            raise AssertionError(
                'Either comment, msg, or description should be specified.')

        if not params.datecreated:
            params.datecreated = UTC_NOW

        # make sure we did not get TOO MUCH information
        assert params.comment is None or params.msg is None, (
            "Expected either a comment or a msg, but got both.")

        # Store binary package name in the description, because
        # storing it as a separate field was a maintenance burden to
        # developers.
        if params.binarypackagename:
            params.comment = "Binary package hint: %s\n\n%s" % (
                params.binarypackagename.name, params.comment)

        # Create the bug comment if one was given.
        if params.comment:
            rfc822msgid = make_msgid('malonedeb')
            params.msg = Message(
                subject=params.title, rfc822msgid=rfc822msgid,
                owner=params.owner, datecreated=params.datecreated)
            MessageChunk(
                message=params.msg, sequence=1, content=params.comment,
                blob=None)

        # Extract the details needed to create the bug and optional msg.
        if not params.description:
            params.description = params.msg.text_contents

        extra_params = {}
        if params.private:
            # We add some auditing information. After bug creation
            # time these attributes are updated by Bug.setPrivate().
            extra_params.update(
                date_made_private=params.datecreated,
                who_made_private=params.owner)

        bug = Bug(
            title=params.title, description=params.description,
            private=params.private, owner=params.owner,
            datecreated=params.datecreated,
            security_related=params.security_related,
            **extra_params)

        if params.subscribe_owner:
            bug.subscribe(params.owner, params.owner)
        if params.tags:
            bug.tags = params.tags

        # Subscribe other users.
        for subscriber in params.subscribers:
            bug.subscribe(subscriber, params.owner)

        # Link the bug to the message.
        BugMessage(bug=bug, message=params.msg)

        # Mark the bug reporter as affected by that bug.
        bug.markUserAffected(bug.owner)

        # Populate the creation event.
        if params.filed_by is None:
            event = ObjectCreatedEvent(bug, user=params.owner)
        else:
            event = ObjectCreatedEvent(bug, user=params.filed_by)

        return (bug, event)

    def getDistinctBugsForBugTasks(self, bug_tasks, user, limit=10):
        """See `IBugSet`."""
        # XXX: Graham Binns 2009-05-28 bug=75764
        #      We slice bug_tasks here to prevent this method from
        #      causing timeouts, since if we try to iterate over it
        #      Transaction.iterSelect() will try to listify the results.
        #      This can be fixed by selecting from Bugs directly, but
        #      that's non-trivial.
        # ---: Robert Collins 20100818: if bug_tasks implements IResultSset
        #      then it should be very possible to improve on it, though
        #      DecoratedResultSets would need careful handling (e.g. type
        #      driven callbacks on columns)
        # We select more than :limit: since if a bug affects more than
        # one source package, it will be returned more than one time. 4
        # is an arbitrary number that should be large enough.
        bugs = []
        for bug_task in bug_tasks[:4*limit]:
            bug = bug_task.bug
            duplicateof = bug.duplicateof
            if duplicateof is not None:
                bug = duplicateof

            if not bug.userCanView(user):
                continue

            if bug not in bugs:
                bugs.append(bug)
                if len(bugs) >= limit:
                    break

        return bugs

    def getByNumbers(self, bug_numbers):
        """See `IBugSet`."""
        if bug_numbers is None or len(bug_numbers) < 1:
            return EmptyResultSet()
        store = IStore(Bug)
        result_set = store.find(Bug, Bug.id.is_in(bug_numbers))
        return result_set.order_by('id')

    def dangerousGetAllBugs(self):
        """See `IBugSet`."""
        store = IStore(Bug)
        result_set = store.find(Bug)
        return result_set.order_by('id')

    def getBugsWithOutdatedHeat(self, max_heat_age):
        """See `IBugSet`."""
        store = IStore(Bug)
        last_updated_cutoff = (
            datetime.now(timezone('UTC')) -
            timedelta(days=max_heat_age))
        last_updated_clause = Or(
            Bug.heat_last_updated < last_updated_cutoff,
            Bug.heat_last_updated == None)

        return store.find(
            Bug, Bug.duplicateof==None, last_updated_clause).order_by('id')


class BugAffectsPerson(SQLBase):
    """A bug is marked as affecting a user."""
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    affected = BoolCol(notNull=True, default=True)
    __storm_primary__ = "bugID", "personID"


class FileBugData:
    """Extra data to be added to the bug."""
    implements(IFileBugData)

    def __init__(self, initial_summary=None, initial_tags=None,
                 private=None, subscribers=None, extra_description=None,
                 comments=None, attachments=None,
                 hwdb_submission_keys=None):
        if initial_tags is None:
            initial_tags = []
        if subscribers is None:
            subscribers = []
        if comments is None:
            comments = []
        if attachments is None:
            attachments = []
        if hwdb_submission_keys is None:
            hwdb_submission_keys = []

        self.initial_summary = initial_summary
        self.private = private
        self.extra_description = extra_description
        self.initial_tags = initial_tags
        self.subscribers = subscribers
        self.comments = comments
        self.attachments = attachments
        self.hwdb_submission_keys = hwdb_submission_keys

    def asDict(self):
        """Return the FileBugData instance as a dict."""
        return self.__dict__.copy()
