****************************
Differences between versions
****************************

total_size_link
===============

In the 'devel' version of the web service, named operations that
return collections will return a 'total_size_link' pointing to the
total size of the collection.

    >>> def get_collection(version, start=0, size=2):
    ...     collection = webservice.get(
    ...         (
    ...             "/people?ws.op=find&text=s&ws.start=%s&ws.size=%s"
    ...             % (start, size)
    ...         ),
    ...         api_version=version,
    ...     )
    ...     return collection.jsonBody()
    ...

    >>> collection = get_collection("devel")
    >>> for key in sorted(collection.keys()):
    ...     print(key)
    ...
    entries
    next_collection_link
    start
    total_size_link
    >>> print(webservice.get(collection["total_size_link"]).jsonBody())
    9

In previous versions, the same named operations will return a
'total_size' containing the actual size of the collection.

    >>> collection = get_collection("1.0")
    >>> for key in sorted(collection.keys()):
    ...     print(key)
    ...
    entries
    next_collection_link
    start
    total_size
    >>> print(collection["total_size"])
    9

Mutator operations
==================

In the 'beta' version of the web service, mutator methods like
IBugTask.transitionToStatus are published as named operations. In
subsequent versions, those named operations are not published.

    >>> from operator import itemgetter

    >>> def get_bugtask_path(version):
    ...     bug_one = webservice.get(
    ...         "/bugs/1", api_version=version
    ...     ).jsonBody()
    ...     bug_one_bugtasks_url = bug_one["bug_tasks_collection_link"]
    ...     bug_one_bugtasks = sorted(
    ...         webservice.get(bug_one_bugtasks_url).jsonBody()["entries"],
    ...         key=itemgetter("self_link"),
    ...     )
    ...     bugtask_path = bug_one_bugtasks[0]["self_link"]
    ...     return bugtask_path
    ...

Here's the 'beta' version, where the named operation works.

    >>> url = get_bugtask_path("beta")
    >>> print(
    ...     webservice.named_post(
    ...         url,
    ...         "transitionToImportance",
    ...         importance="Low",
    ...         api_version="beta",
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...

Now let's try the same thing in the '1.0' version, where it fails.

    >>> url = get_bugtask_path("1.0")
    >>> print(
    ...     webservice.named_post(
    ...         url,
    ...         "transitionToImportance",
    ...         importance="Low",
    ...         api_version="devel",
    ...     )
    ... )
    HTTP/1.1 405 Method Not Allowed
    ...
