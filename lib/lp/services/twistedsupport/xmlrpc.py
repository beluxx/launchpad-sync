# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Support for XML-RPC stuff with Twisted."""

__all__ = [
    'BlockingProxy',
    'DeferredBlockingProxy',
    'trap_fault',
    ]

from twisted.internet import defer
from twisted.web import xmlrpc


class BlockingProxy:
    """Make a ServerProxy behave like a Twisted XML-RPC proxy.

    This is useful for writing code that needs to work in both a synchronous
    and asynchronous fashion.

    Also, some people prefer the callRemote style of invocation, which is more
    explicit.
    """

    def __init__(self, proxy):
        """Construct a `BlockingProxy`.

        :param proxy: An xmlrpc_client.ServerProxy.
        """
        self._proxy = proxy

    def callRemote(self, method_name, *args, **kwargs):
        return getattr(self._proxy, method_name)(*args, **kwargs)


class DeferredBlockingProxy(BlockingProxy):
    """Make a ServerProxy behave more like a Twisted XML-RPC proxy.

    This is almost exactly like 'BlockingProxy', except that this returns
    Deferreds. It is guaranteed to be exactly as synchronous as the passed-in
    proxy. That means if you pass in a normal xmlrpc_client proxy you ought to
    be able to use `lp.services.twistedsupport.extract_result` to get the
    result.
    """

    def callRemote(self, method_name, *args, **kwargs):
        return defer.maybeDeferred(
            super(DeferredBlockingProxy, self).callRemote,
            method_name, *args, **kwargs)


def trap_fault(failure, *fault_classes):
    """Trap a fault, based on fault code.

    :param failure: A Twisted L{Failure}.
    :param *fault_codes: `LaunchpadFault` subclasses.
    :raise Exception: if 'failure' is not a Fault failure, or if the fault
        code does not match the given codes.  In line with L{Failure.trap},
        the exception is the L{Failure} itself on Python 2 and the
        underlying exception on Python 3.
    :return: The Fault if it matches one of the codes.
    """
    failure.trap(xmlrpc.Fault)
    fault = failure.value
    if fault.faultCode in [cls.error_code for cls in fault_classes]:
        return fault
    failure.raiseException()
