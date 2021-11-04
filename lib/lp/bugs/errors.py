# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Errors used in the lp/bugs modules."""

__all__ = [
    'InvalidDuplicateValue',
    'InvalidSearchParameters',
]

import http.client

from lazr.restful.declarations import error_status

from lp.app.validators import LaunchpadValidationError


@error_status(http.client.EXPECTATION_FAILED)
class InvalidDuplicateValue(LaunchpadValidationError):
    """A bug cannot be set as the duplicate of another."""


@error_status(http.client.BAD_REQUEST)
class InvalidSearchParameters(ValueError):
    """Invalid search parameters were passed to searchTasks."""
