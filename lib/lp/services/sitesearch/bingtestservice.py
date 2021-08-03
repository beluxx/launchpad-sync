#!/usr/bin/python3
#
# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
This script runs a simple HTTP server. The server returns JSON files
when given certain user-configurable URLs.
"""

__metaclass__ = type

import logging
import os

from six.moves.BaseHTTPServer import HTTPServer

from lp.services.config import config
from lp.services.osutils import ensure_directory_exists
from lp.services.pidfile import make_pidfile
from lp.services.sitesearch import testservice


# Set up basic logging.
log = logging.getLogger(__name__)

# The default service name, used by the Launchpad service framework.
service_name = 'bing-webservice'


class BingRequestHandler(testservice.RequestHandler):
    default_content_type = 'application/json; charset=UTF-8'
    log = log
    mapfile = config.bing_test_service.mapfile
    content_dir = config.bing_test_service.canned_response_directory


def start_as_process():
    return testservice.start_as_process('bingtestservice')


def get_service_endpoint():
    """Return the host and port that the service is running on."""
    return testservice.hostpair(config.bing.site)


def service_is_available():
    host, port = get_service_endpoint()
    return testservice.service_is_available(host, port)


def wait_for_service():
    host, port = get_service_endpoint()
    return testservice.wait_for_service(host, port)


def kill_running_process():
    global service_name
    host, port = get_service_endpoint()
    return testservice.kill_running_process(service_name, host, port)


def main():
    """Run the HTTP server."""
    # Redirect our service output to a log file.
    global log
    ensure_directory_exists(os.path.dirname(config.bing_test_service.log))
    filelog = logging.FileHandler(config.bing_test_service.log)
    log.addHandler(filelog)
    log.setLevel(logging.DEBUG)

    # To support service shutdown we need to create a PID file that is
    # understood by the Launchpad services framework.
    global service_name
    make_pidfile(service_name)

    host, port = get_service_endpoint()
    server = HTTPServer((host, port), BingRequestHandler)

    log.info("Starting HTTP Bing webservice server on port %s", port)
    server.serve_forever()
