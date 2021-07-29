#!/usr/bin/python2 -S
#
# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Conveniently generates access token and outputs relevant settings."""


import _pythonpath  # noqa: F401

import sys

import six
from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.services.oauth.interfaces import IOAuthConsumerSet
from lp.services.scripts.base import LaunchpadScript
from lp.services.webapp.interfaces import OAuthPermission


LP_API_URL = 'https://api.launchpad.test/devel'


def print_local_settings(user, key, token, secret):
    print("Access token for {user} generated with the following settings:\n\n"
          "LP_API_URL = '{url}'\n"
          "LP_API_CONSUMER_KEY = '{key}'\n"
          "LP_API_TOKEN = '{token}'\n"
          "LP_API_TOKEN_SECRET = '{secret}'").format(
              user=user,
              url=LP_API_URL,
              key=key,
              token=token,
              secret=secret)


class AccessTokenGenerator(LaunchpadScript):

    def add_my_options(self):
        self.parser.usage = "%prog username [-n CONSUMER NAME]"
        self.parser.add_option("-n", "--name", dest="consumer_name")

    def main(self):
        if len(self.args) < 1:
            self.parser.error('No username supplied')
        username = self.args[0]

        key = six.ensure_text(self.options.consumer_name)
        consumer = getUtility(IOAuthConsumerSet).new(key, u'')
        request_token, _ = consumer.newRequestToken()

        # review by username
        person = getUtility(IPersonSet).getByName(username)
        if not person:
            print('Error: No account for username %s.' % username)
            sys.exit(1)
        request_token.review(person, OAuthPermission.WRITE_PRIVATE)

        # create access token
        access_token, access_secret = request_token.createAccessToken()

        self.txn.commit()

        print_local_settings(person.name,
                             self.options.consumer_name,
                             access_token.key,
                             access_secret)


if __name__ == '__main__':
    AccessTokenGenerator('generate-access-token').lock_and_run()
