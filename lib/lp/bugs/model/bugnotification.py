# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bug notifications."""

__all__ = [
    'BugNotification',
    'BugNotificationFilter',
    'BugNotificationRecipient',
    'BugNotificationSet',
    ]

from datetime import (
    datetime,
    timedelta,
    )

import pytz
from storm.expr import (
    In,
    Join,
    LeftJoin,
    )
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Unicode,
    )
from storm.store import Store
from zope.component import getUtility
from zope.interface import implementer

from lp.bugs.enums import BugNotificationStatus
from lp.bugs.interfaces.bugnotification import (
    IBugNotification,
    IBugNotificationFilter,
    IBugNotificationRecipient,
    IBugNotificationSet,
    )
from lp.bugs.model.bugactivity import BugActivity
from lp.bugs.model.bugsubscriptionfilter import (
    BugSubscriptionFilter,
    BugSubscriptionFilterMute,
    )
from lp.bugs.model.structuralsubscription import StructuralSubscription
from lp.registry.interfaces.person import IPersonSet
from lp.services.config import config
from lp.services.database import bulk
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase
from lp.services.messages.model.message import Message


@implementer(IBugNotification)
class BugNotification(StormBase):
    """A textual representation about a bug change."""

    __storm_table__ = 'BugNotification'

    id = Int(primary=True)

    message_id = Int(name='message', allow_none=False)
    message = Reference(message_id, 'Message.id')

    activity_id = Int('activity', allow_none=True)
    activity = Reference(activity_id, 'BugActivity.id')

    bug_id = Int(name='bug', allow_none=False)
    bug = Reference(bug_id, 'Bug.id')

    is_comment = Bool(allow_none=False)
    date_emailed = DateTime(tzinfo=pytz.UTC, allow_none=True)
    status = DBEnum(
        name='status',
        enum=BugNotificationStatus, default=BugNotificationStatus.PENDING,
        allow_none=False)

    def __init__(self, bug, is_comment, message, date_emailed=None,
                 activity=None, status=BugNotificationStatus.PENDING):
        self.bug = bug
        self.is_comment = is_comment
        self.message = message
        self.date_emailed = date_emailed
        self.activity = activity
        self.status = status

    @property
    def recipients(self):
        """See `IBugNotification`."""
        return IStore(BugNotificationRecipient).find(
            BugNotificationRecipient,
            BugNotificationRecipient.bug_notification == self).order_by(
                BugNotificationRecipient.id)

    @property
    def bug_filters(self):
        """See `IStructuralSubscription`."""
        return IStore(BugSubscriptionFilter).find(
            BugSubscriptionFilter,
            (BugSubscriptionFilter.id ==
             BugNotificationFilter.bug_subscription_filter_id),
            BugNotificationFilter.bug_notification == self)

    def destroySelf(self):
        Store.of(self).remove(self)


