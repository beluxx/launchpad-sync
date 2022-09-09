Launchpad field validators
==========================

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from zope.component import getUtility
    >>> from lp.services.webapp.interfaces import IOpenLaunchBag
    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> no_priv = getUtility(IPersonSet).getByEmail("no-priv@canonical.com")
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> firefox = removeSecurityProxy(firefox)
    >>> firefox.bug_supervisor = no_priv

can_be_nominated_for_series
---------------------------

This validator is used to check if the bug in the launchbag can be
nominated for the given series.

    >>> from lp.app.validators.validation import can_be_nominated_for_series

If we create a new bug, all the target's series can be nominated.

    >>> login("no-priv@canonical.com")
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> bug = firefox.createBug(
    ...     CreateBugParams(no_priv, "New Bug", comment="New Bug.")
    ... )
    >>> getUtility(IOpenLaunchBag).add(bug)

    >>> can_be_nominated_for_series(firefox.series)
    True

If we nominate the bug for one of the series, the validation will
fail for that specific series.

    >>> nomination = bug.addNomination(no_priv, firefox.series[0])
    >>> can_be_nominated_for_series(firefox.series)
    Traceback (most recent call last):
    ...
    lp.app.validators.LaunchpadValidationError: ...

    >>> can_be_nominated_for_series([firefox.series[0]])
    Traceback (most recent call last):
    ...
    lp.app.validators.LaunchpadValidationError: ...

It will pass for the rest of the series, though.

    >>> can_be_nominated_for_series(firefox.series[1:])
    True

Of course, if we accept the nomination, the validation will still
fail:

    >>> login("foo.bar@canonical.com")
    >>> foo_bar = getUtility(IPersonSet).getByEmail("foo.bar@canonical.com")
    >>> nomination.approve(foo_bar)
    >>> can_be_nominated_for_series([firefox.series[0]])
    Traceback (most recent call last):
    ...
    lp.app.validators.LaunchpadValidationError: ...

The validation message will contain all the series that can't be
nominated.

    >>> trunk_nomination = bug.addNomination(no_priv, firefox.series[1])
    >>> can_be_nominated_for_series(firefox.series)
    Traceback (most recent call last):
    ...
    lp.app.validators.LaunchpadValidationError:
    This bug has already been nominated for these series: 1.0, Trunk

Declined nominations can be re-nominated.

    >>> trunk_nomination.decline(foo_bar)
    >>> can_be_nominated_for_series([firefox.series[1]])
    True

PersonNameField
---------------

The PersonNameField class, which is only used for extra validation on a
person's/team's name.

All persons have a unique name in launchpad, so to allow them to change
their names, we must make sure that name is not already in use by someone
else.

    >>> login("no-priv@canonical.com")
    >>> lifeless = getUtility(IPersonSet).getByName("lifeless")
    >>> from lp.registry.interfaces.person import PersonNameField
    >>> field = PersonNameField(
    ...     __name__="name",
    ...     title="Unique name",
    ...     description="",
    ...     readonly=False,
    ...     required=True,
    ... )
    >>> field = field.bind(lifeless)
    >>> field.context == lifeless
    True

You can always use your own name.

    >>> field.validate(lifeless.name)

Or a name that is not already in use.

    >>> field.validate("namenotinuse")

But you can't use Mark's name, of course. ;)

    >>> field.validate("mark")
    Traceback (most recent call last):
      ...
    lp.app.validators.LaunchpadValidationError:
    ...mark is already in use by another person or team...
