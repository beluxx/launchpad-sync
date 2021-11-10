# Copyright 2017-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Timeline-friendly Launchpad Memcache client."""

__all__ = [
    'TimelineRecordingClient',
    ]

import logging

from lazr.restful.utils import get_current_browser_request
from pymemcache.client.hash import HashClient

from lp.services import features
from lp.services.timeline.requesttimeline import get_request_timeline


class TimelineRecordingClient(HashClient):

    def __get_timeline_action(self, suffix, key):
        request = get_current_browser_request()
        timeline = get_request_timeline(request)
        return timeline.start("memcache-%s" % suffix, key)

    @property
    def _enabled(self):
        configured_value = features.getFeatureFlag('memcache')
        if configured_value is None:
            return True
        else:
            return configured_value

    def get(self, key):
        if not self._enabled:
            return None
        action = self.__get_timeline_action("get", key)
        try:
            return HashClient.get(self, key)
        finally:
            action.finish()

    def set(self, key, value, expire=0):
        if not self._enabled:
            return None
        action = self.__get_timeline_action("set", key)
        try:
            success = HashClient.set(self, key, value, expire=expire)
            if success:
                logging.debug("Memcache set succeeded for %s", key)
            else:
                logging.warning("Memcache set failed for %s", key)
            return success
        finally:
            action.finish()
