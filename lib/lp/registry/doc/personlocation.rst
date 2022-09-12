Locations for People and Teams
==============================

We no longer allow people to set their geographical locations, but their time
zone (which they can set) is stored together with their latitude/longitude (in
PersonLocation). Until we move the time zone back to the Person table
(bug=933699), we'll maintain the setLocation() API on IPerson.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> personset = getUtility(IPersonSet)

    >>> marilize = personset.getByName("marilize")
    >>> print(marilize.time_zone)
    Africa/Maseru
    >>> print(marilize.latitude)
    None
    >>> print(marilize.longitude)
    None

setLocation() will always set the time zone to the given value and both
latitude and longitude to None, regardless of what was passed in.

    >>> cprov = personset.getByName("cprov")
    >>> ignored = login_person(cprov)
    >>> cprov.setLocation(-43.2, -61.93, "America/Sao_Paulo", cprov)
    >>> print(cprov.time_zone)
    America/Sao_Paulo
    >>> print(cprov.latitude)
    None
    >>> print(cprov.longitude)
    None

We cannot store a location for a team, though.

    >>> jdub = personset.getByName("jdub")
    >>> guadamen = personset.getByName("guadamen")
    >>> guadamen.setLocation(34.5, 23.1, "Africa/Maseru", jdub)
    Traceback (most recent call last):
    ...
    AssertionError:...
