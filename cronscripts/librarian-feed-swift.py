#!/usr/bin/python2 -S
#
# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Move files from Librarian disk storage into Swift."""

__metaclass__ = type

import _pythonpath  # noqa: F401

import os

import six

from lp.services.database.interfaces import ISlaveStore
from lp.services.librarian.model import LibraryFileContent
from lp.services.librarianserver import swift
from lp.services.scripts.base import LaunchpadCronScript


class LibrarianFeedSwift(LaunchpadCronScript):
    def add_my_options(self):
        self.parser.add_option(
            "-i", "--id", action="append", dest="ids", default=[],
            metavar="CONTENT_ID", help="Migrate a single file")
        self.parser.add_option(
            "--remove", action="store_true", default=False,
            help="Remove files from disk after migration (default: False)")
        self.parser.add_option(
            "--rename", action="store_true", default=False,
            help="Rename files on disk after migration (default: False)")
        self.parser.add_option(
            "-s", "--start", action="store", type=int, default=None,
            dest="start", metavar="CONTENT_ID",
            help="Migrate files starting from CONTENT_ID")
        self.parser.add_option(
            "--start-since", action="store", dest='start_since',
            default=None, metavar="INTERVAL",
            help="Migrate files older than INTERVAL (PostgreSQL syntax)")
        self.parser.add_option(
            "-e", "--end", action="store", type=int, default=None,
            dest="end", metavar="CONTENT_ID",
            help="Migrate files up to and including CONTENT_ID")
        self.parser.add_option(
            "--end-at", action="store", dest='end_at',
            default=None, metavar="INTERVAL",
            help="Don't migrate files older than INTERVAL "
                 "(PostgreSQL syntax)")
        self.parser.add_option(
            "--instance-id", action="store", type=int, default=None,
            metavar="INSTANCE_ID",
            help=(
                "Run as instance INSTANCE_ID (starting at 0) out of "
                "NUM_INSTANCES parallel workers"))
        self.parser.add_option(
            "--num-instances", action="store", type=int, default=None,
            metavar="NUM_INSTANCES",
            help="Run NUM_INSTANCES parallel workers")

    @property
    def lockfilename(self):
        if self.options.instance_id is not None:
            return "launchpad-%s-%d.lock" % (
                self.name, self.options.instance_id)
        else:
            return "launchpad-%s.lock" % self.name

    def main(self):
        if self.options.rename and self.options.remove:
            self.parser.error("Cannot both remove and rename")
        elif self.options.rename:
            remove = swift.rename
        elif self.options.remove:
            remove = os.unlink
        else:
            remove = None

        if self.options.start_since:
            self.options.start = ISlaveStore(LibraryFileContent).execute("""
                SELECT MAX(id) FROM LibraryFileContent
                WHERE datecreated < current_timestamp at time zone 'UTC'
                    - CAST(%s AS INTERVAL)
                """, (six.text_type(self.options.start_since),)).get_one()[0]

        if self.options.end_at:
            self.options.end = ISlaveStore(LibraryFileContent).execute("""
                SELECT MAX(id) FROM LibraryFileContent
                WHERE datecreated < current_timestamp at time zone 'UTC'
                    - CAST(%s AS INTERVAL)
                """, (six.text_type(self.options.end_at),)).get_one()[0]

        if ((self.options.instance_id is None) !=
                (self.options.num_instances is None)):
            self.parser.error(
                "Must specify both or neither of --instance-id and "
                "--num-instances")

        kwargs = {
            "instance_id": self.options.instance_id,
            "num_instances": self.options.num_instances,
            "remove_func": remove,
            }

        if self.options.ids and (self.options.start or self.options.end):
            self.parser.error(
                "Cannot specify both individual file(s) and range")

        elif self.options.ids:
            for lfc in self.options.ids:
                swift.to_swift(
                    self.logger, start_lfc_id=lfc, end_lfc_id=lfc, **kwargs)

        else:
            swift.to_swift(
                self.logger, start_lfc_id=self.options.start,
                end_lfc_id=self.options.end, **kwargs)
        self.logger.info('Done')


if __name__ == '__main__':
    # Ensure that our connections to Swift are direct, and not going via
    # a web proxy that would likely block us in any case.
    if 'http_proxy' in os.environ:
        del os.environ['http_proxy']
    if 'HTTP_PROXY' in os.environ:
        del os.environ['HTTP_PROXY']
    script = LibrarianFeedSwift(
        'librarian-feed-swift', dbuser='librarianfeedswift')
    script.lock_and_run(isolation='autocommit')
