Translation focus
=================

The translation focus of a project is the series chosen as the preferred
one to be translated. It's optional. When not set, Launchpad suggests
the development focus as the preferred series to translate, which is
outside the scope of this test.

    >>> evolution = webservice.get("/evolution").jsonBody()
    >>> print(evolution["development_focus_link"])
    http://.../evolution/trunk
    >>> print(evolution["translation_focus_link"])
    None

It's possible to set the translation focus through the API
if you're an admin. The translation focus should be a project series.

    >>> import json
    >>> print(
    ...     webservice.patch(
    ...         evolution["self_link"],
    ...         "application/json",
    ...         json.dumps(
    ...             {
    ...                 "translation_focus_link": evolution[
    ...                     "development_focus_link"
    ...                 ]
    ...             }
    ...         ),
    ...     )
    ... )
    HTTP/1.1 209 Content Returned
    ...

    >>> print(
    ...     webservice.get("/evolution").jsonBody()["translation_focus_link"]
    ... )
    http://.../evolution/trunk

Unprivileged users cannot set the translation focus.

    >>> print(
    ...     user_webservice.patch(
    ...         evolution["self_link"],
    ...         "application/json",
    ...         json.dumps({"translation_focus_link": None}),
    ...     )
    ... )
    HTTP... 401 Unauthorized
    ...