@implementer(IBugNotificationSet)
class BugNotificationSet:
    """A set of bug notifications."""

    def getNotificationsToSend(self):
        """See IBugNotificationSet."""
        # We preload the bug activity and the message in order to
        # try to reduce subsequent database calls: try to get direct
        # dependencies at once.  We then also pre-load the pertinent bugs,
        # people (with their own dependencies), and message chunks before
        # returning the notifications that should be processed.
        # Sidestep circular reference.
        from lp.bugs.model.bug import Bug
        store = IStore(BugNotification)
        source = store.using(BugNotification,
                             Join(Message,
                                  BugNotification.message == Message.id),
                             LeftJoin(
                                BugActivity,
                                BugNotification.activity == BugActivity.id))
        results = list(source.find(
            (BugNotification, BugActivity, Message),
            BugNotification.status == BugNotificationStatus.PENDING,
            BugNotification.date_emailed == None).order_by(
            'BugNotification.bug', '-BugNotification.id'))
        interval = timedelta(
            minutes=int(config.malone.bugnotification_interval))
        time_limit = (
            datetime.now(pytz.UTC) - interval)
        last_omitted_notification = None
        pending_notifications = []
        people_ids = set()
        bug_ids = set()
        for notification, ignore, ignore in results:
            if notification.message.datecreated > time_limit:
                last_omitted_notification = notification
            elif (last_omitted_notification is not None and
                notification.message.ownerID ==
                   last_omitted_notification.message.ownerID and
                notification.bug_id == last_omitted_notification.bug_id and
                last_omitted_notification.message.datecreated -
                notification.message.datecreated < interval):
                last_omitted_notification = notification
            if last_omitted_notification != notification:
                last_omitted_notification = None
                pending_notifications.append(notification)
                people_ids.add(notification.message.ownerID)
                bug_ids.add(notification.bug_id)
        # Now we do some calls that are purely for caching.
        # Converting these into lists forces the queries to execute.
        if pending_notifications:
            list(
                getUtility(IPersonSet).getPrecachedPersonsFromIDs(
                    list(people_ids),
                    need_validity=True,
                    need_preferred_email=True))
            list(
                IStore(Bug).find(Bug, In(Bug.id, list(bug_ids))))
        pending_notifications.reverse()
        return pending_notifications

    def getDeferredNotifications(self):
        """See `IBugNoticationSet`."""
        store = IStore(BugNotification)
        results = store.find(
            BugNotification,
            BugNotification.date_emailed == None,
            BugNotification.status == BugNotificationStatus.DEFERRED)
        return results

    def addNotification(self, bug, is_comment, message, recipients, activity,
                        deferred=False):
        """See `IBugNotificationSet`."""
        if deferred:
            status = BugNotificationStatus.DEFERRED
        else:
            if not recipients:
                return
            status = BugNotificationStatus.PENDING

        bug_notification = BugNotification(
            bug=bug, is_comment=is_comment,
            message=message, date_emailed=None, activity=activity,
            status=status)
        store = Store.of(bug_notification)
        # XXX jamesh 2008-05-21: these flushes are to fix ordering
        # problems in the bugnotification-sending.rst tests.
        store.flush()

        bulk.create(
            (BugNotificationRecipient.bug_notification,
             BugNotificationRecipient.person,
             BugNotificationRecipient.reason_body,
             BugNotificationRecipient.reason_header),
            [(bug_notification, recipient) + recipients.getReason(recipient)
             for recipient in recipients])
        bulk.create(
            (BugNotificationFilter.bug_notification,
             BugNotificationFilter.bug_subscription_filter),
            [(bug_notification, filter)
             for filter in recipients.subscription_filters])

        return bug_notification

    def getRecipientFilterData(self, bug, recipient_to_sources,
                               notifications):
        """See `IBugNotificationSet`."""
        if not notifications or not recipient_to_sources:
            # This is a shortcut that will remove some error conditions.
            return {}
        # Collect bug mute information.
        from lp.bugs.model.bug import BugMute
        store = IStore(BugMute)
        muted_person_ids = set(list(
            store.find(BugMute.person_id,
                       BugMute.bug == bug)))
        # This makes two calls to the database to get all the
        # information we need. The first call gets the filter ids and
        # descriptions for each recipient, and then we divide up the
        # information per recipient.
        # First we get some intermediate data structures set up.
        source_person_id_map = {}
        recipient_id_map = {}
        for recipient, sources in recipient_to_sources.items():
            if recipient.id in muted_person_ids:
                continue
            source_person_ids = set()
            recipient_id_map[recipient.id] = {
                'principal': recipient,
                'filters': {},
                'source person ids': source_person_ids,
                'sources': sources,
                }
            for source in sources:
                person_id = source.person.id
                source_person_ids.add(person_id)
                data = source_person_id_map.get(person_id)
                if data is None:
                    # The "filters" key is the only one we actually use.  The
                    # rest are useful for debugging and introspecting.
                    data = {'sources': set(),
                            'person': source.person,
                            'filters': {}}
                    source_person_id_map[person_id] = data
                data['sources'].add(source)
        # Now we actually look for the filters.
        store = IStore(BugSubscriptionFilter)
        source = store.using(
            BugSubscriptionFilter,
            Join(BugNotificationFilter,
                 BugSubscriptionFilter.id ==
                    BugNotificationFilter.bug_subscription_filter_id),
            Join(StructuralSubscription,
                 BugSubscriptionFilter.structural_subscription_id ==
                    StructuralSubscription.id))
        if len(source_person_id_map) == 0:
            filter_data = []
        else:
            filter_data = source.find(
                (StructuralSubscription.subscriberID,
                 BugSubscriptionFilter.id,
                 BugSubscriptionFilter.description),
                In(BugNotificationFilter.bug_notification_id,
                   [notification.id for notification in notifications]),
                In(StructuralSubscription.subscriberID,
                   list(source_person_id_map)))
        filter_ids = []
        # Record the filters for each source.
        for source_person_id, filter_id, filter_description in filter_data:
            source_person_id_map[source_person_id]['filters'][filter_id] = (
                filter_description)
            filter_ids.append(filter_id)

        # This is only necessary while production and sample data have
        # structural subscriptions without filters.  Assign the filters to
        # each recipient.
        no_filter_marker = -1

        for recipient_data in recipient_id_map.values():
            for source_person_id in recipient_data['source person ids']:
                recipient_data['filters'].update(
                    source_person_id_map[source_person_id]['filters']
                    or {no_filter_marker: None})
        if filter_ids:
            # Now we get the information about subscriptions that might be
            # filtered and take that into account.
            mute_data = store.find(
                (BugSubscriptionFilterMute.person_id,
                 BugSubscriptionFilterMute.filter_id),
                In(BugSubscriptionFilterMute.person_id,
                   list(recipient_id_map)),
                In(BugSubscriptionFilterMute.filter_id, filter_ids))
            for person_id, filter_id in mute_data:
                if filter_id in recipient_id_map[person_id]['filters']:
                    del recipient_id_map[person_id]['filters'][filter_id]
                # This may look odd, but it's here to prevent members of
                # a team with a contact address still getting direct
                # email about a bug after they've muted the
                # subscription.
                if no_filter_marker in recipient_id_map[person_id]['filters']:
                    del recipient_id_map[
                        person_id]['filters'][no_filter_marker]
        # Now recipient_id_map has all the information we need.  Let's
        # build the final result and return it.
        result = {}
        for recipient_data in recipient_id_map.values():
            if recipient_data['filters']:
                filter_descriptions = [
                    description for description
                    in recipient_data['filters'].values() if description]
                filter_descriptions.sort()  # This is good for tests.
                result[recipient_data['principal']] = {
                    'sources': recipient_data['sources'],
                    'filter descriptions': filter_descriptions}
        return result


