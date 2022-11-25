========
Builders
========

The webservice exposes a top-level collection called "builders" which
contains all the registered builders in the Launchpad build farm.

    >>> nopriv_launchpad = launchpadlib_for(
    ...     "builders test", "no-priv", version="devel"
    ... )
    >>> builders = nopriv_launchpad.builders

Iterating over the collection is possible:

    >>> for builder in builders:
    ...     print(builder)
    ...
    http://api.launchpad.test/devel/builders/bob
    http://api.launchpad.test/devel/builders/frog

An individual builder can be retrieved by name by using the getByName()
operation on "builders":

    >>> bob = builders.getByName(name="bob")

Each builder has a number of properties exposed:

    >>> for attribute in bob.lp_attributes:
    ...     print(attribute)
    ...
    self_link
    ...
    active
    builderok
    clean_status
    date_clean_status_changed
    failnotes
    failure_count
    manual
    name
    open_resources
    processors
    restricted_resources
    title
    url
    version
    virtualized
    vm_host
    vm_reset_protocol


Changing builder properties
===========================

If an authorized person (usually a member of the buildd-admins team)
wishes to amend some property of a builder, the usual webservice 'lp_save'
operation is used.

Our "bob" builder was retrieved using the no-priv user, and no-priv does not
have permission to save changes:

    >>> print(bob.active)
    True
    >>> bob.active = False
    >>> bob.lp_save()
    Traceback (most recent call last):
    ...
    lazr.restfulclient.errors.Unauthorized: ...

'cprov', who is a buildd-admin, is able to change the data:

    >>> cprov_launchpad = launchpadlib_for(
    ...     "builders test", "cprov", version="devel"
    ... )
    >>> bob = cprov_launchpad.builders.getByName(name="bob")
    >>> bob.active = False
    >>> bob.lp_save()

