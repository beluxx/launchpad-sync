The location of a person is readable through the Web Service API, and can
be set that way too, but it has been deprecated as we no longer have that
information in our database, so the latitude/longitude will always be None.
The time_zone attribute has not been deprecated, though.

We start with the case where there is no information about the user's
location, at all.

    >>> jdub = webservice.get("/~jdub").jsonBody()
    >>> print(jdub['time_zone'])
    UTC
    >>> print(jdub['latitude'])
    None
    >>> print(jdub['longitude'])
    None

It is also possible to set the location, but as you can see the
latitude/longitude read via the Web API will still be None.

    >>> print(webservice.get("/~jdub").jsonBody()['time_zone'])
    UTC
    >>> print(webservice.named_post(
    ...     '/~jdub', 'setLocation', {},
    ...     latitude='-34.6', longitude='157.0',
    ...     time_zone=u'Australia/Sydney'))
    HTTP/1.1 200 Ok
    ...
    >>> print(webservice.get("/~jdub").jsonBody()['time_zone'])
    Australia/Sydney
    >>> print(jdub['latitude'])
    None
    >>> print(jdub['longitude'])
    None