@implementer(IBugNotificationRecipient)
class BugNotificationRecipient(StormBase):
    """A recipient of a bug notification."""

    __storm_table__ = 'BugNotificationRecipient'

    id = Int(primary=True)

    bug_notification_id = Int(name='bug_notification', allow_none=False)
    bug_notification = Reference(bug_notification_id, 'BugNotification.id')

    person_id = Int(name='person', allow_none=False)
    person = Reference(person_id, 'Person.id')

    reason_header = Unicode(name='reason_header', allow_none=False)
    reason_body = Unicode(name='reason_body', allow_none=False)

    def __init__(self, bug_notification, person, reason_header, reason_body):
        self.bug_notification = bug_notification
        self.person = person
        self.reason_header = reason_header
        self.reason_body = reason_body


@implementer(IBugNotificationFilter)
class BugNotificationFilter(StormBase):
    """See `IBugNotificationFilter`."""

    __storm_table__ = "BugNotificationFilter"
    __storm_primary__ = "bug_notification_id", "bug_subscription_filter_id"

    def __init__(self, bug_notification, bug_subscription_filter):
        self.bug_notification = bug_notification
        self.bug_subscription_filter = bug_subscription_filter

    bug_notification_id = Int(
        "bug_notification", allow_none=False)
    bug_notification = Reference(
        bug_notification_id, "BugNotification.id")

    bug_subscription_filter_id = Int(
        "bug_subscription_filter", allow_none=False)
    bug_subscription_filter = Reference(
        bug_subscription_filter_id, "BugSubscriptionFilter.id")
