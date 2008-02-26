# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Proxies that connect to XML-RPC servers."""

__metaclass__ = type
__all__ = [
    'get_blocking_proxy',
    'get_twisted_proxy',
    'InMemoryBlockingProxy',
    'InMemoryTwistedProxy',
    ]

import xmlrpclib

from canonical.authserver.database import DatabaseUserDetailsStorageV2
from canonical.authserver.xmlrpc import UserDetailsResourceV2

from twisted.internet import defer
from twisted.web.xmlrpc import Proxy

from zope.interface.interface import Method


def get_twisted_proxy(url):
    if url == 'fake:///user-details-2':
        return InMemoryTwistedProxy(
            UserDetailsResourceV2(
                DatabaseUserDetailsStorageV2(_make_connection_pool())))
    return Proxy(url)


def get_blocking_proxy(url):
    return xmlrpclib.ServerProxy(url)


def _make_connection_pool():
    """Construct a ConnectionPool from the database settings in the
    Launchpad config.
    """
    from canonical.config import config
    from twisted.enterprise.adbapi import ConnectionPool
    if config.dbhost is None:
        dbhost = ''
    else:
        dbhost = 'host=' + config.dbhost
    ConnectionPool.min = ConnectionPool.max = 1
    dbpool = ConnectionPool(
        'psycopg', 'dbname=%s %s user=%s' % (
            config.dbname, dbhost, config.authserver.dbuser),
        cp_reconnect=True)
    return dbpool


def get_method_names_in_interface(interface):
    for attribute_name in interface:
        if isinstance(interface[attribute_name], Method):
            yield attribute_name


class InMemoryBlockingProxy:
    """ServerProxy work-a-like that calls methods directly."""

    def __init__(self, xmlrpc_object, method_names):
        self._xmlrpc_object = xmlrpc_object
        self._method_names = method_names

    def _faultMaker(self, code, string):
        """Return a callable that raises a Fault when called."""
        def raise_fault(*args):
            raise xmlrpclib.Fault(code, string)
        return raise_fault

    def _checkMarshalling(self, function):
        """Decorate function to check it for marshallability.

        Checks the arguments and return values for whether or not they can
        be passed via XML-RPC. Mostly, this means checking for None.
        """
        def call_method(*args):
            xmlrpclib.dumps(args)
            result = function(*args)
            try:
                xmlrpclib.dumps((result,))
            except TypeError:
                raise xmlrpclib.Fault(
                    8002, "can't serialize output (%r)" % (result,))
            return result
        return call_method

    def __getattr__(self, name):
        if name not in self._method_names:
            return self._faultMaker(8001, 'function %s not found' % (name,))
        return self._checkMarshalling(getattr(self._xmlrpc_object, name))


class InMemoryTwistedProxy:

    debug = False

    def __init__(self, xmlrpc_object):
        self.xmlrpc_object = xmlrpc_object

    def _checkArgumentsMarshallable(self, args):
        """Raise a `TypeError` if `args` are not marhallable."""
        xmlrpclib.dumps(args)

    def _checkReturnValueMarshallable(self, result):
        try:
            xmlrpclib.dumps((result,))
        except TypeError:
            raise xmlrpclib.Fault(
                8002, "can't serialize output (%r)" % (result,))
        return result

    def callRemote(self, method_name, *args):
        self._checkArgumentsMarshallable(args)
        try:
            method = getattr(self.xmlrpc_object, 'xmlrpc_%s' % (method_name,))
        except AttributeError:
            return defer.fail(xmlrpclib.Fault(
                8001, "Method %r does not exist" % (method_name,)))
        deferred = defer.maybeDeferred(method, *args)
        if self.debug:
            def debug(value, message):
                print '%s%r -> %r (%s)' % (method_name, args, value, message)
                return value
            deferred.addCallback(debug, 'SUCCESS')
            deferred.addErrback(debug, 'FAILURE')
        return deferred.addCallback(self._checkReturnValueMarshallable)
