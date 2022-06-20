TranslationBuildApprover
========================

The TranslationBuildApprover is a much simpler approver than the
TranslationBranchApprover. The latter tries to detect when templates have
been removed or renamed and refuses to approve anything when that happens.
This new approver does not care about these things but tries to approve as
many templates as possible. If this behaviour proofs practical, it should
replace the TranslationBranchApprover in the future.

    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue)
    >>> queue = getUtility(ITranslationImportQueue)
    >>> importer_person = factory.makePerson()
    >>> from lp.translations.model.approver import TranslationBuildApprover
    >>> def makeQueueEntry(path, series):
    ...     return queue.addOrUpdateEntry(
    ...         path, b"#Dummy content.", False, importer_person,
    ...         productseries=series)
    >>> login("foo.bar@canonical.com")

It will approve all template files that it can derive a name from. It will
create a new template if none is found by that name.

    >>> productseries = factory.makeProductSeries()
    >>> approver = TranslationBuildApprover(
    ...     ["po/my_domain.pot"], productseries=productseries)
    >>> entry = makeQueueEntry("po/my_domain.pot", productseries)
    >>> print(entry.status.title)
    Needs Review
    >>> entry = approver.approve(entry)
    >>> print(entry.status.title)
    Approved

If a template with the name exists, it will target the import entry to it and
not create a new template.

    >>> productseries = factory.makeProductSeries()
    >>> existing_potemplate = factory.makePOTemplate(
    ...     name='existing-domain', productseries=productseries)
    >>> approver = TranslationBuildApprover(
    ...     ["po/existing_domain.pot"], productseries=productseries)
    >>> entry = makeQueueEntry(
    ...     "po/existing_domain.pot", productseries)
    >>> entry = approver.approve(entry)
    >>> print(entry.status.title)
    Approved
    >>> print(entry.potemplate == existing_potemplate)
    True

A template file with generic names is only approved if it is the only one that
is being imported and the series has zero or one templates. If no template
exists, a template with the name of the product is created.

    >>> product = factory.makeProduct(name='fooproduct')
    >>> productseries = factory.makeProductSeries(product=product)
    >>> generic_entry = makeQueueEntry('po/messages.pot', productseries)
    >>> approver = TranslationBuildApprover(
    ...     ['po/messages.pot'], productseries=productseries)
    >>> generic_entry = approver.approve(generic_entry)
    >>> print(generic_entry.status.title)
    Approved
    >>> print(generic_entry.potemplate.translation_domain)
    fooproduct
    >>> print(generic_entry.potemplate.name)
    fooproduct

If there are other files or templates, files with generic names are not
approved. Only the ones containing a translation domain are approved.

    >>> productseries = factory.makeProductSeries()
    >>> approver = TranslationBuildApprover(
    ...     ["po/messages.pot", "validdomain.pot"],
    ...     productseries=productseries)
    >>> generic_entry = makeQueueEntry("po/messages.pot", productseries)
    >>> generic_entry = approver.approve(generic_entry)
    >>> print(generic_entry.status.title)
    Needs Review
    >>> valid_entry = makeQueueEntry("validdomain.pot", productseries)
    >>> valid_entry = approver.approve(valid_entry)
    >>> print(valid_entry.status.title)
    Approved
