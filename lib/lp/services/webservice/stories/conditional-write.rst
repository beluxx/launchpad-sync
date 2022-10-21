Conditional writes may work even when the ETags aren't identical
================================================================

This code is tested in lazr.restful, but since it's proven a
longstanding problem in Launchpad, we're giving it a
Launchpad-specific test as well. This will give us a place to start if
the problem crops up again.

Here's a bug: it has an ETag and values for fields like
'date_last_message'.

    >>> url = "/bugs/1"
    >>> bug = webservice.get(url).jsonBody()
    >>> old_etag = bug["http_etag"]
    >>> old_date_last_message = bug["date_last_message"]

When we add a message to a bug, 'date_last_message' is changed as a
side effect.

    >>> print(
    ...     webservice.named_post(
    ...         url, "newMessage", subject="subject", content="content"
    ...     )
    ... )
    HTTP/1.1 201 Created
    ...

    >>> new_bug = webservice.get(url).jsonBody()
    >>> new_date_last_message = new_bug["date_last_message"]
    >>> old_date_last_message == new_date_last_message
    False

Because 'date_last_message' changed, the bug resource's ETag also
changed:

    >>> new_etag = new_bug["http_etag"]
    >>> old_etag == new_etag
    False

A conditional GET request using the old ETag will fail, and the client
will hear about the new value for 'date_last_message'.

    >>> print(webservice.get(url, headers={"If-None-Match": old_etag}))
    HTTP/1.1 200 Ok
    ...

But what if we want to PATCH the bug object after adding a message?
Logically speaking, the PATCH should go through. 'date_last_message' has
changed, but that's not a field that a client can modify
directly. There's no chance that my PATCH will modify
'date_last_message' in a way that conflicts with someone else's
PATCH. But in general, conditional write requests only succeed if the
client's value for If-Match exactly matches the server-side ETag.

lazr.restful resolves this by splitting the ETag into two parts. The
first part changes only on changes to fields that clients cannot
modify directly, like 'date_last_message':

    >>> old_read, old_write = old_etag.rsplit("-", 1)
    >>> new_read, new_write = new_etag.rsplit("-", 1)
    >>> old_read == new_read
    False

The second part changes only on changes to fields that a client could
modify directly.

    >>> old_write == new_write
    True

So long as the second part of the submitted ETag matches, a
conditional write will succeed.

    >>> import json
    >>> data = json.dumps({"title": "New title"})
    >>> headers = {"If-Match": old_etag}
    >>> print(
    ...     webservice.patch(url, "application/json", data, headers=headers)
    ... )
    HTTP/1.1 209 Content Returned
    ...

Of course, now the resource has been modified by a client, and the
ETag has changed.

    >>> newer_etag = webservice.get(url).jsonBody()["http_etag"]
    >>> newer_read, newer_write = newer_etag.rsplit("-", 1)

Both portions of the ETag has changed: the write portion because we
just changed 'description', and the read portion because
'date_last_updated' changed as a side effect.

    >>> new_read == newer_read
    False
    >>> new_write == newer_write
    False

A conditional write will fail when the write portion of the submitted
ETag doesn't match, even if the read portion matches.

    >>> headers = {"If-Match": new_etag}
    >>> print(
    ...     webservice.patch(url, "application/json", data, headers=headers)
    ... )
    HTTP/1.1 412 Precondition Failed
    ...

When two clients attempt overlapping modifications of the same
resource, the later one still gets a 412 error. If an unwritable field
changes, a conditional read will fail, but a conditional write will
succeed, even though the ETags don't match exactly.


It's okay if mod_compress modifies outgoing ETags
=================================================

Here's another way non-identical ETags may be treated as the
same. Apache's mod_compress modifies outgoing ETags when it compresses
the representations. Launchpad's web service will treat an ETag
modified by mod_compress as though it were the original ETag.

    >>> etag = webservice.get(url).jsonBody()["http_etag"]

    >>> headers = {"If-None-Match": etag}
    >>> print(webservice.get(url, headers=headers))
    HTTP/1.1 304 Not Modified
    ...

Some versions of mod_compress turn '"foo"' into '"foo"-gzip', and some
versions turn it into '"foo-gzip"'. We treat all three forms the same.

    >>> headers = {"If-None-Match": etag + "-gzip"}
    >>> print(webservice.get(url, headers=headers))
    HTTP/1.1 304 Not Modified
    ...

    >>> headers = {"If-None-Match": etag[:-1] + "-gzip" + etag[-1]}
    >>> print(webservice.get(url, headers=headers))
    HTTP/1.1 304 Not Modified
    ...

Any other modification to the ETag is treated as a distinct ETag.

    >>> headers = {"If-None-Match": etag + "-not-gzip"}
    >>> print(webservice.get(url, headers=headers))
    HTTP/1.1 200 Ok
    ...
