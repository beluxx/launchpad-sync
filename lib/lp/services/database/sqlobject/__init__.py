# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Expose the Storm SQLObject compatibility layer."""

# SKIP this file when reformatting, due to the sys mangling.
import datetime

from storm.expr import SQL
from storm.sqlobject import *  # noqa: F401,F403

_sqlStringReplace = [
    ("\\", "\\\\"),
    ("'", "''"),
    ("\000", "\\0"),
    ("\b", "\\b"),
    ("\n", "\\n"),
    ("\r", "\\r"),
    ("\t", "\\t"),
]

# XXX 2007-03-07 jamesh:
# This is a cut down version of sqlobject's sqlrepr() method.  Ideally
# we can get rid of this as code is converted to use store.execute().
def sqlrepr(value, dbname=None):
    assert dbname in [None, "postgres"]
    if hasattr(value, "__sqlrepr__"):
        return value.__sqlrepr__(dbname)
    elif hasattr(value, "getquoted"):
        return value.getquoted()
    elif isinstance(value, SQL):
        return value.expr
    elif isinstance(value, str):
        for orig, repl in _sqlStringReplace:
            value = value.replace(orig, repl)
        return "E'%s'" % value
    elif isinstance(value, bool):
        if value:
            return "'t'"
        else:
            return "'f'"
    elif isinstance(value, int):
        return repr(int(value))
    elif isinstance(value, float):
        return repr(value)
    elif value is None:
        return "NULL"
    elif isinstance(value, (list, set, tuple)):
        return "(%s)" % ", ".join(sqlrepr(v, dbname) for v in value)
    elif isinstance(value, datetime.datetime):
        return value.strftime("'%Y-%m-%dT%H:%M:%S'")
    elif isinstance(value, datetime.time):
        return value.strftime("'%H:%M:%S'")
    elif isinstance(value, datetime.date):
        return value.strftime("'%Y-%m-%d'")
    elif isinstance(value, datetime.timedelta):
        return "INTERVAL '%d DAYS %d SECONDS %d MICROSECONDS'" % (
            value.days,
            value.seconds,
            value.microseconds,
        )
    else:
        raise AssertionError("Unhandled type: %r" % type(value))
