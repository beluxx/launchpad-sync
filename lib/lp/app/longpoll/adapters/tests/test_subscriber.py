# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll subscriber adapter tests."""

__metaclass__ = type

from itertools import count

from lazr.restful.interfaces import IJSONRequestCache
from testtools.matchers import Not
from zope.interface import implements

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.app.longpoll.adapters.subscriber import LongPollSubscriber
from lp.app.longpoll.interfaces import (
    ILongPollEvent,
    ILongPollSubscriber,
    )
from lp.services.messaging.queue import (
    RabbitQueue,
    RabbitRoutingKey,
    )
from lp.testing import TestCase
from lp.testing.matchers import Contains


class FakeEvent:

    implements(ILongPollEvent)

    event_key_indexes = count(1)

    def __init__(self):
        self.event_key = "event-key-%d" % next(self.event_key_indexes)


class TestLongPollSubscriber(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_interface(self):
        request = LaunchpadTestRequest()
        subscriber = LongPollSubscriber(request)
        self.assertProvides(subscriber, ILongPollSubscriber)

    def test_subscribe_key(self):
        request = LaunchpadTestRequest()
        subscriber = LongPollSubscriber(request)
        # A subscribe key is not generated yet.
        self.assertIs(subscriber.subscribe_key, None)
        # It it only generated on the first subscription.
        subscriber.subscribe(FakeEvent())
        subscribe_key = subscriber.subscribe_key
        self.assertIsInstance(subscribe_key, str)
        self.assertEqual(36, len(subscribe_key))
        # It remains the same for later subscriptions.
        subscriber.subscribe(FakeEvent())
        self.assertEqual(subscribe_key, subscriber.subscribe_key)

    def test_adapter(self):
        request = LaunchpadTestRequest()
        subscriber = ILongPollSubscriber(request)
        self.assertIsInstance(subscriber, LongPollSubscriber)
        # A difference subscriber is returned on subsequent adaptions, but it
        # has the same subscribe_key.
        subscriber2 = ILongPollSubscriber(request)
        self.assertIsNot(subscriber, subscriber2)
        self.assertEqual(subscriber.subscribe_key, subscriber2.subscribe_key)

    def test_subscribe_queue(self):
        # LongPollSubscriber.subscribe() creates a new queue with a new unique
        # name that is bound to the event's event_key.
        request = LaunchpadTestRequest()
        event = FakeEvent()
        subscriber = ILongPollSubscriber(request)
        subscriber.subscribe(event)
        message = '{"hello": 1234}'
        routing_key = RabbitRoutingKey(event.event_key)
        routing_key.send_now(message)
        subscribe_queue = RabbitQueue(subscriber.subscribe_key)
        self.assertEqual(
            message, subscribe_queue.receive(timeout=5))

    def test_json_cache_not_populated_on_init(self):
        # LongPollSubscriber does not put the name of the new queue into the
        # JSON cache.
        request = LaunchpadTestRequest()
        cache = IJSONRequestCache(request)
        self.assertThat(cache.objects, Not(Contains("longpoll")))
        ILongPollSubscriber(request)
        self.assertThat(cache.objects, Not(Contains("longpoll")))

    def test_json_cache_populated_on_subscribe(self):
        # To aid with debugging the event_key of subscriptions are added to
        # the JSON cache.
        request = LaunchpadTestRequest()
        cache = IJSONRequestCache(request)
        event1 = FakeEvent()
        ILongPollSubscriber(request).subscribe(event1)  # Side-effects!
        self.assertThat(cache.objects, Contains("longpoll"))
        self.assertThat(cache.objects["longpoll"], Contains("key"))
        self.assertThat(cache.objects["longpoll"], Contains("subscriptions"))
        self.assertEqual(
            [event1.event_key],
            cache.objects["longpoll"]["subscriptions"])
        # More events can be subscribed.
        event2 = FakeEvent()
        ILongPollSubscriber(request).subscribe(event2)
        self.assertEqual(
            [event1.event_key, event2.event_key],
            cache.objects["longpoll"]["subscriptions"])
