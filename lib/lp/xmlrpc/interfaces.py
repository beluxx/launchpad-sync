# Copyright 2011-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for the Launchpad application."""

__all__ = [
    'IPrivateApplication',
    ]

from zope.interface import Attribute

from lp.services.webapp.interfaces import ILaunchpadApplication


class IPrivateApplication(ILaunchpadApplication):
    """Launchpad private XML-RPC application root."""

    archive = Attribute("Archive XML-RPC end point.""")

    authserver = Attribute("""Old Authserver API end point.""")

    codeimportscheduler = Attribute("""Code import scheduler end point.""")

    codehosting = Attribute("""Codehosting end point.""")

    mailinglists = Attribute("""Mailing list XML-RPC end point.""")

    bugs = Attribute("""Launchpad Bugs XML-RPC end point.""")

    canonicalsso = Attribute(
        """Canonical SSO XML-RPC end point.""")

    featureflags = Attribute("""Feature flag information endpoint""")

    git = Attribute("Git end point.")
