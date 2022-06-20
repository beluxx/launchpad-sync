DistroSeries translations view classes
======================================

Let's use ubuntu/hoary for these tests.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.series import SeriesStatus
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> hoary = ubuntu.getSeries('hoary')

We set the Hoary status to current, so we get appropriate explanation
message.

    >>> login('foo.bar@canonical.com')
    >>> hoary.status = SeriesStatus.CURRENT


Hiding translations
-------------------

Each distroseries has a switch that allows administrators to either
reveal its translations to the public or hide them from the public.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.app.errors import TranslationUnavailable
    >>> from lp.translations.browser.distroseries import (
    ...     DistroSeriesView)
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.teammembership import (
    ...     ITeamMembershipSet, TeamMembershipStatus)

    >>> def check_translations_access(distroseries):
    ...     """Return any objections to current user accessing
    ...     `distroseries` translations.'
    ...     """
    ...     request = LaunchpadTestRequest()
    ...     view = DistroSeriesView(distroseries, request)
    ...     view.initialize()
    ...
    ...     try:
    ...         view.checkTranslationsViewable()
    ...     except TranslationUnavailable as message:
    ...         return str(message)
    ...     return None

    >>> def check_effect_of_hiding(distroseries):
    ...     """Describe how hiding translations for `distroseries`
    ...     affects current user's access to them.
    ...     """
    ...     original_hide_flag = distroseries.hide_all_translations
    ...     distroseries = removeSecurityProxy(distroseries)
    ...
    ...     distroseries.hide_all_translations = False
    ...     objection = check_translations_access(distroseries)
    ...     if objection is None:
    ...         print("User can access revealed translations.")
    ...     else:
    ...         print("No access to revealed translations!", objection)
    ...
    ...     distroseries.hide_all_translations = True
    ...     objection = check_translations_access(distroseries)
    ...     if objection is None:
    ...         print("User can access hidden translations.")
    ...     else:
    ...         print("User can not access hidden translations:", objection)
    ...
    ...     distroseries.hide_all_translations = original_hide_flag

An administrator will be able to access the translations no matter what
happens.

    >>> login('foo.bar@canonical.com')
    >>> check_effect_of_hiding(hoary)
    User can access revealed translations.
    User can access hidden translations.

A Translations admin ("translations expert") can also still access the
translations even when they're hidden.

    >>> expert = factory.makePerson('expert@example.com')
    >>> expert_team = getUtility(ILaunchpadCelebrities).rosetta_experts
    >>> membership = getUtility(ITeamMembershipSet).new(
    ...     expert, expert_team, TeamMembershipStatus.APPROVED,
    ...     expert_team)
    >>> ignored = login_person(expert)
    >>> check_effect_of_hiding(hoary)
    User can access revealed translations.
    User can access hidden translations.

A regular user can no longer see the translations once they're hidden.

    >>> login('no-priv@canonical.com')
    >>> check_effect_of_hiding(hoary)
    User can access revealed translations.
    User can not access hidden translations: Translations for this
    release series are not currently available.  Please come back soon.

The same goes for anonymous users.
Exactly what message is displayed depends on the series' status.

    >>> login('foo.bar@canonical.com')
    >>> hoary.status = SeriesStatus.EXPERIMENTAL
    >>> login(ANONYMOUS)
    >>> check_effect_of_hiding(hoary)
    User can access revealed translations.
    User can not access hidden translations:
    Translations for this release series are not available yet.

    >>> login('foo.bar@canonical.com')
    >>> hoary.status = SeriesStatus.DEVELOPMENT
    >>> login(ANONYMOUS)
    >>> check_effect_of_hiding(hoary)
    User can access revealed translations.
    User can not access hidden translations:
    Translations for this release series are not available yet.

    >>> login('foo.bar@canonical.com')
    >>> hoary.status = SeriesStatus.FROZEN
    >>> login(ANONYMOUS)
    >>> check_effect_of_hiding(hoary)
    User can access revealed translations.
    User can not access hidden translations:
    Translations for this release series are not currently available.
    Please come back soon.

    >>> login('foo.bar@canonical.com')
    >>> hoary.status = SeriesStatus.CURRENT
    >>> login(ANONYMOUS)
    >>> check_effect_of_hiding(hoary)
    User can access revealed translations.
    User can not access hidden translations:
    Translations for this release series are not currently available.
    Please come back soon.

    >>> login('foo.bar@canonical.com')
    >>> hoary.status = SeriesStatus.SUPPORTED
    >>> login(ANONYMOUS)
    >>> check_effect_of_hiding(hoary)
    User can access revealed translations.
    User can not access hidden translations:
    Translations for this release series are not currently available.
    Please come back soon.

    >>> login('foo.bar@canonical.com')
    >>> hoary.status = SeriesStatus.OBSOLETE
    >>> login(ANONYMOUS)
    >>> check_effect_of_hiding(hoary)
    User can access revealed translations.
    User can not access hidden translations:
    This release series is obsolete.  Its translations are no longer
    available.

    >>> login('foo.bar@canonical.com')
    >>> hoary.status = SeriesStatus.FUTURE
    >>> login(ANONYMOUS)
    >>> check_effect_of_hiding(hoary)
    User can access revealed translations.
    User can not access hidden translations:
    Translations for this release series are not available yet.
