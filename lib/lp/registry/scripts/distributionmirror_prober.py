# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'DistroMirrorProber',
    ]

from datetime import datetime
import http.client
import io
import itertools
import logging
import os.path

import OpenSSL
from OpenSSL.SSL import (
    Context,
    TLSv1_2_METHOD,
    )
import requests
import six
from six.moves.urllib.parse import (
    unquote,
    urljoin,
    urlparse,
    urlunparse,
    )
from treq.client import HTTPClient as TreqHTTPClient
from twisted.internet import (
    defer,
    protocol,
    reactor,
    )
from twisted.internet.defer import (
    CancelledError,
    DeferredSemaphore,
    )
from twisted.internet.ssl import VerificationError
from twisted.python.failure import Failure
from twisted.web.client import (
    Agent,
    BrowserLikePolicyForHTTPS,
    ResponseNeverReceived,
    )
from twisted.web.http import HTTPClient
from twisted.web.iweb import IResponse
from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.distributionmirror import (
    IDistributionMirrorSet,
    MirrorContent,
    MirrorFreshness,
    UnableToFetchCDImageFileList,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.services.config import config
from lp.services.httpproxy.connect_tunneling import TunnelingAgent
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.services.timeout import urlfetch
from lp.services.webapp import canonical_url
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries


# The requests/timeouts ratio has to be at least 3 for us to keep issuing
# requests on a given host. (This ratio is per run, rather than held long
# term)
# IMPORTANT: Changing these values can cause lots of false negatives when
# probing mirrors, so please don't change them unless you know what you're
# doing.

MIN_REQUEST_TIMEOUT_RATIO = 3
MIN_REQUESTS_TO_CONSIDER_RATIO = 30

# XXX Guilherme Salgado 2007-01-30 bug=82201:
# We need to get rid of these global dicts in this module.
host_requests = {}
host_timeouts = {}
# Set of invalid certificate (host, port) tuples, to avoid doing HTTPS calls
# to hosts we already know they are not valid.
invalid_certificate_hosts = set()

MAX_REDIRECTS = 3


class LoggingMixin:
    """Common logging class for archive and releases mirror messages."""

    def _getTime(self):
        """Return the current UTC time."""
        return datetime.utcnow()

    def logMessage(self, message):
        """Append a UTC timestamp to the message returned by the mirror
        prober.
        """
        timestamp = datetime.ctime(self._getTime())
        self.log_file.write(timestamp + ": " + message)


class RequestManager:

    # Yes, I want a mutable class attribute because I want changes done in an
    # instance to be visible in other instances as well.
    host_locks = {}

    def __init__(self, max_parallel, max_parallel_per_host):
        self.max_parallel = max_parallel
        self.max_parallel_per_host = max_parallel_per_host
        self.overall_semaphore = DeferredSemaphore(max_parallel)

    def run(self, host, probe_func):
        # Use a MultiLock with one semaphore limiting the overall
        # connections and another limiting the per-host connections.
        if host in self.host_locks:
            multi_lock = self.host_locks[host]
        else:
            multi_lock = MultiLock(
                self.overall_semaphore,
                DeferredSemaphore(self.max_parallel_per_host))
            self.host_locks[host] = multi_lock
        return multi_lock.run(probe_func)


class MultiLock(defer._ConcurrencyPrimitive):
    """Lock that acquires multiple underlying locks before it is acquired."""

    def __init__(self, overall_lock, host_lock):
        defer._ConcurrencyPrimitive.__init__(self)
        self.overall_lock = overall_lock
        self.host_lock = host_lock
        # host_lock will always be the scarcer resource, so it should be the
        # first to be acquired.
        self._locks = [host_lock, overall_lock]

    def acquire(self):
        return defer.gatherResults([lock.acquire() for lock in self._locks])

    def release(self):
        for lock in self._locks:
            lock.release()


class ProberProtocol(HTTPClient):
    """Simple HTTP client to probe path existence via HEAD."""

    def connectionMade(self):
        """Simply requests path presence."""
        self.makeRequest()
        self.headers = {}

    def makeRequest(self):
        """Request path presence via HTTP/1.1 using HEAD.

        Uses factory.connect_host and factory.connect_path
        """
        self.sendCommand(b'HEAD', self.factory.connect_path.encode('UTF-8'))
        self.sendHeader(b'HOST', self.factory.connect_host.encode('UTF-8'))
        self.sendHeader(b'User-Agent',
            b'Launchpad Mirror Prober ( https://launchpad.net/ )')
        self.endHeaders()

    def handleStatus(self, version, status, message):
        # According to http://lists.debian.org/deity/2001/10/msg00046.html,
        # apt intentionally handles only '200 OK' responses, so we do the
        # same here.
        try:
            status = int(status)
            if status == http.client.OK:
                self.factory.succeeded(status)
            else:
                self.factory.failed(Failure(BadResponseCode(status)))
        except ValueError:
            self.factory.failed(Failure(BadResponseCode(status)))
        self.transport.loseConnection()

    def handleResponse(self, response):
        # The status is all we need, so we don't need to do anything with
        # the response
        pass


class HTTPSProbeFailureHandler:
    """Handler to translate general errors into expected errors on HTTPS
    connections."""
    def __init__(self, factory):
        self.factory = factory

    def handleResponse(self, response):
        """Translates any request with return code different from 200 into
        an error in the callback chain.

        Note that other 2xx codes that are not 200 are considered errors too.
        This behaviour is the same as seen in ProberProtocol.handleStatus,
        for HTTP responses.
        """
        status = response.code
        if status == http.client.OK:
            return response
        else:
            raise BadResponseCode(status, response)

    def handleErrors(self, error):
        """Handle exceptions in https requests.
        """
        if self.isInvalidCertificateError(error):
            invalid_certificate_hosts.add(
                (self.factory.request_host, self.factory.request_port))
            raise InvalidHTTPSCertificate(
                self.factory.request_host, self.factory.request_port)
        if self.isTimeout(error):
            raise ProberTimeout(self.factory.url, self.factory.timeout)
        raise error

    def isTimeout(self, error):
        """Checks if the error was caused by a timeout.
        """
        return self._isErrorFromType(error, CancelledError)

    def isInvalidCertificateError(self, error):
        """Checks if the error was caused by an invalid certificate.
        """
        # It might be a raw SSL error, or a twisted-encapsulated
        # verification error (such as DNSMismatch error when the
        # certificate is valid for a different domain, for example).
        return self._isErrorFromType(
            error, OpenSSL.SSL.Error, VerificationError)

    def _isErrorFromType(self, error, *types):
        """Checks if the error was caused by any of the given types.
        """
        if not isinstance(error.value, ResponseNeverReceived):
            return False
        for reason in error.value.reasons:
            if reason.check(*types) is not None:
                return True
        return False


class RedirectAwareProberProtocol(ProberProtocol):
    """A specialized version of ProberProtocol that follows HTTP redirects."""

    redirected_to_location = False

    # The different redirect statuses that I handle.
    handled_redirect_statuses = (
        http.client.MOVED_PERMANENTLY, http.client.FOUND,
        http.client.SEE_OTHER)

    def handleHeader(self, key, value):
        key = key.lower()
        self.headers.setdefault(key, []).append(value)

    def handleStatus(self, version, status, message):
        if int(status) in self.handled_redirect_statuses:
            # We need to redirect to the location specified in the headers.
            self.redirected_to_location = True
        else:
            # We have the result immediately.
            ProberProtocol.handleStatus(self, version, status, message)

    def handleEndHeaders(self):
        assert self.redirected_to_location, (
            'All headers received but failed to find a result.')

        # Server responded redirecting us to another location.
        location = self.headers.get(b'location')
        url = location[0]
        self.factory.redirect(url)
        self.transport.loseConnection()


class ProberFactory(protocol.ClientFactory):
    """Factory using ProberProtocol to probe single URL existence."""

    protocol = ProberProtocol

    # Details of the URL of the host in which we actually want to request the
    # confirmation from.
    request_scheme = None
    request_host = None
    request_port = None
    request_path = None

    # Details of the URL of the host in which we'll connect, which will only
    # be different from request_* in case we have a configured http_proxy --
    # in that case the scheme, host and port will be the ones extracted from
    # http_proxy and the path will be self.url.
    connect_scheme = None
    connect_host = None
    connect_port = None
    connect_path = None

    https_agent_policy = BrowserLikePolicyForHTTPS

    def __init__(self, url, timeout=config.distributionmirrorprober.timeout):
        # We want the deferred to be a private attribute (_deferred) to make
        # sure our clients will only use the deferred returned by the probe()
        # method; this is to ensure self._cancelTimeout is always the first
        # callback in the chain.
        self._deferred = defer.Deferred()
        self.timeout = timeout
        self.timeoutCall = None
        self.setURL(url)
        self.logger = logging.getLogger('distributionmirror-prober')
        self._https_client = None

    @property
    def is_https(self):
        return self.request_scheme == 'https'

    def probe(self):
        logger = self.logger
        # NOTE: We don't want to issue connections to any outside host when
        # running the mirror prober in a development machine, so we do this
        # hack here.
        if (self.connect_host != 'localhost'
            and config.distributionmirrorprober.localhost_only):
            reactor.callLater(0, self.succeeded, '200')
            logger.debug("Forging a successful response on %s as we've been "
                         "told to probe only local URLs." % self.url)
            return self._deferred

        if should_skip_host(self.request_host):
            reactor.callLater(0, self.failed, ConnectionSkipped(self.url))
            logger.debug("Skipping %s as we've had too many timeouts on this "
                         "host already." % self.url)
            return self._deferred

        if (self.request_host, self.request_port) in invalid_certificate_hosts:
            reactor.callLater(
                0, self.failed, InvalidHTTPSCertificateSkipped(self.url))
            logger.debug("Skipping %s as it doesn't have a valid HTTPS "
                         "certificate" % self.url)
            return self._deferred

        self.connect()
        logger.debug('Probing %s' % self.url)
        return self._deferred

    def getHttpsClient(self):
        if self._https_client is not None:
            return self._https_client
        # Should we use a proxy?
        if not config.launchpad.http_proxy:
            agent = Agent(
                reactor=reactor, contextFactory=self.https_agent_policy())
        else:
            contextFactory = self.https_agent_policy()
            # XXX: pappacena 2020-03-16
            # TLS version 1.2 should work for most servers. But if it
            # doesn't, we should implement a negotiation mechanism to test
            # which version should be used before doing the actual probing
            # request.
            # One way to debug which version a given server is compatible
            # with using curl is issuing the following command:
            # curl -v --head https://<server-host> --tlsv1.2 --tls-max 1.2
            # (changing 1.2 with other version numbers)
            contextFactory.getContext = lambda: Context(TLSv1_2_METHOD)
            agent = TunnelingAgent(
                reactor, (self.connect_host, self.connect_port, None),
                contextFactory=contextFactory)
        self._https_client = TreqHTTPClient(agent)
        return self._https_client

    def connect(self):
        """Starts the connection and sets the self._deferred to the proper
        task.
        """
        host_requests[self.request_host] += 1
        if self.is_https:
            treq = self.getHttpsClient()
            self._deferred.addCallback(
                lambda _: treq.head(
                    self.url, reactor=reactor, allow_redirects=True,
                    timeout=self.timeout))
            error_handler = HTTPSProbeFailureHandler(self)
            self._deferred.addCallback(error_handler.handleResponse)
            self._deferred.addErrback(error_handler.handleErrors)
            reactor.callWhenRunning(self._deferred.callback, None)
        else:
            reactor.connectTCP(self.connect_host, self.connect_port, self)

        if self.timeoutCall is not None and self.timeoutCall.active():
            self._cancelTimeout(None)
        self.timeoutCall = reactor.callLater(
            self.timeout, self.failWithTimeoutError)
        self._deferred.addBoth(self._cancelTimeout)

    connector = None

    def failWithTimeoutError(self):
        host_timeouts[self.request_host] += 1
        self.failed(ProberTimeout(self.url, self.timeout))
        if self.connector is not None:
            self.connector.disconnect()

    def startedConnecting(self, connector):
        self.connector = connector

    def succeeded(self, status):
        if IResponse.providedBy(status):
            status = str(status.code)
        self._deferred.callback(status)

    def failed(self, reason):
        if isinstance(reason, ProberTimeout) and self._deferred.called:
            msg = (
                "Prober %s for url %s tried to fail with timeout after it has "
                "already received a response.")
            self.logger.info(msg, self, self.url)
            return
        self._deferred.errback(reason)

    def _cancelTimeout(self, result):
        if self.timeoutCall.active():
            self.timeoutCall.cancel()
        return result

    def setURL(self, url):
        self.url = url
        scheme, host, port, path = _parse(url)
        # XXX Guilherme Salgado 2006-09-19:
        # We don't actually know how to handle FTP responses, but we
        # expect to be behind a squid HTTP proxy with the patch at
        # https://bugs.squid-cache.org/show_bug.cgi?id=1758 applied. So, if
        # you encounter any problems with FTP URLs you'll probably have to nag
        # the sysadmins to fix squid for you.
        if scheme not in ('http', 'https', 'ftp'):
            raise UnknownURLScheme(url)

        if scheme and host:
            self.request_scheme = scheme
            self.request_host = host
            self.request_port = port
            self.request_path = path

        if self.request_host not in host_requests:
            host_requests[self.request_host] = 0
        if self.request_host not in host_timeouts:
            host_timeouts[self.request_host] = 0

        # If launchpad.http_proxy is set in our configuration, we want to
        # use it as the host we're going to connect to.
        proxy = config.launchpad.http_proxy
        if proxy:
            scheme, host, port, dummy = _parse(proxy)
            path = url

        self.connect_scheme = scheme
        self.connect_host = host
        self.connect_port = port
        self.connect_path = path


class RedirectAwareProberFactory(ProberFactory):

    protocol = RedirectAwareProberProtocol
    redirection_count = 0

    def redirect(self, url):
        self.timeoutCall.reset(self.timeout)

        url = six.ensure_text(url)
        scheme, host, port, orig_path = _parse(self.url)
        scheme, host, port, new_path = _parse(url)
        if (unquote(orig_path.split('/')[-1])
                != unquote(new_path.split('/')[-1])):
            # Server redirected us to a file which doesn't seem to be what we
            # requested.  It's likely to be a stupid server which redirects
            # instead of 404ing (https://launchpad.net/bugs/204460).
            self.failed(Failure(RedirectToDifferentFile(orig_path, new_path)))
            return

        try:
            if self.redirection_count >= MAX_REDIRECTS:
                raise InfiniteLoopDetected()
            self.redirection_count += 1

            logger = logging.getLogger('distributionmirror-prober')
            logger.debug('Got redirected from %s to %s' % (self.url, url))
            # XXX Guilherme Salgado 2007-04-23 bug=109223:
            # We can't assume url to be absolute here.
            self.setURL(url)
        except UnknownURLScheme:
            # Since we've got the UnknownURLScheme after a redirect, we need
            # to raise it in a form that can be ignored in the layer above.
            self.failed(UnknownURLSchemeAfterRedirect(url))
        except InfiniteLoopDetected as e:
            self.failed(e)

        else:
            self.connect()


class ProberError(Exception):
    """A generic prober error.

    This class should be used as a base for more specific prober errors.
    """


class ProberTimeout(ProberError):
    """The initialized URL did not return in time."""

    def __init__(self, url, timeout, *args):
        self.url = url
        self.timeout = timeout
        ProberError.__init__(self, *args)

    def __str__(self):
        return ("HEAD request on %s took longer than %s seconds"
                % (self.url, self.timeout))


class BadResponseCode(ProberError):

    def __init__(self, status, response=None, *args):
        ProberError.__init__(self, *args)
        self.status = status
        self.response = response

    def __str__(self):
        return "Bad response code: %s" % self.status


class InvalidHTTPSCertificate(ProberError):
    def __init__(self, host, port, *args):
        super().__init__(*args)
        self.host = host
        self.port = port

    def __str__(self):
        return "Invalid SSL certificate when trying to probe %s:%s" % (
            self.host, self.port)


class RedirectToDifferentFile(ProberError):

    def __init__(self, orig_path, new_path, *args):
        ProberError.__init__(self, *args)
        self.orig_path = orig_path
        self.new_path = new_path

    def __str__(self):
        return ("Attempt to redirect to a different file; from %s to %s"
                % (self.orig_path, self.new_path))


class InfiniteLoopDetected(ProberError):

    def __str__(self):
        return "Infinite loop detected"


class ConnectionSkipped(ProberError):

    def __str__(self):
        return ("Connection skipped because of too many timeouts on this "
                "host. It will be retried on the next probing run.")


class InvalidHTTPSCertificateSkipped(ProberError):

    def __str__(self):
        return ("Connection skipped because the server doesn't have a valid "
                "HTTPS certificate. It will be retried on the next "
                "probing run.")


class UnknownURLScheme(ProberError):

    def __init__(self, url, *args):
        ProberError.__init__(self, *args)
        self.url = url

    def __str__(self):
        return ("The mirror prober doesn't know how to check this kind of "
                "URLs: %s" % self.url)


class UnknownURLSchemeAfterRedirect(UnknownURLScheme):

    def __str__(self):
        return ("The mirror prober was redirected to: %s. It doesn't know how"
                "to check this kind of URL." % self.url)


class CallScheduler:
    """Keep track of the calls done as callback of deferred or directly,
    so we can postpone them to after the reactor is done.

    The main limitation for deferred callbacks is that we don't deal with
    errors here. You should do error handling synchronously on the methods
    scheduled.
    """
    def __init__(self, mirror, series):
        self.mirror = mirror
        self.series = series
        # A list of tuples with the format:
        # (is_a_callback, callback_result, method, args, kwargs)
        self.calls = []

    def sched(self, method, *args, **kwargs):
        self.calls.append((False, None, method, args, kwargs))

    def schedCallback(self, method, *args, **kwargs):
        def callback(result):
            self.calls.append((True, result, method, args, kwargs))
            return result
        return callback

    def run(self):
        """Runs all the delayed calls, passing forward the result from one
        callback to the next.
        """
        null = object()
        last_result = null
        for is_callback, result, method, args, kwargs in self.calls:
            if is_callback:
                # If it was scheduled as a callback, take care of previous
                # result.
                result = result if last_result is null else last_result
                last_result = method(result, *args, **kwargs)
            else:
                # If it was scheduled as a sync call, just execute the method.
                method(*args, **kwargs)


class ArchiveMirrorProberCallbacks(LoggingMixin):

    expected_failures = (
        BadResponseCode,
        ProberTimeout,
        ConnectionSkipped,
        InvalidHTTPSCertificate,
        InvalidHTTPSCertificateSkipped,
        )

    def __init__(self, mirror, series, pocket, component, url, log_file,
                 call_sched=None):
        self.mirror = mirror
        self.series = series
        self.pocket = pocket
        self.component = component
        self.url = url
        self.log_file = log_file
        self.call_sched = call_sched
        if IDistroArchSeries.providedBy(series):
            self.mirror_class_name = 'MirrorDistroArchSeries'
            self.deleteMethod = self.mirror.deleteMirrorDistroArchSeries
            self.ensureMethod = self.mirror.ensureMirrorDistroArchSeries
        elif IDistroSeries.providedBy(series):
            self.mirror_class_name = 'MirrorDistroSeries'
            self.deleteMethod = self.mirror.deleteMirrorDistroSeriesSource
            self.ensureMethod = self.mirror.ensureMirrorDistroSeriesSource
        else:
            raise AssertionError('series must provide either '
                                 'IDistroArchSeries or IDistroSeries.')

    def deleteMirrorSeries(self, failure):
        """Delete the mirror for self.series, self.pocket and self.component.

        If the failure we get from twisted is not a timeout, a bad response
        code or a connection skipped, then this failure is propagated.
        """
        self.deleteMethod(self.series, self.pocket, self.component)
        msg = ('Deleted %s of %s with url %s because: %s.\n'
               % (self.mirror_class_name,
                  self._getSeriesPocketAndComponentDescription(), self.url,
                  failure.getErrorMessage()))
        self.logMessage(msg)
        failure.trap(*self.expected_failures)

    def ensureMirrorSeries(self, http_status):
        """Make sure we have a mirror for self.series, self.pocket and
        self.component.
        """
        msg = ('Ensuring %s of %s with url %s exists in the database.\n'
               % (self.mirror_class_name,
                  self._getSeriesPocketAndComponentDescription(),
                  self.url))
        mirror = self.ensureMethod(
            self.series, self.pocket, self.component)

        self.logMessage(msg)
        return mirror

    def updateMirrorFreshness(self, arch_or_source_mirror, request_manager):
        """Update the freshness of this MirrorDistro{ArchSeries,SeriesSource}.

        This is done by issuing HTTP HEAD requests on that mirror looking for
        some packages found in our publishing records. Then, knowing what
        packages the mirror contains and when these packages were published,
        we can have an idea of when that mirror was last updated.
        """
        # The errback that's one level before this callback in the chain will
        # return None if it gets any of self.expected_failures as the error,
        # so we need to check that here.
        if arch_or_source_mirror is None:
            return

        scheme, host, port, path = _parse(self.url)
        freshness_url_map = arch_or_source_mirror.getURLsToCheckUpdateness()
        if not freshness_url_map or should_skip_host(host):
            # Either we have no publishing records for self.series,
            # self.pocket and self.component or we got too may timeouts from
            # this host and thus should skip it, so it's better to delete this
            # MirrorDistroArchSeries/MirrorDistroSeriesSource than to keep
            # it with an UNKNOWN freshness.
            self.call_sched.sched(
                self.deleteMethod, self.series, self.pocket, self.component)
            return

        deferredList = []
        # We start setting the freshness to unknown, and then we move on
        # trying to find one of the recently published packages mirrored
        # there.
        self.call_sched.sched(
            self.setMirrorFreshnessUnknown, arch_or_source_mirror)
        for freshness, url in freshness_url_map.items():
            prober = RedirectAwareProberFactory(url)
            deferred = request_manager.run(prober.request_host, prober.probe)
            deferred.addErrback(self.logError, url)
            deferred.addCallback(self.call_sched.schedCallback(
                self.setMirrorFreshness, arch_or_source_mirror,
                freshness, url))
            deferredList.append(deferred)
        return defer.DeferredList(deferredList)

    def setMirrorFreshnessUnknown(self, arch_or_source_mirror):
        arch_or_source_mirror.freshness = MirrorFreshness.UNKNOWN

    def setMirrorFreshness(
            self, http_status, arch_or_source_mirror, freshness, url):
        """Update the freshness of the given arch or source mirror.

        The freshness is changed only if the given freshness refers to a more
        recent date than the current one.
        """
        if freshness < arch_or_source_mirror.freshness:
            msg = ('Found that %s exists. Updating %s of %s freshness to '
                   '%s.\n')
            msg = msg % (
                url, self.mirror_class_name,
                self._getSeriesPocketAndComponentDescription(),
                freshness.title)
            self.logMessage(msg)
            arch_or_source_mirror.freshness = freshness

    def _getSeriesPocketAndComponentDescription(self):
        """Return a string containing the name of the series, pocket and
        component.

        This is meant to be used in the logs, to help us identify if this is a
        MirrorDistroSeriesSource or a MirrorDistroArchSeries.
        """
        if IDistroArchSeries.providedBy(self.series):
            series = self.series.distroseries
            arch = self.series.architecturetag
        else:
            series = self.series
            arch = 'source'
        return '%s %s %s %s' % (
            series.distribution.name, series.getSuite(self.pocket), arch,
            self.component.name)

    def logError(self, failure, url):
        msg = ("%s on %s of %s\n"
               % (failure.getErrorMessage(), url,
                  self._getSeriesPocketAndComponentDescription()))
        if failure.check(*self.expected_failures) is not None:
            self.logMessage(msg)
        else:
            # This is not an error we expect from an HTTP server.
            logger = logging.getLogger('distributionmirror-prober')
            logger.error(msg)
        return None


class MirrorCDImageProberCallbacks(LoggingMixin):

    expected_failures = (
        BadResponseCode,
        ConnectionSkipped,
        ProberTimeout,
        RedirectToDifferentFile,
        UnknownURLSchemeAfterRedirect,
        InvalidHTTPSCertificate,
        InvalidHTTPSCertificateSkipped,
        )

    def __init__(self, mirror, distroseries, flavour, log_file):
        self.mirror = mirror
        self.distroseries = distroseries
        self.flavour = flavour
        self.log_file = log_file

    def ensureOrDeleteMirrorCDImageSeries(self, result):
        """Check if the result of the deferredList contains only success and
        then ensure we have a MirrorCDImageSeries for self.distroseries and
        self.flavour.

        If result contains one or more failures, then we ensure that
        MirrorCDImageSeries is deleted.
        """
        for success_or_failure, response in result:
            if success_or_failure == defer.FAILURE:
                self.mirror.deleteMirrorCDImageSeries(
                    self.distroseries, self.flavour)
                if response.check(*self.expected_failures) is None:
                    msg = ("%s on mirror %s. Check its logfile for more "
                           "details.\n"
                           % (response.getErrorMessage(), self.mirror.name))
                    # This is not an error we expect from an HTTP server.
                    logger = logging.getLogger('distributionmirror-prober')
                    logger.error(msg)
                return None

        mirror = self.mirror.ensureMirrorCDImageSeries(
            self.distroseries, self.flavour)
        self.logMessage(
            "Found all ISO images for series %s and flavour %s.\n"
            % (self.distroseries.title, self.flavour))
        return mirror

    def logMissingURL(self, failure, url):
        self.logMessage(
            "Failed %s: %s\n" % (url, failure.getErrorMessage()))
        return failure

    def urlCallback(self, result, url):
        """The callback to be called for each URL."""
        if isinstance(result, Failure):
            self.logMissingURL(result, url)

    def finalResultCallback(self, result):
        """The callback to be called once all URLs have been probed."""
        return self.ensureOrDeleteMirrorCDImageSeries(result)


def _get_cdimage_file_list():
    url = config.distributionmirrorprober.cdimage_file_list_url
    # In test environments, this may be a file: URL.  Adjust it to be in a
    # form that requests can cope with (i.e. using an absolute path).
    parsed_url = urlparse(url)
    if parsed_url.scheme == 'file' and not os.path.isabs(parsed_url.path):
        assert parsed_url.path == parsed_url[2]
        parsed_url = list(parsed_url)
        parsed_url[2] = os.path.join(config.root, parsed_url[2])
    url = urlunparse(parsed_url)
    try:
        return urlfetch(
            url, headers={'Pragma': 'no-cache', 'Cache-control': 'no-cache'},
            use_proxy=True, allow_file=True)
    except requests.RequestException as e:
        raise UnableToFetchCDImageFileList(
            'Unable to fetch %s: %s' % (url, e))


def get_expected_cdimage_paths():
    """Get all paths where we can find CD image files on a cdimage mirror.

    Return a list containing, for each Ubuntu DistroSeries and flavour, a
    list of CD image file paths for that DistroSeries and flavour.

    This list is read from a file located at http://releases.ubuntu.com,
    so if something goes wrong while reading that file, an
    UnableToFetchCDImageFileList exception will be raised.
    """
    d = {}
    with _get_cdimage_file_list() as response:
        for line in response.iter_lines():
            flavour, seriesname, path, size = six.ensure_text(line).split('\t')
            paths = d.setdefault((flavour, seriesname), [])
            paths.append(path.lstrip('/'))

    ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    paths = []
    for key, value in sorted(d.items()):
        flavour, seriesname = key
        series = ubuntu.getSeries(seriesname)
        paths.append((series, flavour, value))
    return paths


def checkComplete(result, key, unchecked_keys):
    """Check if we finished probing all mirrors, and call reactor.stop()."""
    unchecked_keys.remove(key)
    if not len(unchecked_keys):
        reactor.callLater(0, reactor.stop)
    # This is added to the deferred with addBoth(), which means it'll be
    # called if something goes wrong in the end of the callback chain, and in
    # that case we shouldn't swallow the error.
    return result


def probe_archive_mirror(mirror, logfile, unchecked_keys, logger,
                         max_parallel, max_parallel_per_host):
    """Probe an archive mirror for its contents and freshness.

    First we issue a set of HTTP HEAD requests on some key files to find out
    what is mirrored there, then we check if some packages that we know the
    publishing time are available on that mirror, giving us an idea of when it
    was last synced to the main archive.
    """
    base_url = mirror.base_url
    if not base_url.endswith('/'):
        base_url += '/'
    packages_paths = mirror.getExpectedPackagesPaths()
    sources_paths = mirror.getExpectedSourcesPaths()
    all_paths = itertools.chain(packages_paths, sources_paths)
    request_manager = RequestManager(max_parallel, max_parallel_per_host)

    call_scheds = []
    for series, pocket, component, path in all_paths:
        sched = CallScheduler(mirror, series)
        call_scheds.append(sched)
        url = urljoin(base_url, path)
        callbacks = ArchiveMirrorProberCallbacks(
            mirror, series, pocket, component, url, logfile, sched)
        unchecked_keys.append(url)
        # APT has supported redirects since 0.7.21 (2009-04-14), so allow
        # them here too.
        prober = RedirectAwareProberFactory(url)

        deferred = request_manager.run(prober.request_host, prober.probe)

        # XXX pappacena 2020-11-25: This will do some database operation
        # inside reactor, which might cause problems like timeouts when
        # running HTTP requests. This should be the next optimization point:
        # run {ensure|delete}MirrorSeries and gather all mirror freshness URLs
        # synchronously here, and ask reactor to run just the HTTP requests.
        deferred.addCallbacks(
            callbacks.ensureMirrorSeries, callbacks.deleteMirrorSeries)
        deferred.addCallback(
            callbacks.updateMirrorFreshness, request_manager)
        deferred.addErrback(logger.error)

        deferred.addBoth(checkComplete, url, unchecked_keys)
    return call_scheds


def probe_cdimage_mirror(mirror, logfile, unchecked_keys, logger,
                         max_parallel, max_parallel_per_host):
    """Probe a cdimage mirror for its contents.

    This is done by checking the list of files for each flavour and series
    returned by get_expected_cdimage_paths(). If a mirror contains all
    files for a given series and flavour, then we consider that mirror is
    actually mirroring that series and flavour.
    """
    base_url = mirror.base_url
    if not base_url.endswith('/'):
        base_url += '/'

    # The list of files a mirror should contain will change over time and we
    # don't want to keep records for files a mirror doesn't need to have
    # anymore, so we delete all records before start probing. This also fixes
    # https://launchpad.net/bugs/46662
    mirror.deleteAllMirrorCDImageSeries()
    try:
        cdimage_paths = get_expected_cdimage_paths()
    except UnableToFetchCDImageFileList as e:
        logger.error(e)
        return

    call_scheds = []
    for series, flavour, paths in cdimage_paths:
        callbacks = MirrorCDImageProberCallbacks(
            mirror, series, flavour, logfile)

        mirror_key = (series, flavour)
        unchecked_keys.append(mirror_key)
        deferredList = []
        request_manager = RequestManager(max_parallel, max_parallel_per_host)
        for path in paths:
            url = urljoin(base_url, path)
            # Use a RedirectAwareProberFactory because CD mirrors are allowed
            # to redirect, and we need to cope with that.
            sched = CallScheduler(mirror, series)
            call_scheds.append(sched)
            prober = RedirectAwareProberFactory(url)
            deferred = request_manager.run(prober.request_host, prober.probe)
            deferred.addErrback(
                sched.schedCallback(callbacks.urlCallback, url))
            deferredList.append(deferred)

        sched = CallScheduler(mirror, series)
        call_scheds.append(sched)
        deferredList = defer.DeferredList(deferredList, consumeErrors=True)
        deferredList.addCallback(
            sched.schedCallback(callbacks.finalResultCallback))
        deferredList.addCallback(checkComplete, mirror_key, unchecked_keys)
    return call_scheds


def should_skip_host(host):
    """Return True if the requests/timeouts ratio on this host is too low."""
    requests = host_requests[host]
    timeouts = host_timeouts[host]
    if timeouts == 0 or requests < MIN_REQUESTS_TO_CONSIDER_RATIO:
        return False
    else:
        ratio = float(requests) / timeouts
        return ratio < MIN_REQUEST_TIMEOUT_RATIO


def _parse(url, defaultPort=None):
    """Parse the given URL returning the scheme, host, port and path."""
    scheme, host, path, dummy, dummy, dummy = urlparse(url)
    if ':' in host:
        host, port = host.split(':')
        assert port.isdigit()
        port = int(port)
    elif defaultPort is None:
        port = 443 if scheme == 'https' else 80
    else:
        port = defaultPort
    return scheme, host, port, path


class DistroMirrorProber:
    """Main entry point for the distribution mirror prober."""

    def __init__(self, txn, logger):
        self.txn = txn
        self.logger = logger

    def _sanity_check_mirror(self, mirror):
        """Check that the given mirror is official and has an http_base_url.
        """
        assert mirror.isOfficial(), (
            'Non-official mirrors should not be probed')
        if mirror.base_url is None:
            self.logger.warning(
                "Mirror '%s' of distribution '%s' doesn't have a base URL; "
                "we can't probe it." % (
                    mirror.name, mirror.distribution.name))
            return False
        return True

    def _create_probe_record(self, mirror, logfile):
        """Create a probe record for the given mirror with the given logfile.
        """
        logfile.seek(0)
        filename = '%s-probe-logfile.txt' % mirror.name
        log_data = logfile.getvalue().encode('UTF-8')
        log_file = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(log_data),
            file=io.BytesIO(log_data), contentType='text/plain')
        mirror.newProbeRecord(log_file)

    def probe(self, content_type, no_remote_hosts, ignore_last_probe,
              max_mirrors, notify_owner, max_parallel=100,
              max_parallel_per_host=2):
        """Probe distribution mirrors.

        You should control carefully the parallelism here. Increasing too
        much the number of max_parallel_per_host could make the mirrors take
        too much to answer or deny our requests.

        If we increase too much the max_parallel, we might experience timeouts
        because of our production proxy or internet bandwidth.

        :param content_type: The type of mirrored content, as a
            `MirrorContent`.
        :param no_remote_hosts: If True, restrict access to localhost.
        :param ignore_last_probe: If True, ignore the results of the last
            probe and probe again anyway.
        :param max_mirrors: The maximum number of mirrors to probe. If None,
            no maximum.
        :param notify_owner: Send failure notification to the owners of the
            mirrors.
        :param max_parallel: Maximum number of requests happening
            simultaneously.
        :param max_parallel_per_host: Maximum number of requests to the same
            host happening simultaneously.
        """
        if content_type == MirrorContent.ARCHIVE:
            probe_function = probe_archive_mirror
        elif content_type == MirrorContent.RELEASE:
            probe_function = probe_cdimage_mirror
        else:
            raise ValueError(
                "Unrecognized content_type: %s" % (content_type,))

        self.txn.begin()

        # To me this seems better than passing the no_remote_hosts value
        # through a lot of method/function calls, until it reaches the probe()
        # method. (salgado)
        if no_remote_hosts:
            localhost_only_conf = """
                [distributionmirrorprober]
                localhost_only: True
                """
            config.push('localhost_only_conf', localhost_only_conf)

        self.logger.info('Probing %s Mirrors' % content_type.title)

        mirror_set = getUtility(IDistributionMirrorSet)
        results = mirror_set.getMirrorsToProbe(
            content_type, ignore_last_probe=ignore_last_probe,
            limit=max_mirrors)
        mirror_ids = [mirror.id for mirror in results]
        unchecked_keys = []
        logfiles = {}
        probed_mirrors = []

        all_scheduled_calls = []
        for mirror_id in mirror_ids:
            mirror = mirror_set[mirror_id]
            if not self._sanity_check_mirror(mirror):
                continue

            # XXX: salgado 2006-05-26:
            # Some people registered mirrors on distros other than Ubuntu back
            # in the old times, so now we need to do this small hack here.
            if not mirror.distribution.supports_mirrors:
                self.logger.debug(
                    "Mirror '%s' of distribution '%s' can't be probed --we "
                    "only probe distros that support mirrors."
                    % (mirror.name, mirror.distribution.name))
                continue

            probed_mirrors.append(mirror)
            logfile = six.StringIO()
            logfiles[mirror_id] = logfile
            prob_scheduled_calls = probe_function(
                mirror, logfile, unchecked_keys, self.logger,
                max_parallel, max_parallel_per_host)
            all_scheduled_calls += prob_scheduled_calls

        if probed_mirrors:
            reactor.run()
            self.logger.info('Probed %d mirrors.' % len(probed_mirrors))
            self.logger.info(
                'Starting to update mirrors statuses outside reactor now.')
            for sched_calls in all_scheduled_calls:
                sched_calls.run()
        else:
            self.logger.info('No mirrors to probe.')

        disabled_mirrors = []
        reenabled_mirrors = []
        # Now that we finished probing all mirrors, we check if any of these
        # mirrors appear to have no content mirrored, and, if so, mark them as
        # disabled and notify their owners.
        expected_iso_images_count = len(get_expected_cdimage_paths())
        for mirror in probed_mirrors:
            log = logfiles[mirror.id]
            self._create_probe_record(mirror, log)
            if mirror.shouldDisable(expected_iso_images_count):
                if mirror.enabled:
                    log.seek(0)
                    mirror.disable(notify_owner, log.getvalue())
                    disabled_mirrors.append(canonical_url(mirror))
            else:
                # Ensure the mirror is enabled, so that it shows up on public
                # mirror listings.
                if not mirror.enabled:
                    mirror.enabled = True
                    reenabled_mirrors.append(canonical_url(mirror))

        if disabled_mirrors:
            self.logger.info(
                'Disabling %s mirror(s): %s'
                % (len(disabled_mirrors), ", ".join(disabled_mirrors)))
        if reenabled_mirrors:
            self.logger.info(
                'Re-enabling %s mirror(s): %s'
                % (len(reenabled_mirrors), ", ".join(reenabled_mirrors)))
        # XXX: salgado 2007-04-03:
        # This should be done in LaunchpadScript.lock_and_run() when
        # the isolation used is ISOLATION_LEVEL_AUTOCOMMIT. Also note
        # that replacing this with a flush_database_updates() doesn't
        # have the same effect, it seems.
        self.txn.commit()

        self.logger.info('Done.')
