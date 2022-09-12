Security
========

These tests illustrate how the security model works with the
Launchpad data model objects.


Visibility
----------

A user without permission to see items in a collection will, of
course, not see those items. The 'salgado' user can see all bugs in the
Jokosher project.

    >>> search = "/jokosher?ws.op=searchTasks"
    >>> salgado_output = webservice.get(search).jsonBody()
    >>> salgado_output["total_size"]
    3
    >>> len(salgado_output["entries"])
    3

But the 'no-priv' user can't see bug number 14, which is private.

    >>> print(user_webservice.get("/bugs/14"))
    HTTP/1.1 404 Not Found
    ...

    >>> nopriv_output = user_webservice.get(search).jsonBody()
    >>> nopriv_output["total_size"]
    2
    >>> len(nopriv_output["entries"])
    2

Things are a little different for a user who has permission to see
private data, but is using an OAuth key that restricts the client to
operating on public data.

    >>> print(public_webservice.get("/bugs/14"))
    HTTP/1.1 404 Not Found
    ...

    >>> public_output = public_webservice.get(search).jsonBody()
    >>> public_output["total_size"]
    3
    >>> len(public_output["entries"])
    2

Although this behaviour is inconsistent, it doesn't leak any private
information and implementing it consistently would be very difficult,
so it's good enough. What happened here is that the web service
request was made by a user who can see all 15 bugs, but the user used
an OAuth token that only allows access to public data. The actual bugs
are filtered against the OAuth token at a fairly high level, but the
number of visible bugs comes from database-level code that only
respects the user who made the request. The user can see 15 bugs, but
their token can only see the 14 public bugs.

