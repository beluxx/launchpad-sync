VPOExport and VPOExportSet
=========================

The VPOExport and VPOExportSet classes retrieve and format data for
exports in a more efficient way than fetching the entire objects.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.translations.interfaces.vpoexport import IVPOExportSet

    >>> vpoexportset = getUtility(IVPOExportSet)
    >>> hoary = getUtility(IDistributionSet)['ubuntu']['hoary']

    >>> def describe_pofile(pofile):
    ...     return "%s %s %s" % (
    ...         pofile.potemplate.sourcepackagename.name,
    ...         pofile.potemplate.name, pofile.language.code)

To facilitate language pack exports, IVPOExportSet can enumerate all
current POFiles in a given distro series.

    >>> pofiles = sorted([
    ...     describe_pofile(pofile)
    ...     for pofile in vpoexportset.get_distroseries_pofiles(hoary)])
    >>> for pofile in pofiles:
    ...     print(pofile)
    evolution evolution-2.2 es
    evolution evolution-2.2 ja
    evolution evolution-2.2 xh
    evolution man es
    mozilla   pkgconf-mozilla cs
    mozilla   pkgconf-mozilla da
    mozilla   pkgconf-mozilla de
    mozilla   pkgconf-mozilla en
    mozilla   pkgconf-mozilla es
    mozilla   pkgconf-mozilla fi
    mozilla   pkgconf-mozilla fr
    mozilla   pkgconf-mozilla gl
    mozilla   pkgconf-mozilla it
    mozilla   pkgconf-mozilla ja
    mozilla   pkgconf-mozilla lt
    mozilla   pkgconf-mozilla nl
    mozilla   pkgconf-mozilla pt_BR
    mozilla   pkgconf-mozilla tr
    pmount    pmount ca
    pmount    pmount cs
    pmount    pmount de
    pmount    pmount es
    pmount    pmount es@test
    pmount    pmount fr
    pmount    pmount hr
    pmount    pmount it_IT
    pmount    pmount nb

    >>> print(len(pofiles))
    27
    >>> print(vpoexportset.get_distroseries_pofiles_count(hoary))
    27

The getTranslationRows method lists all translations found in the
pofile.

    >>> package = factory.makeSourcePackage()
    >>> potemplate = factory.makePOTemplate(
    ...     distroseries=package.distroseries,
    ...     sourcepackagename=package.sourcepackagename)
    >>> pofile = factory.makePOFile('eo', potemplate=potemplate)
    >>> tm = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile, current_other=True, translations=["esperanto1"],
    ...     potmsgset=factory.makePOTMsgSet(
    ...         potemplate=potemplate, sequence=1, singular="english1"))
    >>> tm = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile, current_other=False, translations=["esperanto2"],
    ...     potmsgset=factory.makePOTMsgSet(
    ...         potemplate=potemplate, sequence=2, singular="english2"))

    >>> def describe_poexport_row(row):
    ...     return "%s %s %s" % (
    ...         row.sequence, row.msgid_singular, row.translation0)

    >>> rows = sorted([
    ...     describe_poexport_row(row)
    ...     for row in pofile.getTranslationRows()])
    >>> for row in rows:
    ...     print(row)
    1 english1 esperanto1
    2 english2 esperanto2

The getChangedRows method lists all translations found in the
pofile it is given if they were changed after they were imported. These are
all current messages that have not been imported.

    >>> rows = sorted([
    ...     describe_poexport_row(row)
    ...     for row in pofile.getChangedRows()])
    >>> for row in rows:
    ...     print(row)
    2 english2 esperanto2


VPOExport and translation divergence
------------------------------------

A particular product has two series, trunk and stable, each with the
same template.  The templates thus share messages.

    >>> product = factory.makeProduct()
    >>> trunk = product.getSeries('trunk')
    >>> stable = factory.makeProductSeries()
    >>> trunk_template = factory.makePOTemplate(productseries=trunk, name='t')
    >>> stable_template = factory.makePOTemplate(
    ...     productseries=stable, name='t')

The two templates contain the same two POTMsgSets.  They are shared
between the two templates.

    >>> potmsgset1 = factory.makePOTMsgSet(trunk_template, '1', sequence=1)
    >>> potmsgset2 = factory.makePOTMsgSet(trunk_template, '2', sequence=2)
    >>> item = potmsgset1.setSequence(stable_template, 1)
    >>> item = potmsgset2.setSequence(stable_template, 2)

The templates are translated to Dutch.

Of the translations, one message is diverged for trunk and the other is
diverged for stable.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> trunk_pofile = factory.makePOFile('nl', potemplate=trunk_template)
    >>> stable_pofile = factory.makePOFile('nl', potemplate=stable_template)
    >>> message1 = factory.makeDivergedTranslationMessage(
    ...     pofile=removeSecurityProxy(trunk_pofile), potmsgset=potmsgset1,
    ...     translations=['een'])
    >>> message2 = factory.makeDivergedTranslationMessage(
    ...     pofile=removeSecurityProxy(stable_pofile), potmsgset=potmsgset2,
    ...     translations=['twee'])

When we export trunk, only the trunk message shows up.

    >>> for row in trunk_pofile.getTranslationRows():
    ...     print(describe_poexport_row(row))
    1   1   een
    2   2   None

In an export for stable, only the stable message shows up.

    >>> for row in stable_pofile.getTranslationRows():
    ...     print(describe_poexport_row(row))
    2   2   twee
    1   1   None
