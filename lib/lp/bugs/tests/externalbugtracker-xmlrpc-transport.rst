XMLRPC requests transport
-------------------------

When using XMLRPC for connecting to external bug trackers, we need to
use a special transport, which processes http cookies correctly, and
which can connect through an http proxy server.

    >>> from lp.bugs.externalbugtracker.xmlrpc import RequestsTransport

RequestsTransport accepts a CookieJar as an optional parameter upon creation.
This allows us to share a CookieJar - and therefore the cookie it contains -
between different transports or URL openers.

    >>> from requests.cookies import RequestsCookieJar
    >>> jar = RequestsCookieJar()
    >>> transport = RequestsTransport("http://example.com", jar)
    >>> transport.cookie_jar == jar
    True

We define a test response callback that returns the request-url and any
request parameters as an XMLRPC parameter, and sets a cookie from the
server, 'foo=bar'.

    >>> import responses
    >>> import xmlrpc.client

    >>> def test_callback(request):
    ...     params = xmlrpc.client.loads(request.body)[0]
    ...     return (
    ...         200,
    ...         {"Set-Cookie": "foo=bar"},
    ...         xmlrpc.client.dumps(
    ...             ([request.url] + list(params),), methodresponse=True
    ...         ),
    ...     )
    ...

Before sending the request, the transport's cookie jar is empty.

    >>> def print_cookie_jar(jar):
    ...     for name, value in sorted(jar.items()):
    ...         print("%s=%s" % (name, value))
    ...

    >>> print_cookie_jar(transport.cookie_jar)

    >>> request_body = """<?xml version="1.0"?>
    ... <methodCall>
    ...   <methodName>examples.testMethod</methodName>
    ...   <params>
    ...     <param>
    ...       <value>
    ...         <int>42</int>
    ...       </value>
    ...     </param>
    ...   </params>
    ... </methodCall>
    ... """
    >>> with responses.RequestsMock() as requests_mock:
    ...     requests_mock.add_callback(
    ...         "POST", "http://www.example.com/xmlrpc", test_callback
    ...     )
    ...     transport.request("www.example.com", "xmlrpc", request_body)
    ...
    (['http://www.example.com/xmlrpc', 42],)

We received the url as the single XMLRPC result, and the cookie jar now
contains the 'foo=bar' cookie sent by the server.

    >>> print_cookie_jar(transport.cookie_jar)
    foo=bar

In addition to cookies sent by the server, we can set cookies locally.

    >>> transport.setCookie("ding=dong")
    >>> print_cookie_jar(transport.cookie_jar)
    ding=dong
    foo=bar

If an error occurs trying to make the request, an
``xmlrpc.client.ProtocolError`` is raised.

    >>> request_body = """<?xml version="1.0"?>
    ... <methodCall>
    ...   <methodName>examples.testError</methodName>
    ...   <params>
    ...     <param>
    ...       <value>
    ...         <int>42</int>
    ...       </value>
    ...     </param>
    ...   </params>
    ... </methodCall>
    ... """
    >>> with responses.RequestsMock() as requests_mock:
    ...     requests_mock.add(
    ...         "POST", "http://www.example.com/xmlrpc", status=500
    ...     )
    ...     transport.request("www.example.com", "xmlrpc", request_body)
    ...
    Traceback (most recent call last):
    ...
    xmlrpc.client.ProtocolError: <ProtocolError for
    http://www.example.com/xmlrpc: 500 Internal Server Error>

If the transport encounters a redirect response it will make its request
to the location indicated in that response rather than the original
location.

    >>> request_body = """<?xml version="1.0"?>
    ... <methodCall>
    ...   <methodName>examples.whatever</methodName>
    ...   <params>
    ...     <param>
    ...       <value>
    ...         <int>42</int>
    ...       </value>
    ...     </param>
    ...   </params>
    ... </methodCall>
    ... """
    >>> with responses.RequestsMock() as requests_mock:
    ...     target_url = "http://www.example.com/xmlrpc/redirected"
    ...     requests_mock.add(
    ...         "POST",
    ...         "http://www.example.com/xmlrpc",
    ...         status=302,
    ...         headers={"Location": target_url},
    ...     )
    ...     requests_mock.add_callback("POST", target_url, test_callback)
    ...     transport.request("www.example.com", "xmlrpc", request_body)
    ...
    (['http://www.example.com/xmlrpc/redirected', 42],)
