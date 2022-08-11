Migrating translations between distro series
============================================

When a new release series is created for a distribution it usually
inherits all settings and data from its parent (preceding) series. To
facilitate this for the translations the function
copy_active_translations is called from a script once after the release
series is created.

    >>> login("foo.bar@canonical.com")
    >>> foobuntu = factory.makeDistribution('foobuntu', 'Foobuntu')
    >>> barty = factory.makeDistroSeries(foobuntu, '99.0', name='barty')
    >>> carty = factory.makeDistroSeries(foobuntu, '99.1', name='carty')

Functions to create source packages, templates and and translations.

    >>> def makeSourcePackage(name):
    ...     packagename =  factory.getOrMakeSourcePackageName(name)
    ...     return factory.makeDistributionSourcePackage(packagename,
    ...                                                  foobuntu)

    >>> def makePOTemplateAndPOFiles(distroseries, package, name, languages):
    ...     return factory.makePOTemplateAndPOFiles(languages,
    ...         distroseries=distroseries,
    ...         sourcepackagename=package.sourcepackagename,
    ...         name=name, translation_domain=name+'-domain')

    >>> def makeTranslation(template, msgid, translations, sequence=None):
    ...     if sequence is None:
    ...         sequence = factory.getUniqueInteger()
    ...     msgset = factory.makePOTMsgSet(template, msgid, sequence=sequence)
    ...     for language, translation in translations.items():
    ...         pofile = template.getPOFileByLang(language)
    ...         factory.makeCurrentTranslationMessage(
    ...             pofile, msgset, translations=[translation],
    ...             current_other=True)
    ...     return msgset

    >>> package1 = makeSourcePackage('package1')
    >>> package2 = makeSourcePackage('package2')

    >>> template1 = makePOTemplateAndPOFiles(barty, package1,
    ...                                          'template1', ['eo'])
    >>> template2 = makePOTemplateAndPOFiles(barty, package2,
    ...                                          'template2', ['eo', 'de'])
    >>> template3 = makePOTemplateAndPOFiles(barty, package1,
    ...                                          'template3', ['eo'])

    >>> msgset11 = makeTranslation(template1, 'msgid11',
    ...                           {'eo': 'eo11'})
    >>> msgset21 = makeTranslation(template2, 'msgid21',
    ...                            {'eo': 'eo21', 'de': 'de21'})
    >>> msgset22 = makeTranslation(template2, 'msgid22',
    ...                            {'eo': 'eo22', 'de': 'de22'})
    >>> msgset31 = makeTranslation(template3, 'msgid31', {'eo': 'eo31'})

The parent series may have obsolete POTMsgSets which will not be copied.

    >>> msgset12 = makeTranslation(template1, 'msgid12', {'eo': 'eo12'}, 0)

Also, template3 happens to be deactivated.

    >>> template3.iscurrent = False

We need a transaction manager (in this case a fake one) to make the copy work.

    >>> from lp.testing.faketransaction import FakeTransaction
    >>> txn = FakeTransaction()


Performing the migration
========================

A pristine distroseries can be filled with copies of translation templates
and translation files from the parent. The actual translations, stored in
POTMsgSet and TranslationMessage object, are shared between the two series.

    >>> from lp.services.log.logger import DevNullLogger
    >>> from lp.translations.model.distroseries_translations_copy import (
    ...     copy_active_translations)
    >>> logger = DevNullLogger()
    >>> copy_active_translations(barty, carty, txn, logger)

All current templates were copied from the parent series but the deactivated
template template3 was not copied.

    >>> from operator import attrgetter
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> carty_templates = getUtility(
    ...     IPOTemplateSet).getSubset(distroseries=carty)
    >>> len(carty_templates)
    2
    >>> for template in sorted(carty_templates, key=attrgetter('name')):
    ...     print(template.name)
    template1
    template2
    >>> carty_template1 = carty_templates.getPOTemplateByName('template1')
    >>> carty_template2 = carty_templates.getPOTemplateByName('template2')
    >>> carty_template1 == template1
    False
    >>> carty_template2 == template2
    False

