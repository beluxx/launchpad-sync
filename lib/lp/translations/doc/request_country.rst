
Adapting Requests to Countries
------------------------------

Adapting a request to a country allows you to see where the request came from.

Here's a dummy request. Zope adds the REMOTE_ADDR CGI environment variable
for us. Upstream proxy servers (and tinkering users!) may also add
X-Forwarded-For: headers. The X-Forwarded-For: header takes precidence
if it is set.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> request = LaunchpadTestRequest(environ={
    ...     'HTTP_X_FORWARDED_FOR': '127.0.0.1,82.211.81.179',
    ...     'REMOTE_ADDR': '127.0.0.1',
    ...     })

Here's us converting it to a country.

    >>> from lp.services.worlddata.interfaces.country import ICountry
    >>> country = ICountry(request)
    >>> print(country.name)
    United Kingdom

Sometimes we don't know where the request came from.

    >>> request = LaunchpadTestRequest(
    ...     environ={'REMOTE_ADDR': '255.255.255.255'})
    >>> ICountry(request)
    Traceback (most recent call last):
    ...
    TypeError: ('Could not adapt', ...
