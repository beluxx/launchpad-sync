# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""WSGI script to start web server."""

__all__ = []

from zope.event import notify
import zope.processlifetime

from lp.services.webapp.wsgi import get_wsgi_application


application = get_wsgi_application()

notify(zope.processlifetime.ProcessStarting())
