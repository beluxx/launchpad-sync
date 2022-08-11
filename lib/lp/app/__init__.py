# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""This package contains the Launchpad.net web application.

It contains the code and templates that glue all the other components
together. As such, it can import from any modules, but nothing should import
from it.
"""

from typing import List

from zope.formlib import itemswidgets

# Load versioninfo.py so that we get errors on start-up rather than waiting
# for first page load.
import lp.app.versioninfo  # noqa: F401

__all__ = []  # type: List[str]


# Zope recently changed the behaviour of items widgets with regards to missing
# values, but they kindly left this global variable for you to monkey patch if
# you want the old behaviour, just like we do.
itemswidgets.EXPLICIT_EMPTY_SELECTION = False
