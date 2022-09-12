IPublicCodehostingAPI
=====================

    >>> import xmlrpc.client
    >>> from lp.testing.xmlrpc import XMLRPCTestTransport


resolve_lp_path
---------------

The resolve_lp_path API allows clients to retrieve a list of URLs for a
branch by specifying the path component of an lp: URL.

Use of this method by any client other than the 'Launchpad' plugin of
Bazaar is strictly unsupported.

This API is deprecated, and will eventually be replaced with an
equivalent method in the new Launchpad API infrastructure.

    >>> public_codehosting_api = xmlrpc.client.ServerProxy(
    ...     "http://xmlrpc.launchpad.test/bazaar/",
    ...     transport=XMLRPCTestTransport(),
    ... )


On success, resolve_lp_path returns a dict containing a single key,
'urls':

    >>> results = public_codehosting_api.resolve_lp_path(
    ...     "~vcs-imports/evolution/main"
    ... )
    >>> print(list(results))
    ['urls']


The value of a key is a list of URLs from which the branch can be
accessed:

    >>> results = public_codehosting_api.resolve_lp_path(
    ...     "~vcs-imports/evolution/main"
    ... )
    >>> for url in results["urls"]:
    ...     print(url)
    ...
    bzr+ssh://bazaar.launchpad.test/~vcs-imports/evolution/main
    http://bazaar.launchpad.test/~vcs-imports/evolution/main

The URLs that are likely to be faster or provide write access appear
earlier in the list.

For more tests see `lp.code.xmlrpc.tests.test_branch.py`.