All POFiles for the copied POTemplates have also been copied.

    >>> all_pofiles = sum(
    ...     [list(template.pofiles) for template in carty_templates], [])
    >>> for pofile in sorted(all_pofiles, key=attrgetter('path')):
    ...     print(pofile.path)
    template1-domain-eo.po
    template2-domain-de.po
    template2-domain-eo.po

All POTMsgSets from  the parent series that were not obsolete are now found
in the new series.

    >>> potmsgsets = carty_template1.getPOTMsgSets()
    >>> print(potmsgsets.count())
    1
    >>> potmsgsets[0] == msgset11
    True

    >>> potmsgsets = carty_template2.getPOTMsgSets()
    >>> print(potmsgsets.count())
    2
    >>> potmsgsets[0] == msgset21
    True
    >>> potmsgsets[1] == msgset22
    True


Once the migration is done, copy_active_translations must not be called
again as it only operates on distroseries without any translation templates.
Because of message sharing incremental copies are no longer needed.

    >>> copy_active_translations(barty, carty, txn, logger)
    Traceback (most recent call last):
    ...
    AssertionError:
    The target series must not yet have any translation templates.


Running the script
==================

Now, we execute the script that will do the migration using
copy_active_translations. For that we create a new child series to
receive those translations. For testing purposes this series has
translation imports enabled.

    >>> darty = factory.makeDistroSeries(
    ...     foobuntu, '99.2', name='darty', previous_series=barty)
    >>> darty_id = darty.id
    >>> darty.defer_translation_imports = False

The script starts its own transactions, so we need to commit here to be sure
the new series will be available in the script.

    >>> import transaction
    >>> transaction.commit()

The script fails as long as the defer_translation_imports flag is not
set.

    >>> from lp.testing.script import run_script
    >>> returnvalue, output, error_output = run_script(
    ...     'scripts/copy-distroseries-translations.py',
    ...     ['--distribution=foobuntu', '--series=darty'])
    >>> returnvalue
    1
    >>> print(error_output)
    INFO    Creating lockfile:
      /var/lock/launchpad-copy-missing-translations-foobuntu-darty.lock
    ERROR   Before this process starts, set the hide_all_translations and
            defer_translation_imports flags for distribution foobuntu, series
            darty; or use the --force option to make it happen
            automatically.
    INFO    OOPS-...
    <BLANKLINE>

    >>> transaction.abort()
    >>> from lp.registry.model.distroseries import DistroSeries
    >>> darty = DistroSeries.get(darty_id)
    >>> darty.defer_translation_imports
    False
    >>> darty.hide_all_translations
    True

It succeeds, however, when we pass the --force option.  The script then
sets the defer_translation_imports flag itself before copying.

    >>> transaction.abort()
    >>> darty = DistroSeries.get(darty_id)
    >>> returnvalue, output, error_output = run_script(
    ...     'scripts/copy-distroseries-translations.py',
    ...     ['--distribution=foobuntu', '--series=darty', '--force'])
    >>> returnvalue
    0
    >>> print(error_output)
    INFO    Creating lockfile:
      /var/lock/launchpad-copy-missing-translations-foobuntu-darty.lock
    INFO    Starting...
    INFO    Populating blank distroseries foobuntu darty with
            translations from foobuntu barty.
    INFO    Extracting from potemplate into
            "temp_potemplate_holding_foobuntu_darty"...
    INFO    Extracting from translationtemplateitem into
            "temp_translationtemplateitem_holding_foobuntu_darty"...
    INFO    Extracting from pofile into
            "temp_pofile_holding_foobuntu_darty"...
    INFO    Pouring "temp_potemplate_holding_foobuntu_darty"
            back into potemplate...
    INFO    Pouring "temp_translationtemplateitem_holding_foobuntu_darty"
            back into translationtemplateitem...
    INFO    Pouring "temp_pofile_holding_foobuntu_darty"
            back into pofile...
    INFO    Done.
    <BLANKLINE>

