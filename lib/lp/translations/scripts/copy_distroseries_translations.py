# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Copy `DistroSeries` translations from its parent series."""

__all__ = ["copy_distroseries_translations"]

from zope.component import getUtility

from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.database import bulk
from lp.soyuz.interfaces.publishing import active_publishing_status
from lp.soyuz.model.publishing import SourcePackagePublishingHistory
from lp.translations.model.distroseries_translations_copy import (
    copy_active_translations,
)


class SeriesTranslationFlagsModified(Warning):
    """`DistroSeries`' translation flags were modified while we were working.

    The flags `DistroSeries.hide_all_translations` and
    `DistroSeries.defer_translation_imports` flags were set before
    `update_translations` started updating the `DistroSeries`' translations,
    but someone else modified their state before it completed.
    """


class SeriesStateKeeper:
    """Prepare `DistroSeries` state for copying, and later restore it.

    This class is built to act across transaction boundaries, so it can't
    store references to database objects.
    """

    series_id = None
    hide_all_translations = None
    defer_translation_imports = None

    def prepare(self, series):
        """Set up `series`' state for a translations update.

        Use `restore` later to bring `series` back to its original state.
        """
        self.series_id = series.id
        self.hide_all_translations = series.hide_all_translations
        self.defer_translation_imports = series.defer_translation_imports
        series.hide_all_translations = True
        series.defer_translation_imports = True

    def restore(self):
        """Restore `series` to its normal state after translations update."""
        # Re-read series from database.  We can't keep a reference to the
        # database object, since transactions may have been committed since
        # prepare() was called.
        series = getUtility(IDistroSeriesSet).get(self.series_id)

        flags_modified = (
            not series.hide_all_translations
            or not series.defer_translation_imports
        )

        if flags_modified:
            # The flags have been changed while we were working.  Play safe
            # and don't touch them.
            raise SeriesTranslationFlagsModified(
                "Translations flags for %s have been changed while copy was "
                "in progress. "
                "Please check the hide_all_translations and "
                "defer_translation_imports flags for %s, since they may "
                "affect users' ability to work on this series' translations."
                % (series.name, series.name)
            )

        # Restore flags.
        series.hide_all_translations = self.hide_all_translations
        series.defer_translation_imports = self.defer_translation_imports


def copy_distroseries_translations(
    source,
    target,
    txn,
    logger,
    published_sources_only=False,
    check_archive=None,
    check_distroseries=None,
    skip_duplicates=False,
):
    """Copy translations into a new `DistroSeries`.

    Wraps around `copy_active_translations`, but also ensures that the
    `hide_all_translations` and `defer_translation_imports` flags are
    set.  After copying they are restored to their previous state.

    If published_sources_only is set, the set of sources in the target
    will be calculated and only templates for those sources will be
    copied.
    """
    statekeeper = SeriesStateKeeper()
    statekeeper.prepare(target)
    name = target.name
    txn.commit()
    txn.begin()

    copy_failed = False

    try:
        # Do the actual work.
        assert target.defer_translation_imports, (
            "defer_translation_imports not set!"
            " That would corrupt translation data mixing new imports"
            " with the information being copied."
        )
        assert target.hide_all_translations, (
            "hide_all_translations not set!"
            " That would allow users to see and modify incomplete"
            " translation state."
        )

        if published_sources_only:
            if check_archive is None:
                check_archive = target.main_archive
            if check_distroseries is None:
                check_distroseries = target
            spns = bulk.load(
                SourcePackageName,
                check_archive.getPublishedSources(
                    distroseries=check_distroseries,
                    status=active_publishing_status,
                )
                .config(distinct=True)
                .order_by(SourcePackagePublishingHistory.sourcepackagenameID)
                .values(SourcePackagePublishingHistory.sourcepackagenameID),
            )
        else:
            spns = None
        copy_active_translations(
            source,
            target,
            txn,
            logger,
            sourcepackagenames=spns,
            skip_duplicates=skip_duplicates,
        )
    except BaseException:
        copy_failed = True
        # Give us a fresh transaction for proper cleanup.
        txn.abort()
        txn.begin()
        raise
    finally:
        try:
            statekeeper.restore()
        except Warning as message:
            logger.warning(message)
        except BaseException:
            logger.warning(
                "Failed to restore hide_all_translations and "
                "defer_translation_imports flags on %s after translations "
                "copy failed.  Please check them manually." % name
            )
            # If the original copying etc. in the main try block failed, that
            # is the error most worth propagating.  Propagate a failure in
            # restoring the translations flags only if everything else went
            # well.
            if not copy_failed:
                raise