After completing, the script restores the defer_translation_imports
flag to its previous value (off).

    >>> transaction.abort()
    >>> darty = DistroSeries.get(darty_id)
    >>> darty.defer_translation_imports
    False
    >>> darty.hide_all_translations
    True

Once the script has finished, the new distro series has all the active
templates of the parent series.

    >>> dartempls = getUtility(IPOTemplateSet).getSubset(distroseries=darty)
    >>> len(dartempls)
    2
    >>> for template in sorted(dartempls, key=attrgetter('name')):
    ...     print(template.name)
    template1
    template2

The script defaults to copying from the given series' previous_series,
but that can be overridden.

    >>> grumpy = factory.makeDistroSeries(
    ...     distribution=factory.makeDistribution(name="notbuntu"),
    ...     name='grumpy')
    >>> grumpy_id = grumpy.id
    >>> transaction.commit()

    >>> returnvalue, output, error_output = run_script(
    ...     'scripts/copy-distroseries-translations.py',
    ...     ['--distribution=notbuntu', '--series=grumpy'])
    >>> returnvalue
    2
    >>> print(error_output)
    INFO    Creating lockfile:
      /var/lock/launchpad-copy-missing-translations-notbuntu-grumpy.lock
    Usage: copy-distroseries-translations.py [options]
    copy-distroseries-translations.py: error: No source series specified
    and target has no previous series.
    <BLANKLINE>

    >>> returnvalue, output, error_output = run_script(
    ...     'scripts/copy-distroseries-translations.py',
    ...     ['--distribution=notbuntu', '--series=grumpy',
    ...      '--from-distribution=foobuntu' , '--from-series=darty'])
    >>> returnvalue
    0
    >>> print(error_output)
    INFO    Creating lockfile:
      /var/lock/launchpad-copy-missing-translations-notbuntu-grumpy.lock
    INFO    Starting...
    INFO    Populating blank distroseries notbuntu grumpy with
            translations from foobuntu darty.
    ...
    INFO    Done.
    <BLANKLINE>

It's also possible to copy only the subset of templates that have a
corresponding source package published in the target. If we create a new
series containing only package1 and then copy with
--published-sources-only, only template1 makes it across. template2 is
for package2, and template3 is inactive, so they're both skipped.

    >>> lumpy = factory.makeDistroSeries(
    ...     distribution=factory.makeDistribution(name="wartbuntu"),
    ...     name='lumpy', previous_series=carty)
    >>> lumpy_id = lumpy.id
    >>> transaction.commit()

    >>> returnvalue, output, error_output = run_script(
    ...     'scripts/copy-distroseries-translations.py',
    ...     ['--distribution=wartbuntu', '--series=lumpy',
    ...      '--published-sources-only'])
    >>> returnvalue
    0
    >>> transaction.abort()
    >>> lumpy = DistroSeries.get(lumpy_id)
    >>> len(getUtility(IPOTemplateSet).getSubset(distroseries=lumpy))
    0

    >>> factory.makeSourcePackagePublishingHistory(
    ...     archive=lumpy.main_archive, distroseries=lumpy,
    ...     sourcepackagename='package1')
    <SourcePackagePublishingHistory ...>
    >>> transaction.commit()

    >>> returnvalue, output, error_output = run_script(
    ...     'scripts/copy-distroseries-translations.py',
    ...     ['--distribution=wartbuntu', '--series=lumpy',
    ...      '--published-sources-only'])
    >>> returnvalue
    0
    >>> transaction.abort()
    >>> lumpy = DistroSeries.get(lumpy_id)
    >>> for pot in getUtility(IPOTemplateSet).getSubset(distroseries=lumpy):
    ...     print(pot.name)
    template1
